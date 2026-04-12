"""Convert endpoint implementation for CRS-aware shapefile serialization."""

from __future__ import annotations

import collections.abc as cabc
import pickle
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

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
    reproject_geometries,
    resolve_target_crs,
)
from .errors import ShapeConverterError
from .inspect import select_single_shapefile_dataset
from .serialization import serialize_geojson, serialize_geoparquet

OUTPUT_FORMAT_OPTIONS = frozenset({"geojson", "geoparquet"})
_MAX_UPLOAD_COMPRESSED_BYTES = ArchiveLimits().max_compressed_bytes
_MAX_CONVERT_FEATURES = int(os.getenv("SHAPE_CONVERTER_MAX_CONVERT_FEATURES", "1000000"))
_MAX_PARSER_PAYLOAD_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_MAX_PARSER_PAYLOAD_BYTES", str(256 * 1024 * 1024))),
)
_PARSER_SUBPROCESS_TIMEOUT_SECONDS = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_PARSER_TIMEOUT_SECONDS", "90")),
)
_PARSER_SUBPROCESS_KILL_GRACE_SECONDS = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_PARSER_KILL_GRACE_SECONDS", "5")),
)
_PARSER_WORKER_MODULE = "wepppy.microservices.shape_converter.convert_parser_worker"
_PARSER_WORKER_ENV_ALLOWLIST = frozenset(
    {
        "PATH",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONNOUSERSITE",
        "PYTHONHASHSEED",
        "LD_LIBRARY_PATH",
        "GDAL_DATA",
        "PROJ_LIB",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "TZ",
    }
)


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

    loaded = _load_shapefile(
        shp_path=dataset.prefix_path.with_suffix(".shp"),
        scratch=scratch,
    )
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


def _load_shapefile(*, shp_path: Path, scratch: RequestScratchLayout) -> LoadedShapefile:
    parser_output_path = scratch.request_dir / "parser_worker_payload.pickle"
    worker_stdout, worker_stderr = _run_parser_worker(
        shp_path=shp_path,
        output_path=parser_output_path,
        scratch=scratch,
    )

    worker_payload = _read_parser_payload(
        payload_path=parser_output_path,
        worker_stdout=worker_stdout,
        worker_stderr=worker_stderr,
    )

    return _loaded_shapefile_from_payload(worker_payload)


def _build_parser_worker_env() -> dict[str, str]:
    worker_env: dict[str, str] = {
        "LC_ALL": "C",
        "LANG": "C",
    }
    for env_var in _PARSER_WORKER_ENV_ALLOWLIST:
        env_value = os.environ.get(env_var)
        if env_value:
            worker_env[env_var] = env_value
    return worker_env


