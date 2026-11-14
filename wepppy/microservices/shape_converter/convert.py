"""Convert endpoint implementation for CRS-aware shapefile serialization."""

from __future__ import annotations

import collections.abc as cabc
import errno
import os
import shutil
import signal
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pyproj import CRS
from pyproj.exceptions import CRSError
from shapely.errors import EmptyPartError, GEOSException
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
from .parser_ipc import read_payload
from .inspect import read_dbf_metadata, read_projection_metadata, select_single_shapefile_dataset
from .serialization import serialize_geojson, serialize_geoparquet

OUTPUT_FORMAT_OPTIONS = frozenset({"geojson", "geoparquet"})
_MAX_UPLOAD_COMPRESSED_BYTES = ArchiveLimits().max_compressed_bytes
_MAX_CONVERT_FEATURES = int(os.getenv("SHAPE_CONVERTER_MAX_CONVERT_FEATURES", "1000000"))
_MAX_VERTICES_PER_FEATURE = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_MAX_VERTICES_PER_FEATURE", "250000")),
)
_MAX_PARSER_PAYLOAD_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_MAX_PARSER_PAYLOAD_BYTES", str(256 * 1024 * 1024))),
)
_REQUEST_SCRATCH_QUOTA_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_REQUEST_SCRATCH_QUOTA_BYTES", str(700 * 1024 * 1024))),
)
_SCRATCH_PRECHECK_FREE_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_SCRATCH_PRECHECK_FREE_BYTES", str(128 * 1024 * 1024))),
)
_PARSER_SUBPROCESS_TIMEOUT_SECONDS = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_PARSER_TIMEOUT_SECONDS", "90")),
)
_PARSER_SUBPROCESS_KILL_GRACE_SECONDS = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_PARSER_KILL_GRACE_SECONDS", "5")),
)
_MAX_PARSER_INPUT_BYTES = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_MAX_PARSER_INPUT_BYTES", str(600 * 1024 * 1024))),
)
_PARSER_MEMORY_LIMIT_BYTES = max(
    64 * 1024 * 1024,
    int(os.getenv("SHAPE_CONVERTER_PARSER_MEMORY_LIMIT_BYTES", str(512 * 1024 * 1024))),
)
_PARSER_CPU_LIMIT_SECONDS = max(
    1,
    int(os.getenv("SHAPE_CONVERTER_PARSER_CPU_LIMIT_SECONDS", "60")),
)
_PARSER_OPEN_FILE_LIMIT = max(
    8,
    int(os.getenv("SHAPE_CONVERTER_PARSER_OPEN_FILE_LIMIT", "32")),
)
_INSTALLED_PARSER_CLI = Path("/usr/local/bin/shape_parser_cli")
_SOURCE_PARSER_CLI = (
    Path(__file__).resolve().parent
    / "rust"
    / "shape_parser_cli"
    / "target"
    / "release"
    / "shape_parser_cli"
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

    _assert_scratch_free_space(
        scratch=scratch,
        required_free_bytes=len(archive_bytes) + _SCRATCH_PRECHECK_FREE_BYTES,
        stage="archive_preflight",
    )
    _assert_request_scratch_quota(
        scratch=scratch,
        additional_bytes=len(archive_bytes),
        stage="archive_write",
    )

    try:
        scratch.upload_archive_path.write_bytes(archive_bytes)
    except OSError as exc:
        raise _map_capacity_os_error(
            exc=exc,
            stage="archive_write",
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
    sidecar_warning = shp_xml_sidecar_warning_message(
        removed_sidecars=extracted_archive.removed_shp_xml_sidecars
    )
    dataset = select_single_shapefile_dataset(extracted_archive)
    dbf_metadata = read_dbf_metadata(dataset.prefix_path.with_suffix(".dbf"))
    detected_crs, projection_status, projection_warnings = read_projection_metadata(
        dataset.prefix_path.with_suffix(".prj")
    )

    if projection_status == "invalid" and target_crs != "same_as_shapefile":
        raise ShapeConverterError(
            code="invalid_source_crs",
            message="Source CRS is invalid and cannot be used for reprojection.",
            details=(
                f"target_crs={target_crs!r} requires a valid source CRS, "
                "but the uploaded dataset projection (.prj) is malformed."
            ),
        )

    _assert_request_scratch_quota(
        scratch=scratch,
        additional_bytes=_MAX_PARSER_PAYLOAD_BYTES,
        stage="parser_payload_budget",
    )
    loaded = _load_shapefile(
        shp_path=dataset.prefix_path.with_suffix(".shp"),
        scratch=scratch,
        ignore_source_crs=(
            target_crs == "same_as_shapefile" and projection_status == "invalid"
        ),
    )
    crs_plan = resolve_target_crs(
        target_crs_token=target_crs,
        source_crs=loaded.source_crs,
        source_bounds=loaded.source_bounds,
        source_projection_status=projection_status,
    )
    conversion_warnings = list(crs_plan.warnings)
    conversion_warnings.extend(projection_warnings)
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
        projection_status=projection_status,
        attribute_schema=dbf_metadata["fields"],
        detected_crs=detected_crs,
        warnings=serialized.warnings,
    )

    prefix_name = dataset.prefix_path.name
    filename = f"{prefix_name}_{target_crs}.{serialized.extension}"
    output_path = scratch.output_root / filename

    _assert_request_scratch_quota(
        scratch=scratch,
        additional_bytes=len(serialized.content),
        stage="output_write",
    )
    _assert_scratch_free_space(
        scratch=scratch,
        required_free_bytes=len(serialized.content) + _SCRATCH_PRECHECK_FREE_BYTES,
        stage="output_preflight",
    )

    try:
        scratch.output_root.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(serialized.content)
    except OSError as exc:
        raise _map_capacity_os_error(
            exc=exc,
            stage="output_write",
            fallback_code="reprojection_failed",
            fallback_message="Unable to persist converted output artifact.",
            fallback_status_code=500,
        ) from exc

    return ConvertedArtifact(
        request_id=request_id,
        filename=filename,
        content_type=serialized.content_type,
        content=serialized.content,
        metadata=metadata,
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
            message="Insufficient scratch free space for conversion request.",
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
            message="Scratch capacity exhausted during conversion request.",
            details=f"Scratch capacity exhausted during {stage}.",
            status_code=503,
        )

    return ShapeConverterError(
        code=fallback_code,
        message=fallback_message,
        details=str(exc),
        status_code=fallback_status_code,
    )


def _scratch_tree_size_bytes(path: Path) -> int:
    total = 0
    for candidate in path.rglob("*"):
        if candidate.is_file():
            total += candidate.stat().st_size
    return total


def _load_shapefile(
    *,
    shp_path: Path,
    scratch: RequestScratchLayout,
    ignore_source_crs: bool = False,
) -> LoadedShapefile:
    parser_output_path = scratch.request_dir / "parser_worker_payload.json"
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

    return _loaded_shapefile_from_payload(
        worker_payload,
        ignore_source_crs=ignore_source_crs,
    )


def _parser_cli_path() -> Path:
    configured = os.getenv("SHAPE_CONVERTER_PARSER_CLI")
    if configured:
        return Path(configured)
    if _SOURCE_PARSER_CLI.is_file() and os.access(_SOURCE_PARSER_CLI, os.X_OK):
        return _SOURCE_PARSER_CLI
    return _INSTALLED_PARSER_CLI


def probe_parser_runtime(scratch_root: Path) -> tuple[bool, str | None]:
    try:
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="parser-readiness-", dir=scratch_root) as raw_root:
            request_root = Path(raw_root)
            shp_path = request_root / "probe.shp"
            _write_readiness_dataset(shp_path)
            output_path = request_root / "payload.json"
            scratch = RequestScratchLayout(
                request_dir=request_root,
                upload_archive_path=request_root / "unused.zip",
                extraction_root=request_root,
                output_root=request_root,
            )
            _run_parser_worker(shp_path=shp_path, output_path=output_path, scratch=scratch)
            payload = _read_parser_payload(
                payload_path=output_path,
                worker_stdout="",
                worker_stderr="",
            )
    except (OSError, ShapeConverterError, ValueError, TypeError, struct.error):
        return False, "parser_runtime_probe_failed"

    if (
        payload.get("properties") != [{"READY": "yes"}]
        or payload.get("geometries")
        != [{"type": "Point", "coordinates": [1.0, 2.0]}]
        or payload.get("source_bounds") != [1.0, 2.0, 1.0, 2.0]
    ):
        return False, "parser_runtime_probe_semantics_invalid"
    return True, None


