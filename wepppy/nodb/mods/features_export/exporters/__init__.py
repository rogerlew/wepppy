"""Format writer registry and helpers for features export WP-3."""

from __future__ import annotations

import collections.abc as cabc

from ..contracts import FORMAT_ALIASES
from .base import (
    ExportArtifactMetadata,
    ExportBackendCapabilityError,
    ExportPayloadValidationError,
    ExportWriter,
    ExportWriterRequest,
    ExportedLayerArtifact,
    FeaturesExportWriterError,
    MultiLayerContainerWriter,
    PreparedLayerPayload,
    SingleLayerZipWriter,
    deterministic_layer_filename,
)
from .csv import CsvExportWriter
from .geodatabase import GeodatabaseExportWriter
from .geojson import GeoJsonExportWriter
from .geopackage import GeopackageExportWriter
from .geoparquet import GeoparquetExportWriter
from .kmz import KmzExportWriter
from .parquet import ParquetExportWriter

_WRITER_FACTORIES: dict[str, cabc.Callable[[], ExportWriter]] = {
    "geojson": GeoJsonExportWriter,
    "geoparquet": GeoparquetExportWriter,
    "parquet": ParquetExportWriter,
    "csv": CsvExportWriter,
    "kmz": KmzExportWriter,
    "geopackage": GeopackageExportWriter,
    "geodatabase": GeodatabaseExportWriter,
}


def normalize_format_token(format_token: str) -> str:
    """Normalize format token to canonical writer registry key."""

    token = format_token.strip().lower()
    return FORMAT_ALIASES.get(token, token)


def get_export_writer(format_token: str) -> ExportWriter:
    """Return writer implementation for requested export format token."""

    if not isinstance(format_token, str) or not format_token.strip():
        raise FeaturesExportWriterError("format_token must be a non-empty string.")

    normalized = normalize_format_token(format_token)
    factory = _WRITER_FACTORIES.get(normalized)
    if factory is None:
        raise FeaturesExportWriterError(
            f"Unsupported export format {format_token!r}; expected one of {sorted(_WRITER_FACTORIES)}."
        )

    return factory()


def supported_writer_formats() -> tuple[str, ...]:
    """Return canonical export formats available from the writer registry."""

    return tuple(sorted(_WRITER_FACTORIES))


__all__ = [
    "ExportArtifactMetadata",
    "ExportBackendCapabilityError",
    "ExportPayloadValidationError",
    "ExportWriter",
    "ExportWriterRequest",
    "ExportedLayerArtifact",
    "FeaturesExportWriterError",
    "CsvExportWriter",
    "GeodatabaseExportWriter",
    "GeoJsonExportWriter",
    "GeopackageExportWriter",
    "GeoparquetExportWriter",
    "KmzExportWriter",
    "ParquetExportWriter",
    "MultiLayerContainerWriter",
    "PreparedLayerPayload",
    "SingleLayerZipWriter",
    "deterministic_layer_filename",
    "get_export_writer",
    "normalize_format_token",
    "supported_writer_formats",
]
