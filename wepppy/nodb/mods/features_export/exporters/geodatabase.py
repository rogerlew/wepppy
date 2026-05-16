"""FileGDB writer implementation for features export."""

from __future__ import annotations

import collections.abc as cabc
from pathlib import Path
import shutil

from wepppy import f_esri

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


def _default_convert_gpkg_to_gdb(gpkg_path: str, gdb_path: str) -> object:
    return f_esri.c2c_gpkg_to_gdb(gpkg_path, gdb_path, zip_output=True)


def _remove_gdb_container(gdb_path: Path) -> None:
    if not gdb_path.exists():
        return
    if gdb_path.is_dir():
        shutil.rmtree(gdb_path)
        return
    gdb_path.unlink()


class GeodatabaseExportWriter(ExportWriter):
    """Write one FileGDB zip artifact using the canonical f_esri conversion path."""

    format_token = "geodatabase"
    _gpkg_staging_writer = GeopackageExportWriter()

    def __init__(
        self,
        *,
        backend_available: BackendAvailabilityCheck | None = None,
        gpkg_to_gdb_converter: GpkgToGdbConverter | None = None,
    ) -> None:
        self._backend_available = backend_available or f_esri.has_f_esri
        self._gpkg_to_gdb_converter = gpkg_to_gdb_converter or _default_convert_gpkg_to_gdb

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        if not self._backend_available():
            raise ExportBackendCapabilityError(
                "geodatabase export requires f_esri backend capability, but it is unavailable."
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
                "f_esri conversion did not produce expected FileGDB archive: "
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
    "GeodatabaseExportWriter",
    "GpkgToGdbConverter",
]
