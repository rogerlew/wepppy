"""Manifest assembly and serialization for features export artifacts."""

from __future__ import annotations

import collections.abc as cabc
import json
from pathlib import Path

from .contracts import ExportWarning, ResolvedExportPlan
from .dependency_tracker import DependencySnapshot
from .exporters.base import ExportArtifactMetadata

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_GENERATOR_VERSION = "features-export-wp14-publication-registry"


def build_export_manifest(
    *,
    plan: ResolvedExportPlan,
    artifact: ExportArtifactMetadata,
    dependency_snapshot: DependencySnapshot | cabc.Mapping[str, object],
    artifact_id: str,
    cache_hit: bool,
    source_job_id: str | None,
    generation_timestamp_utc: str,
    requested_crs: str | None = None,
    resolved_crs: str | None = None,
    resolved_epsg: int | None = None,
    swat_table_resolution: cabc.Mapping[str, object] | None = None,
    temporal_decisions: cabc.Mapping[str, object] | None = None,
    conversion_summary: cabc.Mapping[str, object] | None = None,
    dependency_preparation: cabc.Sequence[cabc.Mapping[str, object]] | None = None,
    additional_warnings: cabc.Sequence[ExportWarning | cabc.Mapping[str, object]] = (),
    column_metadata_by_output_layer_id: cabc.Mapping[str, cabc.Mapping[str, object]] | None = None,
    request_column_selection_by_layer_id: cabc.Mapping[str, cabc.Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Build pure, deterministic artifact manifest payload for WP-3."""

    if not isinstance(artifact_id, str) or not artifact_id:
        raise ValueError("artifact_id must be a non-empty string.")
    if not isinstance(generation_timestamp_utc, str) or not generation_timestamp_utc:
        raise ValueError("generation_timestamp_utc must be a non-empty string.")

    dependency_mapping = _normalize_dependency_snapshot(dependency_snapshot)
    plan_layers_by_output = {entry.output_layer_id: entry for entry in plan.layers}
    output_column_metadata = _normalize_column_metadata(column_metadata_by_output_layer_id)

    layer_scope_metadata: list[dict[str, object]] = []
    for output in sorted(artifact.layer_outputs, key=lambda item: item.output_layer_id):
        plan_layer = plan_layers_by_output.get(output.output_layer_id)
        entry = {
            "layer_id": output.layer_id,
            "output_layer_id": output.output_layer_id,
            "family": plan_layer.family if plan_layer is not None else None,
            "scope_class": output.scope_class,
            "scope": output.scope,
            "context": plan_layer.context if plan_layer is not None else None,
            "selector_id": plan_layer.selector_id if plan_layer is not None else None,
            "carrier_layer": plan_layer.carrier_layer if plan_layer is not None else None,
            "temporal_mode": plan_layer.temporal_mode if plan_layer is not None else None,
            "artifact_relpath": output.relpath,
            "row_count": output.row_count,
            "feature_count": output.feature_count,
        }
        column_meta = output_column_metadata.get(output.output_layer_id, {})
        if column_meta:
            entry["source_layer_ids"] = list(column_meta.get("source_layer_ids", []))
            entry["selected_columns"] = list(column_meta.get("selected_columns", []))
            entry["unit_mapping"] = dict(column_meta.get("unit_mapping", {}))
        layer_scope_metadata.append(entry)

    warnings_payload = _normalize_warnings(
        [
            *plan.warnings,
            *artifact.warnings,
            *additional_warnings,
        ]
    )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generator_version": MANIFEST_GENERATOR_VERSION,
        "generated_at_utc": generation_timestamp_utc,
        "artifact_id": artifact_id,
        "cache_hit": bool(cache_hit),
        "source_job_id": source_job_id,
        "artifact": {
            "format": artifact.format,
            "artifact_relpath": artifact.artifact_relpath,
            "artifact_path": artifact.artifact_path,
            "packaged_member_relpaths": list(artifact.packaged_member_relpaths),
        },
        "catalog": {
            "catalog_version": plan.catalog_version,
            "schema_version": plan.schema_version,
        },
        "request": {
            "resolved": plan.request.to_mapping(),
            "layers_requested": list(plan.request.layers),
            "output_scopes_requested": list(plan.request.output_scopes),
            "column_selection_by_layer_id": _normalize_generic_mapping(
                request_column_selection_by_layer_id
            ),
        },
        "crs": {
            "requested_crs": requested_crs or plan.request.crs,
            "resolved_crs": resolved_crs or plan.request.crs,
            "resolved_epsg": resolved_epsg,
        },
        "dependency_snapshot": dependency_mapping,
        "layers": layer_scope_metadata,
        "swat_table_resolution": dict(swat_table_resolution or {}),
        "temporal": dict(temporal_decisions or {}),
        "columns": {
            "output_layer_metadata": output_column_metadata,
        },
        "conversion_summary": dict(conversion_summary or {}),
        "dependency_preparation": [dict(item) for item in (dependency_preparation or ())],
        "warnings": warnings_payload,
    }


def _normalize_column_metadata(
    value: cabc.Mapping[str, cabc.Mapping[str, object]] | None,
) -> dict[str, dict[str, object]]:
    if not isinstance(value, cabc.Mapping):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for output_layer_id, entry in value.items():
        if not isinstance(output_layer_id, str) or not output_layer_id.strip():
            continue
        if not isinstance(entry, cabc.Mapping):
            continue
        normalized[output_layer_id.strip()] = _normalize_generic_mapping(entry)
    return normalized


def _normalize_generic_mapping(value: cabc.Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        return {}
    payload = json.loads(json.dumps(dict(value), sort_keys=True, separators=(",", ":")))
    if not isinstance(payload, dict):
        return {}
    return payload


def serialize_export_manifest(manifest: cabc.Mapping[str, object]) -> str:
    """Serialize manifest mapping with deterministic JSON key order."""

    if not isinstance(manifest, cabc.Mapping):
        raise TypeError("manifest must be a mapping.")

    return json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n"


def write_export_manifest(path: str | Path, manifest: cabc.Mapping[str, object]) -> Path:
    """Write manifest JSON payload to disk and return resolved path."""

    resolved_path = Path(path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(serialize_export_manifest(manifest), encoding="utf-8")
    return resolved_path


def _normalize_dependency_snapshot(
    dependency_snapshot: DependencySnapshot | cabc.Mapping[str, object],
) -> dict[str, object]:
    if isinstance(dependency_snapshot, DependencySnapshot):
        return dependency_snapshot.to_mapping()
    if isinstance(dependency_snapshot, cabc.Mapping):
        serialized = json.dumps(dict(dependency_snapshot), sort_keys=True, separators=(",", ":"))
        normalized = json.loads(serialized)
        if not isinstance(normalized, dict):
            raise TypeError("dependency_snapshot mapping must normalize to a dict payload.")
        return normalized
    raise TypeError(
        "dependency_snapshot must be DependencySnapshot or mapping, "
        f"received {type(dependency_snapshot).__name__}."
    )


def _normalize_warnings(
    warnings: cabc.Sequence[ExportWarning | cabc.Mapping[str, object]],
) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[tuple[object, object, object, object]] = set()

    for warning in warnings:
        mapping = _warning_to_mapping(warning)
        dedupe_key = (
            mapping.get("code"),
            mapping.get("message"),
            mapping.get("layer_id"),
            mapping.get("scope"),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(mapping)

    return deduped


def _warning_to_mapping(
    warning: ExportWarning | cabc.Mapping[str, object],
) -> dict[str, object]:
    if isinstance(warning, ExportWarning):
        return warning.to_mapping()
    if isinstance(warning, cabc.Mapping):
        normalized = json.loads(json.dumps(dict(warning), sort_keys=True, separators=(",", ":")))
        if not isinstance(normalized, dict):
            raise TypeError("warning mapping must normalize to dict payload.")
        return normalized
    raise TypeError(
        "warnings must contain ExportWarning or mapping entries, "
        f"received {type(warning).__name__}."
    )


__all__ = [
    "MANIFEST_GENERATOR_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "build_export_manifest",
    "serialize_export_manifest",
    "write_export_manifest",
]
