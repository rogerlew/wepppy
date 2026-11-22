"""Discovery documents for controller, endpoint, and snapshot reads."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_controllers import _controller_names
from .schema_defaults_descriptors import (
    _base_run_read_descriptor,
    _defaults_context,
    _empty_request_schema,
    _operation_document,
)
from .schema_defaults_runtime import LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM, RuntimeState


def _path_parameter_request(field: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field: {"type": "string", "constraint_mode": "static"}},
        "required": [field],
        "additional_properties": False,
    }


def list_controllers(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("list_controllers"),
            path="/api/runs/{runid}/{config}/controllers",
            required_fields=["controllers"],
        ),
        request=_empty_request_schema(),
        defaults_context={
            "controller_count": len(_controller_names(runtime)),
            **_defaults_context(runtime),
        },
    )


def geospatial_metadata(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("geospatial_metadata"),
            path="/api/runs/{runid}/{config}/geospatial-metadata",
            required_fields=[
                "run_state_domain",
                "run_state_vector",
                "updated_at",
                "data_state",
                "data_updated_at",
                "etag",
                "dem_coverage",
                "recommended_defaults",
                "field_availability",
            ],
        ),
        request=_empty_request_schema(),
    )


def get_controller_schema(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_controller_schema"),
            path="/api/runs/{runid}/{config}/controllers/{controller}/schema",
            required_fields=["controller", "fields"],
        ),
        request=_path_parameter_request("controller"),
        resolved_defaults={
            "controller": "climate",
        },
    )


def get_controller_hints(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_controller_hints"),
            path="/api/runs/{runid}/{config}/controllers/{controller}/hints",
            required_fields=["controller", "hints"],
        ),
        request=_path_parameter_request("controller"),
        resolved_defaults={
            "controller": "climate",
        },
    )


def get_controller_templates(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_controller_templates"),
            path="/api/runs/{runid}/{config}/controllers/{controller}/templates",
            required_fields=["controller", "templates"],
        ),
        request=_path_parameter_request("controller"),
        resolved_defaults={
            "controller": "climate",
        },
    )


def list_run_endpoints(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("list_run_endpoints"),
            path="/api/runs/{runid}/{config}/endpoints",
            required_fields=["operations"],
        ),
        request={
            "type": "object",
            "properties": {
                LIST_RUN_ENDPOINTS_INCLUDE_DOCS_PARAM: {
                    "type": "boolean",
                    "constraint_mode": "static",
                    "required": False,
                    "default": False,
                }
            },
            "additional_properties": False,
        },
        defaults_context={
            **_defaults_context(runtime),
            "operation_count": 0,
        },
    )


def get_run_endpoint_schema(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_run_endpoint_schema"),
            path="/api/runs/{runid}/{config}/endpoints/{operation_id}/schema",
            required_fields=["operation_id", "request"],
        ),
        request=_path_parameter_request("operation_id"),
        resolved_defaults={
            "operation_id": rq_operation_id("build_climate"),
        },
    )


def get_run_endpoint_defaults(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_run_endpoint_defaults"),
            path="/api/runs/{runid}/{config}/endpoints/{operation_id}/defaults",
            required_fields=["operation_id", "resolved_defaults"],
        ),
        request=_path_parameter_request("operation_id"),
        resolved_defaults={
            "operation_id": rq_operation_id("build_climate"),
        },
    )


def get_run_endpoint_errors(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_run_endpoint_errors"),
            path="/api/runs/{runid}/{config}/endpoints/{operation_id}/errors",
            required_fields=["operation_id", "errors"],
        ),
        request=_path_parameter_request("operation_id"),
        resolved_defaults={
            "operation_id": rq_operation_id("build_climate"),
        },
        defaults_context={
            **_defaults_context(runtime),
            "error_catalog": "stable",
        },
    )


def get_pipeline(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_pipeline"),
            path="/api/runs/{runid}/{config}/pipeline",
            required_fields=[
                "run_state_domain",
                "run_state_vector",
                "updated_at",
                "data_state",
                "data_updated_at",
                "etag",
                "steps",
            ],
        ),
        request=_empty_request_schema(),
    )


def get_readiness(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_readiness"),
            path="/api/runs/{runid}/{config}/readiness",
            required_fields=[
                "run_state_domain",
                "run_state_vector",
                "updated_at",
                "data_state",
                "data_updated_at",
                "etag",
                "next_actionable_steps",
            ],
        ),
        request=_empty_request_schema(),
    )


def get_outputs(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_outputs"),
            path="/api/runs/{runid}/{config}/outputs",
            required_fields=[
                "run_state_domain",
                "run_state_vector",
                "updated_at",
                "data_state",
                "data_updated_at",
                "etag",
                "artifacts",
                "exports",
            ],
        ),
        request=_empty_request_schema(),
        defaults_context={
            **_defaults_context(runtime),
            "outputs_mode": "artifact_index",
        },
    )
