"""HEC-RAS boundary condition helper utilities."""

from __future__ import annotations

import math
import os
import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
import xml.etree.ElementTree as ET

import numpy as np

from wepppy.all_your_base.geo.geo import read_raster
from wepppy.all_your_base.geo.geo_transformer import GeoTransformer

if TYPE_CHECKING:  # pragma: no cover
    from wepppy.nodb.core.watershed import Watershed
    from wepppy.topo.watershed_abstraction.wepp_top_translator import WeppTopTranslator

__all__ = [
    "BoundaryLine",
    "build_boundary_condition_features",
]


WGS84_EPSG = 4326
GML_NS = "http://www.opengis.net/gml"
BC_NS = "https://weppcloud.org/hec-ras/boundary"
NAMESPACE_MAP = {"gml": GML_NS, "bc": BC_NS}


@dataclass(frozen=True)
class BoundaryLine:
    """Container describing a boundary condition line."""

    topaz_id: int
    wepp_id: Optional[int]
    start_lonlat: Tuple[float, float]
    end_lonlat: Tuple[float, float]
    center_lonlat: Tuple[float, float]


def build_boundary_condition_features(
    watershed: "Watershed",
    channel_ids: Sequence[int],
    dest_dir: str,
    *,
    boundary_width_m: float = 100.0,
) -> List[Dict[str, object]]:
    """Create boundary-line GeoJSON features and persist companion GML files."""

    if boundary_width_m <= 0:
        raise ValueError("boundary_width_m must be positive")

    if not channel_ids:
        return []

    subwta_path = getattr(watershed, "subwta", None)
    if not subwta_path or not os.path.exists(subwta_path):
        return []

    subwta, transform, proj = read_raster(subwta_path, dtype=np.int32)
    if proj is None:
        return []

    logger = getattr(watershed, "logger", None)
    metric = _load_metric_raster(watershed, logger)
    if metric is None or metric.shape != subwta.shape:
        return []

    transformer = GeoTransformer(src_proj4=proj, dst_epsg=WGS84_EPSG)
    translator = watershed.translator_factory()
    dest_dir_path = Path(dest_dir)
    dest_dir_path.mkdir(parents=True, exist_ok=True)
    for stale in dest_dir_path.glob("bc_*.gml"):
        with contextlib.suppress(OSError):
            stale.unlink()

    features: List[Dict[str, object]] = []

    for chn_id in sorted(set(channel_ids)):
        line = _build_boundary_line(
            chn_id,
            subwta,
            metric,
            transform,
            transformer,
            translator,
            boundary_width_m,
            logger,
        )
        if line is None:
            continue
        _write_boundary_gml(line, dest_dir_path)
        features.append(_boundary_line_feature(line, boundary_width_m))

    return features


def _load_metric_raster(
    watershed: "Watershed",
    logger: Optional[logging.Logger],
) -> Optional[np.ndarray]:
    metric_path = getattr(watershed, "relief", None)
    if not metric_path:
        if logger is not None:
            logger.error("Watershed relief raster missing; cannot build boundary lines")
        return None
    if not os.path.exists(metric_path):
        if logger is not None:
            logger.error("Relief raster does not exist at %s", metric_path)
        return None
    data, *_ = read_raster(metric_path, dtype=np.float64)
    return data


