"""Floodplain buffer polygon generator for HEC-RAS."""

from __future__ import annotations

import contextlib
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence, TYPE_CHECKING

import numpy as np
from affine import Affine
from scipy import ndimage
from skimage import measure
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform as shapely_transform, unary_union
from rasterio.crs import CRS
import rasterio
import pandas as pd

from wepppy.all_your_base.geo.geo import read_raster
from wepppy.all_your_base.geo.geo_transformer import GeoTransformer

if TYPE_CHECKING:  # pragma: no cover
    from wepppy.nodb.core.watershed import Watershed

__all__ = ["write_hec_buffer_gml"]

WGS84_EPSG = 4326
GML_NS = "http://www.opengis.net/gml"
BC_NS = "https://weppcloud.org/hec-ras/boundary"
BUFFER_GML_NAME = "channel_buffer.gml"
BUFFER_RASTER_NAME = "channel_buffer_raster.tif"
BUFFER_RASTER_DIRNAME = "ras"
DEFAULT_WIDTH_RULES: Mapping[int | str, float] = {
    1: 30.0,
    2: 60.0,
    3: 90.0,
    4: 120.0,
    "default": 120.0,
}
MIN_MINOR_AXIS_RATIO = 0.4
SMOOTHING_RADIUS_PX = 3


@dataclass(frozen=True)
class _KernelSpec:
    major_width_px: float
    minor_width_px: float


def write_hec_buffer_gml(
    watershed: "Watershed",
    channel_ids: Sequence[int],
    dest_dir: str,
    *,
    width_multiplier: float = 1.0,
    width_rules_m: Optional[Mapping[int | str, float]] = None,
    boundary_channel_ids: Optional[Sequence[int]] = None,
) -> Optional[dict[str, object]]:
    """Create the DSS floodplain buffer raster + GML polygon."""

    if not channel_ids:
        return None

    subwta_path = Path(getattr(watershed, "subwta", "") or "")
    relief_path = Path(getattr(watershed, "relief", "") or "")
    if not subwta_path.exists() or not relief_path.exists():
        return None

    subwta_raw, transform_values, proj = read_raster(subwta_path, dtype=np.int32)
    metric_raw, _, _ = read_raster(relief_path, dtype=np.float64)

    subwta = subwta_raw.T
    metric = metric_raw.T
    if subwta.shape != metric.shape:
        return None

    width_rules: MutableMapping[int | str, float] = dict(DEFAULT_WIDTH_RULES)
    if width_rules_m:
        width_rules.update(width_rules_m)

    affine = Affine.from_gdal(*transform_values)
    cellsize = _resolve_cellsize(affine)

    width_multiplier = max(width_multiplier, 0.01)
    kernel_cache: dict[_KernelSpec, np.ndarray] = {}
    order_lookup = _load_channel_orders(Path(watershed.wat_dir) / "channels.parquet")
    selected_ids = sorted({int(chn) for chn in channel_ids if int(chn) > 0})
    buffer_accum = np.zeros_like(subwta, dtype=np.int32)
    order_counter: Counter[str] = Counter()
    boundary_set = {int(val) for val in boundary_channel_ids or [] if int(val) > 0}

    for chn_id in selected_ids:
        mask = subwta == chn_id
        if not np.any(mask):
            continue
        rows, cols = np.where(mask)
        metric_values = metric[rows, cols]
        ordered_indices = _ordered_unique_indices(np.argsort(metric_values), rows, cols)
        if not ordered_indices:
            continue
        start_idx = 2 if len(ordered_indices) > 2 else 0
        order_value = order_lookup.get(chn_id)
        order_key = str(order_value) if order_value is not None else "unknown"
        order_counter[order_key] += 1

        width_m = width_rules.get(order_value, width_rules["default"])
        width_m *= width_multiplier
        kernel_spec = _kernel_spec(width_m, cellsize)
        offsets = kernel_cache.get(kernel_spec)
        if offsets is None:
            offsets = _build_kernel_offsets(kernel_spec)
            kernel_cache[kernel_spec] = offsets

        if chn_id in boundary_set:
            start_pos = min(start_idx, len(ordered_indices) - 1)
            iter_positions = range(start_pos, -1, -1)
        else:
            iter_positions = range(start_idx, len(ordered_indices))

        for position in iter_positions:
            idx = ordered_indices[position]
            row = int(rows[idx])
            col = int(cols[idx])
            normal = _normal_vector(rows, cols, ordered_indices, position)
            _apply_kernel(buffer_accum, row, col, offsets, normal)

    mask = buffer_accum > 0
    if not np.any(mask):
        return None

    mask = ndimage.binary_dilation(mask, structure=_build_disk_structure(SMOOTHING_RADIUS_PX))
    mask = _fill_holes(mask)
    mask_uint8 = mask.astype(np.uint8) * 255

    dest_path = Path(dest_dir)
    raster_dir = dest_path / BUFFER_RASTER_DIRNAME
    raster_dir.mkdir(parents=True, exist_ok=True)
    raster_path = raster_dir / BUFFER_RASTER_NAME
    gml_path = dest_path / BUFFER_GML_NAME

    _write_mask_raster(mask_uint8, raster_path, affine, proj)
    polygon = _mask_to_polygon(mask_uint8, affine, proj)
    if polygon is None:
        return None
    _write_polygon_gml(polygon, gml_path, {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "widthMultiplier": f"{width_multiplier:.6f}",
        "widthRulesMeters": ",".join(f"{k}:{v}" for k, v in width_rules.items()),
    })

    wd = getattr(watershed, "wd", None)
    rel_raster = _relpath_from(wd, raster_path)
    rel_gml = _relpath_from(wd, gml_path)

    return {
        "buffer_raster": rel_raster,
        "buffer_gml": rel_gml,
        "width_multiplier": width_multiplier,
        "width_rules_m": dict(width_rules),
        "pixel_cellsize_m": cellsize,
        "selected_topaz_ids": selected_ids,
        "stream_order_counts": dict(order_counter),
        "smoothing_radius_px": SMOOTHING_RADIUS_PX,
        "kernel_units": "pixels",
    }


