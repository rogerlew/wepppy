#!/usr/bin/env python3
"""Repeatable daily closure audit for totalwatsed3 parquet outputs.

This tool audits internal depth consistency and daily closure residuals using
both reported depth columns and reconstructed depths from source volume columns.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DATE_SORT_COLUMNS = ["year", "julian", "sim_day_index"]


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    result = np.zeros_like(numerator, dtype=np.float64)
    np.divide(numerator, denominator, out=result, where=denominator > 0.0)
    return result


def _depth_from_volume(volume_m3: np.ndarray, area_m2: np.ndarray) -> np.ndarray:
    return _safe_divide(volume_m3, area_m2) * 1000.0


def _required_columns() -> tuple[str, ...]:
    return (
        "year",
        "julian",
        "sim_day_index",
        "month",
        "day_of_month",
        "water_year",
        "Area",
        "P",
        "RM",
        "runvol",
        "latqcc",
        "Dp",
        "Ep",
        "Es",
        "Er",
        "Total-Soil Water",
        "frozwt",
        "Snow-Water",
    )


def _optional_columns() -> tuple[str, ...]:
    return (
        "Precipitation",
        "Rain+Melt",
        "Runoff",
        "Lateral Flow",
        "Percolation",
        "ET",
        "Interception",
        "SoilWaterTotal",
        "ProfileDepth",
        "ProfilePorosityCap",
        "ProfileFCStore",
        "ProfileWPStore",
    )


def _has_non_null(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and frame[column].notna().any()


def load_dataset(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    missing = [name for name in _required_columns() if name not in frame.columns]
    if missing:
        raise KeyError(f"Missing required columns in {path}: {missing}")

    columns = list(_required_columns()) + [name for name in _optional_columns() if name in frame.columns]
    df = frame[columns].copy()
    for col in columns:
        if col not in DATE_SORT_COLUMNS and col not in ("month", "day_of_month", "water_year", "year", "julian", "sim_day_index"):
            df[col] = df[col].astype(float)
    return df.sort_values(DATE_SORT_COLUMNS, kind="mergesort").reset_index(drop=True)


def compute_daily_audit(df: pd.DataFrame) -> pd.DataFrame:
    audit = df.copy()

    area_m2 = audit["Area"].to_numpy(dtype=np.float64, copy=False)
    precip_calc_mm = _depth_from_volume(audit["P"].to_numpy(dtype=np.float64, copy=False), area_m2)
    rain_melt_calc_mm = _depth_from_volume(audit["RM"].to_numpy(dtype=np.float64, copy=False), area_m2)
    runoff_calc_mm = _depth_from_volume(audit["runvol"].to_numpy(dtype=np.float64, copy=False), area_m2)
    lateral_calc_mm = _depth_from_volume(audit["latqcc"].to_numpy(dtype=np.float64, copy=False), area_m2)
    percolation_calc_mm = _depth_from_volume(audit["Dp"].to_numpy(dtype=np.float64, copy=False), area_m2)
    et_calc_mm = _depth_from_volume(
        audit["Ep"].to_numpy(dtype=np.float64, copy=False)
        + audit["Es"].to_numpy(dtype=np.float64, copy=False)
        + audit["Er"].to_numpy(dtype=np.float64, copy=False),
        area_m2,
    )

    precip_reported_mm = audit["Precipitation"].to_numpy(dtype=np.float64, copy=False) if "Precipitation" in audit else precip_calc_mm
    rain_melt_reported_mm = audit["Rain+Melt"].to_numpy(dtype=np.float64, copy=False) if "Rain+Melt" in audit else rain_melt_calc_mm
    runoff_reported_mm = audit["Runoff"].to_numpy(dtype=np.float64, copy=False) if "Runoff" in audit else runoff_calc_mm
    lateral_reported_mm = audit["Lateral Flow"].to_numpy(dtype=np.float64, copy=False) if "Lateral Flow" in audit else lateral_calc_mm
    percolation_reported_mm = audit["Percolation"].to_numpy(dtype=np.float64, copy=False) if "Percolation" in audit else percolation_calc_mm
    et_reported_mm = audit["ET"].to_numpy(dtype=np.float64, copy=False) if "ET" in audit else et_calc_mm
    if "Interception" in audit:
        interception_reported_mm = np.nan_to_num(
            audit["Interception"].to_numpy(dtype=np.float64, copy=False),
            nan=0.0,
        )
    else:
        interception_reported_mm = np.zeros(audit.shape[0], dtype=np.float64)

    storage_mm = (
        audit["Total-Soil Water"].to_numpy(dtype=np.float64, copy=False)
        + audit["frozwt"].to_numpy(dtype=np.float64, copy=False)
        + audit["Snow-Water"].to_numpy(dtype=np.float64, copy=False)
    )
    storage_delta_mm = np.diff(storage_mm, prepend=storage_mm[0])
    if _has_non_null(audit, "SoilWaterTotal"):
        enriched_storage_mm = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            + audit["Snow-Water"].to_numpy(dtype=np.float64, copy=False)
        )
        enriched_storage_delta_mm = np.diff(enriched_storage_mm, prepend=enriched_storage_mm[0])
    else:
        enriched_storage_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)
        enriched_storage_delta_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)

    # Primary closure accounting uses total precipitation (P/Precipitation), so
    # snowfall water is counted on the input side when Snow-Water is in storage.
    closure_reported_basic_mm = precip_reported_mm - (
        runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm + interception_reported_mm
    )
    closure_reconstructed_basic_mm = precip_reported_mm - (
        runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm + interception_reported_mm
    )
    closure_reported_with_storage_mm = closure_reported_basic_mm - storage_delta_mm
    closure_reconstructed_with_storage_mm = closure_reconstructed_basic_mm - storage_delta_mm

    # Keep Rain+Melt-based closure as a diagnostic to highlight snowpack timing.
    closure_reported_with_storage_rain_melt_mm = rain_melt_reported_mm - (
        runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm + interception_reported_mm
    ) - storage_delta_mm
    closure_reconstructed_with_storage_rain_melt_mm = rain_melt_reported_mm - (
        runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm + interception_reported_mm
    ) - storage_delta_mm

    if np.isnan(enriched_storage_delta_mm).all():
        closure_reported_with_enriched_storage_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)
        closure_reconstructed_with_enriched_storage_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)
        closure_reported_with_enriched_storage_rain_melt_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)
        closure_reconstructed_with_enriched_storage_rain_melt_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)
    else:
        closure_reported_with_enriched_storage_mm = closure_reported_basic_mm - enriched_storage_delta_mm
        closure_reconstructed_with_enriched_storage_mm = closure_reconstructed_basic_mm - enriched_storage_delta_mm
        closure_reported_with_enriched_storage_rain_melt_mm = rain_melt_reported_mm - (
            runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm + interception_reported_mm
        ) - enriched_storage_delta_mm
        closure_reconstructed_with_enriched_storage_rain_melt_mm = rain_melt_reported_mm - (
            runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm + interception_reported_mm
        ) - enriched_storage_delta_mm

    runoff_to_precip_reported_pct = _safe_divide(runoff_reported_mm, precip_reported_mm) * 100.0
    runoff_to_precip_reconstructed_pct = _safe_divide(runoff_calc_mm, precip_reported_mm) * 100.0

    audit["audit_precip_calc_mm"] = precip_calc_mm
    audit["audit_rain_melt_calc_mm"] = rain_melt_calc_mm
    audit["audit_runoff_calc_mm"] = runoff_calc_mm
    audit["audit_lateral_calc_mm"] = lateral_calc_mm
    audit["audit_percolation_calc_mm"] = percolation_calc_mm
    audit["audit_et_calc_mm"] = et_calc_mm

    audit["audit_precip_reported_mm"] = precip_reported_mm
    audit["audit_rain_melt_reported_mm"] = rain_melt_reported_mm
    audit["audit_runoff_reported_mm"] = runoff_reported_mm
    audit["audit_lateral_reported_mm"] = lateral_reported_mm
    audit["audit_percolation_reported_mm"] = percolation_reported_mm
    audit["audit_et_reported_mm"] = et_reported_mm
    audit["audit_interception_reported_mm"] = interception_reported_mm

    audit["audit_storage_mm"] = storage_mm
    audit["audit_storage_delta_mm"] = storage_delta_mm
    audit["audit_enriched_storage_mm"] = enriched_storage_mm
    audit["audit_enriched_storage_delta_mm"] = enriched_storage_delta_mm
    if _has_non_null(audit, "SoilWaterTotal"):
        audit["audit_soilwatertotal_vs_legacy_storage_mm"] = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            - (
                audit["Total-Soil Water"].to_numpy(dtype=np.float64, copy=False)
                + audit["frozwt"].to_numpy(dtype=np.float64, copy=False)
            )
        )
    else:
        audit["audit_soilwatertotal_vs_legacy_storage_mm"] = np.full(audit.shape[0], np.nan, dtype=np.float64)

    if _has_non_null(audit, "SoilWaterTotal") and _has_non_null(audit, "ProfilePorosityCap"):
        soilwater_total = audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
        profile_porosity_cap = audit["ProfilePorosityCap"].to_numpy(dtype=np.float64, copy=False)
        audit["audit_soilwater_to_porosity_fraction"] = _safe_divide(soilwater_total, profile_porosity_cap)
        audit["audit_soilwater_minus_porositycap_mm"] = soilwater_total - profile_porosity_cap
    else:
        audit["audit_soilwater_to_porosity_fraction"] = np.full(audit.shape[0], np.nan, dtype=np.float64)
        audit["audit_soilwater_minus_porositycap_mm"] = np.full(audit.shape[0], np.nan, dtype=np.float64)

    if _has_non_null(audit, "SoilWaterTotal") and _has_non_null(audit, "ProfileFCStore"):
        audit["audit_soilwater_minus_fc_mm"] = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            - audit["ProfileFCStore"].to_numpy(dtype=np.float64, copy=False)
        )
    else:
        audit["audit_soilwater_minus_fc_mm"] = np.full(audit.shape[0], np.nan, dtype=np.float64)

    if _has_non_null(audit, "SoilWaterTotal") and _has_non_null(audit, "ProfileWPStore"):
        audit["audit_soilwater_minus_wp_mm"] = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            - audit["ProfileWPStore"].to_numpy(dtype=np.float64, copy=False)
        )
    else:
        audit["audit_soilwater_minus_wp_mm"] = np.full(audit.shape[0], np.nan, dtype=np.float64)

    if _has_non_null(audit, "ProfilePorosityCap") and _has_non_null(audit, "ProfileFCStore"):
        audit["audit_profile_order_fc_gt_porosity"] = (
            audit["ProfileFCStore"].to_numpy(dtype=np.float64, copy=False)
            > audit["ProfilePorosityCap"].to_numpy(dtype=np.float64, copy=False)
        )
    else:
        audit["audit_profile_order_fc_gt_porosity"] = np.full(audit.shape[0], False, dtype=bool)

    if _has_non_null(audit, "ProfileFCStore") and _has_non_null(audit, "ProfileWPStore"):
        audit["audit_profile_order_wp_gt_fc"] = (
            audit["ProfileWPStore"].to_numpy(dtype=np.float64, copy=False)
            > audit["ProfileFCStore"].to_numpy(dtype=np.float64, copy=False)
        )
    else:
        audit["audit_profile_order_wp_gt_fc"] = np.full(audit.shape[0], False, dtype=bool)

    if _has_non_null(audit, "SoilWaterTotal") and _has_non_null(audit, "ProfilePorosityCap"):
        audit["audit_soilwater_gt_porositycap"] = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            > (audit["ProfilePorosityCap"].to_numpy(dtype=np.float64, copy=False) + 1.0e-9)
        )
    else:
        audit["audit_soilwater_gt_porositycap"] = np.full(audit.shape[0], False, dtype=bool)

    if _has_non_null(audit, "SoilWaterTotal") and _has_non_null(audit, "ProfileWPStore"):
        audit["audit_soilwater_lt_wpstore"] = (
            audit["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
            < (audit["ProfileWPStore"].to_numpy(dtype=np.float64, copy=False) - 1.0e-9)
        )
    else:
        audit["audit_soilwater_lt_wpstore"] = np.full(audit.shape[0], False, dtype=bool)

    audit["audit_runoff_consistency_mm"] = runoff_reported_mm - runoff_calc_mm
    audit["audit_lateral_consistency_mm"] = lateral_reported_mm - lateral_calc_mm
    audit["audit_percolation_consistency_mm"] = percolation_reported_mm - percolation_calc_mm
    audit["audit_et_consistency_mm"] = et_reported_mm - et_calc_mm

    audit["audit_closure_reported_basic_mm"] = closure_reported_basic_mm
    audit["audit_closure_reconstructed_basic_mm"] = closure_reconstructed_basic_mm
    audit["audit_closure_reported_with_storage_mm"] = closure_reported_with_storage_mm
    audit["audit_closure_reconstructed_with_storage_mm"] = closure_reconstructed_with_storage_mm
    audit["audit_closure_reported_with_enriched_storage_mm"] = closure_reported_with_enriched_storage_mm
    audit["audit_closure_reconstructed_with_enriched_storage_mm"] = closure_reconstructed_with_enriched_storage_mm
    audit["audit_closure_reported_with_storage_rain_melt_mm"] = closure_reported_with_storage_rain_melt_mm
    audit["audit_closure_reconstructed_with_storage_rain_melt_mm"] = closure_reconstructed_with_storage_rain_melt_mm
    audit["audit_closure_reported_with_enriched_storage_rain_melt_mm"] = (
        closure_reported_with_enriched_storage_rain_melt_mm
    )
    audit["audit_closure_reconstructed_with_enriched_storage_rain_melt_mm"] = (
        closure_reconstructed_with_enriched_storage_rain_melt_mm
    )

    audit["audit_runoff_to_precip_reported_pct"] = runoff_to_precip_reported_pct
    audit["audit_runoff_to_precip_reconstructed_pct"] = runoff_to_precip_reconstructed_pct

    return audit


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "p50": float(np.quantile(values, 0.50)),
        "p90": float(np.quantile(values, 0.90)),
        "p95": float(np.quantile(values, 0.95)),
        "p99": float(np.quantile(values, 0.99)),
        "max_abs": float(np.max(np.abs(values))) if values.size else 0.0,
    }


def _safe_ratio_scalar(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return float(numerator / denominator)


def _optional_float(value: float) -> float | None:
    if np.isnan(value):
        return None
    return float(value)


def _nan_sum(series: pd.Series) -> float:
    values = series.to_numpy(dtype=np.float64, copy=False)
    if np.isnan(values).all():
        return float("nan")
    return float(np.nansum(values))


def _nan_mean_abs(series: pd.Series) -> float:
    values = series.to_numpy(dtype=np.float64, copy=False)
    if np.isnan(values).all():
        return float("nan")
    return float(np.nanmean(np.abs(values)))


def _build_whole_run_closure(audit: pd.DataFrame) -> dict[str, float]:
    rain_melt_total_mm = float(audit["audit_rain_melt_reported_mm"].sum())
    precip_total_mm = float(audit["audit_precip_reported_mm"].sum())
    runoff_reported_total_mm = float(audit["audit_runoff_reported_mm"].sum())
    runoff_reconstructed_total_mm = float(audit["audit_runoff_calc_mm"].sum())
    lateral_reported_total_mm = float(audit["audit_lateral_reported_mm"].sum())
    lateral_reconstructed_total_mm = float(audit["audit_lateral_calc_mm"].sum())
    percolation_reported_total_mm = float(audit["audit_percolation_reported_mm"].sum())
    percolation_reconstructed_total_mm = float(audit["audit_percolation_calc_mm"].sum())
    et_reported_total_mm = float(audit["audit_et_reported_mm"].sum())
    et_reconstructed_total_mm = float(audit["audit_et_calc_mm"].sum())
    interception_reported_total_mm = float(audit["audit_interception_reported_mm"].sum())
    storage_change_mm = float(audit["audit_storage_mm"].iloc[-1] - audit["audit_storage_mm"].iloc[0])
    closure_reported_basic_total_mm = float(audit["audit_closure_reported_basic_mm"].sum())
    closure_reconstructed_basic_total_mm = float(audit["audit_closure_reconstructed_basic_mm"].sum())
    closure_reported_with_storage_total_mm = float(audit["audit_closure_reported_with_storage_mm"].sum())
    closure_reconstructed_with_storage_total_mm = float(audit["audit_closure_reconstructed_with_storage_mm"].sum())
    closure_reported_with_storage_rain_melt_total_mm = float(
        audit["audit_closure_reported_with_storage_rain_melt_mm"].sum()
    )
    closure_reconstructed_with_storage_rain_melt_total_mm = float(
        audit["audit_closure_reconstructed_with_storage_rain_melt_mm"].sum()
    )
    enriched_storage_available = bool(audit["audit_enriched_storage_mm"].notna().any())
    enriched_storage_change_mm = float("nan")
    closure_reported_with_enriched_storage_total_mm = float("nan")
    closure_reconstructed_with_enriched_storage_total_mm = float("nan")
    closure_reported_with_enriched_storage_rain_melt_total_mm = float("nan")
    closure_reconstructed_with_enriched_storage_rain_melt_total_mm = float("nan")
    if enriched_storage_available:
        first_enriched = audit["audit_enriched_storage_mm"].dropna().iloc[0]
        last_enriched = audit["audit_enriched_storage_mm"].dropna().iloc[-1]
        enriched_storage_change_mm = float(last_enriched - first_enriched)
        closure_reported_with_enriched_storage_total_mm = _nan_sum(
            audit["audit_closure_reported_with_enriched_storage_mm"]
        )
        closure_reconstructed_with_enriched_storage_total_mm = _nan_sum(
            audit["audit_closure_reconstructed_with_enriched_storage_mm"]
        )
        closure_reported_with_enriched_storage_rain_melt_total_mm = _nan_sum(
            audit["audit_closure_reported_with_enriched_storage_rain_melt_mm"]
        )
        closure_reconstructed_with_enriched_storage_rain_melt_total_mm = _nan_sum(
            audit["audit_closure_reconstructed_with_enriched_storage_rain_melt_mm"]
        )
    soilwater_total_available = bool(audit["audit_soilwatertotal_vs_legacy_storage_mm"].notna().any())
    soilwater_total_vs_legacy_max_abs_mm = float("nan")
    if soilwater_total_available:
        soilwater_total_vs_legacy_max_abs_mm = float(
            np.nanmax(np.abs(audit["audit_soilwatertotal_vs_legacy_storage_mm"].to_numpy(dtype=np.float64, copy=False)))
        )
    profile_terms_available = bool(audit["audit_soilwater_to_porosity_fraction"].notna().any())
    profile_order_fc_gt_porosity_days = int(audit["audit_profile_order_fc_gt_porosity"].sum())
    profile_order_wp_gt_fc_days = int(audit["audit_profile_order_wp_gt_fc"].sum())
    soilwater_gt_porositycap_days = int(audit["audit_soilwater_gt_porositycap"].sum())
    soilwater_lt_wpstore_days = int(audit["audit_soilwater_lt_wpstore"].sum())
    row_count = float(audit.shape[0])

    return {
        "closure_basis_primary": "precipitation",
        "closure_basis_diagnostic": "rain_melt",
        "precip_total_mm": precip_total_mm,
        "rain_melt_total_mm": rain_melt_total_mm,
        "runoff_reported_total_mm": runoff_reported_total_mm,
        "runoff_reconstructed_total_mm": runoff_reconstructed_total_mm,
        "lateral_reported_total_mm": lateral_reported_total_mm,
        "lateral_reconstructed_total_mm": lateral_reconstructed_total_mm,
        "percolation_reported_total_mm": percolation_reported_total_mm,
        "percolation_reconstructed_total_mm": percolation_reconstructed_total_mm,
        "et_reported_total_mm": et_reported_total_mm,
        "et_reconstructed_total_mm": et_reconstructed_total_mm,
        "interception_reported_total_mm": interception_reported_total_mm,
        "storage_change_mm": storage_change_mm,
        "closure_reported_basic_total_mm": closure_reported_basic_total_mm,
        "closure_reconstructed_basic_total_mm": closure_reconstructed_basic_total_mm,
        "closure_reported_with_storage_total_mm": closure_reported_with_storage_total_mm,
        "closure_reconstructed_with_storage_total_mm": closure_reconstructed_with_storage_total_mm,
        "closure_reported_with_storage_rain_melt_total_mm": closure_reported_with_storage_rain_melt_total_mm,
        "closure_reconstructed_with_storage_rain_melt_total_mm": closure_reconstructed_with_storage_rain_melt_total_mm,
        "enriched_storage_available": enriched_storage_available,
        "enriched_storage_change_mm": _optional_float(enriched_storage_change_mm),
        "soilwater_total_available": soilwater_total_available,
        "soilwatertotal_vs_legacy_max_abs_mm": _optional_float(soilwater_total_vs_legacy_max_abs_mm),
        "profile_terms_available": profile_terms_available,
        "profile_order_fc_gt_porosity_days": profile_order_fc_gt_porosity_days,
        "profile_order_wp_gt_fc_days": profile_order_wp_gt_fc_days,
        "soilwater_gt_porositycap_days": soilwater_gt_porositycap_days,
        "soilwater_lt_wpstore_days": soilwater_lt_wpstore_days,
        "closure_reported_with_enriched_storage_total_mm": _optional_float(
            closure_reported_with_enriched_storage_total_mm
        ),
        "closure_reconstructed_with_enriched_storage_total_mm": _optional_float(
            closure_reconstructed_with_enriched_storage_total_mm
        ),
        "closure_reported_with_enriched_storage_rain_melt_total_mm": _optional_float(
            closure_reported_with_enriched_storage_rain_melt_total_mm
        ),
        "closure_reconstructed_with_enriched_storage_rain_melt_total_mm": _optional_float(
            closure_reconstructed_with_enriched_storage_rain_melt_total_mm
        ),
        "closure_reported_with_storage_pct_of_precip": _safe_ratio_scalar(
            closure_reported_with_storage_total_mm * 100.0,
            precip_total_mm,
        ),
        "closure_reconstructed_with_storage_pct_of_precip": _safe_ratio_scalar(
            closure_reconstructed_with_storage_total_mm * 100.0,
            precip_total_mm,
        ),
        "closure_reported_with_enriched_storage_pct_of_precip": _optional_float(
            _safe_ratio_scalar(closure_reported_with_enriched_storage_total_mm * 100.0, precip_total_mm)
        ),
        "closure_reconstructed_with_enriched_storage_pct_of_precip": _optional_float(
            _safe_ratio_scalar(closure_reconstructed_with_enriched_storage_total_mm * 100.0, precip_total_mm)
        ),
        "closure_reported_with_storage_rain_melt_pct_of_rain_melt": _safe_ratio_scalar(
            closure_reported_with_storage_rain_melt_total_mm * 100.0,
            rain_melt_total_mm,
        ),
        "closure_reconstructed_with_storage_rain_melt_pct_of_rain_melt": _safe_ratio_scalar(
            closure_reconstructed_with_storage_rain_melt_total_mm * 100.0,
            rain_melt_total_mm,
        ),
        "closure_reported_with_enriched_storage_rain_melt_pct_of_rain_melt": _optional_float(
            _safe_ratio_scalar(closure_reported_with_enriched_storage_rain_melt_total_mm * 100.0, rain_melt_total_mm)
        ),
        "closure_reconstructed_with_enriched_storage_rain_melt_pct_of_rain_melt": _optional_float(
            _safe_ratio_scalar(
                closure_reconstructed_with_enriched_storage_rain_melt_total_mm * 100.0,
                rain_melt_total_mm,
            )
        ),
        # Backward compatibility aliases: these names historically represented
        # Rain+Melt closure percentages.
        "closure_reported_with_storage_pct_of_rain_melt": _safe_ratio_scalar(
            closure_reported_with_storage_rain_melt_total_mm * 100.0,
            rain_melt_total_mm,
        ),
        "closure_reconstructed_with_storage_pct_of_rain_melt": _safe_ratio_scalar(
            closure_reconstructed_with_storage_rain_melt_total_mm * 100.0,
            rain_melt_total_mm,
        ),
        "closure_reported_with_enriched_storage_pct_of_rain_melt": _optional_float(
            _safe_ratio_scalar(closure_reported_with_enriched_storage_rain_melt_total_mm * 100.0, rain_melt_total_mm)
        ),
        "closure_reconstructed_with_enriched_storage_pct_of_rain_melt": _optional_float(
            _safe_ratio_scalar(
                closure_reconstructed_with_enriched_storage_rain_melt_total_mm * 100.0,
                rain_melt_total_mm,
            )
        ),
        "mean_daily_closure_reported_with_storage_mm": _safe_ratio_scalar(
            closure_reported_with_storage_total_mm,
            row_count,
        ),
        "mean_daily_closure_reconstructed_with_storage_mm": _safe_ratio_scalar(
            closure_reconstructed_with_storage_total_mm,
            row_count,
        ),
        "mean_abs_daily_closure_reported_with_storage_mm": float(
            np.abs(audit["audit_closure_reported_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)).mean()
        ),
        "mean_abs_daily_closure_reconstructed_with_storage_mm": float(
            np.abs(audit["audit_closure_reconstructed_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)).mean()
        ),
        "mean_abs_daily_closure_reported_with_enriched_storage_mm": _optional_float(
            _nan_mean_abs(audit["audit_closure_reported_with_enriched_storage_mm"])
        ),
        "mean_abs_daily_closure_reconstructed_with_enriched_storage_mm": _optional_float(
            _nan_mean_abs(audit["audit_closure_reconstructed_with_enriched_storage_mm"])
        ),
        "mean_abs_daily_closure_reported_with_storage_rain_melt_mm": float(
            np.abs(audit["audit_closure_reported_with_storage_rain_melt_mm"].to_numpy(dtype=np.float64, copy=False)).mean()
        ),
        "mean_abs_daily_closure_reconstructed_with_storage_rain_melt_mm": float(
            np.abs(
                audit["audit_closure_reconstructed_with_storage_rain_melt_mm"].to_numpy(dtype=np.float64, copy=False)
            ).mean()
        ),
        "mean_abs_daily_closure_reported_with_enriched_storage_rain_melt_mm": _optional_float(
            _nan_mean_abs(audit["audit_closure_reported_with_enriched_storage_rain_melt_mm"])
        ),
        "mean_abs_daily_closure_reconstructed_with_enriched_storage_rain_melt_mm": _optional_float(
            _nan_mean_abs(audit["audit_closure_reconstructed_with_enriched_storage_rain_melt_mm"])
        ),
    }


def build_summary(audit: pd.DataFrame, source_path: Path) -> dict[str, Any]:
    closure_reported = audit["audit_closure_reported_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    closure_reconstructed = audit["audit_closure_reconstructed_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    closure_enriched = audit["audit_closure_reconstructed_with_enriched_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    closure_reported_rain_melt = audit["audit_closure_reported_with_storage_rain_melt_mm"].to_numpy(
        dtype=np.float64, copy=False
    )
    closure_reconstructed_rain_melt = audit["audit_closure_reconstructed_with_storage_rain_melt_mm"].to_numpy(
        dtype=np.float64, copy=False
    )
    closure_enriched_rain_melt = audit["audit_closure_reconstructed_with_enriched_storage_rain_melt_mm"].to_numpy(
        dtype=np.float64, copy=False
    )
    storage_delta = audit["audit_soilwatertotal_vs_legacy_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    soilwater_to_porosity = audit["audit_soilwater_to_porosity_fraction"].to_numpy(dtype=np.float64, copy=False)
    soilwater_minus_fc = audit["audit_soilwater_minus_fc_mm"].to_numpy(dtype=np.float64, copy=False)
    soilwater_minus_wp = audit["audit_soilwater_minus_wp_mm"].to_numpy(dtype=np.float64, copy=False)
    runoff_consistency = audit["audit_runoff_consistency_mm"].to_numpy(dtype=np.float64, copy=False)
    interception_reported = audit["audit_interception_reported_mm"].to_numpy(dtype=np.float64, copy=False)

    top_runoff = audit.iloc[int(np.argmax(audit["audit_runoff_reported_mm"].to_numpy(dtype=np.float64, copy=False)))]

    return {
        "source": str(source_path),
        "rows": int(audit.shape[0]),
        "date_min": {
            "year": int(audit["year"].iloc[0]),
            "julian": int(audit["julian"].iloc[0]),
            "month": int(audit["month"].iloc[0]),
            "day_of_month": int(audit["day_of_month"].iloc[0]),
        },
        "date_max": {
            "year": int(audit["year"].iloc[-1]),
            "julian": int(audit["julian"].iloc[-1]),
            "month": int(audit["month"].iloc[-1]),
            "day_of_month": int(audit["day_of_month"].iloc[-1]),
        },
        "max_reported_runoff_mm": float(np.max(audit["audit_runoff_reported_mm"].to_numpy(dtype=np.float64, copy=False))),
        "max_reconstructed_runoff_mm": float(np.max(audit["audit_runoff_calc_mm"].to_numpy(dtype=np.float64, copy=False))),
        "max_runoff_to_precip_reported_pct": float(np.max(audit["audit_runoff_to_precip_reported_pct"].to_numpy(dtype=np.float64, copy=False))),
        "max_runoff_to_precip_reconstructed_pct": float(np.max(audit["audit_runoff_to_precip_reconstructed_pct"].to_numpy(dtype=np.float64, copy=False))),
        "runoff_consistency_mm": _quantiles(runoff_consistency),
        "interception_reported_mm": _quantiles(interception_reported),
        "closure_reported_with_storage_mm": _quantiles(closure_reported),
        "closure_reconstructed_with_storage_mm": _quantiles(closure_reconstructed),
        "closure_reconstructed_with_enriched_storage_mm": (
            None if np.isnan(closure_enriched).all() else _quantiles(closure_enriched[~np.isnan(closure_enriched)])
        ),
        "closure_reported_with_storage_rain_melt_mm": _quantiles(closure_reported_rain_melt),
        "closure_reconstructed_with_storage_rain_melt_mm": _quantiles(closure_reconstructed_rain_melt),
        "closure_reconstructed_with_enriched_storage_rain_melt_mm": (
            None
            if np.isnan(closure_enriched_rain_melt).all()
            else _quantiles(closure_enriched_rain_melt[~np.isnan(closure_enriched_rain_melt)])
        ),
        "soilwatertotal_vs_legacy_storage_mm": (
            None if np.isnan(storage_delta).all() else _quantiles(storage_delta[~np.isnan(storage_delta)])
        ),
        "soilwater_to_porosity_fraction": (
            None if np.isnan(soilwater_to_porosity).all() else _quantiles(soilwater_to_porosity[~np.isnan(soilwater_to_porosity)])
        ),
        "soilwater_minus_fc_mm": (
            None if np.isnan(soilwater_minus_fc).all() else _quantiles(soilwater_minus_fc[~np.isnan(soilwater_minus_fc)])
        ),
        "soilwater_minus_wp_mm": (
            None if np.isnan(soilwater_minus_wp).all() else _quantiles(soilwater_minus_wp[~np.isnan(soilwater_minus_wp)])
        ),
        "whole_run_closure": _build_whole_run_closure(audit),
        "max_reported_runoff_day": {
            "year": int(top_runoff["year"]),
            "julian": int(top_runoff["julian"]),
            "month": int(top_runoff["month"]),
            "day_of_month": int(top_runoff["day_of_month"]),
            "reported_runoff_mm": float(top_runoff["audit_runoff_reported_mm"]),
            "reconstructed_runoff_mm": float(top_runoff["audit_runoff_calc_mm"]),
            "runoff_consistency_mm": float(top_runoff["audit_runoff_consistency_mm"]),
            "rain_melt_reported_mm": float(top_runoff["audit_rain_melt_reported_mm"]),
            "precip_reported_mm": float(top_runoff["audit_precip_reported_mm"]),
        },
    }


def _build_output_dir(parquet_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return parquet_path.parent / "audit_totalwatsed3_daily_closure"


def _top_anomalies(audit: pd.DataFrame, top_n: int) -> pd.DataFrame:
    subset = audit[
        [
            "year",
            "julian",
            "month",
            "day_of_month",
            "water_year",
            "audit_rain_melt_reported_mm",
            "audit_precip_reported_mm",
            "audit_runoff_reported_mm",
            "audit_runoff_calc_mm",
            "audit_runoff_consistency_mm",
            "audit_lateral_reported_mm",
            "audit_lateral_calc_mm",
            "audit_et_reported_mm",
            "audit_et_calc_mm",
            "audit_percolation_reported_mm",
            "audit_percolation_calc_mm",
            "audit_interception_reported_mm",
            "audit_storage_delta_mm",
            "audit_enriched_storage_delta_mm",
            "audit_closure_reported_with_storage_mm",
            "audit_closure_reconstructed_with_storage_mm",
            "audit_closure_reported_with_enriched_storage_mm",
            "audit_closure_reconstructed_with_enriched_storage_mm",
            "audit_closure_reported_with_storage_rain_melt_mm",
            "audit_closure_reconstructed_with_storage_rain_melt_mm",
            "audit_closure_reported_with_enriched_storage_rain_melt_mm",
            "audit_closure_reconstructed_with_enriched_storage_rain_melt_mm",
            "audit_soilwatertotal_vs_legacy_storage_mm",
            "audit_soilwater_to_porosity_fraction",
            "audit_soilwater_minus_fc_mm",
            "audit_soilwater_minus_wp_mm",
            "audit_profile_order_fc_gt_porosity",
            "audit_profile_order_wp_gt_fc",
            "audit_soilwater_gt_porositycap",
            "audit_soilwater_lt_wpstore",
            "audit_runoff_to_precip_reported_pct",
            "audit_runoff_to_precip_reconstructed_pct",
        ]
    ].copy()

    subset["abs_closure_reported_with_storage_mm"] = subset["audit_closure_reported_with_storage_mm"].abs()
    subset["abs_runoff_consistency_mm"] = subset["audit_runoff_consistency_mm"].abs()
    subset = subset.sort_values(
        ["abs_closure_reported_with_storage_mm", "abs_runoff_consistency_mm"],
        ascending=[False, False],
        kind="mergesort",
    )
    return subset.head(top_n).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet_path", help="Path to totalwatsed3.parquet")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for audit outputs (default: sibling folder audit_totalwatsed3_daily_closure)",
    )
    parser.add_argument("--top-n", type=int, default=25, help="Number of top anomaly days to export")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.parquet_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    output_dir = _build_output_dir(source_path, Path(args.output_dir).expanduser().resolve() if args.output_dir else None)
    output_dir.mkdir(parents=True, exist_ok=True)

    audit = compute_daily_audit(load_dataset(source_path))
    summary = build_summary(audit, source_path)
    top = _top_anomalies(audit, max(1, int(args.top_n)))

    summary_path = output_dir / "daily_closure_audit_summary.json"
    top_path = output_dir / "daily_closure_audit_top_days.csv"

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    top.to_csv(top_path, index=False)

    print(f"source={source_path}")
    print(f"rows={summary['rows']}")
    print(f"max_reported_runoff_mm={summary['max_reported_runoff_mm']:.6f}")
    print(f"max_reconstructed_runoff_mm={summary['max_reconstructed_runoff_mm']:.6f}")
    print(f"max_runoff_to_precip_reported_pct={summary['max_runoff_to_precip_reported_pct']:.6f}")
    print(f"max_runoff_to_precip_reconstructed_pct={summary['max_runoff_to_precip_reconstructed_pct']:.6f}")
    print(
        "closure_reconstructed_with_storage_total_mm="
        f"{summary['whole_run_closure']['closure_reconstructed_with_storage_total_mm']:.6f}"
    )
    print(
        "closure_reconstructed_with_storage_pct_of_precip="
        f"{summary['whole_run_closure']['closure_reconstructed_with_storage_pct_of_precip']:.6f}"
    )
    print(
        "closure_reconstructed_with_storage_rain_melt_pct_of_rain_melt="
        f"{summary['whole_run_closure']['closure_reconstructed_with_storage_rain_melt_pct_of_rain_melt']:.6f}"
    )
    print(
        "interception_reported_total_mm="
        f"{summary['whole_run_closure']['interception_reported_total_mm']:.6f}"
    )
    if summary["whole_run_closure"]["enriched_storage_available"]:
        print(
            "closure_reconstructed_with_enriched_storage_total_mm="
            f"{summary['whole_run_closure']['closure_reconstructed_with_enriched_storage_total_mm']:.6f}"
        )
        print(
            "closure_reconstructed_with_enriched_storage_pct_of_precip="
            f"{summary['whole_run_closure']['closure_reconstructed_with_enriched_storage_pct_of_precip']:.6f}"
        )
        print(
            "closure_reconstructed_with_enriched_storage_rain_melt_pct_of_rain_melt="
            f"{summary['whole_run_closure']['closure_reconstructed_with_enriched_storage_rain_melt_pct_of_rain_melt']:.6f}"
        )
    if summary["whole_run_closure"]["soilwater_total_available"]:
        print(
            "soilwatertotal_vs_legacy_max_abs_mm="
            f"{summary['whole_run_closure']['soilwatertotal_vs_legacy_max_abs_mm']:.6f}"
        )
    print(
        "profile_violations_days="
        f"fc_gt_porosity:{summary['whole_run_closure']['profile_order_fc_gt_porosity_days']},"
        f"wp_gt_fc:{summary['whole_run_closure']['profile_order_wp_gt_fc_days']},"
        f"soilwater_gt_porosity:{summary['whole_run_closure']['soilwater_gt_porositycap_days']},"
        f"soilwater_lt_wp:{summary['whole_run_closure']['soilwater_lt_wpstore_days']}"
    )
    print(f"summary_json={summary_path}")
    print(f"top_days_csv={top_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
