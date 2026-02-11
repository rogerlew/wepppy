from __future__ import annotations

import logging
import os
import re

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.rq.batch_rq import _active_batch_job_summaries, delete_batch_rq, run_batch_rq

from .auth import AuthError, require_jwt, require_roles
from .responses import error_response, error_response_with_traceback, validation_error_response

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
_BATCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,127}$")
_BATCH_RESERVED_NAMES = {"_base", "resources", "logs"}


def _validate_batch_name(batch_name: str) -> str:
    name = (batch_name or "").strip()
    if not name:
        raise ValueError("Batch name is required.")
    if not _BATCH_NAME_RE.fullmatch(name):
        raise ValueError(
            "Batch name must start with an alphanumeric character and contain only "
            "letters, numbers, underscores, or hyphens (minimum 3 characters)."
        )
    if name in _BATCH_RESERVED_NAMES:
        raise ValueError("Batch name cannot be a reserved directory name.")
    return name


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


@router.post("/batch/_/{batch_name}/delete-batch")
def delete_batch(batch_name: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=["rq:enqueue"])
        require_roles(claims, ["admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine delete-batch auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        batch_name = _validate_batch_name(batch_name)
    except ValueError as exc:
        return validation_error_response(
            [
                {
                    "code": "invalid_batch_name",
                    "message": str(exc),
                    "path": "batch_name",
                }
            ]
        )

    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            active_jobs = _active_batch_job_summaries(batch_name, redis_conn=redis_conn)
            if active_jobs:
                visible_jobs = active_jobs[:5]
                hidden_count = max(0, len(active_jobs) - len(visible_jobs))
                detail = "Active jobs: " + ", ".join(visible_jobs)
                if hidden_count:
                    detail += f" (+{hidden_count} more)"
                return error_response(
                    f"Batch cannot be deleted while jobs are active. {detail}",
                    status_code=409,
                    code="batch_busy",
                    details=detail,
                )

            q = Queue("batch", connection=redis_conn)
            job = q.enqueue_call(delete_batch_rq, (batch_name,), timeout=RQ_TIMEOUT)
    except Exception:
        logger.exception("rq-engine delete-batch enqueue failed")
        return error_response_with_traceback("Failed to enqueue batch delete")

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        batch_runner.set_rq_job_id("delete_batch_rq", job.id)
    except FileNotFoundError:
        # A missing batch is a no-op at worker time; job remains valid and idempotent.
        pass
    except Exception:
        logger.warning("rq-engine delete-batch: failed to persist job id", exc_info=True)

    return JSONResponse(
        {
            "job_id": job.id,
            "message": "Batch delete submitted.",
        },
        status_code=202,
    )


__all__ = ["router"]
