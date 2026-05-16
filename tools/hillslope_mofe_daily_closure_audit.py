#!/usr/bin/env python3
"""Repeatable MOFE-focused daily closure audit for a single hillslope.

This audit extends the baseline hillslope closure audit with:
1. adjacent-OFE chain transfer diagnostics, and
2. a full-physics daily closure diagnostic built from exported WEPP terms.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from tools import hillslope_daily_closure_audit as base


DATE_COLUMNS = tuple(base.DATE_COLUMNS)
DATE_SORT_COLUMNS = list(base.DATE_SORT_COLUMNS)
NONZERO_TOLERANCE = 1.0e-9
SCIREVIEW_LATE_OFE_WINDOW = 3
SCIREVIEW_RESIDUAL_THRESHOLD_MM = 100.0
SCIREVIEW_QOFE_TO_Q_RATIO_THRESHOLD = 2.0
SCIREVIEW_SURFACE_PULSE_PROXY_THRESHOLD_MM = 100.0


def _sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def _safe_depth_scalar(volume_m3: float, area_m2: float) -> float:
    if area_m2 <= 0.0:
        return 0.0
    return float((volume_m3 / area_m2) * 1000.0)


def _compute_surface_pulse_proxy_mm_ofe(
    *,
    qofe: np.ndarray,
    upstrmq: np.ndarray,
    precip: np.ndarray,
    irr: np.ndarray,
    subrin: np.ndarray,
    latqcc: np.ndarray,
) -> np.ndarray:
    raw_proxy = qofe - upstrmq - precip - irr - subrin + latqcc
    return np.where(np.abs(qofe) > NONZERO_TOLERANCE, raw_proxy, np.nan)


def _load_wat_ofe_rows_for_wepp(interchange_dir: Path, wepp_id: int) -> pd.DataFrame:
    targets = base._prepare_paths(interchange_dir)

    with duckdb.connect(":memory:") as con:
        columns = base._describe_columns(con, targets.wat_path)
        context = str(targets.wat_path)
        wepp_column = base._resolve_required_column(columns, ("wepp_id",), context=context)
        year_column = base._resolve_required_column(columns, ("year",), context=context)
        sim_day_column = base._resolve_sim_day_column(columns, context=context)
        julian_column = base._resolve_required_column(columns, ("julian",), context=context)
        month_column = base._resolve_required_column(columns, ("month",), context=context)
        day_of_month_column = base._resolve_required_column(columns, ("day_of_month",), context=context)
        water_year_column = base._resolve_required_column(columns, ("water_year",), context=context)
        area_column = base._resolve_required_column(columns, ("Area",), context=context)
        ofe_column = base._resolve_ofe_column(columns)

        required_terms = (
            "P",
            "RM",
            "Dp",
            "Ep",
            "Es",
            "Er",
            "Tile",
            "Irr",
            "UpStrmQ",
            "SubRIn",
            "latqcc",
            "QOFE",
            "Total-Soil Water",
            "frozwt",
            "Snow-Water",
        )
        resolved_required: dict[str, str] = {}
        for name in required_terms:
            resolved_required[name] = base._resolve_required_column(columns, (name,), context=context)

        q_eff_column = base._resolve_column(columns, ("Q",))
        soilwatertotal_column = base._resolve_column(columns, ("SoilWaterTotal",))
        interception_storage_column = base._resolve_column(columns, ("InterceptionStorage",))

        if ofe_column is None:
            ofe_expr = "CAST(1 AS INTEGER) AS ofe_id"
            order_ofe = "ofe_id"
        else:
            ofe_expr = f'"{ofe_column}" AS ofe_id'
            order_ofe = f'"{ofe_column}"'

        soilwatertotal_expr = (
            f'CAST("{soilwatertotal_column}" AS DOUBLE) AS SoilWaterTotal'
            if soilwatertotal_column is not None
            else "CAST(NULL AS DOUBLE) AS SoilWaterTotal"
        )
        q_eff_expr = (
            f'CAST("{q_eff_column}" AS DOUBLE) AS Q_eff'
            if q_eff_column is not None
            else "CAST(NULL AS DOUBLE) AS Q_eff"
        )
        interception_storage_expr = (
            f'CAST("{interception_storage_column}" AS DOUBLE) AS InterceptionStorage'
            if interception_storage_column is not None
            else "CAST(NULL AS DOUBLE) AS InterceptionStorage"
        )

        query = f"""
            SELECT
                "{year_column}" AS year,
                "{sim_day_column}" AS sim_day_index,
                "{julian_column}" AS julian,
                "{month_column}" AS month,
                "{day_of_month_column}" AS day_of_month,
                "{water_year_column}" AS water_year,
                {ofe_expr},
                CAST("{area_column}" AS DOUBLE) AS Area,
                CAST("{resolved_required['P']}" AS DOUBLE) AS P,
                CAST("{resolved_required['RM']}" AS DOUBLE) AS RM,
                CAST("{resolved_required['Dp']}" AS DOUBLE) AS Dp,
                CAST("{resolved_required['Ep']}" AS DOUBLE) AS Ep,
                CAST("{resolved_required['Es']}" AS DOUBLE) AS Es,
                CAST("{resolved_required['Er']}" AS DOUBLE) AS Er,
                CAST("{resolved_required['Tile']}" AS DOUBLE) AS Tile,
                CAST("{resolved_required['Irr']}" AS DOUBLE) AS Irr,
                CAST("{resolved_required['UpStrmQ']}" AS DOUBLE) AS UpStrmQ,
                CAST("{resolved_required['SubRIn']}" AS DOUBLE) AS SubRIn,
                CAST("{resolved_required['latqcc']}" AS DOUBLE) AS latqcc,
                CAST("{resolved_required['QOFE']}" AS DOUBLE) AS QOFE,
                CAST("{resolved_required['Total-Soil Water']}" AS DOUBLE) AS Total_Soil_Water,
                CAST("{resolved_required['frozwt']}" AS DOUBLE) AS frozwt,
                CAST("{resolved_required['Snow-Water']}" AS DOUBLE) AS Snow_Water,
                {q_eff_expr},
                {soilwatertotal_expr},
                {interception_storage_expr}
            FROM read_parquet('{_sql_path(targets.wat_path)}')
            WHERE "{wepp_column}" = {int(wepp_id)}
            ORDER BY
                "{year_column}",
                "{julian_column}",
                "{sim_day_column}",
                {order_ofe}
        """
        df = con.execute(query).df()

    if df.empty:
        raise ValueError(f"No H.wat OFE rows found for wepp_id={wepp_id} under {targets.interchange_dir}")

    df["ofe_id"] = df["ofe_id"].astype(int)
    numeric_columns = [
        "Area",
        "P",
        "RM",
        "Dp",
        "Ep",
        "Es",
        "Er",
        "Tile",
        "Irr",
        "UpStrmQ",
        "SubRIn",
        "latqcc",
        "QOFE",
        "Q_eff",
        "Total_Soil_Water",
        "frozwt",
        "Snow_Water",
        "SoilWaterTotal",
        "InterceptionStorage",
    ]
    for column in numeric_columns:
        df[column] = df[column].astype(float)

    return df.sort_values(DATE_SORT_COLUMNS + ["ofe_id"], kind="mergesort").reset_index(drop=True)


def _empty_chain_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *DATE_COLUMNS,
            "ofe_up",
            "ofe_down",
            "audit_chain_subsurface_transfer_residual_m3",
            "audit_chain_surface_transfer_residual_m3_geometry_sensitive",
            "audit_chain_subrin_down_m3",
            "audit_chain_latqcc_up_m3",
            "audit_chain_upstrmq_down_m3",
            "audit_chain_qofe_up_m3",
        ]
    )


def compute_mofe_chain_audit(ofe_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    chain_records: list[dict[str, float | int]] = []
    first_records: list[dict[str, float | int]] = []

    for _, day_rows in ofe_rows.groupby(list(DATE_COLUMNS), sort=False):
        ordered = day_rows.sort_values("ofe_id", kind="mergesort").reset_index(drop=True)
        first = ordered.iloc[0]
        first_records.append(
            {
                "year": int(first["year"]),
                "sim_day_index": int(first["sim_day_index"]),
                "julian": int(first["julian"]),
                "month": int(first["month"]),
                "day_of_month": int(first["day_of_month"]),
                "water_year": int(first["water_year"]),
                "audit_first_ofe_id": int(first["ofe_id"]),
                "audit_first_ofe_upstrmq_mm": float(first["UpStrmQ"]),
                "audit_first_ofe_subrin_mm": float(first["SubRIn"]),
            }
        )

        for idx in range(1, ordered.shape[0]):
            up = ordered.iloc[idx - 1]
            down = ordered.iloc[idx]
            subrin_down_m3 = float(down["SubRIn"]) * 0.001 * float(down["Area"])
            latqcc_up_m3 = float(up["latqcc"]) * 0.001 * float(up["Area"])
            upstrmq_down_m3 = float(down["UpStrmQ"]) * 0.001 * float(down["Area"])
            qofe_up_m3 = float(up["QOFE"]) * 0.001 * float(up["Area"])

            chain_records.append(
                {
                    "year": int(up["year"]),
                    "sim_day_index": int(up["sim_day_index"]),
                    "julian": int(up["julian"]),
                    "month": int(up["month"]),
                    "day_of_month": int(up["day_of_month"]),
                    "water_year": int(up["water_year"]),
                    "ofe_up": int(up["ofe_id"]),
                    "ofe_down": int(down["ofe_id"]),
                    "audit_chain_subsurface_transfer_residual_m3": subrin_down_m3 - latqcc_up_m3,
                    "audit_chain_surface_transfer_residual_m3_geometry_sensitive": upstrmq_down_m3 - qofe_up_m3,
                    "audit_chain_subrin_down_m3": subrin_down_m3,
                    "audit_chain_latqcc_up_m3": latqcc_up_m3,
                    "audit_chain_upstrmq_down_m3": upstrmq_down_m3,
                    "audit_chain_qofe_up_m3": qofe_up_m3,
                }
            )

    chain_df = pd.DataFrame.from_records(chain_records) if chain_records else _empty_chain_frame()
    first_df = pd.DataFrame.from_records(first_records)
    return chain_df, first_df


def _compute_daily_full_physical_closure(ofe_rows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    work = ofe_rows.sort_values(DATE_SORT_COLUMNS + ["ofe_id"], kind="mergesort").copy()

    legacy_soil_storage_mm = work["Total_Soil_Water"].to_numpy(dtype=np.float64, copy=False) + work[
        "frozwt"
    ].to_numpy(dtype=np.float64, copy=False)

    soilwatertotal = work["SoilWaterTotal"].to_numpy(dtype=np.float64, copy=False)
    has_soilwatertotal_any = bool(np.isfinite(soilwatertotal).any())
    if has_soilwatertotal_any:
        soil_storage_mm = np.where(np.isfinite(soilwatertotal), soilwatertotal, legacy_soil_storage_mm)
    else:
        soil_storage_mm = legacy_soil_storage_mm

    interception_storage = work["InterceptionStorage"].to_numpy(dtype=np.float64, copy=False)
    has_interception_storage_any = bool(np.isfinite(interception_storage).any())
    interception_storage_mm = np.where(np.isfinite(interception_storage), interception_storage, 0.0)

    storage_basis_base = "SoilWaterTotal_plus_SnowWater" if has_soilwatertotal_any else "LegacyProfileWater_plus_SnowWater"
    storage_basis = (
        f"{storage_basis_base}_plus_InterceptionStorage"
        if has_interception_storage_any
        else storage_basis_base
    )

    work["audit_full_soil_storage_mm_ofe"] = soil_storage_mm
    work["audit_full_interception_storage_mm_ofe"] = interception_storage_mm
    work["audit_full_storage_mm_ofe"] = (
        soil_storage_mm
        + work["Snow_Water"].to_numpy(dtype=np.float64, copy=False)
        + interception_storage_mm
    )
    work["audit_full_storage_delta_mm_ofe"] = (
        work.groupby("ofe_id", sort=False)["audit_full_storage_mm_ofe"].diff().fillna(0.0)
    )
    work["audit_full_et_mm_ofe"] = (
        work["Ep"].to_numpy(dtype=np.float64, copy=False)
        + work["Es"].to_numpy(dtype=np.float64, copy=False)
        + work["Er"].to_numpy(dtype=np.float64, copy=False)
    )

    work["audit_full_physical_ofe_closure_residual_mm"] = (
        work["P"].to_numpy(dtype=np.float64, copy=False)
        + work["Irr"].to_numpy(dtype=np.float64, copy=False)
        + work["UpStrmQ"].to_numpy(dtype=np.float64, copy=False)
        + work["SubRIn"].to_numpy(dtype=np.float64, copy=False)
        - work["QOFE"].to_numpy(dtype=np.float64, copy=False)
        - work["latqcc"].to_numpy(dtype=np.float64, copy=False)
        - work["Dp"].to_numpy(dtype=np.float64, copy=False)
        - work["audit_full_et_mm_ofe"].to_numpy(dtype=np.float64, copy=False)
        - work["Tile"].to_numpy(dtype=np.float64, copy=False)
        - work["audit_full_storage_delta_mm_ofe"].to_numpy(dtype=np.float64, copy=False)
    )
    q_eff = work["Q_eff"].to_numpy(dtype=np.float64, copy=False)
    qofe = work["QOFE"].to_numpy(dtype=np.float64, copy=False)
    work["audit_qofe_to_q_ratio_ofe"] = np.divide(
        qofe,
        q_eff,
        out=np.full_like(qofe, np.nan, dtype=np.float64),
        where=np.abs(q_eff) > NONZERO_TOLERANCE,
    )
    work["audit_surface_pulse_proxy_mm_ofe"] = _compute_surface_pulse_proxy_mm_ofe(
        qofe=qofe,
        upstrmq=work["UpStrmQ"].to_numpy(dtype=np.float64, copy=False),
        precip=work["P"].to_numpy(dtype=np.float64, copy=False),
        irr=work["Irr"].to_numpy(dtype=np.float64, copy=False),
        subrin=work["SubRIn"].to_numpy(dtype=np.float64, copy=False),
        latqcc=work["latqcc"].to_numpy(dtype=np.float64, copy=False),
    )
    work["audit_surface_pulse_proxy_pos_mm_ofe"] = np.maximum(
        work["audit_surface_pulse_proxy_mm_ofe"].to_numpy(dtype=np.float64, copy=False),
        0.0,
    )

    for column in (
        "P",
        "Irr",
        "RM",
        "UpStrmQ",
        "SubRIn",
        "QOFE",
        "latqcc",
        "Dp",
        "audit_full_et_mm_ofe",
        "Tile",
        "audit_full_storage_mm_ofe",
    ):
        work[f"{column}_volume_m3"] = (
            work[column].to_numpy(dtype=np.float64, copy=False)
            * 0.001
            * work["Area"].to_numpy(dtype=np.float64, copy=False)
        )

    day_records: list[dict[str, Any]] = []
    for key, day_rows in work.groupby(list(DATE_COLUMNS), sort=False):
        total_area = float(day_rows["Area"].sum())
        p_v = float(day_rows["P_volume_m3"].sum())
        irr_v = float(day_rows["Irr_volume_m3"].sum())
        external_input_v = p_v + irr_v
        rm_v = float(day_rows["RM_volume_m3"].sum())
        upstrmq_v = float(day_rows["UpStrmQ_volume_m3"].sum())
        subrin_v = float(day_rows["SubRIn_volume_m3"].sum())
        qofe_v = float(day_rows["QOFE_volume_m3"].sum())
        latqcc_v = float(day_rows["latqcc_volume_m3"].sum())
        dp_v = float(day_rows["Dp_volume_m3"].sum())
        et_v = float(day_rows["audit_full_et_mm_ofe_volume_m3"].sum())
        tile_v = float(day_rows["Tile_volume_m3"].sum())
        storage_v = float(day_rows["audit_full_storage_mm_ofe_volume_m3"].sum())

        residual_series = day_rows["audit_full_physical_ofe_closure_residual_mm"].to_numpy(dtype=np.float64, copy=False)
        residual_idx = int(np.argmax(np.abs(residual_series)))
        residual_row = day_rows.iloc[residual_idx]

        max_ofe_id = int(day_rows["ofe_id"].max())
        late_ofe_min = max(1, max_ofe_id - SCIREVIEW_LATE_OFE_WINDOW + 1)
        late_rows = day_rows[day_rows["ofe_id"] >= late_ofe_min].copy()

        late_residual = late_rows["audit_full_physical_ofe_closure_residual_mm"].to_numpy(
            dtype=np.float64, copy=False
        )
        late_pulse = late_rows["audit_surface_pulse_proxy_pos_mm_ofe"].to_numpy(dtype=np.float64, copy=False)
        late_ratio = late_rows["audit_qofe_to_q_ratio_ofe"].to_numpy(dtype=np.float64, copy=False)
        late_ratio_finite = late_ratio[np.isfinite(late_ratio)]

        late_residual_max_abs = float(np.max(np.abs(late_residual))) if late_residual.size else 0.0
        if late_pulse.size:
            late_pulse_max = float("nan") if np.isnan(late_pulse).all() else float(np.nanmax(late_pulse))
        else:
            late_pulse_max = float("nan")
        late_ratio_max = float(np.max(late_ratio_finite)) if late_ratio_finite.size else float("nan")
        late_outlier_idx = int(np.argmax(np.abs(late_residual))) if late_residual.size else 0
        late_outlier_row = late_rows.iloc[late_outlier_idx] if late_residual.size else residual_row

        residual_exceeds = late_residual_max_abs >= SCIREVIEW_RESIDUAL_THRESHOLD_MM
        pulse_supported = bool(np.isfinite(late_pulse_max))
        pulse_exceeds = bool(pulse_supported and (late_pulse_max >= SCIREVIEW_SURFACE_PULSE_PROXY_THRESHOLD_MM))
        ratio_supported = bool(late_ratio_finite.size)
        ratio_exceeds = bool(ratio_supported and (late_ratio_max >= SCIREVIEW_QOFE_TO_Q_RATIO_THRESHOLD))
        all_supported = bool(pulse_supported and ratio_supported)
        requires_scientific_review = bool(all_supported and residual_exceeds and pulse_exceeds and ratio_exceeds)

        scireview_reason = (
            "late_ofe_residual_plus_qofe_to_q_ratio_plus_surface_pulse_proxy"
            if requires_scientific_review
            else "none"
        )

        day_records.append(
            {
                "year": int(key[0]),
                "sim_day_index": int(key[1]),
                "julian": int(key[2]),
                "month": int(key[3]),
                "day_of_month": int(key[4]),
                "water_year": int(key[5]),
                "n_ofe": int(day_rows["ofe_id"].nunique()),
                "audit_full_physical_total_area_m2": total_area,
                "audit_full_p_volume_m3": p_v,
                "audit_full_irr_volume_m3": irr_v,
                "audit_full_external_input_volume_m3": external_input_v,
                "audit_full_rm_volume_m3": rm_v,
                "audit_full_upstrmq_volume_m3": upstrmq_v,
                "audit_full_subrin_volume_m3": subrin_v,
                "audit_full_qofe_volume_m3": qofe_v,
                "audit_full_latqcc_volume_m3": latqcc_v,
                "audit_full_dp_volume_m3": dp_v,
                "audit_full_et_volume_m3": et_v,
                "audit_full_tile_volume_m3": tile_v,
                "audit_full_storage_volume_m3": storage_v,
                "audit_full_max_abs_ofe_closure_residual_mm": float(np.max(np.abs(residual_series))),
                "audit_full_mean_abs_ofe_closure_residual_mm": float(np.mean(np.abs(residual_series))),
                "audit_full_outlier_ofe_id": int(residual_row["ofe_id"]),
                "audit_full_outlier_ofe_closure_residual_mm": float(
                    residual_row["audit_full_physical_ofe_closure_residual_mm"]
                ),
                "audit_late_ofe_min": int(late_ofe_min),
                "audit_late_ofe_max": int(max_ofe_id),
                "audit_late_max_abs_ofe_closure_residual_mm": late_residual_max_abs,
                "audit_late_max_qofe_to_q_ratio": late_ratio_max,
                "audit_late_max_surface_pulse_proxy_mm": late_pulse_max,
                "audit_late_outlier_ofe_id": int(late_outlier_row["ofe_id"]),
                "audit_requires_scientific_review": bool(requires_scientific_review),
                "audit_requires_scientific_review_reason": scireview_reason,
            }
        )

    daily = pd.DataFrame.from_records(day_records).sort_values(DATE_SORT_COLUMNS, kind="mergesort").reset_index(
        drop=True
    )

    storage_volume = daily["audit_full_storage_volume_m3"].to_numpy(dtype=np.float64, copy=False)
    storage_delta_volume = np.diff(storage_volume, prepend=storage_volume[0])
    daily["audit_full_storage_delta_volume_m3"] = storage_delta_volume

    known_inputs_volume = (
        daily["audit_full_external_input_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_upstrmq_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_subrin_volume_m3"].to_numpy(dtype=np.float64, copy=False)
    )
    known_outputs_volume = (
        daily["audit_full_qofe_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_latqcc_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_dp_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_et_volume_m3"].to_numpy(dtype=np.float64, copy=False)
        + daily["audit_full_tile_volume_m3"].to_numpy(dtype=np.float64, copy=False)
    )
    closure_residual_volume = known_inputs_volume - known_outputs_volume - storage_delta_volume

    daily["audit_full_known_inputs_volume_m3"] = known_inputs_volume
    daily["audit_full_known_outputs_volume_m3"] = known_outputs_volume
    daily["audit_full_closure_residual_volume_m3"] = closure_residual_volume

    area = daily["audit_full_physical_total_area_m2"].to_numpy(dtype=np.float64, copy=False)
    daily["audit_full_known_inputs_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(known_inputs_volume, area)],
        dtype=np.float64,
    )
    daily["audit_full_known_outputs_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(known_outputs_volume, area)],
        dtype=np.float64,
    )
    daily["audit_full_storage_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(storage_volume, area)],
        dtype=np.float64,
    )
    daily["audit_full_storage_delta_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(storage_delta_volume, area)],
        dtype=np.float64,
    )
    daily["audit_full_physical_closure_residual_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(closure_residual_volume, area)],
        dtype=np.float64,
    )
    daily["audit_full_implied_unresolved_term_mm"] = daily[
        "audit_full_physical_closure_residual_mm"
    ].to_numpy(dtype=np.float64, copy=False)

    daily["audit_full_rm_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_rm_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_p_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_p_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_irr_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_irr_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_external_input_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_external_input_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_upstrmq_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_upstrmq_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_subrin_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_subrin_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_qofe_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_qofe_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_latqcc_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_latqcc_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_dp_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_dp_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_et_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_et_volume_m3"], area)],
        dtype=np.float64,
    )
    daily["audit_full_tile_mm"] = np.array(
        [_safe_depth_scalar(v, a) for v, a in zip(daily["audit_full_tile_volume_m3"], area)],
        dtype=np.float64,
    )

    metadata = {
        "storage_basis": storage_basis,
        "uses_soilwatertotal": has_soilwatertotal_any,
        "soilwatertotal_missing_rows": int(np.count_nonzero(~np.isfinite(soilwatertotal))),
        "uses_interception_storage": has_interception_storage_any,
        "interception_storage_missing_rows": int(np.count_nonzero(~np.isfinite(interception_storage))),
    }

    keep_columns = [
        *DATE_COLUMNS,
        "audit_full_physical_total_area_m2",
        "audit_full_known_inputs_mm",
        "audit_full_known_outputs_mm",
        "audit_full_storage_mm",
        "audit_full_storage_delta_mm",
        "audit_full_physical_closure_residual_mm",
        "audit_full_implied_unresolved_term_mm",
        "audit_full_p_mm",
        "audit_full_irr_mm",
        "audit_full_external_input_mm",
        "audit_full_rm_mm",
        "audit_full_upstrmq_mm",
        "audit_full_subrin_mm",
        "audit_full_qofe_mm",
        "audit_full_latqcc_mm",
        "audit_full_dp_mm",
        "audit_full_et_mm",
        "audit_full_tile_mm",
        "audit_full_max_abs_ofe_closure_residual_mm",
        "audit_full_mean_abs_ofe_closure_residual_mm",
        "audit_full_outlier_ofe_id",
        "audit_full_outlier_ofe_closure_residual_mm",
        "audit_late_ofe_min",
        "audit_late_ofe_max",
        "audit_late_max_abs_ofe_closure_residual_mm",
        "audit_late_max_qofe_to_q_ratio",
        "audit_late_max_surface_pulse_proxy_mm",
        "audit_late_outlier_ofe_id",
        "audit_requires_scientific_review",
        "audit_requires_scientific_review_reason",
    ]
    return daily[keep_columns].copy(), metadata


def _compute_outlet_qofe_reconciliation(daily_dataset: pd.DataFrame, ofe_rows: pd.DataFrame) -> pd.DataFrame:
    outlet = (
        ofe_rows.sort_values(DATE_SORT_COLUMNS + ["ofe_id"], kind="mergesort")
        .groupby(list(DATE_COLUMNS), as_index=False)
        .tail(1)
        .copy()
    )
    outlet["audit_outlet_ofe_id"] = outlet["ofe_id"].astype(int)
    outlet["audit_outlet_qofe_m3"] = outlet["QOFE"].to_numpy(dtype=np.float64, copy=False) * 0.001 * outlet[
        "Area"
    ].to_numpy(dtype=np.float64, copy=False)
    outlet = outlet[list(DATE_COLUMNS) + ["audit_outlet_ofe_id", "audit_outlet_qofe_m3"]]

    merged = daily_dataset[list(DATE_COLUMNS) + ["runvol"]].merge(
        outlet,
        on=list(DATE_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    merged["audit_outlet_runvol_m3"] = merged["runvol"].to_numpy(dtype=np.float64, copy=False)
    merged["audit_outlet_runvol_vs_qofe_residual_m3"] = (
        merged["audit_outlet_runvol_m3"].to_numpy(dtype=np.float64, copy=False)
        - merged["audit_outlet_qofe_m3"].to_numpy(dtype=np.float64, copy=False)
    )
    return merged[
        list(DATE_COLUMNS)
        + [
            "audit_outlet_ofe_id",
            "audit_outlet_runvol_m3",
            "audit_outlet_qofe_m3",
            "audit_outlet_runvol_vs_qofe_residual_m3",
        ]
    ]


def _daily_chain_extrema(chain_df: pd.DataFrame) -> pd.DataFrame:
    if chain_df.empty:
        return pd.DataFrame(
            columns=[
                *DATE_COLUMNS,
                "audit_chain_max_abs_subsurface_transfer_residual_m3",
                "audit_chain_max_abs_surface_transfer_residual_m3_geometry_sensitive",
            ]
        )

    work = chain_df.copy()
    work["abs_subsurface"] = work["audit_chain_subsurface_transfer_residual_m3"].abs()
    work["abs_surface"] = work["audit_chain_surface_transfer_residual_m3_geometry_sensitive"].abs()

    grouped = (
        work.groupby(list(DATE_COLUMNS), as_index=False)
        .agg(
            audit_chain_max_abs_subsurface_transfer_residual_m3=("abs_subsurface", "max"),
            audit_chain_max_abs_surface_transfer_residual_m3_geometry_sensitive=("abs_surface", "max"),
        )
        .reset_index(drop=True)
    )
    return grouped


def _quantiles(values: np.ndarray) -> dict[str, float] | None:
    if values.size == 0:
        return None
    return {
        "p50": float(np.quantile(values, 0.50)),
        "p90": float(np.quantile(values, 0.90)),
        "p95": float(np.quantile(values, 0.95)),
        "p99": float(np.quantile(values, 0.99)),
        "max_abs": float(np.max(np.abs(values))),
    }


def _top_row_by_abs(df: pd.DataFrame, column: str) -> dict[str, int | float] | None:
    if df.empty:
        return None
    idx = int(np.argmax(np.abs(df[column].to_numpy(dtype=np.float64, copy=False))))
    row = df.iloc[idx]
    return {
        "year": int(row["year"]),
        "julian": int(row["julian"]),
        "month": int(row["month"]),
        "day_of_month": int(row["day_of_month"]),
        column: float(row[column]),
    }


def _top_chain_row_by_abs(df: pd.DataFrame, column: str) -> dict[str, int | float] | None:
    if df.empty:
        return None
    idx = int(np.argmax(np.abs(df[column].to_numpy(dtype=np.float64, copy=False))))
    row = df.iloc[idx]
    return {
        "year": int(row["year"]),
        "julian": int(row["julian"]),
        "month": int(row["month"]),
        "day_of_month": int(row["day_of_month"]),
        "ofe_up": int(row["ofe_up"]),
        "ofe_down": int(row["ofe_down"]),
        column: float(row[column]),
    }


def _build_full_physical_summary(daily_full: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    residual = daily_full["audit_full_physical_closure_residual_mm"].to_numpy(dtype=np.float64, copy=False)
    unresolved = daily_full["audit_full_implied_unresolved_term_mm"].to_numpy(dtype=np.float64, copy=False)
    ofe_max = daily_full["audit_full_max_abs_ofe_closure_residual_mm"].to_numpy(dtype=np.float64, copy=False)
    late_residual = daily_full["audit_late_max_abs_ofe_closure_residual_mm"].to_numpy(dtype=np.float64, copy=False)
    late_ratio = daily_full["audit_late_max_qofe_to_q_ratio"].to_numpy(dtype=np.float64, copy=False)
    late_pulse = daily_full["audit_late_max_surface_pulse_proxy_mm"].to_numpy(dtype=np.float64, copy=False)
    scireview_flags = daily_full["audit_requires_scientific_review"].to_numpy(dtype=bool, copy=False)
    scireview_days = int(np.count_nonzero(scireview_flags))

    rm = daily_full["audit_full_rm_mm"].to_numpy(dtype=np.float64, copy=False)
    rm_total = float(np.sum(rm))
    external_input = daily_full["audit_full_external_input_mm"].to_numpy(dtype=np.float64, copy=False)
    external_input_total = float(np.sum(external_input))
    residual_total = float(np.sum(residual))

    scireview_top: dict[str, int | float | str] | None = None
    if scireview_days > 0:
        flagged = daily_full[daily_full["audit_requires_scientific_review"]].copy()
        idx = int(np.argmax(flagged["audit_late_max_abs_ofe_closure_residual_mm"].to_numpy(dtype=np.float64, copy=False)))
        row = flagged.iloc[idx]
        scireview_top = {
            "year": int(row["year"]),
            "julian": int(row["julian"]),
            "month": int(row["month"]),
            "day_of_month": int(row["day_of_month"]),
            "late_outlier_ofe_id": int(row["audit_late_outlier_ofe_id"]),
            "late_max_abs_ofe_closure_residual_mm": float(row["audit_late_max_abs_ofe_closure_residual_mm"]),
            "late_max_qofe_to_q_ratio": float(row["audit_late_max_qofe_to_q_ratio"]),
            "late_max_surface_pulse_proxy_mm": float(row["audit_late_max_surface_pulse_proxy_mm"]),
            "reason": str(row["audit_requires_scientific_review_reason"]),
        }

    return {
        "rows": int(daily_full.shape[0]),
        "storage_basis": metadata["storage_basis"],
        "uses_soilwatertotal": bool(metadata["uses_soilwatertotal"]),
        "soilwatertotal_missing_rows": int(metadata["soilwatertotal_missing_rows"]),
        "uses_interception_storage": bool(metadata["uses_interception_storage"]),
        "interception_storage_missing_rows": int(metadata["interception_storage_missing_rows"]),
        "external_input_mm": _quantiles(external_input),
        "known_inputs_mm": _quantiles(daily_full["audit_full_known_inputs_mm"].to_numpy(dtype=np.float64, copy=False)),
        "known_outputs_mm": _quantiles(
            daily_full["audit_full_known_outputs_mm"].to_numpy(dtype=np.float64, copy=False)
        ),
        "storage_delta_mm": _quantiles(daily_full["audit_full_storage_delta_mm"].to_numpy(dtype=np.float64, copy=False)),
        "closure_residual_mm": _quantiles(residual),
        "implied_unresolved_term_mm": _quantiles(unresolved),
        "max_abs_ofe_closure_residual_mm": _quantiles(ofe_max),
        "late_max_abs_ofe_closure_residual_mm": _quantiles(late_residual),
        "late_max_qofe_to_q_ratio": _quantiles(late_ratio[np.isfinite(late_ratio)]),
        "late_max_surface_pulse_proxy_mm": _quantiles(late_pulse[np.isfinite(late_pulse)]),
        "requires_scientific_review": bool(scireview_days > 0),
        "requires_scientific_review_days": scireview_days,
        "requires_scientific_review_thresholds": {
            "late_ofe_window": SCIREVIEW_LATE_OFE_WINDOW,
            "late_max_abs_ofe_closure_residual_mm": SCIREVIEW_RESIDUAL_THRESHOLD_MM,
            "late_max_qofe_to_q_ratio": SCIREVIEW_QOFE_TO_Q_RATIO_THRESHOLD,
            "late_max_surface_pulse_proxy_mm": SCIREVIEW_SURFACE_PULSE_PROXY_THRESHOLD_MM,
        },
        "max_requires_scientific_review_day": scireview_top,
        "closure_residual_total_mm": residual_total,
        "closure_residual_pct_of_external_input_total": (
            float((residual_total / external_input_total) * 100.0)
            if external_input_total != 0.0
            else 0.0
        ),
        "closure_residual_pct_of_rm_total": float((residual_total / rm_total) * 100.0) if rm_total != 0.0 else 0.0,
        "implied_unresolved_term_interpretation": (
            "positive_values_indicate_missing_sink_in_exported_terms_"
            "(for_example_interception_or_unexported_storage_terms)"
        ),
        "max_abs_day": _top_row_by_abs(daily_full, "audit_full_physical_closure_residual_mm"),
    }


def _build_mofe_chain_summary(
    chain_df: pd.DataFrame,
    first_df: pd.DataFrame,
    outlet_df: pd.DataFrame,
) -> dict[str, Any]:
    sub = chain_df["audit_chain_subsurface_transfer_residual_m3"].to_numpy(dtype=np.float64, copy=False)
    surf = chain_df["audit_chain_surface_transfer_residual_m3_geometry_sensitive"].to_numpy(dtype=np.float64, copy=False)
    first_up = first_df["audit_first_ofe_upstrmq_mm"].to_numpy(dtype=np.float64, copy=False)
    first_sub = first_df["audit_first_ofe_subrin_mm"].to_numpy(dtype=np.float64, copy=False)
    outlet = outlet_df["audit_outlet_runvol_vs_qofe_residual_m3"].to_numpy(dtype=np.float64, copy=False)

    return {
        "rows": int(chain_df.shape[0]),
        "days": int(first_df.shape[0]),
        "strict_chain_invariants_contract_scope": "non-channel_non-contour_only",
        "strict_chain_invariants_applicable": None,
        "strict_chain_invariants_applicability": "unknown_from_interchange",
        "adjacent_chain_checks_interpretation": "diagnostic_when_applicability_unknown",
        "subsurface_transfer_residual_m3": _quantiles(sub),
        "surface_transfer_residual_m3_geometry_sensitive": _quantiles(surf),
        "first_ofe_upstrmq_mm": _quantiles(first_up),
        "first_ofe_subrin_mm": _quantiles(first_sub),
        "first_ofe_nonzero_upstrmq_days": int(np.count_nonzero(np.abs(first_up) > NONZERO_TOLERANCE)),
        "first_ofe_nonzero_subrin_days": int(np.count_nonzero(np.abs(first_sub) > NONZERO_TOLERANCE)),
        "runoff_pass_vs_outlet_qofe_residual_m3": _quantiles(outlet),
        "max_abs_subsurface_transfer_day": _top_chain_row_by_abs(
            chain_df, "audit_chain_subsurface_transfer_residual_m3"
        ),
        "max_abs_surface_transfer_day": _top_chain_row_by_abs(
            chain_df,
            "audit_chain_surface_transfer_residual_m3_geometry_sensitive",
        ),
    }


def _top_chain_day(chain_df: pd.DataFrame) -> pd.DataFrame:
    if chain_df.empty:
        return pd.DataFrame(
            columns=[
                *DATE_COLUMNS,
                "ofe_up",
                "ofe_down",
                "audit_chain_subsurface_transfer_residual_m3",
                "audit_chain_surface_transfer_residual_m3_geometry_sensitive",
                "abs_chain_subsurface_transfer_residual_m3",
                "abs_chain_surface_transfer_residual_m3_geometry_sensitive",
            ]
        )

    work = chain_df.copy()
    work["abs_chain_subsurface_transfer_residual_m3"] = work[
        "audit_chain_subsurface_transfer_residual_m3"
    ].abs()
    work["abs_chain_surface_transfer_residual_m3_geometry_sensitive"] = work[
        "audit_chain_surface_transfer_residual_m3_geometry_sensitive"
    ].abs()
    work = work.sort_values(
        [
            *DATE_SORT_COLUMNS,
            "abs_chain_subsurface_transfer_residual_m3",
            "abs_chain_surface_transfer_residual_m3_geometry_sensitive",
        ],
        ascending=[True, True, True, False, False],
        kind="mergesort",
    )
    return work.groupby(list(DATE_COLUMNS), as_index=False).head(1).reset_index(drop=True)


def _top_chain_anomalies(audit: pd.DataFrame, chain_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    daily_columns = [
        *DATE_COLUMNS,
        "n_ofe",
        "audit_full_physical_closure_residual_mm",
        "audit_full_implied_unresolved_term_mm",
        "audit_full_max_abs_ofe_closure_residual_mm",
        "audit_full_outlier_ofe_id",
        "audit_full_outlier_ofe_closure_residual_mm",
        "audit_late_ofe_min",
        "audit_late_ofe_max",
        "audit_late_max_abs_ofe_closure_residual_mm",
        "audit_late_max_qofe_to_q_ratio",
        "audit_late_max_surface_pulse_proxy_mm",
        "audit_late_outlier_ofe_id",
        "audit_requires_scientific_review",
        "audit_requires_scientific_review_reason",
        "audit_chain_max_abs_subsurface_transfer_residual_m3",
        "audit_chain_max_abs_surface_transfer_residual_m3_geometry_sensitive",
        "audit_outlet_ofe_id",
        "audit_outlet_runvol_vs_qofe_residual_m3",
        "audit_closure_reconstructed_with_storage_mm",
        "audit_closure_reconstructed_with_enriched_storage_mm",
        "audit_runoff_consistency_mm",
        "audit_rain_melt_reported_mm",
        "audit_precip_reported_mm",
        "audit_runoff_reported_mm",
    ]
    daily = audit[daily_columns].copy()

    chain_day = _top_chain_day(chain_df)
    if chain_day.empty:
        daily["ofe_up"] = np.nan
        daily["ofe_down"] = np.nan
        daily["audit_chain_subsurface_transfer_residual_m3"] = np.nan
        daily["audit_chain_surface_transfer_residual_m3_geometry_sensitive"] = np.nan
        daily["abs_chain_subsurface_transfer_residual_m3"] = np.nan
        daily["abs_chain_surface_transfer_residual_m3_geometry_sensitive"] = np.nan
    else:
        daily = daily.merge(
            chain_day[
                [
                    *DATE_COLUMNS,
                    "ofe_up",
                    "ofe_down",
                    "audit_chain_subsurface_transfer_residual_m3",
                    "audit_chain_surface_transfer_residual_m3_geometry_sensitive",
                    "abs_chain_subsurface_transfer_residual_m3",
                    "abs_chain_surface_transfer_residual_m3_geometry_sensitive",
                ]
            ],
            on=list(DATE_COLUMNS),
            how="left",
            validate="one_to_one",
        )

    daily["abs_full_physical_closure_residual_mm"] = daily["audit_full_physical_closure_residual_mm"].abs()
    daily["abs_outlet_runvol_vs_qofe_residual_m3"] = daily["audit_outlet_runvol_vs_qofe_residual_m3"].abs()

    daily = daily.sort_values(
        [
            "abs_full_physical_closure_residual_mm",
            "audit_full_max_abs_ofe_closure_residual_mm",
            "abs_chain_subsurface_transfer_residual_m3",
            "abs_outlet_runvol_vs_qofe_residual_m3",
        ],
        ascending=[False, False, False, False],
        kind="mergesort",
        na_position="last",
    )
    return daily.head(top_n).reset_index(drop=True)


def _build_output_dir(interchange_dir: Path, wepp_id: int, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return interchange_dir / f"audit_hillslope_mofe_daily_closure_H{int(wepp_id)}"


def _build_daily_scireview_export(audit: pd.DataFrame, wepp_id: int, topaz_id: int | None) -> pd.DataFrame:
    columns = [
        *DATE_COLUMNS,
        "n_ofe",
        "audit_requires_scientific_review",
        "audit_requires_scientific_review_reason",
        "audit_late_max_abs_ofe_closure_residual_mm",
        "audit_late_max_qofe_to_q_ratio",
        "audit_late_max_surface_pulse_proxy_mm",
        "audit_late_outlier_ofe_id",
        "audit_full_physical_closure_residual_mm",
        "audit_full_implied_unresolved_term_mm",
        "audit_full_outlier_ofe_id",
        "audit_full_outlier_ofe_closure_residual_mm",
    ]
    missing = [column for column in columns if column not in audit.columns]
    if missing:
        raise KeyError(
            "daily audit export is missing expected columns: "
            + ", ".join(sorted(missing))
        )

    daily_export = audit[columns].copy()
    daily_export.insert(0, "wepp_id", int(wepp_id))
    daily_export.insert(1, "topaz_id", int(topaz_id) if topaz_id is not None else np.nan)
    return daily_export.sort_values(DATE_SORT_COLUMNS, kind="mergesort").reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interchange_dir", help="Path to .../wepp/output/interchange")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--wepp-id", type=int, default=None, help="Target WEPP hillslope id")
    selector.add_argument("--topaz-id", type=int, default=None, help="Target TOPAZ hillslope id")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for audit outputs (default: <interchange>/audit_hillslope_mofe_daily_closure_H<wepp_id>)",
    )
    parser.add_argument("--top-n", type=int, default=25, help="Number of top anomaly rows to export")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    interchange_dir = Path(args.interchange_dir).expanduser().resolve()
    if not interchange_dir.exists():
        raise FileNotFoundError(interchange_dir)

    topaz_id: int | None = None
    if args.wepp_id is not None:
        wepp_id = int(args.wepp_id)
        topaz_id = base._resolve_topaz_from_wepp(interchange_dir, wepp_id)
    else:
        topaz_id = int(args.topaz_id)
        wepp_id = base._resolve_wepp_from_topaz(interchange_dir, topaz_id)

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

    dataset = base.load_dataset(interchange_dir, wepp_id)
    audit = base.compute_daily_audit(dataset)

    ofe_rows = _load_wat_ofe_rows_for_wepp(interchange_dir, wepp_id)
    chain_df, first_df = compute_mofe_chain_audit(ofe_rows)
    outlet_df = _compute_outlet_qofe_reconciliation(dataset, ofe_rows)
    daily_full, full_metadata = _compute_daily_full_physical_closure(ofe_rows)

    audit = audit.merge(_daily_chain_extrema(chain_df), on=list(DATE_COLUMNS), how="left", validate="one_to_one")
    if not first_df.empty:
        audit = audit.merge(first_df, on=list(DATE_COLUMNS), how="left", validate="one_to_one")
    else:
        audit["audit_first_ofe_id"] = np.nan
        audit["audit_first_ofe_upstrmq_mm"] = np.nan
        audit["audit_first_ofe_subrin_mm"] = np.nan
    audit = audit.merge(outlet_df, on=list(DATE_COLUMNS), how="left", validate="one_to_one")
    audit = audit.merge(daily_full, on=list(DATE_COLUMNS), how="left", validate="one_to_one")

    summary = base.build_summary(
        audit,
        interchange_dir,
        wepp_id=wepp_id,
        topaz_id=topaz_id,
    )
    summary["mofe_chain"] = _build_mofe_chain_summary(chain_df, first_df, outlet_df)
    summary["full_physical_closure"] = _build_full_physical_summary(daily_full, full_metadata)
    summary["sources"] = source_paths

    top = _top_chain_anomalies(audit, chain_df, max(1, int(args.top_n)))

    summary_path = output_dir / "hillslope_mofe_daily_closure_audit_summary.json"
    top_path = output_dir / "hillslope_mofe_daily_closure_audit_top_days.csv"
    daily_path = output_dir / "hillslope_mofe_daily_closure_audit_daily.csv"
    daily_export = _build_daily_scireview_export(audit, wepp_id=wepp_id, topaz_id=topaz_id)

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    top.to_csv(top_path, index=False)
    daily_export.to_csv(daily_path, index=False)

    print(f"interchange_dir={interchange_dir}")
    print(f"wepp_id={wepp_id}")
    print(f"topaz_id={topaz_id}")
    print(f"rows={summary['rows']}")
    print(f"n_ofe_min={summary['n_ofe_min']}")
    print(f"n_ofe_max={summary['n_ofe_max']}")
    print(f"mofe_chain_rows={summary['mofe_chain']['rows']}")
    print(f"mofe_chain_days={summary['mofe_chain']['days']}")
    print(
        "mofe_first_ofe_nonzero_upstrmq_days="
        f"{summary['mofe_chain']['first_ofe_nonzero_upstrmq_days']}"
    )
    print(
        "mofe_first_ofe_nonzero_subrin_days="
        f"{summary['mofe_chain']['first_ofe_nonzero_subrin_days']}"
    )
    print(f"full_physical_storage_basis={summary['full_physical_closure']['storage_basis']}")
    print(
        "full_physical_closure_residual_total_mm="
        f"{summary['full_physical_closure']['closure_residual_total_mm']:.6f}"
    )
    print(
        "full_physical_requires_scientific_review_days="
        f"{summary['full_physical_closure']['requires_scientific_review_days']}"
    )
    print(
        "closure_reconstructed_with_storage_total_mm="
        f"{summary['whole_run_closure']['closure_reconstructed_with_storage_total_mm']:.6f}"
    )
    print(f"summary_json={summary_path}")
    print(f"top_days_csv={top_path}")
    print(f"daily_csv={daily_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
