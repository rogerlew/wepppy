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
    )


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

    storage_mm = (
        audit["Total-Soil Water"].to_numpy(dtype=np.float64, copy=False)
        + audit["frozwt"].to_numpy(dtype=np.float64, copy=False)
        + audit["Snow-Water"].to_numpy(dtype=np.float64, copy=False)
    )
    storage_delta_mm = np.diff(storage_mm, prepend=storage_mm[0])

    closure_reported_basic_mm = rain_melt_reported_mm - (
        runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm
    )
    closure_reconstructed_basic_mm = rain_melt_reported_mm - (
        runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm
    )
    closure_reported_with_storage_mm = closure_reported_basic_mm - storage_delta_mm
    closure_reconstructed_with_storage_mm = closure_reconstructed_basic_mm - storage_delta_mm

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

    audit["audit_storage_mm"] = storage_mm
    audit["audit_storage_delta_mm"] = storage_delta_mm

    audit["audit_runoff_consistency_mm"] = runoff_reported_mm - runoff_calc_mm
    audit["audit_lateral_consistency_mm"] = lateral_reported_mm - lateral_calc_mm
    audit["audit_percolation_consistency_mm"] = percolation_reported_mm - percolation_calc_mm
    audit["audit_et_consistency_mm"] = et_reported_mm - et_calc_mm

    audit["audit_closure_reported_basic_mm"] = closure_reported_basic_mm
    audit["audit_closure_reconstructed_basic_mm"] = closure_reconstructed_basic_mm
    audit["audit_closure_reported_with_storage_mm"] = closure_reported_with_storage_mm
    audit["audit_closure_reconstructed_with_storage_mm"] = closure_reconstructed_with_storage_mm

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


def build_summary(audit: pd.DataFrame, source_path: Path) -> dict[str, Any]:
    closure_reported = audit["audit_closure_reported_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    closure_reconstructed = audit["audit_closure_reconstructed_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    runoff_consistency = audit["audit_runoff_consistency_mm"].to_numpy(dtype=np.float64, copy=False)

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
        "closure_reported_with_storage_mm": _quantiles(closure_reported),
        "closure_reconstructed_with_storage_mm": _quantiles(closure_reconstructed),
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
            "audit_storage_delta_mm",
            "audit_closure_reported_with_storage_mm",
            "audit_closure_reconstructed_with_storage_mm",
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
    print(f"summary_json={summary_path}")
    print(f"top_days_csv={top_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
