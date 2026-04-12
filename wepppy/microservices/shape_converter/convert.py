"""Convert endpoint implementation for CRS-aware shapefile serialization."""

from __future__ import annotations

import collections.abc as cabc
import os
from dataclasses import dataclass
from pathlib import Path

import fiona
import fiona.errors as fiona_errors
from pyproj import CRS
from shapely.errors import GEOSException
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from starlette.datastructures import UploadFile

from .archive_validation import (
    ArchiveLimits,
    read_upload_bytes_with_limit,
    shp_xml_sidecar_warning_message,
    validate_and_extract_zip_archive,
)
from .cleanup import RequestScratchLayout
from .crs import (
    TARGET_CRS_OPTIONS,
    ResolvedTargetCrs,
    crs_identifier,
    crs_to_response_payload,
    parse_source_crs,
    reproject_geometries,
    resolve_target_crs,
)
from .errors import ShapeConverterError
from .inspect import select_single_shapefile_dataset
from .serialization import serialize_geojson, serialize_geoparquet

OUTPUT_FORMAT_OPTIONS = frozenset({"geojson", "geoparquet"})
_MAX_UPLOAD_COMPRESSED_BYTES = ArchiveLimits().max_compressed_bytes
_MAX_CONVERT_FEATURES = int(os.getenv("SHAPE_CONVERTER_MAX_CONVERT_FEATURES", "1000000"))


@dataclass(frozen=True, slots=True)
class LoadedShapefile:
    """In-memory representation of extracted shapefile features."""

    properties: tuple[dict[str, object], ...]
    geometries: tuple[BaseGeometry | None, ...]
    source_bounds: tuple[float, float, float, float]
    source_crs: CRS | None


@dataclass(frozen=True, slots=True)
class ConvertedArtifact:
    """Serialized conversion artifact and sidecar metadata."""

    request_id: str
    filename: str
    content_type: str
    content: bytes
    metadata: dict[str, object]


async def convert_uploaded_archive(
    *,
    archive: UploadFile,
    scratch: RequestScratchLayout,
    request_id: str,
    output_format: str,
    target_crs: str,
) -> ConvertedArtifact:
    """Convert one uploaded archive to requested format/CRS."""

    if output_format not in OUTPUT_FORMAT_OPTIONS:
        raise ShapeConverterError(
            code="invalid_request",
            message="Unsupported output_format value.",
            details=(
                f"output_format={output_format!r} is invalid; "
                f"expected one of {sorted(OUTPUT_FORMAT_OPTIONS)}."
            ),
        )

    if target_crs not in TARGET_CRS_OPTIONS:
        raise ShapeConverterError(
            code="invalid_request",
            message="Unsupported target_crs value.",
            details=(
                f"target_crs={target_crs!r} is invalid; "
                f"expected one of {sorted(TARGET_CRS_OPTIONS)}."
            ),
        )

    archive_name = archive.filename or "upload.zip"
    archive_bytes = await read_upload_bytes_with_limit(
        upload=archive,
        max_bytes=_MAX_UPLOAD_COMPRESSED_BYTES,
    )

    if not archive_bytes:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive payload is empty.",
            details="Uploaded archive contained zero bytes.",
        )

    try:
        scratch.upload_archive_path.write_bytes(archive_bytes)
    except OSError as exc:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Unable to persist uploaded archive.",
            details=str(exc),
            status_code=500,
        ) from exc

    extracted_archive = validate_and_extract_zip_archive(
        archive_name=archive_name,
        archive_bytes=archive_bytes,
        extraction_root=scratch.extraction_root,
    )
    sidecar_warning = shp_xml_sidecar_warning_message(
        removed_sidecars=extracted_archive.removed_shp_xml_sidecars
    )
    dataset = select_single_shapefile_dataset(extracted_archive)

    loaded = _load_shapefile(dataset.prefix_path.with_suffix(".shp"))
    crs_plan = resolve_target_crs(
        target_crs_token=target_crs,
        source_crs=loaded.source_crs,
        source_bounds=loaded.source_bounds,
    )
    conversion_warnings = list(crs_plan.warnings)
    if sidecar_warning:
        conversion_warnings.append(sidecar_warning)

    transformed_geometries = reproject_geometries(
        geometries=loaded.geometries,
        source_crs=crs_plan.source_crs,
        target_crs=crs_plan.target_crs,
    )

    if output_format == "geojson":
        serialized = serialize_geojson(
            properties=loaded.properties,
            geometries=transformed_geometries,
            target_crs=crs_plan.target_crs,
            rfc7946_compliant=crs_plan.rfc7946_compliant_geojson,
            warnings=tuple(conversion_warnings),
        )
    else:
        serialized = serialize_geoparquet(
            properties=loaded.properties,
            geometries=transformed_geometries,
            target_crs=crs_plan.target_crs,
            warnings=tuple(conversion_warnings),
        )

    metadata = _build_convert_metadata(
        request_id=request_id,
        output_format=output_format,
        target_crs=target_crs,
        crs_plan=crs_plan,
        transformed_geometries=transformed_geometries,
        feature_count=len(loaded.properties),
        warnings=serialized.warnings,
    )

    prefix_name = dataset.prefix_path.name
    filename = f"{prefix_name}_{target_crs}.{serialized.extension}"
    output_path = scratch.output_root / filename
    try:
        scratch.output_root.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(serialized.content)
    except OSError as exc:
        raise ShapeConverterError(
            code="reprojection_failed",
            message="Unable to persist converted output artifact.",
            details=str(exc),
            status_code=500,
        ) from exc

    return ConvertedArtifact(
        request_id=request_id,
        filename=filename,
        content_type=serialized.content_type,
        content=serialized.content,
        metadata=metadata,
    )


