"""Authenticated synchronous project-config builder API."""

from __future__ import annotations

from dataclasses import asdict
import logging
import os
from typing import Any, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from wepppy.nodb.config_builder.registry import RegistryError, load_registry
from wepppy.nodb.config_builder.resolver import BuilderConstraintError, describe_builder
from wepppy.nodb.config_builder.snapshot import builder_writer_enabled, parse_builder_selections, resolve_builder_candidate
from wepppy.nodb.core import Ron
from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot
from wepppy.weppcloud.routes.readme_md import ensure_readme_on_create
from wepppy.weppcloud.user_preferences import PreferenceIdentityError, cleanup_new_run_directory, register_owned_run, resolve_creation_actor

from .auth import AuthError, _normalize_roles, require_jwt
from .creation_idempotency import CreationIdempotencyError, build_creation_fingerprint, complete_creation, reserve_creation
from .project_routes import _create_run_dir, _creation_actor_scope, _creation_idempotency_client, _release_creation_safely, _run_url
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, validation_error_response

logger = logging.getLogger(__name__)
router = APIRouter()
_SCOPES = ["rq:enqueue"]
_OVERRIDE_ROLES = frozenset({"poweruser", "admin", "root"})


def _authorize(request: Request) -> tuple[Mapping[str, Any] | None, JSONResponse | None]:
    try:
        return require_jwt(request, required_scopes=_SCOPES), None
    except AuthError as exc:
        return None, error_response(exc.message, status_code=exc.status_code, code=exc.code)


def _can_override(claims: Mapping[str, Any]) -> bool:
    return bool(_normalize_roles(claims.get("roles")) & _OVERRIDE_ROLES)


def _field_error(exc: BuilderConstraintError) -> JSONResponse:
    return validation_error_response([{"field": exc.field, "code": exc.code, "message": str(exc)}])


def _parse_body(payload: object, *, creation: bool) -> tuple[str, object, str | None]:
    if not isinstance(payload, dict):
        raise BuilderConstraintError("request", "invalid_type", "Request must be an object")
    expected = {"registry_revision", "selections"}
    if creation:
        expected.add("creation_idempotency_key")
    unknown = set(payload) - expected
    if unknown:
        raise BuilderConstraintError("request", "unknown_field", f"Unknown request fields: {sorted(unknown)}")
    revision = payload.get("registry_revision")
    if not isinstance(revision, str) or not revision:
        raise BuilderConstraintError("registry_revision", "missing_required_field", "registry_revision is required")
    key = payload.get("creation_idempotency_key") if creation else None
    if creation and (not isinstance(key, str) or not key):
        raise BuilderConstraintError("creation_idempotency_key", "missing_required_field", "creation_idempotency_key is required")
    return revision, payload.get("selections"), key


def _validated_candidate(payload: object, claims: Mapping[str, Any], *, creation: bool):
    revision, raw_selections, key = _parse_body(payload, creation=creation)
    registry = load_registry()
    if revision != registry.revision:
        return None, key, error_response("Builder schema changed; reload and review selections.", status_code=409, code="stale_builder_schema")
    selections = parse_builder_selections(raw_selections)
    if selections.cellsize_override is not None and not _can_override(claims):
        return None, key, error_response("Cell-size override requires PowerUser, Admin, or Root.", status_code=403, code="forbidden")
    return resolve_builder_candidate(selections, registry=registry), key, None


@router.get("/project-config/builder", summary="Describe project config builder", description="Requires JWT `rq:enqueue`; synchronously returns the registered builder schema with no queue or writes.", tags=["rq-engine", "project"], operation_id=rq_operation_id("describe_project_config_builder"), responses=agent_route_responses(success_code=200, success_description="Current builder schema."))
async def builder_description(request: Request) -> JSONResponse:
    claims, auth_error = _authorize(request)
    if auth_error is not None:
        return auth_error
    assert claims is not None
    try:
        description = describe_builder()
    except RegistryError as exc:
        logger.exception("builder description failed")
        return error_response(
            "Builder registry is unavailable.", status_code=500,
            code="builder_registry_error", details=str(exc),
        )
    return JSONResponse({"schema_version": description.schema_version, "registry_revision": description.registry_revision, "components": [asdict(item) for item in description.components], "allowed_cell_sizes": list(description.allowed_cell_sizes), "default_selections": dict(description.default_selections), "capability_graph": {section: dict(options) for section, options in description.capability_graph.items()}, "can_override_cellsize": _can_override(claims), "config_token": "config", "config_filename": "config.cfg"})


