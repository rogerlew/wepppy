#!/usr/bin/env python3
"""Curiosity benchmark: wepppyo3 vs oxidized-rasterstats zonal-style workloads.

This script benchmarks:
- wepppyo3.raster_characteristics.identify_mode_single_raster_key
- rasterstats.zonal_stats (oxidized-rasterstats rust-dispatch path)

using WEPPcloud fixtures from oxidized-rasterstats (`small`, `large_local`).
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from osgeo import gdal, ogr


ROOT = Path("/workdir/wepppy/docs/work-packages/20260303_raster_tools_crosswalk_benchmarks")
RAW = ROOT / "notes" / "raw"
OUT_DIR = RAW / "bench_outputs" / "zonal"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = RAW / "zonal_benchmark_wepppyo3_oxidized_rasterstats.json"
FIXTURE_ROOT = Path("/home/workdir/oxidized-rasterstats/tests/fixtures/weppcloud")

WARMUP = 1
RUNS = 3
STATS = ["count", "majority"]


def _percentile(values: list[float], q: float) -> float:
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    pos = q * (len(sorted_values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = pos - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _timed_runs(fn):
    warmup: list[float] = []
    runs: list[float] = []
    last_result: Any = None
    for i in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        result = fn()
        dt = time.perf_counter() - t0
        if i < WARMUP:
            warmup.append(dt)
        else:
            runs.append(dt)
            last_result = result
    return {
        "warmup_s": warmup,
        "runs_s": runs,
        "median_s": statistics.median(runs),
        "p95_s": _percentile(runs, 0.95),
        "result": last_result,
    }


def _build_topaz_key_raster(vectors_geojson: Path, template_raster: Path, out_raster: Path) -> None:
    template = gdal.Open(str(template_raster))
    if template is None:
        raise RuntimeError(f"Failed to open template raster: {template_raster}")

    driver = gdal.GetDriverByName("GTiff")
    if driver is None:
        raise RuntimeError("GTiff driver unavailable")

    ds_out = driver.Create(
        str(out_raster),
        template.RasterXSize,
        template.RasterYSize,
        1,
        gdal.GDT_Int32,
    )
    if ds_out is None:
        raise RuntimeError(f"Failed to create key raster: {out_raster}")

    ds_out.SetProjection(template.GetProjection())
    ds_out.SetGeoTransform(template.GetGeoTransform())
    band = ds_out.GetRasterBand(1)
    band.SetNoDataValue(-9999)
    band.Fill(-9999)

    vector_ds = ogr.Open(str(vectors_geojson))
    if vector_ds is None:
        raise RuntimeError(f"Failed to open vectors: {vectors_geojson}")
    layer = vector_ds.GetLayer(0)
    if layer is None:
        raise RuntimeError(f"Failed to read layer from vectors: {vectors_geojson}")

    rc = gdal.RasterizeLayer(
        ds_out,
        [1],
        layer,
        options=["ATTRIBUTE=TopazID", "ALL_TOUCHED=TRUE"],
    )
    if rc != 0:
        raise RuntimeError(f"RasterizeLayer failed with code {rc}")

    band.FlushCache()
    ds_out.FlushCache()
    ds_out = None


def _load_topaz_ids(vectors_geojson: Path) -> list[int]:
    data = json.loads(vectors_geojson.read_text(encoding="utf-8"))
    ids: list[int] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        if "TopazID" in props:
            ids.append(int(props["TopazID"]))
    return ids


def main() -> None:
    sys.path.insert(0, "/home/workdir/oxidized-rasterstats/python")
    sys.path.insert(0, "/home/workdir/wepppyo3/release/linux/py312")
    os.environ["OXRS_ENABLE_RUST"] = "1"
    os.environ.pop("OXRS_DISABLE_RUST", None)

    from rasterstats import zonal_stats
    from rasterstats._dispatch import _rust_available_default_on
    from wepppyo3.raster_characteristics import identify_mode_single_raster_key

    datasets = {
        "small": FIXTURE_ROOT / "small",
        "large_local": FIXTURE_ROOT / "large_local",
    }

    output: dict[str, Any] = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "python": sys.version.split()[0],
        "oxidized_rust_available": bool(_rust_available_default_on()),
        "warmup_runs": WARMUP,
        "measured_runs": RUNS,
        "stats": STATS,
        "datasets": {},
    }

    for name, root in datasets.items():
        vectors = root / "dem" / "wbt" / "subcatchments.geojson"
        nlcd = root / "landuse" / "nlcd.tif"
        if not vectors.exists() or not nlcd.exists():
            output["datasets"][name] = {"skipped": True, "reason": "missing vectors or nlcd raster"}
            continue

        key_raster = OUT_DIR / f"{name}_topaz_key.tif"
        _build_topaz_key_raster(vectors, nlcd, key_raster)
        topaz_ids = _load_topaz_ids(vectors)

        def run_wepppyo3():
            return identify_mode_single_raster_key(
                str(key_raster),
                str(nlcd),
                ignore_channels=False,
                ignore_keys=set(),
                band_indx=1,
            )

        def run_oxidized():
            return zonal_stats(
                str(vectors),
                str(nlcd),
                stats=STATS,
                all_touched=True,
                boundless=True,
            )

        wp = _timed_runs(run_wepppyo3)
        ox = _timed_runs(run_oxidized)
        wp_map: dict[str, int] = wp["result"]
        ox_list: list[dict[str, Any]] = ox["result"]

        overlap_count = 0
        matches = 0
        for idx, topaz_id in enumerate(topaz_ids):
            if idx >= len(ox_list):
                break
            majority = ox_list[idx].get("majority")
            if majority is None:
                continue
            key = str(topaz_id)
            if key not in wp_map:
                continue
            overlap_count += 1
            try:
                if int(round(float(majority))) == int(wp_map[key]):
                    matches += 1
            except (TypeError, ValueError):
                continue

        output["datasets"][name] = {
            "vectors": str(vectors),
            "nlcd": str(nlcd),
            "key_raster": str(key_raster),
            "feature_count": len(topaz_ids),
            "wepppyo3": {
                "median_s": wp["median_s"],
                "p95_s": wp["p95_s"],
                "runs_s": wp["runs_s"],
                "result_key_count": len(wp_map),
            },
            "oxidized_rasterstats": {
                "median_s": ox["median_s"],
                "p95_s": ox["p95_s"],
                "runs_s": ox["runs_s"],
                "result_feature_count": len(ox_list),
            },
            "diagnostics": {
                "majority_overlap_count": overlap_count,
                "majority_match_count": matches,
                "majority_match_ratio": (matches / overlap_count) if overlap_count else None,
            },
            "notes": "Semantics are zonal-like but not fully identical: wepppyo3 uses raster key/value mode; oxidized-rasterstats uses polygon zonal stats.",
        }

    OUTPUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
