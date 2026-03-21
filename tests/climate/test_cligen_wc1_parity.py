from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

import pytest

from wepppy.climates.cligen import ClimateFile
from wepppy.climates.cligen.cligen import _wepp_hyetograph_depths, _wepp_hyetograph_segments

try:
    from wepppyo3 import climate as _pyo3_climate
except ImportError:  # pragma: no cover - optional dependency boundary
    _pyo3_climate = None

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_RUNS_ROOT = Path("/wc1/runs")
_BREAKPOINT_RUN = Path("/wc1/runs/co/cowled-apparatchik")
_WINDOWS = (10, 15, 30, 60)
_TIME_STEP_MINUTES = 5.0
_IP_CORRECTION = 0.70
_MAX_NON_BREAKPOINT_FILES = 8
_MAX_EVENTS_PER_FILE = 40
_MAX_BREAKPOINT_EVENTS = 60


def _is_breakpoint_cli(cli_path: Path) -> bool:
    lines = cli_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 2:
        return False
    tokens = lines[1].split()
    if len(tokens) < 2:
        return False
    try:
        return int(tokens[1]) > 0
    except ValueError:
        return False


def _find_data_start(lines: Sequence[str]) -> int:
    for idx, line in enumerate(lines):
        lower = line.strip().lower()
        if lower.startswith("da ") or lower.startswith("day "):
            return idx + 2
    raise ValueError("unable to locate CLI data header")


def _parse_non_breakpoint_events(cli_path: Path, max_events: int) -> list[tuple[float, float, float, float]]:
    lines = cli_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = _find_data_start(lines)
    events: list[tuple[float, float, float, float]] = []
    for line in lines[start:]:
        tokens = line.split()
        if len(tokens) < 7:
            continue
        try:
            prcp = float(tokens[3])
            dur = float(tokens[4])
            tp = float(tokens[5])
            ip = float(tokens[6])
        except ValueError:
            continue
        if not all(math.isfinite(v) for v in (prcp, dur, tp, ip)):
            continue
        if prcp <= 0.0 or dur <= 0.0:
            continue
        events.append((prcp, dur, tp, ip))
        if len(events) >= max_events:
            break
    return events


def _parse_breakpoint_events(cli_path: Path, max_events: int) -> list[tuple[list[float], list[float]]]:
    lines = cli_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = _find_data_start(lines)
    events: list[tuple[list[float], list[float]]] = []
    idx = start
    while idx < len(lines) and len(events) < max_events:
        tokens = lines[idx].split()
        idx += 1
        if not tokens:
            continue
        if len(tokens) == 2:
            continue
        if len(tokens) < 4:
            continue
        try:
            nbrkpt = int(tokens[3])
        except ValueError:
            continue
        if nbrkpt <= 0:
            continue

        times: list[float] = []
        depths: list[float] = []
        for _ in range(nbrkpt):
            if idx >= len(lines):
                break
            bp_tokens = lines[idx].split()
            idx += 1
            if len(bp_tokens) < 2:
                continue
            try:
                time_hr = float(bp_tokens[0])
                depth_mm = float(bp_tokens[1])
            except ValueError:
                continue
            if math.isfinite(time_hr) and math.isfinite(depth_mm):
                times.append(time_hr)
                depths.append(depth_mm)

        if not times or not depths:
            continue
        if times[-1] <= 0.0 or depths[-1] <= 0.0:
            continue
        events.append((times, depths))

    return events


def _peak_intensities_from_depths(
    depths: Sequence[float],
    dt_hours: float,
    storm_depth_mm: float,
    windows_minutes: Sequence[int],
) -> list[float]:
    if not depths or dt_hours <= 0.0:
        return [0.0 for _ in windows_minutes]

    total_bins = len(depths)
    cumulative = [0.0] * (total_bins + 1)
    for i in range(total_bins):
        cumulative[i + 1] = cumulative[i] + depths[i]

    out: list[float] = []
    for window_minutes in windows_minutes:
        window_hours = float(window_minutes) / 60.0
        if window_hours <= 0.0:
            out.append(0.0)
            continue
        window_bins = int(round(window_hours / dt_hours))
        if window_bins <= 0:
            out.append(0.0)
            continue
        if window_bins > total_bins:
            out.append(storm_depth_mm / window_hours)
            continue

        max_depth = 0.0
        for start in range(0, total_bins - window_bins + 1):
            depth = cumulative[start + window_bins] - cumulative[start]
            if depth > max_depth:
                max_depth = depth
        out.append(max_depth / window_hours)
    return out


def _legacy_non_breakpoint_peak_intensities(prcp: float, dur: float, tp: float, ip: float) -> list[float]:
    segments = _wepp_hyetograph_segments(
        prcp,
        dur,
        tp,
        ip,
        ip_correction=_IP_CORRECTION,
        time_step_minutes=_TIME_STEP_MINUTES,
    )
    depths, dt_hours = _wepp_hyetograph_depths(segments, dur, _TIME_STEP_MINUTES)
    return _peak_intensities_from_depths(depths, dt_hours, prcp, _WINDOWS)


