"""Load and normalize RRED/PathCE treatment data for optimization.

This utility module converts raw raster/CSV summaries into structured solver
inputs. It expands treatment definitions, applies severity lookups, and returns
ready-to-score NumPy/Pandas objects consumed by ``path_cost_effective``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence

import numpy as np
import pandas as pd

from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

DEFAULT_SEVERITY_MAP = {
    "High": {105, 119, 129},
    "Moderate": {118, 120, 130},
    "Low": {106, 121, 131},
}

SEDIMENT_DISCHARGE_KEY = "Avg. Ann. sediment discharge from outlet"


@dataclass
class TreatmentOption:
    """Configuration for a single treatable scenario option."""

    label: str
    scenario: str
    quantity: float
    unit_cost: float
    fixed_cost: float = 0.0


@dataclass
class SolverInputs:
    """Normalized inputs required by the optimization solver."""

    data: pd.DataFrame
    treatments: List[str]
    treatment_costs: List[float]
    treatment_quantities: List[float]
    fixed_costs: List[float]
    scenario_lookup: Mapping[str, str]


class PathCEDataError(RuntimeError):
    """Raised when required Omni or watershed artifacts are missing or malformed."""


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise PathCEDataError(f"Required parquet file missing: {path}")
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # pragma: no cover - pandas/pyarrow exceptions are diverse
        raise PathCEDataError(f"Failed to read parquet file: {path}") from exc


def load_solver_inputs(
    wd: str | Path,
    *,
    post_fire_scenario: str,
    undisturbed_scenario: Optional[str],
    treatment_options: Sequence[TreatmentOption],
    severity_map: Optional[Mapping[str, Iterable[int]]] = None,
) -> SolverInputs:
    """
    Assemble the solver-ready dataframe and cost vectors.

    Parameters
    ----------
    wd:
        Working directory for the active WEPPcloud run.
    post_fire_scenario:
        Omni scenario key representing post-fire conditions (baseline for reductions).
    undisturbed_scenario:
        Optional Omni scenario key representing undisturbed reference conditions.
    treatment_options:
        Iterable of treatment options to evaluate.
    severity_map:
        Optional mapping of burn severity labels to Landuse codes. Falls back to
        ``DEFAULT_SEVERITY_MAP``.

    Returns
    -------
    SolverInputs
        Consolidated dataframe and per-option cost metadata.
    """

    if not treatment_options:
        raise PathCEDataError("At least one treatment option must be provided.")

    wd_path = Path(wd)
    omni_dir = wd_path / OMNI_REL_DIR

    hillslope_df = _read_parquet(omni_dir / "scenarios.hillslope_summaries.parquet")
    outlet_df = _read_parquet(omni_dir / "contrasts.out.parquet")
    watershed_df = _read_parquet(wd_path / "watershed" / "hillslopes.parquet")

    scenario_lookup = {option.label: option.scenario for option in treatment_options}

    prepared_df = _prepare_solver_dataframe(
        hillslope_df=hillslope_df,
        outlet_df=outlet_df,
        watershed_df=watershed_df,
        post_fire_scenario=post_fire_scenario,
        undisturbed_scenario=undisturbed_scenario,
        treatment_options=treatment_options,
        severity_map=severity_map or DEFAULT_SEVERITY_MAP,
    )

    treatments = [option.label for option in treatment_options]
    treatment_costs = [float(option.unit_cost) for option in treatment_options]
    treatment_quantities = [float(option.quantity) for option in treatment_options]
    fixed_costs = [float(option.fixed_cost) for option in treatment_options]

    return SolverInputs(
        data=prepared_df,
        treatments=treatments,
        treatment_costs=treatment_costs,
        treatment_quantities=treatment_quantities,
        fixed_costs=fixed_costs,
        scenario_lookup=scenario_lookup,
    )


def _prepare_solver_dataframe(
    *,
    hillslope_df: pd.DataFrame,
    outlet_df: pd.DataFrame,
    watershed_df: pd.DataFrame,
    post_fire_scenario: str,
    undisturbed_scenario: Optional[str],
    treatment_options: Sequence[TreatmentOption],
    severity_map: Mapping[str, Iterable[int]],
) -> pd.DataFrame:
    scenario_frames = _group_by_scenario(hillslope_df)
    if post_fire_scenario not in scenario_frames:
        raise PathCEDataError(
            f"Post-fire scenario '{post_fire_scenario}' not found in Omni hillslope summaries."
        )

    base_df = _normalize_keys(scenario_frames[post_fire_scenario])
    prepared = base_df[["wepp_id", "topaz_id", "landuse"]].copy()
    prepared = _attach_metrics(
        target=prepared,
        source=base_df,
        metric_suffix="post-fire",
    )

    if undisturbed_scenario:
        undisturbed_df = scenario_frames.get(undisturbed_scenario)
        if undisturbed_df is None:
            raise PathCEDataError(
                f"Undisturbed scenario '{undisturbed_scenario}' not found in Omni hillslope summaries."
            )
        prepared = _attach_metrics(
            target=prepared,
            source=_normalize_keys(undisturbed_df),
            metric_suffix="undisturbed",
        )

    for option in treatment_options:
        scenario_df = scenario_frames.get(option.scenario)
        if scenario_df is None:
            raise PathCEDataError(
                f"Treatment scenario '{option.scenario}' not found in Omni hillslope summaries."
            )
        prepared = _attach_metrics(
            target=prepared,
            source=_normalize_keys(scenario_df),
            metric_suffix=f"post-treat {option.label}",
        )
        prepared = _attach_outlet_metrics(
            target=prepared,
            outlet_df=outlet_df,
            treatment_label=option.label,
            scenario_key=option.scenario,
        )

    severity_lookup = _invert_severity_map(severity_map)
    prepared["Burn severity"] = prepared["landuse"].map(severity_lookup).fillna("Unknown")

    prepared["Landuse"] = pd.to_numeric(prepared["landuse"], errors="coerce").astype("Int64")
    prepared.drop(columns=["landuse"], inplace=True)

    prepared = prepared.merge(
        watershed_df[["wepp_id", "topaz_id", "slope_scalar", "area"]],
        how="left",
        on=["wepp_id", "topaz_id"],
    )

    base_area = (
        base_df[["wepp_id", "topaz_id", "Hillslope Area (ha)"]]
        .drop_duplicates(subset=["wepp_id", "topaz_id"])
        .rename(columns={"Hillslope Area (ha)": "area_base"})
    )
    prepared = prepared.merge(base_area, on=["wepp_id", "topaz_id"], how="left")

    if "area" in prepared:
        char_area = pd.to_numeric(prepared["area"], errors="coerce")
    else:
        char_area = pd.Series(np.nan, index=prepared.index)
        prepared["area"] = np.nan
    prepared["area"] = np.where(
        char_area.notna(),
        char_area * 0.0001,
        prepared["area_base"],
    )
    prepared.drop(columns=["area_base"], inplace=True)

    prepared["slope_scalar"] = pd.to_numeric(
        prepared.get("slope_scalar", pd.Series(np.nan, index=prepared.index)),
        errors="coerce",
    )
    prepared["slope_deg"] = np.degrees(np.arctan(prepared["slope_scalar"]))

    prepared = _compute_reductions(prepared, treatment_options)
    prepared = prepared.sort_values("wepp_id").reset_index(drop=True)
    prepared = prepared.dropna(subset=["wepp_id", "topaz_id"])

    return prepared


def _group_by_scenario(hillslope_df: pd.DataFrame) -> MutableMapping[str, pd.DataFrame]:
    grouped: MutableMapping[str, pd.DataFrame] = {}
    for scenario, group in hillslope_df.groupby("scenario"):
        grouped[str(scenario)] = group.copy()
    return grouped


def _normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.rename(
        columns={
            "WeppID": "wepp_id",
            "TopazID": "topaz_id",
            "Landuse": "landuse",
        },
        inplace=True,
    )
    return normalized


METRIC_COLUMN_MAP = {
    "Sediment Yield (t)": "Sdyd",
    "Runoff (mm)": "Runoff",
    "Lateral Flow (mm)": "Lateralflow",
    "Baseflow (mm)": "Baseflow",
    "NTU (g/L)": "NTU",
}


def _attach_metrics(target: pd.DataFrame, source: pd.DataFrame, metric_suffix: str) -> pd.DataFrame:
    rename_map = {
        original: f"{alias} {metric_suffix}"
        for original, alias in METRIC_COLUMN_MAP.items()
        if original in source
    }

    if not rename_map:
        raise PathCEDataError("Hillslope summaries missing expected metric columns.")

    subset = source[["wepp_id", "topaz_id", *rename_map.keys()]].copy().drop_duplicates(
        subset=["wepp_id", "topaz_id"]
    )
    subset.rename(columns=rename_map, inplace=True)
    return target.merge(subset, on=["wepp_id", "topaz_id"], how="left")


def _attach_outlet_metrics(
    *,
    target: pd.DataFrame,
    outlet_df: pd.DataFrame,
    treatment_label: str,
    scenario_key: str,
) -> pd.DataFrame:
    matches = outlet_df[
        (outlet_df["key"] == SEDIMENT_DISCHARGE_KEY)
        & outlet_df["contrast"].astype(str).str.endswith(scenario_key)
    ].copy()

    if matches.empty:
        raise PathCEDataError(
            f"No outlet sediment discharge contrasts found for scenario '{scenario_key}'."
        )

    subset = matches[
        ["contrast_topaz_id", "v", "control_v"]
    ].rename(
        columns={
            "contrast_topaz_id": "topaz_id",
            "v": f"Sddc post-treat {treatment_label}",
            "control_v": "Sddc post-fire",
        }
    )
    subset = subset.drop_duplicates(subset=["topaz_id"])

    merged = target.merge(subset, on="topaz_id", how="left", suffixes=("", "_dup"))
    if "Sddc post-fire_dup" in merged:
        merged.drop(columns=["Sddc post-fire_dup"], inplace=True)
    return merged


def _invert_severity_map(
    severity_map: Mapping[str, Iterable[int]]
) -> Mapping[int, str]:
    inverted: dict[int, str] = {}
    for severity, codes in severity_map.items():
        for code in codes:
            inverted[int(code)] = severity
    return inverted


def _compute_reductions(
    df: pd.DataFrame,
    treatment_options: Sequence[TreatmentOption],
) -> pd.DataFrame:
    df = df.copy()

    for option in treatment_options:
        label = option.label
        sdyd_col = f"Sdyd post-treat {label}"
        sddc_col = f"Sddc post-treat {label}"
        ntu_col = f"NTU post-treat {label}"

        df[f"Sdyd reduction {label}"] = df["Sdyd post-fire"] - df[sdyd_col]
        df[f"Sddc reduction {label}"] = df["Sddc post-fire"] - df[sddc_col]
        df[f"NTU reduction {label}"] = df["NTU post-fire"] - df[ntu_col]

    df["Burn severity"] = df["Burn severity"].fillna("Unknown")
    return df
