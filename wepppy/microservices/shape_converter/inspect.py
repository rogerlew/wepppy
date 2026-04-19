"""Inspect endpoint implementation for ZIP/shapefile metadata extraction."""

from __future__ import annotations

import errno
import os
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

from pyproj import CRS
from pyproj.exceptions import CRSError
from starlette.datastructures import UploadFile

from .archive_validation import (
    REQUIRED_SHAPEFILE_EXTENSIONS,
    ArchiveLimits,
    ExtractedArchive,
    read_upload_bytes_with_limit,
    shp_xml_sidecar_warning_message,
    validate_and_extract_zip_archive,
)
from .cleanup import RequestScratchLayout
from .errors import ShapeConverterError

_SHAPE_TYPE_NAMES = {
    0: "Null",
    1: "Point",
    3: "LineString",
    5: "Polygon",
    8: "MultiPoint",
    11: "PointZ",
    13: "LineStringZ",
    15: "PolygonZ",
    18: "MultiPointZ",
    21: "PointM",
    23: "LineStringM",
    25: "PolygonM",
    28: "MultiPointM",
    31: "MultiPatch",
}

_DBF_TYPE_NAMES = {
    "C": "character",
    "N": "numeric",
    "F": "float",
    "D": "date",
    "L": "logical",
    "M": "memo",
}

_MAX_PRJ_BYTES = 32 * 1024
_MAX_UPLOAD_COMPRESSED_BYTES = ArchiveLimits().max_compressed_bytes
_NULLABILITY_NOTE_FALLBACK = "Not inferable from DBF header metadata."
_SCRATCH_PRECHECK_FREE_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_SCRATCH_PRECHECK_FREE_BYTES", str(128 * 1024 * 1024))),
)
_REQUEST_SCRATCH_QUOTA_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_REQUEST_SCRATCH_QUOTA_BYTES", str(700 * 1024 * 1024))),
)


@dataclass(frozen=True, slots=True)
class ShapefileDataset:
    prefix_path: Path


async def inspect_uploaded_archive(
    *,
    archive: UploadFile,
    scratch: RequestScratchLayout,
    request_id: str,
) -> dict[str, object]:
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

    _assert_scratch_free_space(
        scratch=scratch,
        required_free_bytes=len(archive_bytes) + _SCRATCH_PRECHECK_FREE_BYTES,
        stage="inspect_archive_preflight",
    )
    _assert_request_scratch_quota(
        scratch=scratch,
        additional_bytes=len(archive_bytes),
        stage="inspect_archive_write",
    )

    try:
        scratch.upload_archive_path.write_bytes(archive_bytes)
    except OSError as exc:
        raise _map_capacity_os_error(
            exc=exc,
            stage="inspect_archive_write",
            fallback_code="invalid_archive",
            fallback_message="Unable to persist uploaded archive.",
            fallback_status_code=500,
        ) from exc

    extraction_request_quota = _REQUEST_SCRATCH_QUOTA_BYTES - len(archive_bytes)
    if extraction_request_quota <= 0:
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Request scratch quota exceeded.",
            details="Request scratch quota does not allow archive extraction after upload persistence.",
            status_code=413,
        )

    extracted_archive = validate_and_extract_zip_archive(
        archive_name=archive_name,
        archive_bytes=archive_bytes,
        extraction_root=scratch.extraction_root,
        request_quota_bytes=extraction_request_quota,
    )

    dataset = select_single_shapefile_dataset(extracted_archive)
    sidecar_warning = shp_xml_sidecar_warning_message(
        removed_sidecars=extracted_archive.removed_shp_xml_sidecars
    )
    additional_warnings: tuple[str, ...] = (sidecar_warning,) if sidecar_warning else ()
    return _build_inspect_payload(
        dataset=dataset,
        request_id=request_id,
        additional_warnings=additional_warnings,
    )


def _assert_scratch_free_space(
    *,
    scratch: RequestScratchLayout,
    required_free_bytes: int,
    stage: str,
) -> None:
    try:
        free_bytes = shutil.disk_usage(scratch.request_dir).free
    except OSError as exc:
        raise ShapeConverterError(
            code="service_saturated",
            message="Unable to verify scratch free space.",
            details=f"Scratch free-space probe failed during {stage}: {exc}",
            status_code=503,
        ) from exc

    if free_bytes < required_free_bytes:
        raise ShapeConverterError(
            code="service_saturated",
            message="Insufficient scratch free space for inspect request.",
            details=f"Scratch free-space preflight failed during {stage}.",
            status_code=503,
        )


