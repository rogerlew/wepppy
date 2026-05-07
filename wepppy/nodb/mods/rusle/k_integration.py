"""RUSLE K-factor integration for POLARIS estimators + benchmark harness."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import rasterio
from rasterio.fill import fillnodata

from wepppy.query_engine.activate import update_catalog_entry

from .k_compare import ComparisonThresholds, compare_k_modes_to_reference, write_comparison_summary_json
from .k_epic import OM_TO_OC_FACTOR, compute_polaris_epic_k
from .k_manifest import update_k_manifest
from .k_nomograph import compute_polaris_nomograph_k
from .k_reference import (
    DEFAULT_REFERENCE_MODE_PRECEDENCE,
    ReferencePoint,
    run_reference_harness,
    sample_points_from_raster,
    write_reference_samples_json,
)


NEAR_SURFACE_DEPTHS: tuple[str, str] = ("0_5", "5_15")
DEFAULT_DEPTH_WEIGHTS_CM: dict[str, float] = {"0_5": 5.0, "5_15": 10.0}
GAP_FILL_MAX_HOLE_PIXELS = 64
GAP_FILL_MAX_TOTAL_FRACTION = 0.10
GAP_FILL_MAX_SEARCH_DISTANCE_PX = 6.0
GAP_FILL_SMOOTHING_ITERATIONS = 0


__all__ = ["RusleKResult", "run_rusle_k_factors"]


@dataclass(frozen=True)
class RusleKResult:
    nomograph: str | None
    epic: str | None
    k_default: str | None
    manifest: str
    reference_samples: str | None
    comparison_summary: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative_path(base: str, path: str) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def _layer_path(wd: str, *, property_name: str, statistic: str, depth: str) -> str:
    return _join(wd, "polaris", f"{property_name}_{statistic}_{depth}.tif")


def _read_layer(path: str, *, is_log10: bool) -> tuple[np.ndarray, dict[str, Any]]:
    if not _exists(path):
        raise FileNotFoundError(f"Required POLARIS layer not found: {path}")

    with rasterio.open(path) as dataset:
        data = dataset.read(1).astype(np.float64)
        profile = dict(dataset.profile)
        nodata_value = dataset.nodata

    if nodata_value is not None:
        data[np.isclose(data, float(nodata_value), equal_nan=True)] = np.nan
    data[~np.isfinite(data)] = np.nan

    if is_log10:
        converted = np.full_like(data, np.nan)
        valid = np.isfinite(data)
        converted[valid] = np.power(10.0, data[valid])
        data = converted

    return data, profile


def _weighted_depth_average(
    top: np.ndarray,
    sub: np.ndarray,
    *,
    top_weight_cm: float,
    sub_weight_cm: float,
) -> np.ndarray:
    weights = np.asarray([top_weight_cm, sub_weight_cm], dtype=np.float64)
    stack = np.stack([top, sub], axis=0)
    valid = np.isfinite(stack)

    weighted_sum = np.sum(np.where(valid, stack * weights[:, None, None], 0.0), axis=0)
    weight_sum = np.sum(np.where(valid, weights[:, None, None], 0.0), axis=0)

    result = np.full_like(top, np.nan, dtype=np.float64)
    np.divide(weighted_sum, weight_sum, out=result, where=weight_sum > 0.0)
    return result


def _write_k_raster(path: str, data: np.ndarray, profile: Mapping[str, Any]) -> None:
    out_profile = dict(profile)
    out_profile.update(
        {
            "driver": "GTiff",
            "dtype": "float32",
            "count": 1,
            "nodata": -9999.0,
            "compress": "deflate",
        }
    )

    writable = np.where(np.isfinite(data), data, out_profile["nodata"]).astype(np.float32)
    with rasterio.open(path, "w", **out_profile) as dataset:
        dataset.write(writable, 1)


def _collect_small_interior_holes(
    nodata_mask: np.ndarray,
    *,
    max_hole_pixels: int,
) -> tuple[list[np.ndarray], dict[str, int]]:
    if nodata_mask.ndim != 2:
        raise ValueError("nodata_mask must be a 2D array")

    height, width = nodata_mask.shape
    visited = np.zeros_like(nodata_mask, dtype=bool)
    offsets = (
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    )

    small_interior_holes: list[np.ndarray] = []
    hole_components_total = 0
    interior_hole_components = 0
    candidate_hole_components = 0
    candidate_hole_pixels = 0

    starts = np.argwhere(nodata_mask)
    for start_row, start_col in starts:
        row = int(start_row)
        col = int(start_col)
        if visited[row, col]:
            continue

        hole_components_total += 1
        queue: deque[tuple[int, int]] = deque([(row, col)])
        visited[row, col] = True
        touches_edge = row in {0, height - 1} or col in {0, width - 1}
        component_coords: list[tuple[int, int]] = []
        component_size = 0

        while queue:
            current_row, current_col = queue.pop()
            component_size += 1
            if component_size <= max_hole_pixels:
                component_coords.append((current_row, current_col))

            for d_row, d_col in offsets:
                n_row = current_row + d_row
                n_col = current_col + d_col
                if n_row < 0 or n_row >= height or n_col < 0 or n_col >= width:
                    continue
                if visited[n_row, n_col] or not nodata_mask[n_row, n_col]:
                    continue

                visited[n_row, n_col] = True
                if n_row in {0, height - 1} or n_col in {0, width - 1}:
                    touches_edge = True
                queue.append((n_row, n_col))

        if touches_edge:
            continue

        interior_hole_components += 1
        if component_size > max_hole_pixels:
            continue

        candidate_hole_components += 1
        candidate_hole_pixels += component_size
        small_interior_holes.append(np.asarray(component_coords, dtype=np.int64))

    stats = {
        "hole_components_total": int(hole_components_total),
        "interior_hole_components": int(interior_hole_components),
        "candidate_hole_components": int(candidate_hole_components),
        "candidate_hole_pixels": int(candidate_hole_pixels),
    }
    return small_interior_holes, stats


def _fill_small_hole_component(
    data: np.ndarray,
    component: np.ndarray,
    *,
    max_search_distance: float,
    smoothing_iterations: int,
) -> int:
    if component.size == 0:
        return 0

    height, width = data.shape
    rows = component[:, 0]
    cols = component[:, 1]
    search_radius = max(1, int(np.ceil(max_search_distance)))

    min_row = max(0, int(rows.min()) - search_radius)
    max_row = min(height, int(rows.max()) + search_radius + 1)
    min_col = max(0, int(cols.min()) - search_radius)
    max_col = min(width, int(cols.max()) + search_radius + 1)

    window = data[min_row:max_row, min_col:max_col]
    valid_sources = np.isfinite(window)
    if not np.any(valid_sources):
        return 0

    local_mask = valid_sources.astype(np.uint8)
    local_data = np.where(valid_sources, window, 0.0).astype(np.float32)
    filled = fillnodata(
        local_data,
        mask=local_mask,
        max_search_distance=max_search_distance,
        smoothing_iterations=smoothing_iterations,
    )

    filled_count = 0
    for row, col in component:
        local_row = int(row) - min_row
        local_col = int(col) - min_col
        value = float(filled[local_row, local_col])
        if np.isfinite(value):
            data[int(row), int(col)] = value
            filled_count += 1
    return filled_count


def _apply_conservative_gap_fill(data: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    nodata_mask = ~np.isfinite(data)
    nodata_pixels_in = int(np.count_nonzero(nodata_mask))
    eligible_pixels = int(data.size)

    report: dict[str, Any] = {
        "strategy": "inverse_distance_weighting",
        "enabled": True,
        "max_hole_pixels": int(GAP_FILL_MAX_HOLE_PIXELS),
        "max_total_fraction": float(GAP_FILL_MAX_TOTAL_FRACTION),
        "max_search_distance_px": float(GAP_FILL_MAX_SEARCH_DISTANCE_PX),
        "smoothing_iterations": int(GAP_FILL_SMOOTHING_ITERATIONS),
        "eligible_pixels": int(eligible_pixels),
        "nodata_pixels_in": int(nodata_pixels_in),
        "nodata_pixels_out": int(nodata_pixels_in),
        "filled_pixels": 0,
        "unresolved_candidate_pixels": 0,
        "hole_components_total": 0,
        "interior_hole_components": 0,
        "candidate_hole_components": 0,
        "candidate_hole_pixels": 0,
        "fill_applied": False,
        "reason": "no_nodata" if nodata_pixels_in == 0 else "pending",
    }
    if nodata_pixels_in == 0:
        return data, report

    candidates, component_stats = _collect_small_interior_holes(
        nodata_mask,
        max_hole_pixels=GAP_FILL_MAX_HOLE_PIXELS,
    )
    report.update(component_stats)

    candidate_hole_pixels = int(component_stats["candidate_hole_pixels"])
    if candidate_hole_pixels == 0:
        report["reason"] = "no_small_interior_holes"
        return data, report

    candidate_fraction = candidate_hole_pixels / max(eligible_pixels, 1)
    report["candidate_fraction"] = float(candidate_fraction)
    if candidate_fraction > GAP_FILL_MAX_TOTAL_FRACTION:
        report["reason"] = "candidate_fraction_above_threshold"
        return data, report

    filled_data = np.asarray(data, dtype=np.float64).copy()
    filled_pixels = 0
    for component in candidates:
        filled_pixels += _fill_small_hole_component(
            filled_data,
            component,
            max_search_distance=GAP_FILL_MAX_SEARCH_DISTANCE_PX,
            smoothing_iterations=GAP_FILL_SMOOTHING_ITERATIONS,
        )

    nodata_pixels_out = int(np.count_nonzero(~np.isfinite(filled_data)))
    unresolved_candidate_pixels = max(0, candidate_hole_pixels - int(filled_pixels))
    report.update(
        {
            "filled_pixels": int(filled_pixels),
            "unresolved_candidate_pixels": int(unresolved_candidate_pixels),
            "nodata_pixels_out": int(nodata_pixels_out),
            "fill_applied": bool(filled_pixels > 0),
            "reason": "filled" if filled_pixels > 0 else "no_fillable_neighbors",
        }
    )
    return filled_data, report


def _load_near_surface_property(
    wd: str,
    *,
    property_name: str,
    statistic: str,
    depth_weights_cm: Mapping[str, float],
    is_log10: bool,
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    top_path = _layer_path(wd, property_name=property_name, statistic=statistic, depth=NEAR_SURFACE_DEPTHS[0])
    sub_path = _layer_path(wd, property_name=property_name, statistic=statistic, depth=NEAR_SURFACE_DEPTHS[1])

    top_data, profile = _read_layer(top_path, is_log10=is_log10)
    sub_data, _ = _read_layer(sub_path, is_log10=is_log10)
    top_filled, top_report = _apply_conservative_gap_fill(top_data)
    sub_filled, sub_report = _apply_conservative_gap_fill(sub_data)

    averaged = _weighted_depth_average(
        top_filled,
        sub_filled,
        top_weight_cm=float(depth_weights_cm[NEAR_SURFACE_DEPTHS[0]]),
        sub_weight_cm=float(depth_weights_cm[NEAR_SURFACE_DEPTHS[1]]),
    )
    gap_fill_report = {
        "strategy": "inverse_distance_weighting",
        "max_hole_pixels": int(GAP_FILL_MAX_HOLE_PIXELS),
        "max_total_fraction": float(GAP_FILL_MAX_TOTAL_FRACTION),
        "max_search_distance_px": float(GAP_FILL_MAX_SEARCH_DISTANCE_PX),
        "smoothing_iterations": int(GAP_FILL_SMOOTHING_ITERATIONS),
        "top": top_report,
        "sub": sub_report,
        "averaged_nodata_pixels": int(np.count_nonzero(~np.isfinite(averaged))),
    }
    return averaged, profile, gap_fill_report


def _validate_depth_weights(depth_weights_cm: Mapping[str, float]) -> dict[str, float]:
    missing = [depth for depth in NEAR_SURFACE_DEPTHS if depth not in depth_weights_cm]
    if missing:
        raise ValueError(f"Missing near-surface depth weights for: {tuple(missing)}")

    validated: dict[str, float] = {}
    for depth in NEAR_SURFACE_DEPTHS:
        weight = float(depth_weights_cm[depth])
        if weight <= 0.0:
            raise ValueError(f"Depth weight for {depth} must be > 0, got {weight}")
        validated[depth] = weight
    return validated


def run_rusle_k_factors(
    wd: str,
    *,
    statistic: str = "mean",
    depth_weights_cm: Mapping[str, float] | None = None,
    selected_modes: Sequence[str] | None = None,
    default_k_mode: str = "polaris_nomograph",
    write_default_k: bool = True,
    reference_paths: Mapping[str, str] | None = None,
    comparison_points: Iterable[ReferencePoint | Mapping[str, Any] | Sequence[Any]] | None = None,
    point_crs: str = "EPSG:4326",
    reference_precedence: Sequence[str] = DEFAULT_REFERENCE_MODE_PRECEDENCE,
    thresholds: ComparisonThresholds = ComparisonThresholds(),
) -> RusleKResult:
    """Compute POLARIS K factors and optional benchmark comparison artifacts."""
    if reference_paths is not None and comparison_points is None:
        raise ValueError("comparison_points are required when reference_paths are provided")

    weights = _validate_depth_weights(depth_weights_cm or DEFAULT_DEPTH_WEIGHTS_CM)

    sand, profile, sand_gap_fill = _load_near_surface_property(
        wd,
        property_name="sand",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    silt, _, silt_gap_fill = _load_near_surface_property(
        wd,
        property_name="silt",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    clay, _, clay_gap_fill = _load_near_surface_property(
        wd,
        property_name="clay",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    om, _, om_gap_fill = _load_near_surface_property(
        wd,
        property_name="om",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=True,
    )
    ksat_cm_hr, _, ksat_gap_fill = _load_near_surface_property(
        wd,
        property_name="ksat",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=True,
    )

    nomograph = compute_polaris_nomograph_k(
        sand_pct=sand,
        silt_pct=silt,
        clay_pct=clay,
        om_pct=om,
        ksat_cm_hr=ksat_cm_hr,
    )
    epic = compute_polaris_epic_k(
        sand_pct=sand,
        silt_pct=silt,
        clay_pct=clay,
        om_pct=om,
    )

    rusle_dir = _join(wd, "rusle")
    os.makedirs(rusle_dir, exist_ok=True)

    nomograph_path = _join(rusle_dir, "k_polaris_nomograph.tif")
    epic_path = _join(rusle_dir, "k_polaris_epic.tif")
    manifest_path = _join(rusle_dir, "manifest.json")
    mode_arrays: dict[str, np.ndarray] = {
        "polaris_nomograph": nomograph,
        "polaris_epic": epic,
    }
    mode_paths: dict[str, str] = {
        "polaris_nomograph": nomograph_path,
        "polaris_epic": epic_path,
    }

    selected = [str(mode).strip() for mode in (selected_modes or ("polaris_nomograph", "polaris_epic"))]
    selected_modes_normalized = list(dict.fromkeys(mode for mode in selected if mode))
    if not selected_modes_normalized:
        raise ValueError("selected_modes must include at least one mode")

    invalid_modes = [mode for mode in selected_modes_normalized if mode not in mode_arrays]
    if invalid_modes:
        raise ValueError(f"Unsupported K mode(s): {invalid_modes}")

    default_mode = str(default_k_mode).strip()
    if default_mode not in mode_arrays:
        raise ValueError(f"default_k_mode must be one of {tuple(mode_arrays)}, got {default_k_mode!r}")
    if write_default_k and default_mode not in selected_modes_normalized:
        raise ValueError("default_k_mode must be included in selected_modes when write_default_k=True")

    wrote_nomograph = "polaris_nomograph" in selected_modes_normalized
    wrote_epic = "polaris_epic" in selected_modes_normalized
    if wrote_nomograph:
        _write_k_raster(nomograph_path, nomograph, profile)
    if wrote_epic:
        _write_k_raster(epic_path, epic, profile)

    default_k_path: str | None = None
    if write_default_k:
        default_k_path = _join(rusle_dir, "k.tif")
        _write_k_raster(default_k_path, mode_arrays[default_mode], profile)

    catalog_paths: list[str] = []
    if wrote_nomograph:
        catalog_paths.append(nomograph_path)
    if wrote_epic:
        catalog_paths.append(epic_path)
    if default_k_path is not None:
        catalog_paths.append(default_k_path)
    for path in catalog_paths:
        if path is None:
            continue
        update_catalog_entry(wd, _relative_path(wd, path))

    reference_samples_path: str | None = None
    comparison_path: str | None = None
    comparison_payload: dict[str, Any] | None = None
    harness_payload: dict[str, Any] | None = None

    if reference_paths is not None and comparison_points is not None:
        if not (wrote_nomograph and wrote_epic):
            raise ValueError("reference comparison requires both polaris_nomograph and polaris_epic outputs")
        harness_payload = run_reference_harness(
            reference_paths=reference_paths,
            points=comparison_points,
            point_crs=point_crs,
            precedence=reference_precedence,
        )
        reference_samples_path = _join(rusle_dir, "k_reference_samples.json")
        write_reference_samples_json(reference_samples_path, harness_payload)

        nomograph_samples = [
            asdict(sample)
            for sample in sample_points_from_raster(
                nomograph_path,
                comparison_points,
                mode="polaris_nomograph",
                point_crs=point_crs,
            )
        ]
        epic_samples = [
            asdict(sample)
            for sample in sample_points_from_raster(
                epic_path,
                comparison_points,
                mode="polaris_epic",
                point_crs=point_crs,
            )
        ]

        comparison_payload = compare_k_modes_to_reference(
            reference_samples=harness_payload["samples"],
            nomograph_samples=nomograph_samples,
            epic_samples=epic_samples,
            thresholds=thresholds,
        )
        comparison_payload["reference_mode"] = harness_payload["mode"]

        comparison_path = _join(rusle_dir, "k_benchmark_comparison_summary.json")
        write_comparison_summary_json(comparison_path, comparison_payload)

        update_catalog_entry(wd, _relative_path(wd, reference_samples_path))
        update_catalog_entry(wd, _relative_path(wd, comparison_path))

    k_manifest = {
        "generated_utc": _utc_now_iso(),
        "near_surface_depths": list(NEAR_SURFACE_DEPTHS),
        "near_surface_weights_cm": weights,
        "statistic": statistic,
        "selected_modes": selected_modes_normalized,
        "default_k_mode": default_mode,
        "gap_fill_policy": {
            "enabled": True,
            "strategy": "inverse_distance_weighting",
            "max_hole_pixels": int(GAP_FILL_MAX_HOLE_PIXELS),
            "max_total_fraction": float(GAP_FILL_MAX_TOTAL_FRACTION),
            "max_search_distance_px": float(GAP_FILL_MAX_SEARCH_DISTANCE_PX),
            "smoothing_iterations": int(GAP_FILL_SMOOTHING_ITERATIONS),
        },
        "gap_fill_summary": {
            "sand": sand_gap_fill,
            "silt": silt_gap_fill,
            "clay": clay_gap_fill,
            "om": om_gap_fill,
            "ksat": ksat_gap_fill,
        },
        "mode_contract": {
            "polaris_nomograph": {
                "vfs_source": "rusle2_estimated_from_sand",
                "structure_class_mapping": "modeled_texture_proxy_v1",
                "permeability_class_mapping": "modeled_ksat_proxy_v1",
            },
            "polaris_epic": {
                "oc_conversion_factor": OM_TO_OC_FACTOR,
                "om_clamp_pct": [0.0, 20.0],
            },
            "benchmark_precedence": list(reference_precedence),
            "cfvo_scope": "deferred",
        },
        "comparison_thresholds": {
            "abs_error_warn": thresholds.abs_error_warn,
            "rel_error_warn": thresholds.rel_error_warn,
        },
        "artifacts": {
            "nomograph": _relative_path(wd, nomograph_path) if wrote_nomograph else None,
            "epic": _relative_path(wd, epic_path) if wrote_epic else None,
            "k_default": _relative_path(wd, default_k_path) if default_k_path else None,
            "reference_samples": _relative_path(wd, reference_samples_path) if reference_samples_path else None,
            "comparison_summary": _relative_path(wd, comparison_path) if comparison_path else None,
        },
    }
    if harness_payload is not None:
        k_manifest["reference_mode"] = harness_payload["mode"]
    if comparison_payload is not None:
        k_manifest["comparison_metrics"] = {
            "polaris_nomograph": comparison_payload["modes"]["polaris_nomograph"]["metrics"],
            "polaris_epic": comparison_payload["modes"]["polaris_epic"]["metrics"],
        }

    update_k_manifest(manifest_path, k_manifest)

    return RusleKResult(
        nomograph=nomograph_path if wrote_nomograph else None,
        epic=epic_path if wrote_epic else None,
        k_default=default_k_path,
        manifest=manifest_path,
        reference_samples=reference_samples_path,
        comparison_summary=comparison_path,
    )
