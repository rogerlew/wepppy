from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import rowcol
from shapely.geometry import LineString, MultiLineString, mapping, shape
from shapely.ops import substring, transform

EPSILON = 1e-9
DEFAULT_INPUT_CRS = "EPSG:4326"
DEFAULT_TOLERANCE_M = 0.5
METADATA_PREFIX = "_roads_"
DEFAULT_DESIGN_PROPERTY_KEYS: Tuple[str, ...] = ("DESIGN", "design")


@dataclass(frozen=True)
class MonotonicConversionSummary:
    """High-level counts for a GeoJSON-to-monotonic conversion run."""

    input_feature_count: int
    output_feature_count: int
    split_feature_count: int
    low_point_feature_count: int
    sample_step_m: float
    tolerance_m: float


@dataclass(frozen=True)
class _ChannelLookup:
    channel_mask: np.ndarray
    topaz_ids: np.ndarray
    transform: Any
    crs: Any


def _ensure_feature_collection(geojson: Mapping[str, Any]) -> List[Dict[str, Any]]:
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("Roads GeoJSON must be a FeatureCollection.")

    features = geojson.get("features")
    if not isinstance(features, list):
        raise ValueError("Roads GeoJSON FeatureCollection is missing a valid features list.")
    return features


def _iter_linestring_parts(geometry_obj: Any) -> Iterable[LineString]:
    if isinstance(geometry_obj, LineString):
        yield geometry_obj
        return
    if isinstance(geometry_obj, MultiLineString):
        for part in geometry_obj.geoms:
            yield part
        return
    raise ValueError(f"Unsupported geometry type for roads monotonic conversion: {geometry_obj.geom_type}")


def _first_nonfinite_xy_vertex_index(line: LineString) -> Optional[int]:
    coords = np.asarray(line.coords, dtype=float)
    if coords.ndim != 2 or coords.shape[0] == 0:
        return 0

    invalid_rows = np.flatnonzero(~np.isfinite(coords[:, :2]).all(axis=1))
    if invalid_rows.size == 0:
        return None
    return int(invalid_rows[0])


def _sample_profile(
    line_dem: LineString,
    *,
    dem_dataset: rasterio.io.DatasetReader,
    sample_step_m: float,
) -> Tuple[np.ndarray, np.ndarray]:
    invalid_vertex_index = _first_nonfinite_xy_vertex_index(line_dem)
    if invalid_vertex_index is not None:
        raise ValueError(
            "Road segment geometry contains non-finite DEM coordinates before sampling. "
            "This usually means the road coordinates or declared input_crs are invalid."
        )

    line_length = float(line_dem.length)
    if not np.isfinite(line_length):
        raise ValueError(
            "Road segment geometry has a non-finite DEM length before sampling. "
            "This usually means the road coordinates or declared input_crs are invalid."
        )

    if line_length <= EPSILON:
        raise ValueError("Cannot sample a zero-length road segment.")

    n_steps = max(int(np.ceil(line_length / sample_step_m)), 1)
    distances = np.linspace(0.0, line_length, n_steps + 1, dtype=float)
    points = [line_dem.interpolate(float(distance_m)) for distance_m in distances]
    sampled = np.fromiter(
        (
            float(val[0])
            for val in dem_dataset.sample([(point.x, point.y) for point in points], indexes=1)
        ),
        dtype=float,
    )

    if sampled.shape[0] != distances.shape[0]:
        raise RuntimeError("DEM sampling returned an unexpected number of values.")

    invalid_mask = ~np.isfinite(sampled)
    nodata = dem_dataset.nodata
    if nodata is not None:
        invalid_mask |= np.isclose(sampled, nodata, rtol=0.0, atol=1e-8)

    if np.any(invalid_mask):
        valid_indices = np.flatnonzero(~invalid_mask)
        if valid_indices.size == 0:
            raise ValueError("Road segment sampling encountered no valid DEM values.")

        start_index = int(valid_indices[0])
        end_index = int(valid_indices[-1])
        if np.any(invalid_mask[start_index : end_index + 1]):
            raise ValueError("Road segment sampling encountered interior DEM nodata gaps.")

        distances = distances[start_index : end_index + 1]
        sampled = sampled[start_index : end_index + 1]

    if sampled.shape[0] < 2:
        raise ValueError("Road segment sampling requires at least two valid DEM samples.")

    return distances, sampled


def _find_break_indices(profile_values: np.ndarray, *, tolerance_m: float) -> List[int]:
    diffs = np.diff(profile_values)
    if diffs.size == 0:
        return []

    signs = np.zeros(diffs.shape[0], dtype=np.int8)
    signs[diffs > tolerance_m] = 1
    signs[diffs < -tolerance_m] = -1

    break_indices: List[int] = []
    trend = 0
    for index, sign in enumerate(signs):
        if sign == 0:
            continue
        if trend == 0:
            trend = int(sign)
            continue
        if sign != trend:
            break_indices.append(index)
            trend = int(sign)

    return break_indices


