from __future__ import annotations

import os
from typing import Any

import redis
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.rq.wepp_rq import bootstrap_enable_rq
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

    with redis.Redis(**lock_conn_kwargs) as lock_conn:
        active_job_id = get_bootstrap_enable_job_id(lock_conn, runid)
        if active_job_id:
            return (
                {
                    "enabled": False,
                    "queued": True,
                    "job_id": active_job_id,
                    "message": "Bootstrap enable job already active.",
                },
                202,
            )

        lock = acquire_bootstrap_git_lock(
            lock_conn,
            runid=runid,
            operation="enable",
            actor=actor,
            ttl_seconds=_bootstrap_enable_lock_ttl_seconds(),
        )
        if lock is None:
            raise BootstrapLockBusyError("bootstrap lock busy")

        try:
            with redis.Redis(**rq_conn_kwargs) as rq_conn:
                q = Queue(connection=rq_conn)
                job = q.enqueue_call(
                    bootstrap_enable_rq,
                    args=(runid,),
                    kwargs={"actor": actor, "lock_token": lock.token},
                    timeout=RQ_TIMEOUT,
                )
            set_bootstrap_enable_job_id(
                lock_conn,
                runid=runid,
                job_id=job.id,
                ttl_seconds=_bootstrap_enable_job_ttl_seconds(),
            )
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
