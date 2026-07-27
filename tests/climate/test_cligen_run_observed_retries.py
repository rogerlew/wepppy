from __future__ import annotations

import subprocess
import stat
from types import SimpleNamespace

import pandas as pd
import pytest

import wepppy.climates.cligen.cligen as cligen_module

pytestmark = pytest.mark.unit


def test_df_to_prn_serializes_unpublished_future_values_as_missing_sentinels(tmp_path):
    frame = pd.DataFrame(
        {
            "prcp": [1.0, float("nan")],
            "tmax": [10.0, float("nan")],
            "tmin": [0.0, float("nan")],
        },
        index=pd.to_datetime(["2026-07-23", "2026-07-24"]),
    )
    prn_path = tmp_path / "partial.prn"

    cligen_module.df_to_prn(
        frame,
        str(prn_path),
        "prcp",
        "tmax",
        "tmin",
        pad_to_end_of_year=False,
    )

    future_fields = prn_path.read_text(encoding="ascii").splitlines()[1].split()
    assert future_fields[3:] == ["9999", "9999", "9999"]


def test_df_to_prn_rejects_internal_primary_variable_hole(tmp_path):
    frame = pd.DataFrame(
        {
            "prcp": [1.0, float("nan"), 2.0],
            "tmax": [10.0, 11.0, 12.0],
            "tmin": [0.0, 1.0, 2.0],
        },
        index=pd.to_datetime(["2026-07-23", "2026-07-24", "2026-07-25"]),
    )

    with pytest.raises(
        ValueError,
        match=r"prcp contains an internal missing-data hole.*2026-07-24",
    ):
        cligen_module.df_to_prn(
            frame,
            str(tmp_path / "invalid.prn"),
            "prcp",
            "tmax",
            "tmin",
            reject_internal_missing=True,
        )

    assert not (tmp_path / "invalid.prn").exists()


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


def test_stage_station_parameter_file_replaces_partial_destination_atomically(tmp_path):
    source_dir = tmp_path / "source"
    run_dir = tmp_path / "run"
    source_dir.mkdir()
    run_dir.mkdir()
    source_path = source_dir / "or354811.par"
    destination_path = run_dir / source_path.name
    source_path.write_bytes(b"complete station data\n" * 32)
    destination_path.write_bytes(b"partial")
    source_path.chmod(0o775)
    destination_path.chmod(0o640)

    cligen = object.__new__(cligen_module.Cligen)
    cligen.wd = str(run_dir)
    cligen.station = SimpleNamespace(
        par=source_path.name,
        parpath=str(source_path),
    )

    staged_path = cligen.stage_station_parameter_file()

    assert staged_path == str(destination_path)
    assert destination_path.read_bytes() == source_path.read_bytes()
    assert stat.S_IMODE(destination_path.stat().st_mode) == 0o640
    assert list(run_dir.glob(f".{source_path.name}.*")) == []


def test_stage_station_parameter_file_reuses_complete_destination(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    run_dir = tmp_path / "run"
    source_dir.mkdir()
    run_dir.mkdir()
    source_path = source_dir / "or354811.par"
    destination_path = run_dir / source_path.name
    station_data = b"complete station data\n"
    source_path.write_bytes(station_data)
    destination_path.write_bytes(station_data)

    cligen = object.__new__(cligen_module.Cligen)
    cligen.wd = str(run_dir)
    cligen.station = SimpleNamespace(
        par=source_path.name,
        parpath=str(source_path),
    )
    replace_calls = []
    monkeypatch.setattr(cligen_module.os, "replace", lambda *_args: replace_calls.append(_args))

    assert cligen.stage_station_parameter_file() == str(destination_path)
    assert replace_calls == []


def test_stage_station_parameter_file_first_create_does_not_copy_execute_bits(tmp_path):
    source_dir = tmp_path / "source"
    run_dir = tmp_path / "run"
    source_dir.mkdir()
    run_dir.mkdir()
    source_path = source_dir / "or354811.par"
    destination_path = run_dir / source_path.name
    source_path.write_bytes(b"complete station data\n")
    source_path.chmod(0o775)

    cligen = object.__new__(cligen_module.Cligen)
    cligen.wd = str(run_dir)
    cligen.station = SimpleNamespace(
        par=source_path.name,
        parpath=str(source_path),
    )

    cligen.stage_station_parameter_file()

    assert destination_path.read_bytes() == source_path.read_bytes()
    assert stat.S_IMODE(destination_path.stat().st_mode) & 0o111 == 0


def test_stage_station_parameter_file_preserves_old_copy_and_cleans_up_on_failure(
    tmp_path,
    monkeypatch,
):
    source_dir = tmp_path / "source"
    run_dir = tmp_path / "run"
    source_dir.mkdir()
    run_dir.mkdir()
    source_path = source_dir / "or354811.par"
    destination_path = run_dir / source_path.name
    source_path.write_bytes(b"complete station data\n" * 32)
    destination_path.write_bytes(b"old complete station data\n")

    cligen = object.__new__(cligen_module.Cligen)
    cligen.wd = str(run_dir)
    cligen.station = SimpleNamespace(
        par=source_path.name,
        parpath=str(source_path),
    )
    original_replace = cligen_module.os.replace

    def _fail_replace(_source, _destination):
        assert destination_path.read_bytes() == b"old complete station data\n"
        raise OSError("simulated NAS replace failure")

    monkeypatch.setattr(cligen_module.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="simulated NAS replace failure"):
        cligen.stage_station_parameter_file()

    assert destination_path.read_bytes() == b"old complete station data\n"
    assert list(run_dir.glob(f".{source_path.name}.*")) == []

    monkeypatch.setattr(cligen_module.os, "replace", original_replace)
    assert cligen.stage_station_parameter_file() == str(destination_path)
    assert destination_path.read_bytes() == source_path.read_bytes()


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


def test_run_observed_exit_zero_with_quality_errors_can_silently_pass(monkeypatch, tmp_path):
    cligen = _make_cligen(tmp_path, monkeypatch)
    cli_path = tmp_path / "observed.cli"

    def _fake_popen(*args, **kwargs):
        log_fp = kwargs["stdout"]
        log_fp.write("Failed SN SD test.\n")
        log_fp.write("*** ERROR *** Could not produce desired level of quality in\n")
        log_fp.flush()
        return _FakeObservedProcess({"returncode": 0, "cli_text": "complete\n"}, cli_path)

    monkeypatch.setattr(cligen_module.subprocess, "Popen", _fake_popen)

    bypassed = cligen.run_observed(
        "observed.prn",
        cli_fn="observed.cli",
        silently_pass_quality_guard=True,
    )

    assert bypassed is True
    assert cli_path.exists()