def _split_linestring_by_distances(line: LineString, split_distances: Sequence[float]) -> List[LineString]:
    split_points = [0.0]
    for split_distance in split_distances:
        if split_distance <= split_points[-1] + EPSILON:
            continue
        if split_distance >= line.length - EPSILON:
            continue
        split_points.append(float(split_distance))
    split_points.append(line.length)

    segments: List[LineString] = []
    for start_distance, end_distance in zip(split_points[:-1], split_points[1:]):
        if end_distance - start_distance <= EPSILON:
            continue
        segment = substring(line, start_distance, end_distance, normalized=False)
        if not isinstance(segment, LineString):
            continue
        if segment.length <= EPSILON or len(segment.coords) < 2:
            continue
        segments.append(segment)
    return segments


def _split_line_to_monotonic_segments(
    line_src: LineString,
    *,
    to_dem: Transformer,
    from_dem: Transformer,
    dem_dataset: rasterio.io.DatasetReader,
    sample_step_m: float,
    tolerance_m: float,
    input_crs: str,
    feature_index: int,
    part_index: int,
) -> List[Tuple[LineString, LineString]]:
    line_dem = transform(to_dem.transform, line_src)
    invalid_vertex_index = _first_nonfinite_xy_vertex_index(line_dem)
    if invalid_vertex_index is not None:
        raise ValueError(
            f"Road feature at index {feature_index} part {part_index} transformed to non-finite DEM "
            f"coordinates at vertex {invalid_vertex_index}. This usually means the uploaded road "
            f"coordinates do not match roads input_crs={input_crs!r}."
        )
    try:
        distances, elevations = _sample_profile(line_dem, dem_dataset=dem_dataset, sample_step_m=sample_step_m)
    except ValueError as exc:
        if str(exc) == "Road segment sampling encountered no valid DEM values.":
            raise ValueError(
                f"Road feature at index {feature_index} part {part_index} has no valid DEM samples. "
                "This usually means that road geometry does not overlap the project's DEM extent."
            ) from exc
        raise
    valid_start_distance = float(distances[0])
    valid_end_distance = float(distances[-1])
    if valid_end_distance - valid_start_distance <= EPSILON:
        raise ValueError("Road segment sampling produced an invalid valid-distance interval.")

    if valid_start_distance <= EPSILON and valid_end_distance >= line_dem.length - EPSILON:
        valid_line_dem = line_dem
    else:
        valid_line_dem = substring(line_dem, valid_start_distance, valid_end_distance, normalized=False)
        if not isinstance(valid_line_dem, LineString):
            raise RuntimeError("Failed to clip road segment to valid DEM sampling interval.")

    break_indices = _find_break_indices(elevations, tolerance_m=tolerance_m)
    if not break_indices:
        if valid_line_dem is line_dem:
            return [(line_src, line_dem)]
        segment_src = transform(from_dem.transform, valid_line_dem)
        if not isinstance(segment_src, LineString):
            raise RuntimeError("Failed to transform clipped road segment to source CRS.")
        return [(segment_src, valid_line_dem)]

    split_distances = [float(distances[index] - valid_start_distance) for index in break_indices]
    segments_dem = _split_linestring_by_distances(valid_line_dem, split_distances)

    segments_src: List[Tuple[LineString, LineString]] = []
    for segment_dem in segments_dem:
        segment_src = transform(from_dem.transform, segment_dem)
        if not isinstance(segment_src, LineString):
            continue
        if segment_src.length <= EPSILON or len(segment_src.coords) < 2:
            continue
        segments_src.append((segment_src, segment_dem))

    if not segments_src:
        raise RuntimeError("Road segmentation produced no valid output segments.")
    return segments_src


def _segment_low_point(
    segment_dem: LineString,
    *,
    dem_dataset: rasterio.io.DatasetReader,
    sample_step_m: float,
) -> Tuple[float, float, float]:
    distances, elevations = _sample_profile(
        segment_dem,
        dem_dataset=dem_dataset,
        sample_step_m=sample_step_m,
    )
    min_index = int(np.argmin(elevations))
    low_point_dem = segment_dem.interpolate(float(distances[min_index]))
    return float(low_point_dem.x), float(low_point_dem.y), float(elevations[min_index])


def _resolve_channel_and_topaz_paths(
    *,
    dem_path: str | Path,
    channel_raster_path: Optional[str | Path],
    topaz_id_raster_path: Optional[str | Path],
) -> Tuple[Optional[Path], Optional[Path]]:
    if channel_raster_path is not None:
        resolved_channel = Path(channel_raster_path)
    else:
        dem_dir = Path(dem_path).resolve().parent
        channel_candidates = (
            dem_dir / "netful.tif",
            dem_dir / "netful0.tif",
        )
        resolved_channel = next((candidate for candidate in channel_candidates if candidate.exists()), None)

    if topaz_id_raster_path is not None:
        resolved_topaz = Path(topaz_id_raster_path)
    else:
        dem_dir = Path(dem_path).resolve().parent
        candidate = dem_dir / "subwta.tif"
        resolved_topaz = candidate if candidate.exists() else None

    return resolved_channel, resolved_topaz


