from __future__ import annotations

import contextlib
import json
import logging
import math
import os
import shutil
import statistics
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import rasterio

from wepppy.nodb.core.landuse import Landuse
import wepppy.nodb.core.landuse as landuse_module


PACKAGE_ROOT = Path(
    "/workdir/wepppy/docs/work-packages/20260423_mofe_man_synthesis_process_pool"
)
DEFAULT_ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
ARTIFACTS_DIR = Path(os.getenv("MOFE_BENCH_ARTIFACTS_DIR", str(DEFAULT_ARTIFACTS_DIR)))
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


BENCHMARK_ITERATIONS = _env_int("MOFE_BENCH_ITERATIONS", 3)
BASELINE_CPU_COUNT = _env_int("MOFE_BENCH_BASELINE_CPU_COUNT", 1)
PARALLEL_CPU_COUNT = _env_int(
    "MOFE_BENCH_PARALLEL_CPU_COUNT",
    min(
        max(1, os.cpu_count() or 1),
        getattr(landuse_module, "_MOFE_MAN_SYNTH_MAX_WORKERS", max(1, os.cpu_count() or 1)),
    ),
)


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
    raw = os.getenv("MOFE_BENCH_RUN_IDS")
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


def _resolve_subwta_source(run: RunSpec) -> Path:
    candidates = [
        run.root / "dem" / "wbt" / "subwta.tif",
        run.root / "dem" / "topaz" / "SUBWTA.ARC",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing required subwta raster for {run.run_id}: {candidates}")


def _synthesize_single_ofe_map(subwta_path: Path, mofe_path: Path) -> None:
    with rasterio.open(subwta_path) as src:
        profile = src.profile.copy()
        width = src.width
        height = src.height

    profile.update(dtype="int32", count=1, nodata=0)
    data = np.ones((height, width), dtype=np.int32)
    with rasterio.open(mofe_path, "w", **profile) as dst:
        dst.write(data, 1)


def _prepare_temp_run(run: RunSpec, dst_root: Path) -> Path:
    run_dst = dst_root / run.run_id
    run_dst.mkdir(parents=True, exist_ok=True)

    for child in run.root.iterdir():
        if child.is_file():
            shutil.copy2(child, run_dst / child.name)

    for child in run.root.iterdir():
        if not child.is_dir() or child.name in {"landuse", "watershed"}:
            continue
        os.symlink(child, run_dst / child.name, target_is_directory=True)

    landuse_dst = run_dst / "landuse"
    landuse_dst.mkdir(exist_ok=True)
    source_landuse = run.root / "landuse"
    for child in source_landuse.iterdir():
        if child.name.startswith("hill_") and child.name.endswith(".mofe.man"):
            continue
        os.symlink(child, landuse_dst / child.name, target_is_directory=child.is_dir())

    watershed_dst = run_dst / "watershed"
    watershed_dst.mkdir(exist_ok=True)
    source_watershed = run.root / "watershed"
    if source_watershed.exists():
        for child in source_watershed.iterdir():
            os.symlink(child, watershed_dst / child.name, target_is_directory=child.is_dir())

    return run_dst


@contextlib.contextmanager
def _patched_cpu_count(target: int) -> Iterator[None]:
    original = landuse_module.os.cpu_count
    landuse_module.os.cpu_count = lambda: target
    try:
        yield
    finally:
        landuse_module.os.cpu_count = original


def _mute_logger(logger: logging.Logger | None) -> None:
    if logger is None:
        return
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False


def _build_outputs(
    run_root: Path,
    *,
    cpu_count: int,
) -> tuple[float, int, int, bool]:
    landuse = Landuse.getInstance(str(run_root))
    landuse.locked = lambda *args, **kwargs: contextlib.nullcontext()
    _mute_logger(getattr(landuse, "logger", None))
    _mute_logger(getattr(landuse, "runid_logger", None))

    watershed = landuse.watershed_instance
    _mute_logger(getattr(watershed, "logger", None))
    _mute_logger(getattr(watershed, "runid_logger", None))

    synthetic_single_ofe = False
    mofe_map_path = Path(watershed.mofe_map)
    if not mofe_map_path.exists():
        mofe_map_path.parent.mkdir(parents=True, exist_ok=True)
        _synthesize_single_ofe_map(Path(watershed.subwta), mofe_map_path)
        watershed._mofe_nsegments = {str(topaz_id): 1 for topaz_id in watershed._subs_summary}
        synthetic_single_ofe = True

    with _patched_cpu_count(cpu_count):
        start = time.perf_counter()
        landuse._build_multiple_ofe()
        elapsed = time.perf_counter() - start

    output_files = list((run_root / "landuse").glob("hill_*.mofe.man"))
    return elapsed, len(output_files), len(watershed._subs_summary), synthetic_single_ofe


def _collect_outputs(run_root: Path) -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted((run_root / "landuse").glob("hill_*.mofe.man"))
    }


