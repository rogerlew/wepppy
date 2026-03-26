"""Manifest assembly and serialization for features export artifacts."""

from __future__ import annotations

import collections.abc as cabc
import json
from pathlib import Path

from .contracts import ExportWarning, ResolvedExportPlan
from .dependency_tracker import DependencySnapshot
from .exporters.base import ExportArtifactMetadata

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_GENERATOR_VERSION = "features-export-wp3"


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
) -> dict[str, object]:
    """Build pure, deterministic artifact manifest payload for WP-3."""

    if not isinstance(artifact_id, str) or not artifact_id:
        raise ValueError("artifact_id must be a non-empty string.")
    if not isinstance(generation_timestamp_utc, str) or not generation_timestamp_utc:
        raise ValueError("generation_timestamp_utc must be a non-empty string.")

    dependency_mapping = _normalize_dependency_snapshot(dependency_snapshot)
    layer_outputs_by_id = {entry.output_layer_id: entry for entry in artifact.layer_outputs}

    layer_scope_metadata: list[dict[str, object]] = []
    for layer in sorted(plan.layers, key=lambda item: item.output_layer_id):
        output = layer_outputs_by_id.get(layer.output_layer_id)
        layer_scope_metadata.append(
            {
                "layer_id": layer.layer_id,
                "output_layer_id": layer.output_layer_id,
                "family": layer.family,
                "scope_class": layer.scope_class,
                "scope": layer.scope,
                "temporal_mode": layer.temporal_mode,
                "artifact_relpath": output.relpath if output is not None else artifact.artifact_relpath,
                "row_count": output.row_count if output is not None else None,
                "feature_count": output.feature_count if output is not None else None,
            }
        )

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
        "conversion_summary": dict(conversion_summary or {}),
        "dependency_preparation": [dict(item) for item in (dependency_preparation or ())],
        "warnings": warnings_payload,
    }


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
