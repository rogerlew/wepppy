from __future__ import annotations

import ast
import copy
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from wepppy.nodb.base import (
    CaseSensitiveRawConfigParser,
    get_config_dir,
    get_configs,
    get_default_config_path,
)
from wepppy.weppcloud.utils.auth_tokens import get_jwt_config

from .auth import AuthError, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response

logger = logging.getLogger(__name__)

router = APIRouter()

CONTRACT_VERSION = "1.0.0-draft"
DEPLOYMENT_REVISION_ENV = "RQ_ENGINE_DEPLOYMENT_REVISION"
DEFAULT_DEPLOYMENT_REVISION = "dev"
SETUP_ALLOWED_SCOPES = frozenset({"rq:read", "rq:status"})


@dataclass(frozen=True)
class ConfigMetadata:
    config_id: str
    display_name: str
    active_mods: tuple[str, ...]
    supported_regions: tuple[str, ...]
    required_upload_steps: tuple[str, ...]
    recommended_for: tuple[str, ...]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deployment_revision() -> str:
    value = str(os.getenv(DEPLOYMENT_REVISION_ENV) or DEFAULT_DEPLOYMENT_REVISION).strip()
    return value or DEFAULT_DEPLOYMENT_REVISION


def _base_payload() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "deployment_revision": _deployment_revision(),
    }


def _strip_quotes(value: str) -> str:
    text = str(value).strip()
    if len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'"))
    ):
        return text[1:-1]
    return text


def _normalize_string_values(values: Sequence[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _parse_literal_list(raw_value: str, *, field_name: str, config_id: str) -> list[str]:
    text = str(raw_value or "").strip()
    if not text:
        return []
    try:
        value = ast.literal_eval(text)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name} value in config '{config_id}'.") from exc
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"Expected {field_name} list in config '{config_id}'.")
    return _normalize_string_values(value)


def _derive_required_upload_steps(active_mods: Sequence[str], config_id: str) -> tuple[str, ...]:
    config_token = config_id.lower()
    mods = {mod.lower() for mod in active_mods}
    steps: list[str] = []

    if (
        {"disturbed", "baer", "ash", "debris_flow"} & mods
        or "disturbed" in config_token
        or "fire" in config_token
    ):
        steps.append("upload-sbs")

    return tuple(steps)


def _derive_recommended_for(active_mods: Sequence[str], config_id: str) -> tuple[str, ...]:
    mods = {mod.lower() for mod in active_mods}
    config_token = config_id.lower()
    tags: list[str] = []

    if {"disturbed", "baer", "debris_flow", "ash"} & mods or "disturbed" in config_token or "fire" in config_token:
        tags.append("post_fire")
    if "debris_flow" in mods:
        tags.append("debris_flow")
    if "ash" in mods:
        tags.append("ash_transport")
    if "swat" in mods:
        tags.append("swat")
    if "rhem" in mods:
        tags.append("rhem")
    if "omni" in mods:
        tags.append("omni")
    if "treatments" in mods:
        tags.append("treatments")
    if "ag_fields" in mods:
        tags.append("ag_fields")
    if "lt" in mods or "laketahoe" in config_token:
        tags.append("lake_tahoe")
    if not tags:
        tags.append("baseline_watershed")

    return tuple(_normalize_string_values(tags))


def _read_config_metadata(config_id: str) -> ConfigMetadata:
    config_path = Path(get_config_dir()) / f"{config_id}.cfg"
    if not config_path.exists():
        raise FileNotFoundError(f"Config '{config_id}' does not exist.")

    parser = CaseSensitiveRawConfigParser(allow_no_value=True)
    with open(get_default_config_path(), encoding="utf-8") as fp:
        parser.read_file(fp)
    with open(config_path, encoding="utf-8") as fp:
        parser.read_file(fp)

    display_name_raw = parser.get("general", "name", fallback=config_id)
    locales_raw = parser.get("general", "locales", fallback="[]")
    mods_raw = parser.get("nodb", "mods", fallback="[]")

    active_mods = tuple(_parse_literal_list(mods_raw, field_name="nodb.mods", config_id=config_id))
    supported_regions = tuple(_parse_literal_list(locales_raw, field_name="general.locales", config_id=config_id))
    required_upload_steps = _derive_required_upload_steps(active_mods, config_id)
    recommended_for = _derive_recommended_for(active_mods, config_id)

    return ConfigMetadata(
        config_id=config_id,
        display_name=_strip_quotes(display_name_raw or config_id),
        active_mods=active_mods,
        supported_regions=supported_regions,
        required_upload_steps=required_upload_steps,
        recommended_for=recommended_for,
    )


