import subprocess

import pytest

from wepp_runner import wepp_runner as wepp_runner_module

pytestmark = pytest.mark.unit


class _FakeProcess:
    def __init__(self, behavior):
        self._behavior = behavior
        self._timeout_raised = False
        self.returncode = behavior.get("returncode", 0)

    def communicate(self, timeout=None):
        if self._behavior.get("timeout") and timeout is not None and not self._timeout_raised:
            self._timeout_raised = True
            raise subprocess.TimeoutExpired(cmd=["fake_wepp"], timeout=timeout)
        return self._behavior.get("stdout", ""), ""

    def kill(self):
        self.returncode = -9


def _write_hillslope_inputs(tmp_path, wepp_id):
    for suffix in ("man", "sol", "slp", "cli", "run"):
        (tmp_path / f"p{wepp_id}.{suffix}").write_text("stub\n", encoding="ascii")


def test_run_hillslope_retries_timeout_and_logs_flake(monkeypatch, tmp_path):
    wepp_id = 101
    _write_hillslope_inputs(tmp_path, wepp_id)

    attempts = [
        {"timeout": True, "stdout": "Year 34 of 46\n"},
        {"stdout": "WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY\n"},
    ]
    popen_calls = []
    sleep_calls = []
    metric_events = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeProcess(attempts.pop(0))

    monkeypatch.setattr(wepp_runner_module.random, "uniform", lambda _a, _b: 0.25)
    monkeypatch.setattr(wepp_runner_module, "sleep", lambda delay: sleep_calls.append(delay))
    monkeypatch.setattr(wepp_runner_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        wepp_runner_module.StatusMessenger,
        "publish",
        lambda channel, message: metric_events.append((channel, message)),
    )

    success, returned_id, elapsed = wepp_runner_module.run_hillslope(
        wepp_id=wepp_id,
        runs_dir=str(tmp_path),
        timeout=0.01,
        timeout_retries=3,
        status_channel="unit:test",
    )

    assert success is True
    assert returned_id == wepp_id
    assert elapsed >= 0.0
    assert len(popen_calls) == 2
    assert attempts == []
    assert sleep_calls == [0.75]
    assert metric_events == [
        (
            "unit:test",
            "metric:run_hillslope wepp_id=101 timeout_attempts=1 success_on_retry=1 final_state=success",
        )
    ]

    err_text = (tmp_path / f"p{wepp_id}.err").read_text(encoding="ascii")
    assert "retrying after timeout" in err_text
    assert "flake_detected" in err_text
    assert "Year 34 of 46" in err_text
    assert "metric:run_hillslope wepp_id=101 timeout_attempts=1 success_on_retry=1 final_state=success" in err_text


def test_run_hillslope_exhausts_timeouts_with_context(monkeypatch, tmp_path):
    wepp_id = 202
    _write_hillslope_inputs(tmp_path, wepp_id)

    attempts = [{"timeout": True, "stdout": "Year 34 of 46\n"} for _ in range(4)]
    popen_calls = []
    sleep_calls = []
    metric_events = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeProcess(attempts.pop(0))

    monkeypatch.setattr(wepp_runner_module.random, "uniform", lambda _a, _b: 0.2)
    monkeypatch.setattr(wepp_runner_module, "sleep", lambda delay: sleep_calls.append(delay))
    monkeypatch.setattr(wepp_runner_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        wepp_runner_module.StatusMessenger,
        "publish",
        lambda channel, message: metric_events.append((channel, message)),
    )

    with pytest.raises(TimeoutError) as exc:
        wepp_runner_module.run_hillslope(
            wepp_id=wepp_id,
            runs_dir=str(tmp_path),
            timeout=0.01,
            timeout_retries=3,
            status_channel="unit:test",
        )

    assert len(popen_calls) == 4
    assert attempts == []
    assert sleep_calls == [0.7, 1.2, 2.2]
    assert metric_events == [
        (
            "unit:test",
            "metric:run_hillslope wepp_id=202 timeout_attempts=4 success_on_retry=0 final_state=timeout",
        )
    ]

    err_path = tmp_path / f"p{wepp_id}.err"
    run_path = tmp_path / f"p{wepp_id}.run"
    msg = str(exc.value)
    assert f"wepp_id={wepp_id}" in msg
    assert f"runs_dir={tmp_path}" in msg
    assert f"run_file={run_path}" in msg
    assert f"err_file={err_path}" in msg
    assert "attempts=4" in msg

    err_text = err_path.read_text(encoding="ascii")
    assert "timeout attempt=4/4" in err_text
    assert "retrying after timeout" in err_text
    assert "metric:run_hillslope wepp_id=202 timeout_attempts=4 success_on_retry=0 final_state=timeout" in err_text


@pytest.mark.parametrize("raw_value", ["nan", "inf", "-inf"])
def test_env_float_or_default_rejects_non_finite(monkeypatch, raw_value):
    monkeypatch.setenv("UNIT_WAIT", raw_value)
    result = wepp_runner_module._env_float_or_default("UNIT_WAIT", 30.0, min_value=0.0)
    assert result == 30.0


def test_run_hillslope_waits_for_missing_input_then_succeeds(monkeypatch, tmp_path):
    wepp_id = 303
    _write_hillslope_inputs(tmp_path, wepp_id)
    sol_path = tmp_path / f"p{wepp_id}.sol"
    sol_path.unlink()

    attempts = [{"stdout": "WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY\n"}]
    popen_calls = []
    sleep_calls = []

    def _fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        assert attempts, "Unexpected extra subprocess launch"
        return _FakeProcess(attempts.pop(0))

    def _fake_sleep(delay):
        sleep_calls.append(delay)
        if not sol_path.exists():
            sol_path.write_text("stub\n", encoding="ascii")

    monkeypatch.setattr(wepp_runner_module, "sleep", _fake_sleep)
    monkeypatch.setattr(wepp_runner_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setenv("WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_S", "1")
    monkeypatch.setenv("WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_POLL_S", "0.01")

    success, returned_id, elapsed = wepp_runner_module.run_hillslope(
        wepp_id=wepp_id,
        runs_dir=str(tmp_path),
        timeout=0.01,
        timeout_retries=0,
    )

    assert success is True
    assert returned_id == wepp_id
    assert elapsed >= 0.0
    assert len(popen_calls) == 1
    assert sleep_calls == [0.01]


def test_run_hillslope_missing_input_uses_defaults_when_env_non_finite(monkeypatch, tmp_path):
    wepp_id = 304
    _write_hillslope_inputs(tmp_path, wepp_id)
    (tmp_path / f"p{wepp_id}.sol").unlink()

    monkeypatch.setenv("WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_S", "nan")
    monkeypatch.setenv("WEPP_RUNNER_HILLSLOPE_INPUT_WAIT_POLL_S", "nan")
    monkeypatch.setattr(wepp_runner_module, "_HILLSLOPE_INPUT_WAIT_S_DEFAULT", 0.01)
    monkeypatch.setattr(wepp_runner_module, "_HILLSLOPE_INPUT_WAIT_POLL_S_DEFAULT", 0.001)

    with pytest.raises(FileNotFoundError) as exc:
        wepp_runner_module.run_hillslope(
            wepp_id=wepp_id,
            runs_dir=str(tmp_path),
            timeout=0.01,
            timeout_retries=0,
        )

    msg = str(exc.value)
    assert "Required WEPP hillslope input file was not available within 0.01s" in msg
    assert f"p{wepp_id}.sol" in msg
