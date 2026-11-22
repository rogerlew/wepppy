"""Operation discovery documents for land use."""

from __future__ import annotations

from typing import Any

from .openapi import rq_operation_id
from .schema_defaults_controllers import _controller_defaults
from .schema_defaults_descriptors import (
    _base_run_mutation_descriptor,
    _base_run_read_descriptor,
    _empty_request_schema,
    _operation_document,
)
from .schema_defaults_fields import _landuse_dataset_field, _landuse_method_field
from .schema_defaults_runtime import RuntimeState


def get_landuse_state(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_landuse_state"),
            path="/api/runs/{runid}/{config}/controllers/landuse/state",
            required_fields=[
                "controller",
                "state",
                "run_state_domain",
                "run_state_vector",
                "run_state_revision",
            ],
        ),
        request=_empty_request_schema(),
        resolved_defaults={
            "controller": "landuse",
            "state": _controller_defaults("landuse", runtime),
        },
    )


def build_landuse(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("build_landuse"),
            path="/api/runs/{runid}/{config}/build-landuse",
            execution_mode="async",
            content_types=["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
            returns_job=True,
            job_key="build_landuse_rq",
            required_fields=["job_id"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=120,
            mutates_controllers=["landuse"],
            invalidates_steps=["prep-wepp-watershed", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="batch_returns_message_no_queue",
        ),
        request={
            "type": "object",
            "properties": {
                "input_upload_single_landuse": {
                    "type": "string", "format": "binary", "constraint_mode": "static",
                    "description": "Single User-Defined mode 5 only, with project opt-in. Version 98.4; one OFE; .man/.MAN; maximum 5 MiB. Omit to reuse the accepted source.",
                },
                "landuse_db": {
                    **_landuse_dataset_field(runtime),
                },
                "landuse_mode": {
                    **_landuse_method_field(runtime, runtime_values=True),
                },
                "mofe_buffer_selection": {
                    "type": "integer",
                    "constraint_mode": "static",
                },
                "checkbox_burn_shrubs": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "checkbox_burn_grass": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "burn_shrubs": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "burn_grass": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "landuse_management_mapping_selection": {
                    "type": "string",
                    "constraint_mode": "run_resolved",
                    "constraint_source": "controller_state",
                    "resolved_at": runtime.generated_at,
                },
                "input_upload_landuse": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
        resolved_defaults=_controller_defaults("landuse", runtime),
    )


def set_landuse_mode(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("set_landuse_mode"),
            path="/api/runs/{runid}/{config}/set-landuse-mode",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=2,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "mode": {
                    **_landuse_method_field(
                        runtime, runtime_values=True
                    ),
                },
                "landuse_single_selection": {
                    "type": "string",
                    "constraint_mode": "static",
                },
            },
            "required": ["mode"],
            "additional_properties": True,
        },
    )


def set_landuse_db(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("set_landuse_db"),
            path="/api/runs/{runid}/{config}/set-landuse-db",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=2,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "landuse_db": {
                    **_landuse_dataset_field(runtime),
                },
            },
            "required": ["landuse_db"],
            "additional_properties": True,
        },
    )


def modify_landuse_coverage(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("modify_landuse_coverage"),
            path="/api/runs/{runid}/{config}/modify-landuse-coverage",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=3,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "dom": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "cover": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "value": {
                    "type": "number",
                    "constraint_mode": "static",
                },
            },
            "required": ["dom", "cover", "value"],
            "additional_properties": True,
        },
    )


def modify_landuse_mapping(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("modify_landuse_mapping"),
            path="/api/runs/{runid}/{config}/modify-landuse-mapping",
            execution_mode="async",
            returns_job=True,
            job_key="modify_landuse_mapping_rq",
            required_fields=["job_id", "mapping_count"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=45,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="queue_job",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "mappings": {
                    "type": "array",
                    "constraint_mode": "static",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dom": {"type": "string"},
                            "newdom": {"type": "string"},
                        },
                        "required": ["dom", "newdom"],
                        "additional_properties": False,
                    },
                },
                "dom": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "newdom": {
                    "type": "string",
                    "constraint_mode": "static",
                },
            },
            "additional_properties": True,
        },
    )


