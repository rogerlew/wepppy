"""Operation discovery documents for session tokens and project forks."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _operation_document,
    _session_token_idempotency_window_seconds,
)
from .schema_defaults_runtime import RuntimeState


def issue_session_token(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("issue_session_token"),
            path="/api/runs/{runid}/{config}/session-token",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["token", "session_id", "runid", "config", "scopes"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=1,
            mutates_controllers=[],
            invalidates_steps=[],
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:status"],
                },
                "session_cookie_same_origin": {
                    "same_origin_required": True,
                    "public_run_fallback": True,
                },
            },
            accepted_auth=["bearer_jwt", "session_cookie_same_origin"],
            write_precondition_required=False,
            write_precondition_accepted=["x_run_state_match", "expected_run_state_revision"],
            idempotency_supported=True,
            idempotency_dedupe_window_seconds=_session_token_idempotency_window_seconds(),
            replay_behavior="reject_duplicate",
            content_types=["application/json"],
        ),
        request={
            "type": "object",
            "properties": {
                "expected_run_state_revision": {
                    "type": "string",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "run_state_revision",
                }
            },
            "additional_properties": True,
        },
    )


def fork_project(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("fork_project"),
            path="/api/runs/{runid}/{config}/fork",
            execution_mode="async",
            returns_job=True,
            job_key="fork_rq",
            required_fields=["job_id", "new_runid", "undisturbify", "skip_wepp_runs_output", "skip_omni_scenarios_contrasts"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=15,
            mutates_controllers=[],
            invalidates_steps=[],
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                },
                "captcha": {
                    "challenge_required": True,
                    "required_if_no_authenticated_token": True,
                },
            },
            accepted_auth=["bearer_jwt", "captcha"],
            content_types=["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
        ),
        request={
            "type": "object",
            "properties": {
                "undisturbify": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "skip_wepp_runs_output": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "skip_omni_scenarios_contrasts": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "target_runid": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "cap_token": {
                    "type": "string",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
        resolved_defaults={"undisturbify": False, "skip_wepp_runs_output": False, "skip_omni_scenarios_contrasts": False},
    )