def _load_channel_lookup(
    *,
    dem_path: str | Path,
    channel_raster_path: Optional[str | Path],
    topaz_id_raster_path: Optional[str | Path],
) -> Optional[_ChannelLookup]:
    resolved_channel, resolved_topaz = _resolve_channel_and_topaz_paths(
        dem_path=dem_path,
        channel_raster_path=channel_raster_path,
        topaz_id_raster_path=topaz_id_raster_path,
    )
    if resolved_channel is None or resolved_topaz is None:
        return None

    if not resolved_channel.exists():
        raise FileNotFoundError(f"Channel raster not found: {resolved_channel}")
    if not resolved_topaz.exists():
        raise FileNotFoundError(f"Topaz ID raster not found: {resolved_topaz}")

    with rasterio.open(str(resolved_channel)) as channel_ds, rasterio.open(str(resolved_topaz)) as topaz_ds:
        if channel_ds.crs != topaz_ds.crs:
            raise ValueError("Channel raster CRS does not match topaz-id raster CRS.")
        if channel_ds.transform != topaz_ds.transform:
            raise ValueError("Channel raster transform does not match topaz-id raster transform.")
        if channel_ds.width != topaz_ds.width or channel_ds.height != topaz_ds.height:
            raise ValueError("Channel raster shape does not match topaz-id raster shape.")

        channel_arr = channel_ds.read(1, masked=True)
        channel_values = np.asarray(channel_arr.filled(0.0), dtype=float)
        channel_mask = np.ones(channel_values.shape, dtype=bool)
        if np.ma.isMaskedArray(channel_arr):
            channel_mask &= ~np.ma.getmaskarray(channel_arr)
        channel_mask &= np.isfinite(channel_values)
        channel_nodata = channel_ds.nodata
        if channel_nodata is not None and np.isfinite(channel_nodata):
            channel_mask &= ~np.isclose(channel_values, channel_nodata, rtol=0.0, atol=1e-8)
        channel_mask &= channel_values > 0.0

        topaz_arr = topaz_ds.read(1, masked=True)
        topaz_values = np.asarray(topaz_arr.filled(np.nan), dtype=float)
        if np.ma.isMaskedArray(topaz_arr):
            topaz_values[np.ma.getmaskarray(topaz_arr)] = np.nan
        topaz_nodata = topaz_ds.nodata
        if topaz_nodata is not None and np.isfinite(topaz_nodata):
            topaz_values[np.isclose(topaz_values, topaz_nodata, rtol=0.0, atol=1e-8)] = np.nan
        topaz_values[~np.isfinite(topaz_values)] = np.nan

        return _ChannelLookup(
            channel_mask=channel_mask,
            topaz_ids=topaz_values,
            transform=channel_ds.transform,
            crs=channel_ds.crs,
        )


def _lookup_channel_topaz_id_at_or_near_lowpoint(
    channel_lookup: _ChannelLookup, *, low_point_dem_x: float, low_point_dem_y: float
) -> Tuple[Optional[int], Dict[str, Any]]:
    row, col = rowcol(channel_lookup.transform, low_point_dem_x, low_point_dem_y)
    row_i = int(row)
    col_i = int(col)

    offsets = (
        (0, 0),
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    )

    diagnostics: Dict[str, Any] = {
        "lowpoint_row": row_i,
        "lowpoint_col": col_i,
        "channel_search_offsets_total": len(offsets),
        "channel_search_rank": None,
        "channel_search_offset": None,
        "channel_found": False,
    }

    rows, cols = channel_lookup.channel_mask.shape
    for index, (row_offset, col_offset) in enumerate(offsets):
        rr = int(row_i + row_offset)
        cc = int(col_i + col_offset)
        if rr < 0 or cc < 0 or rr >= rows or cc >= cols:
            continue
        if not bool(channel_lookup.channel_mask[rr, cc]):
            continue

        topaz_value = float(channel_lookup.topaz_ids[rr, cc])
        if not np.isfinite(topaz_value):
            continue
        topaz_id = int(round(topaz_value))
        diagnostics["channel_search_rank"] = int(index)
        diagnostics["channel_search_offset"] = f"{row_offset},{col_offset}"
        diagnostics["channel_found"] = True
        return topaz_id, diagnostics

    return None, diagnostics


def _is_hillslope_topaz_id(topaz_id: Optional[int]) -> bool:
    if topaz_id is None:
        return False
    return abs(int(topaz_id)) % 10 in {1, 2, 3}


