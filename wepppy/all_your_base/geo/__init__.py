"""Convenience exports for geospatial helpers and clients."""

from __future__ import annotations

from . import shapefile as shapefile
from .geo import *  # noqa: F401,F403 - expose core helpers
from .geo import __all__ as _geo_all
from .geo_transformer import GeoTransformer
from .locationinfo import RasterDatasetInterpolator, RDIOutOfBoundsException
from .webclients import elevationquery, wmesque_retrieve

__all__: list[str] = list(_geo_all) + [
    "GeoTransformer",
    "RasterDatasetInterpolator",
    "RDIOutOfBoundsException",
    "shapefile",
    "elevationquery",
    "wmesque_retrieve",
]
