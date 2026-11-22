"""Shared read and mutation descriptors for run operation discovery."""

from __future__ import annotations

import os
from typing import Any

from .schema_defaults_runtime import (
    RuntimeState,
    SCHEMA_DEFAULTS_ALLOWED_SCOPES,
    SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT,
    SESSION_TOKEN_IDEMPOTENCY_TTL_ENV,
)


def _session_token_idempotency_window_seconds() -> int:
    raw = str(os.getenv(SESSION_TOKEN_IDEMPOTENCY_TTL_ENV) or "").strip()
    if not raw:
        return SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return SESSION_TOKEN_IDEMPOTENCY_TTL_DEFAULT


def _read_auth_requirements() -> dict[str, Any]:
    return {
        "bearer_jwt": {
            "required_any_scope": sorted(SCHEMA_DEFAULTS_ALLOWED_SCOPES),
        }
    }


def _empty_request_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "additional_properties": False,
    }


def _predicate(field: str, op: str, value: Any) -> dict[str, Any]:
    return {
        "field": field,
        "op": op,
        "value": value,
    }


def _sbs_available_if() -> dict[str, Any]:
    return {
        "any": [
            _predicate("context.active_mods", "contains", "disturbed"),
            _predicate("context.active_mods", "contains", "baer"),
            _predicate("context.active_mods", "contains", "ash"),
            _predicate("context.active_mods", "contains", "debris_flow"),
        ]
    }


def _rusle_available_if() -> dict[str, Any]:
    return {
        "any": [
            _predicate("context.active_mods", "contains", "disturbed"),
            _predicate("context.active_mods", "contains", "baer"),
        ]
    }


def _base_run_read_descriptor(
    *,
    runtime: RuntimeState,
    operation_id: str,
    path: str,
    required_fields: list[str],
) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "run_scoped": True,
        "method": "GET",
        "path": path,
        "accepted_auth": ["bearer_jwt"],
        "auth_requirements": _read_auth_requirements(),
        "required_if": [],
        "available_if": [],
        "error_catalog_url": (
            f"/api/runs/{runtime.runid}/{runtime.config}/endpoints/{operation_id}/errors"
        ),
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
        "base_project_behavior": "allowed",
        "mutates_controllers": [],
        "invalidates_steps": [],
    }


def _mutation_idempotency_policy(
    idempotency_supported: bool,
    idempotency_dedupe_window_seconds: int | None,
    replay_behavior: str,
) -> dict[str, Any]:
    resolved_replay_behavior = replay_behavior if idempotency_supported else "not_supported"

    dedupe_window_seconds = (
        int(idempotency_dedupe_window_seconds)
        if idempotency_dedupe_window_seconds is not None and idempotency_supported
        else 86400
    )

    idempotency_policy: dict[str, Any] = {
        "supported": idempotency_supported,
        "key_locations": ["header:Idempotency-Key"] if idempotency_supported else [],
        "dedupe_window_seconds": dedupe_window_seconds if idempotency_supported else 0,
        "replay_behavior": resolved_replay_behavior,
        "mismatch_status_code": 409,
        "mismatch_error_code": "idempotency_key_conflict",
    }
    if idempotency_supported and resolved_replay_behavior == "reject_duplicate":
        idempotency_policy["duplicate_replay_status_code"] = 409
        idempotency_policy["duplicate_replay_error_code"] = "idempotency_replay_rejected"
    return idempotency_policy


def _mutation_result_contract(
    execution_mode: str,
    required_fields: list[str],
    async_poll_url_field: str | None,
) -> dict[str, Any]:
    result_contract: dict[str, Any] = {
        "kind": "sync_result",
        "required_response_fields": required_fields,
        "terminal_signal": "http_status_2xx",
    }
    if execution_mode == "async":
        result_contract = {
            "kind": "async_job",
            "required_response_fields": required_fields,
            "terminal_signal": "jobstatus.status in terminal_*_statuses",
            "status_field": "status",
            "non_terminal_statuses": ["queued", "started", "deferred", "scheduled"],
            "terminal_success_statuses": ["finished"],
            "terminal_failure_statuses": ["failed", "stopped", "canceled"],
            "suggested_poll_interval_seconds": 5,
            "progress_field": "progress",
        }
        if async_poll_url_field:
            result_contract["next_poll_url_field"] = async_poll_url_field
        else:
            result_contract["status_url_template"] = "/api/jobstatus/{job_id}"
    return result_contract