def _legacy_breakpoint_peak_intensities(times_hr: Sequence[float], cum_depth_mm: Sequence[float]) -> list[float]:
    segments: list[tuple[float, float, float]] = []
    prev_t = 0.0
    prev_d = 0.0
    for t, d in zip(times_hr, cum_depth_mm):
        dt = t - prev_t
        dd = d - prev_d
        if dt > 0.0 and dd > 0.0:
            segments.append((prev_t, t, dd / dt))
        prev_t = t
        prev_d = d

    dur = float(times_hr[-1]) if times_hr else 0.0
    total_depth = float(cum_depth_mm[-1]) if cum_depth_mm else 0.0
    depths, dt_hours = _wepp_hyetograph_depths(segments, dur, _TIME_STEP_MINUTES)
    return _peak_intensities_from_depths(depths, dt_hours, total_depth, _WINDOWS)


def _find_breakpoint_cli_under_run(run_dir: Path) -> Path | None:
    candidates: list[Path] = []
    preferred = run_dir / "wepp" / "runs" / "pw0.cli"
    if preferred.exists():
        candidates.append(preferred)
    candidates.extend(sorted(run_dir.rglob("*.cli")))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file() and _is_breakpoint_cli(candidate):
            return candidate
    return None


def test_wc1_non_breakpoint_cli_peak_intensity_parity_against_legacy_python() -> None:
    if _pyo3_climate is None:
        pytest.skip("wepppyo3.climate is required for parity testing")
    if not _RUNS_ROOT.exists():
        pytest.skip(f"{_RUNS_ROOT} not found")

    candidate_cli = sorted(_RUNS_ROOT.glob("*/*/wepp/runs/pw0.cli"))
    non_breakpoint = [path for path in candidate_cli if path.is_file() and not _is_breakpoint_cli(path)]
    if not non_breakpoint:
        pytest.skip("no non-breakpoint pw0.cli files found under /wc1/runs")

    sampled = non_breakpoint[:_MAX_NON_BREAKPOINT_FILES]
    compared = 0
    for cli_path in sampled:
        for prcp, dur, tp, ip in _parse_non_breakpoint_events(cli_path, _MAX_EVENTS_PER_FILE):
            rust_out = _pyo3_climate.compute_peak_intensities_non_breakpoint(
                prcp_mm=float(prcp),
                dur_hr=float(dur),
                tp=float(tp),
                ip=float(ip),
                windows_minutes=list(_WINDOWS),
                ip_correction=_IP_CORRECTION,
                time_step_minutes=_TIME_STEP_MINUTES,
            )
            rust_values = [float(rust_out[f"peak_intensity_{window}"]) for window in _WINDOWS]
            legacy_values = _legacy_non_breakpoint_peak_intensities(prcp, dur, tp, ip)
            assert rust_values == pytest.approx(
                legacy_values,
                rel=1.0e-5,
                abs=1.0e-4,
            ), f"parity mismatch in {cli_path}"
            compared += 1

    assert compared > 0, "no non-breakpoint storms were compared"


def test_wc1_breakpoint_cli_peak_intensity_parity_and_contract() -> None:
    if _pyo3_climate is None:
        pytest.skip("wepppyo3.climate is required for parity testing")
    if not _BREAKPOINT_RUN.exists():
        pytest.skip(f"{_BREAKPOINT_RUN} not found")

    breakpoint_cli = _find_breakpoint_cli_under_run(_BREAKPOINT_RUN)
    if breakpoint_cli is None:
        pytest.skip("no breakpoint CLI found under /wc1/runs/co/cowled-apparatchik")

    events = _parse_breakpoint_events(breakpoint_cli, _MAX_BREAKPOINT_EVENTS)
    if not events:
        pytest.skip(f"no breakpoint storms found in {breakpoint_cli}")

    compared = 0
    for times, depths in events:
        rust_out = _pyo3_climate.compute_peak_intensities_breakpoint(
            breakpoint_times_hr=[float(v) for v in times],
            breakpoint_cum_depth_mm=[float(v) for v in depths],
            windows_minutes=list(_WINDOWS),
            time_step_minutes=_TIME_STEP_MINUTES,
        )
        rust_values = [float(rust_out[f"peak_intensity_{window}"]) for window in _WINDOWS]
        legacy_values = _legacy_breakpoint_peak_intensities(times, depths)
        assert rust_values == pytest.approx(
            legacy_values,
            rel=1.0e-5,
            abs=1.0e-4,
        ), f"breakpoint parity mismatch in {breakpoint_cli}"
        compared += 1

    assert compared > 0, "no breakpoint storms were compared"

    df = ClimateFile(str(breakpoint_cli)).as_dataframe(calc_peak_intensities=True)
    breakpoint_rows = df[df["nbrkpt"] > 0]
    assert not breakpoint_rows.empty
    assert (breakpoint_rows[["peak_intensity_10", "peak_intensity_15", "peak_intensity_30", "peak_intensity_60"]] >= 0.0).all().all()
    assert breakpoint_rows["tp"].isna().all()
    assert breakpoint_rows["ip"].isna().all()