def _load_shapefile(shp_path: Path) -> LoadedShapefile:
    properties: list[dict[str, object]] = []
    geometries: list[BaseGeometry | None] = []

    try:
        with fiona.open(shp_path.as_posix()) as dataset:
            raw_bounds = dataset.bounds
            source_bounds = (
                float(raw_bounds[0]),
                float(raw_bounds[1]),
                float(raw_bounds[2]),
                float(raw_bounds[3]),
            )
            source_crs = parse_source_crs(
                crs_wkt=getattr(dataset, "crs_wkt", None),
                crs_mapping=getattr(dataset, "crs", None),
            )

            for index, feature in enumerate(dataset):
                if not isinstance(feature, cabc.Mapping):
                    raise ShapeConverterError(
                        code="invalid_shapefile",
                        message="Shapefile feature payload is invalid.",
                        details=f"Feature at index {index} is not an object.",
                    )

                raw_properties = feature.get("properties")
                if raw_properties is None:
                    normalized_properties: dict[str, object] = {}
                elif isinstance(raw_properties, cabc.Mapping):
                    normalized_properties = {str(key): value for key, value in raw_properties.items()}
                else:
                    normalized_properties = {
                        str(key): value
                        for key, value in dict(raw_properties).items()
                    }

                geometry_payload = feature.get("geometry")
                if geometry_payload is None:
                    geometry = None
                elif isinstance(geometry_payload, cabc.Mapping):
                    geometry = shape(dict(geometry_payload))
                else:
                    raise ShapeConverterError(
                        code="invalid_shapefile",
                        message="Shapefile geometry payload is invalid.",
                        details=f"Feature at index {index} has non-object geometry.",
                    )

                properties.append(normalized_properties)
                geometries.append(geometry)

                if len(properties) > _MAX_CONVERT_FEATURES:
                    raise ShapeConverterError(
                        code="archive_quota_exceeded",
                        message="Feature count exceeds configured conversion limit.",
                        details=(
                            f"Feature count exceeded limit {_MAX_CONVERT_FEATURES} while reading shapefile."
                        ),
                        status_code=413,
                    )
    except ShapeConverterError:
        raise
    except (
        fiona_errors.FionaError,
        GEOSException,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=str(exc),
        ) from exc

    return LoadedShapefile(
        properties=tuple(properties),
        geometries=tuple(geometries),
        source_bounds=source_bounds,
        source_crs=source_crs,
    )


def _build_convert_metadata(
    *,
    request_id: str,
    output_format: str,
    target_crs: str,
    crs_plan: ResolvedTargetCrs,
    transformed_geometries: tuple[BaseGeometry | None, ...],
    feature_count: int,
    warnings: tuple[str, ...],
) -> dict[str, object]:
    geometry_types = sorted({geometry.geom_type for geometry in transformed_geometries if geometry is not None})
    bbox = _geometry_bounds(transformed_geometries)

    return {
        "request_id": request_id,
        "output_format": output_format,
        "target_crs": target_crs,
        "detected_crs": crs_to_response_payload(crs_plan.source_crs),
        "output_crs": crs_to_response_payload(crs_plan.target_crs),
        "output_crs_identifier": crs_identifier(crs_plan.target_crs),
        "feature_count": feature_count,
        "geometry_types": geometry_types,
        "bbox": list(bbox) if bbox is not None else None,
        "warnings": list(warnings),
        "rfc7946_compliant_geojson": crs_plan.rfc7946_compliant_geojson,
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
    "OUTPUT_FORMAT_OPTIONS",
    "ConvertedArtifact",
    "convert_uploaded_archive",
]
