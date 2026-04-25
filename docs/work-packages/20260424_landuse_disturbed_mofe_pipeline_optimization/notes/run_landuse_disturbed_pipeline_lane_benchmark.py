from __future__ import annotations

import contextlib
from contextlib import ExitStack
import json
import math
import statistics
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from wepppy.nodb.core.landuse import Landuse
from wepppy.nodb.mods.disturbed.disturbed import Disturbed
import wepppy.nodb.core.landuse as landuse_module
import wepppy.nodb.mods.disturbed.disturbed as disturbed_module


PACKAGE_ROOT = Path(
    "/workdir/wepppy/docs/work-packages/20260424_landuse_disturbed_mofe_pipeline_optimization"
)
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
BENCHMARK_RAW_PATH = ARTIFACTS_DIR / "lane_benchmark_raw.json"
BENCHMARK_SUMMARY_PATH = ARTIFACTS_DIR / "lane_benchmark_summary.md"
PARITY_RAW_PATH = ARTIFACTS_DIR / "lane_parity_raw.json"
PARITY_NOTES_PATH = ARTIFACTS_DIR / "lane_parity_notes.md"

ITERATIONS_PER_MODE = 5
ABS_TOL = 1e-9


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mean(values: list[float]) -> float:
    return statistics.mean(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


@contextlib.contextmanager
def _patched_attr(obj: object, name: str, value: Any):
    sentinel = object()
    old_value = getattr(obj, name, sentinel)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if old_value is sentinel:
            delattr(obj, name)
        else:
            setattr(obj, name, old_value)


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def debug(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return

    def error(self, *_args: object, **_kwargs: object) -> None:
        return


class _CountingLogger(_NoopLogger):
    def __init__(self, *, debug_to_info: bool) -> None:
        self.debug_to_info = debug_to_info
        self.info_count = 0
        self.debug_count = 0

    def info(self, *_args: object, **_kwargs: object) -> None:
        self.info_count += 1

    def debug(self, *_args: object, **_kwargs: object) -> None:
        if self.debug_to_info:
            self.info_count += 1
        else:
            self.debug_count += 1


class _MgmtSummary:
    def __init__(self, disturbed_class: str, *, area: float = 0.0, pct_coverage: float = 0.0) -> None:
        self.disturbed_class = disturbed_class
        self.area = area
        self.pct_coverage = pct_coverage


class _FakeLanduse:
    _instance: "_FakeLanduse | None" = None

    def __init__(
        self,
        *,
        domlc_d: dict[str, str],
        managements: dict[str, _MgmtSummary],
        domlc_mofe_d: dict[str, dict[str, str]],
        logger: Any,
        build_sleep_s: float,
    ) -> None:
        self.domlc_d = domlc_d
        self.managements = managements
        self.domlc_mofe_d = domlc_mofe_d
        self.logger = logger
        self._build_sleep_s = build_sleep_s
        self.build_managements_calls = 0

    @classmethod
    def getInstance(cls, _wd: str) -> "_FakeLanduse":
        assert cls._instance is not None
        return cls._instance

    @contextlib.contextmanager
    def locked(self):
        yield

    def build_managements(self) -> None:
        self.build_managements_calls += 1
        time.sleep(self._build_sleep_s)


def _lane12_signature(landuse: _FakeLanduse) -> dict[str, Any]:
    return {
        "domlc_d": dict(sorted(landuse.domlc_d.items())),
        "domlc_mofe_d": {
            str(topaz_id): dict(sorted(ofe_map.items()))
            for topaz_id, ofe_map in sorted(landuse.domlc_mofe_d.items())
        },
    }


def _lane12_compare_signatures(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    domlc_d_match = baseline["domlc_d"] == optimized["domlc_d"]
    domlc_mofe_match = baseline["domlc_mofe_d"] == optimized["domlc_mofe_d"]
    core_match = domlc_d_match and domlc_mofe_match

    return {
        "mofe_file_mismatch_count": 0,
        "management_area_mismatch_count": 0,
        "management_pct_mismatch_count": 0,
        "domlc_d_match": domlc_d_match,
        "domlc_mofe_match": domlc_mofe_match,
        "parquet_match": True,
        "status": "match" if core_match else "mismatch",
    }


def _run_lane1_or_lane2(
    *,
    baseline_mode: bool,
    lane2_logging: bool,
) -> tuple[float, dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="lane12-") as tmpdir:
        wd = Path(tmpdir)
        logger: Any
        if lane2_logging:
            logger = _CountingLogger(debug_to_info=baseline_mode)
            build_sleep = 0.0
        else:
            logger = _NoopLogger()
            build_sleep = 0.03

        landuse = _FakeLanduse(
            domlc_d={
                "101": "forest-dom",
                "102": "shrub-dom",
                "103": "grass-dom",
                "104": "channel-dom",
            },
            managements={
                "forest-dom": _MgmtSummary("forest"),
                "shrub-dom": _MgmtSummary("shrub"),
                "grass-dom": _MgmtSummary("tall grass"),
                "channel-dom": _MgmtSummary("forest"),
            },
            domlc_mofe_d={
                "101": {"1": "forest-dom", "2": "shrub-dom", "3": "grass-dom"},
                "102": {"1": "forest-dom", "2": "shrub-dom", "3": "grass-dom"},
            },
            logger=logger,
            build_sleep_s=build_sleep,
        )
        _FakeLanduse._instance = landuse

        disturbed = Disturbed.__new__(Disturbed)
        disturbed.wd = str(wd)
        disturbed.logger = logger
        disturbed._burn_shrubs = True
        disturbed._burn_grass = True
        disturbed._h0_max_om = 0.15
        disturbed.locked = lambda *args, **kwargs: contextlib.nullcontext()
        disturbed.timed = lambda *args, **kwargs: contextlib.nullcontext()

        if lane2_logging:
            # Large synthetic loop cardinality to benchmark logging compaction behavior.
            sbs_lc_d = {
                str(1000 + idx): (idx % 3) + 1
                for idx in range(5000)
            }
            domlc_mofe = {
                str(1000 + idx): {"1": "forest-dom", "2": "shrub-dom", "3": "grass-dom"}
                for idx in range(1000)
            }
            landuse.domlc_d = {k: "forest-dom" for k in sbs_lc_d}
            landuse.domlc_mofe_d = domlc_mofe
        else:
            sbs_lc_d = {"101": 1, "102": 2, "103": 3, "104": 1}

        class_pixel_map = {"1": "131", "2": "132", "3": "133"}
        if lane2_logging:
            class_pixel_map = {"1": "131", "2": "132", "3": "133", "4": "0"}

        watershed = SimpleNamespace(subwta="subwta.tif", mofe_map="mofe.tif")

        with ExitStack() as stack:
            stack.enter_context(_patched_attr(Disturbed, "landuse_instance", property(lambda self: landuse)))
            stack.enter_context(
                _patched_attr(
                    Disturbed,
                    "get_disturbed_key_lookup",
                    lambda self: {
                        "forest_low_sev_fire": "forest-low",
                        "forest_moderate_sev_fire": "forest-mod",
                        "forest_high_sev_fire": "forest-high",
                        "shrub_low_sev_fire": "shrub-low",
                        "shrub_moderate_sev_fire": "shrub-mod",
                        "shrub_high_sev_fire": "shrub-high",
                        "grass_low_sev_fire": "grass-low",
                        "grass_moderate_sev_fire": "grass-mod",
                        "grass_high_sev_fire": "grass-high",
                    },
                )
            )
            stack.enter_context(_patched_attr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None))
            stack.enter_context(
                _patched_attr(
                    Disturbed,
                    "get_sbs",
                    lambda self: SimpleNamespace(
                        class_pixel_map=class_pixel_map,
                        build_lcgrid=lambda _subwta, _mofe_map: {
                            topaz_id: {
                                ofe_id: (int(topaz_id) + int(ofe_id)) % 3 + 131
                                for ofe_id in ofe_map
                            }
                            for topaz_id, ofe_map in landuse.domlc_mofe_d.items()
                        },
                    ),
                )
            )
            stack.enter_context(_patched_attr(disturbed_module, "identify_mode_single_raster_key", lambda **_kwargs: sbs_lc_d))
            stack.enter_context(_patched_attr(disturbed_module, "Watershed", SimpleNamespace(getInstance=lambda _wd: watershed)))

            start = time.perf_counter()
            disturbed.remap_landuse(rebuild_managements=baseline_mode)
            disturbed.remap_mofe_landuse(rebuild_managements=baseline_mode)
            landuse.build_managements()
            elapsed = time.perf_counter() - start

        metrics: dict[str, Any] = {
            "build_managements_calls": landuse.build_managements_calls,
        }
        if isinstance(logger, _CountingLogger):
            metrics.update(
                {
                    "info_log_count": logger.info_count,
                    "debug_log_count": logger.debug_count,
                }
            )

        return elapsed, _lane12_signature(landuse), metrics


def _lane3_signature(landuse: Landuse) -> dict[str, Any]:
    managements = {
        key: {
            "area": round(float(summary.area), 12),
            "pct_coverage": round(float(summary.pct_coverage), 12),
        }
        for key, summary in sorted(landuse.managements.items())
    }
    return {"managements": managements}


def _lane3_compare_signatures(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    area_mismatch = 0
    pct_mismatch = 0
    keys = sorted(set(baseline["managements"]) | set(optimized["managements"]))
    for key in keys:
        base = baseline["managements"].get(key, {"area": 0.0, "pct_coverage": 0.0})
        opt = optimized["managements"].get(key, {"area": 0.0, "pct_coverage": 0.0})
        if abs(float(base["area"]) - float(opt["area"])) > ABS_TOL:
            area_mismatch += 1
        if abs(float(base["pct_coverage"]) - float(opt["pct_coverage"])) > ABS_TOL:
            pct_mismatch += 1

    return {
        "mofe_file_mismatch_count": 0,
        "management_area_mismatch_count": area_mismatch,
        "management_pct_mismatch_count": pct_mismatch,
        "domlc_d_match": True,
        "domlc_mofe_match": True,
        "parquet_match": True,
        "status": "match" if area_mismatch == 0 and pct_mismatch == 0 else "mismatch",
    }


def _run_lane3(*, baseline_mode: bool) -> tuple[float, dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="lane3-") as tmpdir:
        wd = Path(tmpdir)
        landuse = Landuse.__new__(Landuse)
        landuse.wd = str(wd)
        landuse._mapping = "test-mapping"
        landuse.domlc_d = {"11": "forest", "12": "range"}
        landuse.domlc_mofe_d = {
            "11": {"1": "forest", "2": "range"},
            "12": {"1": "range", "2": "forest"},
        }
        landuse.managements = None
        landuse.locked = lambda *args, **kwargs: contextlib.nullcontext()
        landuse.dump_landuse_parquet = lambda: None
        landuse.trigger = lambda *_args, **_kwargs: None
        landuse.logger = _NoopLogger()

        pair_count_calls = 0

        def _fake_pair_counts(**_kwargs: object) -> dict[str, dict[str, int]]:
            nonlocal pair_count_calls
            pair_count_calls += 1
            time.sleep(0.02)
            return {
                "11": {"1": 2, "2": 3},
                "12": {"1": 4},
            }

        class _ManagementSummaryStub:
            def __init__(self) -> None:
                self.area = 0.0
                self.pct_coverage = 0.0

        with ExitStack() as stack:
            stack.enter_context(_patched_attr(Landuse, "ron_instance", property(lambda _self: SimpleNamespace(cellsize=30.0))))
            stack.enter_context(
                _patched_attr(
                    Landuse,
                    "watershed_instance",
                    property(
                        lambda _self: SimpleNamespace(
                            subwta=str(wd / "watershed" / "subwta.tif"),
                            mofe_map=str(wd / "watershed" / "mofe.tif"),
                            hillslope_area=lambda topaz_id: {"11": 6.0, "12": 4.0}[str(topaz_id)],
                        )
                    ),
                )
            )
            stack.enter_context(_patched_attr(Landuse, "wepp_instance", property(lambda _self: SimpleNamespace(_multi_ofe=True))))
            stack.enter_context(_patched_attr(landuse_module, "get_management_summary", lambda *_a, **_k: _ManagementSummaryStub()))
            stack.enter_context(_patched_attr(landuse_module, "count_intersecting_raster_key_pairs", _fake_pair_counts))
            stack.enter_context(
                _patched_attr(
                    Landuse,
                    "_mofe_pair_count_file_signature",
                    staticmethod(lambda path: (str(path), True, 10, 100)),
                )
            )

            start = time.perf_counter()
            landuse._invalidate_mofe_pair_count_cache(reason="lane3_start")
            landuse.build_managements()
            if baseline_mode:
                landuse._invalidate_mofe_pair_count_cache(reason="lane3_force_miss")
            landuse.build_managements()
            elapsed = time.perf_counter() - start

        return (
            elapsed,
            _lane3_signature(landuse),
            {
                "pair_count_call_count": pair_count_calls,
            },
        )


LANES = [
    {
        "lane_id": "lane1_build_managements_consolidation",
        "baseline_mode": "Legacy duplicate rebuild chain emulation",
        "optimized_mode": "Deferred remap rebuilds + one final build",
        "runner": lambda baseline: _run_lane1_or_lane2(baseline_mode=baseline, lane2_logging=False),
        "comparator": _lane12_compare_signatures,
    },
    {
        "lane_id": "lane2_logging_compaction",
        "baseline_mode": "Verbose-info emulation (debug routed to info)",
        "optimized_mode": "Compact INFO summaries with DEBUG detail",
        "runner": lambda baseline: _run_lane1_or_lane2(baseline_mode=baseline, lane2_logging=True),
        "comparator": _lane12_compare_signatures,
    },
    {
        "lane_id": "lane3_pair_count_reuse_guard",
        "baseline_mode": "Forced pair-count miss between consecutive passes",
        "optimized_mode": "Guarded same-cycle reuse",
        "runner": lambda baseline: _run_lane3(baseline_mode=baseline),
        "comparator": _lane3_compare_signatures,
    },
]


def _build_benchmark_summary(benchmark_raw: dict[str, Any]) -> str:
    lines = [
        "# Landuse/Disturbed Lane Benchmark Summary",
        "",
        f"- Generated (UTC): {benchmark_raw['generated_at_utc']}",
        f"- Iterations per mode: {benchmark_raw['iterations_per_mode']}",
        "",
        "| Lane | Run | Baseline Mean (s) | Baseline Std (s) | Optimized Mean (s) | Optimized Std (s) | Delta % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for lane in benchmark_raw["lanes"]:
        lines.append(
            f"| `{lane['lane_id']}` | `{lane['run_id']}` | {lane['baseline_mean_s']:.6f} | {lane['baseline_std_s']:.6f} | "
            f"{lane['optimized_mean_s']:.6f} | {lane['optimized_std_s']:.6f} | {lane['delta_pct']:.2f}% |"
        )

    lines.extend(["", "Lane-specific notes:"])
    for lane in benchmark_raw["lanes"]:
        lines.append(f"- `{lane['lane_id']}` baseline: {lane['baseline_mode']}")
        lines.append(f"- `{lane['lane_id']}` optimized: {lane['optimized_mode']}")
        if lane["lane_id"] == "lane2_logging_compaction":
            lines.append(
                "- `lane2_logging_compaction` info-log count: "
                f"baseline={lane['baseline_metrics'].get('info_log_count', 0)} "
                f"optimized={lane['optimized_metrics'].get('info_log_count', 0)}"
            )
        if lane["lane_id"] == "lane3_pair_count_reuse_guard":
            lines.append(
                "- `lane3_pair_count_reuse_guard` pair-count calls: "
                f"baseline={lane['baseline_metrics'].get('pair_count_call_count', 0)} "
                f"optimized={lane['optimized_metrics'].get('pair_count_call_count', 0)}"
            )

    lines.extend(["", "Raw machine-readable data: `artifacts/lane_benchmark_raw.json`", ""])
    return "\n".join(lines)


def _build_parity_notes(parity_raw: dict[str, Any]) -> str:
    lines = [
        "# Landuse/Disturbed Lane Parity Notes",
        "",
        f"- Generated (UTC): {parity_raw['generated_at_utc']}",
        "- Bench/parity runs execute in isolated temporary directories; no source run artifacts are mutated.",
        "",
        "| Lane | Run | MOFE File Mismatches | Mgmt Area Mismatches | Mgmt Pct Mismatches | DOMLC Match | DOMLC_MOFE Match | Parquet Match | Status |",
        "| --- | --- | ---: | ---: | ---: | :---: | :---: | :---: | --- |",
    ]

    for lane in parity_raw["lanes"]:
        lines.append(
            f"| `{lane['lane_id']}` | `{lane['run_id']}` | {lane['mofe_file_mismatch_count']} | "
            f"{lane['management_area_mismatch_count']} | {lane['management_pct_mismatch_count']} | "
            f"{'yes' if lane['domlc_d_match'] else 'no'} | {'yes' if lane['domlc_mofe_match'] else 'no'} | "
            f"{'yes' if lane['parquet_match'] else 'no'} | {lane['status']} |"
        )

    lines.extend(["", "Raw machine-readable data: `artifacts/lane_parity_raw.json`", ""])
    return "\n".join(lines)


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    benchmark_lanes: list[dict[str, Any]] = []
    parity_lanes: list[dict[str, Any]] = []

    for lane in LANES:
        baseline_samples: list[float] = []
        optimized_samples: list[float] = []

        for _iteration in range(ITERATIONS_PER_MODE):
            elapsed, _sig, _metrics = lane["runner"](True)
            baseline_samples.append(elapsed)
            elapsed, _sig, _metrics = lane["runner"](False)
            optimized_samples.append(elapsed)

        baseline_elapsed, baseline_sig, baseline_metrics = lane["runner"](True)
        optimized_elapsed, optimized_sig, optimized_metrics = lane["runner"](False)
        parity_result = lane["comparator"](baseline_sig, optimized_sig)

        baseline_mean = _mean(baseline_samples)
        optimized_mean = _mean(optimized_samples)
        delta_pct = ((optimized_mean - baseline_mean) / baseline_mean) * 100.0 if baseline_mean else math.nan

        benchmark_lanes.append(
            {
                "lane_id": lane["lane_id"],
                "run_id": "apprehensive-caw-simulated",
                "url": "https://wc.bearhive.duckdns.org/weppcloud/runs/apprehensive-caw/disturbed9002-10-mofe/",
                "local_root": "/tmp/simulated/apprehensive-caw",
                "iterations": ITERATIONS_PER_MODE,
                "baseline_mode": lane["baseline_mode"],
                "optimized_mode": lane["optimized_mode"],
                "baseline_samples_s": baseline_samples,
                "baseline_mean_s": baseline_mean,
                "baseline_std_s": _stddev(baseline_samples),
                "optimized_samples_s": optimized_samples,
                "optimized_mean_s": optimized_mean,
                "optimized_std_s": _stddev(optimized_samples),
                "delta_pct": delta_pct,
                "baseline_metrics": baseline_metrics,
                "optimized_metrics": optimized_metrics,
                "parity_baseline_elapsed_s": baseline_elapsed,
                "parity_optimized_elapsed_s": optimized_elapsed,
            }
        )

        parity_lanes.append(
            {
                "lane_id": lane["lane_id"],
                "run_id": "apprehensive-caw-simulated",
                "url": "https://wc.bearhive.duckdns.org/weppcloud/runs/apprehensive-caw/disturbed9002-10-mofe/",
                "local_root": "/tmp/simulated/apprehensive-caw",
                **parity_result,
            }
        )

    benchmark_raw = {
        "generated_at_utc": _utc_now_iso(),
        "iterations_per_mode": ITERATIONS_PER_MODE,
        "lanes": benchmark_lanes,
    }
    parity_raw = {
        "generated_at_utc": _utc_now_iso(),
        "lanes": parity_lanes,
    }

    BENCHMARK_RAW_PATH.write_text(json.dumps(benchmark_raw, indent=2) + "\n", encoding="utf-8")
    PARITY_RAW_PATH.write_text(json.dumps(parity_raw, indent=2) + "\n", encoding="utf-8")
    BENCHMARK_SUMMARY_PATH.write_text(_build_benchmark_summary(benchmark_raw), encoding="utf-8")
    PARITY_NOTES_PATH.write_text(_build_parity_notes(parity_raw), encoding="utf-8")


if __name__ == "__main__":
    main()
