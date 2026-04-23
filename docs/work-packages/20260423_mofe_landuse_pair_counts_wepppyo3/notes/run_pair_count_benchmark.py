from __future__ import annotations

import json
import math
import shutil
import statistics
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import Affine

from wepppyo3.raster_characteristics import count_intersecting_raster_key_pairs


PACKAGE_ROOT = Path(
    "/workdir/wepppy/docs/work-packages/20260423_mofe_landuse_pair_counts_wepppyo3"
)
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
BENCHMARK_RAW_PATH = ARTIFACTS_DIR / "benchmark_raw.json"
BENCHMARK_SUMMARY_PATH = ARTIFACTS_DIR / "benchmark_summary.md"
PARITY_RAW_PATH = ARTIFACTS_DIR / "parity_raw.json"
PARITY_NOTES_PATH = ARTIFACTS_DIR / "parity_notes.md"

BENCHMARK_ITERATIONS = 6
ABS_TOL = 1e-9


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    url: str
    root: Path


RUN_SPECS = [
    RunSpec(
        run_id="moth-eaten-blackhead",
        url="https://wc.bearhive.duckdns.org/weppcloud/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/",
        root=Path("/wc1/runs/mo/moth-eaten-blackhead"),
    ),
    RunSpec(
        run_id="objectionable-sublimate",
        url="https://wc.bearhive.duckdns.org/weppcloud/runs/objectionable-sublimate/disturbed9002_wbt/",
        root=Path("/wc1/runs/ob/objectionable-sublimate"),
    ),
    RunSpec(
        run_id="cochlear-beriberi",
        url="https://wc.bearhive.duckdns.org/weppcloud/runs/cochlear-beriberi/disturbed9002-mofe/",
        root=Path("/wc1/runs/co/cochlear-beriberi"),
    ),
    RunSpec(
        run_id="ordained-incentive",
        url="https://wc.bearhive.duckdns.org/weppcloud/runs/ordained-incentive/disturbed9002-wbt-mofe/",
        root=Path("/wc1/runs/or/ordained-incentive"),
    ),
    RunSpec(
        run_id="uninsured-deformation",
        url="https://wc.bearhive.duckdns.org/weppcloud/runs/uninsured-deformation/disturbed9002-wbt-mofe/",
        root=Path("/wc1/runs/un/uninsured-deformation"),
    ),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _mean(values: list[float]) -> float:
    return statistics.mean(values)


def _synthesize_single_ofe_map(subwta_path: Path, mofe_path: Path) -> None:
    with rasterio.open(subwta_path) as src:
        profile = src.profile.copy()
        width = src.width
        height = src.height

    profile.update(dtype="int32", count=1, nodata=0)
    data = np.ones((height, width), dtype=np.int32)
    with rasterio.open(mofe_path, "w", **profile) as dst:
        dst.write(data, 1)


def _resolve_subwta_source(run: RunSpec) -> Path:
    candidates = [
        run.root / "dem" / "wbt" / "subwta.tif",
        run.root / "dem" / "topaz" / "SUBWTA.ARC",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing required subwta raster for {run.run_id}: {candidates}")


def _copy_run_inputs(run: RunSpec, dst_root: Path) -> tuple[Path, Path, Path, bool]:
    subwta_src = _resolve_subwta_source(run)
    mofe_src = run.root / "watershed" / "mofe.tif"
    landuse_src = run.root / "landuse.nodb"

    for required in (subwta_src, landuse_src):
        if not required.exists():
            raise FileNotFoundError(f"Missing required run input for {run.run_id}: {required}")

    subwta_dst = dst_root / subwta_src.name
    mofe_dst = dst_root / "mofe.tif"
    landuse_dst = dst_root / "landuse.nodb"
    shutil.copy2(subwta_src, subwta_dst)
    shutil.copy2(landuse_src, landuse_dst)
    synthesized_mofe = False
    if mofe_src.exists():
        shutil.copy2(mofe_src, mofe_dst)
    else:
        _synthesize_single_ofe_map(subwta_dst, mofe_dst)
        synthesized_mofe = True
    return subwta_dst, mofe_dst, landuse_dst, synthesized_mofe


def _load_domlc_mofe_d(path: Path) -> tuple[dict[str, dict[str, str]], bool]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    state = payload.get("py/state")
    if not isinstance(state, dict):
        raise ValueError(f"Invalid NoDb payload (missing py/state): {path}")
    domlc_mofe_d = state.get("domlc_mofe_d")
    derived_from_domlc = False
    if not isinstance(domlc_mofe_d, dict):
        domlc_d = state.get("domlc_d")
        if not isinstance(domlc_d, dict):
            raise ValueError(f"Invalid NoDb payload (missing domlc_mofe_d and domlc_d): {path}")
        domlc_mofe_d = {str(topaz_id): {"1": str(management)} for topaz_id, management in domlc_d.items()}
        derived_from_domlc = True
    normalized: dict[str, dict[str, str]] = {}
    for topaz_id, ofe_map in domlc_mofe_d.items():
        if not isinstance(ofe_map, dict):
            raise ValueError(f"Invalid domlc_mofe_d entry for topaz_id={topaz_id}: {type(ofe_map)}")
        normalized[str(topaz_id)] = {str(ofe_id): str(management) for ofe_id, management in ofe_map.items()}
    return normalized, derived_from_domlc


def _cell_area_ha(path: Path) -> float:
    with rasterio.open(path) as src:
        transform: Affine = src.transform
    cellsize = abs(float(transform.a))
    return (cellsize * cellsize) / 10000.0


def _read_i32(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        band = src.read(1, masked=True)
        fill_value = src.nodata
        if fill_value is None or isinstance(fill_value, float) and math.isnan(fill_value):
            fill_value = 0
        filled = np.nan_to_num(
            band.filled(fill_value),
            nan=float(fill_value),
            posinf=float(fill_value),
            neginf=float(fill_value),
        )
        with np.errstate(invalid="ignore"):
            return filled.astype(np.int32, copy=False)


def _aggregate_from_numpy(
    subwta_path: Path,
    mofe_path: Path,
    domlc_mofe_d: dict[str, dict[str, str]],
    cell_area_ha: float,
) -> tuple[dict[str, float], dict[str, float], float, dict[str, int]]:
    subwta = _read_i32(subwta_path)
    mofe = _read_i32(mofe_path)
    if subwta.shape != mofe.shape:
        raise ValueError(f"subwta/mofe shape mismatch: {subwta.shape} vs {mofe.shape}")

    management_areas: dict[str, float] = {}
    pair_counts: dict[str, int] = {}
    total_area = 0.0

    for topaz_id, ofe_map in domlc_mofe_d.items():
        topaz_value = int(topaz_id)
        for ofe_id, management_key in ofe_map.items():
            ofe_value = int(ofe_id)
            count = int(np.where((subwta == topaz_value) & (mofe == ofe_value))[0].size)
            pair_counts[f"{topaz_id}:{ofe_id}"] = count
            area = float(count) * cell_area_ha
            management_areas[management_key] = management_areas.get(management_key, 0.0) + area
            total_area += area

    management_pcts = {
        key: ((100.0 * area / total_area) if total_area else math.nan)
        for key, area in management_areas.items()
    }
    return management_areas, management_pcts, total_area, pair_counts


def _aggregate_from_rust(
    subwta_path: Path,
    mofe_path: Path,
    domlc_mofe_d: dict[str, dict[str, str]],
    cell_area_ha: float,
) -> tuple[dict[str, float], dict[str, float], float, dict[str, int]]:
    pair_counts_raw = count_intersecting_raster_key_pairs(
        key_fn=str(subwta_path),
        key2_fn=str(mofe_path),
        ignore_channels=False,
        ignore_keys=None,
        ignore_keys2=None,
    )

    management_areas: dict[str, float] = {}
    pair_counts: dict[str, int] = {}
    total_area = 0.0

    for topaz_id, ofe_map in domlc_mofe_d.items():
        topaz_counts = pair_counts_raw.get(str(topaz_id), {})
        for ofe_id, management_key in ofe_map.items():
            count = int(topaz_counts.get(str(ofe_id), 0))
            pair_counts[f"{topaz_id}:{ofe_id}"] = count
            area = float(count) * cell_area_ha
            management_areas[management_key] = management_areas.get(management_key, 0.0) + area
            total_area += area

    management_pcts = {
        key: ((100.0 * area / total_area) if total_area else math.nan)
        for key, area in management_areas.items()
    }
    return management_areas, management_pcts, total_area, pair_counts


def _timed_call(fn: Any, *args: Any) -> tuple[float, Any]:
    start = time.perf_counter()
    result = fn(*args)
    elapsed = time.perf_counter() - start
    return elapsed, result


def _build_benchmark_summary(benchmark_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Benchmark Summary")
    lines.append("")
    lines.append(f"- Generated (UTC): {benchmark_raw['generated_at_utc']}")
    lines.append(f"- Iterations per method: {benchmark_raw['iterations_per_method']}")
    lines.append("")
    lines.append(
        "| Run | Baseline Mean (s) | Baseline Std (s) | Rust Mean (s) | Rust Std (s) | Delta % |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for run in benchmark_raw["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['baseline_mean_s']:.6f} | {run['baseline_std_s']:.6f} | "
            f"{run['rust_mean_s']:.6f} | {run['rust_std_s']:.6f} | {run['delta_pct']:.2f}% |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_parity_notes(parity_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Parity Notes")
    lines.append("")
    lines.append(f"- Generated (UTC): {parity_raw['generated_at_utc']}")
    lines.append("")
    lines.append(
        "| Run | Pair Mismatches | Area Mismatches | Pct Mismatches | Total Area Match | Status |"
    )
    lines.append("| --- | ---: | ---: | ---: | :---: | --- |")
    for run in parity_raw["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['pair_count_mismatch_count']} | {run['area_mismatch_count']} | "
            f"{run['pct_mismatch_count']} | {'yes' if run['total_area_match'] else 'no'} | {run['status']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    benchmark_runs: list[dict[str, Any]] = []
    parity_runs: list[dict[str, Any]] = []

    for run in RUN_SPECS:
        with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-pair-count-") as tmpdir:
            temp_root = Path(tmpdir)
            subwta_path, mofe_path, landuse_path, synthesized_mofe = _copy_run_inputs(run, temp_root)
            domlc_mofe_d, derived_domlc_pairs = _load_domlc_mofe_d(landuse_path)
            cell_area_ha = _cell_area_ha(subwta_path)

            # Benchmark with alternating call order to reduce warm-cache bias.
            baseline_samples: list[float] = []
            rust_samples: list[float] = []
            for index in range(BENCHMARK_ITERATIONS):
                if index % 2 == 0:
                    order = ("baseline", "rust")
                else:
                    order = ("rust", "baseline")

                for label in order:
                    if label == "baseline":
                        elapsed, _ = _timed_call(
                            _aggregate_from_numpy,
                            subwta_path,
                            mofe_path,
                            domlc_mofe_d,
                            cell_area_ha,
                        )
                        baseline_samples.append(elapsed)
                    else:
                        elapsed, _ = _timed_call(
                            _aggregate_from_rust,
                            subwta_path,
                            mofe_path,
                            domlc_mofe_d,
                            cell_area_ha,
                        )
                        rust_samples.append(elapsed)

            baseline_areas, baseline_pcts, baseline_total, baseline_pair_counts = _aggregate_from_numpy(
                subwta_path, mofe_path, domlc_mofe_d, cell_area_ha
            )
            rust_areas, rust_pcts, rust_total, rust_pair_counts = _aggregate_from_rust(
                subwta_path, mofe_path, domlc_mofe_d, cell_area_ha
            )

            area_mismatches: list[dict[str, Any]] = []
            for key in sorted(set(baseline_areas) | set(rust_areas)):
                base_value = float(baseline_areas.get(key, 0.0))
                rust_value = float(rust_areas.get(key, 0.0))
                if abs(base_value - rust_value) > ABS_TOL:
                    area_mismatches.append(
                        {
                            "management": key,
                            "baseline": base_value,
                            "rust": rust_value,
                            "delta": rust_value - base_value,
                        }
                    )

            pct_mismatches: list[dict[str, Any]] = []
            for key in sorted(set(baseline_pcts) | set(rust_pcts)):
                base_value = float(baseline_pcts.get(key, math.nan))
                rust_value = float(rust_pcts.get(key, math.nan))
                both_nan = math.isnan(base_value) and math.isnan(rust_value)
                if not both_nan and abs(base_value - rust_value) > ABS_TOL:
                    pct_mismatches.append(
                        {
                            "management": key,
                            "baseline": base_value,
                            "rust": rust_value,
                            "delta": rust_value - base_value,
                        }
                    )

            pair_mismatches: list[dict[str, Any]] = []
            for pair_key in sorted(set(baseline_pair_counts) | set(rust_pair_counts)):
                base_value = int(baseline_pair_counts.get(pair_key, 0))
                rust_value = int(rust_pair_counts.get(pair_key, 0))
                if base_value != rust_value:
                    pair_mismatches.append(
                        {
                            "pair": pair_key,
                            "baseline": base_value,
                            "rust": rust_value,
                            "delta": rust_value - base_value,
                        }
                    )

            baseline_mean = _mean(baseline_samples)
            rust_mean = _mean(rust_samples)
            delta_pct = ((rust_mean - baseline_mean) / baseline_mean * 100.0) if baseline_mean else math.nan

            benchmark_runs.append(
                {
                    "run_id": run.run_id,
                    "url": run.url,
                    "local_root": str(run.root),
                    "temp_root": str(temp_root),
                    "synthesized_mofe_map": synthesized_mofe,
                    "derived_domlc_pairs": derived_domlc_pairs,
                    "iterations": BENCHMARK_ITERATIONS,
                    "pair_count": sum(len(v) for v in domlc_mofe_d.values()),
                    "management_count": len({m for ofe_map in domlc_mofe_d.values() for m in ofe_map.values()}),
                    "baseline_samples_s": baseline_samples,
                    "baseline_mean_s": baseline_mean,
                    "baseline_std_s": _stddev(baseline_samples),
                    "rust_samples_s": rust_samples,
                    "rust_mean_s": rust_mean,
                    "rust_std_s": _stddev(rust_samples),
                    "delta_pct": delta_pct,
                }
            )

            parity_runs.append(
                {
                    "run_id": run.run_id,
                    "url": run.url,
                    "local_root": str(run.root),
                    "synthesized_mofe_map": synthesized_mofe,
                    "derived_domlc_pairs": derived_domlc_pairs,
                    "pair_count": sum(len(v) for v in domlc_mofe_d.values()),
                    "pair_count_mismatch_count": len(pair_mismatches),
                    "pair_count_mismatches": pair_mismatches[:20],
                    "area_mismatch_count": len(area_mismatches),
                    "area_mismatches": area_mismatches[:20],
                    "pct_mismatch_count": len(pct_mismatches),
                    "pct_mismatches": pct_mismatches[:20],
                    "baseline_total_area_ha": baseline_total,
                    "rust_total_area_ha": rust_total,
                    "total_area_match": abs(rust_total - baseline_total) <= ABS_TOL,
                    "status": "match"
                    if (
                        len(pair_mismatches) == 0
                        and len(area_mismatches) == 0
                        and len(pct_mismatches) == 0
                        and abs(rust_total - baseline_total) <= ABS_TOL
                    )
                    else "mismatch",
                }
            )

    benchmark_raw = {
        "generated_at_utc": _utc_now_iso(),
        "iterations_per_method": BENCHMARK_ITERATIONS,
        "runs": benchmark_runs,
    }
    parity_raw = {
        "generated_at_utc": _utc_now_iso(),
        "runs": parity_runs,
    }

    BENCHMARK_RAW_PATH.write_text(json.dumps(benchmark_raw, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    PARITY_RAW_PATH.write_text(json.dumps(parity_raw, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    BENCHMARK_SUMMARY_PATH.write_text(_build_benchmark_summary(benchmark_raw), encoding="utf-8")
    PARITY_NOTES_PATH.write_text(_build_parity_notes(parity_raw), encoding="utf-8")


if __name__ == "__main__":
    main()