def _lookup_topaz_id_at_lowpoint_cell(
    channel_lookup: _ChannelLookup,
    *,
    low_point_dem_x: float,
    low_point_dem_y: float,
) -> Tuple[Optional[int], Dict[str, Any]]:
    row, col = rowcol(channel_lookup.transform, low_point_dem_x, low_point_dem_y)
    row_i = int(row)
    col_i = int(col)

    diagnostics: Dict[str, Any] = {
        "lowpoint_row": row_i,
        "lowpoint_col": col_i,
        "lowpoint_topaz_id": None,
        "lowpoint_topaz_suffix": None,
        "lowpoint_is_hillslope_pixel": False,
    }

    rows, cols = channel_lookup.topaz_ids.shape
    if row_i < 0 or col_i < 0 or row_i >= rows or col_i >= cols:
        return None, diagnostics

    value = float(channel_lookup.topaz_ids[row_i, col_i])
    if not np.isfinite(value):
        return None, diagnostics

    topaz_id = int(round(value))
    diagnostics["lowpoint_topaz_id"] = int(topaz_id)
    diagnostics["lowpoint_topaz_suffix"] = int(abs(topaz_id) % 10)
    diagnostics["lowpoint_is_hillslope_pixel"] = bool(_is_hillslope_topaz_id(topaz_id))
    return topaz_id, diagnostics


def _is_eligible_inslope_design(design_value: Any) -> bool:
    return isinstance(design_value, str) and design_value.lower() in {"inslope_bd", "inslope_rd"}


def _resolve_eligible_inslope_design(
    properties: Mapping[str, Any],
    *,
    design_property_keys: Sequence[str],
) -> Tuple[Optional[str], Optional[str]]:
    for key in design_property_keys:
        raw_value = properties.get(key)
        if raw_value is None:
            continue
        design_value = str(raw_value).strip()
        if not design_value:
            continue
        if _is_eligible_inslope_design(design_value):
            return design_value, key
    return None, None


def _lookup_hillslope_topaz_id_near_lowpoint(
    channel_lookup: _ChannelLookup,
    *,
    low_point_dem_x: float,
    low_point_dem_y: float,
    topaz_id_chn_lowpoint: int,
) -> Tuple[Optional[int], Dict[str, Any]]:
    topaz_id_chn_lowpoint_i = int(topaz_id_chn_lowpoint)
    candidate_center = topaz_id_chn_lowpoint_i - 3
    candidate_right = topaz_id_chn_lowpoint_i - 2
    candidate_left = topaz_id_chn_lowpoint_i - 1
    diagnostics: Dict[str, Any] = {
        "hillslope_candidates": [candidate_center, candidate_right, candidate_left],
        "hillslope_search_max_radius": 6,
        "hillslope_search_radius": None,
        "hillslope_search_cells_inspected": 0,
        "hillslope_found": False,
        "hillslope_decision": "unresolved",
    }

    if topaz_id_chn_lowpoint_i % 10 != 4:
        diagnostics["hillslope_decision"] = "invalid_channel_topaz_suffix"
        return None, diagnostics

    candidate_priority = {
        candidate_center: 0,
        candidate_right: 1,
        candidate_left: 2,
    }
    candidate_ids = set(candidate_priority)

    row, col = rowcol(channel_lookup.transform, low_point_dem_x, low_point_dem_y)
    row_i = int(row)
    col_i = int(col)
    rows, cols = channel_lookup.topaz_ids.shape

    best: Optional[Tuple[float, int, int]] = None
    best_topaz_id: Optional[int] = None

    max_radius = 6
    for radius in range(max_radius + 1):
        row_start = max(0, row_i - radius)
        row_stop = min(rows, row_i + radius + 1)
        col_start = max(0, col_i - radius)
        col_stop = min(cols, col_i + radius + 1)

        for rr in range(row_start, row_stop):
            for cc in range(col_start, col_stop):
                diagnostics["hillslope_search_cells_inspected"] += 1
                value = float(channel_lookup.topaz_ids[rr, cc])
                if not np.isfinite(value):
                    continue

                topaz_id = int(round(value))
                if topaz_id not in candidate_ids:
                    continue

                distance = float((rr - row_i) ** 2 + (cc - col_i) ** 2)
                sort_key = (distance, candidate_priority[topaz_id], topaz_id)
                if best is None or sort_key < best:
                    best = sort_key
                    best_topaz_id = topaz_id

        if best_topaz_id is not None and best is not None and best[0] <= float(radius**2):
            diagnostics["hillslope_search_radius"] = int(radius)
            break

    if best_topaz_id is None:
        diagnostics["hillslope_decision"] = "no_receiving_hillslope_candidate_near_lowpoint"
        return None, diagnostics

    diagnostics["hillslope_found"] = True
    diagnostics["hillslope_decision"] = "mapped"
    diagnostics["hillslope_selected_distance_sq"] = float(best[0]) if best is not None else None
    diagnostics["hillslope_selected_priority"] = int(best[1]) if best is not None else None
    return best_topaz_id, diagnostics


