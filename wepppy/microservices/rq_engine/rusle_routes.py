from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import build_rusle_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


@router.post(
    "/runs/{runid}/{config}/build-rusle",
    summary="Build RUSLE factors and final A output",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via "
        "`authorize_run_access`. Asynchronously enqueues RUSLE build execution."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_rusle"),
    responses=agent_route_responses(
        success_code=200,
        success_description="RUSLE job accepted and `job_id` returned.",
    ),
)
async def build_rusle(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine build-rusle auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        payload = await parse_request_payload(
            request,
            boolean_fields=("force_polaris_refresh",),
        )
        allowed_keys = (
            "r_mode",
            "c_mode",
            "rap_year",
            "rock_fraction_of_rap_bare",
            "k_modes",
            "default_k_mode",
            "max_slope_length_m",
            "p_value",
            "force_polaris_refresh",
        )
        job_payload: dict[str, Any] = {}
        for key in allowed_keys:
            if key in payload:
                job_payload[key] = payload[key]

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_rusle)

        job_kwargs = {"payload": job_payload} if job_payload else None
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                build_rusle_rq,
                (runid,),
                kwargs=job_kwargs,
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("build_rusle_rq", job.id)

        response_payload: dict[str, Any] = {"job_id": job.id}
        if job_payload:
            response_payload["payload"] = job_payload
        return JSONResponse(response_payload)
    except Exception:
        logger.exception("rq-engine build-rusle enqueue failed")
        return error_response_with_traceback("Error Building RUSLE")


__all__ = ["router"]