@lru_cache(maxsize=1)
def _load_config_catalog() -> tuple[ConfigMetadata, ...]:
    return tuple(_read_config_metadata(config_id) for config_id in sorted(get_configs(), key=str.casefold))


@lru_cache(maxsize=1)
def _config_lookup() -> dict[str, ConfigMetadata]:
    return {metadata.config_id: metadata for metadata in _load_config_catalog()}


def _config_to_payload(metadata: ConfigMetadata) -> dict[str, Any]:
    return {
        "config_id": metadata.config_id,
        "display_name": metadata.display_name,
        "active_mods": list(metadata.active_mods),
        "supported_regions": list(metadata.supported_regions),
        "required_upload_steps": list(metadata.required_upload_steps),
        "recommended_for": list(metadata.recommended_for),
    }


def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
    raw_scope = claims.get("scope")
    separator = get_jwt_config().scope_separator

    def _split_scope_text(value: str) -> set[str]:
        scopes: set[str] = set()
        for chunk in value.split(separator):
            for token in chunk.split():
                if token:
                    scopes.add(token)
        return scopes

    if raw_scope is None:
        return set()
    if isinstance(raw_scope, str):
        return _split_scope_text(raw_scope)
    if isinstance(raw_scope, Sequence):
        scopes: set[str] = set()
        for item in raw_scope:
            if isinstance(item, str):
                scopes.update(_split_scope_text(item))
        return scopes
    return set()


def _require_setup_claims(request: Request) -> Mapping[str, Any]:
    claims = require_jwt(request)
    scopes = _extract_scopes(claims)
    if scopes.intersection(SETUP_ALLOWED_SCOPES):
        return claims

    required_text = ", ".join(sorted(SETUP_ALLOWED_SCOPES))
    raise AuthError(f"Token missing required scope(s): {required_text}", status_code=403, code="forbidden")


def _read_auth_requirements() -> dict[str, Any]:
    return {
        "bearer_jwt": {
            "required_any_scope": sorted(SETUP_ALLOWED_SCOPES),
        }
    }


def _base_read_descriptor(*, operation_id: str, method: str, path: str, required_fields: list[str]) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "run_scoped": False,
        "method": method,
        "path": path,
        "accepted_auth": ["bearer_jwt"],
        "auth_requirements": _read_auth_requirements(),
        "error_catalog_url": f"/api/endpoints/{operation_id}/errors",
        "write_precondition": {
            "required": False,
            "accepted": [],
            "conflict_status_code": 409,
            "conflict_error_code": "stale_run_state",
        },
        "idempotency_policy": {
            "supported": False,
            "key_locations": [],
            "dedupe_window_seconds": 0,
            "replay_behavior": "return_original_success",
            "mismatch_status_code": 409,
            "mismatch_error_code": "idempotency_key_conflict",
        },
        "execution_mode": "sync",
        "returns_job": False,
        "job_key": None,
        "content_types": ["application/json"],
        "file_fields": [],
        "success_status_codes": [200],
        "response_mode": "json",
        "result_contract": {
            "kind": "sync_result",
            "required_response_fields": required_fields,
            "terminal_signal": "http_status_2xx",
        },
        "estimated_duration": {
            "bucket": "fast",
            "typical_seconds": 1,
        },
        "batch_mode_behavior": "n/a",
        "base_project_behavior": "n/a",
        "mutates_controllers": [],
        "invalidates_steps": [],
    }


