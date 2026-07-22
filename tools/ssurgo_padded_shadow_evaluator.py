#!/usr/bin/env python3
"""Evaluate padded-SSURGO donor evidence without changing a completed run."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import random
from typing import Any, Mapping, Sequence


FULL_SSURGO_RELATIVE_PATH = Path("ssurgo/gNATSGSO/2025/.vrt")
DEFAULT_PADDING_M = 2_000.0
DIRECT_VECTOR_FIELDS = {
    "dbthirdbar_r": (0.5, 3.0),
    "ksat_r": (0.0, 100_000.0),
    "cec7_r": (0.0, 200.0),
    "hzdepb_r": (0.1, 1_000.0),
    "fraggt10_r": (0.0, 100.0),
    "frag3to10_r": (0.0, 100.0),
}


def full_ssurgo_vrt() -> Path:
    path = Path(os.environ.get("GEODATA_DIR", "/geodata")) / FULL_SSURGO_RELATIVE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Full gNATSGO VRT not found: {path}")
    return path


def _numeric_mukey(value: Any) -> str:
    return str(value).split("-", 1)[0]


def padded_bounds_epsg5070(project_raster: Path, padding_m: float) -> tuple[float, float, float, float]:
    """Transform a run raster extent to EPSG:5070 and add an isotropic padding."""
    if padding_m < 0:
        raise ValueError("padding_m must be non-negative")
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(project_raster) as dataset:
        if dataset.crs is None:
            raise ValueError(f"Project raster has no CRS: {project_raster}")
        left, bottom, right, top = transform_bounds(dataset.crs, "EPSG:5070", *dataset.bounds, densify_pts=21)
    return left - padding_m, bottom - padding_m, right + padding_m, top + padding_m


def materialize_padded_candidate_raster(
    source_raster: Path, bounds_epsg5070: tuple[float, float, float, float], output_raster: Path
) -> dict[str, Any]:
    """Copy one bounded source crop atomically, returning immutable raster evidence."""
    import rasterio
    from rasterio.windows import from_bounds

    output_raster.parent.mkdir(parents=True, exist_ok=True)
    if output_raster.exists():
        with rasterio.open(output_raster) as dataset:
            return {"path": str(output_raster), "shape": [dataset.height, dataset.width], "reused": True}
    temporary = output_raster.with_suffix(".partial.tif")
    if temporary.exists():
        temporary.unlink()
    with rasterio.open(source_raster) as source:
        window = from_bounds(*bounds_epsg5070, transform=source.transform).round_offsets().round_lengths()
        window = window.intersection(rasterio.windows.Window(0, 0, source.width, source.height))
        if window.width <= 0 or window.height <= 0:
            raise ValueError("Padded candidate bounds do not intersect the full gNATSGO raster")
        profile = source.profile.copy()
        profile.update(
            driver="GTiff", height=int(window.height), width=int(window.width),
            transform=source.window_transform(window), compress="LZW",
        )
        with rasterio.open(temporary, "w", **profile) as destination:
            destination.write(source.read(1, window=window), 1)
    os.replace(temporary, output_raster)
    return {"path": str(output_raster), "shape": [int(window.height), int(window.width)], "reused": False}


def raster_mukeys(raster_path: Path) -> set[int]:
    import numpy as np
    import rasterio

    with rasterio.open(raster_path) as dataset:
        values = set()
        for _, window in dataset.block_windows(1):
            data = dataset.read(1, window=window)
            values.update(int(value) for value in np.unique(data) if int(value) > 0)
    return values


def direct_shallow_profile(layers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Preserve raw source values from the shallowest usable mineral layer."""
    for index, layer in enumerate(layers):
        try:
            organic_matter = float(layer.get("om_r"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(organic_matter) or not 0.0 <= organic_matter <= 20.0:
            continue
        values: dict[str, float] = {}
        for field, (minimum, maximum) in DIRECT_VECTOR_FIELDS.items():
            try:
                value = float(layer.get(field))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and minimum <= value <= maximum:
                values[field] = value
        if len(values) >= 3:
            return {
                "classification": "profile_bearing_residual",
                "source_horizon_index": index,
                "source_chkey": layer.get("chkey"),
                "source_hzname": layer.get("hzname"),
                "organic_matter_pct": organic_matter,
                "direct_values": values,
            }
    return {"classification": "profile_free_or_unusable_residual", "direct_values": {}}


def _vector_distance(source: Mapping[str, float], candidate: Mapping[str, float]) -> tuple[float | None, list[str]]:
    fields = sorted(set(source) & set(candidate))
    if len(fields) < 3:
        return None, fields
    scales = {field: max(abs(source[field]) * 0.05, abs(candidate[field]) * 0.05, 1.0e-6) for field in fields}
    return sum(abs(source[field] - candidate[field]) / scales[field] for field in fields) / len(fields), fields


def shadow_disposition(
    source_profile: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], global_mukey: str | None
) -> dict[str, Any]:
    """Select a shadow-only proposal with complete component provenance."""
    scored = []
    source_values = source_profile.get("direct_values", {})
    for candidate in candidates:
        distance, fields = _vector_distance(source_values, candidate.get("direct_values", {}))
        scored.append({**candidate, "vector_distance": distance, "vector_fields": fields})
    profile_scored = [candidate for candidate in scored if candidate["vector_distance"] is not None]
    if profile_scored:
        profile_scored.sort(key=lambda item: (item["vector_distance"], -item["pixel_support"], int(item["mukey"])))
        return {"proposed_mukey": profile_scored[0]["mukey"], "reason": "profile_vector_shadow", "candidates": scored}
    if scored:
        scored.sort(key=lambda item: (-item["pixel_support"], int(item["mukey"])))
        return {"proposed_mukey": scored[0]["mukey"], "reason": "spatial_support_shadow", "candidates": scored}
    return {"proposed_mukey": None, "reason": "no_local_buildable_candidate", "candidates": [], "global_mukey": global_mukey}


def _global_baseline(raw: Mapping[str, str], valid_mukeys: set[str]) -> str | None:
    counts = Counter(_numeric_mukey(value) for value in raw.values() if _numeric_mukey(value) in valid_mukeys)
    return min(counts, key=lambda mukey: (-counts[mukey], int(mukey))) if counts else None


def current_invalid_mukeys(raw: Mapping[str, str], buildable_mukeys: set[str]) -> set[str]:
    """Return only MUKEYs that fail the current padded candidate build."""
    return {_numeric_mukey(mukey) for mukey in raw.values()} - buildable_mukeys


def masked_valid_seeds(
    raw: Mapping[str, str], project_buildable_mukeys: set[str], *, count: int, seed: int
) -> list[tuple[str, str]]:
    """Choose deterministic hillslope/MUKEY masked-valid counterfactuals."""
    eligible = sorted([
        (str(topaz_id), _numeric_mukey(mukey))
        for topaz_id, mukey in raw.items()
        if _numeric_mukey(mukey) in project_buildable_mukeys
    ])
    if count < 0:
        raise ValueError("masked holdout count must be non-negative")
    if count >= len(eligible):
        return eligible
    return sorted(random.Random(seed).sample(eligible, count), key=lambda item: int(item[0]))


def evaluate_run(
    run_path: Path, output_dir: Path, *, padding_m: float, workers: int,
    masked_holdout_count: int, seed: int,
) -> dict[str, Any]:
    """Build and evaluate a padded candidate cohort without writing run state."""
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import bounds as window_bounds

    from wepppy.soils.ssurgo import SurgoSoilCollection
    from wepppyo3.raster_characteristics import categorical_support_within_bounds

    state = json.loads((run_path / "soils.nodb").read_text(encoding="utf-8")).get("py/state", {})
    raw = {str(topaz_id): _numeric_mukey(mukey) for topaz_id, mukey in state.get("raw_ssurgo_domsoil_d", {}).items()}

    project_raster = run_path / "dem" / "wbt" / "subwta.tif"
    bounds = padded_bounds_epsg5070(project_raster, padding_m)
    candidate_raster = output_dir / "ssurgo_candidate_padded.tif"
    raster_evidence = materialize_padded_candidate_raster(full_ssurgo_vrt(), bounds, candidate_raster)
    candidate_mukeys = raster_mukeys(candidate_raster)
    cache_path = output_dir / "ssurgo_candidate_study.sqlite"
    collection = SurgoSoilCollection(sorted(candidate_mukeys), cache_db_path=str(cache_path))
    collection.makeWeppSoils(initial_sat=0.75, ksflag=True, max_workers=workers)
    buildable = {str(mukey) for mukey in collection.getValidWeppSoils()}
    project_buildable = {_numeric_mukey(mukey) for mukey in raw.values()} & buildable
    invalid_mukeys = current_invalid_mukeys(raw, buildable)
    real_seeds = [(topaz_id, mukey, "current_invalid") for topaz_id, mukey in raw.items() if mukey in invalid_mukeys]
    holdout_seeds = [
        (topaz_id, mukey, "masked_valid_holdout")
        for topaz_id, mukey in masked_valid_seeds(raw, project_buildable, count=masked_holdout_count, seed=seed)
    ]
    records = []
    with rasterio.open(project_raster) as subwta:
        values = subwta.read(1)
        for topaz_id, raw_mukey, seed_kind in sorted(real_seeds + holdout_seeds, key=lambda item: (item[2], int(item[0]))):
            rows, cols = (values == int(topaz_id)).nonzero()
            if rows.size == 0:
                continue
            local_bounds = window_bounds(
                rasterio.windows.Window(cols.min(), rows.min(), cols.max() - cols.min() + 1, rows.max() - rows.min() + 1),
                subwta.transform,
            )
            local_bounds = transform_bounds(subwta.crs, "EPSG:5070", *local_bounds, densify_pts=21)
            excluded_mukeys = set(invalid_mukeys)
            if seed_kind == "masked_valid_holdout":
                excluded_mukeys.add(raw_mukey)
            eligible_mukeys = buildable - ({raw_mukey} if seed_kind == "masked_valid_holdout" else set())
            support = categorical_support_within_bounds(
                str(candidate_raster), local_bounds, padding_m, {int(value) for value in excluded_mukeys}
            )
            candidates = []
            for mukey, pixels in support:
                mukey_text = str(mukey)
                if mukey_text not in eligible_mukeys:
                    continue
                layers = [layer for component in collection.get_components(mukey) for layer in collection.get_layers(component["cokey"])]
                candidates.append({"mukey": mukey_text, "pixel_support": int(pixels), **direct_shallow_profile(layers)})
            source_layers = [
                layer for component in collection.get_components(int(raw_mukey))
                for layer in collection.get_layers(component["cokey"])
            ]
            source_profile = direct_shallow_profile(source_layers)
            baseline = _global_baseline(raw, project_buildable - ({raw_mukey} if seed_kind == "masked_valid_holdout" else set()))
            disposition = shadow_disposition(source_profile, candidates, baseline)
            records.append({
                "record_type": "ssurgo_padded_shadow_evaluation", "schema_version": 1,
                "topaz_id": topaz_id, "raw_mukey": raw_mukey, "global_mukey": baseline,
                "seed_kind": seed_kind, "bounds_epsg5070": list(local_bounds), "source_profile": source_profile,
                "candidate_count": len(candidates), "shadow_disposition": disposition,
            })
    return {
        "record_type": "ssurgo_padded_shadow_cohort", "schema_version": 1,
        "run_path": str(run_path), "padding_m": padding_m, "full_ssurgo_vrt": str(full_ssurgo_vrt()),
        "candidate_raster": raster_evidence, "candidate_mukey_count": len(candidate_mukeys),
        "candidate_buildable_mukey_count": len(buildable), "current_invalid_mukeys": sorted(invalid_mukeys, key=int),
        "masked_holdout_count": masked_holdout_count, "seed": seed,
        "records": records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--padding-m", type=float, default=DEFAULT_PADDING_M)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--masked-holdout-count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be positive")
    result = evaluate_run(
        args.run, args.output_dir, padding_m=args.padding_m, workers=args.workers,
        masked_holdout_count=args.masked_holdout_count, seed=args.seed,
    )
    output = args.output_dir / "shadow_evaluation.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
