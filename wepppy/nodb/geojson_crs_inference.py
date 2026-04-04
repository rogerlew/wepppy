from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Optional, Tuple

from pyproj import CRS

WGS84_CRS = "EPSG:4326"
GeoBounds = Tuple[float, float, float, float]
_UTM_MIN_EASTING = 100000.0
_UTM_MAX_EASTING = 900000.0
_UTM_MIN_NORTHING = -1000000.0
_UTM_MAX_NORTHING = 11000000.0
_RATIO_THRESHOLD = 0.95

__all__ = [
    "GeojsonCrsInference",
    "collect_geojson_xy_samples",
    "infer_geojson_crs",
]


@dataclass(frozen=True)
class GeojsonCrsInference:
    crs: str
    source: str


def _as_finite_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _iter_xy_from_coordinates(node: Any) -> Iterable[Tuple[float, float]]:
    if isinstance(node, (list, tuple)):
        if len(node) >= 2:
            x = _as_finite_float(node[0])
            y = _as_finite_float(node[1])
            if x is not None and y is not None:
                yield (x, y)
                return
        for child in node:
            yield from _iter_xy_from_coordinates(child)


def _iter_xy_from_geometry(geometry: Mapping[str, Any]) -> Iterable[Tuple[float, float]]:
    geometry_type = str(geometry.get("type") or "").strip().lower()
    if geometry_type == "geometrycollection":
        geometries = geometry.get("geometries")
        if isinstance(geometries, list):
            for child in geometries:
                if isinstance(child, Mapping):
                    yield from _iter_xy_from_geometry(child)
        return

    coordinates = geometry.get("coordinates")
    if coordinates is not None:
        yield from _iter_xy_from_coordinates(coordinates)


def collect_geojson_xy_samples(payload: Mapping[str, Any], *, max_points: int = 5000) -> list[Tuple[float, float]]:
    if max_points <= 0:
        return []

    samples: list[Tuple[float, float]] = []

    features = payload.get("features")
    if isinstance(features, list):
        for feature in features:
            if not isinstance(feature, Mapping):
                continue
            geometry = feature.get("geometry")
            if not isinstance(geometry, Mapping):
                continue
            for xy in _iter_xy_from_geometry(geometry):
                samples.append(xy)
                if len(samples) >= max_points:
                    return samples
        return samples

    geometry = payload.get("geometry")
    if isinstance(geometry, Mapping):
        for xy in _iter_xy_from_geometry(geometry):
            samples.append(xy)
            if len(samples) >= max_points:
                return samples
        return samples

    if "type" in payload and "coordinates" in payload:
        for xy in _iter_xy_from_geometry(payload):
            samples.append(xy)
            if len(samples) >= max_points:
                return samples

    return samples


def _ratio_true(values: Iterable[bool]) -> float:
    total = 0
    true_count = 0
    for value in values:
        total += 1
        if value:
            true_count += 1
    if total == 0:
        return 0.0
    return true_count / total


def _looks_like_wgs84(samples: list[Tuple[float, float]]) -> bool:
    if not samples:
        return False
    return (
        _ratio_true(abs(x) <= 180.0 and abs(y) <= 90.0 for x, y in samples)
        >= _RATIO_THRESHOLD
    )


def _looks_like_project_bounds(
    samples: list[Tuple[float, float]],
    *,
    project_bounds: GeoBounds,
) -> bool:
    if not samples:
        return False
    xmin, ymin, xmax, ymax = project_bounds
    return _ratio_true(
        xmin <= x <= xmax and ymin <= y <= ymax
        for x, y in samples
    ) >= 0.05


def _is_utm_crs(project_crs: str) -> bool:
    try:
        epsg = CRS.from_user_input(project_crs).to_epsg()
    except Exception:
        return False
    if epsg is None:
        return False
    return (32601 <= epsg <= 32660) or (32701 <= epsg <= 32760)


def _looks_like_project_utm(
    samples: list[Tuple[float, float]],
    *,
    project_crs: Optional[str],
    project_bounds: Optional[GeoBounds],
) -> bool:
    if not samples:
        return False
    if project_bounds is not None and _looks_like_project_bounds(samples, project_bounds=project_bounds):
        return True
    if not project_crs or not _is_utm_crs(project_crs):
        return False
    return (
        _ratio_true(
            _UTM_MIN_EASTING <= x <= _UTM_MAX_EASTING
            and _UTM_MIN_NORTHING <= y <= _UTM_MAX_NORTHING
            for x, y in samples
        )
        >= _RATIO_THRESHOLD
    )


def infer_geojson_crs(
    payload: Mapping[str, Any],
    *,
    explicit_crs: Optional[str],
    project_crs: Optional[str],
    configured_crs: Optional[str],
    project_bounds: Optional[GeoBounds] = None,
    max_points: int = 5000,
) -> GeojsonCrsInference:
    if explicit_crs:
        return GeojsonCrsInference(crs=str(explicit_crs), source="geojson_crs")

    samples = collect_geojson_xy_samples(payload, max_points=max_points)
    if _looks_like_project_utm(samples, project_crs=project_crs, project_bounds=project_bounds):
        if project_crs:
            return GeojsonCrsInference(
                crs=str(project_crs),
                source="inferred_project_utm_coordinates",
            )

    if _looks_like_wgs84(samples):
        return GeojsonCrsInference(
            crs=WGS84_CRS,
            source="inferred_wgs84_coordinates",
        )

    if configured_crs:
        return GeojsonCrsInference(crs=str(configured_crs), source="configured_input_crs")

    return GeojsonCrsInference(crs=WGS84_CRS, source="default_wgs84")