@lru_cache(maxsize=1)
def _setup_operation_registry() -> dict[str, dict[str, Any]]:
    config_catalog_url = "/api/configs"

    list_configs_id = rq_operation_id("list_configs")
    get_config_id = rq_operation_id("get_config")
    list_endpoints_id = rq_operation_id("list_setup_endpoints")
    schema_id = rq_operation_id("get_setup_endpoint_schema")
    defaults_id = rq_operation_id("get_setup_endpoint_defaults")
    errors_id = rq_operation_id("get_setup_endpoint_errors")
    create_id = rq_operation_id("create")

    operations: dict[str, dict[str, Any]] = {
        list_configs_id: _base_read_descriptor(
            operation_id=list_configs_id,
            method="GET",
            path="/api/configs",
            required_fields=["configs"],
        ),
        get_config_id: _base_read_descriptor(
            operation_id=get_config_id,
            method="GET",
            path="/api/configs/{config}",
            required_fields=["config"],
        ),
        list_endpoints_id: _base_read_descriptor(
            operation_id=list_endpoints_id,
            method="GET",
            path="/api/endpoints",
            required_fields=["operations"],
        ),
        schema_id: _base_read_descriptor(
            operation_id=schema_id,
            method="GET",
            path="/api/endpoints/{operation_id}/schema",
            required_fields=["operation_id", "request"],
        ),
        defaults_id: _base_read_descriptor(
            operation_id=defaults_id,
            method="GET",
            path="/api/endpoints/{operation_id}/defaults",
            required_fields=["operation_id", "resolved_defaults"],
        ),
        errors_id: _base_read_descriptor(
            operation_id=errors_id,
            method="GET",
            path="/api/endpoints/{operation_id}/errors",
            required_fields=["operation_id", "errors"],
        ),
    }

    operations[create_id] = {
        "operation_id": create_id,
        "run_scoped": False,
        "method": "POST",
        "path": "/create/",
        "config_catalog_url": config_catalog_url,
        "accepted_auth": ["rq_token", "bearer_jwt", "session_cookie_same_origin", "captcha"],
        "auth_requirements": {
            "rq_token": {"required_scope": ["rq:enqueue"]},
            "bearer_jwt": {"required_scope": ["rq:enqueue"]},
            "session_cookie_same_origin": {"same_origin_required": True},
            "captcha": {
                "challenge_required": True,
                "required_if_no_authenticated_token": True,
            },
        },
        "error_catalog_url": f"/api/endpoints/{create_id}/errors",
        "write_precondition": {
            "required": False,
            "accepted": [],
            "conflict_status_code": 409,
            "conflict_error_code": "stale_run_state",
        },
        "idempotency_policy": {
            "supported": False,
            "key_locations": [],
            "dedupe_window_seconds": 0,
            "replay_behavior": "not_supported",
            "mismatch_status_code": 409,
            "mismatch_error_code": "idempotency_key_conflict",
        },
        "execution_mode": "sync_redirect",
        "returns_job": False,
        "job_key": None,
        "content_types": ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
        "file_fields": [],
        "success_status_codes": [303],
        "response_mode": "redirect",
        "result_contract": {
            "kind": "sync_redirect",
            "required_response_fields": [],
            "location_header_required": True,
            "terminal_signal": "http_status_303",
        },
        "estimated_duration": {
            "bucket": "fast",
            "typical_seconds": 2,
        },
        "batch_mode_behavior": "n/a",
        "base_project_behavior": "creates_new_run",
        "mutates_controllers": [],
        "invalidates_steps": [],
    }

    ordered_ids = [
        list_configs_id,
        get_config_id,
        create_id,
        list_endpoints_id,
        schema_id,
        defaults_id,
        errors_id,
    ]
    return {operation_id: operations[operation_id] for operation_id in ordered_ids}


def _empty_request_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "additional_properties": False,
    }