def convert_geojson_to_monotonic_segments(
    roads_geojson: Mapping[str, Any],
    *,
    dem_path: str | Path,
    input_crs: str = DEFAULT_INPUT_CRS,
    sample_step_m: Optional[float] = None,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    channel_raster_path: Optional[str | Path] = None,
    topaz_id_raster_path: Optional[str | Path] = None,
    design_property_keys: Sequence[str] = DEFAULT_DESIGN_PROPERTY_KEYS,
    add_segment_metadata: bool = False,
) -> Tuple[Dict[str, Any], MonotonicConversionSummary]:
    """
    Split road paths into monotonic-elevation segments.

    Parameters
    ----------
    roads_geojson:
        Road feature collection containing LineString/MultiLineString geometries.
    dem_path:
        DEM raster used for elevation sampling.
    input_crs:
        CRS for the road coordinates. Defaults to RFC-7946 GeoJSON CRS (EPSG:4326).
    sample_step_m:
        Sampling spacing in meters along each road path. Defaults to DEM pixel size.
    tolerance_m:
        Elevation delta tolerance when detecting direction reversals.
    add_segment_metadata:
        If True, appends `_roads_*` metadata keys to each output feature property map.
        Original properties are preserved either way.
    channel_raster_path/topaz_id_raster_path:
        Optional rasters for channel-neighbor lookup at segment low points.
        Adds `topaz_id_chn_lowpoint` and `topaz_id_hill_lowpoint` to each segment
        (defaults null; set for DESIGN in `Inslope_bd`/`Inslope_rd` when a
        deterministic nearby channel and receiving hillslope are found).
    design_property_keys:
        Ordered property keys checked for inslope design eligibility.
        Defaults to `("DESIGN", "design")`.
    """

    output_geojson, _, summary = _convert_geojson_to_monotonic_segments_internal(
        roads_geojson,
        dem_path=dem_path,
        input_crs=input_crs,
        sample_step_m=sample_step_m,
        tolerance_m=tolerance_m,
        channel_raster_path=channel_raster_path,
        topaz_id_raster_path=topaz_id_raster_path,
        design_property_keys=design_property_keys,
        add_segment_metadata=add_segment_metadata,
    )
    return output_geojson, summary


def convert_geojson_to_monotonic_segments_with_low_points(
    roads_geojson: Mapping[str, Any],
    *,
    dem_path: str | Path,
    input_crs: str = DEFAULT_INPUT_CRS,
    sample_step_m: Optional[float] = None,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    channel_raster_path: Optional[str | Path] = None,
    topaz_id_raster_path: Optional[str | Path] = None,
    design_property_keys: Sequence[str] = DEFAULT_DESIGN_PROPERTY_KEYS,
    add_segment_metadata: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any], MonotonicConversionSummary]:
    """Return both monotonic segment features and per-segment low-point features."""

    return _convert_geojson_to_monotonic_segments_internal(
        roads_geojson,
        dem_path=dem_path,
        input_crs=input_crs,
        sample_step_m=sample_step_m,
        tolerance_m=tolerance_m,
        channel_raster_path=channel_raster_path,
        topaz_id_raster_path=topaz_id_raster_path,
        design_property_keys=design_property_keys,
        add_segment_metadata=add_segment_metadata,
    )


