"""Cancellation guards; real process and Redis scenarios run in clean interpreters."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis

from wepppy.rq import directory_locks

# The global unit fixture removes *_FILE settings. Preserve only the configured
# Redis credential path for configured/opted-in fresh-interpreter integration.
_REAL_REDIS_PASSWORD_FILE = os.environ.get("REDIS_PASSWORD_FILE")


@pytest.mark.parametrize("problem,horse_pid", [("unknown descendants", 0), (None, 123)])
@pytest.mark.unit
def test_uncertain_termination_never_releases_locks(monkeypatch, problem, horse_pid):
    worker = SimpleNamespace(
        _directory_lock_execution_id="a" * 32,
        _directory_lock_containment_error=problem,
        horse_pid=horse_pid,
    )
    monkeypatch.setattr(directory_locks, "release_execution_locks",
                        lambda *_: pytest.fail("uncertain termination released locks"))
    with pytest.raises(RuntimeError):
        directory_locks.cleanup_stopped_execution(worker, SimpleNamespace())


@pytest.mark.unit
def test_containment_refuses_preexisting_children(monkeypatch):
    monkeypatch.setattr(directory_locks, "_child_pids", lambda: {123})
    with pytest.raises(RuntimeError, match="pre-existing"):
        directory_locks.prepare_containment()


@pytest.mark.unit
def test_permission_denied_retains_locks(monkeypatch):
    worker = SimpleNamespace(
        _directory_lock_execution_id="a" * 32,
        _directory_lock_containment_error=None, horse_pid=0,
        _directory_lock_protected_children={},
        heartbeat=lambda: None, job_monitoring_interval=1,
    )
    monkeypatch.setattr(directory_locks, "record_cleanup", lambda *_a, **_k: None)
    def denied(*_args):
        raise PermissionError("injected denied process inspection")
    monkeypatch.setattr(directory_locks, "terminate_adopted_writers", denied)
    monkeypatch.setattr(directory_locks, "release_execution_locks",
                        lambda *_: pytest.fail("denied termination released locks"))
    with pytest.raises(PermissionError):
        directory_locks.cleanup_stopped_execution(worker, SimpleNamespace())


@pytest.mark.unit
def test_missing_live_task_inspection_retains_locks(monkeypatch, tmp_path):
    (tmp_path / "123").mkdir()  # Live task exists but its children interface does not.
    monkeypatch.setattr(directory_locks, "Path", lambda _path: tmp_path)
    worker = SimpleNamespace(
        _directory_lock_execution_id="a" * 32,
        _directory_lock_containment_error=None, horse_pid=0,
        _directory_lock_protected_children={},
        heartbeat=lambda: None, job_monitoring_interval=1,
    )
    monkeypatch.setattr(directory_locks, "record_cleanup", lambda *_a, **_k: None)
    monkeypatch.setattr(directory_locks, "release_execution_locks",
                        lambda *_: pytest.fail("missing kernel inspection released locks"))
    with pytest.raises(RuntimeError, match="inspection unavailable"):
        directory_locks.cleanup_stopped_execution(worker, SimpleNamespace())


@pytest.mark.unit
@pytest.mark.parametrize("error", [redis.WatchError, redis.ConnectionError])
def test_diagnostic_failure_does_not_skip_termination(monkeypatch, caplog, error):
    execution = "a" * 32
    class Pipeline:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def watch(self, *_args): raise error("injected diagnostic failure")
    job = SimpleNamespace(id="job", key="rq:job", connection=SimpleNamespace(pipeline=Pipeline))
    worker = SimpleNamespace(
        _directory_lock_execution_id=execution,
        _directory_lock_containment_error=None, horse_pid=0,
        _directory_lock_protected_children={},
        heartbeat=lambda: None, job_monitoring_interval=1,
    )
    actions = []
    monkeypatch.setattr(directory_locks, "terminate_adopted_writers", lambda *_: actions.append("terminate"))
    monkeypatch.setattr(directory_locks, "release_execution_locks", lambda *_: actions.append("release") or [])
    directory_locks.cleanup_stopped_execution(worker, job)
    assert actions == ["terminate", "release"]
    assert "Could not record directory cleanup" in caplog.text


@pytest.mark.unit
def test_scheduler_death_retains_locks(monkeypatch):
    worker = SimpleNamespace(
        _directory_lock_execution_id="a" * 32,
        _directory_lock_containment_error=None, horse_pid=0,
        _directory_lock_protected_children={123: 9},
        heartbeat=lambda: None, job_monitoring_interval=1,
    )
    monkeypatch.setattr(directory_locks, "record_cleanup", lambda *_a, **_k: None)
    monkeypatch.setattr(directory_locks.select, "select", lambda *_: ([9], [], []))
    monkeypatch.setattr(directory_locks, "release_execution_locks",
                        lambda *_: pytest.fail("uncertain scheduler ownership released locks"))
    with pytest.raises(RuntimeError, match="scheduler exited"):
        directory_locks.cleanup_stopped_execution(worker, SimpleNamespace())


@pytest.mark.unit
def test_lock_redis_failure_records_pending_not_complete(monkeypatch):
    from wepppy.rq.rq_worker import WepppyRqWorker
    worker = object.__new__(WepppyRqWorker)
    worker._directory_lock_execution_id = "a" * 32
    worker._directory_lock_cancel_requested = True
    worker._directory_lock_containment_error = None
    worker._directory_lock_protected_children = {}
    worker._horse_pid = 0
    worker.job_monitoring_interval = 1
    states = []
    monkeypatch.setattr(directory_locks, "record_cleanup", lambda _j, _e, state, **_k: states.append(state))
    monkeypatch.setattr(directory_locks, "terminate_adopted_writers", lambda *_: None)
    def unavailable(*_args):
        raise RuntimeError("could not release directory lock climate: injected Redis failure")
    monkeypatch.setattr(directory_locks, "release_execution_locks", unavailable)
    worker._cleanup_canceled_directory_locks(SimpleNamespace(id="job"))
    assert states == ["terminating_writers", "pending"]


@pytest.mark.integration
@pytest.mark.slow
def test_real_detached_writer_containment():
    result = subprocess.run(
        [sys.executable, "-m", "tests.rq.cancel_directory_lock_probe", "processes"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("scenario", ["ownership", "cancel", "queued", "cancel_watch", "cancel_redis", "crash_then_cancel", "early_failure"])
def test_real_redis_cancellation(scenario):
    enabled = os.environ.get("RQ_CANCEL_TEST_REAL_REDIS")
    configured = _REAL_REDIS_PASSWORD_FILE and Path(_REAL_REDIS_PASSWORD_FILE).is_file()
    if enabled == "0" or (enabled != "1" and not configured):
        pytest.skip("Configure development Redis or set RQ_CANCEL_TEST_REAL_REDIS=1 for real cancellation tests")
    env = os.environ.copy()
    if _REAL_REDIS_PASSWORD_FILE:
        env["REDIS_PASSWORD_FILE"] = _REAL_REDIS_PASSWORD_FILE
    result = subprocess.run(
        [sys.executable, "-m", "tests.rq.cancel_directory_lock_probe", scenario],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
