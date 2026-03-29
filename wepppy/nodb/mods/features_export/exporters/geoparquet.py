"""GeoParquet writer implementation for features export."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from .base import (
    ExportArtifactMetadata,
    ExportPayloadValidationError,
    ExportWriter,
    ExportWriterRequest,
    ExportedLayerArtifact,
    deterministic_layer_filename,
    merge_warnings,
    payload_warnings,
    resolve_layer_payload_pairs,
)
from .packaging import package_files_as_zip


def _coerce_epsg(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if value.is_integer() and value > 0:
            return int(value)
        return None
    if isinstance(value, str):
        token = value.strip()
        if token.isdigit():
            parsed = int(token)
            return parsed if parsed > 0 else None
    return None


def _feature_collection_from_payload(payload_bytes: bytes) -> tuple[dict[str, object], int | None]:
    try:
        payload_text = payload_bytes.decode("utf-8")
        parsed_payload = json.loads(payload_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportPayloadValidationError(
            "GeoParquet payload must be JSON feature-collection content."
        ) from exc

    if not isinstance(parsed_payload, dict):
        raise ExportPayloadValidationError("GeoParquet payload must decode to a JSON object.")

    if parsed_payload.get("type") == "FeatureCollection":
        feature_collection = parsed_payload
    else:
        nested = parsed_payload.get("feature_collection")
        feature_collection = nested if isinstance(nested, dict) else None

    if not isinstance(feature_collection, dict) or feature_collection.get("type") != "FeatureCollection":
        raise ExportPayloadValidationError(
            "GeoParquet payload must include a GeoJSON FeatureCollection."
        )

    return feature_collection, _coerce_epsg(parsed_payload.get("crs_epsg"))


def _geodataframe_from_payload(*, output_layer_id: str, payload_bytes: bytes) -> gpd.GeoDataFrame:
    feature_collection, crs_epsg = _feature_collection_from_payload(payload_bytes)
    raw_features = feature_collection.get("features")
    if not isinstance(raw_features, list):
        raise ExportPayloadValidationError(
            f"GeoParquet payload for {output_layer_id!r} is missing a features array."
        )

    records: list[dict[str, object]] = []
    for index, feature in enumerate(raw_features):
        if not isinstance(feature, dict):
            raise ExportPayloadValidationError(
                f"GeoParquet payload for {output_layer_id!r} includes a non-object feature at index {index}."
            )

        properties = feature.get("properties")
        if properties is None:
            record: dict[str, object] = {}
        elif isinstance(properties, dict):
            record = {str(key): value for key, value in properties.items()}
        else:
            raise ExportPayloadValidationError(
                f"GeoParquet payload for {output_layer_id!r} has non-object properties at index {index}."
            )

        geometry_payload = feature.get("geometry")
        geometry_value = None
        if geometry_payload is not None:
            if not isinstance(geometry_payload, dict):
                raise ExportPayloadValidationError(
                    f"GeoParquet payload for {output_layer_id!r} has invalid geometry at index {index}."
                )
            try:
                geometry_value = shape(geometry_payload)
            except Exception as exc:
                raise ExportPayloadValidationError(
                    f"GeoParquet payload for {output_layer_id!r} has unparseable geometry at index {index}."
                ) from exc

        record["geometry"] = geometry_value
        records.append(record)

    if records:
        frame = gpd.GeoDataFrame(records, geometry="geometry")
    else:
        frame = gpd.GeoDataFrame(pd.DataFrame({"geometry": pd.Series(dtype="object")}), geometry="geometry")

    if crs_epsg is not None:
        frame = frame.set_crs(epsg=crs_epsg, allow_override=True)

    return frame


class GeoparquetExportWriter(ExportWriter):
    """Write one GeoParquet file per resolved layer and package into one zip."""

    format_token = "geoparquet"
    layer_extension = ".geoparquet"

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        per_layer_files: dict[str, Path] = {}
        layer_outputs: list[ExportedLayerArtifact] = []

        for layer, payload in layer_pairs:
            layer_filename = deterministic_layer_filename(layer.output_layer_id, self.layer_extension)
            layer_path = artifact_dir / layer_filename
            frame = _geodataframe_from_payload(
                output_layer_id=layer.output_layer_id,
                payload_bytes=payload.payload_bytes(),
            )
            try:
                frame.to_parquet(layer_path, index=False)
            except Exception as exc:  # boundary: exporter failure should be explicit
                raise ExportPayloadValidationError(
                    f"Failed to write geoparquet payload file {layer_filename!r}: {exc}"
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


__all__ = ["GeoparquetExportWriter"]
