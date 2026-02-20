from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.rq.culvert_rq_pipeline as pipeline

pytestmark = pytest.mark.unit


class _DummyJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.meta: dict[str, object] = {}
        self.saves = 0

    def save(self) -> None:
        self.saves += 1


class _DummyQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def enqueue_call(
        self,
        func,
        args=(),
        kwargs=None,
        timeout=None,
        depends_on=None,
    ) -> _DummyJob:
        job = _DummyJob(f"job-{len(self.calls) + 1}")
        self.calls.append(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "timeout": timeout,
                "depends_on": depends_on,
                "job": job,
            }
        )
        return job


def _make_parent_job() -> SimpleNamespace:
    parent_job = SimpleNamespace(meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]
    return parent_job


def test_enqueue_culvert_batch_jobs_tracks_stage_meta_dependencies_and_child_meta() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        run_culvert_run_rq=object(),
        _final_culvert_batch_complete_rq=object(),
    )
    sleeps: list[float] = []

    final_job, queued_jobs = pipeline.enqueue_culvert_batch_jobs(
        q,
        parent_job,
        culvert_batch_uuid="batch-1",
        run_ids=["1", "2"],
        tasks=tasks,
        timeout=43_200,
        sleep_fn=sleeps.append,
    )

    assert queued_jobs == {"1": "job-1", "2": "job-2"}
    assert final_job.id == "job-3"
    assert parent_job.meta["jobs:0,runid:culvert;;batch-1;;1"] == "job-1"
    assert parent_job.meta["jobs:0,runid:culvert;;batch-1;;2"] == "job-2"
    assert parent_job.meta["jobs:1,func:_final_culvert_batch_complete_rq"] == "job-3"
    assert parent_job.saves == 3

    first_call = q.calls[0]
    second_call = q.calls[1]
    final_call = q.calls[2]

    assert first_call["func"] is tasks.run_culvert_run_rq
    assert first_call["args"] == ("culvert;;batch-1;;1", "batch-1", "1")
    assert second_call["args"] == ("culvert;;batch-1;;2", "batch-1", "2")
    assert first_call["depends_on"] is None
    assert second_call["depends_on"] is None

    final_depends_on = final_call["depends_on"]
    assert isinstance(final_depends_on, list)
    assert [job.id for job in final_depends_on] == ["job-1", "job-2"]

    first_child = first_call["job"]
    second_child = second_call["job"]
    assert isinstance(first_child, _DummyJob)
    assert isinstance(second_child, _DummyJob)
    assert first_child.meta["culvert_batch_uuid"] == "batch-1"
    assert first_child.meta["run_id"] == "1"
    assert second_child.meta["run_id"] == "2"
    assert sleeps == [1.0, 1.0]


def test_enqueue_culvert_batch_jobs_handles_empty_run_ids() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        run_culvert_run_rq=object(),
        _final_culvert_batch_complete_rq=object(),
    )
    sleeps: list[float] = []

    final_job, queued_jobs = pipeline.enqueue_culvert_batch_jobs(
        q,
        parent_job,
        culvert_batch_uuid="batch-empty",
        run_ids=[],
        tasks=tasks,
        timeout=43_200,
        sleep_fn=sleeps.append,
    )

    assert queued_jobs == {}
    assert final_job.id == "job-1"
    assert len(q.calls) == 1
    assert q.calls[0]["func"] is tasks._final_culvert_batch_complete_rq
    assert q.calls[0]["depends_on"] is None
    assert sleeps == []
