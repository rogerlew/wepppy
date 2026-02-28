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
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import run_debris_flow_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _maybe_nodir_error_response(exc: Exception):
    if isinstance(exc, NoDirError):
        return error_response(exc.message, status_code=exc.http_status, code=exc.code)
    return None


def nodir_resolve(_wd: str, _root: str, *, view: str = "effective") -> None:
    return _nodir_resolve(_wd, _root, view=view)


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _first_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        for candidate in value:
            if candidate not in (None, ""):
                return candidate
        return None
    return value


def _preflight_debris_flow_roots(wd: str) -> None:
    _require_directory_root(wd, "watershed")
    _require_directory_root(wd, "soils")


@router.post(
    "/runs/{runid}/{config}/run-debris-flow",
    summary="Run debris-flow analysis",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates debris-flow payload fields and asynchronously enqueues debris-flow processing."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("run_debris_flow"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Debris-flow job accepted and `job_id` returned.",
        extra={
            400: "Debris-flow payload validation failed. Returns the canonical error payload.",
        },
    ),
)
async def run_debris_flow(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine run-debris-flow auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _preflight_debris_flow_roots(wd)

        payload = await parse_request_payload(request)

        clay_pct = _first_value(payload.get("clay_pct"))
        liquid_limit = _first_value(payload.get("liquid_limit"))
        datasource = _first_value(payload.get("datasource"))

        if clay_pct is not None:
            try:
                clay_pct = float(clay_pct)
            except (TypeError, ValueError):
                return error_response("clay_pct must be numeric", status_code=400)

        if liquid_limit is not None:
            try:
                liquid_limit = float(liquid_limit)
            except (TypeError, ValueError):
                return error_response("liquid_limit must be numeric", status_code=400)

        if datasource is not None:
            datasource = str(datasource).strip() or None

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_debris)

        job_kwargs = None
        if any(value is not None for value in (clay_pct, liquid_limit, datasource)):
            job_options: dict[str, Any] = {}
            if clay_pct is not None:
                job_options["clay_pct"] = clay_pct
            if liquid_limit is not None:
                job_options["liquid_limit"] = liquid_limit
            if datasource is not None:
                job_options["datasource"] = datasource
            job_kwargs = {"payload": job_options}

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_debris_flow_rq,
                (runid,),
                kwargs=job_kwargs,
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("run_debris_flow_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine run-debris-flow enqueue failed")
        return error_response_with_traceback("Error Running Debris Flow")


__all__ = ["router"]
