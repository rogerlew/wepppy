"""PATH cost-effective site-selection solver.

Vendored from Jackson Nakae's PATH-cost-effective repository
(https://github.com/jackson-nakae/PATH-cost-effective, ``PATH_CE.py`` @ 4e3b4a6).

``ce_select_sites_flexible`` is a faithful extraction: the model construction,
constraint semantics, fallback behavior, and 13-tuple return contract match
upstream. Seam changes are limited to module logging in place of ``print`` and
a quiet CBC invocation. Keep the function diffable against upstream when
syncing; put wepppy-specific behavior in the wrapper, not the algorithm.

``run_path_cost_effective_solver`` is the wepppy-facing wrapper. It applies
the input cleaning Jackson's report performs on CSV-round-tripped frames
(adapted for parquet frames, which preserve list-typed columns such as
``topaz_ids``), then enforces two seam contracts the faithful core does not:

- **Acre cost basis (D4 / ADR-0023):** wepppy prepared frames carry the area
  column in hectares (upstream multiplies it against $/acre rates — a known
  upstream unit defect). The wrapper converts the area column to acres before
  solving, so cost vectors are ``area (ac) x unit_cost ($/ac) x quantity``.
- **Label-based treatment alignment:** the core pairs treatments to
  ``{Sddc,Sdyd} reduction`` columns positionally (frame column order), while
  ``Sdyd post-treat`` lookups are label-keyed. The wrapper validates configured
  labels against the frame, prunes unconfigured reduction columns, and reorders
  the treatment vectors to the frame's column order so both pairings agree for
  any configured order or subset.

Sync notes and reference goldens: ``docs/work-packages/20260720_path_ce_v2/``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from pulp import (
    LpMinimize,
    LpMaximize,
    LpProblem,
    LpStatus,
    LpVariable,
    PulpSolverError,
    PULP_CBC_CMD,
)

__all__ = [
    "ACRES_PER_HECTARE",
    "PathCESolverError",
    "SolverResult",
    "ce_select_sites_flexible",
    "clean_solver_frame",
    "convert_area_to_acres",
    "detect_area_col",
    "detect_id_col",
    "prepare_solver_inputs",
    "run_path_cost_effective_solver",
]

logger = logging.getLogger(__name__)

ACRES_PER_HECTARE = 2.47105


def _cbc():
    return PULP_CBC_CMD(msg=False)


def ce_select_sites_flexible(
    data,
    treatments,
    treatment_cost,
    treatment_quantity,
    fixed_cost,
    sdyd_threshold,
    sddc_threshold,
    slope_range=None,
    bs_threshold=None,
    id_col=None,
    area_col=None,
    return_increase_class=True,
):
    """Run CE site selection on either cumulative-contribution or stream-order Omni outputs.

    Auto-detects identifier and area columns used by the two common schemas:
    - Legacy/cumulative-style tables: wepp_id + area
    - Aggregate/stream-order-style tables: contrast_id + area_sum
    """
    all_data = data.copy()

    if id_col is None:
        if "wepp_id" in data.columns:
            id_col = "wepp_id"
            logger.info("Using 'wepp_id' as identifier column.")
        elif "contrast_id" in data.columns:
            id_col = "contrast_id"
            logger.info("Using 'contrast_id' as identifier column.")
        else:
            raise KeyError("Data must contain either 'wepp_id' or 'contrast_id'.")

    if area_col is None:
        if "area" in data.columns:
            area_col = "area"
            logger.info("Using 'area' as area column.")
        elif "area_sum" in data.columns:
            area_col = "area_sum"
            logger.info("Using 'area_sum' as area column.")
        else:
            raise KeyError("Data must contain either 'area' or 'area_sum'.")

    total_Sddc_postfire = pd.to_numeric(data["Sddc post-fire"], errors="coerce").iloc[0]
    Sddc_reduction_threshold = total_Sddc_postfire - sddc_threshold
    if Sddc_reduction_threshold <= 0:
        logger.info("Alert: Sddc threshold already met.")
        Sddc_reduction_threshold = 0

    if slope_range is not None:
        min_slope, max_slope = slope_range
        data = data.loc[(data["slope_deg"] >= min_slope) & (data["slope_deg"] <= max_slope)]
    if bs_threshold is not None:
        data = data[data["Burn severity"].isin(bs_threshold)]
    data = data.reset_index(drop=True)

    water_quality = data.filter(regex="Sddc reduction")
    soil_erosion = data.filter(regex="Sdyd reduction")
    if water_quality.empty or soil_erosion.empty:
        raise ValueError("Data is missing required 'Sddc reduction' and/or 'Sdyd reduction' columns.")

    hillslope = data[id_col].values
    sediment_yield_reduction_thresholds = (pd.to_numeric(data["Sdyd post-fire"], errors="coerce") - sdyd_threshold).clip(lower=0)
    num_sites = len(data)

    treatment_cost_vectors = {
        t: pd.to_numeric(data[area_col], errors="coerce") * c * q
        for t, c, q in zip(treatments, treatment_cost, treatment_quantity)
    }

    model_primary = LpProblem("Select_Sites", LpMinimize)
    x = {t: [LpVariable(f"x_{t}_{i}", 0, 1, cat="Binary") for i in range(num_sites)] for t in treatments}
    B = {t: LpVariable(f"B_{t}", 0, 1, cat="Binary") for t in treatments}

    model_primary += (
        sum(x[t][i] * treatment_cost_vectors[t][i] for t in treatments for i in range(num_sites))
        + sum(B[t] * fixed_cost[n] for n, t in enumerate(treatments))
    )

    for i in range(num_sites):
        model_primary += sum(x[t][i] for t in treatments) <= 1

    for t in treatments:
        for i in range(num_sites):
            model_primary += B[t] >= x[t][i]

    model_primary += (
        sum(
            x[t][i] * water_quality.iloc[:, n].values[i]
            for n, t in enumerate(treatments)
            for i in range(num_sites)
        )
        >= Sddc_reduction_threshold
    )

    for i in range(num_sites):
        if max(soil_erosion.iloc[i, :]) > sediment_yield_reduction_thresholds[i]:
            model_primary += (
                sum(x[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                >= sediment_yield_reduction_thresholds[i]
            )
        elif all(soil_erosion.iloc[i, :] <= 0):
            model_primary += sum(x[t][i] for t in treatments) == 0
        else:
            model_primary += (
                sum(x[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                == max(soil_erosion.iloc[i, :])
            )

    try:
        _ = model_primary.solve(_cbc())
        if LpStatus[model_primary.status] != "Optimal":
            logger.warning("No optimal solution found for given thresholds. Second best solution will be returned")
            model_primary_status = 0

            model_secondary = LpProblem("Select_Sites_Secondary", LpMaximize)
            x_2 = {t: [LpVariable(f"x_2_{t}_{i}", 0, 1, cat="Binary") for i in range(num_sites)] for t in treatments}
            B_2 = {t: LpVariable(f"B_2_{t}", 0, 1, cat="Binary") for t in treatments}

            model_secondary += sum(
                x_2[t][i] * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )

            for i in range(num_sites):
                # The fallback model should preserve the primary model's ability to leave a site untreated.
                model_secondary += sum(x_2[t][i] for t in treatments) <= 1

            for t in treatments:
                for i in range(num_sites):
                    model_secondary += B_2[t] >= x_2[t][i]

            for i in range(num_sites):
                if max(soil_erosion.iloc[i, :]) > sediment_yield_reduction_thresholds[i]:
                    model_secondary += (
                        sum(x_2[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                        >= sediment_yield_reduction_thresholds[i]
                    )
                elif all(soil_erosion.iloc[i, :] <= 0):
                    model_secondary += sum(x_2[t][i] for t in treatments) == 0
                else:
                    model_secondary += (
                        sum(x_2[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                        == max(soil_erosion.iloc[i, :])
                    )

            _ = model_secondary.solve(_cbc())
            if LpStatus[model_secondary.status] != "Optimal":
                logger.warning("No second best solution found for given thresholds")
                return None

            selected_sites = [[i for i in range(num_sites) if x_2[t][i].varValue == 1] for t in treatments]
            selected = [i for t in treatments for i in range(num_sites) if x_2[t][i].varValue == 1]
            selected_hillslopes = [hillslope[i] for i in selected]
            treatment_hillslopes = [hillslope[idxs].tolist() for idxs in selected_sites]

            total_cost = sum(treatment_cost_vectors[t][i] for n, t in enumerate(treatments) for i in selected_sites[n])
            total_fixed_cost = sum(B_2[t].varValue * fixed_cost[n] for n, t in enumerate(treatments))
            total_Sddc_reduction = sum(
                x_2[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x_2[t][i].varValue == 1:
                        hillslopes_sdyd.append([data[id_col][i], data[f"Sdyd post-treat {t}"][i]])
            for i in range(num_sites):
                if all(x_2[t][i].varValue == 0 for t in treatments):
                    hillslopes_sdyd.append([data[id_col][i], data["Sdyd post-fire"][i]])

        else:
            logger.info("Optimal solution found")
            model_primary_status = 1

            selected_sites = [[i for i in range(num_sites) if x[t][i].varValue == 1] for t in treatments]
            selected = [i for t in treatments for i in range(num_sites) if x[t][i].varValue == 1]
            selected_hillslopes = [hillslope[i] for i in selected]
            treatment_hillslopes = [hillslope[idxs].tolist() for idxs in selected_sites]

            total_cost = sum(treatment_cost_vectors[t][i] for n, t in enumerate(treatments) for i in selected_sites[n])
            total_fixed_cost = sum(B[t].varValue * fixed_cost[n] for n, t in enumerate(treatments))
            total_Sddc_reduction = sum(
                x[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x[t][i].varValue == 1:
                        hillslopes_sdyd.append([data[id_col][i], data[f"Sdyd post-treat {t}"][i]])
            for i in range(num_sites):
                if all(x[t][i].varValue == 0 for t in treatments):
                    hillslopes_sdyd.append([data[id_col][i], data["Sdyd post-fire"][i]])

        sdyd_df = pd.DataFrame(hillslopes_sdyd, columns=[id_col, "final_Sdyd"])
        untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold].copy()

        # Subclass of untreatable hillslopes: Sdyd increases under every treatment option.
        # Keep this as a dedicated table so plotting/reporting can style it separately.
        untreatable_sdyd_increase = pd.DataFrame(columns=[id_col, "final_Sdyd"])
        treatment_sdyd_cols = [f"Sdyd post-treat {t}" for t in treatments if f"Sdyd post-treat {t}" in data.columns]
        if treatment_sdyd_cols and not untreatable_sdyd.empty:
            tmp_df = data[[id_col, "Sdyd post-fire"] + treatment_sdyd_cols].copy()
            tmp_df["Sdyd post-fire"] = pd.to_numeric(tmp_df["Sdyd post-fire"], errors="coerce")
            for col in treatment_sdyd_cols:
                tmp_df[col] = pd.to_numeric(tmp_df[col], errors="coerce")

            strictly_increase_mask = tmp_df[treatment_sdyd_cols].gt(tmp_df["Sdyd post-fire"], axis=0).all(axis=1)
            increase_ids = set(tmp_df.loc[strictly_increase_mask, id_col].tolist())

            if increase_ids:
                untreatable_sdyd_increase = data[data[id_col].isin(increase_ids)].copy()

        missing_hillslopes = all_data[~all_data[id_col].isin(data[id_col])]
        if not missing_hillslopes.empty:
            missing_sdyd = missing_hillslopes[[id_col, "Sdyd post-fire"]].rename(columns={"Sdyd post-fire": "final_Sdyd"})
            sdyd_df = pd.concat([sdyd_df, missing_sdyd], ignore_index=True)

        sdyd_df = sdyd_df.sort_values(by=id_col).reset_index(drop=True)

    except PulpSolverError:
        logger.error("Solver failed!")
        return None

    results = (
        model_primary_status,
        treatment_cost_vectors,
        sediment_yield_reduction_thresholds,
        selected_hillslopes,
        treatment_hillslopes,
        total_Sddc_reduction,
        final_Sddc,
        hillslopes_sdyd,
        sdyd_df,
        untreatable_sdyd,
        total_cost,
        total_fixed_cost,
    )
    if return_increase_class:
        return results + (untreatable_sdyd_increase,)
    return results


class PathCESolverError(RuntimeError):
    """Raised when the optimization model cannot produce a feasible solution."""


def detect_id_col(data: pd.DataFrame) -> str:
    if "wepp_id" in data.columns:
        return "wepp_id"
    if "contrast_id" in data.columns:
        return "contrast_id"
    raise KeyError("Data must contain either 'wepp_id' or 'contrast_id'.")


def detect_area_col(data: pd.DataFrame) -> str:
    if "area" in data.columns:
        return "area"
    if "area_sum" in data.columns:
        return "area_sum"
    raise KeyError("Data must contain either 'area' or 'area_sum'.")


def clean_solver_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Input cleaning applied before the solver, mirroring the upstream report.

    The upstream QMD cleans a CSV-round-tripped frame with a frame-wide
    ``replace([inf, -inf], nan)`` / ``fillna(0)``. Parquet frames keep
    list-typed columns (``topaz_ids``), on which frame-wide replace raises,
    so both steps are restricted to numeric columns here.

    Pure cleaning — no unit conversion; see :func:`convert_area_to_acres`.
    """
    data = data.copy()
    num_cols = data.select_dtypes(include=[np.number]).columns
    data[num_cols] = data[num_cols].replace([np.inf, -np.inf], np.nan)
    for col in [c for c in data.columns if "Sddc" in c or "Sdyd" in c]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
    data = data.dropna(subset=[detect_id_col(data), detect_area_col(data)])
    num_cols = data.select_dtypes(include=[np.number]).columns
    data[num_cols] = data[num_cols].fillna(0)
    return data.reset_index(drop=True)