@lru_cache(maxsize=1)
def _setup_operation_documents() -> dict[str, dict[str, Any]]:
    config_ids = [metadata.config_id for metadata in _load_config_catalog()]
    default_config = "disturbed9002_wbt" if "disturbed9002_wbt" in config_ids else (config_ids[0] if config_ids else None)

    list_configs_id = rq_operation_id("list_configs")
    get_config_id = rq_operation_id("get_config")
    list_endpoints_id = rq_operation_id("list_setup_endpoints")
    schema_id = rq_operation_id("get_setup_endpoint_schema")
    defaults_id = rq_operation_id("get_setup_endpoint_defaults")
    errors_id = rq_operation_id("get_setup_endpoint_errors")
    create_id = rq_operation_id("create")

    docs: dict[str, dict[str, Any]] = {
        list_configs_id: {
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["configs"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {"query_filters_supported": []},
            },
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {
                    "error_code": "forbidden",
                    "recoverable": True,
                    "http_statuses": [403],
                    "recovery_actions": [],
                },
            ],
        },
        get_config_id: {
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "path_parameters": {
                        "config": {
                            "type": "string",
                            "required": True,
                            "dynamic_enum_from": "/api/configs",
                        }
                    },
                },
                "responses": {"success": {"required": ["config"]}},
            },
            "defaults": {
                "resolved_defaults": {"config": default_config},
                "defaults_context": {"config_count": len(config_ids)},
            },
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
                {
                    "error_code": "not_found",
                    "recoverable": True,
                    "http_statuses": [404],
                    "recovery_actions": [
                        {"operation_id": list_configs_id, "required_fields": []},
                    ],
                },
            ],
        },
        list_endpoints_id: {
            "schema": {
                "schema_version": 1,
                "request": _empty_request_schema(),
                "responses": {"success": {"required": ["operations"]}},
            },
            "defaults": {
                "resolved_defaults": {},
                "defaults_context": {"operation_count": len(_setup_operation_registry())},
            },
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
            ],
        },
        schema_id: {
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "path_parameters": {"operation_id": {"type": "string", "required": True}},
                },
                "responses": {"success": {"required": ["operation_id", "request"]}},
            },
            "defaults": {"resolved_defaults": {}, "defaults_context": {"schema_version": 1}},
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
                {
                    "error_code": "not_found",
                    "recoverable": True,
                    "http_statuses": [404],
                    "recovery_actions": [
                        {"operation_id": list_endpoints_id, "required_fields": []},
                    ],
                },
            ],
        },
        defaults_id: {
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "path_parameters": {"operation_id": {"type": "string", "required": True}},
                },
                "responses": {"success": {"required": ["operation_id", "resolved_defaults"]}},
            },
            "defaults": {"resolved_defaults": {}, "defaults_context": {"defaults_mode": "deployment_scoped"}},
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
                {
                    "error_code": "not_found",
                    "recoverable": True,
                    "http_statuses": [404],
                    "recovery_actions": [
                        {"operation_id": list_endpoints_id, "required_fields": []},
                    ],
                },
            ],
        },
        errors_id: {
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "path_parameters": {"operation_id": {"type": "string", "required": True}},
                },
                "responses": {"success": {"required": ["operation_id", "errors"]}},
            },
            "defaults": {"resolved_defaults": {}, "defaults_context": {"error_catalog": "stable"}},
            "errors": [
                {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
                {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
                {
                    "error_code": "not_found",
                    "recoverable": True,
                    "http_statuses": [404],
                    "recovery_actions": [
                        {"operation_id": list_endpoints_id, "required_fields": []},
                    ],
                },
            ],
        },
        create_id: {
            "schema": {
                "schema_version": 1,
                "request": {
                    "type": "object",
                    "required": ["config"],
                    "properties": {
                        "config": {
                            "type": "string",
                            "catalog_url": "/api/configs",
                            "dynamic_enum_from": "/api/configs",
                            "enum": config_ids,
                        },
                        "rq_token": {"type": "string"},
                        "cap_token": {"type": "string"},
                    },
                    "additional_properties": True,
                },
                "responses": {
                    "success": {
                        "required": [],
                        "location_header_required": True,
                    }
                },
            },
            "defaults": {
                "resolved_defaults": {"config": default_config},
                "defaults_context": {
                    "config_count": len(config_ids),
                    "default_resolution": (
                        "prefer_disturbed9002_wbt"
                        if default_config == "disturbed9002_wbt"
                        else "first_sorted_config"
                    ),
                },
            },
            "errors": [
                {
                    "error_code": "validation_error",
                    "recoverable": True,
                    "http_statuses": [400],
                    "recovery_actions": [{"operation_id": create_id, "required_fields": ["config"]}],
                },
                {
                    "error_code": "unauthorized",
                    "recoverable": True,
                    "http_statuses": [401],
                    "recovery_actions": [],
                },
                {
                    "error_code": "forbidden",
                    "recoverable": True,
                    "http_statuses": [403],
                    "recovery_actions": [],
                },
                {
                    "error_code": "captcha_required",
                    "recoverable": True,
                    "http_statuses": [403],
                    "recovery_actions": [{"operation_id": create_id, "required_fields": ["cap_token"]}],
                },
                {
                    "error_code": "captcha_verification_failed",
                    "recoverable": True,
                    "http_statuses": [403, 500],
                    "recovery_actions": [{"operation_id": create_id, "required_fields": ["cap_token"]}],
                },
            ],
        },
    }
    return docs


def _resolve_operation_descriptor(operation_id: str) -> dict[str, Any] | None:
    return _setup_operation_registry().get(operation_id)


def _resolve_operation_docs(operation_id: str) -> dict[str, Any] | None:
    return _setup_operation_documents().get(operation_id)


