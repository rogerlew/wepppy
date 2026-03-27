"""GeoPackage writer implementation for features export."""

from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path

from osgeo import ogr

from .base import ExportBackendCapabilityError, FeaturesExportWriterError, MultiLayerContainerWriter


def _normalize_table_name(token: str, used_names: set[str]) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in token.lower()).strip("_")
    if not normalized:
        normalized = "layer"
    if normalized[0].isdigit():
        normalized = f"layer_{normalized}"

    candidate = normalized
    suffix = 2
    while candidate in used_names:
        candidate = f"{normalized}_{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


class GeopackageExportWriter(MultiLayerContainerWriter):
    """Write one multi-layer GeoPackage container artifact."""

    format_token = "geopackage"
    container_extension = ".gpkg"

    def build_container_bytes(self, request, layer_payload_pairs) -> bytes:
        used_table_names: set[str] = set()
        fd, tmp_name = tempfile.mkstemp(suffix=".gpkg")
        tmp_path = Path(tmp_name)

        try:
            tmp_path.unlink(missing_ok=True)

            driver = ogr.GetDriverByName("GPKG")
            if driver is None:
                raise ExportBackendCapabilityError(
                    "geopackage export requires GDAL GPKG driver support, but it is unavailable."
                )

            dataset = driver.CreateDataSource(str(tmp_path))
            if dataset is None:
                raise FeaturesExportWriterError(f"Failed to create GeoPackage at {tmp_path}.")

            try:
                for layer, payload in layer_payload_pairs:
                    table_name = _normalize_table_name(layer.output_layer_id, used_table_names)
                    layer_options = [
                        "ASPATIAL_VARIANT=GPKG_ATTRIBUTES",
                        f"IDENTIFIER={layer.output_layer_id}",
                        f"DESCRIPTION={layer.layer_id}",
                    ]
                    ogr_layer = dataset.CreateLayer(
                        table_name,
                        geom_type=ogr.wkbNone,
                        options=layer_options,
                    )
                    if ogr_layer is None:
                        raise FeaturesExportWriterError(
                            f"Failed to create GeoPackage layer {table_name!r}."
                        )

                    _create_layer_fields(ogr_layer)
                    feature = ogr.Feature(ogr_layer.GetLayerDefn())
                    try:
                        feature.SetField("layer_id", layer.layer_id)
                        feature.SetField("output_layer_id", layer.output_layer_id)
                        feature.SetField("scope", layer.scope)
                        feature.SetField("scope_class", layer.scope_class)
                        if payload.row_count is not None:
                            feature.SetField("row_count", int(payload.row_count))
                        if payload.feature_count is not None:
                            feature.SetField("feature_count", int(payload.feature_count))
                        feature.SetField("payload_sha256", payload.payload_sha256())
                        feature.SetField(
                            "payload_base64",
                            base64.b64encode(payload.payload_bytes()).decode("ascii"),
                        )
                        create_result = ogr_layer.CreateFeature(feature)
                        if create_result != 0:
                            raise FeaturesExportWriterError(
                                f"Failed to write GeoPackage feature for layer {table_name!r}."
                            )
                    finally:
                        feature = None
            finally:
                dataset = None

            return tmp_path.read_bytes()
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _create_layer_fields(ogr_layer) -> None:
    field_defs = (
        ("layer_id", ogr.OFTString),
        ("output_layer_id", ogr.OFTString),
        ("scope", ogr.OFTString),
        ("scope_class", ogr.OFTString),
        ("row_count", ogr.OFTInteger64),
        ("feature_count", ogr.OFTInteger64),
        ("payload_sha256", ogr.OFTString),
        ("payload_base64", ogr.OFTString),
    )

    for field_name, field_type in field_defs:
        field_defn = ogr.FieldDefn(field_name, field_type)
        create_status = ogr_layer.CreateField(field_defn)
        if create_status != 0:
            raise FeaturesExportWriterError(
                f"Failed to create GeoPackage field {field_name!r}."
            )


__all__ = ["GeopackageExportWriter"]
