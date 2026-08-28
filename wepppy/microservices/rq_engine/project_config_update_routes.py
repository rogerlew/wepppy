"""Authenticated project configuration update routes."""

from __future__ import annotations

from dataclasses import asdict
import logging
import os
from pathlib import Path
from typing import Any, Literal, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from rq import Queue
from typing_extensions import TypeAliasType

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.project_config_update import (
    CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
    ConfigUpdateAcknowledgmentError,
    ConfigUpdateError,
    ConfigUpdateRegistryError,
    ConfigUpdateResult,
    ConfigUpdateUnavailableError,
    StaleConfigPreviewError,
    preview_project_config_update,
    project_config_digest_warning,
    project_config_update_enabled,
    project_config_update_reconciliation,
    project_config_update_preview_guard,
    project_config_update_status,
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


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CanonicalJsonValue = TypeAliasType(
    "CanonicalJsonValue",
    str
    | int
    | float
    | bool
    | None
    | list["CanonicalJsonValue"]
    | dict[str, "CanonicalJsonValue"],
)


class _UpdateAdditionModel(_ExactModel):
    section: str
    option: str
    value: str
    source_id: str
    source_revision: str


class _SelectedParentModel(_ExactModel):
    kind: str
    id: str
    revision: str


class _CapabilityIdentityModel(_ExactModel):
    graph_sha256: str
    structure_sha256: str
    provider_revision: str
    wepp_binary_revisions: dict[str, str]
    selected_parent_chain: list[_SelectedParentModel]


class _CapabilityDefaultsModel(_ExactModel):
    locale_profile: str
    dem_source: str
    climate_dataset: str
    climate_station_database: str
    landuse_dataset: str
    soil_dataset: str
    delineation_backend: str
    watershed_representation: str
    wepp_binary: str


class _PreservedNodbModel(_ExactModel):
    mods: list[str]


class _PreservedClimateModel(_ExactModel):
    cligen_db: str


class _PreservedSelectionsModel(_ExactModel):
    capability_defaults: _CapabilityDefaultsModel
    nodb: _PreservedNodbModel
    climate: _PreservedClimateModel


class _RefreshAcknowledgmentModel(_ExactModel):
    required: Literal[True]
    revision: Literal["PC-24-capability-refresh-v1"]
    text: str


class _AddedSupportModel(_ExactModel):
    id: str
    support_state: str | None


class _CapabilityChangeModel(_ExactModel):
    section: str
    option: str
    kind: Literal["added", "removed", "changed"]
    before: CanonicalJsonValue
    after: CanonicalJsonValue
    added_ids: list[str]
    removed_ids: list[str]
    added_support: list[_AddedSupportModel]


class _CapabilityRefreshModel(_ExactModel):
    locale_profile: str
    locales: list[str]
    preserved_project_selections: _PreservedSelectionsModel
    acknowledgment: _RefreshAcknowledgmentModel
    prior: _CapabilityIdentityModel
    resulting: _CapabilityIdentityModel
    changes: list[_CapabilityChangeModel]


class _UpdatePreviewModel(_ExactModel):
    available: bool
    preview_id: str
    config_filename: str
    current_digest: str
    resulting_digest: str
    digest_warning: bool
    update_kind: Literal["additive", "capability_refresh", "combined"]
    capability_refresh: _CapabilityRefreshModel | None
    additions: list[_UpdateAdditionModel]


class _LastUpdateModel(_ExactModel):
    sequence: int
    kind: Literal["additive", "capability_refresh", "combined"]
    preview_id: str | None
    prior_sha256: str
    resulting_sha256: str


class _UpdateAvailabilityModel(_ExactModel):
    available: bool
    preview_id: str | None
    digest_warning: bool
    current_digest: str | None
    update_kind: Literal["additive", "capability_refresh", "combined"] | None
    acknowledgment_required: bool
    last_update: _LastUpdateModel | None
    reason: str | None = None
    details: str | None = None


class _UpdateAcceptedModel(_ExactModel):
    job_id: str


class _UpdateRecoveredModel(_ExactModel):
    applied: Literal[True]
    recovered: Literal[True]
    sequence: int
    prior_digest: str
    resulting_digest: str


def _application_revision() -> str:
    return str(os.getenv("RQ_ENGINE_DEPLOYMENT_REVISION") or "dev").strip() or "dev"


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
    result = preview_project_config_update(
        get_wd(_authority_runid(runid)), application_revision=_application_revision()
    )
    if Path(result.config_filename).stem != Path(config).stem:
        raise ConfigUpdateUnavailableError("Route config does not identify the project-owned config")
    return result


def _preview_payload(result) -> dict[str, object]:
    return {
        "available": result.available,
        "preview_id": result.preview_id,
        "config_filename": result.config_filename,
        "current_digest": result.current_digest,
        "resulting_digest": result.resulting_digest,
        "digest_warning": result.digest_warning,
        "update_kind": result.update_kind,
        "capability_refresh": result.capability_refresh,
        "additions": [asdict(item) for item in result.additions],
    }


@router.get(
    "/runs/{runid}/{config}/project-config/update-availability",
    summary="Check project config update availability",
    description="Requires JWT run read access; this is a read-only operation.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_availability"),
    response_model=_UpdateAvailabilityModel,
    responses=agent_route_responses(
        success_code=200,
        success_description="Read-only availability state.",
        extra={503: "Builder registry is unavailable; retry after the advertised interval."},
    ),
)
async def update_availability(runid: str, config: str, request: Request) -> JSONResponse:
    _claims, failure = _authorize(request, runid, mutation=False)
    if failure is not None:
        return failure
    authority_wd = get_wd(_authority_runid(runid))
    current_digest = None
    last_update = None
    try:
        status = project_config_update_status(authority_wd)
        current_digest = status.current_digest
        last_update = status.last_update
    except ConfigUpdateRegistryError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return response
    except ConfigUpdateError as exc:
        logger.info(
            "Project config update status is unavailable for run %s: %s",
            runid,
            exc,
        )
    try:
        digest_warning = project_config_digest_warning(authority_wd)
    except ConfigUpdateRegistryError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return response
    except ConfigUpdateError as exc:
        logger.info(
            "Project config digest status is unavailable for run %s: %s",
            runid,
            exc,
        )
        digest_warning = False
    if not project_config_update_enabled():
        return JSONResponse({
            "available": False,
            "preview_id": None,
            "digest_warning": digest_warning,
            "current_digest": current_digest,
            "update_kind": None,
            "acknowledgment_required": False,
            "last_update": last_update,
            "reason": "updates_disabled",
        })
    try:
        preview = _preview(runid, config)
        return JSONResponse({
            "available": preview.available,
            "preview_id": preview.preview_id,
            "digest_warning": preview.digest_warning,
            "current_digest": preview.current_digest,
            "update_kind": preview.update_kind if preview.available else None,
            "acknowledgment_required": preview.capability_refresh is not None,
            "last_update": last_update,
        })
    except ConfigUpdateRegistryError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return response
    except ConfigUpdateError as exc:
        return JSONResponse({
            "available": False,
            "preview_id": None,
            "digest_warning": digest_warning,
            "current_digest": current_digest,
            "update_kind": None,
            "acknowledgment_required": False,
            "last_update": last_update,
            "reason": "config_update_unavailable",
            "details": str(exc),
        })


