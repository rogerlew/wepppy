from __future__ import annotations

import logging
import os

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import (
    Climate,
    ClimateModeIsUndefinedError,
    NoClimateStationSelectedError,
    WatershedNotAbstractedError,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import build_climate_rq
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


@router.post(
    "/runs/{runid}/{config}/build-climate",
    summary="Build climate inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates climate inputs and, outside batch mode, asynchronously enqueues climate building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_climate"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Climate inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Climate input validation or climate precondition failed. Returns the canonical error payload.",
        },
    ),
)
async def build_climate(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-climate auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    wd = get_wd(runid)

    try:
        _require_directory_root(wd, "climate")
        climate = Climate.getInstance(wd)
        payload = await parse_request_payload(request)
        climate.parse_inputs(payload)
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        # API boundary: translate unexpected parse failures into canonical error payload.
        logger.exception("rq-engine build-climate payload parse failed", extra={"runid": runid, "config": config})
        return error_response_with_traceback("Error parsing climate inputs", status_code=400)

    if climate.run_group == "batch":
        return JSONResponse({"message": "Set climate inputs for batch processing"})

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_climate)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_climate_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("build_climate_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except (
        NoClimateStationSelectedError,
        ClimateModeIsUndefinedError,
        WatershedNotAbstractedError,
    ) as exc:
        return error_response(
            exc.__name__ or "Error building climate",
            status_code=400,
        )
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-climate enqueue failed")
        return error_response_with_traceback("Error building climate")


__all__ = ["router"]
