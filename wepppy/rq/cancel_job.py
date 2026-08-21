from __future__ import annotations

"""Utilities for canceling RQ jobs (and their dependency tree) from workers or CLIs."""

import json
import os
from pathlib import Path
from typing import Dict

import redis
from redis.exceptions import WatchError
from rq import Queue
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)
from wepppy.rq.weppcloudr_backends import (
    BackendError,
    HttpRenderControlPlaneClient,
)

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)
_FORK_ARCHIVE_STARTED_FORBIDDEN = {
    "error": "Started fork/archive jobs require Admin or Root",
    "code": "forbidden",
}
_WEPPCLOUDR_TASK = "wepppy.rq.weppcloudr_rq.render_deval_details_rq"


def _cancel_kubernetes_render(job: Job) -> Dict[str, str] | None:
    """Persist render cancellation before allowing the RQ workhorse to stop."""
    if job.func_name != _WEPPCLOUDR_TASK or job.kwargs.get("backend") != "kubernetes-job":
        return None
    request_digest = job.meta.get("render_request_digest")
    if not isinstance(request_digest, str):
        return {
            "error": "Kubernetes render cancellation state is not yet durable",
            "code": "cleanup_pending",
        }
    endpoint = job.kwargs.get("control_plane_url") or os.getenv(
        "WEPPCLOUDR_K8S_CONTROL_PLANE_URL"
    )
    token_file = job.kwargs.get("control_plane_token_file") or os.getenv(
        "WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE"
    )
    if not isinstance(endpoint, str) or not isinstance(token_file, str):
        return {
            "error": "Kubernetes render cancellation control plane is unavailable",
            "code": "cleanup_pending",
        }
    job.meta["cancel_requested"] = True
    job.meta["render_cleanup_state"] = "deleting"
    job.save_meta()
    try:
        receipt = HttpRenderControlPlaneClient(endpoint, Path(token_file)).cancel(
            job.id, request_digest
        )
    except (BackendError, OSError) as exc:
        job.meta["render_cleanup_state"] = "cleanup_timeout"
        job.save_meta()
        return {"error": str(exc), "code": "cleanup_timeout"}
    if receipt.get("rq_job_id") != job.id or receipt.get("request_digest") != request_digest:
        job.meta["render_cleanup_state"] = "cleanup_timeout"
        job.save_meta()
        return {
            "error": "Kubernetes render cancellation receipt identity mismatch",
            "code": "cleanup_timeout",
        }
    cleanup_state = receipt.get("cleanup_state")
    if cleanup_state not in {"deleting", "complete", "cleanup_timeout"}:
        job.meta["render_cleanup_state"] = "cleanup_timeout"
        job.save_meta()
        return {
            "error": "Kubernetes render controller returned invalid cleanup state",
            "code": "cleanup_timeout",
        }
    job.meta["render_cleanup_state"] = cleanup_state
    job.save_meta()
    if cleanup_state == "complete":
        return None
    if cleanup_state == "deleting":
        return {"status": "accepted", "code": "cleanup_pending"}
    return {
        "error": "Kubernetes render cleanup exceeded its grace period",
        "code": "cleanup_timeout",
    }


def _cancel_job_recursive_unlocked(job: Job, redis_conn: redis.Redis) -> None:
    try:
        if job.get_status() == "started":
            send_stop_job_command(redis_conn, job.id)
        else:
            job.cancel()
    except (NoSuchJobError, InvalidJobOperation):
        # Dispatch parents normally finish before their children. A benign
        # terminal-parent error must not prevent descendant cancellation.
        pass

    for key, child_job_id in job.meta.items():
        if not key.startswith("jobs:"):
            continue
        try:
            child_job = Job.fetch(child_job_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        _cancel_job_recursive_unlocked(child_job, redis_conn)


def _cancel_job_recursive(job: Job, redis_conn: redis.Redis) -> None:
    """Cancel a job and its children, synchronizing with child dispatch."""
    dispatch_lock_key = job.meta.get("child_dispatch_lock_key")
    if not dispatch_lock_key:
        _cancel_job_recursive_unlocked(job, redis_conn)
        return

    with redis_conn.lock(str(dispatch_lock_key), timeout=30, blocking_timeout=30):
        job.meta["cancel_requested"] = True
        job.save_meta()
        _cancel_job_recursive_unlocked(job, redis_conn)


def _cancel_queued_fork_archive(job: Job, redis_conn: redis.Redis) -> Dict[str, str]:
    """Cancel only if ``job`` remains in the queue at transaction commit."""
    queue = Queue(
        job.origin,
        connection=redis_conn,
        job_class=job.__class__,
        serializer=job.serializer,
    )
    with redis_conn.pipeline() as pipe:
        try:
            pipe.watch(queue.key)
            if pipe.lpos(queue.key, job.id) is None:
                return dict(_FORK_ARCHIVE_STARTED_FORBIDDEN)
            pipe.multi()
            job.cancel(pipeline=pipe)
            pipe.execute()
        except (WatchError, InvalidJobOperation):
            return dict(_FORK_ARCHIVE_STARTED_FORBIDDEN)
    return {"status": "ok"}


def cancel_jobs(job_id: str, *, allow_started_fork_archive: bool = True) -> Dict[str, str]:
    """Cancel a job tree rooted at ``job_id``.

    Args:
        job_id: Identifier of the job to cancel.
        allow_started_fork_archive: Whether the caller may stop an already
            dispatched ``fork-archive`` job. When false, cancellation fails
            closed unless the job remains queued.

    Returns:
        Status dictionary reporting success or any lookup error.
    """

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    with redis.Redis(**conn_kwargs) as redis_conn:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            return {"error": "Job not found"}

        if job.origin == "fork-archive" and not allow_started_fork_archive:
            if job.get_status() != "queued":
                return dict(_FORK_ARCHIVE_STARTED_FORBIDDEN)
            return _cancel_queued_fork_archive(job, redis_conn)

        render_cancellation = _cancel_kubernetes_render(job)
        if render_cancellation is not None:
            return render_cancellation

        _cancel_job_recursive(job, redis_conn)
        return {"status": "ok"}
    
    
if __name__ == "__main__":
    import sys
    from pprint import pprint

    if not sys.argv[-1].endswith('.py'):
        job_id = str(sys.argv[-1])
        job_info = cancel_jobs(job_id)
        print(json.dumps(job_info, indent=2))
