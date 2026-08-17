"""Failure-tolerant RQ dependency wiring.

RQ holds a dependent job in ``deferred`` until ``Job.dependencies_are_met``
returns True, and that check only accepts ``FINISHED`` unless the edge was
built with ``allow_failure``. A bare ``depends_on`` therefore strands every
downstream job permanently the first time an upstream job fails -- the
dependent is never released, never expires, and never reaches a terminal
state.

That is how ~9,800 zombie jobs accumulated on the ``batch`` and ``default``
queues. It also breaks the completion contract: stage tails such as
``_log_complete_rq`` and the Omni finalizers stamp ``RedisPrep`` and emit
``END_BROADCAST``, so a stranded tail leaves the UI status stream open
forever and the batch "jobs are active" guard permanently tripped.

Pipelines route their edges through :func:`failure_tolerant_depends_on` so a
failed upstream job still releases its dependents, which then run over
whatever succeeded or fail terminally on their own missing inputs. Either way
the pipeline reaches a terminal state and the tail runs.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from rq import Queue
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry

__all__ = [
    "failure_tolerant_depends_on",
    "release_deferred_job_if_ready",
]


def _dependency_id(candidate: Any) -> Optional[str]:
    if candidate is None:
        return None
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, bytes):
        return candidate.decode()
    job_id = getattr(candidate, "id", None)
    return str(job_id) if job_id is not None else None


def failure_tolerant_depends_on(depends_on: Any) -> Optional[Dependency]:
    """Normalize a ``depends_on`` value into a failure-tolerant ``Dependency``.

    Accepts whatever the enqueue sites already pass -- ``None``, a single
    ``Job``, a job id, an iterable of either, or an existing ``Dependency``
    (returned unchanged so explicit per-edge wiring still wins). Returns
    ``None`` when there is nothing to depend on, so callers can pass the
    result straight through to ``Queue.enqueue_call``.
    """
    if depends_on is None:
        return None
    if isinstance(depends_on, Dependency):
        return depends_on

    if isinstance(depends_on, (str, bytes)) or not isinstance(depends_on, Iterable):
        candidates = [depends_on]
    else:
        candidates = list(depends_on)

    job_ids = [job_id for job_id in (_dependency_id(c) for c in candidates) if job_id]
    if not job_ids:
        return None

    return Dependency(jobs=job_ids, allow_failure=True)


def release_deferred_job_if_ready(queue: Queue, deferred_job: Job) -> None:
    """Enqueue a job whose dependencies were already terminal when it was created.

    ``Queue.setup_dependencies`` defers a new job when any dependency is not
    ``FINISHED`` -- including one that already failed. Such a dependency has
    already fanned out to its dependents, so no later event will release this
    job. Re-evaluate the failure-tolerant condition and enqueue it here.

    A job enqueued without dependencies is never deferred, so skip the status
    round-trip entirely -- most pipeline stages call this on every enqueue.
    """
    if not getattr(deferred_job, "_dependency_ids", None):
        return
    if deferred_job.get_status(refresh=True) != JobStatus.DEFERRED:
        return
    if not deferred_job.dependencies_are_met():
        return

    DeferredJobRegistry(queue=queue).remove(deferred_job)
    queue._enqueue_job(deferred_job)