def _compare_outputs(
    baseline_outputs: dict[str, str],
    concurrent_outputs: dict[str, str],
) -> dict[str, Any]:
    baseline_names = set(baseline_outputs)
    concurrent_names = set(concurrent_outputs)
    missing_in_baseline = sorted(concurrent_names - baseline_names)
    missing_in_concurrent = sorted(baseline_names - concurrent_names)

    mismatches: list[dict[str, Any]] = []
    for name in sorted(baseline_names & concurrent_names):
        baseline_text = baseline_outputs[name]
        concurrent_text = concurrent_outputs[name]
        if baseline_text == concurrent_text:
            continue
        mismatches.append(
            {
                "file": name,
                "baseline_length": len(baseline_text),
                "concurrent_length": len(concurrent_text),
            }
        )

    mismatch_count = (
        len(missing_in_baseline) + len(missing_in_concurrent) + len(mismatches)
    )
    return {
        "baseline_file_count": len(baseline_outputs),
        "concurrent_file_count": len(concurrent_outputs),
        "missing_in_baseline": missing_in_baseline,
        "missing_in_concurrent": missing_in_concurrent,
        "content_mismatch_count": len(mismatches),
        "content_mismatches": mismatches[:20],
        "mismatch_count": mismatch_count,
        "status": "match" if mismatch_count == 0 else "mismatch",
    }