def _write_readiness_dataset(shp_path: Path) -> None:
    record_content = struct.pack("<i2d", 1, 1.0, 2.0)
    record_header = struct.pack(">2i", 1, len(record_content) // 2)
    shp_header = _readiness_shape_header(
        file_length_words=(100 + len(record_header) + len(record_content)) // 2,
    )
    shp_path.write_bytes(shp_header + record_header + record_content)

    shx_record = struct.pack(">2i", 50, len(record_content) // 2)
    shp_path.with_suffix(".shx").write_bytes(
        _readiness_shape_header(file_length_words=(100 + len(shx_record)) // 2)
        + shx_record
    )

    dbf_header = bytearray(32)
    dbf_header[0] = 0x03
    dbf_header[1:4] = bytes((126, 11, 14))
    dbf_header[4:8] = struct.pack("<I", 1)
    dbf_header[8:10] = struct.pack("<H", 65)
    dbf_header[10:12] = struct.pack("<H", 9)
    field = bytearray(32)
    field[:5] = b"READY"
    field[11] = ord("C")
    field[16] = 8
    record = b" " + b"yes".ljust(8, b" ")
    shp_path.with_suffix(".dbf").write_bytes(
        bytes(dbf_header) + bytes(field) + b"\r" + record + b"\x1a"
    )


def _readiness_shape_header(*, file_length_words: int) -> bytes:
    header = bytearray(100)
    struct.pack_into(">i", header, 0, 9994)
    struct.pack_into(">i", header, 24, file_length_words)
    struct.pack_into("<i", header, 28, 1000)
    struct.pack_into("<i", header, 32, 1)
    struct.pack_into("<4d", header, 36, 1.0, 2.0, 1.0, 2.0)
    return bytes(header)


def _build_parser_worker_env() -> dict[str, str]:
    return {
        "LC_ALL": "C",
        "LANG": "C",
    }


def _run_parser_worker(
    *,
    shp_path: Path,
    output_path: Path,
    scratch: RequestScratchLayout,
) -> tuple[str, str]:
    worker_command = [
        os.fspath(_parser_cli_path()),
        "--request-root",
        scratch.request_dir.as_posix(),
        "--shp-path",
        shp_path.as_posix(),
        "--output-path",
        output_path.as_posix(),
        "--max-features",
        str(_MAX_CONVERT_FEATURES),
        "--max-vertices-per-feature",
        str(_MAX_VERTICES_PER_FEATURE),
        "--max-payload-bytes",
        str(_MAX_PARSER_PAYLOAD_BYTES),
        "--max-input-bytes",
        str(_MAX_PARSER_INPUT_BYTES),
        "--max-memory-bytes",
        str(_PARSER_MEMORY_LIMIT_BYTES),
        "--max-cpu-seconds",
        str(_PARSER_CPU_LIMIT_SECONDS),
        "--max-open-files",
        str(_PARSER_OPEN_FILE_LIMIT),
    ]
    worker_env = _build_parser_worker_env()

    try:
        process = subprocess.Popen(
            worker_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=scratch.request_dir.as_posix(),
            env=worker_env,
            start_new_session=True,
        )
    except OSError as exc:
        raise _map_capacity_os_error(
            exc=exc,
            stage="parser_subprocess_start",
            fallback_code="reprojection_failed",
            fallback_message="Unable to start parser subprocess.",
            fallback_status_code=500,
        ) from exc

    try:
        process.communicate(timeout=_PARSER_SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        try:
            process.communicate(timeout=1)
        except (subprocess.TimeoutExpired, OSError):
            pass
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
        if process.returncode == 5:
            raise ShapeConverterError(
                code="archive_quota_exceeded",
                message="Feature vertex count exceeds configured limit.",
                details="vertex_limit_exceeded: configured vertex limit exceeded.",
                status_code=413,
            )
        if process.returncode == 4:
            raise ShapeConverterError(
                code="archive_quota_exceeded",
                message="Feature count exceeds configured limit.",
                details="Feature count exceeded limit.",
                status_code=413,
            )
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser worker failed to parse the dataset.",
        )

    return "", ""


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
    try:
        return read_payload(
            payload_path,
            max_bytes=_MAX_PARSER_PAYLOAD_BYTES,
            max_features=_MAX_CONVERT_FEATURES,
            max_vertices=_MAX_VERTICES_PER_FEATURE,
        )
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise ShapeConverterError(
            code="invalid_shapefile",
            message="Unable to parse shapefile content for conversion.",
            details="Parser payload is invalid or exceeds limit.",
        ) from exc


def _loaded_shapefile_from_payload(
    payload: dict[str, object],
    *,
    ignore_source_crs: bool = False,
) -> LoadedShapefile:
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
    if source_crs_wkt is None or ignore_source_crs:
        source_crs = None
    elif isinstance(source_crs_wkt, str):
        try:
            source_crs = CRS.from_wkt(source_crs_wkt)
        except (CRSError, ValueError, TypeError) as exc:
            raise ShapeConverterError(
                code="invalid_shapefile",
                message="Unable to parse shapefile content for conversion.",
                details="Invalid source CRS in parser payload.",
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
            except (EmptyPartError, GEOSException, IndexError, ValueError, TypeError) as exc:
                raise ShapeConverterError(
                    code="invalid_shapefile",
                    message="Unable to parse shapefile content for conversion.",
                    details="Invalid geometry in parser payload.",
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
    projection_status: str,
    attribute_schema: list[dict[str, object]],
    detected_crs: dict[str, object] | None,
    warnings: tuple[str, ...],
) -> dict[str, object]:
    geometry_types = sorted({geometry.geom_type for geometry in transformed_geometries if geometry is not None})
    bbox = _geometry_bounds(transformed_geometries)

    return {
        "request_id": request_id,
        "output_format": output_format,
        "target_crs": target_crs,
        "detected_crs": detected_crs if detected_crs is not None else crs_to_response_payload(crs_plan.source_crs),
        "projection_status": projection_status,
        "attribute_schema": attribute_schema,
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
