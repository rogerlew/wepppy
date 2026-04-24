from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from wepppy.tools import scheduler


pytestmark = pytest.mark.unit


class _RecordingQueue:
    def __init__(self, name: str, connection: object) -> None:
        self.name = name
        self.connection = connection
        self.enqueued: list[str] = []

    def enqueue(self, func, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.enqueued.append(getattr(func, "__name__", repr(func)))


def test_enqueue_task_skips_when_callable_resolution_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = scheduler.TaskSpec(
        name="broken",
        func_path="broken.module.fn",
        interval_seconds=60,
        queue="default",
        args=[],
        kwargs={},
        enabled=True,
        initial_delay_seconds=0,
        jitter_seconds=0,
        job_timeout=None,
        result_ttl=None,
        job_id=None,
        description=None,
    )
    state = scheduler.TaskState(spec=spec, func=None, next_run=0.0)
    queue = _RecordingQueue("default", object())

    def _raise_import_error(_path: str):  # type: ignore[no-untyped-def]
        raise ImportError("boom")

    monkeypatch.setattr(scheduler, "_resolve_callable", _raise_import_error)

    assert scheduler._enqueue_task(queue, state) is False
    assert queue.enqueued == []
    assert state.func is None


def test_run_scheduler_continues_when_one_task_cannot_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "tasks": [
            {"name": "bad", "func": "bad.module.fn", "interval_seconds": 60, "queue": "default"},
            {"name": "good", "func": "good.module.fn", "interval_seconds": 60, "queue": "default"},
        ]
    }
    enqueued: list[str] = []

    def fake_resolve(path: str):
        if path == "bad.module.fn":
            raise ImportError("missing optional dependency")

        def _good() -> None:
            return None

        _good.__name__ = "good_task"
        return _good

    class _QueueFactory(_RecordingQueue):
        def enqueue(self, func, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            super().enqueue(func, *args, **kwargs)
            enqueued.append(getattr(func, "__name__", repr(func)))

    monotonic_values = iter([100.0, 100.0])
    monkeypatch.setattr(scheduler, "_load_config", lambda _path: config)
    monkeypatch.setattr(scheduler, "_resolve_callable", fake_resolve)
    monkeypatch.setattr(scheduler, "Queue", _QueueFactory)
    monkeypatch.setattr(scheduler.redis, "Redis", lambda **_kwargs: object())
    monkeypatch.setattr(scheduler, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(scheduler.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(scheduler.time, "time", lambda: 0.0)
    monkeypatch.setattr(scheduler, "_monitor_run_locations_freshness", lambda *_args, **_kwargs: None)

    scheduler.run_scheduler("ignored.yml", sleep_seconds=1, dry_run=False, run_once=True)

    assert enqueued == ["good_task"]


def test_run_scheduler_uses_short_retry_after_enqueue_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "tasks": [
            {"name": "bad", "func": "bad.module.fn", "interval_seconds": 86400, "queue": "default"},
        ]
    }
    spec = scheduler.TaskSpec(
        name="bad",
        func_path="bad.module.fn",
        interval_seconds=86400,
        queue="default",
        args=[],
        kwargs={},
        enabled=True,
        initial_delay_seconds=0,
        jitter_seconds=0,
        job_timeout=None,
        result_ttl=None,
        job_id=None,
        description=None,
    )
    state = scheduler.TaskState(spec=spec, func=None, next_run=100.0)
    monotonic_values = iter([100.0, 100.0])

    monkeypatch.setattr(scheduler, "_load_config", lambda _path: config)
    monkeypatch.setattr(scheduler, "_build_states", lambda _specs: [state])
    def _raise_import_error(_path: str):  # type: ignore[no-untyped-def]
        raise ImportError("boom")

    monkeypatch.setattr(scheduler, "_resolve_callable", _raise_import_error)
    monkeypatch.setattr(scheduler, "Queue", _RecordingQueue)
    monkeypatch.setattr(scheduler.redis, "Redis", lambda **_kwargs: object())
    monkeypatch.setattr(scheduler, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(scheduler.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(scheduler.time, "time", lambda: 0.0)
    monkeypatch.setattr(scheduler, "_monitor_run_locations_freshness", lambda *_args, **_kwargs: None)

    scheduler.run_scheduler("ignored.yml", sleep_seconds=30, dry_run=False, run_once=True)

    assert state.next_run == pytest.approx(130.0)


def test_monitor_run_locations_freshness_logs_stale_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_locations = tmp_path / "runid-locations.json"
    run_locations.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(scheduler.time, "time", lambda: 500.0)
    run_locations_mtime = 100.0
    os.utime(run_locations, (run_locations_mtime, run_locations_mtime))

    caplog.set_level(logging.WARNING)
    scheduler._monitor_run_locations_freshness(run_locations, stale_after_seconds=120)

    assert "run-locations stale" in caplog.text


def test_run_scheduler_passes_task_kwargs_to_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "tasks": [
            {
                "name": "usersum_docs_index",
                "func": "wepppy.rq.project_rq.index_usersum_docs_rq",
                "interval_seconds": 60,
                "queue": "batch",
                "kwargs": {
                    "write_index": False,
                    "require_vendor_files": False,
                    "sync_postgres": True,
                },
            }
        ]
    }
    enqueue_calls: list[dict[str, object]] = []

    def fake_resolve(_path: str):
        def _task() -> None:
            return None

        _task.__name__ = "usersum_docs_index_task"
        return _task

    class _QueueFactory(_RecordingQueue):
        def enqueue(self, func, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            enqueue_calls.append(
                {
                    "func_name": getattr(func, "__name__", repr(func)),
                    "args": args,
                    "kwargs": kwargs,
                }
            )

    monotonic_values = iter([100.0, 100.0])
    monkeypatch.setattr(scheduler, "_load_config", lambda _path: config)
    monkeypatch.setattr(scheduler, "_resolve_callable", fake_resolve)
    monkeypatch.setattr(scheduler, "Queue", _QueueFactory)
    monkeypatch.setattr(scheduler.redis, "Redis", lambda **_kwargs: object())
    monkeypatch.setattr(scheduler, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(scheduler.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(scheduler.time, "time", lambda: 0.0)
    monkeypatch.setattr(scheduler, "_monitor_run_locations_freshness", lambda *_args, **_kwargs: None)

    scheduler.run_scheduler("ignored.yml", sleep_seconds=1, dry_run=False, run_once=True)

    assert len(enqueue_calls) == 1
    enqueue_kwargs = enqueue_calls[0]["kwargs"]
    assert isinstance(enqueue_kwargs, dict)
    assert enqueue_kwargs["write_index"] is False
    assert enqueue_kwargs["require_vendor_files"] is False
    assert enqueue_kwargs["sync_postgres"] is True
