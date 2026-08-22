from collections.abc import Callable
from typing import Any, Literal
from dataclasses import dataclass

from rq.job import Dependency, Job

__all__ = [
    "failure_tolerant_depends_on",
    "DeferredWorkflowReconciliation",
    "reconcile_deferred_workflow",
    "release_deferred_job_if_ready",
]

@dataclass(frozen=True)
class DeferredWorkflowReconciliation:
    state: Literal["canceled", "active", "terminal", "missing", "mismatch"]
    job_ids: tuple[str, ...] = ...

def failure_tolerant_depends_on(depends_on: Any) -> Dependency | None: ...
def reconcile_deferred_workflow(
    root_job_id: str | None,
    *,
    connection: Any,
    association: Callable[[Job], bool],
    root_association: Callable[[Job], bool] | None = ...,
    max_attempts: int = ...,
    lease_checkpoint: Callable[[], None] | None = ...,
) -> DeferredWorkflowReconciliation: ...
def release_deferred_job_if_ready(queue: Any, deferred_job: Job) -> None: ...
