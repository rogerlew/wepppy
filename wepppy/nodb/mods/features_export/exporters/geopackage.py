"""GeoPackage writer implementation for features export."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path

from osgeo import ogr, osr

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


def _normalize_field_name(token: str, used_names: set[str]) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in token.lower()).strip("_")
    if not normalized:
        normalized = "field"
    if normalized[0].isdigit():
        normalized = f"f_{normalized}"

    candidate = normalized
    suffix = 2
    while candidate in used_names:
        candidate = f"{normalized}_{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def _field_kind_for_value(value: object) -> str:
    if isinstance(value, bool):
        return "int"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "real"
    return "str"


def _merge_field_kind(current: str | None, incoming: str) -> str:
    if current is None:
        return incoming
    if current == incoming:
        return current
    if "str" in {current, incoming}:
        return "str"
    if "real" in {current, incoming}:
        return "real"
    return "int"


def _ogr_field_type_for_kind(kind: str) -> int:
    if kind == "int":
        return ogr.OFTInteger64
    if kind == "real":
        return ogr.OFTReal
    return ogr.OFTString


def _normalize_field_value(value: object, *, kind: str) -> object | None:
    if value is None:
        return None

    if kind == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        try:
            return int(str(value).strip())
        except ValueError:
            return None

    if kind == "real":
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except ValueError:
            return None

    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _parse_feature_collection_payload(payload) -> tuple[dict[str, object] | None, int | None]:
    try:
        payload_text = payload.payload_bytes().decode("utf-8")
        parsed_payload = json.loads(payload_text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, None

    if not isinstance(parsed_payload, dict):
        return None, None

    feature_collection = None
    if parsed_payload.get("type") == "FeatureCollection":
        feature_collection = parsed_payload
    else:
        nested = parsed_payload.get("feature_collection")
        if isinstance(nested, dict) and nested.get("type") == "FeatureCollection":
            feature_collection = nested

    if not isinstance(feature_collection, dict):
        return None, None

    crs_epsg = parsed_payload.get("crs_epsg")
    if isinstance(crs_epsg, bool):
        crs_epsg = None
    elif isinstance(crs_epsg, float):
        crs_epsg = int(crs_epsg)
    elif isinstance(crs_epsg, str):
        crs_token = crs_epsg.strip()
        if crs_token.isdigit():
            crs_epsg = int(crs_token)
        else:
            crs_epsg = None
    elif not isinstance(crs_epsg, int):
        crs_epsg = None

    return feature_collection, crs_epsg


def _create_spatial_reference(crs_epsg: int | None):
    if not isinstance(crs_epsg, int) or crs_epsg <= 0:
        return None
    srs = osr.SpatialReference()
    import_result = srs.ImportFromEPSG(crs_epsg)
    if import_result != 0:
        return None
    return srs


def _write_feature_collection_layer(ogr_layer, feature_collection: dict[str, object]) -> None:
    raw_features = feature_collection.get("features")
    if not isinstance(raw_features, list):
        return

    features: list[dict[str, object]] = [
        feature for feature in raw_features if isinstance(feature, dict)
    ]

    property_kinds: dict[str, str | None] = {}
    for feature in features:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            continue
        for key, value in properties.items():
            key_name = str(key)
            if key_name not in property_kinds:
                property_kinds[key_name] = None
            if value is None:
                continue
            property_kinds[key_name] = _merge_field_kind(
                property_kinds.get(key_name),
                _field_kind_for_value(value),
            )

    field_name_map: dict[str, str] = {}
    field_kind_map: dict[str, str] = {}
    used_field_names: set[str] = set()
    for property_name in sorted(property_kinds):
        field_name = _normalize_field_name(property_name, used_field_names)
        field_kind = property_kinds[property_name] or "str"
        field_defn = ogr.FieldDefn(field_name, _ogr_field_type_for_kind(field_kind))
        create_status = ogr_layer.CreateField(field_defn)
        if create_status != 0:
            raise FeaturesExportWriterError(
                f"Failed to create GeoPackage field {field_name!r}."
            )
        field_name_map[property_name] = field_name
        field_kind_map[property_name] = field_kind

    for feature in features:
        ogr_feature = ogr.Feature(ogr_layer.GetLayerDefn())
        try:
            geometry_payload = feature.get("geometry")
            if isinstance(geometry_payload, dict):
                geometry_json = json.dumps(
                    geometry_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                geometry = ogr.CreateGeometryFromJson(geometry_json)
                if geometry is not None:
                    ogr_feature.SetGeometry(geometry)

            properties = feature.get("properties")
            if isinstance(properties, dict):
                for property_name, property_value in properties.items():
                    if property_name not in field_name_map:
                        continue
                    normalized_value = _normalize_field_value(
                        property_value,
                        kind=field_kind_map[property_name],
                    )
                    if normalized_value is None:
                        continue
                    ogr_feature.SetField(field_name_map[property_name], normalized_value)

            create_result = ogr_layer.CreateFeature(ogr_feature)
            if create_result != 0:
                raise FeaturesExportWriterError(
                    f"Failed to write GeoPackage feature for layer {ogr_layer.GetName()!r}."
                )
        finally:
            ogr_feature = None


def _create_payload_metadata_fields(ogr_layer) -> None:
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


def _write_payload_metadata_feature(ogr_layer, layer, payload) -> None:
    ogr_feature = ogr.Feature(ogr_layer.GetLayerDefn())
    try:
        ogr_feature.SetField("layer_id", layer.layer_id)
        ogr_feature.SetField("output_layer_id", layer.output_layer_id)
        ogr_feature.SetField("scope", layer.scope)
        ogr_feature.SetField("scope_class", layer.scope_class)
        if payload.row_count is not None:
            ogr_feature.SetField("row_count", int(payload.row_count))
        if payload.feature_count is not None:
            ogr_feature.SetField("feature_count", int(payload.feature_count))
        ogr_feature.SetField("payload_sha256", payload.payload_sha256())
        ogr_feature.SetField("payload_base64", base64.b64encode(payload.payload_bytes()).decode("ascii"))
        create_result = ogr_layer.CreateFeature(ogr_feature)
        if create_result != 0:
            raise FeaturesExportWriterError(
                f"Failed to write GeoPackage feature for layer {ogr_layer.GetName()!r}."
            )
    finally:
        ogr_feature = None


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
                    feature_collection, crs_epsg = _parse_feature_collection_payload(payload)
                    if feature_collection is not None:
                        spatial_ref = _create_spatial_reference(crs_epsg)
                        layer_options = [
                            f"IDENTIFIER={layer.output_layer_id}",
                            f"DESCRIPTION={layer.layer_id}",
                        ]
                        ogr_layer = dataset.CreateLayer(
                            table_name,
                            srs=spatial_ref,
                            geom_type=ogr.wkbUnknown,
                            options=layer_options,
                        )
                    else:
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

                    if feature_collection is not None:
                        _write_feature_collection_layer(ogr_layer, feature_collection)
                    else:
                        _create_payload_metadata_fields(ogr_layer)
                        _write_payload_metadata_feature(ogr_layer, layer, payload)
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


__all__ = ["GeopackageExportWriter"]
