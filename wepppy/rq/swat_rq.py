from __future__ import annotations

import inspect

import redis
from rq import Queue, get_current_job
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs, redis_host
from wepppy.nodb.core import Wepp
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.bootstrap.git_lock import acquire_bootstrap_git_lock, release_bootstrap_git_lock
from wepppy.weppcloud.utils.helpers import get_wd

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)
TIMEOUT: int = 43_200


def _bootstrap_autocommit_actor(job: Job | None) -> str:
    job_id = str(getattr(job, "id", "") or "").strip()
    if job_id:
        return f"rq:{job_id}:swat:auto_commit"
    return "rq:unknown:swat:auto_commit"


def _bootstrap_autocommit_with_lock(runid: str, wepp: Wepp, stage: str, *, actor: str) -> str | None:
    conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    with redis.Redis(**conn_kwargs) as redis_conn:
        lock = acquire_bootstrap_git_lock(
            redis_conn,
            runid=runid,
            operation="auto_commit",
            actor=actor,
        )
        if lock is None:
            wepp.logger.warning("Skipped bootstrap auto-commit for %s: bootstrap lock busy", stage)
            return None
        try:
            return wepp.bootstrap_commit_inputs(stage)
        finally:
            release_bootstrap_git_lock(redis_conn, runid=runid, token=lock.token)


@with_exception_logging
def run_swat_rq(runid: str) -> Job:
    """Enqueue SWAT+ input build + execution using existing WEPP outputs."""
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:swat"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if wepp.islocked():
            raise Exception(f"{runid} is locked")

        wepp.ensure_bootstrap_main()

        if not wepp.mods or "swat" not in wepp.mods:
            raise Exception("SWAT mod is not enabled for this run")

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)

            job_build = q.enqueue_call(_build_swat_inputs_rq, (runid,), timeout=TIMEOUT)
            job.meta["jobs:0,func:_build_swat_inputs_rq"] = job_build.id
            job.save()

            job_run = q.enqueue_call(
                _run_swat_rq,
                (runid,),
                timeout=TIMEOUT,
                depends_on=job_build,
            )
            job.meta["jobs:1,func:_run_swat_rq"] = job_run.id
            job.save()

        StatusMessenger.publish(
            status_channel,
            f"rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job_run.id}",
        )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/swat_rq.py:87", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise

    return job_run


@with_exception_logging
def run_swat_noprep_rq(runid: str) -> Job:
    """Enqueue SWAT+ execution using existing TxtInOut inputs (no prep)."""
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:swat"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if wepp.islocked():
            raise Exception(f"{runid} is locked")

        if not wepp.mods or "swat" not in wepp.mods:
            raise Exception("SWAT mod is not enabled for this run")

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job_run = q.enqueue_call(_run_swat_rq, (runid,), timeout=TIMEOUT)
            job.meta["jobs:0,func:_run_swat_rq"] = job_run.id
            job.save()

        StatusMessenger.publish(
            status_channel,
            f"rq:{job.id} ENQUEUED {func_name}({runid}) -> awaiting final job {job_run.id}",
        )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/swat_rq.py:123", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise

    return job_run


@with_exception_logging
def _build_swat_inputs_rq(runid: str) -> None:
    """Build SWAT+ TxtInOut inputs from WEPP hillslope outputs."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:swat"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        from wepppy.nodb.mods.swat import Swat

        swat = Swat.getInstance(wd)
        swat.build_inputs()
        wepp = Wepp.getInstance(wd)
        _bootstrap_autocommit_with_lock(
            runid,
            wepp,
            "SWAT inputs",
            actor=_bootstrap_autocommit_actor(job),
        )

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(
            status_channel,
            f"rq:{job.id} TRIGGER   swat SWAT_RUN_TASK_COMPLETED",
        )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/swat_rq.py:157", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise


@with_exception_logging
def _run_swat_rq(runid: str) -> None:
    """Execute SWAT+ from the prepared TxtInOut directory."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:swat"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        from wepppy.nodb.mods.swat import Swat

        swat = Swat.getInstance(wd)
        swat.run_swat()

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/swat_rq.py:178", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise


@with_exception_logging
def run_swat_interchange_rq(runid: str) -> None:
    """Generate SWAT interchange parquet outputs for the latest SWAT run."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f"{runid}:swat"
        StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

        from wepppy.nodb.mods.swat import Swat

        swat = Swat.getInstance(wd)
        swat.run_swat_interchange(status_channel=status_channel)

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/swat_rq.py:199", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