def get_landuse_user_defined_catalog(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_landuse_user_defined_catalog"),
            path="/api/runs/{runid}/{config}/landuse-user-defined/catalog",
            required_fields=["items", "lookup_sha256"],
        ),
        request=_empty_request_schema(),
    )


def upload_landuse_user_defined_managements(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("upload_landuse_user_defined_managements"),
            path="/api/runs/{runid}/{config}/landuse-user-defined/upload",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message", "imported_files", "catalog_count", "items", "replace"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=5,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "replace": {
                    "type": "boolean",
                    "constraint_mode": "static",
                },
                "management_upload": {
                    "type": "string",
                    "format": "binary",
                    "constraint_mode": "static",
                },
            },
            "required": ["management_upload"],
            "additional_properties": True,
        },
        resolved_defaults={"replace": False},
    )


def delete_landuse_user_defined_management(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("delete_landuse_user_defined_management"),
            path="/api/runs/{runid}/{config}/landuse-user-defined/delete",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message", "deleted", "catalog_count", "items"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=2,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "constraint_mode": "static",
                },
            },
            "required": ["filename"],
            "additional_properties": True,
        },
    )


def update_landuse_user_defined_management_description(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("update_landuse_user_defined_management_description"),
            path="/api/runs/{runid}/{config}/landuse-user-defined/update-description",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message", "item", "catalog_count", "items"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=2,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "description": {
                    "type": "string",
                    "constraint_mode": "static",
                },
            },
            "required": ["filename", "description"],
            "additional_properties": True,
        },
    )


def get_landuse_map_snapshot(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_read_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("get_landuse_map_snapshot"),
            path="/api/runs/{runid}/{config}/landuse-map/snapshot",
            required_fields=["rows", "management_options", "lookup_sha256"],
        ),
        request=_empty_request_schema(),
    )


def save_landuse_map(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("save_landuse_map"),
            path="/api/runs/{runid}/{config}/landuse-map/save",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message", "lookup_sha256"],
            estimated_duration_bucket="medium",
            estimated_duration_seconds=8,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "if_match_sha256": {
                    "type": "string",
                    "constraint_mode": "static",
                },
                "rows": {
                    "type": "array",
                    "constraint_mode": "static",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "management_file": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["key", "management_file"],
                        "additional_properties": True,
                    },
                },
            },
            "required": ["rows"],
            "additional_properties": True,
        },
    )


def clear_landuse_map_override(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("clear_landuse_map_override"),
            path="/api/runs/{runid}/{config}/landuse-map/clear-override",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=3,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request=_empty_request_schema(),
    )


def modify_landuse(runtime: RuntimeState) -> dict[str, Any]:
    return _operation_document(
        runtime,
        _base_run_mutation_descriptor(
            runtime=runtime,
            operation_id=rq_operation_id("modify_landuse"),
            path="/api/runs/{runid}/{config}/modify-landuse",
            execution_mode="sync",
            returns_job=False,
            job_key=None,
            required_fields=["message", "topaz_count"],
            estimated_duration_bucket="fast",
            estimated_duration_seconds=3,
            mutates_controllers=["landuse"],
            invalidates_steps=["build-landuse", "run-wepp", "run-wepp-watershed"],
            batch_mode_behavior="sync_update_no_queue",
            auth_requirements={
                "bearer_jwt": {
                    "required_scope": ["rq:enqueue"],
                    "token_classes": ["user", "session", "service", "mcp"],
                }
            },
        ),
        request={
            "type": "object",
            "properties": {
                "topaz_ids": {
                    "type": ["array", "string"],
                    "constraint_mode": "static",
                },
                "landuse": {
                    "type": ["integer", "string"],
                    "constraint_mode": "static",
                },
            },
            "required": ["topaz_ids", "landuse"],
            "additional_properties": True,
        },
    )
