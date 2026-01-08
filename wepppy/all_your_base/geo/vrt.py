"""Helpers for building windowed VRTs from raster sources."""

from __future__ import annotations

import math
import os
from typing import Iterable, Sequence, Tuple

from osgeo import gdal
from pyproj import CRS, Transformer

__all__ = [
    "build_windowed_vrt",
    "build_windowed_vrt_from_window",
    "calculate_src_window",
]


def _open_dataset(path: str) -> gdal.Dataset:
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise FileNotFoundError(f"Raster dataset does not exist: {path}")
    return ds


def _dataset_crs(ds: gdal.Dataset) -> CRS:
    wkt = ds.GetProjection()
    if not wkt:
        raise ValueError("Dataset CRS is missing; cannot compute crop window")
    return CRS.from_wkt(wkt)


def _coerce_bbox(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain 4 values")
    min_x, min_y, max_x, max_y = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    return min(min_x, max_x), min(min_y, max_y), max(min_x, max_x), max(min_y, max_y)


def _transform_bbox(
    bbox: Sequence[float],
    bbox_crs: str,
    target_crs: CRS,
) -> Tuple[float, float, float, float]:
    src_crs = CRS.from_user_input(bbox_crs)
    min_x, min_y, max_x, max_y = _coerce_bbox(bbox)
    if src_crs.equals(target_crs):
        return min_x, min_y, max_x, max_y

    transformer = Transformer.from_crs(src_crs, target_crs, always_xy=True)
    corners = (
        (min_x, min_y),
        (min_x, max_y),
        (max_x, min_y),
        (max_x, max_y),
    )
    transformed = [transformer.transform(x, y) for x, y in corners]
    xs = [xy[0] for xy in transformed]
    ys = [xy[1] for xy in transformed]
    return min(xs), min(ys), max(xs), max(ys)


def _calculate_src_window_for_dataset(
    ds: gdal.Dataset,
    bbox: Sequence[float],
    bbox_crs: str,
    pad_px: int = 0,
) -> Tuple[int, int, int, int]:
    if pad_px < 0:
        raise ValueError("pad_px must be non-negative")

    target_crs = _dataset_crs(ds)
    min_x, min_y, max_x, max_y = _transform_bbox(bbox, bbox_crs, target_crs)

    gt = ds.GetGeoTransform()
    if gt is None:
        raise ValueError("Dataset geotransform is missing")
    if gt[2] != 0.0 or gt[4] != 0.0:
        raise ValueError("Rotated geotransforms are not supported for VRT cropping")

    x_origin, x_px, _, y_origin, _, y_px = gt
    if x_px == 0 or y_px == 0:
        raise ValueError("Invalid pixel size in geotransform")

    width = ds.RasterXSize
    height = ds.RasterYSize

    col_vals = [(min_x - x_origin) / x_px, (max_x - x_origin) / x_px]
    row_vals = [(min_y - y_origin) / y_px, (max_y - y_origin) / y_px]

    col_min = math.floor(min(col_vals)) - pad_px
    col_max = math.ceil(max(col_vals)) + pad_px
    row_min = math.floor(min(row_vals)) - pad_px
    row_max = math.ceil(max(row_vals)) + pad_px

    col_min = max(0, col_min)
    row_min = max(0, row_min)
    col_max = min(width, col_max)
    row_max = min(height, row_max)

    xsize = col_max - col_min
    ysize = row_max - row_min
    if xsize <= 0 or ysize <= 0:
        raise ValueError("Computed crop window is empty after clamping")

    return int(col_min), int(row_min), int(xsize), int(ysize)


def calculate_src_window(
    src_path: str,
    bbox: Sequence[float],
    bbox_crs: str,
    pad_px: int = 0,
) -> Tuple[int, int, int, int]:
    """Compute a pixel window for ``src_path`` from a bbox in ``bbox_crs``."""
    ds = _open_dataset(src_path)
    try:
        return _calculate_src_window_for_dataset(ds, bbox, bbox_crs, pad_px=pad_px)
    finally:
        ds = None


def _prepare_vrt_destination(dst_path: str) -> None:
    if os.path.lexists(dst_path):
        if os.path.isdir(dst_path):
            raise IsADirectoryError(f"VRT destination is a directory: {dst_path}")
        os.unlink(dst_path)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)


def build_windowed_vrt(
    src_path: str,
    dst_path: str,
    bbox: Sequence[float],
    bbox_crs: str,
    pad_px: int = 0,
) -> Tuple[int, int, int, int]:
    """Create a windowed VRT from ``src_path`` using a bbox in ``bbox_crs``."""
    ds = _open_dataset(src_path)
    try:
        src_window = _calculate_src_window_for_dataset(ds, bbox, bbox_crs, pad_px=pad_px)
        _prepare_vrt_destination(dst_path)
        result = gdal.Translate(dst_path, ds, format="VRT", srcWin=list(src_window))
        if result is None or not os.path.exists(dst_path):
            raise RuntimeError(f"Failed to create VRT: {dst_path}")
        result = None
        return src_window
    finally:
        ds = None


def build_windowed_vrt_from_window(
    src_path: str,
    dst_path: str,
    src_window: Sequence[int],
    *,
    reference_geotransform: Sequence[float] | None = None,
    reference_shape: Sequence[int] | None = None,
) -> Tuple[int, int, int, int]:
    """Create a windowed VRT from an explicit ``src_window`` (xoff, yoff, xsize, ysize)."""
    if len(src_window) != 4:
        raise ValueError("src_window must contain 4 values")

    ds = _open_dataset(src_path)
    try:
        if reference_geotransform is not None:
            gt = ds.GetGeoTransform()
            if gt is None or len(reference_geotransform) != 6:
                raise ValueError("Invalid geotransform for comparison")
            for left, right in zip(gt, reference_geotransform):
                if not math.isclose(left, right, rel_tol=0.0, abs_tol=1.0e-6):
                    raise ValueError("Raster geotransform does not match crop window reference")

        if reference_shape is not None:
            if len(reference_shape) != 2:
                raise ValueError("reference_shape must be (width, height)")
            if (ds.RasterXSize, ds.RasterYSize) != (int(reference_shape[0]), int(reference_shape[1])):
                raise ValueError("Raster shape does not match crop window reference")

        _prepare_vrt_destination(dst_path)
        result = gdal.Translate(dst_path, ds, format="VRT", srcWin=list(src_window))
        if result is None or not os.path.exists(dst_path):
            raise RuntimeError(f"Failed to create VRT: {dst_path}")
        result = None
        return tuple(int(v) for v in src_window)
    finally:
        ds = None
