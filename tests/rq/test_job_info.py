from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

import wepppy.rq.job_info as job_info
from wepppy.rq.job_info import recursive_get_job_details


pytestmark = pytest.mark.unit


@dataclass
class _FakeJob:
    id: str = "job-1"
    meta: dict[str, Any] = field(default_factory=dict)
    args: tuple[Any, ...] = ()
    status: str = "failed"
    result: Any = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    description: str = "fake job"
    exc_info: str | None = None

    def get_status(self) -> str:
        return self.status


def test_recursive_job_details_prefers_exc_string_meta() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1", "exc_string": "traceback from meta"}, exc_info="traceback from rq")

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["status"] == "failed"
    assert payload["exc_info"] == "traceback from meta"


def test_recursive_job_details_falls_back_to_rq_exc_info() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1"}, exc_info="traceback from rq")

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["exc_info"] == "traceback from rq"


def test_recursive_job_details_exc_info_none_when_missing() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={"runid": "run-1"})

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["exc_info"] is None


def test_recursive_job_details_falls_back_to_runid_from_first_arg() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(meta={}, args=("run-from-arg", "other"))

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["runid"] == "run-from-arg"


def test_get_job_status_progress_updated_at_uses_stable_unknown_when_no_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_job = _FakeJob(id="root", meta={"runid": "run-1"}, status="queued")

    class _FakeRedisContext:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    monkeypatch.setattr(job_info.redis, "Redis", _FakeRedisContext)
    monkeypatch.setattr(job_info.Job, "fetch", lambda job_id, connection: root_job)
    monkeypatch.setattr(
        job_info,
        "recursive_get_job_details",
        lambda job, redis_conn, now: {
            "job_id": "root",
            "runid": "run-1",
            "status": "queued",
            "started_at": None,
            "ended_at": None,
            "children": {
                "0": [{"job_id": "child-1", "status": "queued", "started_at": None, "ended_at": None, "children": {}}]
            },
        },
    )

    payload = job_info.get_wepppy_rq_job_status("root")

    assert payload["status"] == "queued"
    assert payload["progress"] == {
        "completed": 0,
        "total": 2,
        "unit": "jobs",
        "percent": 0.0,
        "updated_at": job_info.UNKNOWN_PROGRESS_UPDATED_AT,
    }


def test_get_job_status_progress_updated_at_uses_latest_seen_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_job = _FakeJob(id="root", meta={"runid": "run-1"}, status="started")

    class _FakeRedisContext:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    monkeypatch.setattr(job_info.redis, "Redis", _FakeRedisContext)
    monkeypatch.setattr(job_info.Job, "fetch", lambda job_id, connection: root_job)
    monkeypatch.setattr(
        job_info,
        "recursive_get_job_details",
        lambda job, redis_conn, now: {
            "job_id": "root",
            "runid": "run-1",
            "status": "started",
            "started_at": "2026-04-10T10:00:00Z",
            "ended_at": None,
            "children": {
                "0": [
                    {
                        "job_id": "child-1",
                        "status": "finished",
                        "started_at": "2026-04-10T10:01:00Z",
                        "ended_at": "2026-04-10T10:05:00Z",
                        "children": {},
                    }
                ],
                "1": [
                    {
                        "job_id": "child-2",
                        "status": "started",
                        "started_at": "2026-04-10T10:06:00Z",
                        "ended_at": None,
                        "children": {},
                    }
                ],
            },
        },
    )

    payload = job_info.get_wepppy_rq_job_status("root")

    assert payload["status"] == "started"
    assert payload["progress"]["completed"] == 1
    assert payload["progress"]["total"] == 3
    assert payload["progress"]["percent"] == pytest.approx(33.33, abs=0.01)
    assert payload["progress"]["updated_at"] == "2026-04-10T10:06:00Z"
