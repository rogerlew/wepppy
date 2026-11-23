"""Admission rules for channel delineation against a configured map boundary."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from pyproj import Transformer
from pyproj.exceptions import ProjError
from shapely.errors import ShapelyError
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union

from wepppy.all_your_base.geo.locationinfo import RasterDatasetInterpolator

if TYPE_CHECKING:
    from .ron import Ron


_logger = logging.getLogger(__name__)
_STATIC_ROOT = Path(__file__).resolve().parents[2] / "weppcloud" / "static"
_WGS84_NAMES = {
    "urn:ogc:def:crs:OGC:1.3:CRS84",
    "urn:ogc:def:crs:OGC::CRS84",
    "OGC:CRS84",
    "CRS84",
    "urn:ogc:def:crs:EPSG::4326",
    "EPSG:4326",
}
_NAD83_NAMES = {"urn:ogc:def:crs:EPSG::4269", "EPSG:4269"}


class ChannelBoundaryError(ValueError):
    """A channel extent rejection with a user-safe message."""

    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _setting(value: str | None) -> str:
    return (value or "").strip().strip("\"'").strip()


def _read_boundary(reference: str):
    local = reference.removeprefix("/")
    if not local.startswith("static/"):
        raise ValueError("Expected a local static boundary reference")

    root = _STATIC_ROOT.resolve(strict=True)
    relative = Path(local.removeprefix("static/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Expected a relative static boundary path")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or path.suffix.lower() not in {".json", ".geojson"} or not path.is_file():
        raise ValueError("Expected a contained regular GeoJSON boundary asset")

    with path.open(encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise ValueError("Expected a GeoJSON object")

    kind = document.get("type")
    if kind == "FeatureCollection":
        geometries = []
        for feature in document["features"]:
            if feature["type"] != "Feature":
                raise ValueError("Expected only GeoJSON features")
            geometries.append(feature["geometry"])
    elif kind == "Feature":
        geometries = [document["geometry"]]
    else:
        geometries = [document]

    polygons = []
    for geometry in geometries:
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise ValueError("Expected polygon boundary geometry")
        polygon = shape(geometry)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Invalid boundary polygon")
        polygons.append(polygon)
    if not polygons:
        raise ValueError("Empty boundary")

    boundary = unary_union(polygons)
    if "crs" in document:
        crs = document["crs"]
        if crs["type"] != "name":
            raise ValueError("Unsupported boundary coordinate reference system")
        name = crs["properties"]["name"]
        if name in _NAD83_NAMES:
            to_wgs84 = Transformer.from_crs(4269, 4326, always_xy=True)
            boundary = transform(to_wgs84.transform, boundary)
        elif name not in _WGS84_NAMES:
            raise ValueError("Unsupported boundary coordinate reference system")

    west, south, east, north = boundary.bounds
    if not boundary.is_valid or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid geographic boundary")
    return boundary


def validate_channel_extent(
    ron: Ron, extent: Sequence[float] | None = None, *, use_dem_extent: bool = False
) -> None:
    """Validate the requested extent or read it from the processing map or DEM."""
    reference = _setting(ron.config_get_raw("map", "boundary"))
    if not reference or reference.lower().startswith("none") or reference.startswith("null"):
        return

    policy = _setting(ron.config_get_raw("map", "boundary_check")).lower() or "intersects"
    if policy == "none":
        return
    try:
        if policy not in {"intersects", "covers"}:
            raise ValueError("Unsupported boundary_check policy")
        boundary = _read_boundary(reference)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, IndexError, AttributeError, ShapelyError, ProjError) as exc:
        _logger.warning("Unable to load channel boundary configuration for %s (%s)", ron.config_stem, type(exc).__name__)
        raise ChannelBoundaryError(
            "invalid_channel_boundary_config",
            "The project map boundary could not be checked. Contact support.",
            status_code=500,
        ) from None

    try:
        bounds = extent
        if use_dem_extent:
            raster = RasterDatasetInterpolator(ron.dem_fn)
            to_wgs84 = Transformer.from_crs(raster.srs.ExportToWkt(), 4326, always_xy=True)
            bounds = to_wgs84.transform_bounds(raster.left, raster.lower, raster.right, raster.upper)
        elif bounds is None:
            bounds = ron.extent
        if bounds is None or not all(math.isfinite(value) for value in bounds):
            raise ValueError("Missing or nonfinite extent")
        west, south, east, north = bounds
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("Invalid bounds")
    except (OSError, RuntimeError, ValueError, TypeError, ArithmeticError, AssertionError, ProjError):
        raise ChannelBoundaryError(
            "invalid_channel_extent", "Select a valid geographic extent to build channels."
        ) from None
    requested = box(west, south, east, north)
    if policy == "intersects" and not boundary.intersects(requested):
        raise ChannelBoundaryError(
            "channel_extent_outside_boundary",
            "Choose an extent or upload a DEM that intersects the project map boundary.",
        )
    if policy == "covers" and not boundary.covers(requested):
        raise ChannelBoundaryError(
            "channel_extent_outside_boundary",
            "Choose an extent or upload a DEM that fits entirely within the project map boundary.",
        )
