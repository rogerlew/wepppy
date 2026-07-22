#!/usr/bin/env python3
"""Evaluate masked-valid SSURGO donor proposals without changing a run."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
DEFAULT_NED1_VRT = Path("/wc1/geodata/ned1/2024/.vrt")
TERRAIN_WEIGHTS = (0.0, 0.1, 0.2, 0.3)
SHALLOW_MINERAL_MAX_ORGANIC_MATTER_PCT = 20.0
SHALLOW_MINERAL_MIN_VECTOR_FIELDS = 3
SHALLOW_MINERAL_VECTOR_RANGES = {
    "bd": (0.5, 3.0),
    "ksat": (0.0, 100_000.0),
    "fc": (0.0, 1.0),
    "wp": (0.0, 1.0),
    "cec": (0.0, 200.0),
    "rfg": (0.0, 100.0),
    "solthk": (1.0, 10_000.0),
}
PROFILE_EXCLUDED_FAILURE_CLASSES = frozenset({
    "no_components",
    "no_horizons",
    "nonphysical_texture_balance",
    "no_valid_horizons",
    "zero_wepp_layers",
})
PROFILE_SUPPORTED_FAILURE_CLASSES = frozenset({"partial_profile", "missing_required_attributes"})
UNSUPPORTED_FAILURE_CLASSES = frozenset({
    "residual_invalid_unclassified",
    "no_eligible_component",
    "urban",
    "water",
    "no_valid_donor",
})


def _numeric_distance(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[float | None, list[str]]:
    fields = sorted(set(reference) & set(candidate))
    deltas: list[float] = []
    used: list[str] = []
    for field in fields:
        try:
            left, right = float(reference[field]), float(candidate[field])
        except (TypeError, ValueError):
            continue
        if math.isfinite(left) and math.isfinite(right):
            deltas.append(abs(left - right))
            used.append(field)
    return (sum(deltas) / len(deltas), used) if deltas else (None, used)


def _finite_profile_fields(
    source_profile: Mapping[str, Any], candidate_profiles: Mapping[str, Mapping[str, Any]], failure_class: str
) -> list[str]:
    """Return directly observed profile fields permitted for one failure class."""
    if failure_class in PROFILE_EXCLUDED_FAILURE_CLASSES | UNSUPPORTED_FAILURE_CLASSES:
        return []
    if failure_class not in PROFILE_SUPPORTED_FAILURE_CLASSES:
        return []
    fields = set(source_profile)
    for profile in candidate_profiles.values():
        fields &= set(profile)
    allowed = []
    for field in sorted(fields):
        try:
            values = [float(source_profile[field]), *(float(profile[field]) for profile in candidate_profiles.values())]
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(value) for value in values):
            allowed.append(field)
    return allowed


def _profile_components(
    source_profile: Mapping[str, Any], candidate_profiles: Mapping[str, Mapping[str, Any]], fields: Sequence[str]
) -> tuple[dict[str, float | None], dict[str, dict[str, float]]]:
    """Return fixture-local robust profile similarity and the persisted scale evidence."""
    if not fields:
        return {mukey: None for mukey in candidate_profiles}, {}
    import numpy as np

    calibration: dict[str, dict[str, float]] = {}
    distances: dict[str, float] = {mukey: 0.0 for mukey in candidate_profiles}
    for field in fields:
        values = np.asarray(
            [float(source_profile[field]), *(float(profile[field]) for profile in candidate_profiles.values())], dtype=float
        )
        median = float(np.median(values))
        iqr = float(np.percentile(values, 75) - np.percentile(values, 25))
        mad = float(np.median(np.abs(values - median)))
        scale = max(iqr, 1.4826 * mad, 1.0)
        calibration[field] = {"median": median, "iqr": iqr, "mad": mad, "scale": scale}
        source_value = float(source_profile[field])
        for mukey, profile in candidate_profiles.items():
            distances[mukey] += abs(source_value - float(profile[field])) / scale
    mean_distances = {mukey: distance / len(fields) for mukey, distance in distances.items()}
    minimum = min(mean_distances.values())
    maximum = max(mean_distances.values())
    if maximum == minimum:
        return {mukey: 1.0 for mukey in candidate_profiles}, calibration
    return {
        mukey: 1.0 - (distance - minimum) / (maximum - minimum)
        for mukey, distance in mean_distances.items()
    }, calibration


def evaluate_masked_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one precomputed local-support case deterministically."""
    withheld = str(case["withheld_mukey"])
    global_mukey = str(case["global_mukey"])
    support = [(str(mukey), int(count)) for mukey, count in case["candidate_support"]]
    support.sort(key=lambda item: (-item[1], int(item[0])))
    local_mukey = support[0][0] if support else None
    summaries = case.get("soil_summaries", {})
    reference = summaries.get(withheld, {})
    local_distance, fields = _numeric_distance(reference, summaries.get(local_mukey, {})) if local_mukey else (None, [])
    global_distance, _ = _numeric_distance(reference, summaries.get(global_mukey, {}))
    candidate_ids = {mukey for mukey, _ in support}
    candidate_ids.update(str(candidate["mukey"]) for candidate in case.get("geometry_candidates", []))
    candidate_feature_distances = {
        mukey: _numeric_distance(reference, summaries.get(mukey, {}))[0]
        for mukey in sorted(candidate_ids, key=int)
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ssurgo_masked_valid_evaluation",
        "case_id": str(case["case_id"]),
        "withheld_mukey": withheld,
        "global_mukey": global_mukey,
        "local_majority_mukey": local_mukey,
        "candidate_support": support,
        "exact_local_recovery": local_mukey == withheld,
        "exact_global_recovery": global_mukey == withheld,
        "local_feature_distance": local_distance,
        "global_feature_distance": global_distance,
        "candidate_feature_distances": candidate_feature_distances,
        "candidate_count": len(candidate_ids),
        "failure_class": str(case.get("failure_class", "masked_valid_all_features")),
        "distance_fields": fields,
        "reason": "local_candidate" if local_mukey else "no_local_candidate",
    }
    for field in (
        "run_path",
        "topaz_id",
        "bounds_epsg5070",
        "search_radius_m",
        "exhausted",
        "pixels_read",
        "local_elevation_delta_m",
        "global_elevation_delta_m",
        "geometry_candidates",
        "candidate_ring_evidence",
        "shallow_mineral_source",
        "shallow_mineral_candidates",
    ):
        if field in case:
            result[field] = case[field]
    if "score_variants" in case:
        score_variants = {}
        for name, variant in case["score_variants"].items():
            selected_mukey = variant.get("selected_mukey")
            selected_distance, selected_fields = (
                _numeric_distance(reference, summaries.get(str(selected_mukey), {}))
                if selected_mukey is not None else (None, [])
            )
            score_variants[name] = {
                **variant,
                "selected_feature_distance": selected_distance,
                "selected_distance_fields": selected_fields,
            }
        result["score_variants"] = score_variants
    if "failure_class" in case and "geometry_candidates" in case:
        geometry = [
            (int(candidate["mukey"]), int(candidate["support_pixels"]), int(candidate["shared_edges"]))
            for candidate in case["geometry_candidates"]
        ]
        failure_aware = score_failure_aware_candidates(
            geometry,
            case.get("candidate_elevation_deltas", {}),
            failure_class=str(case["failure_class"]),
            source_profile=case.get("source_profile"),
            candidate_profiles=case.get("candidate_profiles"),
        )
        selected_mukey = failure_aware["selected_mukey"]
        selected_distance, selected_fields = (
            _numeric_distance(reference, summaries.get(str(selected_mukey), {}))
            if selected_mukey is not None else (None, [])
        )
        result["failure_aware_score"] = {
            **failure_aware,
            "selected_feature_distance": selected_distance,
            "selected_distance_fields": selected_fields,
        }
    return result


