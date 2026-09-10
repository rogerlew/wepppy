"""Surviving-supervisor cleanup for canceled execution directory locks."""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
import select
import signal

import redis
from rq.job import Job

from wepppy.runtime_paths.thaw_freeze import release_execution_locks

LOGGER = logging.getLogger(__name__)


def _child_pids() -> set[int]:
    """Read direct children across supervisor threads, without a /proc PID scan."""
    children = set()
    for task in Path("/proc/self/task").iterdir():
        try:
            children.update(int(pid) for pid in (task / "children").read_text().split())
        except FileNotFoundError:
            if task.exists():
                raise RuntimeError(f"process children inspection unavailable for live task {task.name}")
            # Only a demonstrably exited thread may disappear from the scan.
            continue
    return children


def prepare_containment(scheduler_pid: int | None = None) -> dict[int, int]:
    """Adopt orphan writers before fork, including detached CLIGEN sessions.

    The only supported pre-existing child is RQ's scheduler, which does not
    spawn subprocesses. Pin its identity with a pidfd and never signal/reap it.
    Other children make execution ownership ambiguous.
    """
    children = _child_pids()
    if children - ({scheduler_pid} if scheduler_pid else set()):
        raise RuntimeError("supervisor has pre-existing children; execution containment is unknown")
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux PR_SET_CHILD_SUBREAPER: orphaned descendants reparent here even if
    # they called setsid(). It is not inherited by the forked workhorse.
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))
    return {scheduler_pid: os.pidfd_open(scheduler_pid)} if scheduler_pid else {}


def _verify_protected_children(protected: dict[int, int]) -> None:
    if protected and select.select(list(protected.values()), [], [], 0)[0]:
        raise RuntimeError("RQ scheduler exited; adopted process ownership is uncertain")


def terminate_adopted_writers(heartbeat, monitoring_interval: int, protected: dict[int, int]) -> None:
    """Kill and reap adopted children; return only when no writer can remain.

    Called after RQ reaped the workhorse. Killing a parent can expose more
    adopted children, so drain until empty. pidfds prevent signaling reused
    PIDs. Uninterruptible writers keep cleanup pending with worker heartbeats.
    """
    while True:
        _verify_protected_children(protected)
        children = _child_pids() - protected.keys()
        if not children:
            _verify_protected_children(protected)
            return
        descriptors = {}
        try:
            for pid in children:
                fd = os.pidfd_open(pid)
                descriptors[pid] = fd
                signal.pidfd_send_signal(fd, signal.SIGKILL)
            for pid, fd in descriptors.items():
                while not select.select([fd], [], [], monitoring_interval)[0]:
                    heartbeat()
                os.waitpid(pid, 0)
        finally:
            for fd in descriptors.values():
                os.close(fd)


def has_remaining_writers(protected: dict[int, int]) -> bool:
    """Reap exited non-scheduler children before deciding whether to retire."""
    while children := _child_pids() - protected.keys():
        for pid in children:
            if os.waitpid(pid, os.WNOHANG)[0] == 0:
                return True
    return False


def record_cleanup(job: Job, execution_id: str, state: str, **details) -> None:
    """Update diagnostics without overwriting a retry's or a caller's metadata."""
    try:
        with job.connection.pipeline() as pipe:
            pipe.watch(job.key)
            raw = pipe.hget(job.key, "meta")
            if raw is None:
                return
            meta = job.serializer.loads(raw)
            if meta.get("directory_lock_execution_id") != execution_id:
                return
            meta["directory_lock_cleanup"] = {
                "execution_id": execution_id, "state": state, **details,
            }
            pipe.multi()
            pipe.hset(job.key, "meta", job.serializer.dumps(meta))
            pipe.execute()
    except redis.RedisError:
        # Diagnostic boundary: a Redis outage or optimistic-lock conflict must
        # not prevent local termination of detached writers. Logs remain the
        # receipt when job metadata cannot be written.
        LOGGER.exception("Could not record directory cleanup job_id=%s execution_id=%s state=%s",
                         job.id, execution_id, state)


def cleanup_stopped_execution(worker, job: Job) -> None:
    """Retain locks if containment or termination evidence is unavailable."""
    execution_id = worker._directory_lock_execution_id
    problem = worker._directory_lock_containment_error
    if problem:
        raise RuntimeError(problem)
    if worker.horse_pid:
        raise RuntimeError("RQ has not reaped the workhorse; termination is unknown")
    record_cleanup(job, execution_id, "terminating_writers")
    terminate_adopted_writers(worker.heartbeat, worker.job_monitoring_interval,
                             worker._directory_lock_protected_children)
    cleared = release_execution_locks(job.id, execution_id)
    record_cleanup(job, execution_id, "complete", cleared_keys=cleared)
