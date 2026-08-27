"""Authenticated project configuration update routes."""

from __future__ import annotations

from dataclasses import asdict
import logging
import os
from pathlib import Path
from typing import Any, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.project_config_update import (
    ConfigUpdateError,
    ConfigUpdateUnavailableError,
    StaleConfigPreviewError,
    preview_project_config_update,
    project_config_digest_warning,
    project_config_update_enabled,
)
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.project_config_update_rq import (
    CONFIG_UPDATE_ACTIVE_PREFIX,
    run_project_config_update_rq,
)
from wepppy.weppcloud.utils.helpers import get_wd

from .auth import AuthError, authorize_run_access, authorize_run_mutation, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, validation_error_response

__all__ = ["router"]

logger = logging.getLogger(__name__)
router = APIRouter()
_SCOPES = ["rq:enqueue"]
_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
_ACTIVE_TTL = max(_TIMEOUT, 600)


def _authorize(request: Request, runid: str, *, mutation: bool) -> tuple[Mapping[str, Any] | None, JSONResponse | None]:
    try:
        claims = require_jwt(request, required_scopes=_SCOPES)
        authorize_run_access(claims, runid)
        if mutation:
            authorize_run_mutation(claims, runid)
        return claims, None
    except AuthError as exc:
        return None, error_response(exc.message, status_code=exc.status_code, code=exc.code)


def _authority_runid(runid: str) -> str:
    parts = str(runid).split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        return ";;".join(parts[:-2])
    return runid


def _preview(runid: str, config: str):
    result = preview_project_config_update(get_wd(_authority_runid(runid)))
    if Path(result.config_filename).stem != Path(config).stem:
        raise ConfigUpdateUnavailableError("Route config does not identify the project-owned config")
    return result


def _preview_payload(result) -> dict[str, object]:
    return {
        "available": result.available,
        "preview_id": result.preview_id,
        "config_filename": result.config_filename,
        "current_digest": result.current_digest,
        "digest_warning": result.digest_warning,
        "additions": [asdict(item) for item in result.additions],
    }


@router.get(
    "/runs/{runid}/{config}/project-config/update-availability",
    summary="Check project config update availability",
    description="Requires JWT run read access; this is a read-only operation.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_availability"),
    responses=agent_route_responses(success_code=200, success_description="Read-only availability state."),
)
async def update_availability(runid: str, config: str, request: Request) -> JSONResponse:
    _claims, failure = _authorize(request, runid, mutation=False)
    if failure is not None:
        return failure
    authority_wd = get_wd(_authority_runid(runid))
    try:
        digest_warning = project_config_digest_warning(authority_wd)
    except ConfigUpdateError:
        digest_warning = False
    if not project_config_update_enabled():
        return JSONResponse({
            "available": False,
            "preview_id": None,
            "digest_warning": digest_warning,
            "reason": "updates_disabled",
        })
    try:
        preview = _preview(runid, config)
        return JSONResponse({
            "available": preview.available,
            "preview_id": preview.preview_id,
            "digest_warning": preview.digest_warning,
        })
    except ConfigUpdateError:
        return JSONResponse({"available": False, "reason": "config_update_unavailable"})


@router.get(
    "/runs/{runid}/{config}/project-config/update-preview",
    summary="Preview a complete project config update",
    description="Requires JWT owner/Admin/Root authority; this is a read-only operation.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_preview"),
    responses=agent_route_responses(success_code=200, success_description="Complete merge-only preview.", extra={409: "Updates disabled or unavailable."}),
)
async def update_preview(runid: str, config: str, request: Request) -> JSONResponse:
    _claims, failure = _authorize(request, runid, mutation=True)
    if failure is not None:
        return failure
    if not project_config_update_enabled():
        return error_response("Project config updates are disabled.", status_code=409, code="config_update_unavailable")
    try:
        preview = _preview(runid, config)
        if not preview.available:
            return error_response("No project config update is available.", status_code=409, code="config_update_unavailable")
        return JSONResponse(_preview_payload(preview))
    except ConfigUpdateError as exc:
        return error_response(str(exc), status_code=409, code="config_update_unavailable")


def _apply_payload(payload: object) -> tuple[str, str, str]:
    if not isinstance(payload, dict):
        raise ConfigUpdateError("Request must be an object")
    if set(payload) != {"preview_id", "trigger"}:
        raise ConfigUpdateError("Request requires only preview_id and trigger")
    preview_id = payload.get("preview_id")
    trigger = payload.get("trigger")
    if not isinstance(preview_id, str) or not preview_id:
        raise ConfigUpdateError("preview_id is required")
    if not isinstance(trigger, dict) or set(trigger) != {"section", "option"}:
        raise ConfigUpdateError("trigger requires section and option")
    section, option = trigger.get("section"), trigger.get("option")
    if not isinstance(section, str) or not section or not isinstance(option, str) or not option:
        raise ConfigUpdateError("trigger section and option are required")
    return preview_id, section, option


def _enqueue(runid: str, config: str, preview_id: str, section: str, option: str) -> str:
    job_id = new_rq_job_id()
    key = f"{CONFIG_UPDATE_ACTIVE_PREFIX}{runid}"
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        if not redis_conn.set(key, job_id, nx=True, ex=_ACTIVE_TTL):
            raise RuntimeError("config_update_in_progress")
        try:
            job = Queue(connection=redis_conn).enqueue_call(
                run_project_config_update_rq,
                args=(runid, config, preview_id, section, option),
                timeout=_TIMEOUT,
                job_id=job_id,
            )
        except Exception:  # broad-except: boundary contract
            # Queue submission is the boundary: never strand the reservation
            # when RQ rejects a job before it exists.
            redis_conn.delete(key)
            raise
    return str(job.id)


@router.post(
    "/runs/{runid}/{config}/project-config/update-apply",
    summary="Apply a reviewed project config update",
    description="Requires JWT owner/Admin/Root authority and enqueues one asynchronous RQ job.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_apply"),
    responses=agent_route_responses(success_code=202, success_description="Update job accepted.", extra={400: "Invalid request.", 409: "Stale, unavailable, or active update."}),
)
async def update_apply(runid: str, config: str, request: Request) -> JSONResponse:
    _claims, failure = _authorize(request, runid, mutation=True)
    if failure is not None:
        return failure
    if not project_config_update_enabled():
        return error_response("Project config updates are disabled.", status_code=409, code="config_update_unavailable")
    try:
        preview_id, section, option = _apply_payload(await request.json())
    except (ConfigUpdateError, ValueError) as exc:
        return validation_error_response([{"field": "request", "code": "invalid_request", "message": str(exc)}])
    try:
        current = _preview(runid, config)
        if not current.available:
            return error_response("No project config update is available.", status_code=409, code="config_update_unavailable")
        if current.preview_id != preview_id:
            raise StaleConfigPreviewError("Project config preview is stale; refresh before applying")
        if not any(item.section == section and item.option == option for item in current.additions):
            return error_response(
                "Trigger does not identify a registered missing attribute in this preview.",
                status_code=409,
                code="config_update_unavailable",
            )
        job_id = _enqueue(_authority_runid(runid), config, preview_id, section, option)
        return JSONResponse({"job_id": job_id}, status_code=202)
    except StaleConfigPreviewError as exc:
        return error_response(str(exc), status_code=409, code="stale_config_preview")
    except ConfigUpdateUnavailableError as exc:
        return error_response(str(exc), status_code=409, code="config_update_unavailable")
    except RuntimeError as exc:
        if str(exc) == "config_update_in_progress":
            return error_response("A project config update is already active.", status_code=409, code="config_update_in_progress")
        raise