def _build_boundary_line(
    chn_topaz_id: int,
    subwta: np.ndarray,
    metric: np.ndarray,
    transform: Sequence[float],
    transformer: GeoTransformer,
    translator: "WeppTopTranslator",
    boundary_width_m: float,
    logger: Optional[logging.Logger],
) -> Optional[BoundaryLine]:
    mask = subwta == int(chn_topaz_id)
    if not np.any(mask):
        return None

    cols, rows = np.where(mask)
    values = metric[cols, rows]
    ascending_order = np.argsort(values)
    ordered_bottom_up = _ordered_unique_indices(ascending_order, cols, rows)
    if len(ordered_bottom_up) < 2:
        if logger is not None:
            logger.warning(
                "Boundary generation skipped for chn_%s (need >= 2 unique pixels)",
                chn_topaz_id,
            )
        return None

    downgraded = False

    if len(ordered_bottom_up) >= 3:
        second_idx = ordered_bottom_up[1]
        third_idx = ordered_bottom_up[2]
    else:
        second_idx = ordered_bottom_up[0]
        third_idx = ordered_bottom_up[1]
        downgraded = True

    center_idx = third_idx

    if downgraded and logger is not None:
        logger.warning(
            "Boundary generation fallback for chn_%s (insufficient pixels for spec)",
            chn_topaz_id,
        )

    second_col, second_row = cols[second_idx], rows[second_idx]
    third_col, third_row = cols[third_idx], rows[third_idx]
    center_col, center_row = cols[center_idx], rows[center_idx]

    second_xy = _cell_center(transform, second_col, second_row)
    third_xy = _cell_center(transform, third_col, third_row)
    center_xy = _cell_center(transform, center_col, center_row)

    endpoints_xy = _orthogonal_endpoints(center_xy, second_xy, third_xy, boundary_width_m)
    if endpoints_xy is None:
        if logger is not None:
            logger.warning("Boundary generation skipped for chn_%s (zero-length vector)", chn_topaz_id)
        return None

    start_lon, start_lat = transformer.transform(*endpoints_xy[0])
    end_lon, end_lat = transformer.transform(*endpoints_xy[1])
    center_lon, center_lat = transformer.transform(*center_xy)
    wepp_id = translator.wepp(top=chn_topaz_id)

    return BoundaryLine(
        topaz_id=chn_topaz_id,
        wepp_id=wepp_id,
        start_lonlat=(start_lon, start_lat),
        end_lonlat=(end_lon, end_lat),
        center_lonlat=(center_lon, center_lat),
    )


def _ordered_unique_indices(
    order: np.ndarray,
    cols: np.ndarray,
    rows: np.ndarray,
) -> List[int]:
    seen: set[Tuple[int, int]] = set()
    ordered: List[int] = []
    for idx in order:
        key = (int(cols[idx]), int(rows[idx]))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(int(idx))
    return ordered


def _cell_center(transform: Sequence[float], col: int, row: int) -> Tuple[float, float]:
    a, b, c, d, e, f = transform
    x = a + (col + 0.5) * b + (row + 0.5) * c
    y = d + (col + 0.5) * e + (row + 0.5) * f
    return x, y


def _orthogonal_endpoints(
    center_xy: Tuple[float, float],
    downstream_xy: Tuple[float, float],
    upstream_xy: Tuple[float, float],
    width_m: float,
) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    vx = upstream_xy[0] - downstream_xy[0]
    vy = upstream_xy[1] - downstream_xy[1]
    norm = math.hypot(vx, vy)
    if norm == 0:
        return None

    # normal vector rotated 90 degrees counter-clockwise
    nx = -vy / norm
    ny = vx / norm
    half = width_m / 2.0
    start = (center_xy[0] - nx * half, center_xy[1] - ny * half)
    end = (center_xy[0] + nx * half, center_xy[1] + ny * half)
    return start, end


def _boundary_line_feature(line: BoundaryLine, width_m: float) -> Dict[str, object]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [line.start_lonlat[0], line.start_lonlat[1]],
                [line.end_lonlat[0], line.end_lonlat[1]],
            ],
        },
        "properties": {
            "boundary_condition": True,
            "topaz_id": line.topaz_id,
            "wepp_id": line.wepp_id,
            "center_lon": line.center_lonlat[0],
            "center_lat": line.center_lonlat[1],
            "width_m": width_m,
        },
    }


def _write_boundary_gml(line: BoundaryLine, dest_dir: Path) -> None:
    ET.register_namespace("gml", GML_NS)
    ET.register_namespace("bc", BC_NS)

    fc = ET.Element(ET.QName(GML_NS, "FeatureCollection"))
    member = ET.SubElement(fc, ET.QName(GML_NS, "featureMember"))
    boundary = ET.SubElement(
        member,
        ET.QName(BC_NS, "BoundaryCondition"),
        attrib={
            "topazId": str(line.topaz_id),
            "weppId": str(line.wepp_id) if line.wepp_id is not None else "",
        },
    )
    line_elem = ET.SubElement(boundary, ET.QName(GML_NS, "LineString"), attrib={"srsName": "EPSG:4326"})
    pos_list = ET.SubElement(line_elem, ET.QName(GML_NS, "posList"))
    pos_list.text = _format_pos_list(line.start_lonlat, line.end_lonlat)

    tree = ET.ElementTree(fc)
    target = dest_dir / f"bc_{line.topaz_id}.gml"
    tree.write(target, encoding="utf-8", xml_declaration=True)


def _format_pos_list(
    start_lonlat: Tuple[float, float],
    end_lonlat: Tuple[float, float],
) -> str:
    return " ".join(
        f"{coord:.8f}" for coord in (*start_lonlat, *end_lonlat)
    )
