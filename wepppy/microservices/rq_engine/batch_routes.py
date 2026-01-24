from __future__ import annotations

import logging
import os

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.rq.batch_rq import run_batch_rq

from .auth import AuthError, require_jwt, require_roles
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))


@router.post("/batch/_/{batch_name}/run-batch")
def run_batch(batch_name: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=["rq:enqueue"])
        require_roles(claims, ["admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-batch auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return error_response(str(exc), status_code=404)

    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(run_batch_rq, (batch_name,), timeout=RQ_TIMEOUT)
    except Exception:
        logger.exception("rq-engine run-batch enqueue failed")
        return error_response_with_traceback("Failed to enqueue batch run")

    try:
        batch_runner.set_rq_job_id("run_batch_rq", job.id)
    except Exception:
        logger.warning("rq-engine run-batch: failed to persist job id", exc_info=True)

    return JSONResponse(
        {
            "job_id": job.id,
            "message": "Batch run submitted.",
        }
    )


__all__ = ["router"]
