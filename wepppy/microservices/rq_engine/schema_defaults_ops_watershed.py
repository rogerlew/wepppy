"""Operation discovery documents for watershed delineation."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _defaults_context,
    _operation_document,
    _predicate,
)
from .schema_defaults_fields import _resolved_watershed_defaults
from .schema_defaults_runtime import RuntimeState


def fetch_dem_and_build_channels(runtime: RuntimeState, geospatial_defaults: dict[str, Any]) -> dict[str, Any]:
    map_bounds_default = geospatial_defaults.get("map_bounds")
    map_center_default = geospatial_defaults.get("map_center")
    map_zoom_default = geospatial_defaults.get("map_zoom")
    watershed_defaults = _resolved_watershed_defaults(runtime)
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("fetch_dem_and_build_channels"),
            path="/api/runs/{runid}/{config}/fetch-dem-and-build-channels",
            execution_mode="async",
            returns_job=True,
            job_key="fetch_dem_and_build_channels_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="slow",
            estimated_duration_seconds=180,
            mutates_controllers=["watershed"],
            invalidates_steps=[
                "set-outlet",
                "build-subcatchments-and-abstract-watershed",
                "build-climate",
                "build-landuse",
                "build-soils",
                "prep-wepp-watershed",
                "run-wepp",
                "run-wepp-watershed",
            ],
            batch_mode_behavior="batch_returns_message_no_queue",
            base_project_behavior="base_project_returns_message_no_queue",
        ),
        request={
            "type": "object",
            "properties": {
                "map_bounds": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": runtime.generated_at,
                    "required_if": _predicate("set_extent_mode", "in", [0, 1]),
                },
                "map_center": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": runtime.generated_at,
                    "derived_if_missing": {
                        "field": "map_bounds",
                        "strategy": "bounds_midpoint",
                    },
                },
                "map_zoom": {
                    "type": "number",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": runtime.generated_at,
                    "derived_if_missing": {
                        "field": "map_bounds",
                        "strategy": "bounds_fit_zoom",
                    },
                },
                "csa": {
                    "type": "number",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": runtime.generated_at,
                },
                "mcl": {
                    "type": "number",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": runtime.generated_at,
                },
                "set_extent_mode": {
                    "type": "integer",
                    "constraint_mode": "static",
                    "enum": [0, 1, 2, 3],
                },
                "map_object": {
                    "type": "object",
                    "constraint_mode": "static",
                    "required_if": _predicate("set_extent_mode", "eq", 2),
                },
                "map_bounds_text": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "wbt_fill_or_breach": {
                    "type": "string",
                    "constraint_mode": "static",
                    "enum": [
                        "fill",
                        "breach",
                        "breach_least_cost",
                        "topaz",
                    ],
                },
                "stream_pruning_method": {
                    "type": "string",
                    "constraint_mode": "static",
                    "enum": ["ifolp", "remove_short_streams"],
                },
                "wbt_blc_dist": {
                    "type": "integer",
                    "constraint_mode": "static",
                },
            },
            "required": ["mcl", "csa"],
            "additional_properties": True,
        },
        resolved_defaults={
            "map_bounds": map_bounds_default,
            "map_center": map_center_default,
            "map_zoom": map_zoom_default,
            "csa": watershed_defaults["csa"],
            "mcl": watershed_defaults["mcl"],
            "stream_pruning_method": watershed_defaults["stream_pruning_method"],
            "set_extent_mode": 0,
        },
        defaults_context={
            **_defaults_context(runtime),
            "derived_map_fields": ["map_center", "map_zoom"],
        },
    )


def set_outlet(runtime: RuntimeState, geospatial_defaults: dict[str, Any]) -> dict[str, Any]:
    map_center_default = geospatial_defaults.get("map_center")
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("set_outlet"),
            path="/api/runs/{runid}/{config}/set-outlet",
            execution_mode="async",
            returns_job=True,
            job_key="set_outlet_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=20,
            mutates_controllers=["watershed"],
            invalidates_steps=[
                "build-subcatchments-and-abstract-watershed",
                "build-climate",
                "build-landuse",
                "build-soils",
                "prep-wepp-watershed",
                "run-wepp",
                "run-wepp-watershed",
            ],
        ),
        request={
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "longitude": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "coordinates": {
                    "type": "object",
                    "constraint_mode": "static",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                        "lon": {"type": "number"},
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "additional_properties": True,
                },
            },
            "additional_properties": True,
        },
        resolved_defaults={
            "latitude": float(map_center_default[1]),
            "longitude": float(map_center_default[0]),
        }
        if isinstance(map_center_default, list) and len(map_center_default) == 2
        else {},
    )


def build_subcatchments_and_abstract_watershed(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("build_subcatchments_and_abstract_watershed"),
            path="/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed",
            execution_mode="async",
            returns_job=True,
            job_key="build_subcatchments_and_abstract_watershed_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="slow",
            estimated_duration_seconds=240,
            mutates_controllers=["watershed"],
            invalidates_steps=[
                "build-climate",
                "build-landuse",
                "build-soils",
                "prep-wepp-watershed",
                "run-wepp",
                "run-wepp-watershed",
            ],
            batch_mode_behavior="batch_returns_message_no_queue",
            base_project_behavior="base_project_returns_message_no_queue",
        ),
        request={
            "type": "object",
            "properties": {
                "clip_hillslopes": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "walk_flowpaths": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "clip_hillslope_length": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "mofe_target_length": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "mofe_buffer": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "mofe_buffer_length": {
                    "type": "number",
                    "constraint_mode": "static",
                },
                "mofe_max_ofes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 19,
                    "constraint_mode": "static",
                },
                "bieger2015_widths": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
    )
