"""Native Roads slope assembly and unchanged profile transformations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping
import numpy as np


def _clamp_percent_slope(value: float) -> float:
    return max(0.1, min(40.0, float(value)))


def _clamp_fill_slope_pct(value: float) -> float:
    return max(0.1, min(150.0, float(value)))


def _clamp_buffer_slope_pct(value: float) -> float:
    return max(0.1, min(100.0, float(value)))


def _derive_buffer_profile_from_trace(self, trace_result: Mapping[str, Any]) -> Dict[str, float]:
    path_length_m = self._as_float_or_none(trace_result.get("path_length_m"))
    if path_length_m is None or path_length_m <= 0:
        raise ValueError("Trace result is missing a positive path_length_m for routed contributor assembly.")

    slope_candidates: List[float] = []
    mean_slope = self._as_float_or_none(trace_result.get("mean_slope"))
    if mean_slope is not None and np.isfinite(mean_slope):
        slope_candidates.append(float(mean_slope))

    drop_m = self._as_float_or_none(trace_result.get("drop_m"))
    if drop_m is not None and np.isfinite(drop_m) and path_length_m > 0:
        slope_candidates.append(float(drop_m) / float(path_length_m))

    segment_slope = trace_result.get("segment_slope")
    if isinstance(segment_slope, list):
        for raw in segment_slope:
            value = self._as_float_or_none(raw)
            if value is None or not np.isfinite(value):
                continue
            slope_candidates.append(float(value))

    positive_candidates = [value for value in slope_candidates if value > 0.0]
    slope_fraction = max(positive_candidates) if positive_candidates else 0.001
    slope_pct = self._clamp_percent_slope(slope_fraction * 100.0)
    return {
        "buffer_length_m": max(0.3, float(path_length_m)),
        "buffer_slope_pct": float(slope_pct),
        "buffer_slope_fraction": float(slope_pct / 100.0),
    }


def _derive_buffer_profile_from_feature_or_defaults(
    self,
    *,
    properties: Mapping[str, Any],
    road_profile: Mapping[str, Any],
) -> Dict[str, Any]:
    buffer_length_raw = self._first_non_empty_property(
        properties,
        ("BUFFER_LENGTH_M", "buffer_length_m", "BUFFER_LEN_M", "buffer_len_m"),
    )
    buffer_slope_raw = self._first_non_empty_property(
        properties,
        ("BUFFER_SLOPE_PCT", "buffer_slope_pct", "BUFFER_SLOPE", "buffer_slope"),
    )

    buffer_length_source = "segment_property"
    buffer_length_m = self._coerce_float(buffer_length_raw)
    if buffer_length_m is None or not np.isfinite(buffer_length_m) or buffer_length_m <= 0:
        segment_length_m = self._as_float_or_none(road_profile.get("segment_length_m"))
        if segment_length_m is None or segment_length_m <= 0:
            buffer_length_m = 30.0
        else:
            buffer_length_m = max(0.3, min(float(segment_length_m), 30.0))
        buffer_length_source = "derived_default"

    buffer_slope_source = "segment_property"
    buffer_slope_pct = self._coerce_float(buffer_slope_raw)
    if buffer_slope_pct is None or not np.isfinite(buffer_slope_pct) or buffer_slope_pct <= 0:
        road_slope_pct = self._as_float_or_none(road_profile.get("slope_pct"))
        if road_slope_pct is None or road_slope_pct <= 0:
            buffer_slope_pct = 6.0
        else:
            buffer_slope_pct = float(road_slope_pct) * 0.5
        buffer_slope_source = "derived_default"

    buffer_slope_pct = self._clamp_buffer_slope_pct(float(buffer_slope_pct))
    return {
        "buffer_length_m": max(0.3, min(300.0, float(buffer_length_m))),
        "buffer_slope_pct": float(buffer_slope_pct),
        "buffer_slope_fraction": float(buffer_slope_pct / 100.0),
        "buffer_length_source": buffer_length_source,
        "buffer_slope_source": buffer_slope_source,
    }


def _apply_outslope_unrutted_geometry_parity(
    *,
    road_length_m: float,
    road_width_m: float,
    road_slope_pct: float,
) -> Dict[str, float]:
    outslope_fraction = 0.04
    longitudinal_fraction = max(0.001, float(road_slope_pct) / 100.0)
    road_slope_fraction = (outslope_fraction**2.0) + (longitudinal_fraction**2.0)
    scale = max(road_slope_fraction / outslope_fraction, 1e-6)

    sim_length_m = max(1.0, min(300.0, float(road_length_m) * scale))
    sim_width_m = max(0.3, min(100.0, float(road_width_m) / scale))

    return {
        "sim_length_m": float(sim_length_m),
        "sim_width_m": float(sim_width_m),
        "road_slope_fraction": float(road_slope_fraction),
        "road_slope_pct": float(road_slope_fraction * 100.0),
        "geometry_scale": float(scale),
    }


def _write_routed_two_ofe_slope_file(
    path: Path,
    *,
    width_m: float,
    road_length_m: float,
    road_slope_pct: float,
    buffer_length_m: float,
    buffer_slope_pct: float,
) -> None:
    road_slope_fraction = float(road_slope_pct) / 100.0
    buffer_slope_fraction = float(buffer_slope_pct) / 100.0
    content = [
        "97.3",
        "2",
        f"180.0 {float(width_m):.3f}",
        f"2 {float(road_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
        f"3 {float(buffer_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 0.05, {buffer_slope_fraction:.6f} 1.00, {buffer_slope_fraction:.6f}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_routed_three_ofe_slope_file(
    path: Path,
    *,
    width_m: float,
    road_length_m: float,
    road_slope_pct: float,
    fill_length_m: float,
    fill_slope_pct: float,
    buffer_length_m: float,
    buffer_slope_pct: float,
) -> None:
    road_slope_fraction = float(road_slope_pct) / 100.0
    fill_slope_fraction = float(fill_slope_pct) / 100.0
    buffer_slope_fraction = float(buffer_slope_pct) / 100.0
    content = [
        "97.3",
        "3",
        f"180.0 {float(width_m):.3f}",
        f"2 {float(road_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
        f"3 {float(fill_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
        f"3 {float(buffer_length_m):.3f}",
        f"0.00, {fill_slope_fraction:.6f} 0.05, {buffer_slope_fraction:.6f} 1.00, {buffer_slope_fraction:.6f}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_routed_three_ofe_landuse_road_fill_slope_file(
    path: Path,
    *,
    width_m: float,
    top_landuse_length_m: float,
    top_landuse_slope_pct: float,
    road_length_m: float,
    road_slope_pct: float,
    fill_length_m: float,
    fill_slope_pct: float,
) -> None:
    top_landuse_slope_fraction = float(top_landuse_slope_pct) / 100.0
    road_slope_fraction = float(road_slope_pct) / 100.0
    fill_slope_fraction = float(fill_slope_pct) / 100.0
    content = [
        "97.3",
        "3",
        f"180.0 {float(width_m):.3f}",
        f"2 {float(top_landuse_length_m):.3f}",
        f"0.00, {top_landuse_slope_fraction:.6f} 1.00, {top_landuse_slope_fraction:.6f}",
        f"3 {float(road_length_m):.3f}",
        f"0.00, {top_landuse_slope_fraction:.6f} 0.05, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
        f"3 {float(fill_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_routed_four_ofe_landuse_road_fill_hill_slope_file(
    path: Path,
    *,
    width_m: float,
    top_landuse_length_m: float,
    top_landuse_slope_pct: float,
    road_length_m: float,
    road_slope_pct: float,
    fill_length_m: float,
    fill_slope_pct: float,
    bottom_landuse_length_m: float,
    bottom_landuse_slope_pct: float,
) -> None:
    top_landuse_slope_fraction = float(top_landuse_slope_pct) / 100.0
    road_slope_fraction = float(road_slope_pct) / 100.0
    fill_slope_fraction = float(fill_slope_pct) / 100.0
    bottom_landuse_slope_fraction = float(bottom_landuse_slope_pct) / 100.0
    content = [
        "97.3",
        "4",
        f"180.0 {float(width_m):.3f}",
        f"2 {float(top_landuse_length_m):.3f}",
        f"0.00, {top_landuse_slope_fraction:.6f} 1.00, {top_landuse_slope_fraction:.6f}",
        f"3 {float(road_length_m):.3f}",
        f"0.00, {top_landuse_slope_fraction:.6f} 0.05, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
        f"3 {float(fill_length_m):.3f}",
        f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
        f"3 {float(bottom_landuse_length_m):.3f}",
        f"0.00, {fill_slope_fraction:.6f} 0.05, {bottom_landuse_slope_fraction:.6f} 1.00, {bottom_landuse_slope_fraction:.6f}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_single_ofe_slope_file(path: Path, *, width_m: float, length_m: float, slope_pct: float) -> None:
    slope_fraction = float(slope_pct) / 100.0
    content = [
        "97.3",
        "1",
        f"180.0 {float(width_m):.3f}",
        f"2 {float(length_m):.3f}",
        f"0.00, {slope_fraction:.6f} 1.00, {slope_fraction:.6f}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")
