"""Operation discovery documents for climate and soil builds."""

from __future__ import annotations

import copy
from typing import Any

from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
)
from wepppy.nodb.project_config_capabilities import SOIL_BUILDER_MODES

from .openapi import rq_operation_id
from .schema_defaults_controllers import _controller_defaults
from .schema_defaults_controllers_schema import _controller_schema
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _operation_document,
    _predicate,
)
from .schema_defaults_fields import (
    _climate_mode_for_dataset,
    _default_disturbed_sol_ver,
    _disturbed_sol_ver_options,
    _domain_capability_graph,
    _operation_capability_authority,
    _runtime_method_field,
    _soil_mode_field,
)
from .schema_defaults_runtime import RuntimeState


def _climate_selection_properties(
    runtime: RuntimeState,
    climate_controller_fields: dict[str, Any],
) -> dict[str, Any]:
    if runtime.capability_graph is None:
        if runtime.v1_capabilities and "climate_datasets" in runtime.v1_capabilities:
            return {
                "climate_catalog_id": {
                    "type": "string",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "project_capability_axis_v1",
                    "resolved_at": runtime.generated_at,
                    "enum": list(runtime.v1_capabilities["climate_datasets"]),
                },
            }
        return {}

    return {
        "climate_catalog_id": {
            **copy.deepcopy(
                climate_controller_fields["climate_catalog_id"]
            ),
            "required_for_new_selection": True,
            "runtime_mode_by_value": {
                catalog_id: _climate_mode_for_dataset(catalog_id)
                for catalog_id in runtime.capability_graph.climate_datasets
            },
        },
        "climate_station_method": {
            **copy.deepcopy(
                climate_controller_fields["climate_station_method"]
            ),
        },
        "climate_spatial_method": {
            **copy.deepcopy(
                climate_controller_fields["climate_spatial_method"]
            ),
        },
        "climatestation_mode": {
            **_runtime_method_field(
                climate_controller_fields["climate_station_method"],
                CLIMATE_STATION_METHOD_RUNTIME,
                relation_key="allowed_by_climate_catalog_id",
                defaults_key="defaults_by_climate_catalog_id",
                current_runtime_value=(
                    int(runtime.states["climate_station_mode_code"])
                    if runtime.states.get("climate_station_mode_code") is not None
                    else None
                ),
            ),
        },
        "climate_spatialmode": {
            **_runtime_method_field(
                climate_controller_fields["climate_spatial_method"],
                CLIMATE_SPATIAL_METHOD_RUNTIME,
                relation_key="allowed_by_climate_catalog_id",
                defaults_key="defaults_by_climate_catalog_id",
                current_runtime_value=(
                    int(runtime.states["climate_spatial_mode_code"])
                    if runtime.states.get("climate_spatial_mode_code") is not None
                    else None
                ),
            ),
        },
    }


def build_climate(runtime: RuntimeState) -> dict[str, Any]:
    climate_controller_fields = _controller_schema("climate", runtime)["fields"]
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("build_climate"),
            path="/api/runs/{runid}/{config}/build-climate",
            execution_mode="async",
            returns_job=True,
            job_key="build_climate_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=120,
            mutates_controllers=["climate"],
            invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="batch_returns_message_no_queue",
        ),
        schema_fields=(
            {"capability_authority": _operation_capability_authority(runtime)}
            if runtime.capability_graph is not None
            else {}
        ),
        request={
            "type": "object",
            "properties": {
                **_climate_selection_properties(runtime, climate_controller_fields),
                "climate_mode": {
                    **copy.deepcopy(climate_controller_fields["climate_mode"]),
                },
                "climatestation": {
                    "type": "string",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "available_if": _predicate("climate_mode", "in", [2, 6]),
                    "required_if": _predicate("climate_mode", "in", [2, 6]),
                },
                "observed_start_year": {
                    "type": "integer",
                    "minimum": 1900,
                    "maximum": 2100,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [2, 9, 11, 16]),
                },
                "observed_end_year": {
                    "type": "integer",
                    "minimum": 1900,
                    "maximum": 2100,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [2, 9, 11, 16]),
                },
                "edde_projection": {
                    "type": "string",
                    "enum": ["WRF-MPI/SSP2-4.5", "WRF-MPI/SSP3-7.0", "WRF-Nor/SSP2-4.5"],
                    "required_if": _predicate("climate_mode", "eq", 17),
                    "description": "Future EDDE full years: 2025–2099 for MPI; 2025–2079 for Nor.",
                },
                "future_start_year": {
                    "type": "integer",
                    "minimum": 2006,
                    "maximum": 2099,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [3, 17]),
                },
                "future_end_year": {
                    "type": "integer",
                    "minimum": 2006,
                    "maximum": 2099,
                    "constraint_mode": "static",
                    "required_if": _predicate("climate_mode", "in", [3, 17]),
                },
            },
            "additional_properties": True,
        },
        resolved_defaults=_controller_defaults("climate", runtime),
    )


