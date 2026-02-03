from __future__ import annotations

import inspect

import redis
from rq import Queue, get_current_job
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs, redis_host
from wepppy.nodb.core import Wepp
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)
TIMEOUT: int = 43_200


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

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
    except Exception:
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
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
