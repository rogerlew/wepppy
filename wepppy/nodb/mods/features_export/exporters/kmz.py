"""KMZ writer implementation for features export."""

from __future__ import annotations

from .base import SingleLayerZipWriter


class KmzExportWriter(SingleLayerZipWriter):
    """Write one KMZ file per resolved layer and package into one zip."""

    format_token = "kmz"
    layer_extension = ".kmz"


__all__ = ["KmzExportWriter"]
