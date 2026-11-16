from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Optional

from rq import Queue
from rq.job import Job
from wepppy.rq import batch_outcome
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.job_dependencies import (
    failure_tolerant_depends_on,
    release_deferred_job_if_ready,
)


def _record_parent_meta(
    parent_job: Optional[Job],
    key: str,
    child_job: Job,
) -> Job:
    if parent_job is None:
        return child_job
    parent_job.refresh()
    parent_job.meta[key] = child_job.id
    parent_job.save_meta()
    return child_job


def _enqueue(
    q: Queue,
    parent_job: Optional[Job],
    *,
    key: str,
    func: Any,
    args: tuple[Any, ...] | list[Any] = (),
    kwargs: Optional[dict[str, Any]] = None,
    timeout: Any = None,
    depends_on: Any = None,
    child_meta: Optional[dict[str, Any]] = None,
    queue_name: str | None = None,
    allow_dependency_failure: bool = False,
) -> Job:
    del queue_name
    job_id = new_rq_job_id()
    if parent_job is not None and parent_job.meta.get('batch_outcome_enrolled'):
        if child_meta and 'run_id' in child_meta:
            batch_outcome.register(parent_job, member=child_meta['run_id'], jobs=[job_id])
        else:
            batch_outcome.register(parent_job, finalizer=job_id)
        child_meta = dict(child_meta or {}, batch_outcome_root_id=parent_job.id,
                          child_dispatch_lock_key=parent_job.meta['child_dispatch_lock_key'])
    with batch_outcome.dispatch(parent_job):
        child_job = q.enqueue_call(
            job_id=job_id, result_ttl=-1, failure_ttl=-1, meta=child_meta,
            func=func,
            args=args,
            kwargs=kwargs,
            timeout=timeout,
            depends_on=(
                failure_tolerant_depends_on(depends_on)
                if allow_dependency_failure
                else depends_on
            ),
        )
        if allow_dependency_failure:
            release_deferred_job_if_ready(q, child_job)
        return _record_parent_meta(parent_job, key, child_job)



def enqueue_culvert_batch_jobs(
    q: Queue,
    parent_job: Optional[Job],
    *,
    culvert_batch_uuid: str,
    run_ids: Iterable[str],
    tasks: Any,
    timeout: int,
    stagger_seconds: float = 1.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[Job, dict[str, str]]:
    child_jobs: list[Job] = []
    queued_jobs: dict[str, str] = {}

    for run_id in run_ids:
        runid = f"culvert;;{culvert_batch_uuid};;{run_id}"
        child_job = _enqueue(
            q,
            parent_job,
            key=f"jobs:0,runid:{runid}",
            func=tasks.run_culvert_run_rq,
            args=(runid, culvert_batch_uuid, run_id),
            timeout=timeout,
            depends_on=parent_job.id if parent_job is not None else None,
            queue_name="batch",
            child_meta={
                "runid": runid,
                "culvert_batch_uuid": culvert_batch_uuid,
                "run_id": run_id,
            },
        )
        child_jobs.append(child_job)
        queued_jobs[run_id] = child_job.id
        sleep_fn(stagger_seconds)

    final_job = _enqueue(
        q,
        parent_job,
        key="jobs:1,func:_final_culvert_batch_complete_rq",
        func=tasks._final_culvert_batch_complete_rq,
        args=(culvert_batch_uuid,),
        timeout=timeout,
        queue_name="batch",
        depends_on=([*child_jobs, parent_job] if parent_job is not None else child_jobs) or None,
        allow_dependency_failure=True,
        child_meta={"culvert_batch_uuid": culvert_batch_uuid},
    )
    return final_job, queued_jobs
