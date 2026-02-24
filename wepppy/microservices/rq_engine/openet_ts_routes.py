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
from wepppy.rq.project_rq import fetch_and_analyze_openet_ts_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt, require_roles
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


@router.post(
    "/runs/{runid}/{config}/acquire-openet-ts",
    summary="Enqueue OpenET time-series acquisition",
    description=(
        "Requires JWT Bearer scope `rq:enqueue`, Admin role, and run access via "
        "`authorize_run_access`. "
        "Asynchronously enqueues OpenET acquisition/analysis for the run."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("acquire_openet_ts"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Job accepted and `job_id` returned.",
    ),
)
async def acquire_openet_ts(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
        require_roles(claims, ["admin"])
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine acquire-openet-ts auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(
            request,
            boolean_fields=("force_refresh",),
        )

        force_refresh = None
        if "force_refresh" in payload:
            force_refresh = bool(payload.get("force_refresh"))

        job_payload: dict[str, Any] = {}
        if force_refresh is not None:
            job_payload["force_refresh"] = force_refresh

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_openet_ts)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                fetch_and_analyze_openet_ts_rq,
                (runid,),
                kwargs={"payload": job_payload} if job_payload else {},
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("fetch_and_analyze_openet_ts_rq", job.id)
    except Exception:
        logger.exception("rq-engine acquire-openet-ts enqueue failed")
        return error_response_with_traceback("Error Running OpenET_TS")

    response_payload: dict[str, Any] = {"job_id": job.id}
    if job_payload:
        response_payload["payload"] = job_payload
    return JSONResponse(response_payload)


__all__ = ["router"]