def convert_area_to_acres(data: pd.DataFrame, area_col: Optional[str] = None) -> pd.DataFrame:
    """Convert the frame's area column from hectares to acres (D4 / ADR-0023).

    wepppy prepared frames carry ``area``/``area_sum`` in hectares (data_prep
    scales raw m^2 by 1e-4, matching upstream). Treatment unit costs are $/acre,
    so the solver cost basis must be acres.
    """
    data = data.copy()
    if area_col is None:
        area_col = detect_area_col(data)
    data[area_col] = pd.to_numeric(data[area_col], errors="coerce") * ACRES_PER_HECTARE
    return data


def _reduction_labels(data: pd.DataFrame, family: str) -> List[str]:
    prefix = f"{family} reduction "
    return [c[len(prefix):] for c in data.columns if c.startswith(prefix)]


def _align_frame_and_treatments(
    data: pd.DataFrame,
    treatments: List[str],
    treatment_cost: List[float],
    treatment_quantity: List[float],
    fixed_cost: List[float],
) -> Tuple[pd.DataFrame, List[str], List[float], List[float], List[float]]:
    """Make the core's positional column pairing safe for any configured order/subset.

    Validates every configured label has both reduction columns, prunes
    reduction columns for unconfigured labels, verifies the Sddc and Sdyd
    families end up in the same label order, and reorders the treatment
    vectors to that column order.
    """
    sddc_labels = _reduction_labels(data, "Sddc")
    sdyd_labels = _reduction_labels(data, "Sdyd")
    missing = [t for t in treatments if t not in sddc_labels or t not in sdyd_labels]
    if missing:
        available = sorted(set(sddc_labels) & set(sdyd_labels))
        raise PathCESolverError(
            f"Prepared data has no reduction columns for treatment(s) {missing}; "
            f"available treatment labels: {available}"
        )

    configured = set(treatments)
    drop = [
        f"{family} reduction {label}"
        for family, labels in (("Sddc", sddc_labels), ("Sdyd", sdyd_labels))
        for label in labels
        if label not in configured
    ]
    working = data.drop(columns=drop) if drop else data

    kept_sddc = _reduction_labels(working, "Sddc")
    kept_sdyd = _reduction_labels(working, "Sdyd")
    if kept_sddc != kept_sdyd:
        raise PathCESolverError(
            "Sddc and Sdyd reduction columns are ordered inconsistently "
            f"({kept_sddc} vs {kept_sdyd}); cannot align treatments positionally."
        )

    order = {label: i for i, label in enumerate(kept_sddc)}
    idx = sorted(range(len(treatments)), key=lambda i: order[treatments[i]])
    return (
        working,
        [treatments[i] for i in idx],
        [treatment_cost[i] for i in idx],
        [treatment_quantity[i] for i in idx],
        [fixed_cost[i] for i in idx],
    )


