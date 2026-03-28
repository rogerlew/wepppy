"""Geometryless CSV writer for features export."""

from __future__ import annotations

from pathlib import Path

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
from .tabular_common import build_tabular_frames


class CsvExportWriter(ExportWriter):
    """Write one geometryless csv file per layer and package into one zip."""

    format_token = "csv"

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        concatenate_tables = bool(
            request.plan.request.tabular is not None
            and request.plan.request.tabular.concatenate_tables
        )
        frame_by_filename, filename_by_output_layer_id = build_tabular_frames(
            layer_payload_pairs=layer_pairs,
            file_extension="csv",
            concatenate_tables=concatenate_tables,
        )
        per_layer_files: dict[str, Path] = {}
        layer_outputs: list[ExportedLayerArtifact] = []

        for layer_filename, frame in frame_by_filename.items():
            layer_path = artifact_dir / layer_filename
            try:
                frame.to_csv(layer_path, index=False)
            except Exception as exc:  # boundary: exporter failure should be explicit
                raise ExportPayloadValidationError(
                    f"Failed to write csv payload file {layer_filename!r}: {exc}"
                ) from exc

            per_layer_files[layer_filename] = layer_path

        for layer, payload in layer_pairs:
            layer_filename = filename_by_output_layer_id[layer.output_layer_id]
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
