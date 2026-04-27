import builtins
import errno
import hashlib
import os

import pytest

from wepp_runner import wepp_runner as wepp_runner_module

pytestmark = pytest.mark.unit


class _CommunicateProcess:
    def __init__(self, stdout, *, pid=4242, returncode=0):
        self.stdout = stdout
        self.pid = pid
        self.returncode = returncode

    def communicate(self, timeout=None):
        return self.stdout, ""

    def kill(self):
        self.returncode = -9


class _FakeStdout:
    def __init__(self, lines):
        self._lines = list(lines)

    @property
    def has_lines(self):
        return bool(self._lines)

    def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return ""


class _StreamingProcess:
    def __init__(self, lines, *, pid=4243, returncode=0):
        self.stdout = _FakeStdout(lines)
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        if self.stdout.has_lines:
            return None
        return self.returncode

    def wait(self):
        return self.returncode


class _MemoryLog:
    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        return None


@pytest.fixture(autouse=True)
def _stable_runner_env(monkeypatch):
    monkeypatch.setattr(wepp_runner_module, "_assert_binary_runtime_provenance", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(wepp_runner_module, "_BINARY_IDENTITY_CACHE", {})
    monkeypatch.setenv("WEPP_RUNNER_DSTATE_WATCHDOG_ENABLED", "0")


def test_run_watershed_logs_startup_context_and_binary_identity(monkeypatch, tmp_path):
    run_path = tmp_path / "pw0.run"
    err_path = tmp_path / "pw0.err"
    binary_path = tmp_path / "fake_wepp_watershed"
    binary_bytes = b"fake watershed binary\n"
    expected_sha = hashlib.sha256(binary_bytes).hexdigest()
    run_path.write_text("watershed run\n", encoding="ascii")
    binary_path.write_bytes(binary_bytes)
    published = []

    def _fake_popen(cmd, **kwargs):
        assert kwargs["cwd"] == str(tmp_path)
        assert kwargs["stdin"].name == str(run_path)
        return _StreamingProcess(
            [
                "Year 1 of 1\n",
                "WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY\n",
            ]
        )

    monkeypatch.setattr(wepp_runner_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        wepp_runner_module,
        "_resolve_wepp_cmd",
        lambda _wepp_bin, *, prefer_hill: [str(binary_path)],
    )
    monkeypatch.setattr(
        wepp_runner_module.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    success, elapsed = wepp_runner_module.run_watershed(str(tmp_path), status_channel="unit:watershed")

    assert success is True
    assert elapsed >= 0.0
    assert published == [
        ("unit:watershed", "Year 1 of 1"),
        ("unit:watershed", "WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY"),
    ]

    err_text = err_path.read_text(encoding="ascii")
    assert f"[run_watershed] runs_dir={tmp_path}" in err_text
    assert f"run_file={run_path}" in err_text
    assert f"err_file={err_path}" in err_text
    assert 'cmd="' in err_text
    assert "attempt=1/1" in err_text
    assert "[run_watershed] binary_identity" in err_text
    assert "binary_path=" in err_text
    assert f"binary_sha256={expected_sha}" in err_text
    assert "binary_identity_status=ok" in err_text


def test_run_hillslope_logs_binary_identity_fields(monkeypatch, tmp_path):
    wepp_id = 707
    run_path = tmp_path / f"p{wepp_id}.run"
    err_path = tmp_path / f"p{wepp_id}.err"
    binary_path = tmp_path / "fake_wepp"
    binary_bytes = b"fake wepp binary\n"
    expected_sha = hashlib.sha256(binary_bytes).hexdigest()
    run_path.write_text("hillslope run\n", encoding="ascii")
    binary_path.write_bytes(binary_bytes)

    monkeypatch.setattr(
        wepp_runner_module,
        "_resolve_wepp_cmd",
        lambda _wepp_bin, *, prefer_hill: [str(binary_path)],
    )
    monkeypatch.setattr(
        wepp_runner_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _CommunicateProcess(
            "WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY\n"
        ),
    )

    success, returned_id, elapsed = wepp_runner_module.run_hillslope(
        wepp_id=wepp_id,
        runs_dir=str(tmp_path),
        no_file_checks=True,
        timeout_retries=0,
    )

    assert success is True
    assert returned_id == wepp_id
    assert elapsed >= 0.0

    err_text = err_path.read_text(encoding="ascii")
    assert "[run_hillslope] binary_identity" in err_text
    assert f'binary_path="{binary_path.resolve()}"' in err_text
    assert f"binary_sha256={expected_sha}" in err_text
    assert f"binary_size_bytes={len(binary_bytes)}" in err_text
    assert "binary_identity_status=ok" in err_text
    assert 'binary_identity_error=""' in err_text


def test_binary_identity_records_safe_fallback_when_hash_unavailable(tmp_path):
    missing_binary = tmp_path / "missing_wepp"

    identity = wepp_runner_module._collect_binary_identity(str(missing_binary))

    assert identity["binary_path"] == str(missing_binary)
    assert identity["binary_sha256"] == "<unavailable>"
    assert identity["binary_size_bytes"] == "<unavailable>"
    assert identity["binary_mtime_ns"] == "<unavailable>"
    assert identity["binary_identity_status"] == "unavailable"
    assert "FileNotFoundError" in identity["binary_identity_error"]


def test_binary_identity_refreshes_after_in_place_binary_change(tmp_path):
    binary_path = tmp_path / "wepp_bin"
    first_bytes = b"first binary image\n"
    second_bytes = b"second binary image\n"
    binary_path.write_bytes(first_bytes)

    first_identity = wepp_runner_module._collect_binary_identity(str(binary_path))

    binary_path.write_bytes(second_bytes)
    stat_result = binary_path.stat()
    os.utime(
        binary_path,
        ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns + 1_000_000),
    )
    second_identity = wepp_runner_module._collect_binary_identity(str(binary_path))

    assert first_identity["binary_sha256"] == hashlib.sha256(first_bytes).hexdigest()
    assert second_identity["binary_sha256"] == hashlib.sha256(second_bytes).hexdigest()
    assert first_identity["binary_sha256"] != second_identity["binary_sha256"]


def test_dstate_watchdog_emits_after_threshold_and_stays_bounded(tmp_path):
    states = iter(["D", "D", "D", "D"])
    log = _MemoryLog()
    watchdog = wepp_runner_module._DStateWatchdog(
        runner_name="run_hillslope",
        pid=12345,
        log=log,
        runs_dir=str(tmp_path),
        run_file=str(tmp_path / "p1.run"),
        err_file=str(tmp_path / "p1.err"),
        cmd_text="/tmp/fake_wepp",
        interval_s=1.0,
        threshold_s=5.0,
        max_events=1,
        state_reader=lambda _pid: next(states),
    )

    assert watchdog.poll_once(now=0.0) is False
    assert watchdog.poll_once(now=4.9) is False
    assert watchdog.poll_once(now=5.0) is True
    assert watchdog.poll_once(now=10.0) is False

    assert len(log.lines) == 1
    line = log.lines[0]
    assert "[run_hillslope] dstate_watchdog" in line
    assert "pid=12345" in line
    assert "duration=5.00s" in line
    assert "event=1/1" in line


def test_dstate_watchdog_does_not_emit_before_threshold_or_after_reset(tmp_path):
    states = iter(["D", "R", "D"])
    log = _MemoryLog()
    watchdog = wepp_runner_module._DStateWatchdog(
        runner_name="run_watershed",
        pid=12346,
        log=log,
        runs_dir=str(tmp_path),
        run_file=str(tmp_path / "pw0.run"),
        err_file=str(tmp_path / "pw0.err"),
        cmd_text="/tmp/fake_wepp",
        interval_s=1.0,
        threshold_s=5.0,
        max_events=1,
        state_reader=lambda _pid: next(states),
    )

    assert watchdog.poll_once(now=0.0) is False
    assert watchdog.poll_once(now=10.0) is False
    assert watchdog.poll_once(now=11.0) is False
    assert log.lines == []


def test_start_dstate_watchdog_noops_when_disabled_or_pid_missing(monkeypatch, tmp_path):
    log = _MemoryLog()
    run_file = str(tmp_path / "pw0.run")
    err_file = str(tmp_path / "pw0.err")

    process_with_pid = type("ProcWithPid", (), {"pid": 1234})()
    monkeypatch.setenv("WEPP_RUNNER_DSTATE_WATCHDOG_ENABLED", "0")
    disabled_watchdog = wepp_runner_module._start_dstate_watchdog(
        "run_watershed",
        process_with_pid,
        log,
        runs_dir=str(tmp_path),
        run_file=run_file,
        err_file=err_file,
        cmd_text="/tmp/fake_wepp",
    )
    assert isinstance(disabled_watchdog, wepp_runner_module._DisabledDStateWatchdog)

    process_without_pid = type("ProcNoPid", (), {})()
    monkeypatch.setenv("WEPP_RUNNER_DSTATE_WATCHDOG_ENABLED", "1")
    missing_pid_watchdog = wepp_runner_module._start_dstate_watchdog(
        "run_watershed",
        process_without_pid,
        log,
        runs_dir=str(tmp_path),
        run_file=run_file,
        err_file=err_file,
        cmd_text="/tmp/fake_wepp",
    )
    assert isinstance(missing_pid_watchdog, wepp_runner_module._DisabledDStateWatchdog)


def test_run_watershed_logs_stale_handle_close_diagnostics(monkeypatch, tmp_path, capsys):
    run_path = tmp_path / "pw0.run"
    err_path = tmp_path / "pw0.err"
    run_path.write_text("watershed run\n", encoding="ascii")
    real_open = builtins.open

    class _CloseFailLog:
        closed = False

        def __init__(self):
            self.writes = []

        def write(self, text):
            self.writes.append(text)

        def flush(self):
            return None

        def close(self):
            raise OSError(errno.ESTALE, "Stale file handle")

    fake_log = _CloseFailLog()

    def _fake_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if os.fspath(path) == os.fspath(err_path) and "w" in mode:
            return fake_log
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(wepp_runner_module, "open", _fake_open, raising=False)
    monkeypatch.setattr(
        wepp_runner_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _StreamingProcess(
            ["WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY\n"]
        ),
    )

    with pytest.raises(OSError) as exc:
        wepp_runner_module.run_watershed(str(tmp_path))

    assert exc.value.errno == errno.ESTALE
    captured = capsys.readouterr()
    diagnostic = captured.err
    assert "[run_watershed] close_path_failure" in diagnostic
    assert "stream=err_file" in diagnostic
    assert "classification=stale_file_handle" in diagnostic
    assert f'path="{err_path}"' in diagnostic
    assert "errno=116" in diagnostic
    assert any("close_path_failure" in line for line in fake_log.writes)


def test_run_watershed_preserves_primary_exception_when_close_also_fails(
    monkeypatch, tmp_path, capsys
):
    run_path = tmp_path / "pw0.run"
    err_path = tmp_path / "pw0.err"
    run_path.write_text("watershed run\n", encoding="ascii")
    real_open = builtins.open

    class _CloseFailLog:
        closed = False

        def write(self, _text):
            return None

        def flush(self):
            return None

        def close(self):
            raise OSError(errno.ESTALE, "Stale file handle")

    def _fake_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if os.fspath(path) == os.fspath(err_path) and "w" in mode:
            return _CloseFailLog()
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(wepp_runner_module, "open", _fake_open, raising=False)
    monkeypatch.setattr(
        wepp_runner_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("subprocess boom")),
    )

    with pytest.raises(RuntimeError, match="subprocess boom"):
        wepp_runner_module.run_watershed(str(tmp_path))

    diagnostic = capsys.readouterr().err
    assert "[run_watershed] close_path_failure" in diagnostic
    assert "classification=stale_file_handle" in diagnostic
