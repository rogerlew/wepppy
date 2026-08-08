#!/usr/bin/env python3
"""Generate and validate Phase 1 peak-flow audit protocol schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
SCHEMA_BASE = "https://github.com/rogerlew/wepppy/peakflow-phase1/schemas/"


def _schema(name: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{SCHEMA_BASE}{name}.schema.json",
        "title": name.replace("-", " ").title(),
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", *required],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            **properties,
        },
    }


NONEMPTY = {"type": "string", "minLength": 1}
SHA256 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
NUMBER = {"type": "number"}
NONNEGATIVE = {"type": "number", "minimum": 0}

FORCING_POINT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["point_ordinal", "time_s", "rate_m_s"],
    "properties": {
        "point_ordinal": {"type": "integer", "minimum": 1},
        "time_s": NONNEGATIVE,
        "rate_m_s": NONNEGATIVE,
    },
}

FORCING_INTERVAL = {
    "type": "object",
    "additionalProperties": False,
    "required": ["interval_ordinal", "start_s", "end_s", "rate_m_s"],
    "properties": {
        "interval_ordinal": {"type": "integer", "minimum": 1},
        "start_s": NONNEGATIVE,
        "end_s": NONNEGATIVE,
        "rate_m_s": NONNEGATIVE,
    },
}

APP_DIAGNOSTIC = {
    "type": "object",
    "additionalProperties": False,
    "required": ["vave_m_s", "vstar", "tstar", "tc", "qpstar", "equation_branch", "within_documented_vstar_domain", "within_documented_tstar_domain", "within_documented_qpstar_domain", "finite_result"],
    "properties": {
        "vave_m_s": NONNEGATIVE,
        "vstar": NUMBER,
        "tstar": NUMBER,
        "tc": {"type": ["number", "null"]},
        "qpstar": NUMBER,
        "equation_branch": {"enum": ["partial_equilibrium", "quasi_equilibrium_a", "quasi_equilibrium_b", "constant_or_out_of_domain"]},
        "within_documented_vstar_domain": {"type": "boolean"},
        "within_documented_tstar_domain": {"type": "boolean"},
        "within_documented_qpstar_domain": {"type": "boolean"},
        "finite_result": {"type": "boolean"},
    },
}

REPLAY_PROPERTIES = {
    "appmth_peak_m_s": NONNEGATIVE,
    "hdrive_peak_m_s": NONNEGATIVE,
    "hdrive_nqt": {"type": "integer", "minimum": 0},
    "hdrive_nq": {"type": "integer", "minimum": 0},
    "hdrive_final_routed_volume_fraction": NONNEGATIVE,
    "appmth": APP_DIAGNOSTIC,
}

LEGACY_REPLAY = {
    "type": "object",
    "additionalProperties": False,
    "required": list(REPLAY_PROPERTIES),
    "properties": REPLAY_PROPERTIES,
}

HARMONIZED_REPLAY = {
    "type": "object",
    "additionalProperties": False,
    "required": [*REPLAY_PROPERTIES, "forcing_integral_m", "positive_support_duration_s"],
    "properties": {
        **REPLAY_PROPERTIES,
        "forcing_integral_m": NONNEGATIVE,
        "positive_support_duration_s": NONNEGATIVE,
    },
}


SCHEMAS: dict[str, dict[str, Any]] = {
    "event-packet": _schema(
        "event-packet",
        ["event_id", "source_build_id", "payload_sha256", "scalars", "post_surplus_forcing", "production"],
        {
            "event_id": NONEMPTY,
            "source_build_id": NONEMPTY,
            "payload_sha256": SHA256,
            "scalars": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "calendar_year", "model_day", "run_id", "hillslope_id", "ofe",
                    "solver_call_ordinal", "runoff_pre_reconciliation_m",
                    "runoff_post_reconciliation_m", "surdra_raw_m", "surplus_depth_m",
                    "positive_excess_duration_s", "surplus_assignment_duration_s",
                    "surplus_assignment_mode", "remax_pre_surplus_m_s",
                    "forcing_max_post_surplus_m_s", "surplus_added_rate_m_s", "tp2_s",
                    "alpha", "m", "effective_length_m", "ns",
                ],
                "properties": {
                    "calendar_year": {"type": "integer"},
                    "model_day": {"type": "integer", "minimum": 1},
                    "run_id": NONEMPTY,
                    "hillslope_id": NONEMPTY,
                    "ofe": {"type": "integer", "minimum": 1},
                    "solver_call_ordinal": {"type": "integer", "minimum": 1},
                    "runoff_pre_reconciliation_m": NONNEGATIVE,
                    "runoff_post_reconciliation_m": NONNEGATIVE,
                    "surdra_raw_m": NONNEGATIVE,
                    "surplus_depth_m": NONNEGATIVE,
                    "positive_excess_duration_s": NONNEGATIVE,
                    "surplus_assignment_duration_s": NONNEGATIVE,
                    "surplus_assignment_mode": {"enum": ["none", "positive_excess", "storm", "upstream", "fallback_24h"]},
                    "remax_pre_surplus_m_s": NONNEGATIVE,
                    "forcing_max_post_surplus_m_s": NONNEGATIVE,
                    "surplus_added_rate_m_s": NONNEGATIVE,
                    "tp2_s": NUMBER,
                    "alpha": NUMBER,
                    "m": NUMBER,
                    "effective_length_m": NONNEGATIVE,
                    "ns": {"type": "integer", "minimum": 1},
                },
            },
            "pre_surplus_forcing": {"type": "array", "items": FORCING_INTERVAL},
            "post_surplus_forcing": {"type": "array", "minItems": 2, "items": FORCING_POINT},
            "production": {
                "type": "object",
                "required": ["selected_solver", "peak_m_s"],
                "properties": {
                    "selected_solver": {"enum": ["APPMTH", "HDRIVE"]},
                    "peak_m_s": NONNEGATIVE,
                },
                "additionalProperties": False,
            },
        },
    ),
    "replay-report": _schema(
        "replay-report",
        ["event_id", "packet_sha256", "replay_process", "selected_method_delta_m_s", "legacy_input_replay", "harmonized_forcing_diagnostic", "hdrive_stopping_condition"],
        {
            "event_id": NONEMPTY,
            "packet_sha256": SHA256,
            "replay_process": {"const": "standalone_peak_replay_executable"},
            "selected_method_delta_m_s": NONNEGATIVE,
            "legacy_input_replay": LEGACY_REPLAY,
            "harmonized_forcing_diagnostic": HARMONIZED_REPLAY,
            "hdrive_stopping_condition": {"enum": ["95_percent_volume", "ns_plus_200_limit", "array_limit", "iteration_limit"]},
        },
    ),
    "build-manifest": _schema(
        "build-manifest",
        ["build_id", "source_commit", "compiler", "compiler_version", "source_clean", "executable_sha256"],
        {
            "build_id": NONEMPTY,
            "source_repository": NONEMPTY,
            "source_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "source_clean": {"type": "boolean"},
            "compiler": NONEMPTY,
            "compiler_version": NONEMPTY,
            "optimization_flags": {"type": "array", "items": {"type": "string"}},
            "floating_point_flags": {"type": "array", "items": {"type": "string"}},
            "preprocessor_definitions": {"type": "array", "items": {"type": "string"}},
            "linker_libraries": {"type": "array", "items": {"type": "string"}},
            "os": NONEMPTY,
            "architecture": NONEMPTY,
            "instrumentation_patch_sha256": {"anyOf": [SHA256, {"type": "null"}]},
            "input_tree_sha256": SHA256,
            "executable_sha256": SHA256,
            "reproducibility_level": {"enum": ["internal", "public"]},
        },
    ),
    "run-manifest": _schema(
        "run-manifest",
        ["run_id", "build_id", "site_id", "scenario_id", "input_tree_sha256"],
        {
            "run_id": NONEMPTY,
            "build_id": NONEMPTY,
            "site_id": NONEMPTY,
            "scenario_id": NONEMPTY,
            "mutation_id": {"type": ["string", "null"]},
            "input_tree_sha256": SHA256,
            "command": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "canonical_output_policy": NONEMPTY,
            "terminal_status": {"enum": ["created", "running", "complete", "failed"]},
        },
    ),
    "mutation-manifest": _schema(
        "mutation-manifest",
        ["mutation_id", "target", "parameter", "requested_value", "realized_value", "units"],
        {
            "mutation_id": NONEMPTY,
            "target": NONEMPTY,
            "parameter": NONEMPTY,
            "requested_value": NUMBER,
            "realized_value": NUMBER,
            "units": NONEMPTY,
            "baseline_value": NUMBER,
            "clipped": {"type": "boolean"},
            "input_diff_sha256": SHA256,
            "expected_hydrologically_active": {"type": "boolean"},
        },
    ),
    "event-scalar": _schema(
        "event-scalar",
        ["event_id", "run_id", "hillslope_id", "ofe", "model_day", "solver_call_ordinal", "event_present"],
        {
            "event_id": NONEMPTY,
            "run_id": NONEMPTY,
            "hillslope_id": NONEMPTY,
            "ofe": {"type": "integer", "minimum": 1},
            "model_day": {"type": "integer", "minimum": 1},
            "calendar_date": {"type": "string", "format": "date"},
            "solver_call_ordinal": {"type": "integer", "minimum": 1},
            "event_present": {"type": "boolean"},
            "positive_excess_duration_s": NONNEGATIVE,
            "surplus_assignment_duration_s": NONNEGATIVE,
            "surplus_assignment_mode": {"enum": ["positive_excess", "storm", "upstream", "fallback_24h", "none"]},
            "surplus_depth_mm": NONNEGATIVE,
            "surplus_added_rate_mm_h": NONNEGATIVE,
            "remax_pre_surplus_mm_h": NONNEGATIVE,
            "forcing_max_post_surplus_mm_h": NONNEGATIVE,
            "runoff_pre_reconciliation_mm": NONNEGATIVE,
            "runoff_post_reconciliation_mm": NONNEGATIVE,
            "tp2_s": NUMBER,
            "selected_solver": {"enum": ["APPMTH", "HDRIVE", "none"]},
            "production_peak_mm_h": NONNEGATIVE,
            "packet_sha256": SHA256,
        },
    ),
    "layer-state": _schema(
        "layer-state",
        ["event_id", "layer", "water_mm", "saturation_fraction"],
        {
            "event_id": NONEMPTY,
            "layer": {"type": "integer", "minimum": 1},
            "water_mm": NONNEGATIVE,
            "saturation_fraction": {"type": "number", "minimum": 0},
            "frozen_water_mm": NONNEGATIVE,
        },
    ),
    "event-forcing": _schema(
        "event-forcing",
        ["event_id", "stage", "interval_ordinal", "start_s", "end_s", "rate_mm_h"],
        {
            "event_id": NONEMPTY,
            "stage": {"enum": ["pre_surplus", "post_surplus", "hourly_surface_return"]},
            "interval_ordinal": {"type": "integer", "minimum": 1},
            "start_s": NONNEGATIVE,
            "end_s": NONNEGATIVE,
            "rate_mm_h": NONNEGATIVE,
        },
    ),
    "routing-response": _schema(
        "routing-response",
        ["mutation_event_id", "reach_id", "downstream_ordinal", "event_present"],
        {
            "mutation_event_id": NONEMPTY,
            "reach_id": NONEMPTY,
            "downstream_ordinal": {"type": "integer", "minimum": 0},
            "event_present": {"type": "boolean"},
            "runoff_volume_m3": NONNEGATIVE,
            "peak_flow_m3_s": NONNEGATIVE,
            "peak_time_s": NONNEGATIVE,
            "on_declared_downstream_path": {"type": "boolean"},
        },
    ),
    "hydrograph": _schema(
        "hydrograph",
        ["routing_response_id", "timestamp_s", "flow_m3_s"],
        {
            "routing_response_id": NONEMPTY,
            "timestamp_s": NONNEGATIVE,
            "flow_m3_s": NONNEGATIVE,
        },
    ),
    "site-selection": _schema(
        "site-selection",
        ["site_id", "portfolio", "selection_status", "selection_examined_peak_anomalies"],
        {
            "site_id": NONEMPTY,
            "portfolio": {"enum": ["enriched_discovery", "blind_audit"]},
            "selection_status": {"enum": ["candidate", "admitted", "excluded"]},
            "selection_examined_peak_anomalies": {"type": "boolean"},
            "hydrologic_regime": NONEMPTY,
            "provenance_criteria": {"type": "array", "items": NONEMPTY},
            "exclusion_reason": {"type": ["string", "null"]},
        },
    ),
    "artifact-storage": _schema(
        "artifact-storage",
        ["artifact_id", "locator", "format", "byte_size", "sha256", "retention_status"],
        {
            "artifact_id": NONEMPTY,
            "locator": NONEMPTY,
            "format": NONEMPTY,
            "byte_size": {"type": "integer", "minimum": 0},
            "sha256": SHA256,
            "producer_run_id": NONEMPTY,
            "dataset_schema_version": NONEMPTY,
            "retention_status": {"enum": ["committed", "authoritative_external", "derived_rebuildable", "expired"]},
        },
    ),
}


def write_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, schema in SCHEMAS.items():
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


def validate_directory(schema_dir: Path) -> None:
    import jsonschema

    expected = {f"{name}.schema.json" for name in SCHEMAS}
    actual = {path.name for path in schema_dir.glob("*.schema.json")}
    if actual != expected:
        raise SystemExit(f"schema set mismatch: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    for name, expected_schema in SCHEMAS.items():
        actual_schema = json.loads((schema_dir / f"{name}.schema.json").read_text())
        if actual_schema != expected_schema:
            raise SystemExit(f"generated schema drift: {name}")
        jsonschema.Draft7Validator.check_schema(actual_schema)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("write", "validate"))
    parser.add_argument("schema_dir", type=Path)
    args = parser.parse_args()
    if args.command == "write":
        write_schemas(args.schema_dir)
    else:
        validate_directory(args.schema_dir)


if __name__ == "__main__":
    main()