def _require_finite(name: str, values: Sequence[float]) -> None:
    for v in values:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise PathCESolverError(f"{name} must be finite numbers; got {v!r}")


def prepare_solver_inputs(
    data: pd.DataFrame,
    treatments: Sequence[str],
    treatment_cost: Sequence[float],
    treatment_quantity: Sequence[float],
    fixed_cost: Sequence[float],
) -> Tuple[pd.DataFrame, List[str], List[float], List[float], List[float], str, str]:
    """Full seam pipeline: validate, clean, acre-convert, align.

    Returns ``(frame, treatments, treatment_cost, treatment_quantity,
    fixed_cost, id_col, area_col)`` ready for ``ce_select_sites_flexible``
    or ``threshold_sweep.all_thresholds``.
    """
    treatments = [str(t) for t in treatments]
    treatment_cost = list(treatment_cost)
    treatment_quantity = list(treatment_quantity)
    fixed_cost = list(fixed_cost)

    if not (len(treatments) == len(treatment_cost) == len(treatment_quantity) == len(fixed_cost)):
        raise PathCESolverError("Treatment metadata must have matching lengths.")
    if not treatments:
        raise PathCESolverError("At least one treatment is required.")
    if len(set(treatments)) != len(treatments):
        raise PathCESolverError(f"Treatment labels must be unique; got {treatments}")
    _require_finite("treatment_cost", treatment_cost)
    _require_finite("treatment_quantity", treatment_quantity)
    _require_finite("fixed_cost", fixed_cost)

    working = clean_solver_frame(data)
    if working.empty:
        raise PathCESolverError("No hillslopes available after cleaning input data.")

    id_col = detect_id_col(working)
    area_col = detect_area_col(working)
    working = convert_area_to_acres(working, area_col)

    working, treatments, treatment_cost, treatment_quantity, fixed_cost = _align_frame_and_treatments(
        working, treatments, treatment_cost, treatment_quantity, fixed_cost
    )
    return working, treatments, treatment_cost, treatment_quantity, fixed_cost, id_col, area_col


