"""Linear-programming solver utilities for the PathCE mod.

Encapsulates the pulp model setup and post-processing routines that compute the
most cost-effective set of hillslope treatments while respecting sediment
reduction targets. Split out so the NoDb controller can test the optimization
logic in isolation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from pulp import (
    LpConstraint,
    LpMaximize,
    LpMinimize,
    LpProblem,
    LpStatus,
    LpVariable,
    PulpSolverError,
)


@dataclass
class SolverResult:
    selected_hillslopes: List[int]
    treatment_hillslopes: Mapping[str, List[int]]
    total_sddc_reduction: float
    final_sddc: float
    hillslopes_sdyd: pd.DataFrame
    untreatable_sdyd: pd.DataFrame
    total_cost: float
    total_fixed_cost: float
    status: str
    used_secondary: bool


class PathCESolverError(RuntimeError):
    """Raised when the optimization model cannot produce a feasible solution."""


def run_path_cost_effective_solver(
    data: pd.DataFrame,
    treatments: Sequence[str],
    treatment_cost: Sequence[float],
    treatment_quantity: Sequence[float],
    fixed_cost: Sequence[float],
    *,
    sdyd_threshold: float,
    sddc_threshold: float,
    slope_range: Optional[Tuple[Optional[float], Optional[float]]] = None,
    severity_filter: Optional[Sequence[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> SolverResult:
    """
    Execute the PATH cost-effective solver.

    Parameters mirror the historical prototype while returning a structured result.
    """

    if logger is None:
        logger = logging.getLogger(__name__)

    all_data = data.copy()
    working = data.copy()

    total_sddc_postfire = working["NTU post-fire"].sum()
    sddc_reduction_threshold = max(total_sddc_postfire - sddc_threshold, 0)

    if sddc_reduction_threshold == 0:
        logger.info("PATH CE: Sddc threshold already satisfied; solver will run with zero reduction target.")

    if slope_range:
        min_slope, max_slope = slope_range
        if min_slope is not None:
            working = working[working["slope_deg"] >= min_slope]
        if max_slope is not None:
            working = working[working["slope_deg"] <= max_slope]

    if severity_filter:
        severity_filter_set = set(severity_filter)
        working = working[working["Burn severity"].isin(severity_filter_set)]

    working = working.reset_index(drop=True)

    water_quality = working.filter(regex=r"^NTU reduction ")
    soil_erosion = working.filter(regex=r"^Sdyd reduction ")

    benefits = [water_quality, soil_erosion]
    if any(df.empty for df in benefits):
        shape = benefits[0].shape
        benefits = [pd.DataFrame(np.zeros(shape)) if df.empty else df for df in benefits]
        water_quality, soil_erosion = benefits

    hillslope_ids = working["wepp_id"].tolist()
    sediment_yield_thresholds = (working["Sdyd post-fire"] - sdyd_threshold).clip(lower=0)

    num_sites = len(working)
    if num_sites == 0:
        raise PathCESolverError("No hillslopes available after applying filters.")
    num_treatments = len(treatments)
    if not (num_treatments == len(treatment_cost) == len(treatment_quantity) == len(fixed_cost)):
        raise PathCESolverError("Treatment metadata must have matching lengths.")

    treatment_cost_vectors = {
        treatment: working["area"] * cost * quantity
        for treatment, cost, quantity in zip(treatments, treatment_cost, treatment_quantity)
    }

    primary_model = LpProblem("PathCostEffective", LpMinimize)
    x_vars = {
        treatment: [LpVariable(f"x_{treatment}_{i}", 0, 1, cat="Binary") for i in range(num_sites)]
        for treatment in treatments
    }
    b_vars = {treatment: LpVariable(f"B_{treatment}", 0, 1, cat="Binary") for treatment in treatments}

    primary_model += (
        sum(
            x_vars[t][i] * float(treatment_cost_vectors[t].iat[i])
            for t in treatments
            for i in range(num_sites)
        )
        + sum(b_vars[t] * fixed_cost[idx] for idx, t in enumerate(treatments))
    )

    for i in range(num_sites):
        primary_model += sum(x_vars[t][i] for t in treatments) <= 1

    for idx, treatment in enumerate(treatments):
        for i in range(num_sites):
            primary_model += b_vars[treatment] >= x_vars[treatment][i]

    primary_model += (
        sum(
            x_vars[t][i] * float(water_quality.iloc[i, idx])
            for idx, t in enumerate(treatments)
            for i in range(num_sites)
        )
        >= sddc_reduction_threshold
    )

    for i in range(num_sites):
        max_reduction = float(soil_erosion.iloc[i, :].max())
        threshold = float(sediment_yield_thresholds.iat[i])
        if max_reduction > threshold:
            primary_model += (
                sum(
                    x_vars[t][i] * float(soil_erosion.iloc[i, idx])
                    for idx, t in enumerate(treatments)
                )
                >= threshold
            )
        else:
            primary_model += (
                sum(
                    x_vars[t][i] * float(soil_erosion.iloc[i, idx])
                    for idx, t in enumerate(treatments)
                )
                == max_reduction
            )

    used_secondary = False
    try:
        status_code = primary_model.solve()
    except PulpSolverError as exc:  # pragma: no cover - solver backend error
        raise PathCESolverError("PuLP failed to solve the optimization problem.") from exc

    if LpStatus[status_code] != "Optimal":
        logger.warning("PATH CE: primary model not optimal (%s). Attempting secondary maximize.", LpStatus[status_code])
        secondary_result = _run_secondary_model(
            treatments=treatments,
            fixed_cost=fixed_cost,
            treatment_cost_vectors=treatment_cost_vectors,
            water_quality=water_quality,
            soil_erosion=soil_erosion,
            sediment_yield_thresholds=sediment_yield_thresholds,
            num_sites=num_sites,
        )
        if secondary_result is None:
            raise PathCESolverError("No feasible solution found for the configured thresholds.")
        used_secondary = True
        allocation_vars, b_solution, solver_status = secondary_result
    else:
        allocation_vars = {t: [x.varValue for x in x_vars[t]] for t in treatments}
        b_solution = {t: b_vars[t].varValue for t in treatments}
        solver_status = LpStatus[status_code]

    selected_indices = [
        idx for t in treatments for idx, value in enumerate(allocation_vars[t]) if _is_selected(value)
    ]
    selected_hillslopes = [hillslope_ids[idx] for idx in selected_indices]

    treatment_hillslopes = {
        treatment: [hillslope_ids[i] for i, value in enumerate(allocation_vars[treatment]) if _is_selected(value)]
        for treatment in treatments
    }

    total_cost = sum(
        treatment_cost_vectors[treatment].iat[i]
        for treatment in treatments
        for i, value in enumerate(allocation_vars[treatment])
        if _is_selected(value)
    )
    total_fixed_cost = sum(
        (b_solution[treatment] or 0) * fixed_cost[idx] for idx, treatment in enumerate(treatments)
    )

    total_sddc_reduction = sum(
        (allocation_vars[treatment][i] or 0) * float(water_quality.iloc[i, idx])
        for idx, treatment in enumerate(treatments)
        for i in range(num_sites)
    )
    final_sddc = total_sddc_postfire - total_sddc_reduction

    sdyd_records = []
    for i in range(num_sites):
        treatment_applied = None
        for treatment in treatments:
            if _is_selected(allocation_vars[treatment][i]):
                treatment_applied = treatment
                break
        if treatment_applied is not None:
            value = working.at[i, f"Sdyd post-treat {treatment_applied}"]
        else:
            value = working.at[i, "Sdyd post-fire"]
        sdyd_records.append({"wepp_id": hillslope_ids[i], "final_Sdyd": value})

    sdyd_df = pd.DataFrame(sdyd_records)
    untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold].copy()

    missing = all_data[~all_data["wepp_id"].isin(working["wepp_id"])]
    if not missing.empty:
        missing_records = missing[["wepp_id", "Sdyd post-fire"]].rename(
            columns={"Sdyd post-fire": "final_Sdyd"}
        )
        sdyd_df = pd.concat([sdyd_df, missing_records], ignore_index=True)

    sdyd_df.sort_values("wepp_id", inplace=True, ignore_index=True)

    return SolverResult(
        selected_hillslopes=selected_hillslopes,
        treatment_hillslopes=treatment_hillslopes,
        total_sddc_reduction=float(total_sddc_reduction),
        final_sddc=float(final_sddc),
        hillslopes_sdyd=sdyd_df,
        untreatable_sdyd=untreatable_sdyd,
        total_cost=float(total_cost),
        total_fixed_cost=float(total_fixed_cost),
        status=solver_status,
        used_secondary=used_secondary,
    )


def _run_secondary_model(
    *,
    treatments: Sequence[str],
    fixed_cost: Sequence[float],
    treatment_cost_vectors: Mapping[str, pd.Series],
    water_quality: pd.DataFrame,
    soil_erosion: pd.DataFrame,
    sediment_yield_thresholds: pd.Series,
    num_sites: int,
) -> Optional[Tuple[Mapping[str, List[float]], Mapping[str, float], str]]:
    secondary_model = LpProblem("PathCostEffective_Secondary", LpMaximize)
    x_vars = {
        treatment: [
            LpVariable(f"x_secondary_{treatment}_{i}", 0, 1, cat="Binary")
            for i in range(num_sites)
        ]
        for treatment in treatments
    }
    b_vars = {treatment: LpVariable(f"B_secondary_{treatment}", 0, 1, cat="Binary") for treatment in treatments}

    secondary_model += sum(
        x_vars[treatment][i] * float(water_quality.iloc[i, idx])
        for idx, treatment in enumerate(treatments)
        for i in range(num_sites)
    )

    for i in range(num_sites):
        secondary_model += sum(x_vars[t][i] for t in treatments) == 1

    for treatment in treatments:
        for i in range(num_sites):
            secondary_model += b_vars[treatment] >= x_vars[treatment][i]

    for i in range(num_sites):
        max_reduction = float(soil_erosion.iloc[i, :].max())
        threshold = float(sediment_yield_thresholds.iat[i])
        if max_reduction > threshold:
            secondary_model += (
                sum(
                    x_vars[treatment][i] * float(soil_erosion.iloc[i, idx])
                    for idx, treatment in enumerate(treatments)
                )
                >= threshold
            )
        else:
            secondary_model += (
                sum(
                    x_vars[treatment][i] * float(soil_erosion.iloc[i, idx])
                    for idx, treatment in enumerate(treatments)
                )
                == max_reduction
            )

    try:
        status_code = secondary_model.solve()
    except PulpSolverError:  # pragma: no cover - solver backend error
        return None

    if LpStatus[status_code] != "Optimal":
        return None

    allocations = {t: [var.varValue for var in x_vars[t]] for t in treatments}
    b_solution = {t: b_vars[t].varValue for t in treatments}

    return allocations, b_solution, LpStatus[status_code]


def _is_selected(value: Optional[float]) -> bool:
    return value is not None and value >= 0.5
