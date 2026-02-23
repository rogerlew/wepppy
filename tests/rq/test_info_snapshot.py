from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.rq import info_snapshot


pytestmark = pytest.mark.unit


def test_discover_queue_names_returns_sorted_unique(monkeypatch: pytest.MonkeyPatch) -> None:
    queue_defs = [
        SimpleNamespace(name="batch"),
        SimpleNamespace(name="default"),
        SimpleNamespace(name="batch"),
        SimpleNamespace(name=" high "),
    ]
    monkeypatch.setattr(info_snapshot.Queue, "all", lambda connection: queue_defs)

    names = info_snapshot._discover_queue_names(redis_conn=object())

    assert names == ["batch", "default", "high"]


def test_queue_names_for_iteration_prefers_requested() -> None:
    names = info_snapshot._queue_names_for_iteration(
        redis_conn=object(),
        requested_queue_names=["default", "batch"],
    )
    assert names == ["default", "batch"]


def test_queue_names_for_iteration_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(info_snapshot, "_discover_queue_names", lambda redis_conn: [])

    names = info_snapshot._queue_names_for_iteration(
        redis_conn=object(),
        requested_queue_names=[],
    )
    assert names == ["default", "batch"]


@pytest.mark.parametrize(
    ("job_id", "state", "fallback_ids", "expected"),
    [
        ("job-1", "idle", [], "busy"),
        ("", "busy", [], "busy"),
        ("", "idle", ["job-2"], "busy"),
        ("", "idle", [], "idle"),
    ],
)
def test_worker_status(
    job_id: str,
    state: str,
    fallback_ids: list[str],
    expected: str,
) -> None:
    class DummyWorker:
        def __init__(self, current_job_id: str, current_state: str) -> None:
            self._current_job_id = current_job_id
            self._current_state = current_state

        def get_current_job_id(self):
            return self._current_job_id

        def get_state(self):
            return self._current_state

    worker = DummyWorker(job_id, state)
    assert info_snapshot._worker_status(worker, fallback_ids) == expected