def _numeric_mukey(value: Any) -> str:
    """Return the numeric MUKEY portion of a generated-soil identifier."""
    return str(value).split("-", 1)[0]


def _finite_features(soil: Any) -> dict[str, float]:
    """Extract declared, comparable first-profile WEPP summary features."""
    util = soil.get_weppsoilutil()
    horizon = util.obj["ofes"][0]["horizons"][0]
    candidate_values = {
        "bulk_density_g_cm3": horizon.get("bd"),
        "clay_pct": horizon.get("clay"),
        "field_capacity": horizon.get("fc"),
        "organic_matter_pct": horizon.get("orgmat"),
        "rock_fragment_pct": horizon.get("rfg"),
        "sand_pct": horizon.get("sand"),
        "soil_depth_mm": util.soil_depth,
        "wilting_point": horizon.get("wp"),
    }
    features: dict[str, float] = {}
    for key, value in candidate_values.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            features[key] = numeric
    return features


def validated_shallow_mineral_horizon(horizons: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Return the shallowest non-organic WEPP horizon with validated nontexture fields."""
    for index, horizon in enumerate(horizons):
        try:
            organic_matter = float(horizon["orgmat"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(organic_matter) or not 0.0 <= organic_matter <= SHALLOW_MINERAL_MAX_ORGANIC_MATTER_PCT:
            continue
        values: dict[str, float] = {}
        rejected_fields: list[str] = []
        for field, (minimum, maximum) in SHALLOW_MINERAL_VECTOR_RANGES.items():
            try:
                value = float(horizon[field])
            except (KeyError, TypeError, ValueError):
                rejected_fields.append(field)
                continue
            if math.isfinite(value) and minimum <= value <= maximum:
                values[field] = value
            else:
                rejected_fields.append(field)
        if "fc" in values and "wp" in values and values["wp"] > values["fc"]:
            values.pop("fc")
            values.pop("wp")
            rejected_fields.extend(("fc", "wp"))
        if len(values) >= SHALLOW_MINERAL_MIN_VECTOR_FIELDS:
            return {
                "horizon_index": index,
                "organic_matter_pct": organic_matter,
                "validated_fields": values,
                "rejected_fields": sorted(set(rejected_fields)),
            }
    return None


def _shallow_mineral_horizon(soil: Any) -> dict[str, Any] | None:
    return validated_shallow_mineral_horizon(soil.get_weppsoilutil().obj["ofes"][0]["horizons"])


def score_shallow_mineral_vectors(
    source: Mapping[str, Any] | None,
    candidates: Mapping[str, Mapping[str, Any]],
    geometry: Sequence[tuple[int, int, int]],
    elevation_deltas: Mapping[str, float | None],
    *,
    source_evidence_class: str,
) -> dict[str, Any]:
    """Rank permitted candidates by validated shallow-mineral vector similarity."""
    if source_evidence_class not in {"masked_valid_simulation", *PROFILE_SUPPORTED_FAILURE_CLASSES}:
        return {"selected_mukey": None, "reason": "profile_evidence_not_permitted", "candidates": []}
    if source is None:
        return {"selected_mukey": None, "reason": "no_validated_shallow_mineral_source", "candidates": []}
    source_values = source["validated_fields"]
    geometry_by_mukey = {str(mukey): (support, shared_edges) for mukey, support, shared_edges in geometry}
    eligible: dict[str, tuple[Mapping[str, Any], list[str]]] = {}
    for mukey, candidate in candidates.items():
        fields = sorted(set(source_values) & set(candidate["validated_fields"]))
        if len(fields) >= SHALLOW_MINERAL_MIN_VECTOR_FIELDS and mukey in geometry_by_mukey:
            eligible[mukey] = (candidate, fields)
    if not eligible:
        return {"selected_mukey": None, "reason": "insufficient_validated_shallow_mineral_vectors", "candidates": []}
    field_scales: dict[str, float] = {}
    for field in sorted({field for _, fields in eligible.values() for field in fields}):
        values = [float(source_values[field])]
        values.extend(float(candidate["validated_fields"][field]) for candidate, fields in eligible.values() if field in fields)
        median = statistics.median(values)
        mad = statistics.median(abs(value - median) for value in values)
        field_scales[field] = max(1.4826 * mad, abs(median) * 0.05, 1.0e-6)
    scored = []
    for mukey, (candidate, fields) in eligible.items():
        vector_distance = sum(
            abs(float(source_values[field]) - float(candidate["validated_fields"][field])) / field_scales[field]
            for field in fields
        ) / len(fields)
        support, shared_edges = geometry_by_mukey[mukey]
        elevation_delta = elevation_deltas.get(mukey)
        scored.append({
            "mukey": mukey,
            "score": -vector_distance,
            "vector_distance": vector_distance,
            "vector_fields": fields,
            "candidate_horizon_index": candidate["horizon_index"],
            "support_pixels": support,
            "shared_edges": shared_edges,
            "elevation_delta_m": elevation_delta,
        })
    scored.sort(key=lambda candidate: (
        candidate["vector_distance"], -candidate["shared_edges"],
        candidate["elevation_delta_m"] is None, candidate["elevation_delta_m"] if candidate["elevation_delta_m"] is not None else math.inf,
        int(candidate["mukey"]),
    ))
    return {
        "selected_mukey": scored[0]["mukey"],
        "reason": "validated_shallow_mineral_vector",
        "source_horizon_index": source["horizon_index"],
        "source_validated_fields": sorted(source_values),
        "field_scales": field_scales,
        "candidates": scored,
    }


def _global_baseline(
    raw_domsoil_d: Mapping[str, str], valid_mukeys: set[str], valid_order: Sequence[str], withheld_mukey: str
) -> str | None:
    """Reproduce the current global fallback after a masked MUKEY is removed."""
    remaining = valid_mukeys - {withheld_mukey}
    if not remaining:
        return None
    counts = Counter(
        _numeric_mukey(mukey)
        for mukey in raw_domsoil_d.values()
        if _numeric_mukey(mukey) in remaining
    )
    if counts:
        return min(counts, key=lambda mukey: (-counts[mukey], int(mukey)))
    return next((mukey for mukey in valid_order if mukey in remaining), None)


def _restrict_eligible_case_ids(
    eligible: Sequence[tuple[str, str]], run_name: str, requested_case_ids: set[str] | None
) -> list[tuple[str, str]]:
    """Select a fixed masked-valid subset without changing its donor baseline."""
    if not requested_case_ids:
        return list(eligible)
    return [
        (topaz_id, mukey)
        for topaz_id, mukey in eligible
        if f"{run_name}:{topaz_id}" in requested_case_ids
    ]


def _median(values: Any) -> float | None:
    import numpy as np

    finite = values[np.isfinite(values)]
    return float(np.median(finite)) if finite.size else None


def _read_aligned_dem(ssurgo_path: Path, dem_path: Path) -> tuple[Any, dict[str, Any]]:
    """Read a DEM onto the SSURGO grid, warping only when alignment requires it."""
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    with rasterio.open(ssurgo_path) as ssurgo, rasterio.open(dem_path) as dem:
        aligned = (
            dem.crs == ssurgo.crs
            and dem.transform == ssurgo.transform
            and dem.shape == ssurgo.shape
        )
        if aligned:
            values = dem.read(1).astype(float)
            if dem.nodata is not None:
                values[values == dem.nodata] = math.nan
            return values, {
                "dem_path": str(dem_path),
                "dem_resampling": "native_aligned",
                "dem_crs": str(dem.crs),
            }
        with WarpedVRT(
            dem,
            crs=ssurgo.crs,
            transform=ssurgo.transform,
            width=ssurgo.width,
            height=ssurgo.height,
            resampling=Resampling.bilinear,
            src_nodata=dem.nodata,
            nodata=np.nan,
            dtype="float32",
        ) as warped:
            return warped.read(1).astype(float), {
                "dem_path": str(dem_path),
                "dem_resampling": "bilinear_to_ssurgo_grid",
                "dem_crs": str(dem.crs),
            }


def _candidate_elevation_deltas(
    mukeys: Any,
    elevation: Any,
    transform: Any,
    *,
    source_mukey: str,
    bounds: tuple[float, float, float, float],
    search_radius_m: float | None,
    candidates: Sequence[int],
) -> dict[str, float | None]:
    """Compare source-MUKEY and candidate elevations using cropped map windows."""
    from rasterio.windows import Window, from_bounds

    min_x, min_y, max_x, max_y = bounds
    source_window = from_bounds(min_x, min_y, max_x, max_y, transform=transform).round_offsets().round_lengths()
    full = Window(0, 0, mukeys.shape[1], mukeys.shape[0])
    try:
        source_window = source_window.intersection(full)
    except ValueError:
        return {str(candidate): None for candidate in candidates}
    row_start, col_start = int(source_window.row_off), int(source_window.col_off)
    row_stop, col_stop = row_start + int(source_window.height), col_start + int(source_window.width)
    source_median = _median(
        elevation[row_start:row_stop, col_start:col_stop][
            mukeys[row_start:row_stop, col_start:col_stop] == int(source_mukey)
        ]
    )
    if source_median is None or search_radius_m is None:
        return {str(candidate): None for candidate in candidates}
    window = from_bounds(
        min_x - search_radius_m,
        min_y - search_radius_m,
        max_x + search_radius_m,
        max_y + search_radius_m,
        transform=transform,
    ).round_offsets().round_lengths()
    try:
        window = window.intersection(full)
    except ValueError:
        return {str(candidate): None for candidate in candidates}
    row_start, col_start = int(window.row_off), int(window.col_off)
    row_stop, col_stop = row_start + int(window.height), col_start + int(window.width)
    local_mukeys = mukeys[row_start:row_stop, col_start:col_stop]
    local_elevation = elevation[row_start:row_stop, col_start:col_stop]
    return {
        str(candidate): (
            abs(source_median - candidate_median)
            if (candidate_median := _median(local_elevation[local_mukeys == candidate])) is not None
            else None
        )
        for candidate in candidates
    }


def _source_elevation_median(
    mukeys: Any, elevation: Any, transform: Any, *, source_mukey: str, bounds: tuple[float, float, float, float]
) -> float | None:
    """Return the source-MUKEY elevation median inside its source-local bounds."""
    from rasterio.windows import Window, from_bounds

    min_x, min_y, max_x, max_y = bounds
    window = from_bounds(min_x, min_y, max_x, max_y, transform=transform).round_offsets().round_lengths()
    try:
        window = window.intersection(Window(0, 0, mukeys.shape[1], mukeys.shape[0]))
    except ValueError:
        return None
    row_start, col_start = int(window.row_off), int(window.col_off)
    row_stop, col_stop = row_start + int(window.height), col_start + int(window.width)
    return _median(
        elevation[row_start:row_stop, col_start:col_stop][
            mukeys[row_start:row_stop, col_start:col_stop] == int(source_mukey)
        ]
    )


def score_geometry_terrain_candidates(
    candidates: Sequence[tuple[int, int, int]], elevation_deltas: Mapping[str, float | None]
) -> dict[str, dict[str, Any]]:
    """Score bounded local candidates across research terrain-weight variants."""
    edge_total = sum(shared_edges for _, _, shared_edges in candidates)
    support_total = sum(support for _, support, _ in candidates)
    geometry_denominator = edge_total if edge_total else support_total
    finite_deltas = [delta for delta in elevation_deltas.values() if delta is not None]
    minimum_delta = min(finite_deltas) if finite_deltas else None
    maximum_delta = max(finite_deltas) if finite_deltas else None
    variants: dict[str, dict[str, Any]] = {}
    for terrain_weight in TERRAIN_WEIGHTS:
        scored = []
        for mukey, support, shared_edges in candidates:
            geometry = (shared_edges if edge_total else support) / geometry_denominator if geometry_denominator else 0.0
            elevation_delta = elevation_deltas.get(str(mukey))
            if elevation_delta is None or minimum_delta is None or maximum_delta is None:
                terrain = None
            elif maximum_delta == minimum_delta:
                terrain = 1.0
            else:
                terrain = 1.0 - (elevation_delta - minimum_delta) / (maximum_delta - minimum_delta)
            if terrain is None:
                score = geometry
            else:
                score = (1.0 - terrain_weight) * geometry + terrain_weight * terrain
            scored.append(
                {
                    "mukey": str(mukey),
                    "score": score,
                    "geometry_component": geometry,
                    "terrain_component": terrain,
                    "support_pixels": support,
                    "shared_edges": shared_edges,
                    "elevation_delta_m": elevation_delta,
                }
            )
        scored.sort(key=lambda candidate: (-candidate["score"], int(candidate["mukey"])))
        variants[f"terrain_{int(terrain_weight * 100):02d}pct"] = {
            "terrain_weight": terrain_weight,
            "selected_mukey": scored[0]["mukey"] if scored else None,
            "candidates": scored,
            "geometry_basis": "shared_edges" if edge_total else "support_pixels",
        }
    return variants


def derive_candidate_ring_evidence(
    geometry_by_radius: Mapping[float, Sequence[tuple[int, int, int]]],
) -> list[dict[str, Any]]:
    """Describe first bounded-window appearance using support set differences."""
    prior_support: dict[int, int] = {}
    evidence: dict[int, dict[str, Any]] = {}
    for radius_m in sorted(geometry_by_radius):
        current = {
            int(mukey): (int(support_pixels), int(shared_edges))
            for mukey, support_pixels, shared_edges in geometry_by_radius[radius_m]
        }
        for mukey, (support_pixels, shared_edges) in current.items():
            if mukey not in evidence:
                evidence[mukey] = {
                    "mukey": str(mukey),
                    "first_radius_m": radius_m,
                    "first_ring_support_pixels": support_pixels - prior_support.get(mukey, 0),
                    "support_pixels": support_pixels,
                    "shared_edges": shared_edges,
                }
            elif radius_m == max(geometry_by_radius):
                evidence[mukey]["support_pixels"] = support_pixels
                evidence[mukey]["shared_edges"] = shared_edges
        prior_support = {mukey: support_pixels for mukey, (support_pixels, _) in current.items()}
    return [evidence[mukey] for mukey in sorted(evidence)]


def score_ring_candidates(
    candidates: Sequence[Mapping[str, Any]], elevation_deltas: Mapping[str, float | None]
) -> dict[str, dict[str, Any]]:
    """Rank a fixed wider candidate set by ring, then support and terrain ties."""
    def elevation_key(candidate: Mapping[str, Any]) -> tuple[bool, float]:
        value = elevation_deltas.get(str(candidate["mukey"]))
        return (value is None, float(value) if value is not None else math.inf)

    def ordered(name: str, key: Any) -> dict[str, Any]:
        ranked = sorted(candidates, key=key)
        return {
            "selection_basis": name,
            "selected_mukey": str(ranked[0]["mukey"]) if ranked else None,
            "candidates": [
                {
                    **candidate,
                    "elevation_delta_m": elevation_deltas.get(str(candidate["mukey"])),
                }
                for candidate in ranked
            ],
        }

    return {
        "ring_only": ordered("first_radius_m", lambda candidate: (candidate["first_radius_m"], int(candidate["mukey"]))),
        "ring_support": ordered(
            "first_radius_m_then_first_ring_support",
            lambda candidate: (
                candidate["first_radius_m"],
                -int(candidate["first_ring_support_pixels"]),
                int(candidate["mukey"]),
            ),
        ),
        "ring_support_terrain": ordered(
            "first_radius_m_then_first_ring_support_then_elevation",
            lambda candidate: (
                candidate["first_radius_m"],
                -int(candidate["first_ring_support_pixels"]),
                elevation_key(candidate),
                int(candidate["mukey"]),
            ),
        ),
    }


def score_failure_aware_candidates(
    candidates: Sequence[tuple[int, int, int]],
    elevation_deltas: Mapping[str, float | None],
    *,
    failure_class: str,
    source_profile: Mapping[str, Any] | None = None,
    candidate_profiles: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return one transparent research heuristic subject to failure-class gates.

    This function is deliberately independent of hillslope topology. It accepts
    only source-region map evidence, aligned terrain deltas, and the raw fields
    explicitly declared as retained for a simulated partial-profile failure.
    Its weights are fixture-research hypotheses, not production parameters.
    """
    source_profile = source_profile or {}
    candidate_profiles = candidate_profiles or {}
    if failure_class in UNSUPPORTED_FAILURE_CLASSES:
        return {
            "failure_class": failure_class,
            "selected_mukey": None,
            "reason": "unsupported_failure_class_global_fallback",
            "profile_fields": [],
            "candidates": [],
        }
    if not candidates:
        return {
            "failure_class": failure_class,
            "selected_mukey": None,
            "reason": "no_local_candidate_global_fallback",
            "profile_fields": [],
            "candidates": [],
        }

    candidate_ids = [str(mukey) for mukey, _, _ in candidates]
    scoped_profiles = {mukey: candidate_profiles[mukey] for mukey in candidate_ids if mukey in candidate_profiles}
    profile_fields = _finite_profile_fields(source_profile, scoped_profiles, failure_class)
    if len(scoped_profiles) != len(candidate_ids):
        profile_fields = []
    profile_components, profile_calibration = _profile_components(source_profile, scoped_profiles, profile_fields)

    edge_total = sum(shared_edges for _, _, shared_edges in candidates)
    support_total = sum(support for _, support, _ in candidates)
    geometry_denominator = edge_total if edge_total else support_total
    finite_terrain = [
        float(delta)
        for mukey, delta in elevation_deltas.items()
        if mukey in candidate_ids and delta is not None and math.isfinite(float(delta))
    ]
    terrain_minimum = min(finite_terrain) if finite_terrain else None
    terrain_maximum = max(finite_terrain) if finite_terrain else None
    terrain_available = terrain_minimum is not None and terrain_maximum is not None

    if profile_fields:
        weights = {"profile": 0.55, "geometry": 0.30, "terrain": 0.15 if terrain_available else 0.0}
        if not terrain_available:
            weights["geometry"] = 0.45
    elif terrain_available:
        weights = {"profile": 0.0, "geometry": 0.70, "terrain": 0.30}
    else:
        weights = {"profile": 0.0, "geometry": 1.0, "terrain": 0.0}

    scored = []
    for mukey, support, shared_edges in candidates:
        mukey_id = str(mukey)
        geometry = (shared_edges if edge_total else support) / geometry_denominator if geometry_denominator else 0.0
        elevation_delta = elevation_deltas.get(mukey_id)
        if elevation_delta is not None and not math.isfinite(float(elevation_delta)):
            elevation_delta = None
        if elevation_delta is None or not terrain_available:
            terrain = None
        elif terrain_maximum == terrain_minimum:
            terrain = 1.0
        else:
            terrain = 1.0 - (elevation_delta - terrain_minimum) / (terrain_maximum - terrain_minimum)
        profile = profile_components.get(mukey_id)
        score = weights["geometry"] * geometry
        if profile is not None:
            score += weights["profile"] * profile
        if terrain is not None:
            score += weights["terrain"] * terrain
        scored.append(
            {
                "mukey": mukey_id,
                "score": score,
                "geometry_component": geometry,
                "terrain_component": terrain,
                "profile_component": profile,
                "support_pixels": support,
                "shared_edges": shared_edges,
                "elevation_delta_m": elevation_delta,
            }
        )
    scored.sort(key=lambda candidate: (-candidate["score"], int(candidate["mukey"])))
    return {
        "failure_class": failure_class,
        "selected_mukey": scored[0]["mukey"],
        "reason": "failure_aware_local_candidate",
        "geometry_basis": "shared_edges" if edge_total else "support_pixels",
        "profile_fields": profile_fields,
        "profile_calibration": profile_calibration,
        "weights": weights,
        "candidates": scored,
    }


def summarize_evaluations(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return transparent, per-run paired comparison counts for an M3 cohort."""
    def summarize(group: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        comparable = [
            row for row in group
            if row["local_feature_distance"] is not None and row["global_feature_distance"] is not None
        ]
        elevation_comparable = [
            row for row in group
            if row.get("local_elevation_delta_m") is not None and row.get("global_elevation_delta_m") is not None
        ]
        return {
            "cases": len(group),
            "local_available": sum(row["local_majority_mukey"] is not None for row in group),
            "proposal_disagreements": sum(
                row["local_majority_mukey"] != row["global_mukey"]
                for row in group if row["local_majority_mukey"] is not None
            ),
            "feature_comparable": len(comparable),
            "feature_local_better": sum(
                row["local_feature_distance"] < row["global_feature_distance"] for row in comparable
            ),
            "feature_global_better": sum(
                row["global_feature_distance"] < row["local_feature_distance"] for row in comparable
            ),
            "feature_tied": sum(
                row["local_feature_distance"] == row["global_feature_distance"] for row in comparable
            ),
            "elevation_comparable": len(elevation_comparable),
            "elevation_local_better": sum(
                row["local_elevation_delta_m"] < row["global_elevation_delta_m"]
                for row in elevation_comparable
            ),
            "elevation_global_better": sum(
                row["global_elevation_delta_m"] < row["local_elevation_delta_m"]
                for row in elevation_comparable
            ),
            "elevation_tied": sum(
                row["local_elevation_delta_m"] == row["global_elevation_delta_m"]
                for row in elevation_comparable
            ),
        }

    by_run = {}
    for run_path in sorted({str(row.get("run_path", "input")) for row in results}):
        by_run[run_path] = summarize([row for row in results if str(row.get("run_path", "input")) == run_path])
    return {"all_runs": summarize(results), "by_run": by_run}


def summarize_score_variants(results: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """Compare every research score variant with the same global baseline."""
    names = sorted({name for row in results for name in row.get("score_variants", {})})
    summary = {}
    for name in names:
        comparable = [
            row for row in results
            if (variant := row.get("score_variants", {}).get(name)) is not None
            and variant["selected_feature_distance"] is not None
            and row["global_feature_distance"] is not None
        ]
        summary[name] = {
            "comparable": len(comparable),
            "local_better": sum(
                row["score_variants"][name]["selected_feature_distance"] < row["global_feature_distance"]
                for row in comparable
            ),
            "global_better": sum(
                row["global_feature_distance"] < row["score_variants"][name]["selected_feature_distance"]
                for row in comparable
            ),
            "tied": sum(
                row["score_variants"][name]["selected_feature_distance"] == row["global_feature_distance"]
                for row in comparable
            ),
        }
    return summary


def _candidate_count_bucket(count: int) -> str:
    if count == 0:
        return "0"
    if count == 1:
        return "1"
    if count <= 3:
        return "2-3"
    return "4+"


def _candidate_study_group(results: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Separate local candidate-set coverage from the ranking outcome."""
    variant_names = sorted({name for row in results for name in row.get("score_variants", {})})
    summary: dict[str, dict[str, Any]] = {}
    for name in variant_names:
        comparable = []
        for row in results:
            variant = row.get("score_variants", {}).get(name)
            global_distance = row.get("global_feature_distance")
            distances = row.get("candidate_feature_distances", {})
            if variant is None or global_distance is None or not distances:
                continue
            ranked = [str(candidate["mukey"]) for candidate in variant.get("candidates", [])]
            local_distances = {
                mukey: distance for mukey, distance in distances.items()
                if distance is not None and math.isfinite(float(distance))
            }
            if not ranked or not local_distances:
                continue
            comparable.append((row, variant, float(global_distance), local_distances, ranked))

        def outcome(distance: float, global_distance: float) -> str:
            if distance < global_distance:
                return "local_better"
            if global_distance < distance:
                return "global_better"
            return "tied"

        counts = Counter()
        candidate_counts: list[int] = []
        margins: list[float] = []
        for row, variant, global_distance, local_distances, ranked in comparable:
            candidate_counts.append(len(ranked))
            counts[f"oracle_{outcome(min(local_distances.values()), global_distance)}"] += 1
            counts["global_in_local_candidate_set"] += int(str(row["global_mukey"]) in local_distances)
            for top_k in (1, 2, 3):
                top_distances = [local_distances[mukey] for mukey in ranked[:top_k] if mukey in local_distances]
                if top_distances:
                    counts[f"top_{top_k}_{outcome(min(top_distances), global_distance)}"] += 1
            scores = [float(candidate["score"]) for candidate in variant.get("candidates", []) if "score" in candidate]
            if len(scores) == len(ranked) and len(scores) > 1:
                margins.append(scores[0] - scores[1])
        summary[name] = {
            "comparable": len(comparable),
            "median_candidate_count": statistics.median(candidate_counts) if candidate_counts else None,
            "global_in_local_candidate_set": counts["global_in_local_candidate_set"],
            "oracle_local_better": counts["oracle_local_better"],
            "oracle_global_better": counts["oracle_global_better"],
            "oracle_tied": counts["oracle_tied"],
            "median_score_margin": statistics.median(margins) if margins else None,
            "zero_score_margin": sum(margin == 0.0 for margin in margins),
            **{
                f"top_{top_k}_{outcome_name}": counts[f"top_{top_k}_{outcome_name}"]
                for top_k in (1, 2, 3)
                for outcome_name in ("local_better", "global_better", "tied")
            },
        }
    return summary


def summarize_candidate_study(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Stratify candidate-set coverage and ranking evidence without selecting policy."""
    groupings = {
        "by_run": lambda row: str(row.get("run_path", "input")),
        "by_candidate_count": lambda row: _candidate_count_bucket(int(row.get("candidate_count", 0))),
        "by_global_local_candidate": lambda row: str(
            str(row.get("global_mukey")) in row.get("candidate_feature_distances", {})
        ).lower(),
        "by_failure_class": lambda row: str(row.get("failure_class", "masked_valid_all_features")),
    }
    return {
        "all_runs": _candidate_study_group(results),
        **{
            name: {
                value: _candidate_study_group([row for row in results if key(row) == value])
                for value in sorted({key(row) for row in results})
            }
            for name, key in groupings.items()
        },
    }


def build_run_cases(
    run_path: Path,
    *,
    max_cases: int,
    seed: int,
    initial_radius_m: float,
    max_radius_m: float,
    workers: int | None,
    dem_path: Path,
    requested_case_ids: set[str] | None = None,
    candidate_ring_m: Sequence[float] | None = None,
    shallow_mineral_vector: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build read-only masked-valid cases from one completed gridded SSURGO run."""
    import rasterio

    from wepppy.nodb.core.soils import Soils
    from wepppyo3.raster_characteristics import local_mukey_geometry

    soils = Soils.getInstance(str(run_path))
    raw_domsoil_d = soils.raw_ssurgo_domsoil_d or {}
    if not raw_domsoil_d:
        raise ValueError(f"run has no raw SSURGO dominant-soil map: {run_path}")
    soil_by_mukey = {
        _numeric_mukey(mukey): soil
        for mukey, soil in (soils.soils or {}).items()
        if _numeric_mukey(mukey).isdigit()
    }
    valid_order = list(soil_by_mukey)
    valid_mukeys = set(valid_order)
    eligible = [
        (str(topaz_id), _numeric_mukey(mukey))
        for topaz_id, mukey in raw_domsoil_d.items()
        if _numeric_mukey(mukey) in valid_mukeys and len(valid_mukeys - {_numeric_mukey(mukey)}) > 0
    ]
    eligible.sort(key=lambda item: int(item[0]))
    eligible = _restrict_eligible_case_ids(eligible, run_path.name, requested_case_ids)
    if max_cases <= 0:
        raise ValueError("max_cases must be positive")
    if len(eligible) > max_cases:
        eligible = sorted(random.Random(seed).sample(eligible, max_cases), key=lambda item: int(item[0]))

    subwta_path = run_path / "dem" / "wbt" / "subwta.tif"
    ssurgo_path = run_path / "soils" / "ssurgo.tif"
    with rasterio.open(subwta_path) as subwta:
        labels = subwta.read(1)
        bounds_by_topaz: dict[str, tuple[float, float, float, float]] = {}
        for topaz_id, _ in eligible:
            rows, cols = (labels == int(topaz_id)).nonzero()
            if rows.size == 0:
                continue
            window = rasterio.windows.Window(
                cols.min(), rows.min(), cols.max() - cols.min() + 1, rows.max() - rows.min() + 1
            )
            bounds_by_topaz[topaz_id] = rasterio.windows.bounds(window, subwta.transform)

    with rasterio.open(ssurgo_path) as ssurgo:
        mukey_grid = ssurgo.read(1)
        ssurgo_transform = ssurgo.transform
    elevation_grid, dem_metadata = _read_aligned_dem(ssurgo_path, dem_path)
    global_elevation_medians = {
        mukey: _median(elevation_grid[mukey_grid == int(mukey)]) for mukey in valid_mukeys
    }

    selected = [(topaz_id, mukey) for topaz_id, mukey in eligible if topaz_id in bounds_by_topaz]
    clusters = [(topaz_id, int(mukey), bounds_by_topaz[topaz_id]) for topaz_id, mukey in selected]
    cases: list[dict[str, Any]] = []
    for withheld_mukey in sorted({mukey for _, mukey in selected}, key=int):
        masked_valid = {int(mukey) for mukey in valid_mukeys - {withheld_mukey}}
        matching = [(topaz_id, mukey) for topaz_id, mukey in selected if mukey == withheld_mukey]
        matching_sources = [cluster for cluster in clusters if cluster[0] in {topaz_id for topaz_id, _ in matching}]
        if candidate_ring_m:
            results_by_radius = {
                radius_m: local_mukey_geometry(
                    raster_path=str(ssurgo_path),
                    sources=matching_sources,
                    valid_mukeys=masked_valid,
                    initial_radius_m=radius_m,
                    max_radius_m=radius_m,
                    workers=workers,
                )
                for radius_m in candidate_ring_m
            }
            results = results_by_radius[max(candidate_ring_m)]
        else:
            results = local_mukey_geometry(
                raster_path=str(ssurgo_path),
                sources=matching_sources,
                valid_mukeys=masked_valid,
                initial_radius_m=initial_radius_m,
                max_radius_m=max_radius_m,
                workers=workers,
            )
        global_mukey = _global_baseline(raw_domsoil_d, valid_mukeys, valid_order, withheld_mukey)
        if global_mukey is None:
            continue
        for topaz_id, _ in matching:
            _, radius_m, geometry, exhausted, pixels_read = results[topaz_id]
            geometry_by_radius = (
                {candidate_radius: results_by_radius[candidate_radius][topaz_id][2] for candidate_radius in candidate_ring_m}
                if candidate_ring_m else None
            )
            candidate_ring_evidence = derive_candidate_ring_evidence(geometry_by_radius) if geometry_by_radius else None
            support = [(mukey, support_pixels) for mukey, support_pixels, _ in geometry]
            local_mukey = _numeric_mukey(sorted(support, key=lambda item: (-item[1], item[0]))[0][0]) if support else None
            candidate_elevation_deltas = _candidate_elevation_deltas(
                mukey_grid,
                elevation_grid,
                ssurgo_transform,
                source_mukey=withheld_mukey,
                bounds=bounds_by_topaz[topaz_id],
                search_radius_m=radius_m,
                candidates=[mukey for mukey, _, _ in geometry],
            )
            local_elevation_delta_m = candidate_elevation_deltas.get(local_mukey) if local_mukey else None
            source_elevation_median = _source_elevation_median(
                mukey_grid,
                elevation_grid,
                ssurgo_transform,
                source_mukey=withheld_mukey,
                bounds=bounds_by_topaz[topaz_id],
            )
            global_elevation_median = global_elevation_medians.get(global_mukey)
            global_elevation_delta_m = (
                abs(source_elevation_median - global_elevation_median)
                if source_elevation_median is not None and global_elevation_median is not None
                else None
            )
            score_variants = score_geometry_terrain_candidates(geometry, candidate_elevation_deltas)
            if candidate_ring_evidence:
                score_variants.update(score_ring_candidates(candidate_ring_evidence, candidate_elevation_deltas))
            summary_mukeys = {withheld_mukey, global_mukey, *(str(mukey) for mukey, _, _ in geometry)}
            shallow_mineral_source = _shallow_mineral_horizon(soil_by_mukey[withheld_mukey]) if shallow_mineral_vector else None
            shallow_mineral_candidates = {
                mukey: horizon
                for mukey in summary_mukeys
                if mukey != withheld_mukey and mukey in soil_by_mukey
                if (horizon := _shallow_mineral_horizon(soil_by_mukey[mukey])) is not None
            } if shallow_mineral_vector else {}
            if shallow_mineral_vector:
                score_variants["shallow_mineral_vector"] = score_shallow_mineral_vectors(
                    shallow_mineral_source,
                    shallow_mineral_candidates,
                    geometry,
                    candidate_elevation_deltas,
                    source_evidence_class="masked_valid_simulation",
                )
            cases.append(
                {
                    "case_id": f"{run_path.name}:{topaz_id}",
                    "run_path": str(run_path),
                    "topaz_id": topaz_id,
                    "withheld_mukey": withheld_mukey,
                    "global_mukey": global_mukey,
                    "candidate_support": support,
                    "soil_summaries": {
                        mukey: _finite_features(soil_by_mukey[mukey])
                        for mukey in summary_mukeys
                        if mukey in soil_by_mukey
                    },
                    "bounds_epsg5070": list(bounds_by_topaz[topaz_id]),
                    "search_radius_m": radius_m,
                    "exhausted": bool(exhausted),
                    "pixels_read": pixels_read,
                    "local_elevation_delta_m": local_elevation_delta_m,
                    "global_elevation_delta_m": global_elevation_delta_m,
                    "geometry_candidates": [
                        {"mukey": str(mukey), "support_pixels": support_pixels, "shared_edges": shared_edges}
                        for mukey, support_pixels, shared_edges in geometry
                    ],
                    **({"candidate_ring_evidence": candidate_ring_evidence} if candidate_ring_evidence else {}),
                    **({"shallow_mineral_source": shallow_mineral_source} if shallow_mineral_source else {}),
                    **({"shallow_mineral_candidates": shallow_mineral_candidates} if shallow_mineral_candidates else {}),
                    "score_variants": score_variants,
                }
            )
    metadata = {
        "run_path": str(run_path),
        "eligible_hillslopes": len(eligible),
        "evaluated_hillslopes": len(cases),
        "seed": seed,
        "initial_radius_m": initial_radius_m,
        "max_radius_m": max_radius_m,
        "requested_case_count": len(requested_case_ids) if requested_case_ids else None,
        "candidate_rings_m": list(candidate_ring_m) if candidate_ring_m else None,
        "shallow_mineral_vector": shallow_mineral_vector,
        **dem_metadata,
    }
    return cases, metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--run", action="append", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-cases", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--initial-radius-m", type=float, default=250.0)
    parser.add_argument("--max-radius-m", type=float, default=2000.0)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--dem-vrt", type=Path, default=DEFAULT_NED1_VRT)
    parser.add_argument(
        "--candidate-ring-m",
        action="append",
        type=float,
        help="Force and compare bounded candidate windows; repeat in ascending order and end at --max-radius-m.",
    )
    parser.add_argument(
        "--shallow-mineral-vector",
        action="store_true",
        help="Evaluate validated shallow-mineral vector matching in masked-valid run mode.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="Restrict run mode to a stable '<run-name>:<topaz-id>' masked-valid case; repeatable.",
    )
    args = parser.parse_args(argv)
    if args.input is not None:
        if args.case_id or args.candidate_ring_m or args.shallow_mineral_vector:
            parser.error("--case-id, --candidate-ring-m, and --shallow-mineral-vector are only available with --run")
        cases = json.loads(args.input.read_text(encoding="utf-8"))
        results: Any = [evaluate_masked_case(case) for case in cases]
    else:
        candidate_ring_m = None
        if args.candidate_ring_m:
            candidate_ring_m = tuple(args.candidate_ring_m)
            if candidate_ring_m != tuple(sorted(set(candidate_ring_m))) or candidate_ring_m[-1] != args.max_radius_m:
                parser.error("--candidate-ring-m values must be unique, ascending, and end at --max-radius-m")
            if candidate_ring_m[0] < args.initial_radius_m:
                parser.error("--candidate-ring-m values must not be below --initial-radius-m")
        cases = []
        cohorts = []
        for run_path in args.run:
            run_cases, metadata = build_run_cases(
                run_path,
                max_cases=args.max_cases,
                seed=args.seed,
                initial_radius_m=args.initial_radius_m,
                max_radius_m=args.max_radius_m,
                workers=args.workers,
                dem_path=args.dem_vrt,
                requested_case_ids=set(args.case_id) if args.case_id else None,
                candidate_ring_m=candidate_ring_m,
                shallow_mineral_vector=args.shallow_mineral_vector,
            )
            cases.extend(run_cases)
            cohorts.append(metadata)
        results = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "ssurgo_masked_valid_cohort",
            "cohorts": cohorts,
            "results": [evaluate_masked_case(case) for case in cases],
        }
        results["summary"] = summarize_evaluations(results["results"])
        results["scoring_summary"] = summarize_score_variants(results["results"])
        results["candidate_study"] = summarize_candidate_study(results["results"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
