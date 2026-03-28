"""Geometryless CSV writer for features export."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .base import (
    ExportArtifactMetadata,
    ExportPayloadValidationError,
    ExportWriter,
    ExportWriterRequest,
    ExportedLayerArtifact,
    merge_warnings,
    payload_warnings,
    resolve_layer_payload_pairs,
)
from .packaging import package_files_as_zip


def _table_rows_from_payload(layer, payload) -> list[dict[str, object]]:
    try:
        parsed = json.loads(payload.payload_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None

    if isinstance(parsed, dict):
        feature_collection = parsed.get("feature_collection")
        if isinstance(feature_collection, dict) and feature_collection.get("type") == "FeatureCollection":
            rows: list[dict[str, object]] = []
            for feature in feature_collection.get("features", []):
                if not isinstance(feature, dict):
                    continue
                properties = feature.get("properties")
                if isinstance(properties, dict):
                    rows.append(dict(properties))
            if rows:
                return rows

    return [
        {
            "layer_id": layer.layer_id,
            "output_layer_id": layer.output_layer_id,
            "scope": layer.scope,
            "scope_class": layer.scope_class,
            "payload_sha256": payload.payload_sha256(),
        }
    ]


class CsvExportWriter(ExportWriter):
    """Write one geometryless csv file per layer and package into one zip."""

    format_token = "csv"

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        per_layer_files: dict[str, Path] = {}
        layer_outputs: list[ExportedLayerArtifact] = []

        for layer, payload in layer_pairs:
            rows = _table_rows_from_payload(layer, payload)
            frame = pd.DataFrame(rows)
            layer_filename = f"{layer.output_layer_id}.csv"
            layer_path = artifact_dir / layer_filename
            try:
                frame.to_csv(layer_path, index=False)
            except Exception as exc:  # boundary: exporter failure should be explicit
                raise ExportPayloadValidationError(
                    f"Failed to write csv payload for layer {layer.output_layer_id!r}: {exc}"
                ) from exc

            per_layer_files[layer_filename] = layer_path
            layer_outputs.append(
                ExportedLayerArtifact(
                    layer_id=layer.layer_id,
                    output_layer_id=layer.output_layer_id,
                    scope=layer.scope,
                    scope_class=layer.scope_class,
                    format=self.format_token,
                    relpath=layer_filename,
                    row_count=payload.row_count,
                    feature_count=payload.feature_count,
                )
            )

        bundle_filename = f"{request.artifact_basename}.{self.format_token}.zip"
        bundle_path = artifact_dir / bundle_filename
        packaged_member_relpaths = package_files_as_zip(bundle_path, per_layer_files)

        warnings = merge_warnings(
            request.plan.warnings,
            payload_warnings(layer_pairs),
        )

        return ExportArtifactMetadata(
            format=self.format_token,
            artifact_relpath=bundle_filename,
            artifact_path=str(bundle_path),
            layer_outputs=tuple(layer_outputs),
            warnings=warnings,
            packaged_member_relpaths=packaged_member_relpaths,
        )


__all__ = ["CsvExportWriter"]
