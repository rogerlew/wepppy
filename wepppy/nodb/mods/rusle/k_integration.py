"""RUSLE K-factor integration for POLARIS estimators + benchmark harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import rasterio

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


__all__ = ["RusleKResult", "run_rusle_k_factors"]


@dataclass(frozen=True)
class RusleKResult:
    nomograph: str
    epic: str
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


def _load_near_surface_property(
    wd: str,
    *,
    property_name: str,
    statistic: str,
    depth_weights_cm: Mapping[str, float],
    is_log10: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    top_path = _layer_path(wd, property_name=property_name, statistic=statistic, depth=NEAR_SURFACE_DEPTHS[0])
    sub_path = _layer_path(wd, property_name=property_name, statistic=statistic, depth=NEAR_SURFACE_DEPTHS[1])

    top_data, profile = _read_layer(top_path, is_log10=is_log10)
    sub_data, _ = _read_layer(sub_path, is_log10=is_log10)

    averaged = _weighted_depth_average(
        top_data,
        sub_data,
        top_weight_cm=float(depth_weights_cm[NEAR_SURFACE_DEPTHS[0]]),
        sub_weight_cm=float(depth_weights_cm[NEAR_SURFACE_DEPTHS[1]]),
    )
    return averaged, profile


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

    sand, profile = _load_near_surface_property(
        wd,
        property_name="sand",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    silt, _ = _load_near_surface_property(
        wd,
        property_name="silt",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    clay, _ = _load_near_surface_property(
        wd,
        property_name="clay",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=False,
    )
    om, _ = _load_near_surface_property(
        wd,
        property_name="om",
        statistic=statistic,
        depth_weights_cm=weights,
        is_log10=True,
    )
    ksat_cm_hr, _ = _load_near_surface_property(
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

    _write_k_raster(nomograph_path, nomograph, profile)
    _write_k_raster(epic_path, epic, profile)

    default_k_path: str | None = None
    if write_default_k:
        default_k_path = _join(rusle_dir, "k.tif")
        _write_k_raster(default_k_path, nomograph, profile)

    for path in (nomograph_path, epic_path, default_k_path):
        if path is None:
            continue
        update_catalog_entry(wd, _relative_path(wd, path))

    reference_samples_path: str | None = None
    comparison_path: str | None = None
    comparison_payload: dict[str, Any] | None = None
    harness_payload: dict[str, Any] | None = None

    if reference_paths is not None and comparison_points is not None:
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
        "default_k_mode": "polaris_nomograph",
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
            "nomograph": _relative_path(wd, nomograph_path),
            "epic": _relative_path(wd, epic_path),
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
        nomograph=nomograph_path,
        epic=epic_path,
        k_default=default_k_path,
        manifest=manifest_path,
        reference_samples=reference_samples_path,
        comparison_summary=comparison_path,
    )
