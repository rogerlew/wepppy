"""GeoJSON writer implementation for features export."""

from __future__ import annotations

from .base import SingleLayerZipWriter


class GeoJsonExportWriter(SingleLayerZipWriter):
    """Write one GeoJSON file per resolved layer and package into one zip."""

    format_token = "geojson"
    layer_extension = ".geojson"


__all__ = ["GeoJsonExportWriter"]