@router.post("/project-config/builder/validate", summary="Validate project config proposal", description="Requires JWT `rq:enqueue`; synchronously resolves a complete proposal with no queue or writes.", tags=["rq-engine", "project"], operation_id=rq_operation_id("validate_project_config_builder"), responses=agent_route_responses(success_code=200, success_description="Valid resolved proposal.", extra={400: "Validation failed. Returns the canonical error payload.", 409: "Stale schema. Returns the canonical error payload."}))
async def validate_builder(request: Request) -> JSONResponse:
    claims, auth_error = _authorize(request)
    if auth_error is not None:
        return auth_error
    try:
        candidate, _key, failure = _validated_candidate(await request.json(), claims or {}, creation=False)
        if failure is not None:
            return failure
        assert candidate is not None
        return JSONResponse({"valid": True, "registry_revision": candidate.resolved.registry_revision, "review": dict(candidate.review)})
    except BuilderConstraintError as exc:
        return _field_error(exc)
    except RegistryError as exc:
        logger.exception("builder validation failed")
        return error_response(
            "Builder registry is unavailable.", status_code=500,
            code="builder_registry_error", details=str(exc),
        )
    except ValueError:
        return error_response("Invalid builder request.", status_code=400, code="validation_error")


@router.post("/project-config/builder/create", summary="Create project from builder", description="Requires JWT `rq:enqueue`; synchronously creates one fixed-token project with no queue.", tags=["rq-engine", "project"], operation_id=rq_operation_id("create_project_config_builder"), responses=agent_route_responses(success_code=201, success_description="Builder project created.", extra={400: "Validation failed. Returns the canonical error payload.", 409: "Stale or duplicate request. Returns the canonical error payload.", 503: "Creation unavailable. Returns the canonical error payload."}))
async def create_builder_project(request: Request) -> JSONResponse:
    claims, auth_error = _authorize(request)
    if auth_error is not None:
        return auth_error
    try:
        if not builder_writer_enabled():
            return error_response("Builder creation is not enabled.", status_code=503, code="builder_writer_disabled")
        payload = await request.json()
        candidate, key, failure = _validated_candidate(payload, claims or {}, creation=True)
        if failure is not None:
            return failure
        assert candidate is not None and key is not None
    except BuilderConstraintError as exc:
        return _field_error(exc)
    except RegistryError as exc:
        logger.exception("builder registry failed during creation")
        return error_response(
            "Builder registry is unavailable.", status_code=500,
            code="builder_registry_error", details=str(exc),
        )
    except ValueError:
        logger.exception("builder creation validation failed")
        return error_response("Invalid builder request.", status_code=400, code="validation_error")

    try:
        actor = resolve_creation_actor(claims)
    except (PreferenceIdentityError, SQLAlchemyError) as exc:
        logger.exception("builder project owner resolution failed")
        return error_response(
            "Could not resolve project owner.", status_code=500,
            code="run_ownership_failed", details=str(exc),
        )
    fingerprint = build_creation_fingerprint(mode="builder", preset_id="config", normalized_overrides=dict(candidate.review), registry_revision=candidate.resolved.registry_revision)
    client = _creation_idempotency_client()
    try:
        reservation = reserve_creation(client, idempotency_key=key, actor_scope=_creation_actor_scope(actor), fingerprint=fingerprint)
    except (CreationIdempotencyError, redis.RedisError):
        return error_response("Project creation is temporarily unavailable.", status_code=503, code="creation_idempotency_unavailable")
    if reservation.status == "conflict":
        return error_response("Creation idempotency key conflicts with different input.", status_code=409, code="idempotency_key_conflict")
    if reservation.status == "in_progress":
        response = error_response("Project creation is already in progress.", status_code=409, code="creation_in_progress")
        response.headers["Retry-After"] = "2"
        return response
    if reservation.status == "replay":
        return JSONResponse({"run_id": reservation.run_id, "location": reservation.location, "config_token": "config"}, status_code=200)
    runid = ""
    wd = ""
    try:
        runid, wd = _create_run_dir(actor.email if actor else None)
        materialize_preset_snapshot(wd, candidate.artifact)
        Ron(wd, "config.cfg")
        from wepppy.weppcloud.utils.run_ttl import initialize_ttl

        initialize_ttl(wd)
        if actor is not None:
            register_owned_run(runid, "config", actor.user_id)
        ensure_readme_on_create(runid, "config")
        location = _run_url(runid, "config")
        complete_creation(client, reservation, run_id=runid, location=location)
        if candidate.resolved.cellsize_source == "privileged_override":
            logger.info("builder privileged cell-size override", extra={"actor_user_id": actor.user_id if actor else None, "runid": runid})
        return JSONResponse({"run_id": runid, "location": location, "config_token": "config"}, status_code=201)
    except Exception:  # broad-except: creation boundary must clean partial runs and release reservations
        logger.exception("builder project initialization failed", extra={"runid": runid or None})
        if runid and wd:
            try:
                cleanup_new_run_directory(runid, wd)
            except (OSError, redis.RedisError, RuntimeError, ValueError):
                logger.exception("builder project cleanup failed", extra={"runid": runid})
        _release_creation_safely(client, reservation)
        return error_response("Could not create builder project.", status_code=500, code="run_initialization_failed")


__all__ = ["router"]
