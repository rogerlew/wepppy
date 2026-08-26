from __future__ import annotations

import os
from typing import Any

import redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.rq.wepp_rq import bootstrap_enable_rq
from wepppy.rq.job_dependencies import reconcile_deferred_workflow
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import RqEnqueueVerificationError, recover_committed_enqueue
from wepppy.weppcloud.utils.helpers import get_wd

from .git_lock import (
    BOOTSTRAP_ENABLE_JOB_TTL_SECONDS,
    BOOTSTRAP_GIT_LOCK_TTL_SECONDS,
    acquire_bootstrap_git_lock,
    get_bootstrap_enable_job_id,
    release_bootstrap_git_lock,
    set_bootstrap_enable_job_id,
)

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))


class BootstrapLockBusyError(RuntimeError):
    """Raised when a run-scoped bootstrap git lock is already held."""


def _bootstrap_enable_lock_ttl_seconds() -> int:
    # Keep the enable lock alive for at least the configured job timeout.
    return max(BOOTSTRAP_GIT_LOCK_TTL_SECONDS, RQ_TIMEOUT + 300)


def _bootstrap_enable_job_ttl_seconds() -> int:
    # Keep the dedupe key aligned with the max expected job lifetime.
    return max(BOOTSTRAP_ENABLE_JOB_TTL_SECONDS, RQ_TIMEOUT + 300)


def enqueue_bootstrap_enable(runid: str, *, actor: str) -> tuple[dict[str, Any], int]:
    wd = get_wd(runid, prefer_active=False)
    wepp = Wepp.getInstance(wd)
    if wepp.bootstrap_enabled:
        return {"enabled": True, "message": "Bootstrap already enabled."}, 200

    lock_conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    rq_conn_kwargs = redis_connection_kwargs(RedisDB.RQ)

    with redis.Redis(**lock_conn_kwargs) as lock_conn, redis.Redis(**rq_conn_kwargs) as rq_conn:
        active_job_id = get_bootstrap_enable_job_id(lock_conn, runid)
        if active_job_id:
            prior_lock_token = None
            try:
                prior_job = Job.fetch(active_job_id, connection=rq_conn)
                prior_lock_token = dict(prior_job.kwargs or {}).get("lock_token")
            except NoSuchJobError:
                pass
            result = reconcile_deferred_workflow(
                active_job_id,
                connection=rq_conn,
                association=lambda candidate: (
                    str(candidate.func_name)
                    == f"{bootstrap_enable_rq.__module__}.{bootstrap_enable_rq.__qualname__}"
                    and str(candidate.origin) == "default"
                    and tuple(candidate.args or ())[:1] == (runid,)
                ),
                root_association=lambda candidate: (
                    str(candidate.func_name)
                    == f"{bootstrap_enable_rq.__module__}.{bootstrap_enable_rq.__qualname__}"
                    and str(candidate.origin) == "default"
                    and tuple(candidate.args or ())[:1] == (runid,)
                ),
            )
            if result.state in {"active", "mismatch"}:
                return (
                    {
                        "enabled": False,
                        "queued": True,
                        "job_id": active_job_id,
                        "message": "Bootstrap enable job already active.",
                    },
                    202,
                )
            if result.state in {"canceled", "terminal"} and prior_lock_token:
                release_bootstrap_git_lock(
                    lock_conn, runid=runid, token=str(prior_lock_token)
                )
            elif result.state in {"missing", "terminal"}:
                # New enable submissions use their planned job ID as the
                # opaque lock token. This compare-and-delete clears only the
                # lock correlated with the stale receipt; a newer owner wins.
                release_bootstrap_git_lock(
                    lock_conn, runid=runid, token=active_job_id
                )

        job_id = new_rq_job_id()
        lock = acquire_bootstrap_git_lock(
            lock_conn,
            runid=runid,
            operation="enable",
            actor=actor,
            ttl_seconds=_bootstrap_enable_lock_ttl_seconds(),
            token=job_id,
        )
        if lock is None:
            raise BootstrapLockBusyError("bootstrap lock busy")

        try:
            set_bootstrap_enable_job_id(
                lock_conn,
                runid=runid,
                job_id=job_id,
                ttl_seconds=_bootstrap_enable_job_ttl_seconds(),
            )
            q = Queue(connection=rq_conn)
            try:
                job = q.enqueue_call(
                    bootstrap_enable_rq,
                    args=(runid,),
                    kwargs={"actor": actor, "lock_token": lock.token},
                    timeout=RQ_TIMEOUT,
                    job_id=job_id,
                )
            except redis.RedisError:
                job = recover_committed_enqueue(
                    rq_conn, job_id, func=bootstrap_enable_rq,
                    runid=runid, origin=str(q.name),
                    args=(runid,), kwargs={"actor": actor, "lock_token": lock.token},
                )
                if job is None:
                    raise
        except RqEnqueueVerificationError:
            raise
        except Exception:
            release_bootstrap_git_lock(lock_conn, runid=runid, token=lock.token)
            raise

    return (
        {
            "enabled": False,
            "queued": True,
            "job_id": job.id,
            "message": "Bootstrap enable job enqueued.",
        },
        202,
    )


__all__ = ["BootstrapLockBusyError", "enqueue_bootstrap_enable"]
