from __future__ import annotations

import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Soils, WatershedNotAbstractedError
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as _nodir_resolve
from wepppy.rq.project_rq import build_soils_rq
from wepppy.soils.ssurgo import NoValidSoilsException
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


def _to_float(value: Any) -> float:
    if value is None:
        raise ValueError("missing")
    if isinstance(value, (list, tuple)):
        if not value:
            raise ValueError("missing")
        return _to_float(value[0])
    return float(value)


@router.post(
    "/runs/{runid}/{config}/build-soils",
    summary="Build soils inputs",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Mutates soils settings and, outside batch mode, asynchronously enqueues soils building."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("build_soils"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Soils inputs accepted; returns batch update message or enqueued `job_id`.",
        extra={
            400: "Soils validation or precondition failed. Returns the canonical error payload.",
        },
    ),
)
async def build_soils(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: boundary contract
        logger.exception("rq-engine build-soils auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        _require_directory_root(wd, "soils")

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_soils)

        payload = await parse_request_payload(request)
        try:
            initial_sat = _to_float(payload.get("initial_sat"))
        except (TypeError, ValueError):
            return error_response("initial_sat must be numeric", status_code=400)

        soils = Soils.getInstance(wd)
        soils.initial_sat = initial_sat

        if "disturbed" in soils.mods:
            disturbed = Disturbed.getInstance(wd)
            try:
                disturbed.sol_ver = _to_float(payload.get("sol_ver"))
            except (TypeError, ValueError):
                return error_response("sol_ver must be numeric", status_code=400)

        if soils.run_group == "batch":
            return JSONResponse({"message": "Set soils inputs for batch processing"})

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_soils_rq, (runid,), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("build_soils_rq", job.id)
        return JSONResponse({"job_id": job.id})
    except (NoValidSoilsException, WatershedNotAbstractedError) as exc:
        return error_response(
            exc.__name__ or "Building Soil Failed",
            status_code=400,
        )
    except Exception as exc:  # broad-except: boundary contract
        nodir_response = _maybe_nodir_error_response(exc)
        if nodir_response is not None:
            return nodir_response
        logger.exception("rq-engine build-soils enqueue failed")
        return error_response_with_traceback("Building Soil Failed")


__all__ = ["router"]