@router.get(
    "/configs",
    summary="List setup configs",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup metadata; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("list_configs"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Config catalog returned.",
    ),
)
def list_configs(request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup list-configs auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        payload = _base_payload()
        payload["configs"] = [_config_to_payload(metadata) for metadata in _load_config_catalog()]
        return JSONResponse(payload)
    except Exception:
        logger.exception("rq-engine setup list-configs failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/configs/{config}",
    summary="Get setup config",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup metadata; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("get_config"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Config metadata returned.",
        extra={404: "Config not found. Returns the canonical error payload."},
    ),
)
def get_config(config: str, request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup get-config auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        metadata = _config_lookup().get(config)
        if metadata is None:
            return error_response(
                f"Unknown config '{config}'",
                status_code=404,
                code="not_found",
            )

        payload = _base_payload()
        payload["config"] = _config_to_payload(metadata)
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine setup get-config failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/endpoints",
    summary="List setup endpoints",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup endpoint catalog; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("list_setup_endpoints"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Setup operation catalog returned.",
    ),
)
def list_setup_endpoints(request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup list-endpoints auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        payload = _base_payload()
        payload["operations"] = [copy.deepcopy(descriptor) for descriptor in _setup_operation_registry().values()]
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine setup list-endpoints failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/endpoints/{operation_id}/schema",
    summary="Get setup schema",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup schema lookup; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("get_setup_endpoint_schema"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Setup operation schema returned.",
        extra={404: "Operation not found. Returns the canonical error payload."},
    ),
)
def get_setup_endpoint_schema(operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup schema auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        descriptor = _resolve_operation_descriptor(operation_id)
        docs = _resolve_operation_docs(operation_id)
        if descriptor is None or docs is None:
            return error_response(
                f"Unknown operation_id '{operation_id}'",
                status_code=404,
                code="not_found",
            )

        payload = _base_payload()
        payload.update(
            {
                "operation_id": descriptor["operation_id"],
                "run_scoped": descriptor["run_scoped"],
                "method": descriptor["method"],
                "path": descriptor["path"],
                "operation_descriptor": copy.deepcopy(descriptor),
                "schema_version": docs["schema"]["schema_version"],
                "request": copy.deepcopy(docs["schema"]["request"]),
                "responses": copy.deepcopy(docs["schema"]["responses"]),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine setup schema failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/endpoints/{operation_id}/defaults",
    summary="Get setup defaults",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup defaults; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("get_setup_endpoint_defaults"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Setup operation defaults returned.",
        extra={404: "Operation not found. Returns the canonical error payload."},
    ),
)
def get_setup_endpoint_defaults(operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup defaults auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        descriptor = _resolve_operation_descriptor(operation_id)
        docs = _resolve_operation_docs(operation_id)
        if descriptor is None or docs is None:
            return error_response(
                f"Unknown operation_id '{operation_id}'",
                status_code=404,
                code="not_found",
            )

        defaults_doc = copy.deepcopy(docs["defaults"])
        defaults_doc["computed_at"] = _utc_timestamp()

        payload = _base_payload()
        payload.update(
            {
                "operation_id": descriptor["operation_id"],
                "resolved_defaults": defaults_doc["resolved_defaults"],
                "defaults_context": defaults_doc["defaults_context"],
                "computed_at": defaults_doc["computed_at"],
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine setup defaults failed")
        return error_response("Error Handling Request", status_code=500)


@router.get(
    "/endpoints/{operation_id}/errors",
    summary="Get setup errors",
    description=(
        "Requires JWT Bearer (`rq:status` or `rq:read`). "
        "Read-only setup error taxonomy; no queue."
    ),
    tags=["rq-engine", "setup"],
    operation_id=rq_operation_id("get_setup_endpoint_errors"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Setup operation error catalog returned.",
        extra={404: "Operation not found. Returns the canonical error payload."},
    ),
)
def get_setup_endpoint_errors(operation_id: str, request: Request) -> JSONResponse:
    try:
        _require_setup_claims(request)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine setup errors auth failed")
        return error_response("Failed to authorize request", status_code=401)

    try:
        descriptor = _resolve_operation_descriptor(operation_id)
        docs = _resolve_operation_docs(operation_id)
        if descriptor is None or docs is None:
            return error_response(
                f"Unknown operation_id '{operation_id}'",
                status_code=404,
                code="not_found",
            )

        payload = _base_payload()
        payload.update(
            {
                "operation_id": descriptor["operation_id"],
                "errors": copy.deepcopy(docs["errors"]),
            }
        )
        return JSONResponse(payload)
    except Exception:  # broad-except: route boundary contract
        logger.exception("rq-engine setup errors failed")
        return error_response("Error Handling Request", status_code=500)


__all__ = ["router"]
