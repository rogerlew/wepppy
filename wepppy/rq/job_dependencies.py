"""RQ dependency and deferred-workflow recovery helpers.

Required-output dependency edges use ordinary strict RQ dependencies: a failed
prerequisite must never release executable downstream work. The failure-
tolerant helpers in this module are limited to explicitly reviewed terminal
finalizers and independent resource-serialization edges. Controller retries use
``reconcile_deferred_workflow`` to cancel and detach obsolete never-started
graphs before enqueueing replacement work, so strict dependencies do not create
user-facing lockout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal, Optional

from redis.exceptions import WatchError
from rq import Queue
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry

__all__ = [
    "failure_tolerant_depends_on",
    "DeferredWorkflowReconciliation",
    "reconcile_deferred_workflow",
    "release_deferred_job_if_ready",
]

_ACTIVE_JOB_STATUSES = frozenset({"queued", "started", "scheduled"})
_TERMINAL_JOB_STATUSES = frozenset({"finished", "failed", "stopped", "canceled"})
_MAX_RECONCILE_ATTEMPTS = 5


@dataclass(frozen=True)
class DeferredWorkflowReconciliation:
    """Result of reconciling a recorded workflow before replacement enqueue."""

    state: Literal["canceled", "active", "terminal", "missing", "mismatch"]
    job_ids: tuple[str, ...] = ()


def _normalize_status(value: Any) -> str:
    normalized = getattr(value, "value", value)
    if isinstance(normalized, bytes):
        normalized = normalized.decode("utf-8", errors="replace")
    return str(normalized or "").strip().lower()


def _linked_job_ids(job: Job) -> set[str]:
    linked: set[str] = {str(job_id) for job_id in job.dependent_ids if job_id}
    dependency_prefix = Job.redis_job_namespace_prefix
    for raw_job_id in job.dependency_ids:
        job_id = raw_job_id.decode("utf-8") if isinstance(raw_job_id, bytes) else str(raw_job_id)
        if job_id.startswith(dependency_prefix):
            job_id = job_id[len(dependency_prefix):]
        if job_id:
            linked.add(job_id)
    metadata = job.meta if isinstance(job.meta, dict) else {}
    for key, value in metadata.items():
        if str(key).startswith("jobs:") and value:
            linked.add(str(value))
    return linked


def _snapshot_linked_job_ids(pipeline: Any, job: Job) -> set[str]:
    """Read every adjacency source through an established WATCH pipeline."""
    linked: set[str] = set()
    dependency_prefix = Job.redis_job_namespace_prefix
    for raw_job_id in pipeline.smembers(job.dependencies_key):
        job_id = raw_job_id.decode("utf-8") if isinstance(raw_job_id, bytes) else str(raw_job_id)
        if job_id.startswith(dependency_prefix):
            job_id = job_id[len(dependency_prefix):]
        if job_id:
            linked.add(job_id)
    for raw_job_id in pipeline.smembers(job.dependents_key):
        job_id = raw_job_id.decode("utf-8") if isinstance(raw_job_id, bytes) else str(raw_job_id)
        if job_id:
            linked.add(job_id)
    raw_meta = pipeline.hget(job.key, "meta")
    if raw_meta:
        metadata = job.serializer.loads(raw_meta)
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if str(key).startswith("jobs:") and value:
                    linked.add(str(value))
    return linked


def _job_dependency_ids(job: Job) -> set[str]:
    dependency_prefix = Job.redis_job_namespace_prefix
    dependency_ids: set[str] = set()
    for raw_job_id in job.dependency_ids:
        job_id = raw_job_id.decode("utf-8") if isinstance(raw_job_id, bytes) else str(raw_job_id)
        if job_id.startswith(dependency_prefix):
            job_id = job_id[len(dependency_prefix):]
        if job_id:
            dependency_ids.add(job_id)
    return dependency_ids


def _collect_workflow_jobs(
    root_job: Job,
    *,
    association: Callable[[Job], bool],
    excluded_dependency_job_ids: Callable[[Job], Iterable[str]] | None = None,
    lease_checkpoint: Callable[[], None] | None = None,
) -> tuple[list[Job], bool, dict[str, set[str]]]:
    jobs: list[Job] = []
    adjacency: dict[str, set[str]] = {}
    pending = [root_job]
    seen: set[str] = set()
    mismatch = False

    while pending:
        if lease_checkpoint is not None:
            lease_checkpoint()
        job = pending.pop()
        job_id = str(job.id)
        if job_id in seen:
            continue
        seen.add(job_id)
        if not association(job):
            mismatch = True
            continue
        jobs.append(job)
        linked_job_ids = _linked_job_ids(job)
        if excluded_dependency_job_ids is not None:
            excluded_ids = {
                str(job_id)
                for job_id in excluded_dependency_job_ids(job)
                if job_id
            }
            linked_job_ids.difference_update(excluded_ids & _job_dependency_ids(job))
        adjacency[job_id] = linked_job_ids
        for linked_job_id in linked_job_ids:
            if linked_job_id in seen:
                continue
            try:
                pending.append(Job.fetch(linked_job_id, connection=job.connection))
            except NoSuchJobError:
                continue

    return jobs, mismatch, adjacency


def reconcile_deferred_workflow(
    root_job_id: str | None,
    *,
    connection: Any,
    association: Callable[[Job], bool],
    root_association: Callable[[Job], bool],
    excluded_dependency_job_ids: Callable[[Job], Iterable[str]] | None = None,
    max_attempts: int = _MAX_RECONCILE_ATTEMPTS,
    lease_checkpoint: Callable[[], None] | None = None,
) -> DeferredWorkflowReconciliation:
    """Cancel one safely associated all-deferred workflow conditionally.

    The watched transaction closes the race between reading ``deferred`` and
    RQ promoting the job. Any associated queued, started, or scheduled member
    preserves the workflow as active. A linked job that fails ``association``
    prevents mutation of the complete graph.
    """
    normalized_root_id = str(root_job_id or "").strip()
    if not normalized_root_id:
        return DeferredWorkflowReconciliation("missing")

    attempts = max(1, int(max_attempts))
    for _attempt in range(attempts):
        with connection.pipeline() as pipeline:
            jobs: list[Job] = []
            pending = [normalized_root_id]
            seen: set[str] = set()
            mismatch = False
            restart = False
            while pending:
                if lease_checkpoint is not None:
                    lease_checkpoint()
                job_id = pending.pop()
                if job_id in seen:
                    continue
                seen.add(job_id)
                # Establish the hash watch before loading any identity fields
                # used by the association policy.
                pipeline.watch(Job.key_for(job_id))
                try:
                    job = Job.fetch(job_id, connection=connection)
                except NoSuchJobError:
                    if job_id == normalized_root_id:
                        pipeline.multi()
                        pipeline.ping()
                        try:
                            pipeline.execute()
                        except WatchError:
                            restart = True
                            break
                        return DeferredWorkflowReconciliation("missing")
                    continue
                if (
                    job_id == normalized_root_id
                    and not root_association(job)
                ):
                    mismatch = True
                    continue
                if not association(job):
                    mismatch = True
                    continue
                jobs.append(job)
                pipeline.watch(job.dependencies_key, job.dependents_key)
                pipeline.watch(DeferredJobRegistry(
                    job.origin,
                    connection=connection,
                    job_class=job.__class__,
                    serializer=job.serializer,
                ).key)
                linked_job_ids = _snapshot_linked_job_ids(pipeline, job)
                if excluded_dependency_job_ids is not None:
                    excluded_ids = {
                        str(linked_id)
                        for linked_id in excluded_dependency_job_ids(job)
                        if linked_id
                    }
                    stored_dependency_ids: set[str] = set()
                    for raw_id in pipeline.smembers(job.dependencies_key):
                        dependency_id = (
                            raw_id.decode("utf-8")
                            if isinstance(raw_id, bytes)
                            else str(raw_id)
                        )
                        if dependency_id.startswith(Job.redis_job_namespace_prefix):
                            dependency_id = dependency_id[
                                len(Job.redis_job_namespace_prefix):
                            ]
                        if dependency_id:
                            stored_dependency_ids.add(dependency_id)
                    linked_job_ids.difference_update(
                        excluded_ids & stored_dependency_ids
                    )
                pending.extend(linked_job_ids - seen)

            if restart:
                continue
            if mismatch or not jobs:
                pipeline.unwatch()
                return DeferredWorkflowReconciliation("mismatch")

            job_ids = tuple(str(job.id) for job in jobs)

            statuses: dict[str, str] = {}
            for job in jobs:
                if lease_checkpoint is not None:
                    lease_checkpoint()
                statuses[str(job.id)] = _normalize_status(
                    pipeline.hget(job.key, "status")
                )
            active_ids = tuple(
                job_id for job_id, status in statuses.items() if status in _ACTIVE_JOB_STATUSES
            )
            if active_ids:
                pipeline.multi()
                pipeline.ping()
                try:
                    pipeline.execute()
                except WatchError:
                    continue
                return DeferredWorkflowReconciliation("active", active_ids)

            deferred_jobs = [job for job in jobs if statuses[str(job.id)] == "deferred"]
            unknown_ids = tuple(
                job_id
                for job_id, status in statuses.items()
                if status not in _ACTIVE_JOB_STATUSES
                and status not in _TERMINAL_JOB_STATUSES
                and status != "deferred"
            )
            if unknown_ids:
                pipeline.multi()
                pipeline.ping()
                try:
                    pipeline.execute()
                except WatchError:
                    continue
                return DeferredWorkflowReconciliation("mismatch", unknown_ids)
            if not deferred_jobs:
                pipeline.multi()
                pipeline.ping()
                try:
                    pipeline.execute()
                except WatchError:
                    continue
                return DeferredWorkflowReconciliation("terminal", job_ids)

            dependency_keys_by_job_id: dict[str, set[Any]] = {}
            for job in deferred_jobs:
                if lease_checkpoint is not None:
                    lease_checkpoint()
                dependency_keys_by_job_id[str(job.id)] = pipeline.smembers(
                    job.dependencies_key
                )
            try:
                pipeline.multi()
                for job in deferred_jobs:
                    if lease_checkpoint is not None:
                        lease_checkpoint()
                    for dependency_id in dependency_keys_by_job_id[str(job.id)]:
                        if isinstance(dependency_id, bytes):
                            dependency_id = dependency_id.decode("utf-8")
                        pipeline.srem(job.dependents_key_for(dependency_id), job.id)
                    pipeline.delete(job.dependencies_key)
                    pipeline.delete(job.dependents_key)
                    try:
                        job.cancel(pipeline=pipeline, enqueue_dependents=False)
                    except InvalidJobOperation:
                        # The watched job hash will force retry if another actor
                        # changed cancellation state after the status read.
                        pipeline.reset()
                        break
                else:
                    if lease_checkpoint is not None:
                        lease_checkpoint()
                    pipeline.execute()
                    return DeferredWorkflowReconciliation(
                        "canceled",
                        tuple(str(job.id) for job in deferred_jobs),
                    )
            except WatchError:
                continue

    # Reconcile once more without mutation so callers can return the correct
    # active/terminal outcome after repeated promotion contention.
    try:
        root_job = Job.fetch(normalized_root_id, connection=connection)
    except NoSuchJobError:
        # Repeated contention makes a permissive absence unsafe: an ambiguous
        # enqueue may be recreating this exact receipt.
        return DeferredWorkflowReconciliation("mismatch", (normalized_root_id,))
    jobs, mismatch, _adjacency = _collect_workflow_jobs(
        root_job,
        association=association,
        excluded_dependency_job_ids=excluded_dependency_job_ids,
        lease_checkpoint=lease_checkpoint,
    )
    if mismatch:
        return DeferredWorkflowReconciliation("mismatch")
    final_statuses = {
        str(job.id): _normalize_status(job.get_status(refresh=True))
        for job in jobs
    }
    active_ids = tuple(
        job_id
        for job_id, status in final_statuses.items()
        if status in _ACTIVE_JOB_STATUSES
    )
    if active_ids:
        return DeferredWorkflowReconciliation("active", active_ids)
    # Without WATCH ownership, a terminal-looking graph can gain a new edge or
    # executable member immediately after this read. Fail closed after retry
    # exhaustion; a later ordinary submission can retry reconciliation.
    return DeferredWorkflowReconciliation("mismatch", tuple(str(job.id) for job in jobs))


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
    """Build an explicitly authorized failure-tolerant ``Dependency``.

    Accepts whatever the enqueue sites already pass -- ``None``, a single
    ``Job``, a job id, an iterable of either, or an existing ``Dependency``
    (returned unchanged so explicit per-edge wiring still wins). Callers must
    be one of the reviewed finalizer or independent-serialization sites; this
    helper is not the default for required-output pipeline edges.
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
    pipeline = queue.connection.pipeline()
    while True:
        try:
            pipeline.watch(deferred_job.key, deferred_job.dependencies_key)
            deferred_job.refresh()
            if deferred_job.get_status(refresh=False) != JobStatus.DEFERRED:
                return

            stored_ids = {
                dependency_id.decode()
                if isinstance(dependency_id, bytes)
                else str(dependency_id)
                for dependency_id in pipeline.smembers(deferred_job.dependencies_key)
            }
            expected_ids = {
                dependency_id.decode()
                if isinstance(dependency_id, bytes)
                else str(dependency_id)
                for dependency_id in deferred_job._dependency_ids
            }
            if not expected_ids or stored_ids != expected_ids:
                return

            dependency_keys = [Job.key_for(dependency_id) for dependency_id in expected_ids]
            dependent_set_keys = [
                Job.dependents_key_for(dependency_id) for dependency_id in expected_ids
            ]
            pipeline.watch(*dependency_keys, *dependent_set_keys)
            dependencies = Job.fetch_many(
                sorted(expected_ids),
                connection=queue.connection,
                serializer=deferred_job.serializer,
            )
            if any(dependency is None for dependency in dependencies):
                return
            statuses = {
                dependency.get_status(refresh=True)
                for dependency in dependencies
                if dependency is not None
            }
            if not statuses.issubset({JobStatus.FINISHED, JobStatus.FAILED}):
                return

            pipeline.multi()
            for dependents_key in dependent_set_keys:
                pipeline.srem(dependents_key, deferred_job.id)
            pipeline.delete(deferred_job.dependencies_key)
            DeferredJobRegistry(queue=queue).remove(deferred_job, pipeline=pipeline)
            queue._enqueue_job(deferred_job, pipeline=pipeline)
            pipeline.execute()
            return
        except WatchError:
            continue
        finally:
            pipeline.reset()
