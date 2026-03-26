"""GeoPackage writer implementation for features export."""

from __future__ import annotations

from .base import MultiLayerContainerWriter


class GeopackageExportWriter(MultiLayerContainerWriter):
    """Write one multi-layer GeoPackage container artifact."""

    format_token = "geopackage"
    container_extension = ".gpkg"


__all__ = ["GeopackageExportWriter"]
