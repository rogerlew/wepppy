from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import shutil
import statistics
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio

from wepppy.nodb.core.landuse import Landuse


PACKAGE_ROOT = Path(
    "/workdir/wepppy/docs/work-packages/20260423_landuse_multi_ofe_build_optimization"
)
DEFAULT_ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
ARTIFACTS_DIR = Path(os.getenv("LANDUSE_MULTI_OFE_BENCH_ARTIFACTS_DIR", str(DEFAULT_ARTIFACTS_DIR)))
BENCHMARK_RAW_PATH = ARTIFACTS_DIR / "benchmark_raw.json"
BENCHMARK_SUMMARY_PATH = ARTIFACTS_DIR / "benchmark_summary.md"
PARITY_RAW_PATH = ARTIFACTS_DIR / "parity_raw.json"
PARITY_NOTES_PATH = ARTIFACTS_DIR / "parity_notes.md"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be >= 1; got {value}")
    return value


BENCHMARK_ITERATIONS = _env_int("LANDUSE_MULTI_OFE_BENCH_ITERATIONS", 2)
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

RUN_SPECS_BY_ID = {run.run_id: run for run in RUN_SPECS}


def _selected_runs() -> list[RunSpec]:
    raw = os.getenv("LANDUSE_MULTI_OFE_BENCH_RUN_IDS")
    if not raw:
        return RUN_SPECS

    selected_ids = [run_id.strip() for run_id in raw.split(",") if run_id.strip()]
    missing = [run_id for run_id in selected_ids if run_id not in RUN_SPECS_BY_ID]
    if missing:
        raise ValueError(f"Unknown run id(s): {missing}")
    return [RUN_SPECS_BY_ID[run_id] for run_id in selected_ids]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mean(values: list[float]) -> float:
    return statistics.mean(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _copy_landuse_tree(source: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    for child in source.iterdir():
        target = dest / child.name
        if child.is_dir():
            shutil.copytree(child, target, symlinks=False)
        else:
            shutil.copy2(child, target)


def _prepare_temp_run(run: RunSpec, dst_root: Path) -> Path:
    run_dst = dst_root / run.run_id
    run_dst.mkdir(parents=True, exist_ok=True)

    for child in run.root.iterdir():
        if child.is_file():
            shutil.copy2(child, run_dst / child.name)

    for child in run.root.iterdir():
        if not child.is_dir() or child.name == "landuse":
            continue
        os.symlink(child, run_dst / child.name, target_is_directory=True)

    _copy_landuse_tree(run.root / "landuse", run_dst / "landuse")
    return run_dst


def _mute_logger(logger: Any) -> None:
    if logger is None:
        return
    with contextlib.suppress(Exception):
        logger.info = lambda *args, **kwargs: None
    with contextlib.suppress(Exception):
        logger.debug = lambda *args, **kwargs: None
    with contextlib.suppress(Exception):
        logger.setLevel(100)
    with contextlib.suppress(Exception):
        logger.propagate = False


def _synthesize_single_ofe_map(subwta_path: Path, mofe_path: Path) -> None:
    with rasterio.open(subwta_path) as src:
        profile = src.profile.copy()
        width = src.width
        height = src.height

    profile.update(dtype="int32", count=1, nodata=0)
    data = np.ones((height, width), dtype=np.int32)
    mofe_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(mofe_path, "w", **profile) as dst:
        dst.write(data, 1)


def _prepare_landuse_controller(run_root: Path) -> Landuse:
    landuse = Landuse.getInstance(str(run_root))
    landuse.locked = lambda *args, **kwargs: contextlib.nullcontext()
    landuse.trigger = lambda *_args, **_kwargs: None
    _mute_logger(getattr(landuse, "logger", None))
    _mute_logger(getattr(landuse, "runid_logger", None))

    watershed = landuse.watershed_instance
    _mute_logger(getattr(watershed, "logger", None))
    _mute_logger(getattr(watershed, "runid_logger", None))

    mofe_path = Path(watershed.mofe_map)
    if not mofe_path.exists():
        subwta_path = Path(watershed.subwta)
        if not subwta_path.exists():
            raise FileNotFoundError(
                f"Cannot synthesize MOFE map for {run_root}: missing subwta raster {subwta_path}"
            )
        _synthesize_single_ofe_map(subwta_path, mofe_path)
        synthetic_segments = {str(topaz_id): 1 for topaz_id in watershed._subs_summary}
        watershed._mofe_nsegments = synthetic_segments

    if getattr(watershed, "_mofe_nsegments", None) is None:
        domlc_mofe_d = getattr(landuse, "domlc_mofe_d", None)
        if isinstance(domlc_mofe_d, dict) and domlc_mofe_d:
            watershed._mofe_nsegments = {
                str(topaz_id): len(ofe_map)
                for topaz_id, ofe_map in domlc_mofe_d.items()
            }
        else:
            watershed._mofe_nsegments = {
                str(topaz_id): 1 for topaz_id in watershed._subs_summary
            }

    return landuse


def _run_legacy_orchestration(run_root: Path) -> tuple[float, dict[str, Any]]:
    landuse = _prepare_landuse_controller(run_root)

    start = time.perf_counter()
    landuse.build_managements()
    landuse._build_multiple_ofe()
    landuse.build_managements()
    elapsed = time.perf_counter() - start

    return elapsed, _collect_state_signature(run_root, landuse)


def _run_optimized_orchestration(run_root: Path) -> tuple[float, dict[str, Any]]:
    landuse = _prepare_landuse_controller(run_root)
    landuse.domlc_mofe_d = None

    start = time.perf_counter()
    landuse._build_multiple_ofe()
    landuse.build_managements()
    elapsed = time.perf_counter() - start

    return elapsed, _collect_state_signature(run_root, landuse)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, dict):
        return {str(k): _normalize_json_value(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(v) for v in value]

    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return value


def _parquet_semantic_signature(path: Path) -> str:
    table = pd.read_parquet(path)
    records = table.to_dict(orient="records")
    normalized_records = [_normalize_json_value(record) for record in records]
    normalized_records.sort(
        key=lambda record: json.dumps(record, sort_keys=True, separators=(",", ":"))
    )
    payload = json.dumps(normalized_records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _management_signature(landuse: Landuse) -> dict[str, dict[str, float]]:
    signature: dict[str, dict[str, float]] = {}
    for key, summary in sorted(landuse.managements.items(), key=lambda item: str(item[0])):
        area = float(getattr(summary, "area", 0.0) or 0.0)
        pct = float(getattr(summary, "pct_coverage", 0.0) or 0.0)
        signature[str(key)] = {
            "area": round(area, 12),
            "pct_coverage": round(pct, 12),
        }
    return signature


def _collect_state_signature(run_root: Path, landuse: Landuse) -> dict[str, Any]:
    landuse_dir = run_root / "landuse"
    managed_files = sorted(landuse_dir.glob("hill_*.mofe.man"))
    parquet_path = landuse_dir / "landuse.parquet"
    parquet_signature = _parquet_semantic_signature(parquet_path) if parquet_path.exists() else None

    domlc_mofe_d = getattr(landuse, "domlc_mofe_d", {}) or {}
    normalized_domlc_mofe_d = {
        str(topaz_id): {
            str(ofe_id): str(dom)
            for ofe_id, dom in sorted(ofe_map.items(), key=lambda item: int(str(item[0])))
        }
        for topaz_id, ofe_map in sorted(domlc_mofe_d.items(), key=lambda item: int(str(item[0])))
    }

    return {
        "parquet_signature": parquet_signature,
        "mofe_man_files": {
            path.name: _hash_file(path) for path in managed_files
        },
        "managements": _management_signature(landuse),
        "domlc_mofe_d": normalized_domlc_mofe_d,
    }


def _compare_signatures(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    parquet_match = baseline["parquet_signature"] == optimized["parquet_signature"]

    baseline_files = baseline["mofe_man_files"]
    optimized_files = optimized["mofe_man_files"]
    missing_in_baseline = sorted(set(optimized_files) - set(baseline_files))
    missing_in_optimized = sorted(set(baseline_files) - set(optimized_files))
    file_hash_mismatches = [
        name
        for name in sorted(set(baseline_files) & set(optimized_files))
        if baseline_files[name] != optimized_files[name]
    ]
    file_mismatch_count = (
        len(missing_in_baseline)
        + len(missing_in_optimized)
        + len(file_hash_mismatches)
    )

    baseline_mgmt = baseline["managements"]
    optimized_mgmt = optimized["managements"]
    mgmt_keys = sorted(set(baseline_mgmt) | set(optimized_mgmt))
    mgmt_area_mismatches: list[dict[str, Any]] = []
    mgmt_pct_mismatches: list[dict[str, Any]] = []
    for key in mgmt_keys:
        base_values = baseline_mgmt.get(key, {"area": 0.0, "pct_coverage": 0.0})
        opt_values = optimized_mgmt.get(key, {"area": 0.0, "pct_coverage": 0.0})

        base_area = float(base_values["area"])
        opt_area = float(opt_values["area"])
        if abs(base_area - opt_area) > ABS_TOL:
            mgmt_area_mismatches.append(
                {
                    "management": key,
                    "baseline": base_area,
                    "optimized": opt_area,
                    "delta": opt_area - base_area,
                }
            )

        base_pct = float(base_values["pct_coverage"])
        opt_pct = float(opt_values["pct_coverage"])
        if abs(base_pct - opt_pct) > ABS_TOL:
            mgmt_pct_mismatches.append(
                {
                    "management": key,
                    "baseline": base_pct,
                    "optimized": opt_pct,
                    "delta": opt_pct - base_pct,
                }
            )

    domlc_mofe_match = baseline["domlc_mofe_d"] == optimized["domlc_mofe_d"]
    core_match = (
        file_mismatch_count == 0
        and not mgmt_area_mismatches
        and not mgmt_pct_mismatches
        and domlc_mofe_match
    )

    return {
        "parquet_match": parquet_match,
        "mofe_file_mismatch_count": file_mismatch_count,
        "missing_mofe_files_in_baseline": missing_in_baseline,
        "missing_mofe_files_in_optimized": missing_in_optimized,
        "mofe_file_hash_mismatches": file_hash_mismatches[:20],
        "management_area_mismatch_count": len(mgmt_area_mismatches),
        "management_area_mismatches": mgmt_area_mismatches[:20],
        "management_pct_mismatch_count": len(mgmt_pct_mismatches),
        "management_pct_mismatches": mgmt_pct_mismatches[:20],
        "domlc_mofe_match": domlc_mofe_match,
        "status": "match" if core_match else "mismatch",
        "parquet_variance_only": bool(core_match and not parquet_match),
    }


def _build_benchmark_summary(benchmark_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Landuse Multi-OFE Build Benchmark Summary")
    lines.append("")
    lines.append(f"- Generated (UTC): {benchmark_raw['generated_at_utc']}")
    lines.append(f"- Iterations per mode: {benchmark_raw['iterations_per_mode']}")
    lines.append("- Baseline mode: legacy orchestration emulation (`build_managements` -> `_build_multiple_ofe` -> `build_managements`).")
    lines.append("- Optimized mode: current orchestration (`domlc_mofe_d=None` -> `_build_multiple_ofe` -> `build_managements`).")
    lines.append("")
    lines.append(
        "| Run | Baseline Mean (s) | Baseline Std (s) | Optimized Mean (s) | Optimized Std (s) | Delta % |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for run in benchmark_raw["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['baseline_mean_s']:.6f} | {run['baseline_std_s']:.6f} | "
            f"{run['optimized_mean_s']:.6f} | {run['optimized_std_s']:.6f} | {run['delta_pct']:.2f}% |"
        )
    lines.append("")
    lines.append("Raw machine-readable data: `artifacts/benchmark_raw.json`")
    lines.append("")
    return "\n".join(lines)


def _build_parity_notes(parity_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Landuse Multi-OFE Build Parity Notes")
    lines.append("")
    lines.append(f"- Generated (UTC): {parity_raw['generated_at_utc']}")
    lines.append("- Baseline mode: legacy orchestration emulation with duplicate management build pass.")
    lines.append("- Optimized mode: duplicate-pass collapsed orchestration.")
    lines.append("- Parity status is based on MOFE management files, management area/coverage values, and DOMLC_MOFE assignments.")
    lines.append("- `Parquet Match` is reported for observability; row-level semantics may match even when file-level signatures vary.")
    lines.append("")
    lines.append(
        "| Run | MOFE File Mismatches | Mgmt Area Mismatches | Mgmt Pct Mismatches | Parquet Match | DOMLC_MOFE Match | Status |"
    )
    lines.append("| --- | ---: | ---: | ---: | :---: | :---: | --- |")
    for run in parity_raw["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['mofe_file_mismatch_count']} | "
            f"{run['management_area_mismatch_count']} | {run['management_pct_mismatch_count']} | "
            f"{'yes' if run['parquet_match'] else 'no'} | {'yes' if run['domlc_mofe_match'] else 'no'} | "
            f"{run['status']} |"
        )
    lines.append("")
    lines.append("Raw machine-readable data: `artifacts/parity_raw.json`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    benchmark_runs: list[dict[str, Any]] = []
    parity_runs: list[dict[str, Any]] = []

    for run in _selected_runs():
        baseline_samples: list[float] = []
        optimized_samples: list[float] = []

        for iteration in range(BENCHMARK_ITERATIONS):
            order = ("baseline", "optimized") if iteration % 2 == 0 else ("optimized", "baseline")
            for mode in order:
                with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-{mode}-bench-") as tmpdir:
                    run_root = _prepare_temp_run(run, Path(tmpdir))
                    if mode == "baseline":
                        elapsed, _ = _run_legacy_orchestration(run_root)
                        baseline_samples.append(elapsed)
                    else:
                        elapsed, _ = _run_optimized_orchestration(run_root)
                        optimized_samples.append(elapsed)

        baseline_mean = _mean(baseline_samples)
        optimized_mean = _mean(optimized_samples)
        delta_pct = (
            ((optimized_mean - baseline_mean) / baseline_mean) * 100.0
            if baseline_mean
            else math.nan
        )

        with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-baseline-parity-") as baseline_tmp:
            baseline_root = _prepare_temp_run(run, Path(baseline_tmp))
            _elapsed, baseline_signature = _run_legacy_orchestration(baseline_root)

        with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-optimized-parity-") as optimized_tmp:
            optimized_root = _prepare_temp_run(run, Path(optimized_tmp))
            _elapsed, optimized_signature = _run_optimized_orchestration(optimized_root)

        parity_result = _compare_signatures(baseline_signature, optimized_signature)

        benchmark_runs.append(
            {
                "run_id": run.run_id,
                "url": run.url,
                "local_root": str(run.root),
                "iterations": BENCHMARK_ITERATIONS,
                "baseline_samples_s": baseline_samples,
                "baseline_mean_s": baseline_mean,
                "baseline_std_s": _stddev(baseline_samples),
                "optimized_samples_s": optimized_samples,
                "optimized_mean_s": optimized_mean,
                "optimized_std_s": _stddev(optimized_samples),
                "delta_pct": delta_pct,
            }
        )

        parity_runs.append(
            {
                "run_id": run.run_id,
                "url": run.url,
                "local_root": str(run.root),
                **parity_result,
            }
        )

    benchmark_raw = {
        "generated_at_utc": _utc_now_iso(),
        "iterations_per_mode": BENCHMARK_ITERATIONS,
        "runs": benchmark_runs,
    }
    parity_raw = {
        "generated_at_utc": _utc_now_iso(),
        "runs": parity_runs,
    }

    BENCHMARK_RAW_PATH.write_text(
        json.dumps(benchmark_raw, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    PARITY_RAW_PATH.write_text(
        json.dumps(parity_raw, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    BENCHMARK_SUMMARY_PATH.write_text(
        _build_benchmark_summary(benchmark_raw),
        encoding="utf-8",
    )
    PARITY_NOTES_PATH.write_text(
        _build_parity_notes(parity_raw),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