def _assert_request_scratch_quota(
    *,
    scratch: RequestScratchLayout,
    additional_bytes: int,
    stage: str,
) -> None:
    try:
        current_usage = _scratch_tree_size_bytes(scratch.request_dir)
    except OSError as exc:
        raise ShapeConverterError(
            code="service_saturated",
            message="Unable to evaluate request scratch usage.",
            details=f"Scratch quota evaluation failed during {stage}: {exc}",
            status_code=503,
        ) from exc

    projected_usage = current_usage + max(0, additional_bytes)
    if projected_usage > _REQUEST_SCRATCH_QUOTA_BYTES:
        raise ShapeConverterError(
            code="archive_quota_exceeded",
            message="Request scratch quota exceeded.",
            details=f"Request scratch usage exceeded configured quota during {stage}.",
            status_code=413,
        )


def _scratch_tree_size_bytes(path: Path) -> int:
    total = 0
    for candidate in path.rglob("*"):
        if candidate.is_file():
            total += candidate.stat().st_size
    return total


def _map_capacity_os_error(
    *,
    exc: OSError,
    stage: str,
    fallback_code: str,
    fallback_message: str,
    fallback_status_code: int,
) -> ShapeConverterError:
    if exc.errno == errno.ENOSPC:
        return ShapeConverterError(
            code="service_saturated",
            message="Scratch capacity exhausted during inspect request.",
            details=f"Scratch capacity exhausted during {stage}.",
            status_code=503,
        )

    return ShapeConverterError(
        code=fallback_code,
        message=fallback_message,
        details=str(exc),
        status_code=fallback_status_code,
    )


def select_single_shapefile_dataset(extracted_archive: ExtractedArchive) -> ShapefileDataset:
    sidecar_map: dict[str, set[str]] = {}
    prefix_paths: dict[str, Path] = {}

    for extracted_file in extracted_archive.extracted_files:
        suffix = extracted_file.suffix.lower()
        if not suffix:
            continue

        normalized_prefix_key = str(extracted_file.with_suffix("").relative_to(extracted_archive.extraction_root)).lower()
        sidecar_map.setdefault(normalized_prefix_key, set()).add(suffix)
        prefix_paths.setdefault(normalized_prefix_key, extracted_file.with_suffix(""))

    complete_prefixes = [
        prefix for prefix, extensions in sidecar_map.items() if REQUIRED_SHAPEFILE_EXTENSIONS.issubset(extensions)
    ]

    if not complete_prefixes:
        if sidecar_map:
            first_prefix = sorted(sidecar_map)[0]
            missing = sorted(REQUIRED_SHAPEFILE_EXTENSIONS - sidecar_map[first_prefix])
            raise ShapeConverterError(
                code="missing_required_sidecar",
                message="Archive is missing required shapefile sidecars.",
                details=f"Dataset '{first_prefix}' missing required sidecars: {missing}.",
            )
        raise ShapeConverterError(
            code="missing_required_sidecar",
            message="Archive does not contain a shapefile dataset.",
            details="No .shp/.shx/.dbf sidecar set was found.",
        )

    if len(complete_prefixes) > 1:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Archive contains multiple shapefile datasets.",
            details=f"Detected shapefile prefixes: {sorted(complete_prefixes)}.",
        )

    selected_prefix = complete_prefixes[0]
    return ShapefileDataset(prefix_path=prefix_paths[selected_prefix])


def _build_inspect_payload(
    *,
    dataset: ShapefileDataset,
    request_id: str,
    additional_warnings: tuple[str, ...] = (),
) -> dict[str, object]:
    shp_metadata = _read_shp_metadata(dataset.prefix_path.with_suffix(".shp"))
    dbf_metadata = read_dbf_metadata(dataset.prefix_path.with_suffix(".dbf"))
    detected_crs, projection_status, projection_warnings = read_projection_metadata(
        dataset.prefix_path.with_suffix(".prj")
    )
    warnings = list(additional_warnings)
    warnings.extend(projection_warnings)

    shape_type_name = _SHAPE_TYPE_NAMES.get(shp_metadata["shape_type"], "Unknown")
    if shape_type_name == "Unknown":
        warnings.append(
            f"Unknown shapefile shape type '{shp_metadata['shape_type']}' encountered in header."
        )

    return {
        "request_id": request_id,
        "detected_crs": detected_crs,
        "projection_status": projection_status,
        "feature_count": dbf_metadata["num_records"],
        "geometry_types": [shape_type_name],
        "bbox": shp_metadata["bbox"],
        "attribute_schema": dbf_metadata["fields"],
        "warnings": warnings,
    }


