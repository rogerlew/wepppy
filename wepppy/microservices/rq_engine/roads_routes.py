from __future__ import annotations

import logging
import os
import time

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.roads_rq import (
    RoadsSingleFlightConflict,
    acquire_roads_submit_lock,
    ensure_no_active_roads_job,
    release_roads_submit_lock,
    run_roads_prepare_rq,
    run_roads_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _enqueue_roads_job(runid: str, *, func, prep_key: str) -> str:
    wd = get_wd(runid)
    prep = RedisPrep.getInstance(wd)

    submit_owner = f"{prep_key}:{int(time.time() * 1000)}"
    if not acquire_roads_submit_lock(runid, submit_owner):
        raise RoadsSingleFlightConflict("Roads enqueue already in progress for this run.")

    try:
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            ensure_no_active_roads_job(runid, prep, redis_conn)
            prep.remove_timestamp(TaskEnum.run_roads)
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(
                func,
                (runid,),
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id(prep_key, job.id)
        return str(job.id)
    finally:
        release_roads_submit_lock(runid, submit_owner)


@router.post(
    "/runs/{runid}/{config}/prepare-roads",
    summary="Prepare Roads monotonic segments and low-point mapping",
    description=(
        "Requires JWT bearer auth with `rq:enqueue` scope and run access. "
        "Enqueues the Roads prepare worker and returns an RQ `job_id`."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("prepare_roads"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Roads prepare job accepted and `job_id` returned.",
        extra={
            409: "Roads single-flight lock contention; another Roads job is already active.",
        },
    ),
)
async def prepare_roads(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine prepare-roads auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        job_id = _enqueue_roads_job(runid, func=run_roads_prepare_rq, prep_key="run_roads_prepare_rq")
        return JSONResponse({"job_id": job_id}, status_code=202)
    except RoadsSingleFlightConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except Exception:
        logger.exception("rq-engine prepare-roads enqueue failed")
        return error_response_with_traceback("Error Preparing Roads")


@router.post(
    "/runs/{runid}/{config}/run-roads",
    summary="Execute Roads WEPP run and watershed reroute integration",
    description=(
        "Requires JWT bearer auth with `rq:enqueue` scope and run access. "
        "Enqueues the Roads run worker and returns an RQ `job_id`."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_roads"),
    responses=agent_route_responses(
        success_code=202,
        success_description="Roads run job accepted and `job_id` returned.",
        extra={
            409: "Roads single-flight lock contention; another Roads job is already active.",
        },
    ),
)
async def run_roads(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine run-roads auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        job_id = _enqueue_roads_job(runid, func=run_roads_rq, prep_key="run_roads_rq")
        return JSONResponse({"job_id": job_id}, status_code=202)
    except RoadsSingleFlightConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except Exception:
        logger.exception("rq-engine run-roads enqueue failed")
        return error_response_with_traceback("Error Running Roads")


__all__ = ["router"]
