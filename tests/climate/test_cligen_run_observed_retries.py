from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

import wepppy.climates.cligen.cligen as cligen_module

pytestmark = pytest.mark.unit


class _FakeObservedProcess:
    def __init__(self, behavior, cli_path):
        self._behavior = behavior
        self._cli_path = cli_path
        self._wait_calls = 0
        self.returncode = behavior.get("returncode", 0)
        if "cli_text" in behavior:
            cli_path.write_text(behavior["cli_text"], encoding="ascii")

    def wait(self, timeout=None):
        self._wait_calls += 1
        if self._behavior.get("timeout") and self._wait_calls == 1:
            raise subprocess.TimeoutExpired(cmd=["fake_cligen"], timeout=timeout)
        if self._behavior.get("terminate_timeout") and self._wait_calls == 2:
            raise subprocess.TimeoutExpired(cmd=["fake_cligen"], timeout=timeout)
        if self._behavior.get("kill_timeout") and self._wait_calls == 3:
            raise subprocess.TimeoutExpired(cmd=["fake_cligen"], timeout=timeout)
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.returncode = -9


def _make_cligen(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cligen532").write_text("#!/bin/sh\n", encoding="ascii")
    monkeypatch.setattr(cligen_module, "_bin_dir", str(bin_dir))

    (tmp_path / "or354811.par").write_text("par\n", encoding="ascii")
    (tmp_path / "observed.prn").write_text("prn\n", encoding="ascii")

    cligen = object.__new__(cligen_module.Cligen)
    cligen.wd = str(tmp_path)
    cligen.cliver = "5.3.2"
    cligen.station = SimpleNamespace(
        par="or354811.par",
        parpath=str(tmp_path / "or354811.par"),
    )
    return cligen


def test_run_observed_retries_timeout_and_logs_flake(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"
    attempts = [
        {"timeout": True, "cli_text": "partial\n"},
        {"returncode": 0, "cli_text": "complete\n"},
    ]
    popen_calls = []
    sleep_calls = []
    wait_timeouts = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeObservedProcess(attempts.pop(0), cli_path)

    original_wait = _FakeObservedProcess.wait

    def _tracking_wait(self, timeout=None):
        wait_timeouts.append(timeout)
        return original_wait(self, timeout=timeout)

    monkeypatch.setattr(_FakeObservedProcess, "wait", _tracking_wait)
    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(cligen_module.random, "uniform", lambda _a, _b: 0.25)
    monkeypatch.setattr(cligen_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    cligen.run_observed("observed.prn", cli_fn="observed.cli")

    assert cli_path.read_text(encoding="ascii") == "complete\n"
    assert len(popen_calls) == 2
    assert attempts == []
    assert sleep_calls == [0.75]
    assert wait_timeouts == [20, 2, 20]

    log_text = (tmp_path / "cligen_observed.log").read_text(encoding="ascii")
    assert "timeout=20s timeout_retries=3" in log_text
    assert "retrying after timeout" in log_text
    assert "flake_detected timeout_attempts=1 success_attempt=2/4" in log_text


def test_run_observed_exhausts_timeouts_and_removes_partial_cli(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"
    attempts = [
        {"timeout": True, "cli_text": "partial one\n"},
        {"timeout": True, "cli_text": "partial two\n"},
    ]
    popen_calls = []
    sleep_calls = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeObservedProcess(attempts.pop(0), cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(cligen_module.random, "uniform", lambda _a, _b: 0.2)
    monkeypatch.setattr(cligen_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    with pytest.raises(TimeoutError) as exc:
        cligen.run_observed(
            "observed.prn",
            cli_fn="observed.cli",
            timeout=1,
            timeout_retries=1,
        )

    assert "timeout=1s" in str(exc.value)
    assert "attempts=2" in str(exc.value)
    assert not cli_path.exists()
    assert len(popen_calls) == 2
    assert attempts == []
    assert sleep_calls == [0.7]

    log_text = (tmp_path / "cligen_observed.log").read_text(encoding="ascii")
    assert "timeout attempt=2/2" in log_text
    assert "retrying after timeout" in log_text


def test_run_observed_timeout_retries_zero_fails_after_first_timeout(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"
    attempts = [{"timeout": True, "cli_text": "partial\n"}]
    popen_calls = []
    sleep_calls = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeObservedProcess(attempts.pop(0), cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(cligen_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    with pytest.raises(TimeoutError) as exc:
        cligen.run_observed(
            "observed.prn",
            cli_fn="observed.cli",
            timeout=1,
            timeout_retries=0,
        )

    assert "attempts=1" in str(exc.value)
    assert not cli_path.exists()
    assert len(popen_calls) == 1
    assert attempts == []
    assert sleep_calls == []


def test_run_observed_process_linger_fails_without_retry(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"
    attempts = [
        {
            "timeout": True,
            "terminate_timeout": True,
            "kill_timeout": True,
            "cli_text": "partial\n",
        }
    ]
    popen_calls = []
    sleep_calls = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeObservedProcess(attempts.pop(0), cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(cligen_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    with pytest.raises(TimeoutError) as exc:
        cligen.run_observed(
            "observed.prn",
            cli_fn="observed.cli",
            timeout=1,
            timeout_retries=3,
        )

    assert "attempts=4" in str(exc.value)
    assert not cli_path.exists()
    assert len(popen_calls) == 1
    assert attempts == []
    assert sleep_calls == []

    log_text = (tmp_path / "cligen_observed.log").read_text(encoding="ascii")
    assert "kill timed out; process may linger" in log_text
    assert "retrying after timeout" not in log_text


def test_run_observed_nonzero_exit_removes_partial_cli(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"

    def _fake_popen(*args, **kwargs):
        return _FakeObservedProcess(
            {"returncode": 2, "cli_text": "partial\n"},
            cli_path,
        )

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)

    with pytest.raises(RuntimeError) as exc:
        cligen.run_observed("observed.prn", cli_fn="observed.cli")

    assert "exited 2" in str(exc.value)
    assert not cli_path.exists()


def test_run_observed_exit_zero_without_cli_fails(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"

    def _fake_popen(*args, **kwargs):
        return _FakeObservedProcess({"returncode": 0}, cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)

    with pytest.raises(AssertionError) as exc:
        cligen.run_observed("observed.prn", cli_fn="observed.cli")

    assert "Failed to create observed.cli" in str(exc.value)
    assert not cli_path.exists()


def test_run_observed_exit_zero_with_quality_errors_fails(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"

    def _fake_popen(*args, **kwargs):
        log_fp = kwargs["stdout"]
        log_fp.write("Failed SN SD test.\n")
        log_fp.write("*** ERROR *** Could not produce desired level of quality in\n")
        log_fp.flush()
        return _FakeObservedProcess({"returncode": 0, "cli_text": "complete\n"}, cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)

    with pytest.raises(RuntimeError) as exc:
        cligen.run_observed("observed.prn", cli_fn="observed.cli")

    message = str(exc.value)
    assert "quality guard tripped" in message
    assert "failed sn sd test" in message
    assert "could not produce desired level of quality" in message
    assert not cli_path.exists()