def _read_shp_metadata(shp_path: Path) -> dict[str, object]:
    try:
        with shp_path.open("rb") as handle:
            header = handle.read(100)
    except OSError as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to read shapefile geometry header.",
            details=str(exc),
        ) from exc

    if len(header) < 100:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Shapefile header is truncated.",
            details=f"Expected 100 header bytes in '{shp_path.name}'.",
        )

    try:
        file_code = struct.unpack(">i", header[0:4])[0]
        version = struct.unpack("<i", header[28:32])[0]
        shape_type = struct.unpack("<i", header[32:36])[0]
        bbox = struct.unpack("<4d", header[36:68])
    except struct.error as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Failed to decode shapefile header.",
            details=str(exc),
        ) from exc

    if file_code != 9994:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Shapefile header has invalid file code.",
            details=f"Expected 9994 but found {file_code}.",
        )

    if version != 1000:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unsupported shapefile version.",
            details=f"Expected version 1000 but found {version}.",
        )

    return {
        "shape_type": int(shape_type),
        "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
    }


def read_dbf_metadata(dbf_path: Path) -> dict[str, object]:
    try:
        with dbf_path.open("rb") as handle:
            header = handle.read(32)
            if len(header) < 32:
                raise ShapeConverterError(
                    code="invalid_shapefile",
                    message="DBF header is truncated.",
                    details=f"Expected 32 header bytes in '{dbf_path.name}'.",
                )

            num_records = struct.unpack("<I", header[4:8])[0]
            header_length = struct.unpack("<H", header[8:10])[0]

            if header_length < 33:
                raise ShapeConverterError(
                    code="invalid_shapefile",
                    message="DBF header length is invalid.",
                    details=f"Header length {header_length} is smaller than minimum 33 bytes.",
                )

            fields: list[dict[str, object]] = []
            while True:
                first = handle.read(1)
                if not first:
                    raise ShapeConverterError(
                        code="invalid_shapefile",
                        message="DBF field descriptors are truncated.",
                        details=f"Field descriptor terminator missing in '{dbf_path.name}'.",
                    )
                if first == b"\r":
                    break

                remainder = handle.read(31)
                if len(remainder) < 31:
                    raise ShapeConverterError(
                        code="invalid_shapefile",
                        message="DBF field descriptor is truncated.",
                        details=f"Corrupt field descriptor in '{dbf_path.name}'.",
                    )

                descriptor = first + remainder
                raw_name = descriptor[0:11].split(b"\x00", maxsplit=1)[0]
                field_name = raw_name.decode("ascii", errors="ignore").strip()
                dbf_type = chr(descriptor[11])
                width = int(descriptor[16])
                precision = int(descriptor[17])
                fields.append(
                    {
                        "name": field_name,
                        "type": _DBF_TYPE_NAMES.get(dbf_type, "unknown"),
                        "dbf_type": dbf_type,
                        "width": width,
                        "precision": precision,
                        "nullability_note": _dbf_nullability_note(dbf_type),
                    }
                )

            return {
                "num_records": int(num_records),
                "fields": fields,
            }
    except OSError as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to read DBF metadata.",
            details=str(exc),
        ) from exc


def read_projection_metadata(prj_path: Path) -> tuple[dict[str, object] | None, str, list[str]]:
    warnings: list[str] = []

    if not prj_path.exists():
        warnings.append("Source projection file (.prj) is missing.")
        return None, "unknown", warnings

    try:
        prj_bytes = prj_path.read_bytes()
    except OSError as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to read projection file.",
            details=str(exc),
        ) from exc

    if not prj_bytes:
        warnings.append("Projection file exists but is empty.")
        return None, "invalid", warnings

    if len(prj_bytes) > _MAX_PRJ_BYTES:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Projection file exceeds size limit.",
            details=(
                f"Projection file '{prj_path.name}' is {len(prj_bytes)} bytes; "
                f"limit is {_MAX_PRJ_BYTES} bytes."
            ),
        )

    wkt_text: str | None = None
    for encoding in ("utf-8", "latin-1"):
        try:
            wkt_text = prj_bytes.decode(encoding).strip()
            break
        except UnicodeDecodeError:
            continue

    if not wkt_text:
        warnings.append("Projection file could not be decoded.")
        return None, "invalid", warnings

    try:
        parsed = CRS.from_wkt(wkt_text)
    except (CRSError, TypeError, ValueError):
        warnings.append("Projection file exists but contains invalid WKT.")
        return None, "invalid", warnings

    authority_tuple = parsed.to_authority()
    detected_crs: dict[str, object] = {"wkt": parsed.to_wkt()}
    if authority_tuple is not None:
        detected_crs["authority"] = f"{authority_tuple[0].upper()}:{authority_tuple[1]}"

    return detected_crs, "known", warnings


def _dbf_nullability_note(dbf_type: str) -> str:
    # DBF headers do not carry a strict nullable constraint bit.
    if dbf_type == "L":
        return (
            "Logical fields can encode unknown values (for example '?'), "
            "but strict nullability is not inferable from DBF metadata."
        )
    return _NULLABILITY_NOTE_FALLBACK


__all__ = [
    "ShapefileDataset",
    "inspect_uploaded_archive",
    "read_dbf_metadata",
    "read_projection_metadata",
    "select_single_shapefile_dataset",
]
