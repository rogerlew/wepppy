"""FileGDB writer implementation for features export."""

from __future__ import annotations

import collections.abc as cabc
import os
from pathlib import Path
import shutil
import stat
import subprocess

from osgeo import gdal, ogr

from .base import (
    ExportArtifactMetadata,
    ExportBackendCapabilityError,
    ExportWriter,
    ExportWriterRequest,
    FeaturesExportWriterError,
    container_layer_outputs,
    merge_warnings,
    payload_warnings,
    resolve_layer_payload_pairs,
)
from .geopackage import GeopackageExportWriter

BackendAvailabilityCheck = cabc.Callable[[], bool]
GpkgToGdbConverter = cabc.Callable[[str, str], object]
DEFAULT_OPENFILEGDB_TIMEOUT = int(os.getenv("OPENFILEGDB_COMMAND_TIMEOUT", "1800"))
OGR2OGR_BINARY = os.getenv("FEATURES_EXPORT_OGR2OGR_BINARY", "ogr2ogr")
_FILE_PERMISSION_BITS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
_DIR_PERMISSION_BITS = _FILE_PERMISSION_BITS | stat.S_IXUSR | stat.S_IXGRP


def _default_convert_gpkg_to_gdb(gpkg_path: str, gdb_path: str) -> object:
    return convert_geopackage_to_openfilegdb(gpkg_path, gdb_path)


def openfilegdb_create_available() -> bool:
    """Return whether GDAL exposes native OpenFileGDB dataset creation."""

    driver = ogr.GetDriverByName("OpenFileGDB")
    return driver is not None and driver.GetMetadataItem(gdal.DCAP_CREATE) == "YES"


def _ensure_mode_bits(path: Path, *, required_bits: int) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return

    if stat.S_ISLNK(mode):
        return

    desired_mode = mode | required_bits
    if desired_mode != mode:
        os.chmod(path, desired_mode)


def _set_gdb_tree_permissions(gdb_path: Path) -> None:
    if not gdb_path.exists():
        return

    _ensure_mode_bits(gdb_path.parent, required_bits=_DIR_PERMISSION_BITS)
    if not gdb_path.is_dir():
        _ensure_mode_bits(gdb_path, required_bits=_FILE_PERMISSION_BITS)
        return

    for root, dirs, files in os.walk(gdb_path):
        root_path = Path(root)
        _ensure_mode_bits(root_path, required_bits=_DIR_PERMISSION_BITS)
        for dirname in dirs:
            _ensure_mode_bits(root_path / dirname, required_bits=_DIR_PERMISSION_BITS)
        for filename in files:
            _ensure_mode_bits(root_path / filename, required_bits=_FILE_PERMISSION_BITS)
    _ensure_mode_bits(gdb_path, required_bits=_DIR_PERMISSION_BITS)


