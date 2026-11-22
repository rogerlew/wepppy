"""Operation discovery documents for file uploads."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _operation_document,
    _sbs_available_if,
)
from .schema_defaults_runtime import RuntimeState
from .upload_climate_routes import UPLOAD_CLI_ALLOWED_EXTENSIONS, UPLOAD_CLI_MAX_BYTES
from .upload_disturbed_routes import (
    UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS,
    UPLOAD_COVER_TRANSFORM_MAX_BYTES,
    UPLOAD_SBS_ALLOWED_EXTENSIONS,
    UPLOAD_SBS_MAX_BYTES,
)
from .watershed_routes import (
    UPLOAD_DEM_ALLOWED_EXTENSIONS,
    UPLOAD_DEM_MAX_BYTES,
    UPLOAD_DEM_MAX_DIMENSION,
)


def upload_dem(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("upload_dem"),
            path="/api/runs/{runid}/{config}/tasks/upload-dem/",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["result"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=10,
            mutates_controllers=["watershed"],
            invalidates_steps=[
                "fetch-dem-and-build-channels",
                "set-outlet",
                "build-subcatchments-and-abstract-watershed",
                "build-climate",
                "build-landuse",
                "build-soils",
                "prep-wepp-watershed",
                "run-wepp",
                "run-wepp-watershed",
            ],
            content_types=["multipart/form-data"],
            file_fields=[
                {
                    "name": "input_upload_dem",
                    "required": True,
                    "allowed_extensions": [f".{ext}" for ext in UPLOAD_DEM_ALLOWED_EXTENSIONS],
                    "allowed_media_types": ["image/tiff", "application/geotiff", "application/x-geotiff"],
                    "max_bytes": UPLOAD_DEM_MAX_BYTES,
                    "crs_requirements": {
                        "mode": "must_define_spatial_reference",
                        "allow_reprojection": True,
                        "preferred_projection_family": "utm",
                    },
                    "extent_requirements": {
                        "mode": "must_define_georeferenced_extent",
                    },
                    "resolution_requirements": {
                        "mode": "square_pixels_required",
                        "max_dimension_px": UPLOAD_DEM_MAX_DIMENSION,
                    },
                    "value_semantics": {
                        "classification_type": "continuous_elevation",
                        "required_numeric_type": "float32_or_float64",
                    },
                }
            ],
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_dem": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": runtime.generated_at,
                },
            },
            "required": ["input_upload_dem"],
            "additional_properties": True,
        },
    )


def upload_cli(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("upload_cli"),
            path="/api/runs/{runid}/{config}/tasks/upload-cli/",
            execution_mode="async",
            returns_job=True,
            job_key="upload_cli_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=8,
            mutates_controllers=["climate"],
            invalidates_steps=["build-climate", "prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
            content_types=["multipart/form-data"],
            file_fields=[
                {
                    "name": "input_upload_cli",
                    "required": True,
                    "allowed_extensions": [f".{ext}" for ext in UPLOAD_CLI_ALLOWED_EXTENSIONS],
                    "allowed_media_types": ["text/plain", "application/octet-stream"],
                    "max_bytes": UPLOAD_CLI_MAX_BYTES,
                    "value_semantics": {
                        "classification_type": "station_climate_timeseries",
                    },
                }
            ],
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_cli": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "static",
                },
            },
            "required": ["input_upload_cli"],
            "additional_properties": True,
        },
    )


def upload_cover_transform(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("upload_cover_transform"),
            path="/api/runs/{runid}/{config}/tasks/upload-cover-transform",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=[],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=5,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            content_types=["multipart/form-data"],
            file_fields=[
                {
                    "name": "input_upload_cover_transform",
                    "required": True,
                    "allowed_extensions": [f".{ext}" for ext in UPLOAD_COVER_TRANSFORM_ALLOWED_EXTENSIONS],
                    "allowed_media_types": ["text/csv", "application/vnd.ms-excel"],
                    "max_bytes": UPLOAD_COVER_TRANSFORM_MAX_BYTES,
                    "value_semantics": {
                        "classification_type": "cover_transform_table",
                    },
                }
            ],
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_cover_transform": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "static",
                },
            },
            "required": ["input_upload_cover_transform"],
            "additional_properties": True,
        },
    )


def upload_sbs(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("upload_sbs"),
            path="/api/runs/{runid}/{config}/tasks/upload-sbs/",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["result"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=8,
            mutates_controllers=["disturbed", "landuse", "soils"],
            invalidates_steps=["build-landuse", "build-soils", "run-wepp", "run-wepp-watershed"],
            content_types=["multipart/form-data"],
            file_fields=[
                {
                    "name": "input_upload_sbs",
                    "required": True,
                    "allowed_extensions": [f".{ext}" for ext in UPLOAD_SBS_ALLOWED_EXTENSIONS],
                    "allowed_media_types": [],
                    "max_bytes": UPLOAD_SBS_MAX_BYTES,
                    "crs_requirements": {
                        "mode": "must_have_valid_projection",
                    },
                    "value_semantics": {
                        "classification_type": "integer_class_raster",
                        "required_integer_values": True,
                        "max_unique_classes": 256,
                        "color_table_mode": "optional_unknown_colors_unassigned",
                    },
                }
            ],
            required_if=[_sbs_available_if()],
            available_if=[_sbs_available_if()],
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_sbs": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "geospatial_metadata",
                    "resolved_at": runtime.generated_at,
                    "required_if": _sbs_available_if(),
                },
            },
            "required": ["input_upload_sbs"],
            "additional_properties": True,
        },
    )