def _convert_geojson_to_monotonic_segments_internal(
    roads_geojson: Mapping[str, Any],
    *,
    dem_path: str | Path,
    input_crs: str,
    sample_step_m: Optional[float],
    tolerance_m: float,
    channel_raster_path: Optional[str | Path],
    topaz_id_raster_path: Optional[str | Path],
    design_property_keys: Sequence[str],
    add_segment_metadata: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any], MonotonicConversionSummary]:
    if tolerance_m < 0.0:
        raise ValueError("tolerance_m must be >= 0.")

    normalized_design_property_keys = tuple(
        key.strip()
        for key in design_property_keys
        if isinstance(key, str) and key.strip()
    )
    if not normalized_design_property_keys:
        normalized_design_property_keys = DEFAULT_DESIGN_PROPERTY_KEYS

    features = _ensure_feature_collection(roads_geojson)

    output_geojson: Dict[str, Any] = {
        key: copy.deepcopy(value) for key, value in roads_geojson.items() if key != "features"
    }
    output_geojson["type"] = "FeatureCollection"
    output_features: List[Dict[str, Any]] = []

    low_points_geojson: Dict[str, Any] = {
        "type": "FeatureCollection",
        "features": [],
    }
    low_point_features: List[Dict[str, Any]] = []

    split_feature_count = 0
    segment_counter = 0
    total_source_parts = 0
    skipped_no_dem_sample_parts: List[Tuple[int, int]] = []

    channel_lookup = _load_channel_lookup(
        dem_path=dem_path,
        channel_raster_path=channel_raster_path,
        topaz_id_raster_path=topaz_id_raster_path,
    )

    with rasterio.open(str(dem_path)) as dem_dataset:
        dem_crs = dem_dataset.crs
        if dem_crs is None:
            raise ValueError("DEM must have a CRS for monotonic segmentation.")
        if channel_lookup is not None and channel_lookup.crs != dem_crs:
            raise ValueError("Channel/topaz rasters must share the same CRS as the DEM.")

        pixel_size_m = abs(float(dem_dataset.transform.a))
        effective_step_m = pixel_size_m if sample_step_m is None else float(sample_step_m)
        if effective_step_m <= 0.0:
            raise ValueError("sample_step_m must be > 0.")

        to_dem = Transformer.from_crs(input_crs, dem_crs, always_xy=True)
        from_dem = Transformer.from_crs(dem_crs, input_crs, always_xy=True)

        for feature_index, feature in enumerate(features):
            geometry_payload = feature.get("geometry")
            if geometry_payload is None:
                raise ValueError(f"Feature at index {feature_index} is missing geometry.")

            source_geometry = shape(geometry_payload)
            source_parts = list(_iter_linestring_parts(source_geometry))
            source_part_count = len(source_parts)
            emitted_for_feature = 0

            for part_index, part in enumerate(source_parts):
                total_source_parts += 1
                try:
                    monotonic_parts = _split_line_to_monotonic_segments(
                        part,
                        to_dem=to_dem,
                        from_dem=from_dem,
                        dem_dataset=dem_dataset,
                        sample_step_m=effective_step_m,
                        tolerance_m=tolerance_m,
                        input_crs=input_crs,
                        feature_index=feature_index,
                        part_index=part_index,
                    )
                except ValueError as exc:
                    if "has no valid DEM samples" in str(exc):
                        skipped_no_dem_sample_parts.append((feature_index, part_index))
                        continue
                    raise

                for segment_index, (segment_src, segment_dem) in enumerate(monotonic_parts):
                    segment_counter += 1
                    segment_id = f"roads-seg-{segment_counter:06d}"

                    properties = copy.deepcopy(feature.get("properties", {}))
                    if "segment_id" in properties:
                        properties[f"{METADATA_PREFIX}original_segment_id"] = properties["segment_id"]
                    properties["segment_id"] = segment_id

                    low_point_dem_x, low_point_dem_y, low_point_z = _segment_low_point(
                        segment_dem,
                        dem_dataset=dem_dataset,
                        sample_step_m=effective_step_m,
                    )
                    low_point_x, low_point_y = from_dem.transform(low_point_dem_x, low_point_dem_y)

                    properties[f"{METADATA_PREFIX}low_point_x"] = float(low_point_x)
                    properties[f"{METADATA_PREFIX}low_point_y"] = float(low_point_y)
                    properties[f"{METADATA_PREFIX}low_point_elevation_m"] = float(low_point_z)

                    topaz_id_chn_lowpoint: Optional[int] = None
                    topaz_id_hill_lowpoint: Optional[int] = None
                    design_value, design_source_key = _resolve_eligible_inslope_design(
                        properties,
                        design_property_keys=normalized_design_property_keys,
                    )
                    is_design_eligible = design_value is not None
                    channel_diagnostics: Dict[str, Any] = {}
                    lowpoint_topaz_diagnostics: Dict[str, Any] = {}
                    hillslope_diagnostics: Dict[str, Any] = {}
                    lowpoint_decision = "design_not_eligible"
                    routing_eligibility = "design_not_eligible"
                    non_channel_routable = False

                    if is_design_eligible and channel_lookup is None:
                        lowpoint_decision = "missing_channel_lookup_rasters"
                        routing_eligibility = "missing_channel_lookup_rasters"
                    elif is_design_eligible and channel_lookup is not None:
                        _, lowpoint_topaz_diagnostics = _lookup_topaz_id_at_lowpoint_cell(
                            channel_lookup,
                            low_point_dem_x=low_point_dem_x,
                            low_point_dem_y=low_point_dem_y,
                        )
                        topaz_id_chn_lowpoint, channel_diagnostics = _lookup_channel_topaz_id_at_or_near_lowpoint(
                            channel_lookup,
                            low_point_dem_x=low_point_dem_x,
                            low_point_dem_y=low_point_dem_y,
                        )
                        if topaz_id_chn_lowpoint is None:
                            if bool(lowpoint_topaz_diagnostics.get("lowpoint_is_hillslope_pixel")):
                                lowpoint_decision = "non_channel_hillslope_routable"
                                routing_eligibility = "non_channel_routable"
                                non_channel_routable = True
                            else:
                                lowpoint_decision = "no_channel_pixel_near_lowpoint"
                                routing_eligibility = "non_routable"
                        else:
                            topaz_id_hill_lowpoint, hillslope_diagnostics = _lookup_hillslope_topaz_id_near_lowpoint(
                                channel_lookup,
                                low_point_dem_x=low_point_dem_x,
                                low_point_dem_y=low_point_dem_y,
                                topaz_id_chn_lowpoint=topaz_id_chn_lowpoint,
                            )
                            lowpoint_decision = str(
                                hillslope_diagnostics.get("hillslope_decision")
                                or "no_receiving_hillslope_candidate_near_lowpoint"
                            )
                            routing_eligibility = "non_routable"
                            if topaz_id_hill_lowpoint is not None:
                                lowpoint_decision = "mapped"
                                routing_eligibility = "channel_associated"

                    properties["topaz_id_chn_lowpoint"] = (
                        int(topaz_id_chn_lowpoint) if topaz_id_chn_lowpoint is not None else None
                    )
                    properties["topaz_id_hill_lowpoint"] = (
                        int(topaz_id_hill_lowpoint) if topaz_id_hill_lowpoint is not None else None
                    )
                    properties[f"{METADATA_PREFIX}design_source_key"] = design_source_key
                    properties[f"{METADATA_PREFIX}design_eligible"] = bool(is_design_eligible)
                    properties[f"{METADATA_PREFIX}channel_lookup_available"] = bool(channel_lookup is not None)
                    properties[f"{METADATA_PREFIX}lowpoint_decision"] = str(lowpoint_decision)
                    properties[f"{METADATA_PREFIX}routing_eligibility"] = str(routing_eligibility)
                    properties[f"{METADATA_PREFIX}non_channel_routable"] = bool(non_channel_routable)
                    properties[f"{METADATA_PREFIX}lowpoint_topaz_id"] = lowpoint_topaz_diagnostics.get(
                        "lowpoint_topaz_id"
                    )
                    properties[f"{METADATA_PREFIX}lowpoint_topaz_suffix"] = lowpoint_topaz_diagnostics.get(
                        "lowpoint_topaz_suffix"
                    )
                    properties[f"{METADATA_PREFIX}lowpoint_is_hillslope_pixel"] = lowpoint_topaz_diagnostics.get(
                        "lowpoint_is_hillslope_pixel"
                    )

                    properties[f"{METADATA_PREFIX}lowpoint_row"] = channel_diagnostics.get("lowpoint_row")
                    properties[f"{METADATA_PREFIX}lowpoint_col"] = channel_diagnostics.get("lowpoint_col")
                    properties[f"{METADATA_PREFIX}channel_search_rank"] = channel_diagnostics.get(
                        "channel_search_rank"
                    )
                    properties[f"{METADATA_PREFIX}channel_search_offset"] = channel_diagnostics.get(
                        "channel_search_offset"
                    )
                    properties[f"{METADATA_PREFIX}channel_search_offsets_total"] = channel_diagnostics.get(
                        "channel_search_offsets_total"
                    )
                    properties[f"{METADATA_PREFIX}channel_found"] = channel_diagnostics.get("channel_found")

                    properties[f"{METADATA_PREFIX}hillslope_candidates"] = hillslope_diagnostics.get(
                        "hillslope_candidates"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_search_radius"] = hillslope_diagnostics.get(
                        "hillslope_search_radius"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_search_max_radius"] = hillslope_diagnostics.get(
                        "hillslope_search_max_radius"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_search_cells_inspected"] = hillslope_diagnostics.get(
                        "hillslope_search_cells_inspected"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_found"] = hillslope_diagnostics.get("hillslope_found")
                    properties[f"{METADATA_PREFIX}hillslope_decision"] = hillslope_diagnostics.get(
                        "hillslope_decision"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_selected_distance_sq"] = hillslope_diagnostics.get(
                        "hillslope_selected_distance_sq"
                    )
                    properties[f"{METADATA_PREFIX}hillslope_selected_priority"] = hillslope_diagnostics.get(
                        "hillslope_selected_priority"
                    )

                    if add_segment_metadata:
                        properties.update(
                            {
                                f"{METADATA_PREFIX}source_feature_index": feature_index,
                                f"{METADATA_PREFIX}source_part_index": part_index,
                                f"{METADATA_PREFIX}segment_index": segment_index,
                                f"{METADATA_PREFIX}segment_count_for_part": len(monotonic_parts),
                            }
                        )

                    output_features.append(
                        {
                            "type": "Feature",
                            "geometry": mapping(segment_src),
                            "properties": properties,
                        }
                    )
                    emitted_for_feature += 1

                    low_point_properties = copy.deepcopy(properties)
                    low_point_properties[f"{METADATA_PREFIX}feature_type"] = "segment_low_point"
                    low_point_features.append(
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [float(low_point_x), float(low_point_y)],
                            },
                            "properties": low_point_properties,
                        }
                    )

            if emitted_for_feature > source_part_count:
                split_feature_count += 1

    output_geojson["features"] = output_features
    low_points_geojson["features"] = low_point_features

    if not output_features and skipped_no_dem_sample_parts:
        examples = ", ".join(
            f"feature {feature_index} part {part_index}"
            for feature_index, part_index in skipped_no_dem_sample_parts[:5]
        )
        raise ValueError(
            "Road monotonic conversion found no segments overlapping valid DEM cells "
            f"(skipped {len(skipped_no_dem_sample_parts)}/{total_source_parts} source parts; "
            f"examples: {examples}). Check that uploaded roads overlap the project DEM extent."
        )

    summary = MonotonicConversionSummary(
        input_feature_count=len(features),
        output_feature_count=len(output_features),
        split_feature_count=split_feature_count,
        low_point_feature_count=len(low_point_features),
        sample_step_m=effective_step_m,
        tolerance_m=tolerance_m,
    )
    return output_geojson, low_points_geojson, summary