def convert_geopackage_to_openfilegdb(
    gpkg_path: str,
    gdb_path: str,
    *,
    timeout: int = DEFAULT_OPENFILEGDB_TIMEOUT,
    ogr2ogr_binary: str = OGR2OGR_BINARY,
) -> str:
    """Convert one GeoPackage to a zipped FileGDB with native OpenFileGDB."""

    source_path = Path(gpkg_path).resolve()
    target_path = Path(gdb_path).resolve()
    zip_path = target_path.with_suffix(f"{target_path.suffix}.zip")

    if not source_path.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {source_path}")
    if not openfilegdb_create_available():
        raise ExportBackendCapabilityError(
            "geodatabase export requires GDAL OpenFileGDB vector-create capability, "
            "but it is unavailable."
        )

    _remove_gdb_container(target_path)
    if zip_path.exists():
        zip_path.unlink()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ogr2ogr_binary,
        "-f",
        "OpenFileGDB",
        str(target_path),
        str(source_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise FeaturesExportWriterError(
            f"OpenFileGDB conversion executable not found: {ogr2ogr_binary}"
        ) from exc
    except PermissionError as exc:
        raise FeaturesExportWriterError(
            f"OpenFileGDB conversion executable is not runnable: {ogr2ogr_binary}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        _remove_gdb_container(target_path)
        raise FeaturesExportWriterError(
            f"OpenFileGDB conversion exceeded the {timeout}-second timeout."
        ) from exc

    if result.returncode != 0:
        _remove_gdb_container(target_path)
        raise FeaturesExportWriterError(
            "OpenFileGDB conversion failed:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    if not target_path.is_dir():
        _remove_gdb_container(target_path)
        raise FeaturesExportWriterError(
            f"OpenFileGDB conversion did not create expected directory: {target_path}"
        )

    _set_gdb_tree_permissions(target_path)
    try:
        shutil.make_archive(
            str(target_path),
            "zip",
            root_dir=str(target_path.parent),
            base_dir=target_path.name,
        )
    except OSError as exc:
        if zip_path.exists():
            zip_path.unlink()
        _remove_gdb_container(target_path)
        raise FeaturesExportWriterError(
            f"Failed to package OpenFileGDB output: {zip_path}"
        ) from exc
    _ensure_mode_bits(zip_path, required_bits=_FILE_PERMISSION_BITS)
    return str(target_path)


def _remove_gdb_container(gdb_path: Path) -> None:
    if not gdb_path.exists():
        return
    if gdb_path.is_dir():
        shutil.rmtree(gdb_path)
        return
    gdb_path.unlink()


class GeodatabaseExportWriter(ExportWriter):
    """Write one FileGDB zip artifact using native GDAL OpenFileGDB."""

    format_token = "geodatabase"
    _gpkg_staging_writer = GeopackageExportWriter()

    def __init__(
        self,
        *,
        backend_available: BackendAvailabilityCheck | None = None,
        gpkg_to_gdb_converter: GpkgToGdbConverter | None = None,
    ) -> None:
        self._backend_available = backend_available or openfilegdb_create_available
        self._gpkg_to_gdb_converter = gpkg_to_gdb_converter or _default_convert_gpkg_to_gdb

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        if not self._backend_available():
            raise ExportBackendCapabilityError(
                "geodatabase export requires GDAL OpenFileGDB vector-create capability, "
                "but it is unavailable."
            )

        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        gpkg_staging_path = artifact_dir / f"{request.artifact_basename}.geodatabase_source.gpkg"
        gpkg_staging_path.write_bytes(
            self._gpkg_staging_writer.build_container_bytes(request, layer_pairs)
        )

        gdb_container_path = artifact_dir / f"{request.artifact_basename}.gdb"
        self._gpkg_to_gdb_converter(str(gpkg_staging_path), str(gdb_container_path))

        gdb_zip_path = gdb_container_path.with_suffix(".gdb.zip")
        if not gdb_zip_path.exists():
            raise FeaturesExportWriterError(
                "OpenFileGDB conversion did not produce expected FileGDB archive: "
                f"{gdb_zip_path}"
            )
        _remove_gdb_container(gdb_container_path)

        relpath = gdb_zip_path.name
        warnings = merge_warnings(
            request.plan.warnings,
            payload_warnings(layer_pairs),
        )
        return ExportArtifactMetadata(
            format=self.format_token,
            artifact_relpath=relpath,
            artifact_path=str(gdb_zip_path),
            layer_outputs=container_layer_outputs(
                format_token=self.format_token,
                relpath=relpath,
                layer_payload_pairs=layer_pairs,
            ),
            warnings=warnings,
            packaged_member_relpaths=(relpath,),
        )


__all__ = [
    "BackendAvailabilityCheck",
    "DEFAULT_OPENFILEGDB_TIMEOUT",
    "GeodatabaseExportWriter",
    "GpkgToGdbConverter",
    "OGR2OGR_BINARY",
    "convert_geopackage_to_openfilegdb",
    "openfilegdb_create_available",
]
