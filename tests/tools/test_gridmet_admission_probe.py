"""Safety and evidence checks for the bounded live acceptance CLI."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools import gridmet_admission_probe as probe


pytestmark = pytest.mark.unit
KEY = probe.ACCEPTANCE_PREFIX + "0123456789ab-20260907-test"


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    previous = probe.signal.getsignal(probe.signal.SIGTERM)
    yield
    probe.signal.signal(probe.signal.SIGTERM, previous)


@pytest.mark.parametrize("key", [probe.CANONICAL_KEY, "custom:operational"])
def test_operational_namespaces_are_inspection_only(monkeypatch, key):
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_KEY", " custom:operational ")
    with pytest.raises(ValueError, match="read-only"):
        probe.validate_key(key)
    assert probe.validate_key(key, readonly=True) == key


def test_even_acceptance_shaped_operational_override_is_protected(monkeypatch):
    monkeypatch.setenv("GRIDMET_REDIS_ADMISSION_KEY", KEY)
    with pytest.raises(ValueError, match="read-only"):
        probe.validate_key(KEY)


@pytest.mark.parametrize("key", ["arbitrary", probe.ACCEPTANCE_PREFIX + "short", "x{y}", "redis://secret@host", "a" * 161])
def test_mutations_require_unique_bounded_acceptance_identifier(key):
    with pytest.raises(ValueError):
        probe.validate_key(key)


def test_valid_acceptance_key():
    assert probe.validate_key(KEY) == KEY


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "601"])
def test_unbounded_timing_rejected(value):
    with pytest.raises(probe.argparse.ArgumentTypeError):
        probe.bounded_number(value)


def evidence():
    events = []
    for sequence in range(1, 7):
        events.extend([
            {"event": "acquired", "key": KEY, "sequence": sequence, "admitted_at_server_seconds": sequence,
             "container": "container1", "pid": sequence, "id": str(sequence)},
            {"event": "released", "key": KEY, "container": "container1", "pid": sequence, "id": str(sequence)},
        ])
    samples = [{"active": 2, "queued": 4}, {"active": 0, "queued": 0}]
    return events, samples


def test_summary_requires_full_concurrency_and_cleanup_evidence():
    events, samples = evidence()
    summary = probe.summarize(events, samples, 6, 2)
    assert summary["pass"]
    assert summary["observed_peak"] == 2
    assert summary["acquisition_order"] == list(range(1, 7))
    assert summary["completed"] == 6


@pytest.mark.parametrize("defect", ["over_limit", "no_queue", "not_empty", "missing_worker", "fifo", "duplicate"])
def test_summary_does_not_claim_incomplete_or_invalid_run_passes(defect):
    events, samples = evidence()
    if defect == "over_limit":
        samples[0]["active"] = 3
    elif defect == "no_queue":
        samples[0]["queued"] = 0
    elif defect == "not_empty":
        samples[-1]["active"] = 1
    elif defect == "missing_worker":
        events.pop()
    elif defect == "fifo":
        events[0]["admitted_at_server_seconds"] = 10
    elif defect == "duplicate":
        events[2]["sequence"] = 1
    assert not probe.summarize(events, samples, 6, 2)["pass"]


def test_cli_sanitizes_exception_text(monkeypatch, capsys):
    def fail(_args):
        raise RuntimeError("redis://username:credential@host full-query?secret=token")

    monkeypatch.setattr(probe, "worker", fail)
    assert probe.main(["worker", "--key", KEY]) == 1
    result = capsys.readouterr().out
    assert "credential" not in result and "secret" not in result and "token" not in result
    assert json.loads(result)["error_type"] == "RuntimeError"


@pytest.mark.parametrize("option,value", [("--contenders", "17"), ("--limit", "0"), ("--poll-seconds", "0.001")])
def test_cli_refuses_excess_processes_or_redis_sampling(monkeypatch, capsys, option, value):
    def unexpected(_args):
        pytest.fail("invalid probe must not construct a controller")

    monkeypatch.setattr(probe, "controller", unexpected)
    assert probe.main(["run", "--key", KEY, option, value]) == 1
    assert json.loads(capsys.readouterr().out)["error_type"] == "ValueError"


def test_worker_releases_on_foreground_failure(monkeypatch):
    released = []

    class Permit:
        snapshot = SimpleNamespace(sequence=7, server_time_seconds=100)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            released.append(True)

        def check(self):
            raise RuntimeError("lease lost")

    client = SimpleNamespace(acquire=lambda **_kwargs: Permit())
    monkeypatch.setattr(probe, "controller", lambda _args: client)
    monkeypatch.setattr(probe, "observe_once", lambda _client: {"active": 1, "queued": 0})
    monkeypatch.setattr(probe, "emit", lambda _event: None)
    args = probe.parser().parse_args(["worker", "--key", KEY])
    with pytest.raises(RuntimeError, match="lease lost"):
        probe.worker(args)
    assert released == [True]


def test_offline_summary_combines_observer_and_containers(tmp_path):
    events, samples = evidence()
    worker_path = tmp_path / "workers.jsonl"
    observer_path = tmp_path / "observer.jsonl"
    worker_path.write_text("\n".join(json.dumps(event) for event in events))
    observer_path.write_text("\n".join(json.dumps({"event": "sample", "key": KEY, "server_time": index, **sample})
                                         for index, sample in enumerate(samples)))
    args = probe.parser().parse_args(["summarize", "--key", KEY, "--input", str(worker_path), "--input", str(observer_path)])
    assert probe.summarize_files(args)["pass"]
    args.minimum_containers = 2
    assert not probe.summarize_files(args)["pass"]
    args.key = KEY + "-different"
    with pytest.raises(ValueError, match="namespace"):
        probe.summarize_files(args)


def test_summary_checks_each_released_identity():
    events, samples = evidence()
    events[1]["pid"] = 999
    assert not probe.summarize(events, samples, 6, 2)["pass"]


def test_unresponsive_children_are_killed_and_reaped():
    operations = []

    class Child:
        waits = 0

        def poll(self):
            return None

        def terminate(self):
            operations.append("terminate")

        def kill(self):
            operations.append("kill")

        def wait(self, timeout):
            assert 0 < timeout <= 5
            self.waits += 1
            operations.append("wait")
            if self.waits == 1:
                raise probe.subprocess.TimeoutExpired("probe", timeout)
            return -9

    probe.stop_children([Child()])
    assert operations == ["terminate", "wait", "kill", "wait"]
