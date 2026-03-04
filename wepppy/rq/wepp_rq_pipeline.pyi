from __future__ import annotations

from typing import Any, Callable, Optional

from rq import Queue
from rq.job import Job

def enqueue_log_complete(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    tasks: Any,
    kwargs: Optional[dict[str, Any]] = ...,
    depends_on: Any = ...,
) -> Job: ...

def enqueue_log_prep_complete(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    tasks: Any,
    kwargs: Optional[dict[str, Any]] = ...,
    depends_on: Any = ...,
) -> Job: ...

def enqueue_wepp_prep_only_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    tasks: Any,
    timeout: int,
) -> Job: ...

def enqueue_wepp_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
) -> Job: ...

def enqueue_wepp_noprep_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
) -> Job: ...

def enqueue_watershed_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
    has_hillslope_outputs: bool,
    publish_status: Callable[[str], None] | None = ...,
) -> Job: ...

def enqueue_watershed_noprep_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
    has_hillslope_outputs: bool,
    publish_status: Callable[[str], None] | None = ...,
) -> Job: ...
