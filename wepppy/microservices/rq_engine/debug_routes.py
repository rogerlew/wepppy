from __future__ import annotations

import logging

import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from rq import Callback, Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

from .responses import error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

TIMEOUT = 216_000


def hello_world_rq(runid: str) -> None:
    logger.info("hello_world_rq: %s", runid)


def report_success(job, connection, result, *args, **kwargs):
    logger.info("Job %s completed successfully", job.id)
    return result


def report_failure(job, connection, exc_type, value, traceback):
    logger.warning("Job %s failed", job.id)
    return traceback


def report_stopped(job, connection):
    logger.warning("Job %s stopped", job.id)
    return job.exc_info


@router.get("/runs/{runid}/{config}/hello-world")
@router.post("/runs/{runid}/{config}/hello-world")
def hello_world(runid: str, config: str) -> JSONResponse:
    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("m4", connection=redis_conn)
            job = q.enqueue_call(
                hello_world_rq,
                (runid,),
                timeout=TIMEOUT,
                on_success=Callback(report_success),
                on_failure=Callback(report_failure, timeout=10),
                on_stopped=Callback(report_stopped, timeout="2m"),
            )
    except Exception:
        logger.exception("rq-engine hello-world failed")
        return error_response_with_traceback(
            "hello-world failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        {"job_id": job.id, "exc_info": job.exc_info, "is_failed": job.is_failed},
        status_code=status.HTTP_200_OK,
    )


__all__ = ["router"]
