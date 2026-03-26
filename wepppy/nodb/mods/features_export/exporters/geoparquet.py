"""GeoParquet writer implementation for features export."""

from __future__ import annotations

from .base import SingleLayerZipWriter


class GeoparquetExportWriter(SingleLayerZipWriter):
    """Write one GeoParquet file per resolved layer and package into one zip."""

    format_token = "geoparquet"
    layer_extension = ".parquet"


__all__ = ["GeoparquetExportWriter"]
