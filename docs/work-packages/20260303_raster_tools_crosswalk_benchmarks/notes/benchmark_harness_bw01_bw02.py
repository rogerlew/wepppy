#!/usr/bin/env python3
"""Minimal benchmark harness for BW-01 and BW-02.

Runs current-stack and raster_tools variants with identical warmup/measure loops,
then computes basic parity outcomes for draft benchmarking.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from osgeo import gdal, osr

ROOT = Path("/workdir/wepppy/docs/work-packages/20260303_raster_tools_crosswalk_benchmarks")
RAW = ROOT / "notes" / "raw"
OUT = RAW / "bench_outputs"
OUT.mkdir(parents=True, exist_ok=True)

WARMUP = 1
RUNS = 3

SRC_DEM = Path("/home/workdir/raster_tools/tests/data/raster/dem_small.tif")
SRC_CLIP_DEM = Path("/home/workdir/raster_tools/tests/data/raster/dem.tif")
SRC_CLIP_VEC = Path("/home/workdir/raster_tools/tests/data/vector/pods_first_10.shp")

VENV_PY = Path("/tmp/raster-tools-bench-venv/bin/python")
SYSTEM_PY = Path("/usr/bin/python3")


@dataclass
class Variant:
    name: str
    cmd: List[str]
    env: Dict[str, str] | None = None


@dataclass
class Case:
    case_id: str
    current: Variant
    candidate: Variant
    current_out: Path
    candidate_out: Path


def _percentile(values: List[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile for empty sample list")
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    pos = q * (len(sorted_values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = pos - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def timed_runs(variant: Variant) -> dict:
    warmup_times: List[float] = []
    measured_times: List[float] = []
    stderr_samples: List[str] = []

    for i in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        proc = subprocess.run(
            variant.cmd,
            env=variant.env,
            text=True,
            capture_output=True,
            check=False,
        )
        dt = time.perf_counter() - t0

        if proc.returncode != 0:
            return {
                "ok": False,
                "returncode": proc.returncode,
                "stderr": proc.stderr.strip(),
                "stdout": proc.stdout.strip(),
            }

        if proc.stderr.strip():
            stderr_samples.append(proc.stderr.strip())

        if i < WARMUP:
            warmup_times.append(dt)
        else:
            measured_times.append(dt)

    return {
        "ok": True,
        "warmup_s": warmup_times,
        "runs_s": measured_times,
        "median_s": statistics.median(measured_times),
        "p95_s": _percentile(measured_times, 0.95),
        "stderr_samples": stderr_samples[:3],
    }


def _open(path: Path):
    ds = gdal.Open(str(path))
    if ds is None:
        raise RuntimeError(f"Failed to open raster: {path}")
    return ds


def _grid_metadata(ds) -> Tuple[Tuple[int, int], Tuple[float, ...], str]:
    shape = (ds.RasterYSize, ds.RasterXSize)
    geotransform = tuple(float(v) for v in ds.GetGeoTransform())
    projection = ds.GetProjection()
    return shape, geotransform, projection


def _same_projection(wkt_a: str, wkt_b: str) -> bool:
    proj_a = osr.SpatialReference(wkt=wkt_a)
    proj_b = osr.SpatialReference(wkt=wkt_b)
    return bool(proj_a.IsSame(proj_b))


def _same_geotransform(gt_a: Tuple[float, ...], gt_b: Tuple[float, ...], tol: float = 1e-9) -> bool:
    if len(gt_a) != len(gt_b):
        return False
    return all(abs(a - b) <= tol for a, b in zip(gt_a, gt_b))


def _comparability(ds_a, ds_b) -> dict:
    shape_a, gt_a, proj_a = _grid_metadata(ds_a)
    shape_b, gt_b, proj_b = _grid_metadata(ds_b)
    same_proj = _same_projection(proj_a, proj_b)
    same_shape = shape_a == shape_b
    same_geotransform = _same_geotransform(gt_a, gt_b)
    comparable = bool(same_proj and same_shape and same_geotransform)
    reason = None
    if not comparable:
        reason = "grid mismatch (projection/shape/geotransform)"
    return {
        "shape_current": list(shape_a),
        "shape_candidate": list(shape_b),
        "geotransform_current": list(gt_a),
        "geotransform_candidate": list(gt_b),
        "same_projection": same_proj,
        "same_shape": same_shape,
        "same_geotransform": same_geotransform,
        "comparable": comparable,
        "non_comparable_reason": reason,
    }


def _valid_mask(arr, nodata):
    mask = (arr == arr)
    if nodata is not None:
        mask &= arr != nodata
    return mask


def parity_bw01(current_path: Path, candidate_path: Path) -> dict:
    ds_a = _open(current_path)
    ds_b = _open(candidate_path)

    grid = _comparability(ds_a, ds_b)
    arr_a = ds_a.GetRasterBand(1).ReadAsArray()
    arr_b = ds_b.GetRasterBand(1).ReadAsArray()

    if grid["comparable"]:
        nodata_a = ds_a.GetRasterBand(1).GetNoDataValue()
        nodata_b = ds_b.GetRasterBand(1).GetNoDataValue()
        mask = _valid_mask(arr_a, nodata_a) & _valid_mask(arr_b, nodata_b)
        valid_count = int(mask.sum())
        if valid_count > 0:
            diff = (arr_a[mask] - arr_b[mask]).astype("float64")
            rmse = float((diff * diff).mean() ** 0.5)
            max_abs = float(abs(diff).max())
        else:
            rmse = None
            max_abs = None
    else:
        rmse = None
        max_abs = None

    if not grid["comparable"]:
        parity_status = "non_comparable"
        pass_value = None
    elif rmse is None:
        parity_status = "non_comparable"
        grid["non_comparable_reason"] = "no overlapping valid cells after nodata masking"
        pass_value = None
    else:
        pass_value = bool(rmse <= 1.0)
        parity_status = "pass" if pass_value else "fail"

    return {
        **grid,
        "rmse": rmse,
        "max_abs": max_abs,
        "pass": pass_value,
        "parity_status": parity_status,
        "tolerance": "comparable grid required (same projection/shape/geotransform), then RMSE<=1.0 on non-nodata cells",
    }


def parity_bw02(current_path: Path, candidate_path: Path) -> dict:
    ds_a = _open(current_path)
    ds_b = _open(candidate_path)

    grid = _comparability(ds_a, ds_b)
    arr_a = ds_a.GetRasterBand(1).ReadAsArray()
    arr_b = ds_b.GetRasterBand(1).ReadAsArray()

    nodata_a = ds_a.GetRasterBand(1).GetNoDataValue()
    nodata_b = ds_b.GetRasterBand(1).GetNoDataValue()
    valid_a = _valid_mask(arr_a, nodata_a)
    valid_b = _valid_mask(arr_b, nodata_b)
    nz_a = int(valid_a.sum())
    nz_b = int(valid_b.sum())
    ratio = (min(nz_a, nz_b) / max(nz_a, nz_b)) if max(nz_a, nz_b) else 1.0

    if not grid["comparable"]:
        parity_status = "non_comparable"
        pass_value = None
    else:
        pass_value = bool(ratio >= 0.85)
        parity_status = "pass" if pass_value else "fail"

    return {
        **grid,
        "nonzero_current": nz_a,
        "nonzero_candidate": nz_b,
        "nonzero_ratio": ratio,
        "pass": pass_value,
        "parity_status": parity_status,
        "tolerance": "comparable grid required (same projection/shape/geotransform), then nonzero footprint ratio >= 0.85",
    }


def main() -> None:
    bw01_current_out = OUT / "bw01_current_gdal.tif"
    bw01_candidate_out = OUT / "bw01_candidate_raster_tools.tif"
    bw02_current_out = OUT / "bw02_current_gdal_clip.tif"
    bw02_candidate_out = OUT / "bw02_candidate_raster_tools_clip.tif"

    bw01 = Case(
        case_id="BW-01",
        current=Variant(
            name="current_gdal_warp",
            cmd=[
                str(SYSTEM_PY),
                "-c",
                (
                    "from osgeo import gdal; "
                    f"src=r'{SRC_DEM}'; out=r'{bw01_current_out}'; "
                    "opts=gdal.WarpOptions(dstSRS='EPSG:5070',resampleAlg='bilinear'); "
                    "ds=gdal.Warp(out, src, options=opts); "
                    "assert ds is not None"
                ),
            ],
        ),
        candidate=Variant(
            name="candidate_raster_tools_reproject",
            cmd=[
                str(VENV_PY),
                "-c",
                (
                    "import raster_tools as rts; from raster_tools import warp; "
                    f"src=r'{SRC_DEM}'; out=r'{bw01_candidate_out}'; "
                    "r=rts.Raster(src); rr=warp.reproject(r, 'EPSG:5070', resample_method='bilinear'); rr.save(out)"
                ),
            ],
            env={**os.environ, "PYTHONPATH": "/home/workdir/raster_tools"},
        ),
        current_out=bw01_current_out,
        candidate_out=bw01_candidate_out,
    )

    bw02 = Case(
        case_id="BW-02",
        current=Variant(
            name="current_gdal_cutline_clip",
            cmd=[
                str(SYSTEM_PY),
                "-c",
                (
                    "from osgeo import gdal; "
                    f"src=r'{SRC_CLIP_DEM}'; cut=r'{SRC_CLIP_VEC}'; out=r'{bw02_current_out}'; "
                    "opts=gdal.WarpOptions(cutlineDSName=cut, cropToCutline=True); "
                    "ds=gdal.Warp(out, src, options=opts); assert ds is not None"
                ),
            ],
        ),
        candidate=Variant(
            name="candidate_raster_tools_clip",
            cmd=[
                str(VENV_PY),
                "-c",
                (
                    "import raster_tools as rts; from raster_tools import clipping; "
                    f"src=r'{SRC_CLIP_DEM}'; vec=r'{SRC_CLIP_VEC}'; out=r'{bw02_candidate_out}'; "
                    "r=rts.Raster(src); v=rts.open_vectors(vec); rc=clipping.clip(v, r); rc.save(out)"
                ),
            ],
            env={**os.environ, "PYTHONPATH": "/home/workdir/raster_tools"},
        ),
        current_out=bw02_current_out,
        candidate_out=bw02_candidate_out,
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "harness": {"warmup": WARMUP, "runs": RUNS},
        "cases": {},
    }

    for case in (bw01, bw02):
        current_result = timed_runs(case.current)
        candidate_result = timed_runs(case.candidate)

        parity = None
        if current_result.get("ok") and candidate_result.get("ok"):
            if case.case_id == "BW-01":
                parity = parity_bw01(case.current_out, case.candidate_out)
            elif case.case_id == "BW-02":
                parity = parity_bw02(case.current_out, case.candidate_out)

        results["cases"][case.case_id] = {
            "current": current_result,
            "candidate": candidate_result,
            "parity": parity,
            "outputs": {
                "current": str(case.current_out),
                "candidate": str(case.candidate_out),
            },
        }

    out_json = RAW / "benchmark_runs_bw01_bw02.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    out_json_ts = RAW / f"benchmark_runs_bw01_bw02_{run_id}.json"
    out_json_ts.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_json_ts}")


if __name__ == "__main__":
    main()