def _resolve_cellsize(transform: Affine) -> float:
    return float((abs(transform.a) + abs(transform.e)) / 2.0)


def _kernel_spec(width_m: float, cellsize: float) -> _KernelSpec:
    width_px = max(width_m / cellsize, 1.0)
    major_width_px = max(width_px, 1.0)
    minor_width_px = max(major_width_px * MIN_MINOR_AXIS_RATIO, 1.0)
    return _KernelSpec(major_width_px=major_width_px, minor_width_px=minor_width_px)


def _build_kernel_offsets(spec: _KernelSpec) -> np.ndarray:
    half_major = spec.major_width_px / 2.0
    half_minor = spec.minor_width_px / 2.0
    col_radius = int(math.ceil(spec.major_width_px))
    row_radius = int(math.ceil(spec.minor_width_px))
    offsets: list[tuple[float, float]] = []
    for drow in range(-row_radius, row_radius + 1):
        for dcol in range(-col_radius, col_radius + 1):
            val = (dcol / half_major) ** 2 + (drow / half_minor) ** 2
            if val <= 1.0:
                offsets.append((float(drow), float(dcol)))
    return np.array(offsets, dtype=np.float32)


def _build_disk_structure(radius_px: int) -> np.ndarray:
    radius_px = max(int(radius_px), 1)
    size = radius_px * 2 + 1
    y, x = np.ogrid[-radius_px : radius_px + 1, -radius_px : radius_px + 1]
    mask = x**2 + y**2 <= radius_px**2
    return mask.astype(np.uint8)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    structure = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.uint8)
    neighbor_count = ndimage.convolve(mask.astype(np.uint8), structure, mode="constant", cval=0)
    filled = np.logical_or(mask, neighbor_count == 4)
    return filled


def _apply_kernel(
    accum: np.ndarray,
    row: int,
    col: int,
    offsets: np.ndarray,
    normal: tuple[float, float],
) -> None:
    max_rows, max_cols = accum.shape
    nx, ny = normal
    if nx == 0 and ny == 0:
        nx, ny = 1.0, 0.0
    visited: set[tuple[int, int]] = set()
    for drow, dcol in offsets:
        # Treat dcol as x, drow as y for rotation
        rx = dcol * nx - drow * ny
        ry = dcol * ny + drow * nx
        rr = row + int(round(ry))
        rc = col + int(round(rx))
        if (rr, rc) in visited:
            continue
        if 0 <= rr < max_rows and 0 <= rc < max_cols:
            accum[rr, rc] += 1
            visited.add((rr, rc))


def _normal_vector(
    rows: np.ndarray,
    cols: np.ndarray,
    ordered_indices: Sequence[int],
    position: int,
) -> tuple[float, float]:
    if not ordered_indices:
        return (1.0, 0.0)
    prev_pos = max(position - 1, 0)
    next_pos = min(position + 1, len(ordered_indices) - 1)
    prev_idx = ordered_indices[prev_pos]
    next_idx = ordered_indices[next_pos]
    ty = float(rows[next_idx] - rows[prev_idx])
    tx = float(cols[next_idx] - cols[prev_idx])
    norm = math.hypot(tx, ty)
    if norm == 0:
        return (1.0, 0.0)
    nx = -ty / norm
    ny = tx / norm
    return (nx, ny)


