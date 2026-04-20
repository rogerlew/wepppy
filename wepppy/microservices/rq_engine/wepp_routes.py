from __future__ import annotations

import logging
import os
import time
import uuid

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.wepp_rq import (
    WeppSingleFlightConflict,
    acquire_wepp_submit_lock,
    ensure_no_active_wepp_job,
    prep_wepp_watershed_rq,
    release_wepp_submit_lock,
    run_wepp_rq,
    run_wepp_watershed_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback
from .wepp_run_payload import (
    WEPP_BOOLEAN_FIELDS,
    WeppRunPayloadValidationError,
    apply_wepp_run_payload,
)

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _persist_wepp_job_hint(wepp: Wepp, *, job_id: str, job_key: str) -> None:
    """Persist a last-known WEPP controller job hint without failing enqueue."""
    try:
        wepp.job_id = job_id
        wepp.job_key = job_key
    except RuntimeError:
        # Boundary catch: enqueue already succeeded; keep response stable even
        # if NoDb hint persistence fails.
        logger.exception("rq-engine run-wepp failed to persist NoDb WEPP job hint")


def _is_base_project_context(runid: str, config: str) -> bool:
    runid_leaf = runid.split(";;")[-1].strip().lower() if runid else ""
    config_token = str(config).strip().lower() if config is not None else ""
    return runid_leaf == "_base" or config_token == "_base"


async def _handle_run_wepp_request(
    runid: str,
    config: str,
    request: Request,
    *,
    job_fn,
    job_key: str,
) -> JSONResponse:
    try:
        wd = get_wd(runid)
    except ValueError as exc:
        return error_response(str(exc), status_code=400)

    payload = await parse_request_payload(request, boolean_fields=WEPP_BOOLEAN_FIELDS)
    try:
        wepp = apply_wepp_run_payload(
            wd,
            payload,
            wepp_cls=Wepp,
            soils_cls=Soils,
            watershed_cls=Watershed,
            ron_cls=Ron,
        )
    except WeppRunPayloadValidationError as exc:
        return error_response(
            str(exc),
            status_code=400,
            code=exc.code,
            details=exc.details,
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except RuntimeError:
        logger.exception("rq-engine run-wepp parse failed")
        return error_response_with_traceback("Error preparing WEPP run request")

    if getattr(wepp, "run_group", "") == "batch" or _is_base_project_context(runid, config):
        return JSONResponse({"message": "Set wepp inputs for batch processing"})

    try:
        prep = RedisPrep.getInstance(wd)
        submit_owner = f"{job_key}:{int(time.time() * 1000)}:{uuid.uuid4().hex}"
        if not acquire_wepp_submit_lock(runid, submit_owner):
            raise WeppSingleFlightConflict("WEPP enqueue already in progress for this run.")

        job = None
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        try:
            with redis.Redis(**conn_kwargs) as redis_conn:
                ensure_no_active_wepp_job(runid, prep, redis_conn)
                prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)
                prep.remove_timestamp(TaskEnum.run_wepp_watershed)
                prep.remove_timestamp(TaskEnum.run_omni_scenarios)
                prep.remove_timestamp(TaskEnum.run_path_cost_effective)
                q = Queue(connection=redis_conn)
                job = q.enqueue_call(job_fn, (runid,), timeout=RQ_TIMEOUT)
                prep.set_rq_job_id(job_key, job.id)
                _persist_wepp_job_hint(wepp, job_id=str(job.id), job_key=job_key)
        finally:
            try:
                release_wepp_submit_lock(runid, submit_owner)
            except (redis.RedisError, RuntimeError):
                if job is None:
                    raise
                logger.exception("rq-engine run-wepp submit-lock release failed after enqueue")
        if job is None:
            raise RuntimeError("WEPP enqueue returned no job object")
        return JSONResponse({"job_id": job.id})
    except WeppSingleFlightConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except redis.RedisError:
        logger.exception("rq-engine run-wepp enqueue failed")
        return error_response_with_traceback("Error Handling Request")
    except RuntimeError:
        logger.exception("rq-engine run-wepp enqueue failed")
        return error_response_with_traceback("Error Handling Request")


@router.post(
    "/runs/{runid}/{config}/run-wepp",
    summary="Run WEPP hillslope workflow",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/soil/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues hillslope WEPP."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_wepp"),
    responses=agent_route_responses(
        success_code=200,
        success_description="WEPP inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
            409: "WEPP single-flight lock contention; another WEPP job is already active.",
        },
    ),
)
async def run_wepp(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (redis.RedisError, RuntimeError):
        logger.exception("rq-engine run-wepp auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=run_wepp_rq,
        job_key="run_wepp_rq",
    )


@router.post(
    "/runs/{runid}/{config}/run-wepp-watershed",
    summary="Run WEPP watershed workflow",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues watershed WEPP."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_wepp_watershed"),
    responses=agent_route_responses(
        success_code=200,
        success_description=(
            "WEPP watershed inputs accepted; returns batch update message or enqueued `job_id`."
        ),
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
            409: "WEPP single-flight lock contention; another WEPP job is already active.",
        },
    ),
)
async def run_wepp_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (redis.RedisError, RuntimeError):
        logger.exception("rq-engine run-wepp-watershed auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=run_wepp_watershed_rq,
        job_key="run_wepp_watershed_rq",
    )


@router.post(
    "/runs/{runid}/{config}/prep-wepp-watershed",
    summary="Prepare WEPP hillslope and watershed inputs only",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates WEPP/soil/watershed run options from payload and, outside batch mode, "
        "asynchronously enqueues prep-only hillslope + watershed input generation."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("prep_wepp_watershed"),
    responses=agent_route_responses(
        success_code=200,
        success_description=(
            "WEPP prep-only inputs accepted; returns batch update message or enqueued `job_id`."
        ),
        extra={
            400: "WEPP payload validation failed. Returns the canonical error payload.",
            409: "WEPP single-flight lock contention; another WEPP job is already active.",
        },
    ),
)
async def prep_wepp_watershed(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (redis.RedisError, RuntimeError):
        logger.exception("rq-engine prep-wepp-watershed auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    return await _handle_run_wepp_request(
        runid,
        config,
        request,
        job_fn=prep_wepp_watershed_rq,
        job_key="prep_wepp_watershed_rq",
    )


__all__ = ["router"]
