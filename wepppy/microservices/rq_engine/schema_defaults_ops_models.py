"""Operation discovery documents for model runs."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_controllers import _controller_defaults
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _operation_document,
    _predicate,
    _rusle_available_if,
)
from .schema_defaults_fields import (
    _model_operation_capability_authority,
    _model_tuple_binaries_for_runtime,
)
from .schema_defaults_runtime import RuntimeState


def prep_wepp_watershed(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("prep_wepp_watershed"),
            path="/api/runs/{runid}/{config}/prep-wepp-watershed",
            execution_mode="async",
            returns_job=True,
            job_key="prep_wepp_watershed_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=90,
            mutates_controllers=["wepp"],
            invalidates_steps=["run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="batch_returns_message_no_queue",
            base_project_behavior="base_project_returns_message_no_queue",
        ),
        request={
            "type": "object",
            "properties": {
                "clip_soils": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "clip_soils_depth": {
                    "type": "number",
                    "minimum": 0.0,
                    "constraint_mode": "static",
                    "available_if": _predicate("clip_soils", "eq", True),
                    "required_if": _predicate("clip_soils", "eq", True),
                },
                "initial_sat": {
                    "type": "number",
                    "constraint_mode": "static",
                }
            },
            "additional_properties": True,
        },
        resolved_defaults=_controller_defaults("wepp", runtime),
    )


def _wepp_binary_properties(runtime: RuntimeState) -> dict[str, Any]:
    if runtime.model_capability_graph is not None or runtime.wepp_binary_options is not None:
        source = (
            "installed_release_capabilities"
            if runtime.wepp_binary_options is not None
            else "project_capability_graph"
        )
        binaries = _model_tuple_binaries_for_runtime(runtime)
    elif runtime.v1_capabilities and "wepp_binaries" in runtime.v1_capabilities:
        source = "project_capability_axis_v1"
        binaries = list(runtime.v1_capabilities["wepp_binaries"])
    else:
        return {}

    return {
        "wepp_bin": {
            "type": "string",
            "constraint_mode": "run_resolved",
            "constraint_source": source,
            "resolved_at": runtime.generated_at,
            "enum": binaries,
        },
    }


def run_wepp(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("run_wepp"),
            path="/api/runs/{runid}/{config}/run-wepp",
            execution_mode="async",
            returns_job=True,
            job_key="run_wepp_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="slow",
            estimated_duration_seconds=300,
            mutates_controllers=["wepp", "soils"],
            invalidates_steps=["run-wepp-watershed"],
            batch_mode_behavior="batch_returns_message_no_queue",
            base_project_behavior="base_project_returns_message_no_queue",
        ),
        schema_fields=(
            {"capability_authority": _model_operation_capability_authority(runtime)}
            if runtime.model_capability_graph is not None
            else {}
        ),
        request={
            "type": "object",
            "properties": {
                **_wepp_binary_properties(runtime),
                "clip_soils": {
                    "type": "boolean",
                    "constraint_mode": "static",
                    "source_controller": "soils",
                },
                "clip_soils_depth": {
                    "type": "number",
                    "minimum": 0.0,
                    "constraint_mode": "static",
                    "source_controller": "soils",
                    "available_if": _predicate("clip_soils", "eq", True),
                    "required_if": _predicate("clip_soils", "eq", True),
                },
                "initial_sat": {
                    "type": "number",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
        resolved_defaults={
            **_controller_defaults("wepp", runtime),
        },
    )


def run_wepp_watershed(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("run_wepp_watershed"),
            path="/api/runs/{runid}/{config}/run-wepp-watershed",
            execution_mode="async",
            returns_job=True,
            job_key="run_wepp_watershed_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="slow",
            estimated_duration_seconds=300,
            mutates_controllers=["wepp"],
            invalidates_steps=[],
            batch_mode_behavior="batch_returns_message_no_queue",
            base_project_behavior="base_project_returns_message_no_queue",
        ),
        schema_fields=(
            {"capability_authority": _model_operation_capability_authority(runtime)}
            if runtime.model_capability_graph is not None
            else {}
        ),
        request={
            "type": "object",
            "properties": {
                **_wepp_binary_properties(runtime),
                "clip_soils": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "clip_soils_depth": {
                    "type": "number",
                    "minimum": 0.0,
                    "constraint_mode": "static",
                    "available_if": _predicate("clip_soils", "eq", True),
                    "required_if": _predicate("clip_soils", "eq", True),
                },
                "initial_sat": {
                    "type": "number",
                    "constraint_mode": "static",
                }
            },
            "additional_properties": True,
        },
        resolved_defaults=_controller_defaults("wepp", runtime),
    )


def build_rusle(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("build_rusle"),
            path="/api/runs/{runid}/{config}/build-rusle",
            execution_mode="async",
            returns_job=True,
            job_key="build_rusle_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=120,
            mutates_controllers=["disturbed"],
            invalidates_steps=[],
            batch_mode_behavior="batch_returns_message_no_queue",
            available_if=[_rusle_available_if()],
            required_if=[_rusle_available_if()],
        ),
        request={
            "type": "object",
            "properties": {
                "r_mode": {
                    "type": "integer",
                    "constraint_mode": "static",
                },
                "c_mode": {
                    "type": "integer",
                    "constraint_mode": "static",
                },
                "rap_year": {
                    "type": "integer",
                    "constraint_mode": "static",
                },
                "rock_fraction_of_rap_bare": {
                    "type": "string_or_number",
                    "constraint_mode": "static",
                    "one_of": [
                        {"type": "string", "enum": ["auto"]},
                        {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    ],
                    "available_if": _predicate("c_mode", "eq", "observed_rap"),
                },
                "rock_fraction_of_sbs_bare": {
                    "type": "string_or_number",
                    "constraint_mode": "static",
                    "one_of": [
                        {"type": "string", "enum": ["auto"]},
                        {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    ],
                    "available_if": _predicate("c_mode", "eq", "scenario_sbs"),
                },
                "k_modes": {
                    "type": "array",
                    "constraint_mode": "static",
                },
                "default_k_mode": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "max_slope_length_m": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "p_value": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "force_polaris_refresh": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
        resolved_defaults={
            "force_polaris_refresh": False,
            "rock_fraction_of_rap_bare": "auto",
            "rock_fraction_of_sbs_bare": "auto",
        },
    )
