from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from rq import Queue
from rq.job import Job

def enqueue_culvert_batch_jobs(
    q: Queue,
    parent_job: Optional[Job],
    *,
    culvert_batch_uuid: str,
    run_ids: Iterable[str],
    tasks: Any,
    timeout: int,
    stagger_seconds: float = ...,
    sleep_fn: Callable[[float], None] = ...,
) -> tuple[Job, dict[str, str]]: ...

