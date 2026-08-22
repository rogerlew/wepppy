"""Admission helpers that replace superseded deferred controller workflows."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
import threading
import time
import hashlib
import fcntl
import os
import logging
from typing import Any, Callable, Iterator

from redis.exceptions import LockError, RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.job_dependencies import reconcile_deferred_workflow
from wepppy.rq.job_id import new_rq_job_id


class RqSubmissionConflict(RuntimeError):
    """Raised when recorded work is active or cannot be safely associated."""


class RqEnqueueVerificationError(RuntimeError):
    """Raised when an ambiguous enqueue cannot be verified as present or absent."""


_HELD_LIFECYCLES: ContextVar[dict[str, "SubmissionLease"]] = ContextVar(
    "rq_submission_held_lifecycles", default={}
)
_LIFECYCLE_LOCK_DIR = os.getenv(
    "WEPPCLOUD_RQ_LIFECYCLE_LOCK_DIR", "/wc1/runs/.rq-lifecycle-locks"
)


def checkpoint_run_lifecycle(runid: str) -> None:
    """Fail before mutation when the current request lost its run lease."""
    lease = _HELD_LIFECYCLES.get().get(f"run\0{runid}")
    if lease is not None:
        lease.checkpoint()


def recover_committed_enqueue(
    connection: Any,
    job_id: str,
    *,
    func: Any,
    runid: str,
    origin: str,
    run_arg_index: int = 0,
    args: tuple[Any, ...] | list[Any] = (),
    kwargs: dict[str, Any] | None = None,
) -> Job | None:
    """Return an exact committed job after an ambiguous Redis enqueue error."""
    try:
        job = Job.fetch(job_id, connection=connection)
    except NoSuchJobError:
        return None
    except RedisError as exc:
        raise RqEnqueueVerificationError(
            "Unable to verify whether the planned job was committed."
        ) from exc
    expected_func = f"{func.__module__}.{func.__qualname__}"
    if str(job.func_name) != expected_func or str(job.origin) != str(origin):
        return None
    if not _job_targets_run(job, runid, arg_index=run_arg_index):
        return None
    if tuple(job.args or ()) != tuple(args) or dict(job.kwargs or {}) != dict(kwargs or {}):
        return None
    return job


class SubmissionLease:
    """Owner-safe Redis lease with explicit mutation checkpoints."""

    def __init__(self, locks: Iterable[Any]) -> None:
        self._locks = tuple(locks)
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._renewer = threading.Thread(
            target=self._renew_periodically,
            name="rq-submission-lease-renewer",
            daemon=True,
        )
        self._renewer.start()

    def _renew_periodically(self) -> None:
        while not self._stop.wait(30):
            try:
                for lock in self._locks:
                    if not lock.extend(120, replace_ttl=True):
                        self._lost.set()
                        return
            except (LockError, RedisError):
                self._lost.set()
                return

    def close(self) -> None:
        self._stop.set()
        self._renewer.join(timeout=1)

    def checkpoint(self) -> None:
        if self._lost.is_set():
            raise RqSubmissionConflict("Submission lock expired.")
        try:
            renewed = all(
                lock.extend(120, replace_ttl=True) for lock in self._locks
            )
        except LockError as exc:
            raise RqSubmissionConflict("Submission lock expired.") from exc
        if not renewed:
            raise RqSubmissionConflict("Submission lock expired.")


@contextmanager
def rq_submission_lock(
    connection: Any,
    resource_key: str,
    *,
    lifecycle_key: str,
    lifecycle_type: str = "run",
    blocking_timeout: float = 10,
) -> Iterator[SubmissionLease]:
    """Hold the owner-safe admission lock for a submission transaction."""
    resource = str(resource_key)
    lock_names = [f"rq:submission:{resource}"]
    # Keep lifecycle identities in a namespace distinct from family/resource
    # identities.  A run named ``batch:x`` must never alias batch ``x``.
    lifecycle = f"{lifecycle_type}\0{lifecycle_key}"
    lifecycle_digest = hashlib.sha256(lifecycle.encode("utf-8")).hexdigest()
    parent_lease = _HELD_LIFECYCLES.get().get(lifecycle)
    already_held = parent_lease is not None
    if not already_held:
        lock_names.insert(0, f"rq:submission-lifecycle:{lifecycle_digest}")
    locks = [
        connection.lock(
            lock_name,
            timeout=120,
            blocking_timeout=10,
            thread_local=False,
        )
        for lock_name in dict.fromkeys(lock_names)
    ]
    acquired: list[Any] = []
    lifecycle_fd: int | None = None
    try:
        for lock in locks:
            if blocking_timeout > 0:
                acquired_lock = lock.acquire(
                    blocking=True, blocking_timeout=blocking_timeout
                )
            else:
                acquired_lock = lock.acquire(blocking=False)
            if not acquired_lock:
                raise RqSubmissionConflict("Another submission is already in progress.")
            acquired.append(lock)
        if lifecycle_type == "run" and not already_held:
            lifecycle_dir = _LIFECYCLE_LOCK_DIR
            os.makedirs(lifecycle_dir, exist_ok=True)
            lifecycle_path = os.path.join(lifecycle_dir, lifecycle_digest)
            lifecycle_fd = os.open(lifecycle_path, os.O_CREAT | os.O_RDWR, 0o600)
            deadline = time.monotonic() + max(0, blocking_timeout)
            while True:
                try:
                    fcntl.flock(lifecycle_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() < deadline:
                        time.sleep(0.05)
                        continue
                    os.close(lifecycle_fd)
                    lifecycle_fd = None
                    raise RqSubmissionConflict("Another submission is already in progress.")
    except (OSError, RedisError, RqSubmissionConflict):
        if lifecycle_fd is not None:
            os.close(lifecycle_fd)
        for held_lock in reversed(acquired):
            try:
                held_lock.release()
            except (LockError, RedisError):
                pass
        raise
    lease = SubmissionLease(acquired)
    lifecycle_token = None
    try:
        if not already_held:
            held_lifecycles = dict(_HELD_LIFECYCLES.get())
            held_lifecycles[lifecycle] = lease
            lifecycle_token = _HELD_LIFECYCLES.set(
                held_lifecycles
            )
        elif parent_lease is not None:
            parent_lease.checkpoint()
        lease.checkpoint()
        if (
            lifecycle_type == "run"
            and not already_held
            and resource.endswith(":request")
        ):
            fork_state = connection.hget(
                f"rq:fork:planned:{lifecycle_key}", "state"
            )
            if isinstance(fork_state, bytes):
                fork_state = fork_state.decode("utf-8")
            if fork_state and str(fork_state) != "succeeded":
                raise RqSubmissionConflict(
                    "This project is still being prepared by a fork job."
                )
        yield lease
    finally:
        if lifecycle_token is not None:
            _HELD_LIFECYCLES.reset(lifecycle_token)
        lease.close()
        if lifecycle_fd is not None:
            try:
                fcntl.flock(lifecycle_fd, fcntl.LOCK_UN)
            except OSError:
                # Teardown follows the mutation boundary and must not turn an
                # already-committed enqueue into a false client-visible failure.
                logging.getLogger(__name__).warning(
                    "Could not release local run lifecycle fence", exc_info=True
                )
            try:
                os.close(lifecycle_fd)
            except OSError:
                logging.getLogger(__name__).warning(
                    "Could not close local run lifecycle fence", exc_info=True
                )
        for lock in reversed(acquired):
            try:
                lock.release()
            except (LockError, RedisError):
                # Compare-and-delete never removes a successor's lease.
                pass


def _job_targets_run(job: Job, runid: str, *, arg_index: int = 0) -> bool:
    metadata = job.meta if isinstance(job.meta, dict) else {}
    metadata_runid = str(metadata.get("runid") or "").strip()
    args = list(job.args or [])
    if len(args) <= arg_index or str(args[arg_index]) != runid:
        return False
    return not metadata_runid or metadata_runid == runid


def prepare_redisprep_job_id(
    prep: RedisPrep,
    *,
    job_key: str,
    replacement_job_id: str,
    connection: Any,
    runid: str,
    conflict_keys: Iterable[str] | None = None,
    allowed_origins: Iterable[str] | None = None,
    expected_root_module: str | None = None,
    expected_root_func_name: str | None = None,
    allowed_root_func_names: Iterable[str] | None = None,
    allowed_workflow_func_names: Iterable[str] | None = None,
    allowed_workflow_modules: Iterable[str] | None = None,
    root_run_arg_index: int = 0,
    association: Callable[[Job], bool] | None = None,
    lease_checkpoint: Callable[[], None] | None = None,
) -> None:
    """Reap deferred prior receipts, then persist a preallocated replacement ID."""
    origins = {str(origin) for origin in allowed_origins or ()}
    root_func_names = {str(name) for name in allowed_root_func_names or ()}
    if expected_root_func_name:
        root_func_names.add(expected_root_func_name)
    workflow_modules = {str(module) for module in allowed_workflow_modules or ()}
    workflow_func_names = {
        str(name) for name in allowed_workflow_func_names or ()
    }
    keys = tuple(dict.fromkeys(conflict_keys or (job_key,)))
    for candidate_key in keys:
        prior_job_id = prep.get_rq_job_id(candidate_key)
        if not prior_job_id or str(prior_job_id) == replacement_job_id:
            continue
        default_association = lambda job: (
            _job_targets_run(job, runid, arg_index=root_run_arg_index)
            and (
                str(job.func_name) in root_func_names
                or str(job.func_name) in workflow_func_names
                or str(job.func_name).rpartition(".")[0] in workflow_modules
            )
            and (
                not expected_root_module
                or str(job.func_name).rpartition(".")[0] == expected_root_module
                or str(job.func_name) in workflow_func_names
                or str(job.func_name).rpartition(".")[0] in workflow_modules
            )
            and (not origins or str(job.origin) in origins)
        )
        root_association = lambda job: (
            _job_targets_run(job, runid, arg_index=root_run_arg_index)
            and str(job.func_name) in root_func_names
            and (
                not expected_root_module
                or str(job.func_name).rpartition(".")[0] == expected_root_module
            )
            and (not origins or str(job.origin) in origins)
        )
        if lease_checkpoint is not None:
            lease_checkpoint()
        result = reconcile_deferred_workflow(
            str(prior_job_id),
            connection=connection,
            association=association or default_association,
            root_association=root_association,
            lease_checkpoint=lease_checkpoint,
        )
        if result.state == "active":
            raise RqSubmissionConflict(
                f"Recorded {candidate_key} job is still active ({result.job_ids[0]})."
            )
        if result.state == "mismatch":
            raise RqSubmissionConflict(
                f"Recorded {candidate_key} workflow association could not be verified."
            )
    if lease_checkpoint is not None:
        lease_checkpoint()
    prep.set_rq_job_id(job_key, replacement_job_id)


def enqueue_tracked_rq_job(
    queue: Any,
    func: Any,
    *,
    prep: RedisPrep,
    job_key: str,
    runid: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any] | None = None,
    timeout: Any = None,
    meta: dict[str, Any] | None = None,
    conflict_keys: Iterable[str] | None = None,
    allowed_origins: Iterable[str] | None = None,
    allowed_root_funcs: Iterable[Any] | None = None,
    allowed_workflow_funcs: Iterable[Any] | None = None,
    allowed_workflow_modules: Iterable[str] | None = None,
) -> Job:
    """Pre-save a replacement receipt and enqueue that exact RQ job id."""
    keys = tuple(dict.fromkeys(conflict_keys or (job_key,)))
    family = ":".join(sorted(keys))
    with rq_submission_lock(
        queue.connection, f"{runid}:{family}", lifecycle_key=runid
    ) as lease:
        replacement_job_id = new_rq_job_id()
        prepare_redisprep_job_id(
            prep,
            job_key=job_key,
            replacement_job_id=replacement_job_id,
            connection=queue.connection,
            runid=runid,
            conflict_keys=keys,
            allowed_origins=allowed_origins or (str(getattr(queue, "name", "default")),),
            expected_root_module=None if allowed_root_funcs else str(func.__module__),
            expected_root_func_name=f"{func.__module__}.{func.__qualname__}",
            allowed_root_func_names=(
                f"{candidate.__module__}.{candidate.__qualname__}"
                for candidate in (allowed_root_funcs or ())
            ),
            allowed_workflow_func_names=(
                f"{candidate.__module__}.{candidate.__qualname__}"
                for candidate in (allowed_workflow_funcs or ())
            ),
            allowed_workflow_modules=allowed_workflow_modules,
            lease_checkpoint=lease.checkpoint,
        )
        lease.checkpoint()
        enqueue_kwargs: dict[str, Any] = {
            "args": args,
            "timeout": timeout,
            "job_id": replacement_job_id,
        }
        if kwargs is not None:
            enqueue_kwargs["kwargs"] = kwargs
        enqueue_meta = dict(meta or {})
        enqueue_meta.setdefault("runid", runid)
        enqueue_kwargs["meta"] = enqueue_meta
        try:
            return queue.enqueue_call(func, **enqueue_kwargs)
        except RedisError:
            committed = recover_committed_enqueue(
                queue.connection,
                replacement_job_id,
                func=func,
                runid=runid,
                origin=str(getattr(queue, "name", "default")),
                args=args,
                kwargs=kwargs,
            )
            if committed is not None:
                return committed
            raise


__all__ = [
    "RqSubmissionConflict",
    "RqEnqueueVerificationError",
    "enqueue_tracked_rq_job",
    "prepare_redisprep_job_id",
    "recover_committed_enqueue",
    "rq_submission_lock",
]
