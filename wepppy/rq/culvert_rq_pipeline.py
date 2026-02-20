from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Optional

from rq import Queue
from rq.job import Job


def _record_parent_meta(
    parent_job: Optional[Job],
    key: str,
    child_job: Job,
) -> Job:
    if parent_job is None:
        return child_job
    parent_job.meta[key] = child_job.id
    parent_job.save()
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
) -> Job:
    child_job = q.enqueue_call(
        func=func,
        args=args,
        kwargs=kwargs,
        timeout=timeout,
        depends_on=depends_on,
    )
    if child_meta:
        child_job.meta.update(child_meta)
        child_job.save()
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
        depends_on=child_jobs if child_jobs else None,
        child_meta={"culvert_batch_uuid": culvert_batch_uuid},
    )
    return final_job, queued_jobs