def _run_parser_worker(
    *,
    shp_path: Path,
    output_path: Path,
    scratch: RequestScratchLayout,
) -> tuple[str, str]:
    worker_command = [
        sys.executable,
        "-m",
        _PARSER_WORKER_MODULE,
        "--shp-path",
        shp_path.as_posix(),
        "--output-path",
        output_path.as_posix(),
        "--max-features",
        str(_MAX_CONVERT_FEATURES),
    ]
    worker_env = _build_parser_worker_env()

    try:
        process = subprocess.Popen(
            worker_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=scratch.request_dir.as_posix(),
            env=worker_env,
            start_new_session=True,
        )
    except OSError as exc:
        raise ShapeConverterError(
            code="reprojection_failed",
            message="Unable to start parser subprocess.",
            details=str(exc),
            status_code=500,
        ) from exc

    try:
        worker_stdout, worker_stderr = process.communicate(timeout=_PARSER_SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        try:
            worker_stdout, worker_stderr = process.communicate(timeout=1)
        except (subprocess.TimeoutExpired, OSError):
            worker_stdout, worker_stderr = "", ""
        raise ShapeConverterError(
            code="request_timeout",
            message="Convert parser exceeded timeout and was terminated.",
            details=(
                "Shapefile parser subprocess exceeded "
                f"{_PARSER_SUBPROCESS_TIMEOUT_SECONDS} seconds and the process group was terminated."
            ),
            status_code=408,
        ) from exc

    if process.returncode != 0:
        details = worker_stderr.strip() or worker_stdout.strip() or f"Parser subprocess exited with code {process.returncode}."
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=details,
        )

    return worker_stdout, worker_stderr


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    pid = process.pid
    if pid is None:
        process.kill()
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=_PARSER_SUBPROCESS_KILL_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def _read_parser_payload(
    *,
    payload_path: Path,
    worker_stdout: str,
    worker_stderr: str,
) -> dict[str, object]:
    if not payload_path.is_file():
        details = (
            worker_stderr.strip()
            or worker_stdout.strip()
            or f"Parser subprocess did not emit payload at '{payload_path}'."
        )
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=details,
        )

    try:
        payload_size = payload_path.stat().st_size
    except OSError as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=f"Parser payload stat failed: {exc}",
        ) from exc

    if payload_size > _MAX_PARSER_PAYLOAD_BYTES:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=(
                f"Parser payload size {payload_size} bytes exceeds limit "
                f"{_MAX_PARSER_PAYLOAD_BYTES} bytes."
            ),
        )

    try:
        with payload_path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError, ValueError, TypeError, AttributeError) as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details=f"Parser payload decode failed: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload was not a mapping.",
        )

    return payload


def _loaded_shapefile_from_payload(payload: dict[str, object]) -> LoadedShapefile:
    raw_bounds = payload.get("source_bounds")
    if (
        not isinstance(raw_bounds, (list, tuple))
        or len(raw_bounds) != 4
    ):
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload missing valid source bounds.",
        )
    source_bounds = (
        float(raw_bounds[0]),
        float(raw_bounds[1]),
        float(raw_bounds[2]),
        float(raw_bounds[3]),
    )

    source_crs_wkt = payload.get("source_crs_wkt")
    source_crs: CRS | None
    if source_crs_wkt is None:
        source_crs = None
    elif isinstance(source_crs_wkt, str):
        try:
            source_crs = CRS.from_wkt(source_crs_wkt)
        except (ValueError, TypeError) as exc:
            raise ShapeConverterError(
                code="invalid_shapefile",
                message="Unable to parse shapefile content for conversion.",
                details=f"Invalid source CRS in parser payload: {exc}",
            ) from exc
    else:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload source CRS field is invalid.",
        )

    raw_properties = payload.get("properties")
    raw_geometries = payload.get("geometries")
    if not isinstance(raw_properties, list) or not isinstance(raw_geometries, list):
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload properties/geometries fields are invalid.",
        )
    if len(raw_properties) != len(raw_geometries):
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload properties/geometries lengths do not match.",
        )

    properties: list[dict[str, object]] = []
    geometries: list[BaseGeometry | None] = []
    for index, feature_properties in enumerate(raw_properties):
        if isinstance(feature_properties, cabc.Mapping):
            normalized_properties = {str(key): value for key, value in feature_properties.items()}
        elif feature_properties is None:
            normalized_properties = {}
        else:
            raise ShapeConverterError(
                code="invalid_shapefile",
                message="Unable to parse shapefile content for conversion.",
                details=f"Parser payload properties at index {index} is not an object.",
            )

        geometry_payload = raw_geometries[index]
        if geometry_payload is None:
            geometry = None
        elif isinstance(geometry_payload, cabc.Mapping):
            try:
                geometry = shape(dict(geometry_payload))
            except (GEOSException, ValueError, TypeError) as exc:
                raise ShapeConverterError(
                    code="invalid_shapefile",
                    message="Unable to parse shapefile content for conversion.",
                    details=f"Invalid geometry at index {index}: {exc}",
                ) from exc
        else:
            raise ShapeConverterError(
                code="invalid_shapefile",
                message="Unable to parse shapefile content for conversion.",
                details=f"Parser payload geometry at index {index} is not an object.",
            )

        properties.append(normalized_properties)
        geometries.append(geometry)

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
