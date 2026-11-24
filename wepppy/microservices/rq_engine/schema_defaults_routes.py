"""HTTP endpoints for run-scoped discovery, schemas, defaults and outputs."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
from typing import Any, Mapping

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from wepppy.weppcloud.utils.auth_tokens import get_jwt_config

from .auth import AuthError, _normalize_scopes, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import PayloadRoute
from .responses import error_response
from .schema_defaults_controllers import (
    _controller_catalog,
    _controller_hints,
    _controller_templates,
    _resolve_controller,
)
from .schema_defaults_controllers_schema import _controller_schema
from .schema_defaults_geospatial import _geospatial_payload
from .schema_defaults_operation_docs import _build_operation_docs_snapshot, _build_operation_error_catalog
from .schema_defaults_ops import _build_run_operations
from .schema_defaults_outputs import _build_outputs_payload, _sha256_file as _sha256_file
from .schema_defaults_runtime import (
    LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM,
    SCHEMA_DEFAULTS_ALLOWED_SCOPES,
    CapabilityAuthorityInvalidError,
    RunConfigMismatchError,
    RuntimeState,
    _base_payload,
    _load_runtime_state,
    _runtime_snapshot_updated_at,
    _snapshot_freshness,
    _utc_timestamp,
)

logger = logging.getLogger(__name__)

router = APIRouter(route_class=PayloadRoute)


def _run_authority_error_response(exc: CapabilityAuthorityInvalidError) -> JSONResponse:
    response = error_response(
        exc.message,
        status_code=exc.status_code,
        code=exc.code,
        details=str(exc),
    )
    if exc.status_code == 503:
        response.headers["Retry-After"] = "5"
    return response


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    return _normalize_scopes(claims.get("scope"), get_jwt_config().scope_separator)


def _require_schema_defaults_claims(request: Request, runid: str) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if not scopes.intersection(SCHEMA_DEFAULTS_ALLOWED_SCOPES):
        required_text = ", ".join(sorted(SCHEMA_DEFAULTS_ALLOWED_SCOPES))
        raise AuthError(
            f"Token missing required scope(s): {required_text}",
            status_code=403,
            code="forbidden",
        )
    authorize_run_access(claims, runid)
    return claims


def _authorized_runtime(
    request: Request, runid: str, config: str, log_context: str
) -> RuntimeState | JSONResponse:
    try:
        _require_schema_defaults_claims(request, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:  # broad-except: unexpected auth failures use the canonical 401 envelope
        logger.exception("rq-engine %s auth failed", log_context)
        return error_response("Failed to authorize request", status_code=401)

    try:
        return _load_runtime_state(runid, config)
    except (FileNotFoundError, RunConfigMismatchError):
        return error_response("Run not found", status_code=404, code="not_found")
    except CapabilityAuthorityInvalidError as exc:
        return _run_authority_error_response(exc)
    except Exception:  # broad-except: isolate controller loading at the HTTP boundary
        logger.exception("rq-engine %s state load failed", log_context)
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/geospatial-metadata",
    summary="Get run geospatial metadata",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only geospatial constraints/defaults metadata for run-scoped planning; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("geospatial_metadata"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Geospatial metadata returned.",
        extra={
            404: "Run not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_geospatial_metadata(runid: str, config: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "geospatial-metadata")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        geospatial_payload = _geospatial_payload(runtime)
        etag_input = {
            "run_state_revision": runtime.run_state_revision,
            "geospatial": {
                key: value
                for key, value in geospatial_payload.items()
                if key != "computed_at"
            },
        }
        etag_digest = hashlib.sha256(
            json.dumps(etag_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        freshness = _snapshot_freshness(
            data_state="materialized",
            data_updated_at=None,
            fallback_updated_at=_runtime_snapshot_updated_at(
                runid=runtime.runid,
                generated_at=runtime.generated_at,
            ),
        )

        payload = _base_payload(runtime)
        payload.update(geospatial_payload)
        payload.update(freshness)
        payload["etag"] = f'W/"geospatial:{runtime.runid}:{etag_digest}"'
        payload["computed_at"] = freshness["updated_at"]
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine geospatial-metadata payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers",
    summary="List run controllers",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller catalog; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("list_controllers"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller catalog returned.",
        extra={
            404: "Run not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def list_controllers(runid: str, config: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "controllers")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        payload = _base_payload(runtime)
        payload.update(
            {
                "runid": runtime.runid,
                "config": runtime.config,
                "active_mods": list(runtime.active_mods),
                "endpoints_url": f"/api/runs/{runtime.runid}/{runtime.config}/endpoints",
                "pipeline_url": f"/api/runs/{runtime.runid}/{runtime.config}/pipeline",
                "readiness_url": f"/api/runs/{runtime.runid}/{runtime.config}/readiness",
                "outputs_url": f"/api/runs/{runtime.runid}/{runtime.config}/outputs",
                "controllers": list(_controller_catalog(runtime).values()),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controllers payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/schema",
    summary="Get controller schema",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller schema + constraints; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_schema"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller schema returned.",
        extra={
            404: "Run or controller not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_controller_schema(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "controller schema")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        controller_schema = _controller_schema(resolved_controller, runtime)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "schema_version": controller_schema["schema_version"],
                "fields": controller_schema["fields"],
            }
        )
        if "model_authority" in controller_schema:
            payload["model_authority"] = controller_schema["model_authority"]
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller schema failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/hints",
    summary="Get controller hints",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only controller hint metadata; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_hints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller hints returned.",
        extra={
            404: "Run or controller not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_controller_hints(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "controller hints")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        hints = _controller_hints(resolved_controller)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "schema_version": hints["schema_version"],
                "hints": {
                    "context_fields": hints["context_fields"],
                    "groups": hints["groups"],
                    "field_hints": hints["field_hints"],
                },
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller hints failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/controllers/{controller}/templates",
    summary="Get controller templates",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only templates + run-resolved defaults; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_controller_templates"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Controller templates returned.",
        extra={
            404: "Run or controller not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_controller_templates(runid: str, config: str, controller: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "controller templates")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        resolved_controller = _resolve_controller(controller, runtime)
        if resolved_controller is None:
            return error_response(
                "Controller not found",
                status_code=404,
                code="not_found",
            )

        templates_payload = _controller_templates(resolved_controller, runtime)

        payload = _base_payload(runtime)
        payload.update(
            {
                "controller": resolved_controller,
                "templates": templates_payload["templates"],
                "run_resolved_defaults": templates_payload["run_resolved_defaults"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine controller templates failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints",
    summary="List run endpoints",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only run-scoped operation catalog; no queue. "
        f"Set `{LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM}=true` to include per-operation schema/defaults/errors in one response."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("list_run_endpoints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run-scoped endpoint catalog returned.",
        extra={
            404: "Run not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def list_run_endpoints(
    runid: str,
    config: str,
    request: Request,
    include_operation_docs: bool = Query(
        default=False,
        description=(
            "Optional boolean. When true, include per-operation schema/defaults/errors snapshot "
            "under `operation_docs`."
        ),
    ),
) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "run-endpoints")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        operations = _build_run_operations(runtime)
        operation_descriptors = [copy.deepcopy(operation["descriptor"]) for operation in operations.values()]

        payload = _base_payload(runtime)
        payload["operations"] = operation_descriptors
        if include_operation_docs:
            payload["operation_docs"] = _build_operation_docs_snapshot(
                operations=operations,
                computed_at=_utc_timestamp(),
            )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoints payload build failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/schema",
    summary="Get run endpoint schema",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only request schema + operation descriptor; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_schema"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation schema returned.",
        extra={
            404: "Run or operation not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_run_endpoint_schema(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "run-endpoint schema")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        descriptor = copy.deepcopy(operation_docs["descriptor"])
        schema = copy.deepcopy(operation_docs["schema"])

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": descriptor["operation_id"],
                "run_scoped": descriptor["run_scoped"],
                "method": descriptor["method"],
                "path": descriptor["path"],
                "operation_descriptor": descriptor,
                "schema_version": schema["schema_version"],
                "request": schema["request"],
                "responses": schema["responses"],
            }
        )
        if "capability_authority" in schema:
            payload["capability_authority"] = schema["capability_authority"]
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint schema failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/defaults",
    summary="Get run endpoint defaults",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only run-resolved defaults for an operation; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_defaults"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation defaults returned.",
        extra={
            404: "Run or operation not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_run_endpoint_defaults(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "run-endpoint defaults")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        defaults_doc = copy.deepcopy(operation_docs["defaults"])
        defaults_doc["computed_at"] = _utc_timestamp()

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": operation_id,
                "resolved_defaults": defaults_doc["resolved_defaults"],
                "defaults_context": defaults_doc["defaults_context"],
                "computed_at": defaults_doc["computed_at"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint defaults failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/endpoints/{operation_id}/errors",
    summary="Get run endpoint errors",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only operation error taxonomy for one run-scoped operation; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_run_endpoint_errors"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run operation error catalog returned.",
        extra={
            404: "Run or operation not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_run_endpoint_errors(runid: str, config: str, operation_id: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "run-endpoint errors")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        operations = _build_run_operations(runtime)
        operation_docs = operations.get(operation_id)
        if operation_docs is None:
            return error_response(
                "Operation not found",
                status_code=404,
                code="not_found",
            )

        payload = _base_payload(runtime)
        payload.update(
            {
                "operation_id": operation_id,
                "errors": _build_operation_error_catalog(
                    operation_id=operation_id,
                    operation_docs=operation_docs,
                ),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine run-endpoint errors failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/runs/{runid}/{config}/outputs",
    summary="Get run outputs",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`) with run access checks. "
        "Read-only outputs/artifact discovery snapshot with retrieval handles and provenance metadata; no queue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("get_outputs"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Run outputs snapshot returned.",
        extra={
            404: "Run not found. Returns the canonical error payload.",
            409: "Invalid stored project capability authority.",
            503: "Builder registry is unavailable; retry after the advertised interval.",
        },
    ),
)
def get_outputs(runid: str, config: str, request: Request) -> JSONResponse:
    runtime = _authorized_runtime(request, runid, config, "outputs")
    if isinstance(runtime, JSONResponse):
        return runtime

    try:
        payload = _base_payload(runtime)
        payload.update(_build_outputs_payload(runtime))
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine outputs failed")
        return error_response("Error Handling Request", status_code=500)


__all__ = ["router"]