@router.get(
    "/runs/{runid}/{config}/project-config/update-preview",
    summary="Preview a complete project config update",
    description="Requires JWT; Owner/Admin/Root read-only typed preview.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_preview"),
    response_model=_UpdatePreviewModel,
    responses=agent_route_responses(
        success_code=200,
        success_description="Complete additive or acknowledged-refresh preview.",
        extra={
            409: "Updates disabled or unavailable.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
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
    except ConfigUpdateRegistryError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return response
    except ConfigUpdateError as exc:
        return error_response(str(exc), status_code=409, code="config_update_unavailable")


def _apply_payload(
    payload: object,
    preview,
) -> tuple[str, str | None, str | None, bool, str | None]:
    if not isinstance(payload, dict):
        raise ConfigUpdateError("Request must be an object")
    expected = {"preview_id"}
    if preview.additions:
        expected.add("trigger")
    if preview.capability_refresh is not None:
        expected.add("capability_acknowledgment")
    if set(payload) != expected:
        if preview.capability_refresh is not None:
            raise ConfigUpdateAcknowledgmentError(
                "Request must include the exact capability refresh acknowledgment"
            )
        raise ConfigUpdateError("Request shape does not match the current preview")
    preview_id = payload.get("preview_id")
    if not isinstance(preview_id, str) or not preview_id:
        raise ConfigUpdateError("preview_id is required")
    section: str | None = None
    option: str | None = None
    if preview.additions:
        trigger = payload.get("trigger")
        if not isinstance(trigger, dict) or set(trigger) != {"section", "option"}:
            raise ConfigUpdateError("trigger requires section and option")
        section, option = trigger.get("section"), trigger.get("option")
        if not isinstance(section, str) or not section or not isinstance(option, str) or not option:
            raise ConfigUpdateError("trigger section and option are required")
    accepted = False
    revision: str | None = None
    if preview.capability_refresh is not None:
        acknowledgment = payload.get("capability_acknowledgment")
        if not isinstance(acknowledgment, dict) or set(acknowledgment) != {"accepted", "revision"}:
            raise ConfigUpdateAcknowledgmentError(
                "The exact capability refresh acknowledgment is required"
            )
        accepted = acknowledgment.get("accepted") is True
        revision_value = acknowledgment.get("revision")
        revision = revision_value if isinstance(revision_value, str) else None
        if not accepted or revision != CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION:
            raise ConfigUpdateAcknowledgmentError(
                "The exact capability refresh acknowledgment is required"
            )
    return preview_id, section, option, accepted, revision


def _validate_recovered_payload(payload: object, update_kind: str) -> None:
    if not isinstance(payload, dict):
        raise ConfigUpdateError("Request must be an object")
    expected = {"preview_id"}
    if update_kind in {"additive", "combined"}:
        expected.add("trigger")
    if update_kind in {"capability_refresh", "combined"}:
        expected.add("capability_acknowledgment")
    if set(payload) != expected:
        if update_kind in {"capability_refresh", "combined"}:
            raise ConfigUpdateAcknowledgmentError(
                "The exact capability refresh acknowledgment is required"
            )
        raise ConfigUpdateError("Request shape does not match the committed update")
    if "trigger" in expected:
        trigger = payload.get("trigger")
        if not isinstance(trigger, dict) or set(trigger) != {"section", "option"}:
            raise ConfigUpdateError("trigger requires section and option")
        if not all(isinstance(trigger.get(key), str) and trigger[key] for key in ("section", "option")):
            raise ConfigUpdateError("trigger section and option are required")
    if "capability_acknowledgment" in expected:
        acknowledgment = payload.get("capability_acknowledgment")
        if (
            not isinstance(acknowledgment, dict)
            or set(acknowledgment) != {"accepted", "revision"}
            or acknowledgment.get("accepted") is not True
            or acknowledgment.get("revision")
            != CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION
        ):
            raise ConfigUpdateAcknowledgmentError(
                "The exact capability refresh acknowledgment is required"
            )


def _recovered_apply_response(
    payload: object,
    recovered: ConfigUpdateResult,
) -> JSONResponse:
    try:
        _validate_recovered_payload(payload, recovered.update_kind)
    except ConfigUpdateAcknowledgmentError as exc:
        return error_response(
            "Capability refresh acknowledgment is required.",
            status_code=400,
            code="capability_refresh_acknowledgment_required",
            details=str(exc),
        )
    except ConfigUpdateError as exc:
        return validation_error_response([{
            "field": "request", "code": "invalid_request", "message": str(exc)
        }])
    return JSONResponse({
        "applied": True,
        "recovered": True,
        "sequence": recovered.sequence,
        "prior_digest": recovered.prior_digest,
        "resulting_digest": recovered.resulting_digest,
    })


def _enqueue(
    runid: str,
    config: str,
    preview_id: str,
    section: str | None,
    option: str | None,
    acknowledgment_accepted: bool,
    acknowledgment_revision: str | None,
    application_revision: str,
) -> str:
    job_id = new_rq_job_id()
    key = f"{CONFIG_UPDATE_ACTIVE_PREFIX}{runid}"
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        if not redis_conn.set(key, job_id, nx=True, ex=_ACTIVE_TTL):
            raise RuntimeError("config_update_in_progress")
        try:
            job = Queue(connection=redis_conn).enqueue_call(
                run_project_config_update_rq,
                args=(
                    runid,
                    config,
                    preview_id,
                    application_revision,
                    section,
                    option,
                    acknowledgment_accepted,
                    acknowledgment_revision,
                ),
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
    description="Requires JWT; Owner/Admin/Root enqueue.",
    tags=["rq-engine", "project"],
    operation_id=rq_operation_id("project_config_update_apply"),
    status_code=202,
    response_model=_UpdateAcceptedModel,
    responses={
        **agent_route_responses(
            success_code=202,
            success_description="Update job accepted.",
            extra={
                400: "Invalid request or missing refresh acknowledgment.",
                409: "Stale, unavailable, or active update.",
                503: "Builder registry is unavailable; retry after the advertised interval.",
            },
        ),
        200: {
            "model": _UpdateRecoveredModel,
            "description": "Matching latest preview was already committed and recovered.",
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": [
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["preview_id", "trigger"],
                                "properties": {
                                    "preview_id": {"type": "string", "minLength": 1},
                                    "trigger": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["section", "option"],
                                        "properties": {
                                            "section": {"type": "string", "minLength": 1},
                                            "option": {"type": "string", "minLength": 1},
                                        },
                                    },
                                },
                            },
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["preview_id", "capability_acknowledgment"],
                                "properties": {
                                    "preview_id": {"type": "string", "minLength": 1},
                                    "capability_acknowledgment": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["accepted", "revision"],
                                        "properties": {
                                            "accepted": {"const": True, "type": "boolean"},
                                            "revision": {"const": "PC-24-capability-refresh-v1", "type": "string"},
                                        },
                                    },
                                },
                            },
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["preview_id", "trigger", "capability_acknowledgment"],
                                "properties": {
                                    "preview_id": {"type": "string", "minLength": 1},
                                    "trigger": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["section", "option"],
                                        "properties": {
                                            "section": {"type": "string", "minLength": 1},
                                            "option": {"type": "string", "minLength": 1},
                                        },
                                    },
                                    "capability_acknowledgment": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["accepted", "revision"],
                                        "properties": {
                                            "accepted": {"const": True, "type": "boolean"},
                                            "revision": {"const": "PC-24-capability-refresh-v1", "type": "string"},
                                        },
                                    },
                                },
                            },
                        ]
                    }
                }
            },
        }
    },
)
async def update_apply(runid: str, config: str, request: Request) -> JSONResponse:
    _claims, failure = _authorize(request, runid, mutation=True)
    if failure is not None:
        return failure
    if not project_config_update_enabled():
        return error_response("Project config updates are disabled.", status_code=409, code="config_update_unavailable")
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("preview_id"), str):
            raise ConfigUpdateError("Request requires preview_id")
    except (ConfigUpdateError, ValueError) as exc:
        return validation_error_response([{"field": "request", "code": "invalid_request", "message": str(exc)}])
    try:
        requested_preview_id = str(payload["preview_id"])
        authority_runid = _authority_runid(runid)
        authority_wd = get_wd(authority_runid)
        status = project_config_update_status(authority_wd)
        if (
            status.config_filename is None
            or Path(status.config_filename).stem != Path(config).stem
        ):
            raise ConfigUpdateUnavailableError(
                "Route config does not identify the project-owned config"
            )
        recovered = project_config_update_reconciliation(
            authority_wd, requested_preview_id
        )
        if recovered is not None:
            return _recovered_apply_response(payload, recovered)
        application_revision = _application_revision()
        update_unavailable = False
        job_id = None
        with project_config_update_preview_guard(
            authority_wd, application_revision=application_revision
        ) as current:
            if Path(current.config_filename).stem != Path(config).stem:
                raise ConfigUpdateUnavailableError(
                    "Route config does not identify the project-owned config"
                )
            if not current.available:
                update_unavailable = True
            elif current.preview_id != requested_preview_id:
                raise StaleConfigPreviewError("Project config preview is stale; refresh before applying")
            else:
                try:
                    preview_id, section, option, accepted, revision = _apply_payload(
                        payload, current
                    )
                except ConfigUpdateAcknowledgmentError as exc:
                    return error_response(
                        "Capability refresh acknowledgment is required.",
                        status_code=400,
                        code="capability_refresh_acknowledgment_required",
                        details=str(exc),
                    )
                except ConfigUpdateError as exc:
                    return validation_error_response([{
                        "field": "request", "code": "invalid_request", "message": str(exc)
                    }])
                if current.additions and not any(
                    item.section == section and item.option == option
                    for item in current.additions
                ):
                    return error_response(
                        "Trigger does not identify a registered missing attribute in this preview.",
                        status_code=409,
                        code="config_update_unavailable",
                    )
                job_id = _enqueue(
                    authority_runid,
                    config,
                    preview_id,
                    section,
                    option,
                    accepted,
                    revision,
                    application_revision,
                )
        if update_unavailable:
            recovered = project_config_update_reconciliation(
                authority_wd, requested_preview_id
            )
            if recovered is not None:
                return _recovered_apply_response(payload, recovered)
            return error_response(
                "No project config update is available.",
                status_code=409,
                code="config_update_unavailable",
            )
        assert job_id is not None
        return JSONResponse({"job_id": job_id}, status_code=202)
    except StaleConfigPreviewError as exc:
        return error_response(str(exc), status_code=409, code="stale_config_preview")
    except ConfigUpdateRegistryError as exc:
        response = error_response(
            "Builder registry is unavailable.",
            status_code=503,
            code="builder_registry_error",
            details=str(exc),
        )
        response.headers["Retry-After"] = "5"
        return response
    except ConfigUpdateUnavailableError as exc:
        return error_response(str(exc), status_code=409, code="config_update_unavailable")
    except ConfigUpdateError as exc:
        return error_response(
            "Project config update state is invalid.",
            status_code=409,
            code="config_update_unavailable",
            details=str(exc),
        )
    except RuntimeError as exc:
        if str(exc) == "config_update_in_progress":
            return error_response("A project config update is already active.", status_code=409, code="config_update_in_progress")
        raise
