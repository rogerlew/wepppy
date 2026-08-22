from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager
from typing import Any

from rq.job import Job
from wepppy.nodb.redis_prep import RedisPrep

__all__ = [
    "RqSubmissionConflict",
    "RqEnqueueVerificationError",
    "enqueue_tracked_rq_job",
    "prepare_redisprep_job_id",
    "recover_committed_enqueue",
    "rq_submission_lock",
]

class RqSubmissionConflict(RuntimeError): ...
class RqEnqueueVerificationError(RuntimeError): ...

def checkpoint_run_lifecycle(runid: str) -> None: ...
def recover_committed_enqueue(connection: Any, job_id: str, *, func: Any, runid: str, origin: str, run_arg_index: int = ..., args: tuple[Any, ...] | list[Any] = ..., kwargs: dict[str, Any] | None = ...) -> Job | None: ...
class SubmissionLease:
    def __init__(self, locks: Iterable[Any]) -> None: ...
    def close(self) -> None: ...
    def checkpoint(self) -> None: ...

def rq_submission_lock(
    connection: Any,
    resource_key: str,
    *,
    lifecycle_key: str,
    lifecycle_type: str = ...,
    blocking_timeout: float = ...,
) -> AbstractContextManager[SubmissionLease]: ...
def prepare_redisprep_job_id(
    prep: RedisPrep,
    *,
    job_key: str,
    replacement_job_id: str,
    connection: Any,
    runid: str,
    conflict_keys: Iterable[str] | None = ...,
    allowed_origins: Iterable[str] | None = ...,
    expected_root_module: str | None = ...,
    expected_root_func_name: str | None = ...,
    allowed_root_func_names: Iterable[str] | None = ...,
    allowed_workflow_func_names: Iterable[str] | None = ...,
    allowed_workflow_modules: Iterable[str] | None = ...,
    root_run_arg_index: int = ...,
    association: Callable[[Job], bool] | None = ...,
    lease_checkpoint: Callable[[], None] | None = ...,
) -> None: ...
def enqueue_tracked_rq_job(
    queue: Any,
    func: Any,
    *,
    prep: RedisPrep,
    job_key: str,
    runid: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any] | None = ...,
    timeout: Any = ...,
    meta: dict[str, Any] | None = ...,
    conflict_keys: Iterable[str] | None = ...,
    allowed_origins: Iterable[str] | None = ...,
    allowed_root_funcs: Iterable[Any] | None = ...,
    allowed_workflow_funcs: Iterable[Any] | None = ...,
    allowed_workflow_modules: Iterable[str] | None = ...,
) -> Job: ...
