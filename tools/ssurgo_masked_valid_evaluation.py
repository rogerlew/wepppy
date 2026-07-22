#!/usr/bin/env python3
"""Evaluate masked-valid SSURGO donor proposals without changing a run."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1


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
    ):
        if field in case:
            result[field] = case[field]
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


def _median(values: Any) -> float | None:
    import numpy as np

    finite = values[np.isfinite(values)]
    return float(np.median(finite)) if finite.size else None


def _elevation_deltas(
    labels: Any,
    mukeys: Any,
    elevation: Any,
    transform: Any,
    *,
    topaz_id: str,
    bounds: tuple[float, float, float, float],
    search_radius_m: float | None,
    local_mukey: str | None,
    global_mukey: str,
    global_elevation_medians: Mapping[str, float | None],
) -> tuple[float | None, float | None]:
    """Compare source-hillslope elevation with vectorized local/global MUKEY masks."""
    import numpy as np
    from rasterio.windows import Window, from_bounds

    source_median = _median(elevation[labels == int(topaz_id)])
    if source_median is None:
        return None, None
    global_median = global_elevation_medians.get(global_mukey)
    global_delta = abs(source_median - global_median) if global_median is not None else None
    if local_mukey is None or search_radius_m is None:
        return None, global_delta
    min_x, min_y, max_x, max_y = bounds
    window = from_bounds(
        min_x - search_radius_m,
        min_y - search_radius_m,
        max_x + search_radius_m,
        max_y + search_radius_m,
        transform=transform,
    ).round_offsets().round_lengths()
    full = Window(0, 0, mukeys.shape[1], mukeys.shape[0])
    try:
        window = window.intersection(full)
    except ValueError:
        return None, global_delta
    row_start, col_start = int(window.row_off), int(window.col_off)
    row_stop, col_stop = row_start + int(window.height), col_start + int(window.width)
    local_median = _median(
        elevation[row_start:row_stop, col_start:col_stop][
            mukeys[row_start:row_stop, col_start:col_stop] == int(local_mukey)
        ]
    )
    local_delta = abs(source_median - local_median) if local_median is not None else None
    return local_delta, global_delta


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


def build_run_cases(
    run_path: Path,
    *,
    max_cases: int,
    seed: int,
    initial_radius_m: float,
    max_radius_m: float,
    workers: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build read-only masked-valid cases from one completed gridded SSURGO run."""
    import rasterio

    from wepppy.nodb.core.soils import Soils
    from wepppyo3.raster_characteristics import local_mukey_candidates

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
    if max_cases <= 0:
        raise ValueError("max_cases must be positive")
    if len(eligible) > max_cases:
        eligible = sorted(random.Random(seed).sample(eligible, max_cases), key=lambda item: int(item[0]))

    subwta_path = run_path / "dem" / "wbt" / "subwta.tif"
    ssurgo_path = run_path / "soils" / "ssurgo.tif"
    with rasterio.open(subwta_path) as subwta:
        labels = subwta.read(1)
        transform = subwta.transform
        bounds_by_topaz: dict[str, tuple[float, float, float, float]] = {}
        for topaz_id, _ in eligible:
            rows, cols = (labels == int(topaz_id)).nonzero()
            if rows.size == 0:
                continue
            window = rasterio.windows.Window(
                cols.min(), rows.min(), cols.max() - cols.min() + 1, rows.max() - rows.min() + 1
            )
            bounds_by_topaz[topaz_id] = rasterio.windows.bounds(window, subwta.transform)

    with rasterio.open(ssurgo_path) as ssurgo, rasterio.open(run_path / "dem" / "dem.tif") as dem:
        if ssurgo.shape != dem.shape or ssurgo.transform != dem.transform:
            raise ValueError(f"unaligned SSURGO and DEM grids: {run_path}")
        mukey_grid = ssurgo.read(1)
        elevation_grid = dem.read(1).astype(float)
        if dem.nodata is not None:
            elevation_grid[elevation_grid == dem.nodata] = math.nan
    global_elevation_medians = {
        mukey: _median(elevation_grid[mukey_grid == int(mukey)]) for mukey in valid_mukeys
    }

    selected = [(topaz_id, mukey) for topaz_id, mukey in eligible if topaz_id in bounds_by_topaz]
    clusters = [(topaz_id, [int(mukey)], bounds_by_topaz[topaz_id]) for topaz_id, mukey in selected]
    cases: list[dict[str, Any]] = []
    for withheld_mukey in sorted({mukey for _, mukey in selected}, key=int):
        masked_valid = {int(mukey) for mukey in valid_mukeys - {withheld_mukey}}
        matching = [(topaz_id, mukey) for topaz_id, mukey in selected if mukey == withheld_mukey]
        results = local_mukey_candidates(
            raster_path=str(ssurgo_path),
            clusters=[cluster for cluster in clusters if cluster[0] in {topaz_id for topaz_id, _ in matching}],
            valid_mukeys=masked_valid,
            initial_radius_m=initial_radius_m,
            max_radius_m=max_radius_m,
            workers=workers,
        )
        global_mukey = _global_baseline(raw_domsoil_d, valid_mukeys, valid_order, withheld_mukey)
        if global_mukey is None:
            continue
        for topaz_id, _ in matching:
            _, radius_m, support, exhausted, pixels_read = results[topaz_id]
            local_mukey = _numeric_mukey(sorted(support, key=lambda item: (-item[1], item[0]))[0][0]) if support else None
            local_elevation_delta_m, global_elevation_delta_m = _elevation_deltas(
                labels,
                mukey_grid,
                elevation_grid,
                transform,
                topaz_id=topaz_id,
                bounds=bounds_by_topaz[topaz_id],
                search_radius_m=radius_m,
                local_mukey=local_mukey,
                global_mukey=global_mukey,
                global_elevation_medians=global_elevation_medians,
            )
            summary_mukeys = {withheld_mukey, global_mukey}
            if local_mukey is not None:
                summary_mukeys.add(local_mukey)
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
                }
            )
    metadata = {
        "run_path": str(run_path),
        "eligible_hillslopes": len(eligible),
        "evaluated_hillslopes": len(cases),
        "seed": seed,
        "initial_radius_m": initial_radius_m,
        "max_radius_m": max_radius_m,
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
    args = parser.parse_args(argv)
    if args.input is not None:
        cases = json.loads(args.input.read_text(encoding="utf-8"))
        results: Any = [evaluate_masked_case(case) for case in cases]
    else:
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
