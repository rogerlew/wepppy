from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.rq.project_rq import fetch_and_analyze_rap_ts_rq
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _normalize_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        result = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [token for token in (tok.strip() for tok in stripped.split(",")) if token]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item is not None and str(item).strip()]
        if parsed is None:
            return []
        return [str(parsed).strip()]
    return [str(value).strip()]


def _normalize_schedule(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("Schedule payload must be valid JSON.") from exc
        return parsed
    raise ValueError("Schedule payload must be a list, object, or JSON string.")


@router.post(
    "/runs/{runid}/{config}/acquire-rap-ts",
    summary="Enqueue RAP time-series acquisition",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates RAP dataset/schedule inputs and asynchronously enqueues RAP acquisition/analysis."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("acquire_rap_ts"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Job accepted and `job_id` returned.",
        extra={
            400: "Input validation failed (for example invalid RAP schedule payload). Returns the canonical error payload.",
        },
    ),
)
async def acquire_rap_ts(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine acquire-rap-ts auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        raw_json = None
        try:
            raw_json = await request.json()
        except (UnicodeDecodeError, ValueError, RuntimeError):
            raw_json = None

        payload = await parse_request_payload(
            request,
            boolean_fields=("force_refresh",),
        )

        raw_datasets = payload.get("datasets")
        if isinstance(raw_json, dict) and raw_json.get("datasets") is not None:
            raw_datasets = raw_json.get("datasets")
        raw_schedule = payload.get("schedule")
        if isinstance(raw_json, dict) and raw_json.get("schedule") is not None:
            raw_schedule = raw_json.get("schedule")
        raw_force_refresh = payload.get("force_refresh")

        datasets = _normalize_string_list(raw_datasets)
        schedule = None
        if raw_schedule is not None:
            try:
                schedule = _normalize_schedule(raw_schedule)
            except ValueError as exc:
                return error_response(str(exc), status_code=400)

        force_refresh = None
        if raw_force_refresh is not None:
            force_refresh = bool(raw_force_refresh)

        job_payload: dict[str, Any] = {}
        if datasets:
            job_payload["datasets"] = datasets
        if schedule not in (None, [], {}):
            job_payload["schedule"] = schedule
        if force_refresh is not None:
            job_payload["force_refresh"] = force_refresh

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_rap_ts)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                fetch_and_analyze_rap_ts_rq,
                (runid,),
                kwargs={"payload": job_payload} if job_payload else {},
                timeout=RQ_TIMEOUT,
            )
            prep.set_rq_job_id("fetch_and_analyze_rap_ts_rq", job.id)
    except Exception:
        logger.exception("rq-engine acquire-rap-ts enqueue failed")
        return error_response_with_traceback("Error Running RAP_TS")

    response_payload: dict[str, Any] = {"job_id": job.id}
    if job_payload:
        response_payload["payload"] = job_payload
    return JSONResponse(response_payload)


__all__ = ["router"]
