from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest
import redis

import wepppy.rq.job_info as job_info


pytestmark = pytest.mark.unit


OBSERVED_AT = datetime(2026, 8, 7, 18, 42, 11, tzinfo=timezone.utc)


class _EnumLikeStatus:
    def __init__(self, value: str) -> None:
        self.value = value


class _NoncanonicalStatus:
    def __str__(self) -> str:
        return "not-a-rq-status"


@dataclass
class _FakeJob:
    id: str
    status: Any = "finished"
    origin: str | None = "batch"
    meta: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    description: str = "fake job"
    exc_info: str | None = None

    def get_status(self) -> Any:
        return self.status


class _QueueDouble:
    ids: list[str] = []
    reads = 0

    def __init__(self, name: str, connection: object) -> None:
        self.name = name
        self.connection = connection

    def get_job_ids(self) -> list[str]:
        type(self).reads += 1
        return list(type(self).ids)


class _RaisingQueue:
    def __init__(self, name: str, connection: object) -> None:
        del name, connection

    def get_job_ids(self) -> list[str]:
        raise redis.exceptions.ConnectionError("queue unavailable")


class _RedisContext:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        del exc_type, exc, tb
        return False


def test_standalone_root_at_queue_offset_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _QueueDouble.ids = ["root"]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [("root", "queued", "batch")],
        observed_at=OBSERVED_AT,
    )

    assert snapshot == {
        "name": "batch",
        "rank": 1,
        "jobs_ahead": 0,
        "position_job_id": "root",
        "basis": "next_queued_job_in_tree",
        "observed_at": "2026-08-07T18:42:11Z",
    }


def test_standalone_root_after_unrelated_entries_does_not_disclose_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _QueueDouble.ids = ["unrelated-1", "unrelated-2", "root"]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [("root", "queued", "batch")],
        observed_at=OBSERVED_AT,
    )

    assert snapshot is not None
    assert snapshot["rank"] == 3
    assert snapshot["jobs_ahead"] == 2
    assert snapshot["position_job_id"] == "root"
    assert "unrelated-1" not in snapshot.values()
    assert "unrelated-2" not in snapshot.values()


def test_multiple_candidates_choose_minimum_queue_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _QueueDouble.ids = ["unrelated", "child-2", "child-1"]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [
            ("child-1", "queued", "batch"),
            ("child-2", "queued", "batch"),
        ],
        observed_at=OBSERVED_AT,
    )

    assert snapshot is not None
    assert snapshot["position_job_id"] == "child-2"
    assert snapshot["jobs_ahead"] == 1
    assert snapshot["rank"] == 2


def test_duplicate_queue_entry_uses_earliest_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _QueueDouble.ids = ["candidate", "unrelated", "candidate"]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [("candidate", "queued", "batch")],
        observed_at=OBSERVED_AT,
    )

    assert snapshot is not None
    assert snapshot["jobs_ahead"] == 0
    assert snapshot["rank"] == 1


def test_queue_snapshot_uses_one_ordered_read_for_large_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_ids = [f"child-{index}" for index in range(1000)]
    _QueueDouble.ids = ["unrelated", *candidate_ids]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [(job_id, "queued", "batch") for job_id in candidate_ids],
        observed_at=OBSERVED_AT,
    )

    assert snapshot is not None
    assert snapshot["position_job_id"] == "child-0"
    assert snapshot["rank"] == 2
    assert _QueueDouble.reads == 1


@pytest.mark.parametrize(
    "candidates",
    [
        [],
        [("job", "started", "batch")],
        [("job", "finished", "batch")],
        [("job", "deferred", "batch")],
        [("job", "scheduled", "batch")],
        [("job", "queued", "")],
        [("job", "queued", None)],
        [("job-1", "queued", "default"), ("job-2", "queued", "batch")],
    ],
)
def test_queue_snapshot_omits_unrankable_trees(
    candidates: list[tuple[str, str, str | None]],
) -> None:
    assert job_info._build_queue_snapshot(object(), candidates, OBSERVED_AT) is None


def test_dequeue_race_omits_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    _QueueDouble.ids = []
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    assert (
        job_info._build_queue_snapshot(
            object(), [("gone", "queued", "batch")], OBSERVED_AT
        )
        is None
    )


def test_partial_dequeue_race_ranks_remaining_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _QueueDouble.ids = ["remaining"]
    _QueueDouble.reads = 0
    monkeypatch.setattr(job_info, "Queue", _QueueDouble)

    snapshot = job_info._build_queue_snapshot(
        object(),
        [("gone", "queued", "batch"), ("remaining", "queued", "batch")],
        OBSERVED_AT,
    )

    assert snapshot is not None
    assert snapshot["position_job_id"] == "remaining"
    assert snapshot["rank"] == 1


def test_status_normalization_handles_enum_and_string_but_not_other_object() -> None:
    assert job_info._normalize_job_status(_EnumLikeStatus("queued")) == "queued"
    assert job_info._normalize_job_status("queued") == "queued"
    assert job_info._normalize_job_status(_NoncanonicalStatus()) != "queued"


def _status_payload(
    monkeypatch: pytest.MonkeyPatch,
    jobs: dict[str, _FakeJob],
    queue_ids: list[str],
    queue_type: type[_QueueDouble] = _QueueDouble,
) -> dict[str, Any]:
    queue_type.ids = queue_ids
    queue_type.reads = 0
    monkeypatch.setattr(job_info.redis, "Redis", _RedisContext)
    monkeypatch.setattr(job_info.Job, "fetch", lambda job_id, connection: jobs[job_id])
    monkeypatch.setattr(job_info, "Queue", queue_type)
    return job_info.get_wepppy_rq_job_status("root")


def test_culvert_root_ranks_registered_queued_child_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = {
        "root": _FakeJob(
            "root",
            status="finished",
            origin="batch",
            meta={"jobs:0,runid:culvert-child": "child"},
        ),
        "child": _FakeJob("child", status="queued", origin="batch"),
    }

    payload = _status_payload(monkeypatch, jobs, ["unrelated", "child"])

    assert payload["status"] == "queued"
    assert payload["queue"]["name"] == "batch"
    assert payload["queue"]["position_job_id"] == "child"
    assert payload["queue"]["rank"] == 2
    assert "unrelated" not in str(payload)


def test_registered_finalizer_can_be_ranked_after_finished_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = {
        "root": _FakeJob(
            "root",
            status="finished",
            origin="batch",
            meta={
                "jobs:0,runid:culvert-child": "child",
                "jobs:1,func:finalizer": "finalizer",
            },
        ),
        "child": _FakeJob("child", status="finished", origin="batch"),
        "finalizer": _FakeJob("finalizer", status="queued", origin="batch"),
    }

    payload = _status_payload(monkeypatch, jobs, ["finalizer"])

    assert payload["queue"]["position_job_id"] == "finalizer"
    assert payload["queue"]["rank"] == 1


def test_redis_error_omits_queue_but_preserves_authoritative_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = {"root": _FakeJob("root", status="queued", origin="batch")}

    payload = _status_payload(monkeypatch, jobs, [], _RaisingQueue)

    assert payload["status"] == "queued"
    assert "queue" not in payload
