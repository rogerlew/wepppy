"""Output serialization helpers for shape-converter convert requests."""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass

from pyproj import CRS
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from .crs import crs_identifier
from .errors import ShapeConverterError

_MAX_GEOJSON_OUTPUT_BYTES = int(os.getenv("SHAPE_CONVERTER_MAX_GEOJSON_OUTPUT_BYTES", str(100 * 1024 * 1024)))
_MAX_GEOPARQUET_OUTPUT_BYTES = int(
    os.getenv("SHAPE_CONVERTER_MAX_GEOPARQUET_OUTPUT_BYTES", str(100 * 1024 * 1024))
)


@dataclass(frozen=True, slots=True)
class SerializedArtifact:
    """Serialized conversion artifact payload plus metadata."""

    content: bytes
    content_type: str
    extension: str
    warnings: tuple[str, ...]


def serialize_geojson(
    *,
    properties: tuple[dict[str, object], ...],
    geometries: tuple[BaseGeometry | None, ...],
    target_crs: CRS | None,
    rfc7946_compliant: bool,
    warnings: tuple[str, ...] = (),
) -> SerializedArtifact:
    """Serialize transformed features as GeoJSON bytes."""

    feature_collection: dict[str, object] = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": dict(feature_properties),
                "geometry": mapping(feature_geometry) if feature_geometry is not None else None,
            }
            for feature_properties, feature_geometry in zip(properties, geometries, strict=True)
        ],
    }

    output_warnings = list(warnings)
    if not rfc7946_compliant:
        crs_name = crs_identifier(target_crs)
        if crs_name:
            feature_collection["crs"] = {
                "type": "name",
                "properties": {"name": crs_name},
            }
            output_warnings.append(
                "GeoJSON output is not RFC 7946 compliant because coordinates are in a projected CRS."
            )
        else:
            output_warnings.append(
                "GeoJSON output CRS is unknown; RFC 7946 compliance cannot be guaranteed."
            )

    try:
        payload_bytes = json.dumps(
            feature_collection,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Failed to serialize GeoJSON output.",
            details=str(exc),
            status_code=500,
        ) from exc

    if len(payload_bytes) > _MAX_GEOJSON_OUTPUT_BYTES:
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Serialized GeoJSON exceeds configured output size limit.",
            details=(
                f"GeoJSON output is {len(payload_bytes)} bytes, exceeding limit "
                f"{_MAX_GEOJSON_OUTPUT_BYTES} bytes."
            ),
            status_code=413,
        )

    return SerializedArtifact(
        content=payload_bytes,
        content_type=("application/geo+json" if rfc7946_compliant else "application/json"),
        extension="geojson",
        warnings=tuple(output_warnings),
    )


def serialize_geoparquet(
    *,
    properties: tuple[dict[str, object], ...],
    geometries: tuple[BaseGeometry | None, ...],
    target_crs: CRS | None,
    warnings: tuple[str, ...] = (),
) -> SerializedArtifact:
    """Serialize transformed features as GeoParquet bytes with required geo metadata."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime image includes pyarrow
        raise ShapeConverterError(
            code="invalid_request",
            message="GeoParquet output is not available in this runtime.",
            details=str(exc),
            status_code=500,
        ) from exc

    try:
        property_columns = _normalize_property_columns(properties)
        property_arrays = {name: pa.array(values) for name, values in property_columns.items()}
        geometry_wkb = [geometry.wkb if geometry is not None else None for geometry in geometries]
        geometry_array = pa.array(geometry_wkb, type=pa.binary())

        table_columns = dict(property_arrays)
        table_columns["geometry"] = geometry_array
        table = pa.table(table_columns)

        geo_metadata = _build_geo_metadata(geometries=geometries, target_crs=target_crs)
        existing_metadata = dict(table.schema.metadata or {})
        existing_metadata[b"geo"] = json.dumps(
            geo_metadata,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        table = table.replace_schema_metadata(existing_metadata)

        output_warnings = list(warnings)
        if target_crs is None:
            output_warnings.append(
                "GeoParquet CRS metadata was omitted because source CRS is unknown."
            )

        output_buffer = io.BytesIO()
        pq.write_table(table, output_buffer)
    except (OSError, ValueError, TypeError, pa.ArrowException) as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Failed to serialize GeoParquet output.",
            details=str(exc),
            status_code=500,
        ) from exc

    payload_bytes = output_buffer.getvalue()
    if len(payload_bytes) > _MAX_GEOPARQUET_OUTPUT_BYTES:
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Serialized GeoParquet exceeds configured output size limit.",
            details=(
                f"GeoParquet output is {len(payload_bytes)} bytes, exceeding limit "
                f"{_MAX_GEOPARQUET_OUTPUT_BYTES} bytes."
            ),
            status_code=413,
        )

    return SerializedArtifact(
        content=payload_bytes,
        content_type="application/vnd.apache.parquet",
        extension="geoparquet",
        warnings=tuple(output_warnings),
    )


def _normalize_property_columns(properties: tuple[dict[str, object], ...]) -> dict[str, list[object]]:
    column_names = sorted({str(column) for row in properties for column in row.keys()})
    normalized: dict[str, list[object]] = {name: [] for name in column_names}

    for row in properties:
        for name in column_names:
            normalized[name].append(row.get(name))

    return normalized


def _build_geo_metadata(*, geometries: tuple[BaseGeometry | None, ...], target_crs: CRS | None) -> dict[str, object]:
    geometry_types = sorted({geometry.geom_type for geometry in geometries if geometry is not None})
    bbox = _geometry_bounds(geometries)

    geometry_column: dict[str, object] = {
        "encoding": "WKB",
        "geometry_types": geometry_types,
    }
    if bbox is not None:
        geometry_column["bbox"] = list(bbox)

    if target_crs is not None:
        geometry_column["crs"] = target_crs.to_json_dict()

    return {
        "version": "1.1.0",
        "primary_column": "geometry",
        "columns": {
            "geometry": geometry_column,
        },
    }


def _geometry_bounds(geometries: tuple[BaseGeometry | None, ...]) -> tuple[float, float, float, float] | None:
    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None

    for geometry in geometries:
        if geometry is None or geometry.is_empty:
            continue

        geom_min_x, geom_min_y, geom_max_x, geom_max_y = geometry.bounds
        min_x = geom_min_x if min_x is None else min(min_x, geom_min_x)
        min_y = geom_min_y if min_y is None else min(min_y, geom_min_y)
        max_x = geom_max_x if max_x is None else max(max_x, geom_max_x)
        max_y = geom_max_y if max_y is None else max(max_y, geom_max_y)

    if min_x is None or min_y is None or max_x is None or max_y is None:
        return None

    return float(min_x), float(min_y), float(max_x), float(max_y)


__all__ = [
    "SerializedArtifact",
    "serialize_geojson",
    "serialize_geoparquet",
]