def _ordered_unique_indices(order: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> list[int]:
    seen: set[tuple[int, int]] = set()
    ordered: list[int] = []
    for idx in order:
        key = (int(rows[idx]), int(cols[idx]))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(int(idx))
    return ordered


def _load_channel_orders(parquet_path: Path) -> dict[int, int]:
    if not parquet_path.exists():
        return {}
    df = pd.read_parquet(parquet_path, columns=["topaz_id", "order"])
    df = df.dropna(subset=["topaz_id"])
    lookup: dict[int, int] = {}
    for record in df.itertuples(index=False):
        try:
            topaz_id = int(getattr(record, "topaz_id"))
        except (TypeError, ValueError):
            continue
        order_value = getattr(record, "order", None)
        if order_value is None or (isinstance(order_value, float) and math.isnan(order_value)):
            continue
        try:
            lookup[topaz_id] = int(order_value)
        except (TypeError, ValueError):
            continue
    return lookup


def _write_mask_raster(
    mask_u8: np.ndarray,
    raster_path: Path,
    transform: Affine,
    proj: Optional[str],
) -> None:
    height, width = mask_u8.shape
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": mask_u8.dtype,
        "transform": transform,
    }
    if proj:
        profile["crs"] = CRS.from_string(proj)

    with rasterio.open(raster_path, "w", **profile) as dst:
        dst.write(mask_u8, 1)


def _mask_to_polygon(
    mask_u8: np.ndarray,
    transform: Affine,
    proj: Optional[str],
) -> Optional[MultiPolygon | Polygon]:
    if proj is None:
        return None
    bool_mask = mask_u8 > 0
    contour_polys = _extract_contour_polygons(bool_mask, transform)
    if not contour_polys:
        return None
    merged = unary_union(contour_polys)
    if merged.is_empty:
        return None
    transformer = GeoTransformer(src_proj4=proj, dst_epsg=WGS84_EPSG)

    def _to_wgs(x: float, y: float, z: Optional[float] = None) -> tuple[float, float] | tuple[float, float, float]:
        tx, ty = transformer.transform(x, y)
        if z is None:
            return (tx, ty)
        return (tx, ty, z)

    converted = shapely_transform(_to_wgs, merged)
    if isinstance(converted, Polygon):
        return converted
    if isinstance(converted, MultiPolygon):
        return converted
    return converted.buffer(0)


def _extract_contour_polygons(mask: np.ndarray, transform: Affine) -> list[Polygon]:
    if not np.any(mask):
        return []
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant", constant_values=0)
    contours = measure.find_contours(padded.astype(np.float32), 0.5)
    geoms: list[Polygon] = []
    for contour in contours:
        if len(contour) < 3:
            continue
        # remove padding offset
        rows = contour[:, 0] - 1.0
        cols = contour[:, 1] - 1.0
        coords = [_affine_point(transform, col, row) for row, col in zip(rows, cols)]
        if not coords:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        poly = Polygon(coords)
        if poly.is_empty or not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        geoms.append(poly)
    return geoms


def _affine_point(transform: Affine, col: float, row: float) -> tuple[float, float]:
    x, y = transform * (col, row)
    return (float(x), float(y))


def _write_polygon_gml(
    polygon: MultiPolygon | Polygon,
    gml_path: Path,
    attribs: Mapping[str, str],
) -> None:
    import xml.etree.ElementTree as ET

    ET.register_namespace("gml", GML_NS)
    ET.register_namespace("bc", BC_NS)

    fc = ET.Element(ET.QName(GML_NS, "FeatureCollection"))
    member = ET.SubElement(fc, ET.QName(GML_NS, "featureMember"))
    buffer_elem = ET.SubElement(member, ET.QName(BC_NS, "ChannelBuffer"), attrib=attribs)
    multi = ET.SubElement(buffer_elem, ET.QName(GML_NS, "MultiSurface"), attrib={"srsName": "EPSG:4326"})
    polygons = polygon.geoms if isinstance(polygon, MultiPolygon) else [polygon]

    for poly in polygons:
        surface_member = ET.SubElement(multi, ET.QName(GML_NS, "surfaceMember"))
        poly_elem = ET.SubElement(surface_member, ET.QName(GML_NS, "Polygon"))
        exterior = ET.SubElement(poly_elem, ET.QName(GML_NS, "exterior"))
        ring = ET.SubElement(exterior, ET.QName(GML_NS, "LinearRing"))
        pos_list = ET.SubElement(ring, ET.QName(GML_NS, "posList"))
        pos_list.text = _format_pos_list(poly.exterior.coords)
        for interior in poly.interiors:
            inner = ET.SubElement(poly_elem, ET.QName(GML_NS, "interior"))
            inner_ring = ET.SubElement(inner, ET.QName(GML_NS, "LinearRing"))
            inner_pos_list = ET.SubElement(inner_ring, ET.QName(GML_NS, "posList"))
            inner_pos_list.text = _format_pos_list(interior.coords)

    tree = ET.ElementTree(fc)
    tree.write(gml_path, encoding="utf-8", xml_declaration=True)


def _format_pos_list(coords: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{x:.8f} {y:.8f}" for x, y in coords)


def _relpath_from(base_dir: Optional[str], target: Path) -> str:
    if not base_dir:
        return str(target)
    with contextlib.suppress(ValueError):
        return os.path.relpath(target, base_dir)
    return str(target)