def _base_run_mutation_descriptor(
    *,
    runtime: RuntimeState,
    operation_id: str,
    path: str,
    execution_mode: str,
    returns_job: bool,
    job_key: str | None,
    required_fields: list[str],
    estimated_duration_bucket: str,
    estimated_duration_seconds: int,
    mutates_controllers: list[str],
    invalidates_steps: list[str],
    content_types: list[str] | None = None,
    file_fields: list[dict[str, Any]] | None = None,
    auth_requirements: dict[str, Any] | None = None,
    accepted_auth: list[str] | None = None,
    write_precondition_required: bool = False,
    write_precondition_accepted: list[str] | None = None,
    idempotency_supported: bool = False,
    idempotency_dedupe_window_seconds: int | None = None,
    replay_behavior: str = "return_original_success",
    required_if: list[dict[str, Any]] | None = None,
    available_if: list[dict[str, Any]] | None = None,
    batch_mode_behavior: str = "n/a",
    base_project_behavior: str = "allowed",
    async_poll_url_field: str | None = None,
) -> dict[str, Any]:
    descriptor_auth_requirements = auth_requirements or {
        "bearer_jwt": {
            "required_scope": ["rq:enqueue"],
        }
    }
    descriptor_accepted_auth = accepted_auth or ["bearer_jwt"]
    accepted_preconditions = (
        write_precondition_accepted
        if write_precondition_accepted is not None
        else (["x_run_state_match", "expected_run_state_revision"] if write_precondition_required else [])
    )

    return {
        "operation_id": operation_id,
        "run_scoped": True,
        "method": "POST",
        "path": path,
        "accepted_auth": descriptor_accepted_auth,
        "auth_requirements": descriptor_auth_requirements,
        "required_if": required_if or [],
        "available_if": available_if or [],
        "error_catalog_url": (
            f"/api/runs/{runtime.runid}/{runtime.config}/endpoints/{operation_id}/errors"
        ),
        "write_precondition": {
            "required": write_precondition_required,
            "accepted": accepted_preconditions,
            "conflict_status_code": 409,
            "conflict_error_code": "stale_run_state",
        },
        "idempotency_policy": _mutation_idempotency_policy(
            idempotency_supported, idempotency_dedupe_window_seconds, replay_behavior
        ),
        "execution_mode": execution_mode,
        "returns_job": returns_job,
        "job_key": job_key,
        "content_types": content_types or ["application/json", "application/x-www-form-urlencoded"],
        "file_fields": file_fields or [],
        "success_status_codes": [200],
        "response_mode": "json",
        "result_contract": _mutation_result_contract(execution_mode, required_fields, async_poll_url_field),
        "estimated_duration": {
            "bucket": estimated_duration_bucket,
            "typical_seconds": estimated_duration_seconds,
        },
        "batch_mode_behavior": batch_mode_behavior,
        "base_project_behavior": base_project_behavior,
        "mutates_controllers": mutates_controllers,
        "invalidates_steps": invalidates_steps,
    }


def _defaults_context(runtime: RuntimeState) -> dict[str, Any]:
    return {
        "config": runtime.config,
        "active_mods": list(runtime.active_mods),
        "region": runtime.region,
    }


def _operation_document(
    runtime: RuntimeState,
    descriptor: dict[str, Any],
    *,
    request: dict[str, Any],
    resolved_defaults: dict[str, Any] | None = None,
    defaults_context: dict[str, Any] | None = None,
    schema_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish the descriptor's success contract in the operation schema as well."""
    required = descriptor["result_contract"]["required_response_fields"]
    return {
        "descriptor": descriptor,
        "schema": {
            "schema_version": 1,
            **(schema_fields or {}),
            "request": request,
            "responses": {"success": {"required": list(required)}},
        },
        "defaults": {
            "resolved_defaults": resolved_defaults if resolved_defaults is not None else {},
            "defaults_context": (
                defaults_context if defaults_context is not None else _defaults_context(runtime)
            ),
        },
    }
