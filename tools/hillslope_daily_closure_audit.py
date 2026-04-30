#!/usr/bin/env python3
"""Repeatable daily closure audit for a single hillslope interchange dataset.

This tool audits internal depth consistency and daily closure residuals for one
hillslope, using H.wat + H.pass and optional H.soil/H.element interchange
artifacts.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd


DATE_COLUMNS = ("year", "sim_day_index", "julian", "month", "day_of_month", "water_year")
DATE_SORT_COLUMNS = ["year", "julian", "sim_day_index"]
WAT_OPTIONAL_COLUMNS = (
    "SoilWaterTotal",
    "ProfileDepth",
    "ProfilePorosityCap",
    "ProfileFCStore",
    "ProfileWPStore",
)
ELEMENT_OPTIONAL_COLUMNS = ("QRain", "QSnow")


@dataclass(frozen=True)
class _DatasetPaths:
    interchange_dir: Path
    pass_path: Path
    wat_path: Path
    soil_path: Path | None
    element_path: Path | None


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    result = np.zeros_like(numerator, dtype=np.float64)
    np.divide(numerator, denominator, out=result, where=denominator > 0.0)
    return result


def _depth_from_volume(volume_m3: np.ndarray, area_m2: np.ndarray) -> np.ndarray:
    return _safe_divide(volume_m3, area_m2) * 1000.0


def _safe_depth(volume: np.ndarray, area: np.ndarray) -> np.ndarray:
    return _depth_from_volume(volume, area)


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
        "SoilWaterTotal",
        "ProfileDepth",
        "ProfilePorosityCap",
        "ProfileFCStore",
        "ProfileWPStore",
        "TSMF",
        "QRain",
        "QSnow",
        "sbrunv",
        "n_ofe",
    )


def _has_non_null(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and frame[column].notna().any()


def _sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def _describe_columns(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{_sql_path(path)}')").fetchall()
    return [str(row[0]) for row in rows]


def _resolve_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lookup = {column.lower(): column for column in columns}
    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found is not None:
            return found
    return None


def _resolve_required_column(columns: list[str], candidates: tuple[str, ...], *, context: str) -> str:
    resolved = _resolve_column(columns, candidates)
    if resolved is None:
        raise KeyError(f"Missing required column in {context}: one of {candidates}")
    return resolved


def _resolve_sim_day_column(columns: list[str], *, context: str) -> str:
    return _resolve_required_column(columns, ("sim_day_index", "day"), context=context)


def _resolve_ofe_column(columns: list[str]) -> str | None:
    return _resolve_column(columns, ("ofe_id", "OFE"))


def _prepare_paths(interchange_dir: Path | str) -> _DatasetPaths:
    base = Path(interchange_dir).expanduser().resolve()
    pass_path = base / "H.pass.parquet"
    wat_path = base / "H.wat.parquet"
    soil_path = base / "H.soil.parquet"
    element_path = base / "H.element.parquet"
    if not pass_path.exists():
        raise FileNotFoundError(pass_path)
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)
    return _DatasetPaths(
        interchange_dir=base,
        pass_path=pass_path,
        wat_path=wat_path,
        soil_path=soil_path if soil_path.exists() else None,
        element_path=element_path if element_path.exists() else None,
    )


def _aggregate_pass_for_wepp(con: duckdb.DuckDBPyConnection, pass_path: Path, wepp_id: int) -> pd.DataFrame:
    columns = _describe_columns(con, pass_path)
    context = str(pass_path)
    wepp_column = _resolve_required_column(columns, ("wepp_id",), context=context)
    year_column = _resolve_required_column(columns, ("year",), context=context)
    sim_day_column = _resolve_sim_day_column(columns, context=context)
    julian_column = _resolve_required_column(columns, ("julian",), context=context)
    month_column = _resolve_required_column(columns, ("month",), context=context)
    day_of_month_column = _resolve_required_column(columns, ("day_of_month",), context=context)
    water_year_column = _resolve_required_column(columns, ("water_year",), context=context)
    runvol_column = _resolve_required_column(columns, ("runvol",), context=context)
    sbrunv_column = _resolve_column(columns, ("sbrunv",))
    sbrunv_expr = (
        f'SUM(COALESCE("{sbrunv_column}", 0.0)) AS sbrunv'
        if sbrunv_column is not None
        else "CAST(NULL AS DOUBLE) AS sbrunv"
    )

    query = f"""
        SELECT
            "{year_column}" AS year,
            "{sim_day_column}" AS sim_day_index,
            "{julian_column}" AS julian,
            "{month_column}" AS month,
            "{day_of_month_column}" AS day_of_month,
            "{water_year_column}" AS water_year,
            SUM(COALESCE("{runvol_column}", 0.0)) AS runvol,
            {sbrunv_expr}
        FROM read_parquet('{_sql_path(pass_path)}')
        WHERE "{wepp_column}" = {int(wepp_id)}
        GROUP BY
            "{year_column}",
            "{sim_day_column}",
            "{julian_column}",
            "{month_column}",
            "{day_of_month_column}",
            "{water_year_column}"
        ORDER BY
            "{year_column}",
            "{julian_column}",
            "{sim_day_column}"
    """
    return con.execute(query).df()


def _aggregate_wat_for_wepp(con: duckdb.DuckDBPyConnection, wat_path: Path, wepp_id: int) -> pd.DataFrame:
    columns = _describe_columns(con, wat_path)
    context = str(wat_path)
    wepp_column = _resolve_required_column(columns, ("wepp_id",), context=context)
    year_column = _resolve_required_column(columns, ("year",), context=context)
    sim_day_column = _resolve_sim_day_column(columns, context=context)
    julian_column = _resolve_required_column(columns, ("julian",), context=context)
    month_column = _resolve_required_column(columns, ("month",), context=context)
    day_of_month_column = _resolve_required_column(columns, ("day_of_month",), context=context)
    water_year_column = _resolve_required_column(columns, ("water_year",), context=context)
    area_column = _resolve_required_column(columns, ("Area",), context=context)
    ofe_column = _resolve_ofe_column(columns)

    required_depth_columns = (
        "P",
        "RM",
        "Q",
        "Dp",
        "latqcc",
        "QOFE",
        "Ep",
        "Es",
        "Er",
        "UpStrmQ",
        "SubRIn",
        "Total-Soil Water",
        "frozwt",
        "Snow-Water",
        "Tile",
        "Irr",
    )
    resolved_required: dict[str, str] = {}
    for name in required_depth_columns:
        resolved_required[name] = _resolve_required_column(columns, (name,), context=context)

    optional_exprs: list[str] = []
    for name in WAT_OPTIONAL_COLUMNS:
        resolved = _resolve_column(columns, (name,))
        if resolved is None:
            optional_exprs.append(f'CAST(NULL AS DOUBLE) AS "{name}_volume"')
        else:
            optional_exprs.append(f'SUM(COALESCE("{resolved}", 0.0) * 0.001 * "{area_column}") AS "{name}_volume"')
    optional_sql = ",\n            ".join(optional_exprs)

    if ofe_column is None:
        source_clause = f"""
        FROM read_parquet('{_sql_path(wat_path)}')
        WHERE "{wepp_column}" = {int(wepp_id)}
        """
        latqcc_expr = f'SUM(COALESCE("{resolved_required["latqcc"]}", 0.0) * 0.001 * "{area_column}") AS latqcc,'
        n_ofe_expr = "CAST(1 AS INTEGER) AS n_ofe,"
    else:
        source_clause = f"""
        FROM (
            SELECT
                *,
                MAX("{ofe_column}") OVER (
                    PARTITION BY
                        "{year_column}",
                        "{sim_day_column}",
                        "{julian_column}",
                        "{month_column}",
                        "{day_of_month_column}",
                        "{water_year_column}"
                ) AS _max_ofe_id
            FROM read_parquet('{_sql_path(wat_path)}')
            WHERE "{wepp_column}" = {int(wepp_id)}
        ) AS wat
        """
        latqcc_expr = (
            f'SUM(CASE WHEN "{ofe_column}" = _max_ofe_id '
            f'THEN COALESCE("{resolved_required["latqcc"]}", 0.0) * 0.001 * "{area_column}" ELSE 0 END) AS latqcc,'
        )
        n_ofe_expr = f'COUNT(DISTINCT "{ofe_column}") AS n_ofe,'

    query = f"""
        SELECT
            "{year_column}" AS year,
            "{sim_day_column}" AS sim_day_index,
            "{julian_column}" AS julian,
            "{month_column}" AS month,
            "{day_of_month_column}" AS day_of_month,
            "{water_year_column}" AS water_year,
            {n_ofe_expr}
            SUM(COALESCE("{area_column}", 0.0)) AS Area,
            SUM(COALESCE("{resolved_required["P"]}", 0.0) * 0.001 * "{area_column}") AS P,
            SUM(COALESCE("{resolved_required["RM"]}", 0.0) * 0.001 * "{area_column}") AS RM,
            SUM(COALESCE("{resolved_required["Q"]}", 0.0) * 0.001 * "{area_column}") AS Q,
            SUM(COALESCE("{resolved_required["Dp"]}", 0.0) * 0.001 * "{area_column}") AS Dp,
            {latqcc_expr}
            SUM(COALESCE("{resolved_required["QOFE"]}", 0.0) * 0.001 * "{area_column}") AS QOFE,
            SUM(COALESCE("{resolved_required["Ep"]}", 0.0) * 0.001 * "{area_column}") AS Ep,
            SUM(COALESCE("{resolved_required["Es"]}", 0.0) * 0.001 * "{area_column}") AS Es,
            SUM(COALESCE("{resolved_required["Er"]}", 0.0) * 0.001 * "{area_column}") AS Er,
            SUM(COALESCE("{resolved_required["UpStrmQ"]}", 0.0) * 0.001 * "{area_column}") AS UpStrmQ_volume,
            SUM(COALESCE("{resolved_required["SubRIn"]}", 0.0) * 0.001 * "{area_column}") AS SubRIn_volume,
            SUM(COALESCE("{resolved_required["Total-Soil Water"]}", 0.0) * 0.001 * "{area_column}") AS Total_Soil_Water_volume,
            {optional_sql},
            SUM(COALESCE("{resolved_required["frozwt"]}", 0.0) * 0.001 * "{area_column}") AS frozwt_volume,
            SUM(COALESCE("{resolved_required["Snow-Water"]}", 0.0) * 0.001 * "{area_column}") AS Snow_Water_volume,
            SUM(COALESCE("{resolved_required["Tile"]}", 0.0) * 0.001 * "{area_column}") AS Tile_volume,
            SUM(COALESCE("{resolved_required["Irr"]}", 0.0) * 0.001 * "{area_column}") AS Irr_volume
        {source_clause}
        GROUP BY
            "{year_column}",
            "{sim_day_column}",
            "{julian_column}",
            "{month_column}",
            "{day_of_month_column}",
            "{water_year_column}"
        ORDER BY
            "{year_column}",
            "{julian_column}",
            "{sim_day_column}"
    """
    return con.execute(query).df()


def _aggregate_soil_tsmf_for_wepp(
    con: duckdb.DuckDBPyConnection,
    soil_path: Path,
    wat_path: Path,
    wepp_id: int,
) -> pd.DataFrame | None:
    soil_columns = _describe_columns(con, soil_path)
    wat_columns = _describe_columns(con, wat_path)
    if _resolve_column(soil_columns, ("TSMF",)) is None:
        return None

    soil_context = str(soil_path)
    wat_context = str(wat_path)

    soil_wepp_column = _resolve_required_column(soil_columns, ("wepp_id",), context=soil_context)
    soil_day_column = _resolve_sim_day_column(soil_columns, context=soil_context)
    soil_ofe_column = _resolve_ofe_column(soil_columns)
    if soil_ofe_column is None:
        return None

    wat_day_column = _resolve_sim_day_column(wat_columns, context=wat_context)
    wat_ofe_column = _resolve_ofe_column(wat_columns)
    if wat_ofe_column is None:
        return None

    soil_year_column = _resolve_required_column(soil_columns, ("year",), context=soil_context)
    soil_julian_column = _resolve_required_column(soil_columns, ("julian",), context=soil_context)
    soil_month_column = _resolve_required_column(soil_columns, ("month",), context=soil_context)
    soil_dom_column = _resolve_required_column(soil_columns, ("day_of_month",), context=soil_context)
    soil_wy_column = _resolve_required_column(soil_columns, ("water_year",), context=soil_context)
    soil_tsmf_column = _resolve_required_column(soil_columns, ("TSMF",), context=soil_context)

    wat_wepp_column = _resolve_required_column(wat_columns, ("wepp_id",), context=wat_context)
    wat_year_column = _resolve_required_column(wat_columns, ("year",), context=wat_context)
    wat_area_column = _resolve_required_column(wat_columns, ("Area",), context=wat_context)

    query = f"""
        SELECT
            soil."{soil_year_column}" AS year,
            soil."{soil_day_column}" AS sim_day_index,
            soil."{soil_julian_column}" AS julian,
            soil."{soil_month_column}" AS month,
            soil."{soil_dom_column}" AS day_of_month,
            soil."{soil_wy_column}" AS water_year,
            SUM(CASE WHEN soil."{soil_tsmf_column}" IS NOT NULL THEN soil."{soil_tsmf_column}" * wat."{wat_area_column}" ELSE 0 END) AS tsmf_weighted_sum,
            SUM(CASE WHEN soil."{soil_tsmf_column}" IS NOT NULL THEN wat."{wat_area_column}" ELSE 0 END) AS tsmf_area
        FROM read_parquet('{_sql_path(soil_path)}') AS soil
        INNER JOIN read_parquet('{_sql_path(wat_path)}') AS wat
            ON soil."{soil_wepp_column}" = wat."{wat_wepp_column}"
            AND soil."{soil_ofe_column}" = wat."{wat_ofe_column}"
            AND soil."{soil_year_column}" = wat."{wat_year_column}"
            AND soil."{soil_day_column}" = wat."{wat_day_column}"
        WHERE soil."{soil_wepp_column}" = {int(wepp_id)}
        GROUP BY
            soil."{soil_year_column}",
            soil."{soil_day_column}",
            soil."{soil_julian_column}",
            soil."{soil_month_column}",
            soil."{soil_dom_column}",
            soil."{soil_wy_column}"
        ORDER BY
            soil."{soil_year_column}",
            soil."{soil_julian_column}",
            soil."{soil_day_column}"
    """

    df = con.execute(query).df()
    if df.empty:
        return None

    weighted_sum = df["tsmf_weighted_sum"].to_numpy(dtype=np.float64, copy=False)
    weights = df["tsmf_area"].to_numpy(dtype=np.float64, copy=False)
    tsmf = np.full(df.shape[0], np.nan, dtype=np.float64)
    np.divide(weighted_sum, weights, out=tsmf, where=weights > 0.0)
    result = df[list(DATE_COLUMNS)].copy()
    result["TSMF"] = tsmf
    return result


def _aggregate_element_partitions_for_wepp(
    con: duckdb.DuckDBPyConnection,
    element_path: Path,
    wat_path: Path,
    wepp_id: int,
) -> pd.DataFrame | None:
    element_columns = _describe_columns(con, element_path)
    wat_columns = _describe_columns(con, wat_path)

    available_columns = [column for column in ELEMENT_OPTIONAL_COLUMNS if _resolve_column(element_columns, (column,))]
    if not available_columns:
        return None

    elem_context = str(element_path)
    wat_context = str(wat_path)

    elem_wepp_column = _resolve_required_column(element_columns, ("wepp_id",), context=elem_context)
    elem_ofe_column = _resolve_ofe_column(element_columns)
    if elem_ofe_column is None:
        return None
    wat_wepp_column = _resolve_required_column(wat_columns, ("wepp_id",), context=wat_context)
    wat_ofe_column = _resolve_ofe_column(wat_columns)
    if wat_ofe_column is None:
        return None

    elem_year_column = _resolve_required_column(element_columns, ("year",), context=elem_context)
    elem_julian_column = _resolve_required_column(element_columns, ("julian",), context=elem_context)
    elem_month_column = _resolve_required_column(element_columns, ("month",), context=elem_context)
    elem_dom_column = _resolve_required_column(element_columns, ("day_of_month",), context=elem_context)
    elem_wy_column = _resolve_required_column(element_columns, ("water_year",), context=elem_context)

    wat_year_column = _resolve_required_column(wat_columns, ("year",), context=wat_context)
    wat_day_column = _resolve_sim_day_column(wat_columns, context=wat_context)
    wat_julian_column = _resolve_required_column(wat_columns, ("julian",), context=wat_context)
    wat_month_column = _resolve_required_column(wat_columns, ("month",), context=wat_context)
    wat_dom_column = _resolve_required_column(wat_columns, ("day_of_month",), context=wat_context)
    wat_wy_column = _resolve_required_column(wat_columns, ("water_year",), context=wat_context)
    wat_area_column = _resolve_required_column(wat_columns, ("Area",), context=wat_context)

    metric_exprs: list[str] = []
    for name in available_columns:
        elem_col = _resolve_required_column(element_columns, (name,), context=elem_context)
        metric_exprs.append(
            f'SUM(CASE WHEN elem."{elem_col}" IS NOT NULL THEN elem."{elem_col}" * 0.001 * wat."{wat_area_column}" ELSE 0 END) AS "{name}_volume"'
        )
        metric_exprs.append(
            f'SUM(CASE WHEN elem."{elem_col}" IS NOT NULL THEN wat."{wat_area_column}" ELSE 0 END) AS "{name}_area"'
        )
    metrics_sql = ",\n            ".join(metric_exprs)

    query = f"""
        SELECT
            elem."{elem_year_column}" AS year,
            wat."{wat_day_column}" AS sim_day_index,
            elem."{elem_julian_column}" AS julian,
            elem."{elem_month_column}" AS month,
            elem."{elem_dom_column}" AS day_of_month,
            elem."{elem_wy_column}" AS water_year,
            {metrics_sql}
        FROM read_parquet('{_sql_path(element_path)}') AS elem
        INNER JOIN read_parquet('{_sql_path(wat_path)}') AS wat
            ON elem."{elem_wepp_column}" = wat."{wat_wepp_column}"
            AND elem."{elem_ofe_column}" = wat."{wat_ofe_column}"
            AND elem."{elem_year_column}" = wat."{wat_year_column}"
            AND elem."{elem_julian_column}" = wat."{wat_julian_column}"
            AND elem."{elem_month_column}" = wat."{wat_month_column}"
            AND elem."{elem_dom_column}" = wat."{wat_dom_column}"
            AND elem."{elem_wy_column}" = wat."{wat_wy_column}"
        WHERE elem."{elem_wepp_column}" = {int(wepp_id)}
        GROUP BY
            elem."{elem_year_column}",
            wat."{wat_day_column}",
            elem."{elem_julian_column}",
            elem."{elem_month_column}",
            elem."{elem_dom_column}",
            elem."{elem_wy_column}"
        ORDER BY
            elem."{elem_year_column}",
            elem."{elem_julian_column}",
            wat."{wat_day_column}"
    """

    df = con.execute(query).df()
    if df.empty:
        return None

    result = df[list(DATE_COLUMNS)].copy()
    for name in available_columns:
        volume = df[f"{name}_volume"].to_numpy(dtype=np.float64, copy=False)
        area = df[f"{name}_area"].to_numpy(dtype=np.float64, copy=False)
        depth = np.full(df.shape[0], np.nan, dtype=np.float64)
        np.divide(volume, area, out=depth, where=area > 0.0)
        depth *= 1000.0
        result[name] = depth
    return result


def load_dataset(interchange_dir: Path, wepp_id: int) -> pd.DataFrame:
    targets = _prepare_paths(interchange_dir)

    with duckdb.connect(":memory:") as con:
        pass_df = _aggregate_pass_for_wepp(con, targets.pass_path, wepp_id)
        wat_df = _aggregate_wat_for_wepp(con, targets.wat_path, wepp_id)
        soil_df = None
        if targets.soil_path is not None:
            soil_df = _aggregate_soil_tsmf_for_wepp(con, targets.soil_path, targets.wat_path, wepp_id)
        element_df = None
        if targets.element_path is not None:
            element_df = _aggregate_element_partitions_for_wepp(con, targets.element_path, targets.wat_path, wepp_id)

    if wat_df.empty:
        raise ValueError(f"No H.wat rows found for wepp_id={wepp_id} under {targets.interchange_dir}")

    merged = wat_df.merge(pass_df, on=list(DATE_COLUMNS), how="left", suffixes=("", "_pass"))
    if pass_df.empty:
        merged[["runvol", "sbrunv"]] = 0.0
    else:
        merged["runvol"] = merged["runvol"].fillna(0.0)
        if "sbrunv" in merged.columns:
            merged["sbrunv"] = merged["sbrunv"].fillna(0.0)
        else:
            merged["sbrunv"] = np.nan

    area = merged["Area"].to_numpy(dtype=np.float64, copy=False)
    merged["UpStrmQ"] = _safe_depth(merged.pop("UpStrmQ_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["SubRIn"] = _safe_depth(merged.pop("SubRIn_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Total-Soil Water"] = _safe_depth(
        merged.pop("Total_Soil_Water_volume").to_numpy(dtype=np.float64, copy=False),
        area,
    )
    for column in WAT_OPTIONAL_COLUMNS:
        volume_col = f"{column}_volume"
        if volume_col in merged and not merged[volume_col].isna().all():
            merged[column] = _safe_depth(merged.pop(volume_col).to_numpy(dtype=np.float64, copy=False), area)
        else:
            merged.drop(columns=[volume_col], inplace=True, errors="ignore")
            merged[column] = np.nan
    merged["frozwt"] = _safe_depth(merged.pop("frozwt_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Snow-Water"] = _safe_depth(merged.pop("Snow_Water_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Tile"] = _safe_depth(merged.pop("Tile_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Irr"] = _safe_depth(merged.pop("Irr_volume").to_numpy(dtype=np.float64, copy=False), area)

    if soil_df is not None:
        merged = merged.merge(soil_df, on=list(DATE_COLUMNS), how="left", validate="one_to_one")
    else:
        merged["TSMF"] = np.nan

    if element_df is not None:
        merged = merged.merge(element_df, on=list(DATE_COLUMNS), how="left", validate="one_to_one")
    for column in ELEMENT_OPTIONAL_COLUMNS:
        if column not in merged:
            merged[column] = np.nan

    merged["Precipitation"] = _safe_depth(merged["P"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Rain+Melt"] = _safe_depth(merged["RM"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Percolation"] = _safe_depth(merged["Dp"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Lateral Flow"] = _safe_depth(merged["latqcc"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Runoff"] = _safe_depth(merged["runvol"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Transpiration"] = _safe_depth(merged["Ep"].to_numpy(dtype=np.float64, copy=False), area)
    evaporation_volume = merged["Es"].to_numpy(dtype=np.float64, copy=False) + merged["Er"].to_numpy(
        dtype=np.float64,
        copy=False,
    )
    merged["Evaporation"] = _safe_depth(evaporation_volume, area)
    merged["ET"] = _safe_depth(
        merged["Ep"].to_numpy(dtype=np.float64, copy=False)
        + merged["Es"].to_numpy(dtype=np.float64, copy=False)
        + merged["Er"].to_numpy(dtype=np.float64, copy=False),
        area,
    )

    if "n_ofe" not in merged.columns:
        merged["n_ofe"] = 1

    required = [name for name in _required_columns() if name in merged.columns]
    optional = [name for name in _optional_columns() if name in merged.columns]
    df = merged[required + optional].copy()

    missing = [name for name in _required_columns() if name not in df.columns]
    if missing:
        raise KeyError(f"Missing required aggregated columns for wepp_id={wepp_id}: {missing}")

    for col in df.columns:
        if col in ("year", "julian", "sim_day_index", "month", "day_of_month", "water_year", "n_ofe"):
            continue
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
    if "sbrunv" in audit:
        sbrunv_calc_mm = _depth_from_volume(audit["sbrunv"].to_numpy(dtype=np.float64, copy=False), area_m2)
    else:
        sbrunv_calc_mm = np.full(audit.shape[0], np.nan, dtype=np.float64)

    precip_reported_mm = (
        audit["Precipitation"].to_numpy(dtype=np.float64, copy=False) if "Precipitation" in audit else precip_calc_mm
    )
    rain_melt_reported_mm = audit["Rain+Melt"].to_numpy(dtype=np.float64, copy=False) if "Rain+Melt" in audit else rain_melt_calc_mm
    runoff_reported_mm = audit["Runoff"].to_numpy(dtype=np.float64, copy=False) if "Runoff" in audit else runoff_calc_mm
    lateral_reported_mm = (
        audit["Lateral Flow"].to_numpy(dtype=np.float64, copy=False) if "Lateral Flow" in audit else lateral_calc_mm
    )
    percolation_reported_mm = (
        audit["Percolation"].to_numpy(dtype=np.float64, copy=False) if "Percolation" in audit else percolation_calc_mm
    )
    et_reported_mm = audit["ET"].to_numpy(dtype=np.float64, copy=False) if "ET" in audit else et_calc_mm

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
        runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm
    )
    closure_reconstructed_basic_mm = precip_reported_mm - (
        runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm
    )
    closure_reported_with_storage_mm = closure_reported_basic_mm - storage_delta_mm
    closure_reconstructed_with_storage_mm = closure_reconstructed_basic_mm - storage_delta_mm

    # Keep Rain+Melt-based closure as a diagnostic to highlight snowpack timing.
    closure_reported_with_storage_rain_melt_mm = rain_melt_reported_mm - (
        runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm
    ) - storage_delta_mm
    closure_reconstructed_with_storage_rain_melt_mm = rain_melt_reported_mm - (
        runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm
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
            runoff_reported_mm + lateral_reported_mm + et_reported_mm + percolation_reported_mm
        ) - enriched_storage_delta_mm
        closure_reconstructed_with_enriched_storage_rain_melt_mm = rain_melt_reported_mm - (
            runoff_calc_mm + lateral_calc_mm + et_calc_mm + percolation_calc_mm
        ) - enriched_storage_delta_mm

    runoff_to_precip_reported_pct = _safe_divide(runoff_reported_mm, precip_reported_mm) * 100.0
    runoff_to_precip_reconstructed_pct = _safe_divide(runoff_calc_mm, precip_reported_mm) * 100.0

    audit["audit_precip_calc_mm"] = precip_calc_mm
    audit["audit_rain_melt_calc_mm"] = rain_melt_calc_mm
    audit["audit_runoff_calc_mm"] = runoff_calc_mm
    audit["audit_lateral_calc_mm"] = lateral_calc_mm
    audit["audit_percolation_calc_mm"] = percolation_calc_mm
    audit["audit_et_calc_mm"] = et_calc_mm
    audit["audit_sbrunv_calc_mm"] = sbrunv_calc_mm

    audit["audit_precip_reported_mm"] = precip_reported_mm
    audit["audit_rain_melt_reported_mm"] = rain_melt_reported_mm
    audit["audit_runoff_reported_mm"] = runoff_reported_mm
    audit["audit_lateral_reported_mm"] = lateral_reported_mm
    audit["audit_percolation_reported_mm"] = percolation_reported_mm
    audit["audit_et_reported_mm"] = et_reported_mm

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


def build_summary(
    audit: pd.DataFrame,
    source_path: Path,
    *,
    wepp_id: int,
    topaz_id: int | None,
) -> dict[str, Any]:
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

    top_runoff = audit.iloc[int(np.argmax(audit["audit_runoff_reported_mm"].to_numpy(dtype=np.float64, copy=False)))]

    n_ofe_min = None
    n_ofe_max = None
    if "n_ofe" in audit.columns:
        n_ofe_vals = audit["n_ofe"].to_numpy(dtype=np.float64, copy=False)
        if n_ofe_vals.size:
            n_ofe_min = int(np.nanmin(n_ofe_vals))
            n_ofe_max = int(np.nanmax(n_ofe_vals))

    return {
        "source": str(source_path),
        "wepp_id": int(wepp_id),
        "topaz_id": None if topaz_id is None else int(topaz_id),
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
        "n_ofe_min": n_ofe_min,
        "n_ofe_max": n_ofe_max,
        "max_reported_runoff_mm": float(np.max(audit["audit_runoff_reported_mm"].to_numpy(dtype=np.float64, copy=False))),
        "max_reconstructed_runoff_mm": float(np.max(audit["audit_runoff_calc_mm"].to_numpy(dtype=np.float64, copy=False))),
        "max_runoff_to_precip_reported_pct": float(np.max(audit["audit_runoff_to_precip_reported_pct"].to_numpy(dtype=np.float64, copy=False))),
        "max_runoff_to_precip_reconstructed_pct": float(np.max(audit["audit_runoff_to_precip_reconstructed_pct"].to_numpy(dtype=np.float64, copy=False))),
        "runoff_consistency_mm": _quantiles(runoff_consistency),
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
            "sbrunv_calc_mm": float(top_runoff["audit_sbrunv_calc_mm"])
            if "audit_sbrunv_calc_mm" in top_runoff
            else None,
        },
    }


def _build_output_dir(interchange_dir: Path, wepp_id: int, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return interchange_dir / f"audit_hillslope_daily_closure_H{int(wepp_id)}"


def _top_anomalies(audit: pd.DataFrame, top_n: int) -> pd.DataFrame:
    base_columns = [
        "year",
        "julian",
        "sim_day_index",
        "month",
        "day_of_month",
        "water_year",
        "n_ofe",
        "audit_rain_melt_reported_mm",
        "audit_precip_reported_mm",
        "audit_runoff_reported_mm",
        "audit_runoff_calc_mm",
        "audit_runoff_consistency_mm",
        "audit_sbrunv_calc_mm",
        "audit_lateral_reported_mm",
        "audit_lateral_calc_mm",
        "audit_et_reported_mm",
        "audit_et_calc_mm",
        "audit_percolation_reported_mm",
        "audit_percolation_calc_mm",
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
    optional = [name for name in ("TSMF", "QRain", "QSnow") if name in audit.columns]
    subset = audit[base_columns + optional].copy()

    subset["abs_closure_reported_with_storage_mm"] = subset["audit_closure_reported_with_storage_mm"].abs()
    subset["abs_runoff_consistency_mm"] = subset["audit_runoff_consistency_mm"].abs()
    subset = subset.sort_values(
        ["abs_closure_reported_with_storage_mm", "abs_runoff_consistency_mm"],
        ascending=[False, False],
        kind="mergesort",
    )
    return subset.head(top_n).reset_index(drop=True)


def _resolve_run_root(interchange_dir: Path) -> Path:
    for parent in [interchange_dir, *interchange_dir.parents]:
        if (parent / "wepp").is_dir():
            return parent
    raise FileNotFoundError(f"Unable to resolve run root from interchange path: {interchange_dir}")


def _resolve_wepp_from_topaz(interchange_dir: Path, topaz_id: int) -> int:
    from wepppy.nodb.core import Watershed

    run_root = _resolve_run_root(interchange_dir)
    watershed = Watershed.getInstance(str(run_root))
    translator = watershed.translator_factory()
    return int(translator.wepp(top=int(topaz_id)))


def _resolve_topaz_from_wepp(interchange_dir: Path, wepp_id: int) -> int | None:
    try:
        from wepppy.nodb.core import Watershed
    except ModuleNotFoundError:
        return None

    run_root = _resolve_run_root(interchange_dir)
    watershed = Watershed.getInstance(str(run_root))
    translator = watershed.translator_factory()
    try:
        return int(translator.top(wepp=int(wepp_id)))
    except KeyError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interchange_dir", help="Path to .../wepp/output/interchange")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--wepp-id", type=int, default=None, help="Target WEPP hillslope id")
    selector.add_argument("--topaz-id", type=int, default=None, help="Target TOPAZ hillslope id")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for audit outputs (default: <interchange>/audit_hillslope_daily_closure_H<wepp_id>)",
    )
    parser.add_argument("--top-n", type=int, default=25, help="Number of top anomaly days to export")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    interchange_dir = Path(args.interchange_dir).expanduser().resolve()
    if not interchange_dir.exists():
        raise FileNotFoundError(interchange_dir)

    topaz_id: int | None = None
    if args.wepp_id is not None:
        wepp_id = int(args.wepp_id)
        topaz_id = _resolve_topaz_from_wepp(interchange_dir, wepp_id)
    else:
        topaz_id = int(args.topaz_id)
        wepp_id = _resolve_wepp_from_topaz(interchange_dir, topaz_id)

    output_dir = _build_output_dir(
        interchange_dir,
        wepp_id,
        Path(args.output_dir).expanduser().resolve() if args.output_dir else None,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    source_paths = {
        "interchange_dir": str(interchange_dir),
        "pass": str(interchange_dir / "H.pass.parquet"),
        "wat": str(interchange_dir / "H.wat.parquet"),
        "soil": str(interchange_dir / "H.soil.parquet"),
        "element": str(interchange_dir / "H.element.parquet"),
    }

    dataset = load_dataset(interchange_dir, wepp_id)
    audit = compute_daily_audit(dataset)
    summary = build_summary(
        audit,
        interchange_dir,
        wepp_id=wepp_id,
        topaz_id=topaz_id,
    )
    summary["sources"] = source_paths
    top = _top_anomalies(audit, max(1, int(args.top_n)))

    summary_path = output_dir / "hillslope_daily_closure_audit_summary.json"
    top_path = output_dir / "hillslope_daily_closure_audit_top_days.csv"

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    top.to_csv(top_path, index=False)

    print(f"interchange_dir={interchange_dir}")
    print(f"wepp_id={wepp_id}")
    print(f"topaz_id={topaz_id}")
    print(f"rows={summary['rows']}")
    print(f"n_ofe_min={summary['n_ofe_min']}")
    print(f"n_ofe_max={summary['n_ofe_max']}")
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
