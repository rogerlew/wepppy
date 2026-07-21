"""PATH cost-effective data preparation.

Vendored from Jackson Nakae's PATH-cost-effective repository
(https://github.com/jackson-nakae/PATH-cost-effective, ``PATH_data_prep.py`` @ 4e3b4a6).

Faithful extraction with these seam changes only:

- ``legacy_gatecreek_format`` branch removed (with its private helpers
  ``_load_df`` / ``_first_int_from_any``); wepppy has no legacy consumers.
- ``print`` debug chatter routed through the module logger.
- ``write_outputs`` persists parquet instead of CSV (no CSV interchange in
  wepppy; parquet also preserves the list-typed ``topaz_ids`` columns).

Upstream defines ``build_aggregates`` twice — the first (core) definition is
captured as ``_build_aggregates_core`` and shadowed by the grouped-mode
wrapper. That shadowing pattern is preserved deliberately so the file diffs
cleanly against upstream when syncing.

Inputs are wepppy run artifacts consumed in place: ``omni/
scenarios.hillslope_summaries.parquet`` (hillslopes), ``omni/
contrasts.out.parquet`` (contrasts), ``watershed/hillslopes.parquet``
(hillslope_char), ``omni/scenarios.out.parquet`` (outlet_totals), and
``omni/contrast_id_definitions.psv`` (contrast_groups, grouped mode).

Sync notes and reference goldens: ``docs/work-packages/20260720_path_ce_v2/``.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

__all__ = [
    "build_aggregates",
    "prepare_ce_and_plot_data",
]

logger = logging.getLogger(__name__)


def _parse_topaz_ids(value: Any) -> list[int]:
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Series)):
        seq = list(value)
    elif pd.isna(value):
        return []
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = ast.literal_eval(s)
        except (ValueError, SyntaxError):
            seq = [token.strip() for token in s.split(",") if token.strip()]
        else:
            if isinstance(parsed, (list, tuple, set, np.ndarray, pd.Series)):
                seq = list(parsed)
            else:
                seq = [parsed]
    else:
        seq = [value]

    out = []
    for item in seq:
        if pd.isna(item):
            continue
        try:
            out.append(int(float(item)))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def _to_int_list(value: Any) -> list[int]:
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Series)):
        seq = list(value)
    elif pd.isna(value):
        return []
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = ast.literal_eval(s)
        except (ValueError, SyntaxError):
            seq = [t.strip() for t in s.replace("[", "").replace("]", "").split(",") if t.strip()]
        else:
            if isinstance(parsed, (list, tuple, set, np.ndarray, pd.Series)):
                seq = list(parsed)
            else:
                seq = [parsed]
    else:
        seq = [value]

    out = []
    for item in seq:
        if pd.isna(item):
            continue
        try:
            out.append(int(float(item)))
        except (TypeError, ValueError):
            continue
    return out


def build_aggregates(
    hillslopes,
    contrasts,
    hillslope_char,
    contrast_path=None,
    project_name="coastal-candelabrum",
    target_scenario="mulch_15_sbs_map",
    slope_range=None,
    bs_filter=None,
    outlet_totals=None,
    contrast_groups=None,
):
    """Build transformed aggregate tables for hillslopes, outlet contrasts, and hillslope characteristics."""
    target_path = f"/wc1/runs/co/{project_name}/_pups/omni/scenarios/"

    hills = hillslopes.copy()
    outlet = contrasts.copy()
    hills_char = hillslope_char.copy()

    hills_aliases = {
        "TopazID": "Topaz ID",
        "topaz_id": "Topaz ID",
        "Landuse": "Landuse Key",
        "Hillslope Area (ha)": "Landuse Area (ha)",
        "Runoff (mm)": "Runoff Depth (mm/yr)",
        "Lateral Flow (mm)": "Lateral Flow Depth (mm/yr)",
        "Baseflow (mm)": "Baseflow Depth (mm/yr)",
        "Soil Loss (kg/ha)": "Soil Loss Density (kg/ha/yr)",
        "Sediment Deposition (kg/ha)": "Sediment Deposition Density (kg/ha/yr)",
        "Sediment Yield (kg/ha)": "Sediment Yield Density (kg/ha/yr)",
    }
    for src, dst in hills_aliases.items():
        if src in hills.columns and dst not in hills.columns:
            hills[dst] = hills[src]

    if "Topaz ID" not in hills.columns:
        raise KeyError("hillslopes must contain Topaz ID information (e.g., 'Topaz ID', 'TopazID', or 'topaz_id').")

    if "Slope" not in hills.columns:
        if "slope_scalar" in hills.columns:
            hills["Slope"] = hills["slope_scalar"]
        else:
            hills["Slope"] = np.nan

    if "Landuse Area (ha)" in hills.columns:
        area_ha = pd.to_numeric(hills["Landuse Area (ha)"], errors="coerce")
        if "Soil Loss (kg/yr)" not in hills.columns and "Soil Loss Density (kg/ha/yr)" in hills.columns:
            hills["Soil Loss (kg/yr)"] = pd.to_numeric(hills["Soil Loss Density (kg/ha/yr)"], errors="coerce") * area_ha
        if "Sediment Deposition (kg/yr)" not in hills.columns and "Sediment Deposition Density (kg/ha/yr)" in hills.columns:
            hills["Sediment Deposition (kg/yr)"] = pd.to_numeric(
                hills["Sediment Deposition Density (kg/ha/yr)"], errors="coerce"
            ) * area_ha
        if "Sediment Yield (kg/yr)" not in hills.columns and "Sediment Yield Density (kg/ha/yr)" in hills.columns:
            hills["Sediment Yield (kg/yr)"] = pd.to_numeric(hills["Sediment Yield Density (kg/ha/yr)"], errors="coerce") * area_ha

    use_contrast_files = False
    matching_topaz_ids_df = pd.DataFrame(columns=["contrast_id", "topaz_ids", "scenario"])

    if contrast_groups is not None:
        use_contrast_files = True
        if isinstance(contrast_groups, pd.DataFrame):
            groups = contrast_groups.copy()
        elif isinstance(contrast_groups, str):
            cpath = contrast_groups.strip()
            if cpath.lower().endswith(".psv"):
                groups = pd.read_csv(cpath, sep="|", header=None, names=["contrast_id", "topaz_ids"])
            elif cpath.lower().endswith(".tsv"):
                groups = pd.read_csv(cpath, sep="\t")
            else:
                groups = pd.read_csv(cpath)
        else:
            raise TypeError("contrast_groups must be a DataFrame or path string.")

        if "contrast_id" not in groups.columns or "topaz_ids" not in groups.columns:
            if len(groups.columns) >= 2:
                groups = groups.rename(columns={groups.columns[0]: "contrast_id", groups.columns[1]: "topaz_ids"})
            else:
                raise KeyError("contrast_groups must include contrast_id and topaz_ids columns.")

        groups = groups[["contrast_id", "topaz_ids"]].copy()
        groups["contrast_id"] = pd.to_numeric(groups["contrast_id"], errors="coerce").astype("Int64")
        groups["topaz_ids"] = groups["topaz_ids"].apply(_parse_topaz_ids)
        groups = groups.dropna(subset=["contrast_id"])
        groups = groups[groups["topaz_ids"].map(len) > 0].reset_index(drop=True)
        matching_topaz_ids_df = groups.copy()

    elif contrast_path is not None:
        contrast_paths = sorted(Path(contrast_path).glob("*.tsv"))
        if contrast_paths:
            use_contrast_files = True
            all_contrasts = {}
            for path in contrast_paths:
                df = pd.read_csv(path, sep="\t")
                id_col = df.columns[0]
                loc_col = df.columns[1]
                df.loc[len(df)] = [np.int64(id_col), loc_col]
                df = df.rename(columns={id_col: "Topaz ID", loc_col: "Path"})
                all_contrasts[path.stem] = df

            matching_topaz_ids_dict = {}
            for filename, df in all_contrasts.items():
                mask = df["Path"].astype(str).str.startswith(target_path)
                topaz_ids = pd.to_numeric(df.loc[mask, "Topaz ID"], errors="coerce").dropna().astype(int).tolist()
                contrast_num = int(filename[-4:])
                matching_topaz_ids_dict[contrast_num] = sorted(set(topaz_ids))

            matching_topaz_ids_df = pd.DataFrame(
                list(matching_topaz_ids_dict.items()),
                columns=["contrast_id", "topaz_ids"],
            )

    if "contrast_scenario" not in outlet.columns and "contrast" in outlet.columns:
        outlet["contrast_scenario"] = outlet["contrast"].astype(str).str.split("to__").str[-1]

    if "control_v" not in outlet.columns and "control" in outlet.columns:
        outlet = outlet.rename(columns={"control": "control_v"})
    elif "control_v" not in outlet.columns:
        if {"v", "control-contrast_v"}.issubset(outlet.columns):
            outlet["control_v"] = pd.to_numeric(outlet["v"], errors="coerce") + pd.to_numeric(
                outlet["control-contrast_v"], errors="coerce"
            )
        else:
            raise KeyError(
                "contrasts is missing 'control_v' and cannot derive it because required fallback columns are unavailable."
            )

    outlet["control_v"] = pd.to_numeric(outlet["control_v"], errors="coerce")
    outlet["v"] = pd.to_numeric(outlet["v"], errors="coerce")
    outlet["control-contrast_v"] = outlet["control_v"] - outlet["v"]

    outlet_totals_df = outlet_totals
    if outlet_totals_df is not None:
        if not isinstance(outlet_totals_df, pd.DataFrame):
            outlet_totals_df = pd.DataFrame(outlet_totals_df)
        totals = outlet_totals_df.copy()
        if "scenario" in totals.columns:
            totals = totals.loc[totals["scenario"].eq("sbs_map")].copy()
        if {"key", "value"}.issubset(totals.columns):
            totals["value"] = pd.to_numeric(totals["value"], errors="coerce")
            totals_map = totals.dropna(subset=["key"]).drop_duplicates(subset=["key"]).set_index("key")["value"]
            mapped_control_v = outlet["key"].map(totals_map)
            outlet["control_v"] = mapped_control_v.combine_first(pd.to_numeric(outlet["control_v"], errors="coerce"))
            outlet["control-contrast_v"] = outlet["control_v"] - outlet["v"]

    if use_contrast_files:
        contrast_to_scenario = outlet.set_index("contrast_id")["contrast_scenario"].to_dict()
        matching_topaz_ids_df["scenario"] = matching_topaz_ids_df["contrast_id"].map(contrast_to_scenario)
    else:
        if "contrast_id" not in hills.columns:
            if {"contrast_id", "contrast_topaz_id"}.issubset(outlet.columns):
                topaz_to_contrast = (
                    outlet[["contrast_topaz_id", "contrast_id"]]
                    .dropna()
                    .drop_duplicates(subset=["contrast_topaz_id"])
                    .set_index("contrast_topaz_id")["contrast_id"]
                    .to_dict()
                )
                hills["contrast_id"] = pd.to_numeric(hills["Topaz ID"], errors="coerce").map(topaz_to_contrast)
            else:
                hills["contrast_id"] = pd.to_numeric(hills["Topaz ID"], errors="coerce").rank(method="dense").astype("Int64")

        hills["contrast_id"] = pd.to_numeric(hills["contrast_id"], errors="coerce").astype("Int64")

        matching_topaz_ids_df = (
            hills.dropna(subset=["contrast_id", "scenario"])
            .assign(
                contrast_id=lambda d: pd.to_numeric(d["contrast_id"], errors="coerce").astype("Int64"),
                _topaz=lambda d: pd.to_numeric(d["Topaz ID"], errors="coerce").astype("Int64"),
            )
            .dropna(subset=["_topaz"])
            .groupby(["contrast_id", "scenario"], as_index=False)["_topaz"]
            .agg(lambda values: sorted(pd.Series(values).dropna().astype(int).unique().tolist()))
            .rename(columns={"_topaz": "topaz_ids"})
        )

    if use_contrast_files:
        hills["contrast_id"] = pd.Series(index=hills.index, dtype="object")

        rows = []
        for _, mapping_row in matching_topaz_ids_df.iterrows():
            for topaz_id in mapping_row["topaz_ids"]:
                rows.append(
                    {
                        "scenario": mapping_row["scenario"],
                        "Topaz ID": topaz_id,
                        "contrast_id": int(mapping_row["contrast_id"]),
                    }
                )

        scenario_topaz_to_contrast = pd.DataFrame(rows).drop_duplicates(subset=["scenario", "Topaz ID"])

        hills = hills.merge(
            scenario_topaz_to_contrast,
            on=["scenario", "Topaz ID"],
            how="left",
            suffixes=("", "_mapped"),
        )

        non_sbs_mask = hills["scenario"] != "sbs_map"
        mapped_non_sbs = pd.to_numeric(hills.loc[non_sbs_mask, "contrast_id_mapped"], errors="coerce").astype("Int64")
        hills.loc[non_sbs_mask, "contrast_id"] = mapped_non_sbs.astype(object)

        matching_topaz_ids_df = matching_topaz_ids_df.copy()
        matching_topaz_ids_df["topaz_signature"] = matching_topaz_ids_df["topaz_ids"].apply(lambda values: tuple(sorted(values)))

        signature_lengths = matching_topaz_ids_df["topaz_signature"].apply(len)
        no_grouping_case = bool((signature_lengths <= 1).all())

        if no_grouping_case:
            base_groups = matching_topaz_ids_df[["contrast_id", "topaz_signature", "scenario"]].copy()
            base_groups["is_target_scenario"] = base_groups["scenario"].eq(target_scenario)
            signature_to_contrast = (
                base_groups
                .sort_values(["topaz_signature", "is_target_scenario", "contrast_id"], ascending=[True, False, True])
                .drop_duplicates(subset=["topaz_signature"], keep="first")
            )

            topaz_to_contrast_sbs = {}
            for _, row in signature_to_contrast.iterrows():
                if len(row["topaz_signature"]) == 1:
                    topaz_to_contrast_sbs[int(row["topaz_signature"][0])] = int(row["contrast_id"])

            sbs_mask = hills["scenario"] == "sbs_map"
            mapped_sbs = pd.to_numeric(hills.loc[sbs_mask, "Topaz ID"].map(topaz_to_contrast_sbs), errors="coerce").astype("Int64")
            hills.loc[sbs_mask, "contrast_id"] = mapped_sbs.astype(object)
        else:
            signature_order = (
                matching_topaz_ids_df.groupby("topaz_signature", as_index=False)["contrast_id"]
                .min()
                .sort_values("contrast_id")
                .reset_index(drop=True)
            )
            signature_order["base_label"] = [f"base_{i + 1}" for i in range(len(signature_order))]

            topaz_to_base = {}
            for _, row in signature_order.iterrows():
                for topaz_id in row["topaz_signature"]:
                    topaz_to_base.setdefault(topaz_id, row["base_label"])

            sbs_mask = hills["scenario"] == "sbs_map"
            hills.loc[sbs_mask, "contrast_id"] = hills.loc[sbs_mask, "Topaz ID"].map(topaz_to_base)

        hills = hills.drop(columns=["contrast_id_mapped"])
    else:
        hills["contrast_id"] = pd.to_numeric(hills["contrast_id"], errors="coerce").astype("Int64")

    hills["Slope"] = pd.to_numeric(hills["Slope"], errors="coerce")
    hills["Landuse Key"] = pd.to_numeric(hills["Landuse Key"], errors="coerce")
    hills["slope_deg"] = np.degrees(np.arctan(hills["Slope"]))

    high_severity = [105, 119, 129, 105015, 105030, 105060, 119015, 119030, 119060]
    mod_severity = [118, 120, 130, 118015, 118030, 118060, 120060, 120030, 120015]
    low_severity = [106, 121, 131, 106015, 106030, 106060, 121060, 121030, 121015]

    hills["Burn severity"] = "NaN"
    hills.loc[hills["Landuse Key"].isin(high_severity), "Burn severity"] = "High"
    hills.loc[hills["Landuse Key"].isin(mod_severity), "Burn severity"] = "Moderate"
    hills.loc[hills["Landuse Key"].isin(low_severity), "Burn severity"] = "Low"

    hills["Landuse Area (ac)"] = pd.to_numeric(hills["Landuse Area (ha)"], errors="coerce") * 2.47105
    hills["Sediment Yield (t/ac)"] = pd.to_numeric(hills["Sediment Yield (t)"], errors="coerce") / hills["Landuse Area (ac)"]

    sum_column_candidates = [
        "Landuse Area (ha)",
        "Landuse Area (ac)",
        "Runoff Depth (mm/yr)",
        "Lateral Flow Depth (mm/yr)",
        "Baseflow Depth (mm/yr)",
        "Soil Loss (kg/yr)",
        "Soil Loss Density (kg/ha/yr)",
        "Sediment Deposition (kg/yr)",
        "Sediment Deposition Density (kg/ha/yr)",
        "Sediment Yield (kg/yr)",
        "Sediment Yield Density (kg/ha/yr)",
        "Runoff (m^3)",
        "Lateral Flow (m^3)",
        "Baseflow (m^3)",
        "Soil Loss (t)",
        "Sediment Deposition (t)",
        "Sediment Yield (t)",
    ]
    sum_columns = [col for col in sum_column_candidates if col in hills.columns]

    def most_common_landuse_key(series):
        numeric_vals = pd.to_numeric(series, errors="coerce").dropna()
        if numeric_vals.empty:
            return np.nan
        counts = numeric_vals.value_counts()
        max_count = counts.max()
        return counts[counts == max_count].index.max()

    agg_dict = {col: "sum" for col in sum_columns}
    agg_dict["_ntu_weighted_numer"] = "sum"
    agg_dict["Slope"] = "mean"
    agg_dict["Landuse Key"] = most_common_landuse_key

    if slope_range is not None or bs_filter is not None:
        sbs_rows = hills[hills["scenario"] == "sbs_map"].copy()
        sbs_rows["Topaz ID"] = pd.to_numeric(sbs_rows["Topaz ID"], errors="coerce").astype("Int64")

        eligible_sbs_mask = pd.Series(True, index=sbs_rows.index)
        if slope_range is not None:
            min_slope, max_slope = slope_range
            eligible_sbs_mask = eligible_sbs_mask & sbs_rows["slope_deg"].between(min_slope, max_slope)
        if bs_filter is not None:
            allowed_bs = [bs_filter] if isinstance(bs_filter, str) else list(bs_filter)
            eligible_sbs_mask = eligible_sbs_mask & sbs_rows["Burn severity"].isin(allowed_bs)

        eligible_topaz_ids = set(sbs_rows.loc[eligible_sbs_mask, "Topaz ID"].dropna().astype(int).tolist())

        metric_cols_to_sub = [c for c in (sum_columns + ["NTU (g/L)"]) if c in hills.columns]
        sbs_lookup = sbs_rows.drop_duplicates(subset=["Topaz ID"]).set_index("Topaz ID")[metric_cols_to_sub]

        treatment_scenarios = ["mulch_15_sbs_map", "mulch_30_sbs_map", "mulch_60_sbs_map"]
        hills["_topaz_numeric"] = pd.to_numeric(hills["Topaz ID"], errors="coerce").astype("Int64")
        inelig_mask = hills["scenario"].isin(treatment_scenarios) & ~hills["_topaz_numeric"].isin(eligible_topaz_ids)

        if inelig_mask.any():
            inelig_idx = hills[inelig_mask].index
            topaz_for_inelig = hills.loc[inelig_idx, "_topaz_numeric"]
            for col in metric_cols_to_sub:
                if col in sbs_lookup.columns:
                    hills.loc[inelig_idx, col] = topaz_for_inelig.map(sbs_lookup[col]).values

        hills = hills.drop(columns=["_topaz_numeric"])

    hills["NTU (g/L)"] = pd.to_numeric(hills["NTU (g/L)"], errors="coerce")
    hills["Runoff (m^3)"] = pd.to_numeric(hills["Runoff (m^3)"], errors="coerce")
    hills["_ntu_weighted_numer"] = hills["NTU (g/L)"] * hills["Runoff (m^3)"]

    # FIX: Handle undisturbed scenario when using contrast_files
    # When use_contrast_files is True, undisturbed rows don't get contrast_ids assigned because
    # they're not part of the contrast groupings. This causes them to be dropped below.
    # Assign undisturbed rows the same contrast_ids as their sbs_map counterparts.
    if use_contrast_files and "scenario" in hills.columns:
        undisturbed_mask = hills["scenario"] == "undisturbed"
        if undisturbed_mask.any():
            logger.debug("Found %d undisturbed rows", undisturbed_mask.sum())
            # Build a mapping from Topaz ID to contrast_id using sbs_map rows
            sbs_rows = hills[hills["scenario"] == "sbs_map"].copy()
            sbs_rows["Topaz ID"] = pd.to_numeric(sbs_rows["Topaz ID"], errors="coerce").astype("Int64")
            sbs_rows["contrast_id"] = pd.to_numeric(sbs_rows["contrast_id"], errors="coerce").astype("Int64")

            # Create topaz_id to contrast_id mapping from sbs_map
            topaz_to_contrast_map = (
                sbs_rows[["Topaz ID", "contrast_id"]]
                .dropna(subset=["Topaz ID", "contrast_id"])
                .drop_duplicates(subset=["Topaz ID"])
                .set_index("Topaz ID")["contrast_id"]
                .to_dict()
            )

            logger.debug("Created mapping with %d Topaz IDs", len(topaz_to_contrast_map))
            # Apply mapping to undisturbed rows
            undisturbed_topaz = pd.to_numeric(hills.loc[undisturbed_mask, "Topaz ID"], errors="coerce").astype("Int64")
            mapped_contrast_ids = undisturbed_topaz.map(topaz_to_contrast_map)
            logger.debug("Mapped %d undisturbed rows to contrast_ids", mapped_contrast_ids.notna().sum())
            hills.loc[undisturbed_mask, "contrast_id"] = mapped_contrast_ids

    hills_agg = hills.dropna(subset=["contrast_id"]).groupby(["contrast_id", "scenario"], as_index=False).agg(agg_dict)
    hills_agg["Sediment Yield (t/ac)"] = hills_agg["Sediment Yield (t)"] / hills_agg["Landuse Area (ac)"]
    hills_agg["NTU (g/L)"] = np.where(
        pd.to_numeric(hills_agg["Runoff (m^3)"], errors="coerce") > 0,
        pd.to_numeric(hills_agg["_ntu_weighted_numer"], errors="coerce") / pd.to_numeric(hills_agg["Runoff (m^3)"], errors="coerce"),
        np.nan,
    )
    hills_agg = hills_agg.drop(columns=["_ntu_weighted_numer"])
    hills_agg["contrast_id"] = hills_agg["contrast_id"].astype(str)
    hills_agg["Landuse"] = pd.to_numeric(hills_agg["Landuse Key"], errors="coerce").astype("Int64")
    hills_agg["Burn severity"] = "NaN"
    hills_agg.loc[hills_agg["Landuse"].isin(high_severity), "Burn severity"] = "High"
    hills_agg.loc[hills_agg["Landuse"].isin(mod_severity), "Burn severity"] = "Moderate"
    hills_agg.loc[hills_agg["Landuse"].isin(low_severity), "Burn severity"] = "Low"
    hills_agg["slope_deg"] = np.degrees(np.arctan(pd.to_numeric(hills_agg["Slope"], errors="coerce")))

    base_groups = matching_topaz_ids_df[["contrast_id", "topaz_ids", "scenario"]].copy()
    base_groups["topaz_signature"] = base_groups["topaz_ids"].apply(lambda values: tuple(sorted(values)))
    base_groups["is_target_scenario"] = base_groups["scenario"].eq(target_scenario)

    signature_to_contrast = (
        base_groups.sort_values(["topaz_signature", "is_target_scenario", "contrast_id"], ascending=[True, False, True])
        .drop_duplicates(subset=["topaz_signature"], keep="first")[["topaz_signature", "contrast_id"]]
    )

    topaz_to_contrast = {}
    for _, row in signature_to_contrast.iterrows():
        for topaz_id in row["topaz_signature"]:
            topaz_to_contrast.setdefault(int(topaz_id), int(row["contrast_id"]))

    char_aliases = {"TopazID": "topaz_id"}
    for src, dst in char_aliases.items():
        if src in hills_char.columns and dst not in hills_char.columns:
            hills_char[dst] = hills_char[src]

    if "contrast_id" in hills_char.columns:
        hills_char["contrast_id"] = pd.to_numeric(hills_char["contrast_id"], errors="coerce").astype("Int64")
    else:
        if "topaz_id" not in hills_char.columns and "Topaz ID" not in hills_char.columns:
            raise KeyError("hillslope_char must contain 'contrast_id' or 'topaz_id'/'Topaz ID'.")
        topaz_char_col = "topaz_id" if "topaz_id" in hills_char.columns else "Topaz ID"
        hills_char["contrast_id"] = (
            pd.to_numeric(hills_char[topaz_char_col], errors="coerce").astype("Int64").map(topaz_to_contrast).astype("Int64")
        )

    def pick_col(candidates: Iterable[str], df: pd.DataFrame):
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        return None

    topaz_col = "topaz_id" if "topaz_id" in hills_char.columns else "Topaz ID"
    area_col = pick_col(["area", "Area", "area_ha", "Area (ha)", "Landuse Area (ha)"], hills_char)
    length_col = pick_col(["length", "Length", "length_m", "Length (m)"], hills_char)
    width_col = pick_col(["width", "Width", "width_m", "Width (m)"], hills_char)
    slope_scalar_col = pick_col(["slope_scalar", "Slope Scalar", "slope", "Slope"], hills_char)
    direction_col = pick_col(["direction", "Direction"], hills_char)
    aspect_col = pick_col(["aspect", "Aspect"], hills_char)
    elevation_col = pick_col(["elevation", "Elevation"], hills_char)

    required_cols = ["contrast_id", topaz_col, "centroid_lon", "centroid_lat"]
    optional_cols = [c for c in [area_col, length_col, width_col, slope_scalar_col, direction_col, aspect_col, elevation_col] if c is not None]

    working_all = hills_char[required_cols + optional_cols].copy()
    for col in optional_cols + ["centroid_lon", "centroid_lat"]:
        working_all[col] = pd.to_numeric(working_all[col], errors="coerce")
    working_all[topaz_col] = pd.to_numeric(working_all[topaz_col], errors="coerce").astype("Int64")

    hills_filter_source = hills[hills["scenario"] == "sbs_map"].copy()
    if hills_filter_source.empty:
        hills_filter_source = hills.copy()

    eligible_mask = pd.Series(True, index=hills_filter_source.index)
    if slope_range is not None:
        min_slope, max_slope = slope_range
        eligible_mask = eligible_mask & hills_filter_source["slope_deg"].between(min_slope, max_slope)
    if bs_filter is not None:
        allowed_bs = [bs_filter] if isinstance(bs_filter, str) else list(bs_filter)
        eligible_mask = eligible_mask & hills_filter_source["Burn severity"].isin(allowed_bs)

    eligible_topaz_ids = set(
        pd.to_numeric(hills_filter_source.loc[eligible_mask, "Topaz ID"], errors="coerce").dropna().astype(int).tolist()
    )

    working_eligible = working_all.copy() if (slope_range is None and bs_filter is None) else working_all[working_all[topaz_col].isin(eligible_topaz_ids)].copy()

    def aggregate_char(df):
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "contrast_id",
                    "topaz_ids",
                    "area_sum",
                    "length_sum",
                    "width_sum",
                    "slope_scalar_mean",
                    "direction_mean",
                    "aspect_mean",
                    "elevation_mean",
                    "area_weight_sum",
                    "lon_weight_sum",
                    "lat_weight_sum",
                ]
            )

        if area_col is None:
            df["_weight_area"] = 1.0
        else:
            df["_weight_area"] = pd.to_numeric(df[area_col], errors="coerce").fillna(0)

        df["_lon_weighted"] = df["centroid_lon"] * df["_weight_area"]
        df["_lat_weighted"] = df["centroid_lat"] * df["_weight_area"]

        return df.groupby("contrast_id", as_index=False).agg(
            topaz_ids=(topaz_col, lambda values: sorted(pd.Series(values).dropna().astype(int).tolist())),
            area_sum=(area_col, "sum") if area_col is not None else ("_weight_area", "sum"),
            length_sum=(length_col, "sum") if length_col is not None else ("_weight_area", "sum"),
            width_sum=(width_col, "sum") if width_col is not None else ("_weight_area", "sum"),
            slope_scalar_mean=(slope_scalar_col, "mean") if slope_scalar_col is not None else ("_weight_area", "mean"),
            direction_mean=(direction_col, "mean") if direction_col is not None else ("_weight_area", "mean"),
            aspect_mean=(aspect_col, "mean") if aspect_col is not None else ("_weight_area", "mean"),
            elevation_mean=(elevation_col, "mean") if elevation_col is not None else ("_weight_area", "mean"),
            area_weight_sum=("_weight_area", "sum"),
            lon_weight_sum=("_lon_weighted", "sum"),
            lat_weight_sum=("_lat_weighted", "sum"),
        )

    all_char = aggregate_char(working_all.copy())[["contrast_id", "topaz_ids"]].rename(columns={"topaz_ids": "topaz_ids_all"})
    eligible_char = aggregate_char(working_eligible.copy())

    hills_char_grouped = all_char.merge(eligible_char, on="contrast_id", how="left")
    hills_char_grouped["topaz_ids"] = hills_char_grouped["topaz_ids"].apply(lambda v: v if isinstance(v, list) else [])

    fill_zero_cols = [
        "area_sum",
        "length_sum",
        "width_sum",
        "slope_scalar_mean",
        "direction_mean",
        "aspect_mean",
        "elevation_mean",
        "area_weight_sum",
        "lon_weight_sum",
        "lat_weight_sum",
    ]
    for col in fill_zero_cols:
        hills_char_grouped[col] = pd.to_numeric(hills_char_grouped[col], errors="coerce").fillna(0)

    hills_char_grouped["centroid_lon_area_weighted"] = np.where(
        hills_char_grouped["area_weight_sum"] > 0,
        hills_char_grouped["lon_weight_sum"] / hills_char_grouped["area_weight_sum"],
        0,
    )
    hills_char_grouped["centroid_lat_area_weighted"] = np.where(
        hills_char_grouped["area_weight_sum"] > 0,
        hills_char_grouped["lat_weight_sum"] / hills_char_grouped["area_weight_sum"],
        0,
    )

    hills_char_grouped = hills_char_grouped[
        [
            "contrast_id",
            "topaz_ids",
            "topaz_ids_all",
            "area_sum",
            "length_sum",
            "width_sum",
            "slope_scalar_mean",
            "direction_mean",
            "aspect_mean",
            "elevation_mean",
            "centroid_lon_area_weighted",
            "centroid_lat_area_weighted",
        ]
    ].sort_values("contrast_id").reset_index(drop=True)

    hills_char_grouped["contrast_id"] = pd.to_numeric(hills_char_grouped["contrast_id"], errors="coerce").astype("Int64")
    hills_char_grouped["area_sum"] = pd.to_numeric(hills_char_grouped["area_sum"], errors="coerce") * 0.0001
    hills_char_grouped["topaz_ids"] = hills_char_grouped["topaz_ids"].astype(str)
    hills_char_grouped["topaz_ids_all"] = hills_char_grouped["topaz_ids_all"].astype(str)

    return hills_agg, outlet, hills_char_grouped


def _prepare_ce_and_plot_data_impl(
    hillslopes,
    contrasts,
    hillslope_char,
    contrast_path=None,
    contrast_groups=None,
    project_name="coastal-candelabrum",
    target_scenario="mulch_15_sbs_map",
    slope_range=None,
    bs_filter=None,
    outlet_totals=None,
    write_outputs=True,
    output_dir=".",
    output_prefix="catchment",
):
    hillslope_data_agg, outlet_data_final, hillslope_char_data_agg = build_aggregates(
        hillslopes,
        contrasts,
        hillslope_char,
        contrast_path=contrast_path,
        project_name=project_name,
        target_scenario=target_scenario,
        slope_range=slope_range,
        bs_filter=bs_filter,
        outlet_totals=outlet_totals,
        contrast_groups=contrast_groups,
    )

    def _subset(df, scenario_name, cols):
        return df.loc[df["scenario"].eq(scenario_name), ["contrast_id"] + cols].reset_index(drop=True).copy()

    def _align_rows(df, target_len, label):
        out = df.reset_index(drop=True).copy()
        if len(out) < target_len:
            raise ValueError(f"{label} has fewer rows than reference scenario ({len(out)} < {target_len}).")
        return out.iloc[:target_len].reset_index(drop=True)

    def _scenario_rate_label(scenario_name):
        match = re.match(r"^mulch_(\d+)_sbs_map$", str(scenario_name))
        if not match:
            return scenario_name
        amount = int(match.group(1))
        rate = amount / 30.0
        return f"{rate:g} tons/acre"

    hills_agg = hillslope_data_agg.copy()
    out_agg = outlet_data_final.copy()
    char_agg = hillslope_char_data_agg.copy()

    if hills_agg.empty or out_agg.empty or char_agg.empty:
        raise ValueError("One or more aggregated inputs are empty; cannot build final_data.")

    cols = [
        "Landuse Key",
        "Landuse Area (ac)",
        "Sediment Yield (t/ac)",
        "Runoff (m^3)",
        "Lateral Flow (m^3)",
        "Baseflow (m^3)",
        "NTU (g/L)",
    ]

    hills_scenarios = set(hills_agg["scenario"].dropna().astype(str).tolist())

    out_treatments = []
    if "contrast_scenario" in out_agg.columns:
        out_treatments = [
            s
            for s in out_agg["contrast_scenario"].dropna().astype(str).unique().tolist()
            if s.startswith("mulch_") and s.endswith("_sbs_map")
        ]

    treatment_scenarios = sorted(
        [s for s in out_treatments if s in hills_scenarios],
        key=lambda s: int(re.match(r"^mulch_(\d+)_sbs_map$", s).group(1)) if re.match(r"^mulch_(\d+)_sbs_map$", s) else 10**9,
    )

    if not treatment_scenarios:
        treatment_scenarios = sorted(
            [s for s in hills_scenarios if s.startswith("mulch_") and s.endswith("_sbs_map")],
            key=lambda s: int(re.match(r"^mulch_(\d+)_sbs_map$", s).group(1)) if re.match(r"^mulch_(\d+)_sbs_map$", s) else 10**9,
        )

    if not treatment_scenarios:
        raise ValueError("No treatment scenarios found in aggregated hillslope data.")

    sbs = _subset(hills_agg, "sbs_map", cols)
    if sbs.empty:
        raise ValueError("Required scenario missing in hillslope_data_agg: sbs_map.")

    treatment_frames = {}
    for scen in treatment_scenarios:
        frame = _subset(hills_agg, scen, cols)
        if not frame.empty:
            treatment_frames[scen] = frame

    if not treatment_frames:
        raise ValueError("No non-empty treatment scenario data found after filtering.")

    reference_scenario = next(iter(treatment_frames.keys()))
    reference = treatment_frames[reference_scenario].reset_index(drop=True)

    for scen in list(treatment_frames.keys()):
        treatment_frames[scen] = _align_rows(treatment_frames[scen], len(reference), scen)

    sbs = _align_rows(sbs, len(reference), "sbs_map")
    und = _subset(hills_agg, "undisturbed", cols)
    if und.empty:
        und = pd.DataFrame(index=range(len(reference)), columns=reference.columns)
    else:
        und = _align_rows(und, len(reference), "undisturbed")

    contrast_ids = pd.to_numeric(reference["contrast_id"], errors="coerce").astype("Int64")

    final_data = pd.DataFrame(
        {
            "contrast_id": contrast_ids,
            "Landuse": sbs["Landuse Key"],
            "Landuse Area (ac)": sbs["Landuse Area (ac)"],
        }
    )

    for scen, frame in treatment_frames.items():
        label = _scenario_rate_label(scen)
        final_data[f"Sdyd post-treat {label}"] = frame["Sediment Yield (t/ac)"]
        final_data[f"Runoff post-treat {label}"] = frame["Runoff (m^3)"]
        final_data[f"Lateralflow post-treat {label}"] = frame["Lateral Flow (m^3)"]
        final_data[f"Baseflow post-treat {label}"] = frame["Baseflow (m^3)"]
        final_data[f"NTU post-treat {label}"] = frame["NTU (g/L)"]

        final_data[f"Sdyd reduction {label}"] = sbs["Sediment Yield (t/ac)"] - frame["Sediment Yield (t/ac)"]
        final_data[f"Runoff reduction {label}"] = sbs["Runoff (m^3)"] - frame["Runoff (m^3)"]
        final_data[f"Lateralflow reduction {label}"] = sbs["Lateral Flow (m^3)"] - frame["Lateral Flow (m^3)"]
        final_data[f"Baseflow reduction {label}"] = sbs["Baseflow (m^3)"] - frame["Baseflow (m^3)"]
        final_data[f"NTU reduction {label}"] = sbs["NTU (g/L)"] - frame["NTU (g/L)"]

    final_data["Sdyd post-fire"] = sbs["Sediment Yield (t/ac)"]
    final_data["Sdyd undisturbed"] = und["Sediment Yield (t/ac)"]
    final_data["Runoff post-fire"] = sbs["Runoff (m^3)"]
    final_data["Runoff undisturbed"] = und["Runoff (m^3)"]
    final_data["Lateralflow post-fire"] = sbs["Lateral Flow (m^3)"]
    final_data["Lateralflow undisturbed"] = und["Lateral Flow (m^3)"]
    final_data["Baseflow post-fire"] = sbs["Baseflow (m^3)"]
    final_data["Baseflow undisturbed"] = und["Baseflow (m^3)"]
    final_data["NTU post-fire"] = sbs["NTU (g/L)"]
    final_data["NTU undisturbed"] = und["NTU (g/L)"]

    out_agg["contrast_id"] = pd.to_numeric(out_agg["contrast_id"], errors="coerce").astype("Int64")
    out_key = "Avg. Ann. sediment discharge from outlet"
    outlet_subset = out_agg.loc[out_agg["key"].eq(out_key)].copy()

    control_series = None
    for scen, frame in treatment_frames.items():
        out_scen = outlet_subset.loc[
            outlet_subset["contrast_scenario"].eq(scen),
            ["contrast_id", "v", "control_v"],
        ].dropna(subset=["contrast_id"]).drop_duplicates(subset=["contrast_id"])

        out_map_v = out_scen.set_index("contrast_id")["v"] if not out_scen.empty else pd.Series(dtype=float)
        out_map_ctl = out_scen.set_index("contrast_id")["control_v"] if not out_scen.empty else pd.Series(dtype=float)

        scen_ids = pd.to_numeric(frame["contrast_id"], errors="coerce").astype("Int64").reset_index(drop=True)

        label = _scenario_rate_label(scen)
        final_data[f"Sddc post-treat {label}"] = scen_ids.map(out_map_v).values

        if control_series is None:
            control_series = scen_ids.map(out_map_ctl)

    final_data["Sddc post-fire"] = control_series if control_series is not None else np.nan

    for scen in treatment_frames.keys():
        label = _scenario_rate_label(scen)
        post_col = f"Sddc post-treat {label}"
        if post_col in final_data.columns:
            final_data[f"Sddc reduction {label}"] = final_data["Sddc post-fire"] - final_data[post_col]

    for col in ["topaz_ids", "topaz_ids_all"]:
        if col in char_agg.columns:
            char_agg[col] = char_agg[col].apply(_to_int_list)

    char_agg["contrast_id"] = pd.to_numeric(char_agg["contrast_id"], errors="coerce").astype("Int64")
    final_data = final_data.merge(char_agg, on="contrast_id", how="left")

    if "slope_deg" not in final_data.columns:
        final_data["slope_deg"] = np.degrees(np.arctan(pd.to_numeric(final_data.get("slope_scalar_mean"), errors="coerce")))

    final_data["Landuse"] = pd.to_numeric(final_data["Landuse"], errors="coerce").astype("Int64")
    high_severity = [105, 119, 129, 105015, 105030, 105060, 119015, 119030, 119060]
    mod_severity = [118, 120, 130, 118015, 118030, 118060, 120060, 120030, 120015]
    low_severity = [106, 121, 131, 106015, 106030, 106060, 121060, 121030, 121015]

    final_data["Burn severity"] = "NaN"
    final_data.loc[final_data["Landuse"].isin(high_severity), "Burn severity"] = "High"
    final_data.loc[final_data["Landuse"].isin(mod_severity), "Burn severity"] = "Moderate"
    final_data.loc[final_data["Landuse"].isin(low_severity), "Burn severity"] = "Low"

    if write_outputs:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        final_data.to_parquet(output_dir / f"{output_prefix}_final_data.parquet", index=False)
        hillslope_data_agg.to_parquet(output_dir / f"{output_prefix}_hillslope_agg.parquet", index=False)
        outlet_data_final.to_parquet(output_dir / f"{output_prefix}_outlet_agg.parquet", index=False)
        hillslope_char_data_agg.to_parquet(output_dir / f"{output_prefix}_char_agg.parquet", index=False)

    return hillslope_data_agg, outlet_data_final, hillslope_char_data_agg, final_data


def prepare_ce_and_plot_data(
    hillslopes,
    contrasts,
    hillslope_char,
    contrast_path=None,
    contrast_groups=None,
    project_name="coastal-candelabrum",
    target_scenario="mulch_15_sbs_map",
    slope_range=None,
    bs_filter=None,
    outlet_totals=None,
    write_outputs=True,
    output_dir=".",
    output_prefix="catchment",
):
    """Public entry point for CE/plot preparation."""
    return _prepare_ce_and_plot_data_impl(
        hillslopes=hillslopes,
        contrasts=contrasts,
        hillslope_char=hillslope_char,
        contrast_path=contrast_path,
        contrast_groups=contrast_groups,
        project_name=project_name,
        target_scenario=target_scenario,
        slope_range=slope_range,
        bs_filter=bs_filter,
        outlet_totals=outlet_totals,
        write_outputs=write_outputs,
        output_dir=output_dir,
        output_prefix=output_prefix,
    )


_build_aggregates_core = build_aggregates


def _load_contrast_groups_df(contrast_groups):
    if isinstance(contrast_groups, pd.DataFrame):
        groups = contrast_groups.copy()
    elif isinstance(contrast_groups, str):
        path = contrast_groups.strip()
        if path.lower().endswith(".psv"):
            groups = pd.read_csv(path, sep="|", header=None, names=["contrast_id", "topaz_ids"])
        elif path.lower().endswith(".tsv"):
            groups = pd.read_csv(path, sep="\t")
        else:
            groups = pd.read_csv(path)
    else:
        raise TypeError("contrast_groups must be a DataFrame or file path string.")

    if "contrast_id" not in groups.columns or "topaz_ids" not in groups.columns:
        if len(groups.columns) >= 2:
            groups = groups.rename(columns={groups.columns[0]: "contrast_id", groups.columns[1]: "topaz_ids"})
        else:
            raise KeyError("contrast_groups must include contrast_id and topaz_ids columns.")

    groups = groups[["contrast_id", "topaz_ids"]].copy()
    groups["contrast_id"] = pd.to_numeric(groups["contrast_id"], errors="coerce").astype("Int64")
    groups["topaz_ids"] = groups["topaz_ids"].apply(_parse_topaz_ids)
    groups = groups.dropna(subset=["contrast_id"])
    groups = groups[groups["topaz_ids"].map(len) > 0].reset_index(drop=True)
    return groups


def build_aggregates(
    hillslopes,
    contrasts,
    hillslope_char,
    contrast_path=None,
    project_name="coastal-candelabrum",
    target_scenario="mulch_15_sbs_map",
    slope_range=None,
    bs_filter=None,
    outlet_totals=None,
    contrast_groups=None,
):
    # Primary path: use unified core implementation.
    if contrast_groups is None:
        return _build_aggregates_core(
            hillslopes=hillslopes,
            contrasts=contrasts,
            hillslope_char=hillslope_char,
            contrast_path=contrast_path,
            project_name=project_name,
            target_scenario=target_scenario,
            slope_range=slope_range,
            bs_filter=bs_filter,
            outlet_totals=outlet_totals,
            contrast_groups=None,
        )

    # Compatibility path for pre-built groups (matches notebook behavior).
    hills = hillslopes.copy()
    outlet = contrasts.copy()
    groups = _load_contrast_groups_df(contrast_groups)

    if "Topaz ID" not in hills.columns:
        if "TopazID" in hills.columns:
            hills["Topaz ID"] = hills["TopazID"]
        elif "topaz_id" in hills.columns:
            hills["Topaz ID"] = hills["topaz_id"]
        else:
            raise KeyError("hillslopes must contain Topaz ID information.")

    hills["Topaz ID"] = pd.to_numeric(hills["Topaz ID"], errors="coerce").astype("Int64")

    if "contrast_scenario" not in outlet.columns and "contrast" in outlet.columns:
        outlet["contrast_scenario"] = outlet["contrast"].astype(str).str.split("to__").str[-1]

    if "contrast_scenario" not in outlet.columns:
        raise KeyError("contrasts must contain contrast_scenario (or contrast) for grouped mapping.")

    contrast_to_scenario = (
        outlet[["contrast_id", "contrast_scenario"]]
        .dropna()
        .drop_duplicates(subset=["contrast_id"])
        .set_index("contrast_id")["contrast_scenario"]
        .to_dict()
    )

    expanded_rows = []
    for _, row in groups.iterrows():
        scenario_name = contrast_to_scenario.get(int(row["contrast_id"]))
        if pd.isna(scenario_name) or scenario_name is None:
            continue
        for topaz_id in row["topaz_ids"]:
            expanded_rows.append(
                {
                    "scenario": scenario_name,
                    "Topaz ID": int(topaz_id),
                    "contrast_id": int(row["contrast_id"]),
                }
            )

    if not expanded_rows:
        raise ValueError("No scenario-aware contrast mapping could be built from contrast_groups and contrasts.")

    scenario_map_df = pd.DataFrame(expanded_rows).drop_duplicates(subset=["scenario", "Topaz ID"])
    hills = hills.merge(
        scenario_map_df,
        on=["scenario", "Topaz ID"],
        how="left",
        suffixes=("", "_mapped"),
    )

    if "contrast_id_mapped" in hills.columns:
        hills["contrast_id"] = pd.to_numeric(hills["contrast_id_mapped"], errors="coerce").astype("Int64")
        hills = hills.drop(columns=["contrast_id_mapped"])
    else:
        hills["contrast_id"] = pd.to_numeric(hills.get("contrast_id"), errors="coerce").astype("Int64")

    topaz_to_group = {}
    for _, row in groups.iterrows():
        for topaz_id in row["topaz_ids"]:
            topaz_to_group.setdefault(int(topaz_id), int(row["contrast_id"]))

    sbs_mask = hills["scenario"].eq("sbs_map")
    hills.loc[sbs_mask, "contrast_id"] = hills.loc[sbs_mask, "Topaz ID"].map(topaz_to_group).astype("Int64")

    # Also handle undisturbed scenario - assign it the same contrast_ids as sbs_map based on Topaz IDs
    und_mask = hills["scenario"].eq("undisturbed")
    if und_mask.any():
        hills.loc[und_mask, "contrast_id"] = hills.loc[und_mask, "Topaz ID"].map(topaz_to_group).astype("Int64")

    return _build_aggregates_core(
        hillslopes=hills,
        contrasts=outlet,
        hillslope_char=hillslope_char,
        contrast_path=None,
        project_name=project_name,
        target_scenario=target_scenario,
        slope_range=slope_range,
        bs_filter=bs_filter,
        outlet_totals=outlet_totals,
        contrast_groups=None,
    )
