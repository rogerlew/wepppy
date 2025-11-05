#!/usr/bin/env python3
"""Benchmark NoDb controller setters against real run directories.

Copies project runs into a temporary workspace, loads the relevant NoDb
controllers, and measures the latency of selected attribute setters.

Usage (inside the wepppy repo with PYTHONPATH set):
    python tools/perf/benchmark_nodb_setters.py --profile us-small-wbt-daymet-rap-wepp

The script prints timing summaries (mean / median / p95 in milliseconds) for each
measured operation so performance regressions can be spotted easily.
"""
from __future__ import annotations

import argparse
import shutil
import statistics
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List

PROFILE_ROOT = Path("/workdir/wepppy-test-engine-data/profiles")


@dataclass
class BenchmarkResult:
    label: str
    samples: List[float]

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def p95(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = max(0, int(0.95 * (len(sorted_samples) - 1)))
        return sorted_samples[idx]

    def summary(self) -> str:
        if not self.samples:
            return f"{self.label:42s} skipped"
        return (
            f"{self.label:42s} mean={self.mean*1000:8.1f} ms "
            f"median={self.median*1000:8.1f} ms p95={self.p95*1000:8.1f} ms"
        )


@contextmanager
def temporary_run_copy(profile: str) -> Iterable[Path]:
    """Copy a profile run directory into a temporary workspace."""
    src = PROFILE_ROOT / profile / "run"
    if not src.exists():
        raise FileNotFoundError(f"Run directory not found for profile '{profile}': {src}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f"nodb-bench-{profile}-"))
    dest = temp_dir / "run"
    shutil.copytree(src, dest)
    try:
        yield dest
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def time_operation(label: str, func: Callable[[], None], repeats: int) -> BenchmarkResult:
    samples: List[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        samples.append(end - start)
    return BenchmarkResult(label, samples)


def benchmark_watershed_setters(
    run_dir: Path,
    repeats: int,
    include_heavy: bool,
) -> List[BenchmarkResult]:
    from wepppy.nodb.core.watershed import Watershed

    results: List[BenchmarkResult] = []

    Watershed._instances.clear()
    watershed = Watershed.getInstance(str(run_dir))

    try:
        watershed.logger.setLevel("ERROR")
    except Exception:
        pass

    if hasattr(watershed, "_wbt"):
        watershed._wbt = None  # type: ignore[attr-defined]

    def measure_attr(attr: str, value) -> None:
        results.append(
            time_operation(f"Watershed.{attr}", lambda: setattr(watershed, attr, value), repeats)
        )

    # Boolean toggles
    measure_attr("clip_hillslopes", watershed.clip_hillslopes)
    measure_attr("walk_flowpaths", watershed.walk_flowpaths)
    measure_attr("mofe_buffer", getattr(watershed, "mofe_buffer", False))
    measure_attr("bieger2015_widths", getattr(watershed, "bieger2015_widths", False))

    # Numeric setters
    measure_attr("clip_hillslope_length", watershed.clip_hillslope_length)
    measure_attr("mofe_target_length", getattr(watershed, "mofe_target_length", 300.0))
    measure_attr("mofe_buffer_length", getattr(watershed, "mofe_buffer_length", 0.0))

    # Outlet handling (if available)
    outlet = watershed.outlet
    if include_heavy and outlet is not None:
        lng, lat = outlet.actual_loc
        results.append(
            time_operation(
                "Watershed.set_outlet",
                lambda: watershed.set_outlet(lng, lat),
                repeats,
            )
        )
    else:
        results.append(BenchmarkResult("Watershed.set_outlet", []))

    # Subcatchment build (expensive; run fewer times)
    if include_heavy:
        def build_subcatchments_once() -> None:
            watershed.build_subcatchments()

        results.append(
            time_operation(
                "Watershed.build_subcatchments",
                build_subcatchments_once,
                max(1, repeats // 3),
            )
        )
    else:
        results.append(BenchmarkResult("Watershed.build_subcatchments", []))

    return results


def format_heading(title: str) -> str:
    bar = "=" * len(title)
    return f"\n{title}\n{bar}"


def run_benchmark(profiles: List[str], repeats: int, include_heavy: bool) -> None:
    print(format_heading("NoDb Setter Benchmark"))
    print(f"Profiles: {', '.join(profiles)}")
    print(f"Repeats per operation: {repeats}\n")

    for profile in profiles:
        print(format_heading(f"Profile: {profile}"))
        with temporary_run_copy(profile) as run_dir:
            results = benchmark_watershed_setters(run_dir, repeats, include_heavy)

        for result in results:
            print(result.summary())
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark NoDb setters using real run data")
    parser.add_argument(
        "--profile",
        action="append",
        dest="profiles",
        help="Profile directory name under /workdir/wepppy-test-engine-data/profiles",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of repetitions per setter (default: 3)",
    )
    parser.add_argument(
        "--include-heavy",
        action="store_true",
        help="Include expensive operations (set_outlet, build_subcatchments)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    profiles = args.profiles or [p.name for p in PROFILE_ROOT.iterdir() if (p / "run").exists()]
    run_benchmark(
        sorted(profiles),
        repeats=max(1, args.repeats),
        include_heavy=args.include_heavy,
    )
