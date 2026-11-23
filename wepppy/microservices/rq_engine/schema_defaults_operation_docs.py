"""Build per-operation error catalogs and serializable discovery snapshots."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .openapi import rq_operation_id


def _operation_required_fields(operation_docs: Mapping[str, Any]) -> list[str]:
    schema = operation_docs.get("schema")
    if not isinstance(schema, Mapping):
        return []
    request = schema.get("request")
    if not isinstance(request, Mapping):
        return []
    required = request.get("required")
    if not isinstance(required, list):
        return []
    fields: list[str] = []
    for raw in required:
        value = str(raw or "").strip()
        if not value or value in fields:
            continue
        fields.append(value)
    return fields


def _domain_operation_errors(operation_id: str, required_fields: list[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if operation_id == rq_operation_id("fetch_dem_and_build_channels"):
        retry = [{"operation_id": operation_id, "required_fields": required_fields}]
        errors.extend([
            {"error_code": "channel_extent_outside_boundary", "recoverable": True,
             "http_statuses": [400], "recovery_actions": retry},
            {"error_code": "invalid_channel_extent", "recoverable": True,
             "http_statuses": [400], "recovery_actions": retry},
            {"error_code": "invalid_channel_boundary_config", "recoverable": False,
             "http_statuses": [500], "recovery_actions": []},
        ])

    if operation_id == rq_operation_id("build_climate"):
        errors.extend(
            [
                {
                    "error_code": "missing_station_selection",
                    "recoverable": True,
                    "http_statuses": [400, 409],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": ["climatestation"]}],
                },
                {
                    "error_code": "climate_mode_unavailable_for_region",
                    "recoverable": True,
                    "http_statuses": [400],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": ["climate_mode"]}],
                },
            ]
        )

    domain_capability_operations = {
        rq_operation_id("build_climate"),
        rq_operation_id("build_landuse"),
        rq_operation_id("set_landuse_mode"),
        rq_operation_id("set_landuse_db"),
        rq_operation_id("build_soils"),
    }
    if operation_id in domain_capability_operations:
        errors.extend([
            {
                "error_code": "unsupported_capability",
                "recoverable": True,
                "http_statuses": [400],
                "recovery_actions": [{
                    "operation_id": operation_id,
                    "required_fields": required_fields,
                }],
            },
            {
                "error_code": "capability_authority_invalid",
                "recoverable": False,
                "http_statuses": [409],
                "recovery_actions": [],
            },
            {
                "error_code": "locale_authority_invalid",
                "recoverable": False,
                "http_statuses": [409],
                "recovery_actions": [],
            },
            {
                "error_code": "builder_registry_error",
                "recoverable": True,
                "http_statuses": [503],
                "recovery_actions": [{
                    "operation_id": operation_id,
                    "required_fields": required_fields,
                }],
            },
        ])

    if operation_id in {
        rq_operation_id("run_wepp"),
        rq_operation_id("run_wepp_watershed"),
    }:
        errors.append(
            {
                "error_code": "invalid_watershed_abstraction_state",
                "recoverable": True,
                "http_statuses": [409],
                "recovery_actions": [
                    {
                        "operation_id": rq_operation_id(
                            "build_subcatchments_and_abstract_watershed"
                        ),
                        "required_fields": [],
                    }
                ],
                "recovery_notes": [
                    "This recovery action enqueues subcatchment rebuild work only "
                    "outside batch/_base contexts. Batch/_base callers must "
                    "materialize watershed.subwta through their normal setup flow "
                    "before retrying run-wepp endpoints."
                ],
            }
        )

    return errors


def _build_operation_error_catalog(
    *,
    operation_id: str,
    operation_docs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    descriptor = operation_docs.get("descriptor")
    descriptor_map = descriptor if isinstance(descriptor, Mapping) else {}
    method = str(descriptor_map.get("method") or "").strip().upper()
    execution_mode = str(descriptor_map.get("execution_mode") or "").strip().lower()
    write_precondition = descriptor_map.get("write_precondition")
    write_precondition_map = write_precondition if isinstance(write_precondition, Mapping) else {}
    idempotency_policy = descriptor_map.get("idempotency_policy")
    idempotency_policy_map = idempotency_policy if isinstance(idempotency_policy, Mapping) else {}
    required_fields = _operation_required_fields(operation_docs)

    list_run_endpoints_id = rq_operation_id("list_run_endpoints")
    errors: list[dict[str, Any]] = [
        {"error_code": "unauthorized", "recoverable": True, "http_statuses": [401], "recovery_actions": []},
        {"error_code": "forbidden", "recoverable": True, "http_statuses": [403], "recovery_actions": []},
        {
            "error_code": "not_found",
            "recoverable": True,
            "http_statuses": [404],
            "recovery_actions": [{"operation_id": list_run_endpoints_id, "required_fields": []}],
        },
    ]

    if method == "POST":
        errors.append(
            {
                "error_code": "validation_error",
                "recoverable": True,
                "http_statuses": [400],
                "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
            }
        )

        accepted_preconditions = write_precondition_map.get("accepted")
        has_accepted_preconditions = isinstance(accepted_preconditions, list) and len(accepted_preconditions) > 0
        if bool(write_precondition_map.get("required")) or has_accepted_preconditions:
            errors.append(
                {
                    "error_code": "stale_run_state",
                    "recoverable": True,
                    "http_statuses": [409],
                    "recovery_actions": [
                        {
                            "operation_id": operation_id,
                            "required_fields": ["expected_run_state_revision"],
                        }
                    ],
                }
            )

        if bool(idempotency_policy_map.get("supported")):
            mismatch_status_code = int(idempotency_policy_map.get("mismatch_status_code") or 409)
            mismatch_error_code = str(idempotency_policy_map.get("mismatch_error_code") or "idempotency_key_conflict")
            errors.append(
                {
                    "error_code": mismatch_error_code,
                    "recoverable": True,
                    "http_statuses": [mismatch_status_code],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
                }
            )

            replay_behavior = str(idempotency_policy_map.get("replay_behavior") or "").strip().lower()
            if replay_behavior == "reject_duplicate":
                duplicate_status_code = int(idempotency_policy_map.get("duplicate_replay_status_code") or 409)
                duplicate_error_code = str(
                    idempotency_policy_map.get("duplicate_replay_error_code") or "idempotency_replay_rejected"
                )
                errors.append(
                    {
                        "error_code": duplicate_error_code,
                        "recoverable": True,
                        "http_statuses": [duplicate_status_code],
                        "recovery_actions": [{"operation_id": operation_id, "required_fields": required_fields}],
                    }
                )

        if execution_mode == "async":
            errors.append(
                {
                    "error_code": "enqueue_failed",
                    "recoverable": True,
                    "http_statuses": [500],
                    "recovery_actions": [{"operation_id": operation_id, "required_fields": []}],
                }
            )

    errors.extend(_domain_operation_errors(operation_id, required_fields))
    return errors


def _build_operation_docs_snapshot(
    *,
    operations: Mapping[str, Mapping[str, Any]],
    computed_at: str,
) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for operation_id, operation_docs in operations.items():
        descriptor = copy.deepcopy(operation_docs["descriptor"])
        schema = copy.deepcopy(operation_docs["schema"])
        defaults_doc = copy.deepcopy(operation_docs["defaults"])
        snapshot[operation_id] = {
            "operation_descriptor": descriptor,
            "schema_version": schema["schema_version"],
            "request": schema["request"],
            "responses": schema["responses"],
            "resolved_defaults": defaults_doc["resolved_defaults"],
            "defaults_context": defaults_doc["defaults_context"],
            "computed_at": computed_at,
            "errors": _build_operation_error_catalog(
                operation_id=operation_id,
                operation_docs=operation_docs,
            ),
        }
        if "capability_authority" in schema:
            snapshot[operation_id]["capability_authority"] = schema["capability_authority"]
    return snapshot
