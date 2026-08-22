from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from rq.job import JobStatus

from wepppy.rq import wepp_rq


pytestmark = pytest.mark.unit


@dataclass
class _FakeJob:
    id: str
    status: str | JobStatus
    meta: dict[str, str] = field(default_factory=dict)
    dependency_ids: list[str | bytes] = field(default_factory=list)

    def get_status(self, *, refresh: bool = False) -> str | JobStatus:
        assert refresh is False
        return self.status


class _FakePrep:
    def __init__(self, job_ids: dict[str, str]) -> None:
        self.job_ids = job_ids

    def get_rq_job_id(self, key: str) -> str | None:
        return self.job_ids.get(key)


def _install_jobs(monkeypatch: pytest.MonkeyPatch, jobs: list[_FakeJob]) -> Any:
    jobs_by_id = {job.id: job for job in jobs}

    def fetch(job_id: str, *, connection: Any) -> _FakeJob:
        del connection
        try:
            return jobs_by_id[job_id]
        except KeyError as exc:
            raise wepp_rq.NoSuchJobError from exc

    monkeypatch.setattr(wepp_rq.Job, "fetch", fetch)
    return object()


@pytest.mark.parametrize("job_key", wepp_rq.WEPP_RQ_JOB_KEYS)
def test_finished_root_tracks_active_descendant_for_every_wepp_path(
    monkeypatch: pytest.MonkeyPatch,
    job_key: str,
) -> None:
    root = _FakeJob("root", "finished", {"jobs:1,func:run": "child"})
    child = _FakeJob("child", "started")
    redis_conn = _install_jobs(monkeypatch, [root, child])

    active = wepp_rq.get_active_wepp_job(_FakePrep({job_key: root.id}), redis_conn)

    assert active == {"key": job_key, "job_id": child.id, "status": "started"}
    with pytest.raises(wepp_rq.WeppSingleFlightConflict, match="job_id=child"):
        wepp_rq.ensure_no_active_wepp_job("run-1", _FakePrep({job_key: root.id}), redis_conn)


def test_rq_job_status_enum_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _FakeJob("root", JobStatus.STARTED)
    redis_conn = _install_jobs(monkeypatch, [root])

    active = wepp_rq.get_active_wepp_job(
        _FakePrep({"run_wepp_rq": root.id}),
        redis_conn,
    )

    assert active == {"key": "run_wepp_rq", "job_id": root.id, "status": "started"}


def test_viable_deferred_descendant_does_not_block_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _FakeJob("root", "finished", {"jobs:1,func:run": "run", "jobs:6,func:final": "final"})
    run = _FakeJob("run", "finished")
    final = _FakeJob("final", "deferred", dependency_ids=[f"rq:job:{run.id}".encode()])
    redis_conn = _install_jobs(monkeypatch, [root, run, final])

    active = wepp_rq.get_active_wepp_job(
        _FakePrep({"run_wepp_watershed_rq": root.id}),
        redis_conn,
    )

    assert active is None


@pytest.mark.parametrize("failed_status", ["failed", "stopped", "canceled"])
def test_stranded_deferred_descendant_does_not_block_retry(
    monkeypatch: pytest.MonkeyPatch,
    failed_status: str,
) -> None:
    root = _FakeJob("root", "finished", {"jobs:1,func:run": "run", "jobs:6,func:final": "final"})
    run = _FakeJob("run", failed_status)
    final = _FakeJob("final", "deferred", dependency_ids=[f"rq:job:{run.id}".encode()])
    redis_conn = _install_jobs(monkeypatch, [root, run, final])

    assert (
        wepp_rq.get_active_wepp_job(
            _FakePrep({"run_wepp_watershed_noprep_rq": root.id}),
            redis_conn,
        )
        is None
    )


def test_active_sibling_blocks_even_when_another_descendant_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _FakeJob(
        "root",
        "finished",
        {
            "jobs:0,func:failed_prep": "failed",
            "jobs:0,func:running_prep": "running",
            "jobs:6,func:final": "final",
        },
    )
    failed = _FakeJob("failed", "failed")
    running = _FakeJob("running", "queued")
    final = _FakeJob("final", "deferred", dependency_ids=[failed.id, running.id])
    redis_conn = _install_jobs(monkeypatch, [root, failed, running, final])

    active = wepp_rq.get_active_wepp_job(
        _FakePrep({"prep_wepp_watershed_rq": root.id}),
        redis_conn,
    )

    assert active == {
        "key": "prep_wepp_watershed_rq",
        "job_id": running.id,
        "status": "queued",
    }


def test_nested_active_descendant_is_tracked(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _FakeJob("root", "finished", {"jobs:0,func:stage": "stage"})
    stage = _FakeJob("stage", "finished", {"jobs:1,func:leaf": "leaf"})
    leaf = _FakeJob("leaf", "scheduled")
    redis_conn = _install_jobs(monkeypatch, [root, stage, leaf])

    active = wepp_rq.get_active_wepp_job(
        _FakePrep({"run_wepp_rq": root.id}),
        redis_conn,
    )

    assert active == {"key": "run_wepp_rq", "job_id": leaf.id, "status": "scheduled"}


def test_unrelated_failure_does_not_make_deferred_branch_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _FakeJob(
        "root",
        "finished",
        {
            "jobs:0,func:failed_branch": "failed",
            "jobs:1,func:finished_branch": "finished",
            "jobs:2,func:deferred_branch": "deferred",
        },
    )
    failed = _FakeJob("failed", "failed")
    finished = _FakeJob("finished", "finished")
    deferred = _FakeJob(
        "deferred",
        "deferred",
        dependency_ids=[f"rq:job:{finished.id}".encode()],
    )
    redis_conn = _install_jobs(monkeypatch, [root, failed, finished, deferred])

    active = wepp_rq.get_active_wepp_job(
        _FakePrep({"run_wepp_watershed_rq": root.id}),
        redis_conn,
    )

    assert active is None


def test_missing_child_record_does_not_block_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _FakeJob("root", "finished", {"jobs:1,func:expired": "missing"})
    redis_conn = _install_jobs(monkeypatch, [root])

    assert (
        wepp_rq.get_active_wepp_job(
            _FakePrep({"run_wepp_noprep_rq": root.id}),
            redis_conn,
        )
        is None
    )


def test_finished_tree_does_not_block_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _FakeJob("root", "finished", {"jobs:1,func:run": "run"})
    run = _FakeJob("run", "finished")
    redis_conn = _install_jobs(monkeypatch, [root, run])

    assert (
        wepp_rq.get_active_wepp_job(
            _FakePrep({"run_wepp_rq": root.id}),
            redis_conn,
        )
        is None
    )
