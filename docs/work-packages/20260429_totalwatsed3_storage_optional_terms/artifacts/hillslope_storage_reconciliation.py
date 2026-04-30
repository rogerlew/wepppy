#!/usr/bin/env python3
"""Hillslope-level closure reconciliation for selected WEPP IDs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0.0 or np.isnan(denominator):
        return None
    return float(numerator / denominator)


def _optional(value: float) -> float | None:
    if np.isnan(value):
        return None
    return float(value)


def _reconcile_one(interchange_dir: Path, wepp_id: int) -> dict[str, Any]:
    wat_path = interchange_dir / "H.wat.parquet"
    pass_path = interchange_dir / "H.pass.parquet"
    element_path = interchange_dir / "H.element.parquet"

    wat_schema = set(duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{wat_path.as_posix()}')").df()["column_name"])
    has_enriched = "SoilWaterTotal" in wat_schema
    optional_select = (
        'SUM("SoilWaterTotal" * 0.001 * Area) AS soil_water_total_volume,'
        if has_enriched
        else "CAST(NULL AS DOUBLE) AS soil_water_total_volume,"
    )
    optional_column = "soil_water_total_volume"

    with duckdb.connect() as con:
        wat_df = con.execute(
            f"""
            WITH wat AS (
                SELECT
                    *,
                    MAX("OFE") OVER (
                        PARTITION BY wepp_id, year, sim_day_index, julian, month, day_of_month, water_year
                    ) AS max_ofe
                FROM read_parquet('{wat_path.as_posix()}')
                WHERE wepp_id = ?
            )
            SELECT
                year,
                sim_day_index,
                julian,
                month,
                day_of_month,
                water_year,
                SUM(Area) AS area_m2,
                SUM(RM * 0.001 * Area) AS rain_melt_volume,
                SUM(P * 0.001 * Area) AS precipitation_volume,
                SUM(Dp * 0.001 * Area) AS percolation_volume,
                SUM((Ep + Es + Er) * 0.001 * Area) AS et_volume,
                SUM(CASE WHEN "OFE" = max_ofe THEN latqcc * 0.001 * Area ELSE 0 END) AS lateral_volume,
                SUM(("Total-Soil Water" + frozwt + "Snow-Water") * 0.001 * Area) AS storage_volume,
                {optional_select}
                SUM("Snow-Water" * 0.001 * Area) AS snow_water_volume
            FROM wat
            GROUP BY year, sim_day_index, julian, month, day_of_month, water_year
            ORDER BY year, julian, sim_day_index
            """,
            [wepp_id],
        ).df()

        pass_df = con.execute(
            f"""
            SELECT
                year,
                sim_day_index,
                julian,
                month,
                day_of_month,
                water_year,
                SUM(runvol) AS runoff_volume,
                SUM(sbrunv) AS subsurface_runoff_volume
            FROM read_parquet('{pass_path.as_posix()}')
            WHERE wepp_id = ?
            GROUP BY year, sim_day_index, julian, month, day_of_month, water_year
            ORDER BY year, julian, sim_day_index
            """,
            [wepp_id],
        ).df()

        partition_df = pd.DataFrame()
        if element_path.exists():
            partition_df = con.execute(
                f"""
                SELECT
                    elem.year,
                    wat.sim_day_index,
                    elem.julian,
                    elem.month,
                    elem.day_of_month,
                    elem.water_year,
                    SUM(elem.QRain * 0.001 * wat.Area) AS qrain_volume,
                    SUM(elem.QSnow * 0.001 * wat.Area) AS qsnow_volume
                FROM read_parquet('{element_path.as_posix()}') AS elem
                INNER JOIN read_parquet('{wat_path.as_posix()}') AS wat
                    ON elem.wepp_id = wat.wepp_id
                    AND elem."OFE" = wat."OFE"
                    AND elem.year = wat.year
                    AND elem.julian = wat.julian
                    AND elem.month = wat.month
                    AND elem.day_of_month = wat.day_of_month
                    AND elem.water_year = wat.water_year
                WHERE elem.wepp_id = ?
                GROUP BY elem.year, wat.sim_day_index, elem.julian, elem.month, elem.day_of_month, elem.water_year
                ORDER BY elem.year, elem.julian, wat.sim_day_index
                """,
                [wepp_id],
            ).df()

    if wat_df.empty:
        return {"wepp_id": wepp_id, "rows": 0, "error": "no WAT rows"}

    key = ["year", "sim_day_index", "julian", "month", "day_of_month", "water_year"]
    df = wat_df.merge(pass_df, on=key, how="left")
    df["runoff_volume"] = df["runoff_volume"].fillna(0.0)
    if not partition_df.empty:
        df = df.merge(partition_df, on=key, how="left")
    for col in ("qrain_volume", "qsnow_volume"):
        if col not in df:
            df[col] = np.nan

    area = df["area_m2"].to_numpy(dtype=np.float64, copy=False)
    for volume_col, depth_col in (
        ("rain_melt_volume", "rain_melt_mm"),
        ("precipitation_volume", "precipitation_mm"),
        ("runoff_volume", "runoff_mm"),
        ("lateral_volume", "lateral_mm"),
        ("percolation_volume", "percolation_mm"),
        ("et_volume", "et_mm"),
        ("storage_volume", "storage_mm"),
        (optional_column, "soil_water_total_mm"),
        ("snow_water_volume", "snow_water_mm"),
        ("qrain_volume", "qrain_mm"),
        ("qsnow_volume", "qsnow_mm"),
    ):
        values = df[volume_col].to_numpy(dtype=np.float64, copy=False)
        depth = np.full(df.shape[0], np.nan, dtype=np.float64)
        np.divide(values, area, out=depth, where=area > 0.0)
        df[depth_col] = depth * 1000.0

    df["storage_delta_mm"] = np.diff(df["storage_mm"], prepend=df["storage_mm"].iloc[0])
    if has_enriched:
        df["enriched_storage_mm"] = df["soil_water_total_mm"] + df["snow_water_mm"]
        df["enriched_storage_delta_mm"] = np.diff(
            df["enriched_storage_mm"], prepend=df["enriched_storage_mm"].iloc[0]
        )
    else:
        df["enriched_storage_mm"] = np.nan
        df["enriched_storage_delta_mm"] = np.nan

    df["closure_with_storage_mm"] = df["rain_melt_mm"] - (
        df["runoff_mm"] + df["lateral_mm"] + df["percolation_mm"] + df["et_mm"] + df["storage_delta_mm"]
    )
    if has_enriched:
        df["closure_with_enriched_storage_mm"] = df["rain_melt_mm"] - (
            df["runoff_mm"]
            + df["lateral_mm"]
            + df["percolation_mm"]
            + df["et_mm"]
            + df["enriched_storage_delta_mm"]
        )
    else:
        df["closure_with_enriched_storage_mm"] = np.nan

    closure = df["closure_with_storage_mm"].to_numpy(dtype=np.float64, copy=False)
    rain_melt_total = float(df["rain_melt_mm"].sum())
    closure_total = float(df["closure_with_storage_mm"].sum())
    max_idx = int(np.nanargmax(np.abs(closure)))
    top = df.iloc[max_idx]
    qrain_total = float(df["qrain_mm"].sum(skipna=True)) if df["qrain_mm"].notna().any() else float("nan")
    qsnow_total = float(df["qsnow_mm"].sum(skipna=True)) if df["qsnow_mm"].notna().any() else float("nan")

    return {
        "wepp_id": wepp_id,
        "rows": int(df.shape[0]),
        "date_min": {
            "year": int(df["year"].iloc[0]),
            "julian": int(df["julian"].iloc[0]),
            "month": int(df["month"].iloc[0]),
            "day_of_month": int(df["day_of_month"].iloc[0]),
        },
        "date_max": {
            "year": int(df["year"].iloc[-1]),
            "julian": int(df["julian"].iloc[-1]),
            "month": int(df["month"].iloc[-1]),
            "day_of_month": int(df["day_of_month"].iloc[-1]),
        },
        "enriched_storage_available": bool(has_enriched),
        "rain_melt_total_mm": rain_melt_total,
        "runoff_total_mm": float(df["runoff_mm"].sum()),
        "lateral_total_mm": float(df["lateral_mm"].sum()),
        "percolation_total_mm": float(df["percolation_mm"].sum()),
        "et_total_mm": float(df["et_mm"].sum()),
        "storage_change_mm": float(df["storage_mm"].iloc[-1] - df["storage_mm"].iloc[0]),
        "closure_with_storage_total_mm": closure_total,
        "closure_with_storage_pct_of_rain_melt": _safe_ratio(closure_total * 100.0, rain_melt_total),
        "mean_abs_daily_closure_with_storage_mm": float(np.nanmean(np.abs(closure))),
        "qrain_total_mm": _optional(qrain_total),
        "qsnow_total_mm": _optional(qsnow_total),
        "qrain_plus_qsnow_total_mm": _optional(qrain_total + qsnow_total),
        "top_abs_closure_day": {
            "year": int(top["year"]),
            "julian": int(top["julian"]),
            "month": int(top["month"]),
            "day_of_month": int(top["day_of_month"]),
            "rain_melt_mm": float(top["rain_melt_mm"]),
            "runoff_mm": float(top["runoff_mm"]),
            "lateral_mm": float(top["lateral_mm"]),
            "percolation_mm": float(top["percolation_mm"]),
            "et_mm": float(top["et_mm"]),
            "storage_delta_mm": float(top["storage_delta_mm"]),
            "closure_with_storage_mm": float(top["closure_with_storage_mm"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interchange_dir")
    parser.add_argument("--wepp-id", action="append", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    interchange_dir = Path(args.interchange_dir).expanduser().resolve()
    result = {
        "interchange_dir": str(interchange_dir),
        "hillslopes": [_reconcile_one(interchange_dir, wepp_id) for wepp_id in args.wepp_id],
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