def convert_geojson_file_to_monotonic_segments(
    *,
    input_geojson_path: str | Path,
    dem_path: str | Path,
    output_geojson_path: str | Path,
    input_crs: str = DEFAULT_INPUT_CRS,
    sample_step_m: Optional[float] = None,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    channel_raster_path: Optional[str | Path] = None,
    topaz_id_raster_path: Optional[str | Path] = None,
    design_property_keys: Sequence[str] = DEFAULT_DESIGN_PROPERTY_KEYS,
    low_points_output_geojson_path: Optional[str | Path] = None,
    add_segment_metadata: bool = False,
) -> MonotonicConversionSummary:
    """Read an input roads GeoJSON file, split to monotonic segments, and write output GeoJSON."""

    input_path = Path(input_geojson_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input roads GeoJSON file not found: {input_path}")

    roads_geojson = json.loads(input_path.read_text(encoding="utf-8"))
    output_geojson, low_points_geojson, summary = _convert_geojson_to_monotonic_segments_internal(
        roads_geojson,
        dem_path=dem_path,
        input_crs=input_crs,
        sample_step_m=sample_step_m,
        tolerance_m=tolerance_m,
        channel_raster_path=channel_raster_path,
        topaz_id_raster_path=topaz_id_raster_path,
        design_property_keys=design_property_keys,
        add_segment_metadata=add_segment_metadata,
    )

    output_path = Path(output_geojson_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_geojson, indent=2), encoding="utf-8")

    if low_points_output_geojson_path is not None:
        low_points_output_path = Path(low_points_output_geojson_path)
        low_points_output_path.parent.mkdir(parents=True, exist_ok=True)
        low_points_output_path.write_text(json.dumps(low_points_geojson, indent=2), encoding="utf-8")

    return summary