def _build_benchmark_summary(benchmark_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MOFE `.mofe.man` Synthesis Benchmark")
    lines.append("")
    lines.append(f"- Generated (UTC): {benchmark_raw['generated_at_utc']}")
    lines.append(
        f"- Baseline mode: forced sequential (`cpu_count={benchmark_raw['baseline_cpu_count']}`), "
        "matching pre-migration single-process behavior."
    )
    lines.append(
        f"- Concurrent mode: canonical process-pool path (`cpu_count={benchmark_raw['parallel_cpu_count']}`), "
        "matching the bounded MOFE synthesis worker cap in production."
    )
    lines.append(f"- Iterations per mode: {benchmark_raw['iterations_per_mode']}")
    lines.append("")
    lines.append(
        "| Run | Baseline Mean (s) | Baseline Std (s) | Concurrent Mean (s) | Concurrent Std (s) | Delta % | Notes |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for run in benchmark_raw["runs"]:
        note = "synthetic single-OFE MOFE map" if run["synthetic_single_ofe_adaptation"] else "match"
        lines.append(
            f"| `{run['run_id']}` | {run['baseline_mean_s']:.6f} | {run['baseline_std_s']:.6f} | "
            f"{run['concurrent_mean_s']:.6f} | {run['concurrent_std_s']:.6f} | {run['delta_pct']:.2f}% | {note} |"
        )
    lines.append("")
    lines.append("Raw machine-readable data: `artifacts/benchmark_raw.json`")
    lines.append("")
    return "\n".join(lines)


def _build_parity_notes(parity_raw: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MOFE `.mofe.man` Synthesis Parity Notes")
    lines.append("")
    lines.append(f"- Generated (UTC): {parity_raw['generated_at_utc']}")
    lines.append(
        f"- Baseline mode: forced sequential (`cpu_count={parity_raw['baseline_cpu_count']}`), "
        "used as the pre-migration parity oracle."
    )
    lines.append(
        f"- Concurrent mode: canonical process-pool path (`cpu_count={parity_raw['parallel_cpu_count']}`), "
        "matching the bounded MOFE synthesis worker cap in production."
    )
    lines.append("")
    lines.append(
        "| Run | Files (Baseline/Concurrent) | Mismatches | Synthetic MOFE Adaptation | Status |"
    )
    lines.append("| --- | ---: | ---: | :---: | --- |")
    for run in parity_raw["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['baseline_file_count']}/{run['concurrent_file_count']} | "
            f"{run['mismatch_count']} | "
            f"{'yes' if run['synthetic_single_ofe_adaptation'] else 'no'} | {run['status']} |"
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
        concurrent_samples: list[float] = []
        benchmark_synthetic = False
        hillslope_count = 0
        output_file_count = 0

        for iteration in range(BENCHMARK_ITERATIONS):
            order = ("baseline", "concurrent") if iteration % 2 == 0 else ("concurrent", "baseline")
            for mode in order:
                with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-{mode}-bench-") as tmpdir:
                    run_root = _prepare_temp_run(run, Path(tmpdir))
                    elapsed, output_files, hillslopes, synthetic = _build_outputs(
                        run_root,
                        cpu_count=BASELINE_CPU_COUNT if mode == "baseline" else PARALLEL_CPU_COUNT,
                    )
                    benchmark_synthetic = benchmark_synthetic or synthetic
                    hillslope_count = hillslopes
                    output_file_count = output_files
                    if mode == "baseline":
                        baseline_samples.append(elapsed)
                    else:
                        concurrent_samples.append(elapsed)

        baseline_mean = _mean(baseline_samples)
        concurrent_mean = _mean(concurrent_samples)
        delta_pct = (
            ((concurrent_mean - baseline_mean) / baseline_mean) * 100.0
            if baseline_mean
            else math.nan
        )

        with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-baseline-parity-") as baseline_tmp:
            baseline_root = _prepare_temp_run(run, Path(baseline_tmp))
            _elapsed, _output_files, _hillslopes, baseline_synthetic = _build_outputs(
                baseline_root,
                cpu_count=BASELINE_CPU_COUNT,
            )
            baseline_outputs = _collect_outputs(baseline_root)

        with tempfile.TemporaryDirectory(prefix=f"{run.run_id}-concurrent-parity-") as concurrent_tmp:
            concurrent_root = _prepare_temp_run(run, Path(concurrent_tmp))
            _elapsed, _output_files, _hillslopes, concurrent_synthetic = _build_outputs(
                concurrent_root,
                cpu_count=PARALLEL_CPU_COUNT,
            )
            concurrent_outputs = _collect_outputs(concurrent_root)

        parity_result = _compare_outputs(baseline_outputs, concurrent_outputs)
        synthetic_single_ofe = benchmark_synthetic or baseline_synthetic or concurrent_synthetic

        benchmark_runs.append(
            {
                "run_id": run.run_id,
                "url": run.url,
                "local_root": str(run.root),
                "synthetic_single_ofe_adaptation": synthetic_single_ofe,
                "hillslope_count": hillslope_count,
                "output_file_count": output_file_count,
                "baseline_samples_s": baseline_samples,
                "baseline_mean_s": baseline_mean,
                "baseline_std_s": _stddev(baseline_samples),
                "concurrent_samples_s": concurrent_samples,
                "concurrent_mean_s": concurrent_mean,
                "concurrent_std_s": _stddev(concurrent_samples),
                "delta_pct": delta_pct,
            }
        )

        parity_runs.append(
            {
                "run_id": run.run_id,
                "url": run.url,
                "local_root": str(run.root),
                "synthetic_single_ofe_adaptation": synthetic_single_ofe,
                **parity_result,
            }
        )

    benchmark_raw = {
        "generated_at_utc": _utc_now_iso(),
        "iterations_per_mode": BENCHMARK_ITERATIONS,
        "baseline_cpu_count": BASELINE_CPU_COUNT,
        "parallel_cpu_count": PARALLEL_CPU_COUNT,
        "runs": benchmark_runs,
    }
    parity_raw = {
        "generated_at_utc": _utc_now_iso(),
        "baseline_cpu_count": BASELINE_CPU_COUNT,
        "parallel_cpu_count": PARALLEL_CPU_COUNT,
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
