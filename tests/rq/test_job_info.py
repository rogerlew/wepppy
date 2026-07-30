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


def test_recursive_job_details_redacts_actor_and_private_wbt_snapshot() -> None:
    now = datetime.now(timezone.utc)
    job = _FakeJob(
        meta={
            "auth_actor": {
                "token_class": "session",
                "session_id": "private-session",
                "user_id": 42,
            },
            "wbt_boundary_policy_snapshot": {
                "schema_version": 1,
                "runid": "run-1",
                "actor_token_class": "session",
                "actor_user_id": 42,
                "config_policy": "warn",
                "effective_policy": "error",
                "source": "user_preference",
            },
        }
    )

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["auth_actor"] is None
    assert "wbt_boundary_policy_snapshot" not in payload
    assert "private-session" not in str(payload)


def test_recursive_job_details_suppresses_traceback_for_controlled_error() -> None:
    now = datetime.now(timezone.utc)
    error = {
        "code": "watershed_boundary_touches_dem_edge",
        "message": "boundary",
        "details": {"edge_hillslope_ids": [1, 2]},
    }
    job = _FakeJob(
        meta={"runid": "run-1", "error": error, "error_id": "error-1"},
        exc_info="raw traceback",
    )

    payload = recursive_get_job_details(job, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["exc_info"] is None
    assert payload["error"] == error
    assert payload["error_id"] == "error-1"


def test_recursive_job_details_aggregates_controlled_child_failure(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    root = _FakeJob(id="root", status="finished", meta={"jobs:0,func:build": "child"})
    child = _FakeJob(
        id="child",
        status="failed",
        meta={
            "error": {
                "code": "watershed_boundary_touches_dem_edge",
                "message": "boundary",
                "details": {"edge_hillslope_ids": [2]},
            },
            "error_id": "error-2",
        },
        exc_info="raw traceback",
    )
    monkeypatch.setattr(job_info.Job, "fetch", lambda job_id, connection: child)

    payload = recursive_get_job_details(root, redis_conn=object(), now=now)  # type: ignore[arg-type]

    assert payload["status"] == "failed"
    assert payload["exc_info"] is None
    assert payload["error"]["code"] == "watershed_boundary_touches_dem_edge"
    assert payload["error_id"] == "error-2"


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


@pytest.mark.parametrize(
    ("second_child_status", "expected_status"),
    [("started", "started"), ("finished", "failed")],
)
def test_get_job_status_keeps_failed_allow_failure_tree_nonterminal_until_children_finish(
    monkeypatch: pytest.MonkeyPatch,
    second_child_status: str,
    expected_status: str,
) -> None:
    root_job = _FakeJob(id="root", meta={"runid": "run-1"}, status="finished")

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
            "status": "finished",
            "started_at": "2026-07-15T20:00:00Z",
            "ended_at": "2026-07-15T20:00:01Z",
            "children": {
                "0": [
                    {
                        "job_id": "child-1",
                        "status": "failed",
                        "started_at": "2026-07-15T20:00:02Z",
                        "ended_at": "2026-07-15T20:00:03Z",
                        "children": {},
                    }
                ],
                "1": [
                    {
                        "job_id": "child-2",
                        "status": second_child_status,
                        "started_at": "2026-07-15T20:00:04Z",
                        "ended_at": (
                            "2026-07-15T20:00:05Z"
                            if second_child_status == "finished"
                            else None
                        ),
                        "children": {},
                    }
                ],
            },
        },
    )

    payload = job_info.get_wepppy_rq_job_status("root")

    assert payload["status"] == expected_status
    assert payload["ended_at"] == (
        "2026-07-15T20:00:05Z" if second_child_status == "finished" else None
    )


@pytest.mark.parametrize("case", ["missing", "multiple", "wrong_root", "valid"])
def test_terminal_required_conditioning_diagnostics_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    root_job = _FakeJob(id="root", meta={"runid": "run-1"}, status="finished")
    diagnostic = {
        "schema_version": 1,
        "root_job_id": "wrong" if case == "wrong_root" else "root",
        "producer_job_id": "child",
        "operation_id": "0123456789abcdef0123456789abcdef",
        "method": "fill",
        "elevation_unit": "m",
        "maximum_raise": 379.0,
        "maximum_cut": 0.0,
        "summary": "Fill completed.",
    }
    child = {
        "job_id": "child",
        "status": "finished",
        "started_at": "2026-07-30T00:00:00Z",
        "ended_at": "2026-07-30T00:00:01Z",
        "children": {},
        "_conditioning_diagnostics_required": True,
    }
    if case != "missing":
        child["_conditioning_diagnostics"] = diagnostic
    children = [child]
    if case == "multiple":
        children.append({**child, "job_id": "child-2"})

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
            "status": "finished",
            "started_at": "2026-07-30T00:00:00Z",
            "ended_at": "2026-07-30T00:00:01Z",
            "children": {"0": children},
        },
    )

    payload = job_info.get_wepppy_rq_job_status("root")

    if case == "valid":
        assert payload["status"] == "finished"
        assert payload["conditioning_diagnostics"] == diagnostic
    else:
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "wbt_conditioning_diagnostics_invalid"
        assert len(payload["error_id"]) == 32


def test_private_conditioning_metadata_is_removed_from_jobinfo_tree() -> None:
    tree = {
        "_conditioning_diagnostics_required": True,
        "children": {
            "0": [{
                "_conditioning_diagnostics": {"schema_version": 1},
                "children": {},
            }]
        },
    }

    job_info._strip_private_conditioning_metadata(tree)

    assert "_conditioning_diagnostics_required" not in tree
    assert "_conditioning_diagnostics" not in tree["children"]["0"][0]


def test_jobinfo_overlays_aggregate_conditioning_failure() -> None:
    details = {"status": "finished", "exc_info": "stale"}
    status = {
        "status": "failed",
        "error": {
            "code": "wbt_conditioning_diagnostics_invalid",
            "message": "Diagnostics invalid.",
            "details": {"reason": "missing"},
        },
        "error_id": "0123456789abcdef0123456789abcdef",
    }

    job_info._overlay_conditioning_diagnostics_failure(details, status)

    assert details["status"] == "failed"
    assert details["error"] == status["error"]
    assert details["error_id"] == status["error_id"]
    assert details["exc_info"] is None
