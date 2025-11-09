from __future__ import annotations

from collections.abc import Sequence
import os
from typing import Any

import numpy as np
from osgeo import osr

PathType = str | os.PathLike[str]

SCRATCH_DIR: str
wgs84_proj4: str
wgs84_wkt: str
resample_methods: tuple[str, ...]


def has_f_esri() -> bool: ...


def f_esri_gpkg_to_gdb(gpkg_fn: PathType, gdb_fn: PathType) -> None: ...


def utm_raster_transform(
    wgs_extent: Sequence[float],
    src_fn: PathType,
    dst_fn: PathType,
    cellsize: float,
    resample: str = ...,
) -> None: ...


def validate_srs(file_path: PathType) -> bool: ...


def utm_srid(zone: int, northern: bool) -> str: ...


def centroid_px(indx: Sequence[float], indy: Sequence[float]) -> tuple[int, int]: ...


def crop_geojson(fn: PathType, bbox: Sequence[float]) -> dict[str, Any]: ...


def get_raster_extent(match_fn: PathType, wgs: bool = ...) -> tuple[float, ...]: ...


def raster_stacker(
    src_fn: PathType,
    match_fn: PathType,
    dst_fn: PathType,
    resample: str = ...,
) -> None: ...


def warp2match(src_filename: PathType, match_filename: PathType, dst_filename: PathType) -> None: ...


def px_to_utm(transform: Sequence[float], x: int, y: int) -> tuple[float, float]: ...


def px_to_lnglat(
    transform: Sequence[float],
    x: int,
    y: int,
    utm_proj: str,
    wgs_proj: str,
) -> tuple[float, float]: ...


def translate_tif_to_asc(fn: PathType, fn2: PathType | None = ...) -> str: ...


def translate_asc_to_tif(fn: PathType, fn2: PathType | None = ...) -> str: ...


def raster_extent(fn: PathType) -> list[float]: ...


def read_raster(
    fn: PathType,
    dtype: Any = ...,
) -> tuple[np.ndarray, tuple[float, ...], str | None]: ...


def wkt_2_proj4(wkt: str) -> str: ...


def read_tif(
    fn: PathType,
    dtype: Any = ...,
    band: int = ...,
) -> tuple[np.ndarray, tuple[float, ...], str | None]: ...


def read_arc(
    fn: PathType,
    dtype: Any = ...,
) -> tuple[np.ndarray, tuple[float, ...], str | None]: ...


def write_arc(
    data: Any,
    fname: PathType,
    ll_x: float,
    ll_y: float,
    cellsize: float,
    no_data: float = ...,
) -> None: ...


def build_mask(points: Sequence[tuple[float, float]], georef_fn: PathType) -> np.ndarray: ...


def get_utm_zone(srs: osr.SpatialReference | PathType) -> tuple[str, int, str] | None: ...


def haversine(
    point1: tuple[float, float],
    point2: tuple[float, float],
    miles: bool = ...,
) -> float: ...


def determine_band_type(vrt: PathType) -> str | None: ...


def raster_stats(src: PathType) -> dict[str, float]: ...


def format_convert(src: PathType, _format: str) -> str: ...


def crop_and_transform(
    src: PathType,
    dst: PathType,
    bbox: Sequence[float],
    layer: str = ...,
    cellsize: float = ...,
    resample: str | None = ...,
    fmt: str | None = ...,
    gdaldem: str | None = ...,
) -> None: ...


def rasterize_geometry_from_geojson(
    dem_fn: PathType,
    geometry: Any,
    dst_fn: PathType,
) -> None: ...