def _default_low_points_output_path(output_geojson_path: str | Path) -> str:
    output_path = Path(output_geojson_path)
    if output_path.suffix.lower() == ".geojson":
        return str(output_path.with_suffix(".low_points.geojson"))
    return f"{output_path}.low_points.geojson"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert roads GeoJSON paths into monotonic-elevation road segments."
    )
    parser.add_argument("--input-geojson", required=True, help="Path to the source roads GeoJSON.")
    parser.add_argument("--dem", required=True, help="Path to DEM GeoTIFF used for elevation sampling.")
    parser.add_argument("--output-geojson", required=True, help="Path for the monotonic output GeoJSON.")
    parser.add_argument(
        "--input-crs",
        default=DEFAULT_INPUT_CRS,
        help=f"CRS of input road coordinates (default: {DEFAULT_INPUT_CRS}).",
    )
    parser.add_argument(
        "--sample-step-m",
        type=float,
        default=None,
        help="Sampling interval in meters (default: DEM pixel size).",
    )
    parser.add_argument(
        "--channel-raster",
        default=None,
        help=(
            "Optional channel-mask raster. If omitted, auto-detects "
            "`netful.tif` or `netful0.tif` next to the DEM."
        ),
    )
    parser.add_argument(
        "--topaz-id-raster",
        default=None,
        help="Optional topaz-id raster. If omitted, auto-detects `subwta.tif` next to the DEM.",
    )
    parser.add_argument(
        "--tolerance-m",
        type=float,
        default=DEFAULT_TOLERANCE_M,
        help=f"Elevation tolerance in meters for monotonic trend detection (default: {DEFAULT_TOLERANCE_M}).",
    )
    parser.add_argument(
        "--low-points-output-geojson",
        default=None,
        help="Optional explicit path for low-point feature GeoJSON output.",
    )
    parser.add_argument(
        "--no-low-points-output",
        action="store_true",
        help="Disable companion low-point feature GeoJSON output.",
    )
    parser.add_argument(
        "--add-segment-metadata",
        action="store_true",
        help="Append `_roads_*` segment metadata fields to output properties.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    low_points_output_path: Optional[str]
    if args.no_low_points_output:
        low_points_output_path = None
    elif args.low_points_output_geojson:
        low_points_output_path = str(args.low_points_output_geojson)
    else:
        low_points_output_path = _default_low_points_output_path(args.output_geojson)

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=args.input_geojson,
        dem_path=args.dem,
        output_geojson_path=args.output_geojson,
        input_crs=args.input_crs,
        sample_step_m=args.sample_step_m,
        tolerance_m=args.tolerance_m,
        channel_raster_path=args.channel_raster,
        topaz_id_raster_path=args.topaz_id_raster,
        low_points_output_geojson_path=low_points_output_path,
        add_segment_metadata=args.add_segment_metadata,
    )
    print(
        "Converted roads to monotonic segments: "
        f"input_features={summary.input_feature_count}, "
        f"output_features={summary.output_feature_count}, "
        f"split_features={summary.split_feature_count}, "
        f"low_point_features={summary.low_point_feature_count}, "
        f"sample_step_m={summary.sample_step_m:.3f}, "
        f"tolerance_m={summary.tolerance_m:.3f}, "
        f"low_points_output={low_points_output_path if low_points_output_path else 'disabled'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