def build_soils(runtime: RuntimeState) -> dict[str, Any]:
    disturbed_enabled = bool(runtime.states.get("disturbed_enabled", False))
    disturbed_sol_ver_options = _disturbed_sol_ver_options(runtime)
    build_soils_required_fields = ["initial_sat", "sol_ver"] if disturbed_enabled else ["initial_sat"]
    build_soil_mode_field = _soil_mode_field(runtime, runtime_values=True)
    build_soil_mode_default = build_soil_mode_field.get("current_value")
    soil_graph = _domain_capability_graph(runtime, "soil")
    if build_soil_mode_default is None and soil_graph is not None:
        soil_dataset = soil_graph.defaults["soil_dataset"]
        build_soil_mode_default = SOIL_BUILDER_MODES[
            soil_graph.soil_builder_defaults[soil_dataset]
        ]
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("build_soils"),
            path="/api/runs/{runid}/{config}/build-soils",
            execution_mode="async",
            content_types=["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
            returns_job=True,
            job_key="build_soils_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=120,
            mutates_controllers=["soils"],
            invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="batch_returns_message_no_queue",
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_single_soil": {
                    "type": "string", "format": "binary", "constraint_mode": "static",
                    "description": "Single User-Defined mode 5 only, with project opt-in. Version 7778; one OFE; .sol/.SOL; maximum 5 MiB. Omit to reuse the accepted source.",
                },
                "soil_mode": {
                    **copy.deepcopy(build_soil_mode_field),
                },
                "mode": {
                    **copy.deepcopy(build_soil_mode_field),
                    "alias_of": "soil_mode",
                },
                "initial_sat": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "clear_ssurgo_cache_on_rebuild": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "sol_ver": {
                    "type": "number",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": runtime.generated_at,
                    "enum_available": disturbed_sol_ver_options,
                    "available_if": _predicate("context.active_mods", "contains", "disturbed"),
                    "required_if": _predicate("context.active_mods", "contains", "disturbed"),
                },
            },
            "required": build_soils_required_fields,
            "additional_properties": True,
        },
        resolved_defaults={
            **(
                {
                    "soil_mode": build_soil_mode_default,
                    "mode": build_soil_mode_default,
                }
                if build_soil_mode_default is not None
                else {}
            ),
            **{
                "initial_sat": (
                    runtime.states.get("initial_sat")
                    if runtime.states.get("initial_sat") is not None
                    else 0.75
                )
            },
            "clear_ssurgo_cache_on_rebuild": bool(
                runtime.states.get("clear_ssurgo_cache_on_rebuild", False)
            ),
            **(
                {
                    "sol_ver": (
                        runtime.states.get("disturbed_sol_ver")
                        if runtime.states.get("disturbed_sol_ver") is not None
                        else _default_disturbed_sol_ver(runtime)
                    )
                }
                if disturbed_enabled
                else {}
            ),
        },
    )
