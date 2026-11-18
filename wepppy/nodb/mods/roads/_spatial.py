"""Roads spatial selection and terrain sampling using existing native/geospatial components."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple
import numpy as np
import rasterio
from pyproj import CRS, Geod, Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform, unary_union
from wepppy.nodb.mods.roads import _unrutted
from ._constants import OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS, _is_hillslope_topaz_id


def _extract_segment_coordinates(feature: Mapping[str, Any]) -> List[List[float]]:
    geometry = feature.get("geometry") if isinstance(feature, Mapping) else None
    if not isinstance(geometry, Mapping):
        raise ValueError("Road segment feature is missing geometry.")

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "LineString":
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ValueError("Road segment LineString must include at least two coordinates.")
        return coordinates

    if geometry_type == "MultiLineString":
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("Road segment MultiLineString must include at least one linestring.")
        candidates = [line for line in coordinates if isinstance(line, list) and len(line) >= 2]
        if not candidates:
            raise ValueError("Road segment MultiLineString has no valid linestring members.")
        candidates.sort(key=len, reverse=True)
        return candidates[0]

    raise ValueError(f"Unsupported segment geometry type for Roads WEPP run assembly: {geometry_type!r}")


def _line_length_m(coords: List[List[float]], transformer: Transformer, geod: Geod) -> float:
    lons: List[float] = []
    lats: List[float] = []
    for point in coords:
        x = float(point[0])
        y = float(point[1])
        lon, lat = transformer.transform(x, y)
        lons.append(lon)
        lats.append(lat)
    return float(geod.line_length(lons, lats))


def _load_hillslope_geometries_wgs84(self) -> List[Dict[str, Any]]:
    hillslope_geojson_path = self._normalize_existing_path(getattr(self.watershed_instance, "subwta_shp", None))
    if hillslope_geojson_path is None:
        raise FileNotFoundError("Roads outslope_unrutted replacement requires watershed subcatchments WGS GeoJSON.")

    payload = json.loads(Path(hillslope_geojson_path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("type") != "FeatureCollection":
        raise ValueError("Watershed subcatchments payload is malformed; expected FeatureCollection.")

    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Watershed subcatchments payload is missing a features array.")

    hillslopes: List[Dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        properties = feature.get("properties")
        geometry_payload = feature.get("geometry")
        if not isinstance(properties, Mapping) or not isinstance(geometry_payload, Mapping):
            continue

        topaz_id_hill = self._resolve_topaz_id_from_properties(properties)
        if topaz_id_hill is None or not _is_hillslope_topaz_id(topaz_id_hill):
            continue

        geometry = shape(geometry_payload)
        if geometry.is_empty:
            continue

        hillslopes.append(
            {
                "topaz_id_hill": int(topaz_id_hill),
                "geometry_wgs84": geometry,
            }
        )

    if not hillslopes:
        raise ValueError("No hillslope geometries were resolved from watershed subcatchments.")

    grouped = defaultdict(list)
    for row in hillslopes:
        grouped[row["topaz_id_hill"]].append(row["geometry_wgs84"])
    return [{"topaz_id_hill": key, "geometry_wgs84": unary_union(parts)}
            for key, parts in sorted(grouped.items())]


def _select_outslope_unrutted_hillslope_segments(
    self,
    *,
    pending_segments: Sequence[Dict[str, Any]],
    input_crs: CRS,
    geod: Geod,
    top2wepp: Mapping[int, Any],
) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
    params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
    sources = {}
    for pending in pending_segments:
        inputs = self._resolve_segment_run_inputs(
            properties=pending["properties"], params=params, segment_id=pending["segment_id"],
            design="outslope_unrutted", warning_counts=Counter(), warning_examples=[], warning_limit=0,
        )
        effective = {key: value for key, value in inputs.items() if key != "resolution_sources"}
        # Include required raw-invalid values: missing inputs must remain failures,
        # never get merged with a neighbor whose valid inputs would hide them.
        for key, aliases in OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS.items():
            raw = self._first_non_empty_property(pending["properties"], aliases)
            parsed = self._coerce_float(raw)
            effective[key] = parsed if parsed is not None and np.isfinite(parsed) else raw
        sources[str(pending["segment_id"])] = {
            **pending, "inputs": inputs,
            "signature": json.dumps(effective, sort_keys=True, allow_nan=False),
            "geometry": shapely_transform(input_to_wgs84.transform, shape(pending["feature"]["geometry"])),
        }
    selected_by_wepp = defaultdict(list)
    statuses = {}
    records = []
    for hillslope in self._load_hillslope_geometries_wgs84():
        topaz = int(hillslope["topaz_id_hill"])
        wepp_id = self._as_int_or_none(top2wepp.get(topaz))
        width = float(self.watershed_instance.hillslope_width(topaz))
        if not np.isfinite(width) or width <= 0:
            raise ValueError(f"Unrutted hillslope {topaz} width must be finite and positive.")
        rows = []
        for source, pending in sources.items():
            geometry = pending["geometry"].intersection(hillslope["geometry_wgs84"])
            parts = list(_unrutted.line_parts(geometry))
            if parts:
                rows.append({"geometry": unary_union(parts), "source": source,
                             "signature": pending["signature"]})
        if not rows:
            continue
        components = _unrutted.crossings(rows)
        membership = Counter(source for row in components for source in row["sources"])
        candidates = []
        record = {"topaz_id_hill": topaz, "wepp_id_hill": wepp_id,
                  "segment_ids_included": [], "segment_ids_excluded": [], "segment_ids_capped": [],
                  "inclusion_ratio_by_segment": {}, "top_ofe_compensation_m": 0.0,
                  "area_error_before_compensation_m2": 0.0, "area_error_after_compensation_m2": 0.0,
                  "geometry_policy": _unrutted.POLICY, "connectivity_limitation": _unrutted.LIMITATION,
                  "excluded_road_target_area_m2": 0.0, "excluded_road_area_unknown_count": 0,
                  "area_accounting_status": "unavailable", "area_accounting_reason": "not_executed",
                  **{key: None for key in ("reference_area_m2", "affected_area_m2", "remainder_area_m2",
                     "area_residual_m2", "road_target_area_m2", "road_modeled_area_m2", "road_area_deficit_m2", "strip_width_factor")}}
        for component in components:
            source = component["sources"][0]
            pending = sources[source]
            suffix = "::" + component["key"][:12] if membership[source] > 1 else ""
            identity = self._build_segment_hillslope_id(source + suffix, topaz)
            length = self._geometry_line_length_m_wgs84(component["geometry"], geod=geod)
            if not np.isfinite(length) or length <= 0:
                raise ValueError("Unrutted crossing length must be finite and positive.")
            candidate = {"segment_hillslope_id": identity, "source_segment_id": source,
                         "source_segment_ids": component["sources"], "geometry_key": component["key"],
                         "topaz_id_hill": topaz, "hillslope_wepp_id": wepp_id,
                         "overlap_length_m": length, "hillslope_width_m": width,
                         "inclusion_ratio": length / width, "overlap_geometry_wgs84": component["geometry"],
                         "feature": pending["feature"], "properties": pending["properties"],
                         "road_target_area_m2": length * pending["inputs"]["road_width_m"]}
            candidates.append(candidate)
            record["inclusion_ratio_by_segment"][identity] = length / width
        eligible = 0
        for candidate in sorted(candidates, key=lambda row: (-row["overlap_length_m"], row["geometry_key"])):
            identity = candidate["segment_hillslope_id"]
            status = "included"
            if candidate["overlap_length_m"] < 10.0:
                status = "excluded_overlap_length_min"
            elif wepp_id is None:
                raise ValueError(f"Unrutted hillslope {topaz} is missing its WEPP mapping.")
            elif eligible >= 3:
                status = "excluded_cap_limit"
            if status == "included":
                eligible += 1
                selected_by_wepp[wepp_id].append(candidate)
                record["segment_ids_included"].append(identity)
            else:
                record["segment_ids_excluded"].append(identity)
                record["excluded_road_target_area_m2"] += candidate["road_target_area_m2"]
                if status == "excluded_cap_limit":
                    record["segment_ids_capped"].append(identity)
            statuses[identity] = {**candidate, "status": status}
        records.append(record)
    counts = Counter(row["status"] for row in statuses.values())
    diagnostics = {"outslope_unrutted_targeted_hillslope_count": len(selected_by_wepp),
                   "outslope_unrutted_included_segment_count": counts["included"],
                   "outslope_unrutted_excluded_segment_count": counts["excluded_overlap_length_min"],
                   "outslope_unrutted_capped_segment_count": counts["excluded_cap_limit"],
                   "outslope_unrutted_hillslope_records": records}
    return dict(selected_by_wepp), diagnostics, statuses


def _sample_dem_elevation(
    dataset: rasterio.io.DatasetReader,
    transformer: Transformer,
    x: float,
    y: float,
) -> float:
    dx, dy = transformer.transform(float(x), float(y))
    sample = next(dataset.sample([(dx, dy)]))
    value = float(sample[0])
    if dataset.nodata is not None and abs(value - float(dataset.nodata)) < 1e-12:
        raise ValueError("Segment endpoint sampled nodata elevation from DEM.")
    return value


def _build_segment_profile(
    self,
    *,
    feature: Mapping[str, Any],
    input_crs: CRS,
    dem_dataset: rasterio.io.DatasetReader,
    input_to_wgs84: Transformer,
    input_to_dem: Transformer,
    geod: Geod,
) -> Dict[str, Any]:
    coords = self._extract_segment_coordinates(feature)
    segment_length_m = self._line_length_m(coords, input_to_wgs84, geod)
    if segment_length_m <= 0:
        raise ValueError("Segment geometry length is zero; cannot build Roads slope profile.")

    start = coords[0]
    end = coords[-1]
    start_elevation = self._sample_dem_elevation(dem_dataset, input_to_dem, start[0], start[1])
    end_elevation = self._sample_dem_elevation(dem_dataset, input_to_dem, end[0], end[1])

    if start_elevation >= end_elevation:
        high_point = start
        low_point = end
        elevation_high = start_elevation
        elevation_low = end_elevation
    else:
        high_point = end
        low_point = start
        elevation_high = end_elevation
        elevation_low = start_elevation

    raw_slope_pct = ((elevation_high - elevation_low) / segment_length_m) * 100.0
    clamped_slope_pct = self._clamp_percent_slope(raw_slope_pct)

    return {
        "segment_length_m": float(segment_length_m),
        "elevation_high_m": float(elevation_high),
        "elevation_low_m": float(elevation_low),
        "raw_slope_pct": float(raw_slope_pct),
        "slope_pct": float(clamped_slope_pct),
        "high_point": [float(high_point[0]), float(high_point[1])],
        "low_point": [float(low_point[0]), float(low_point[1])],
    }