@dataclass
class SolverResult:
    """Structured view of the upstream 13-tuple returned by ce_select_sites_flexible.

    ``treatments`` holds the label order the solver actually ran with (the
    wrapper realigns configured vectors to the frame's reduction-column
    order); ``treatment_hillslopes`` is parallel to it.
    """

    treatments: List[str]
    primary_status: int
    treatment_cost_vectors: Mapping[str, pd.Series]
    sediment_yield_reduction_thresholds: pd.Series
    selected_hillslopes: List
    treatment_hillslopes: List[List]
    total_sddc_reduction: float
    final_sddc: float
    hillslopes_sdyd: List
    sdyd_df: pd.DataFrame
    untreatable_sdyd: pd.DataFrame
    total_cost: float
    total_fixed_cost: float
    untreatable_sdyd_increase: pd.DataFrame
    id_col: str
    area_col: str

    @property
    def used_secondary(self) -> bool:
        return self.primary_status == 0


def run_path_cost_effective_solver(
    data: pd.DataFrame,
    treatments: Sequence[str],
    treatment_cost: Sequence[float],
    treatment_quantity: Sequence[float],
    fixed_cost: Sequence[float],
    *,
    sdyd_threshold: float,
    sddc_threshold: float,
    slope_range: Optional[Tuple[float, float]] = None,
    bs_threshold: Optional[Sequence[str]] = None,
) -> SolverResult:
    """Run the faithful upstream solver behind the wepppy seam contracts.

    Cleans the prepared frame, converts the area column to acres, aligns
    treatment vectors to the frame's reduction-column order, then solves.
    """

    _require_finite("sdyd_threshold/sddc_threshold", [sdyd_threshold, sddc_threshold])

    working, treatments, treatment_cost, treatment_quantity, fixed_cost, id_col, area_col = (
        prepare_solver_inputs(data, treatments, treatment_cost, treatment_quantity, fixed_cost)
    )

    result = ce_select_sites_flexible(
        data=working,
        treatments=treatments,
        treatment_cost=treatment_cost,
        treatment_quantity=treatment_quantity,
        fixed_cost=fixed_cost,
        sdyd_threshold=sdyd_threshold,
        sddc_threshold=sddc_threshold,
        slope_range=slope_range,
        bs_threshold=list(bs_threshold) if bs_threshold else None,
        id_col=id_col,
        area_col=area_col,
        return_increase_class=True,
    )
    if result is None:
        raise PathCESolverError("No feasible solution found for the configured thresholds.")

    (
        primary_status,
        treatment_cost_vectors,
        sediment_yield_reduction_thresholds,
        selected_hillslopes,
        treatment_hillslopes,
        total_sddc_reduction,
        final_sddc,
        hillslopes_sdyd,
        sdyd_df,
        untreatable_sdyd,
        total_cost,
        total_fixed_cost,
        untreatable_sdyd_increase,
    ) = result

    return SolverResult(
        treatments=list(treatments),
        primary_status=int(primary_status),
        treatment_cost_vectors=treatment_cost_vectors,
        sediment_yield_reduction_thresholds=sediment_yield_reduction_thresholds,
        selected_hillslopes=list(selected_hillslopes),
        treatment_hillslopes=[list(t) for t in treatment_hillslopes],
        total_sddc_reduction=float(total_sddc_reduction),
        final_sddc=float(final_sddc),
        hillslopes_sdyd=hillslopes_sdyd,
        sdyd_df=sdyd_df,
        untreatable_sdyd=untreatable_sdyd,
        total_cost=float(total_cost),
        total_fixed_cost=float(total_fixed_cost),
        untreatable_sdyd_increase=untreatable_sdyd_increase,
        id_col=id_col,
        area_col=area_col,
    )
