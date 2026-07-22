"""PATH cost-effective threshold sweep and plot helpers.

Vendored from Jackson Nakae's PATH-cost-effective repository
(https://github.com/jackson-nakae/PATH-cost-effective, ``PATH_plot.py`` @ 4e3b4a6).

Faithful extraction with these seam changes only:

- imports the vendored solver (``.path_ce_solver``) instead of ``PATH_CE``;
- upstream's commented-out alternative ``find_threshold_ranges`` block removed.

``find_threshold_ranges`` binary-searches the minimum primary-feasible Sddc
threshold; ``all_thresholds`` sweeps a bounded threshold grid (up to ~75x75 LP
solves) powering the report's interactive sliders, cost surface, and threshold
plots. Sweep-result caching is the caller's responsibility (RQ task persists
under ``<wd>/path/``); this module stays pure compute, matching upstream.

The matplotlib/geopandas plot helpers import their dependencies lazily
(upstream style) so this module stays importable in the worker without a
plotting stack.

Sync notes and reference goldens: ``docs/work-packages/20260720_path_ce_v2/``.
"""

import os
import ast
from contextlib import redirect_stderr, redirect_stdout

import numpy as np
import pandas as pd
from pulp import PulpSolverError

from .path_ce_solver import ce_select_sites_flexible

__all__ = [
    "all_thresholds",
    "find_threshold_ranges",
    "plot_sddc_vs_cost",
    "plot_sdyd_vs_cost",
    "plot_treatment_selection_map",
]


def find_threshold_ranges(data, treatments, treatment_cost, treatment_quantity,
                                    fixed_cost, step_size=5, tolerance=1e-6):
    """
    Find SDDC/SDYD ranges and the minimum feasible SDDC threshold.

    This implementation uses binary search on SDDC feasibility, which reduces
    solve count from O(N) threshold scans to O(log N) model solves.

    Returns:
    - sddc_threshold_range: (lower_bound_sddc, max_sddc_threshold)
    - sdyd_threshold_range: (min_sdyd_threshold, max_sdyd_threshold)
    - sddc_threshold: lower_bound_sddc (minimum feasible SDDC)
    - sdyd_threshold: max_sdyd_val (maximum SDYD)
    """
    import pandas as pd
    import os
    from contextlib import redirect_stdout, redirect_stderr

    # Determine Sdyd min/max from data based on post-treat columns for provided treatments.
    sdyd_treatments = []
    for i in range(len(treatments)):
        sdyd_treatment = "Sdyd post-treat " + treatments[i]
        sdyd_treatments.append(sdyd_treatment)

    max_sdyd_val = int(data["Sdyd post-fire"].max()) + 1
    available_sdyd_treatments = [column for column in sdyd_treatments if column in data.columns]
    if available_sdyd_treatments:
        min_sdyd_val = data[available_sdyd_treatments].min().min()
    else:
        # Fallback if post-treat columns differ; use post-fire min.
        min_sdyd_val = data["Sdyd post-fire"].min()
    min_sdyd_round = int(min_sdyd_val)

    # Use post-fire SDDC maximum to set the upper bound of the search interval.
    max_sddc_val = data["Sddc post-fire"].max()
    max_sddc_round = int(max_sddc_val) + 1

    def _status_for_threshold(sddc_thr):
        try:
            with open(os.devnull, "w") as devnull:
                with redirect_stdout(devnull), redirect_stderr(devnull):
                    result = ce_select_sites_flexible(
                        data=data,
                        treatments=treatments,
                        treatment_cost=treatment_cost,
                        treatment_quantity=treatment_quantity,
                        fixed_cost=fixed_cost,
                        sdyd_threshold=max_sdyd_val,
                        sddc_threshold=int(sddc_thr),
                        slope_range=None,
                        bs_threshold=None,
                    )
            if result is None:
                return None
            return result[0]
        except PulpSolverError:
            return None

    # We search for the minimum feasible SDDC threshold (status == 1).
    # Assumption: feasibility is monotonic with SDDC threshold.
    low, high = 0, max_sddc_round
    best_feasible = None

    high_status = _status_for_threshold(high)
    if high_status != 1:
        # If even the upper bound is not feasible, return the conservative bound.
        lower_bound_sddc = max_sddc_round
    else:
        low_status = _status_for_threshold(low)
        if low_status == 1:
            lower_bound_sddc = 0
        else:
            while low <= high:
                mid = (low + high) // 2
                status = _status_for_threshold(mid)

                if status == 1:
                    best_feasible = mid
                    high = mid - 1
                else:
                    low = mid + 1

            lower_bound_sddc = best_feasible if best_feasible is not None else max_sddc_round

    sddc_threshold_range = (int(lower_bound_sddc), int(max_sddc_round))
    sdyd_threshold_range = (int(min_sdyd_round), int(max_sdyd_val))
    return sddc_threshold_range, sdyd_threshold_range, int(lower_bound_sddc), int(max_sdyd_val)


def all_thresholds(
    data,
    treatments,
    treatment_cost,
    treatment_quantity,
    fixed_cost,
    sdyd_threshold_range,
    sddc_threshold_range,
    sdyd_threshold,
    sddc_threshold,
    return_increase_class=True,
    slope_range=None,
    bs_threshold=None,
    id_col=None,
    area_col=None,
    quiet=True,
):
    """
    Sweep sdyd/sddc threshold combinations and run ce_select_sites_flexible for each pair.

    sdyd_threshold/sddc_threshold are required anchor values and are forcibly included
    in the sampled threshold vectors for visualization consistency.
    """
    sdyd_min, sdyd_max = int(sdyd_threshold_range[0]), int(sdyd_threshold_range[1])
    sddc_min, sddc_max = int(sddc_threshold_range[0]), int(sddc_threshold_range[1])
    sdyd_threshold = int(sdyd_threshold)
    sddc_threshold = int(sddc_threshold)

    def _build_steps(lower, upper):
        span = upper - lower
        if span <= 20:
            arr = np.linspace(lower, upper, span + 1, dtype=int)
        elif span <= 200:
            arr = np.linspace(lower, upper, 20, dtype=int)
        elif span <= 2000:
            arr = np.linspace(lower, upper, 50, dtype=int)
        else:
            arr = np.linspace(lower, upper, 75, dtype=int)
        return np.unique(arr.astype(int))

    sdyd_step_values = _build_steps(sdyd_min, sdyd_max)
    sddc_step_values = _build_steps(sddc_min, sddc_max)
    sdyd_step_values = np.unique(np.append(sdyd_step_values, sdyd_threshold).astype(int))
    sddc_step_values = np.unique(np.append(sddc_step_values, sddc_threshold).astype(int))

    results = []
    for sdyd_thr in sdyd_step_values:
        for sddc_thr in sddc_step_values:
            try:
                if quiet:
                    with open(os.devnull, 'w') as devnull:
                        with redirect_stdout(devnull), redirect_stderr(devnull):
                            result = ce_select_sites_flexible(
                                data=data,
                                treatments=treatments,
                                treatment_cost=treatment_cost,
                                treatment_quantity=treatment_quantity,
                                fixed_cost=fixed_cost,
                                sdyd_threshold=int(sdyd_thr),
                                sddc_threshold=int(sddc_thr),
                                slope_range=slope_range,
                                bs_threshold=bs_threshold,
                                id_col=id_col,
                                area_col=area_col,
                                return_increase_class=return_increase_class,
                            )
                else:
                    result = ce_select_sites_flexible(
                        data=data,
                        treatments=treatments,
                        treatment_cost=treatment_cost,
                        treatment_quantity=treatment_quantity,
                        fixed_cost=fixed_cost,
                        sdyd_threshold=int(sdyd_thr),
                        sddc_threshold=int(sddc_thr),
                        slope_range=slope_range,
                        bs_threshold=bs_threshold,
                        id_col=id_col,
                        area_col=area_col,
                        return_increase_class=return_increase_class,
                    )

                if result is None:
                    results.append({
                        'sddc_threshold': int(sddc_thr),
                        'sdyd_threshold': int(sdyd_thr),
                        'model_primary_status': None,
                        'selected_hillslopes': None,
                        'treatment_hillslopes': None,
                        'total_Sddc_reduction': np.nan,
                        'final_Sddc': np.nan,
                        'hillslopes_sdyd': None,
                        'sdyd_df': None,
                        'untreatable_sdyd': None,
                        'total_cost': np.nan,
                        'total_fixed_cost': np.nan,
                    })
                    continue

                (
                    model_primary_status,
                    _treatment_cost_vectors,
                    _sediment_yield_reduction_thresholds,
                    selected_hillslopes,
                    treatment_hillslopes,
                    total_Sddc_reduction,
                    final_Sddc,
                    hillslopes_sdyd,
                    sdyd_df,
                    untreatable_sdyd,
                    total_cost,
                    total_fixed_cost,
                    untreatable_sdyd_increase,
                ) = result

                results.append({
                    'sddc_threshold': int(sddc_thr),
                    'sdyd_threshold': int(sdyd_thr),
                    'model_primary_status': model_primary_status,
                    'selected_hillslopes': selected_hillslopes,
                    'treatment_hillslopes': treatment_hillslopes,
                    'total_Sddc_reduction': total_Sddc_reduction,
                    'final_Sddc': final_Sddc,
                    'hillslopes_sdyd': hillslopes_sdyd,
                    'sdyd_df': sdyd_df,
                    'untreatable_sdyd': untreatable_sdyd,
                    'total_cost': total_cost,
                    'total_fixed_cost': total_fixed_cost,
                    'untreatable_sdyd_increase': untreatable_sdyd_increase,
                })
            except KeyboardInterrupt:
                raise
            except PulpSolverError as exc:
                results.append({
                    'sddc_threshold': int(sddc_thr),
                    'sdyd_threshold': int(sdyd_thr),
                    'model_primary_status': None,
                    'selected_hillslopes': None,
                    'treatment_hillslopes': None,
                    'total_Sddc_reduction': np.nan,
                    'final_Sddc': np.nan,
                    'hillslopes_sdyd': None,
                    'sdyd_df': None,
                    'untreatable_sdyd': None,
                    'total_cost': np.nan,
                    'total_fixed_cost': np.nan,
                    'untreatable_sdyd_increase': None,
                    'error': repr(exc),
                })
    results_df = pd.DataFrame(results)
    return results_df


def _to_int_set(values):
    """Convert an iterable of mixed values into a set of ints."""
    if values is None:
        return set()
    series = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    return set(series.astype(int).tolist())


def _parse_id_list(value):
    """Parse list-like cells used by topaz_ids/topaz_ids_all columns."""
    if isinstance(value, list):
        return [int(v) for v in pd.to_numeric(pd.Series(value), errors="coerce").dropna().astype(int).tolist()]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return [int(v) for v in pd.to_numeric(pd.Series(parsed), errors="coerce").dropna().astype(int).tolist()]
        except (ValueError, SyntaxError):
            return []
    return []


def _first_present(columns, candidates):
    for col in candidates:
        if col in columns:
            return col
    return None


def _extract_result_payload(result):
    """Read selection outputs from either CE tuple output or a results_df row/dict."""
    if isinstance(result, tuple) and len(result) >= 12:
        return {
            "selected_hillslopes": result[3],
            "treatment_hillslopes": result[4],
            "final_Sddc": result[6],
            "untreatable_sdyd": result[9],
            "total_cost": result[10],
            "untreatable_sdyd_increase": result[12] if len(result) >= 13 else None,
        }

    if isinstance(result, pd.Series):
        result = result.to_dict()

    if isinstance(result, dict):
        return {
            "selected_hillslopes": result.get("selected_hillslopes", []),
            "treatment_hillslopes": result.get("treatment_hillslopes", []),
            "final_Sddc": result.get("final_Sddc", np.nan),
            "untreatable_sdyd": result.get("untreatable_sdyd", None),
            "total_cost": result.get("total_cost", np.nan),
            "untreatable_sdyd_increase": result.get("untreatable_sdyd_increase", None),
        }

    raise TypeError("result must be a CE tuple, pandas Series row, or dict-like payload.")


def plot_treatment_selection_map(
    result,
    final_data,
    gdf,
    gdf_channels=None,
    treatments=None,
    title_prefix="",
    figsize=(10, 10),
    include_group_borders=True,
    include_untreatable=True,
    untreatable_sdyd_increase=None,
):
    """Plot selected treatment areas on hillslope polygons across PATH watershed schemas.

    Supports all current watershed data variants by auto-detecting identifier styles:
    - contrast-based selection: final_data contains contrast_id + topaz_ids(_all)
    - Topaz-based selection: selected IDs align with TopazID-like columns
    - Wepp-based selection: selected IDs align with WeppID/wepp_id columns
    """
    import geopandas as gpd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from shapely.geometry import Polygon, MultiPolygon

    payload = _extract_result_payload(result)
    treatment_hillslopes = payload["treatment_hillslopes"] if payload["treatment_hillslopes"] is not None else []
    untreatable_sdyd = payload["untreatable_sdyd"]
    if untreatable_sdyd_increase is None:
        untreatable_sdyd_increase = payload.get("untreatable_sdyd_increase")
    total_cost = payload["total_cost"]
    final_sddc = payload["final_Sddc"]

    if treatments is None:
        if isinstance(treatment_hillslopes, list) and treatment_hillslopes:
            treatments = [f"Treatment {i + 1}" for i in range(len(treatment_hillslopes))]
        else:
            treatments = []

    final_df = final_data.copy()
    gdf_plot = gdf.copy()

    topaz_ids_col = _first_present(final_df.columns, ["topaz_ids_all", "topaz_ids"])
    final_contrast_col = _first_present(final_df.columns, ["contrast_id"])
    final_topaz_col = _first_present(final_df.columns, ["TopazID", "topaz_id", "Topaz ID"])
    final_wepp_col = _first_present(final_df.columns, ["wepp_id", "WeppID"])

    gdf_topaz_col = _first_present(gdf_plot.columns, ["TopazID", "topaz_id", "Topaz ID"])
    gdf_wepp_col = _first_present(gdf_plot.columns, ["WeppID", "wepp_id"])
    if gdf_topaz_col is None and gdf_wepp_col is None:
        raise KeyError("gdf must include a TopazID-like or WeppID-like identifier column.")

    gdf_plot["_topaz_id"] = (
        pd.to_numeric(gdf_plot[gdf_topaz_col], errors="coerce").astype("Int64") if gdf_topaz_col else pd.Series(pd.NA, index=gdf_plot.index, dtype="Int64")
    )
    gdf_plot["_wepp_id"] = (
        pd.to_numeric(gdf_plot[gdf_wepp_col], errors="coerce").astype("Int64") if gdf_wepp_col else pd.Series(pd.NA, index=gdf_plot.index, dtype="Int64")
    )

    contrast_to_topaz = {}
    if final_contrast_col is not None and topaz_ids_col is not None:
        for _, row in final_df[[final_contrast_col, topaz_ids_col]].dropna(subset=[final_contrast_col]).iterrows():
            cid = int(pd.to_numeric(row[final_contrast_col], errors="coerce"))
            tids = _parse_id_list(row[topaz_ids_col])
            if tids:
                contrast_to_topaz[cid] = tids

    treatment_id_sets = []
    for i in range(len(treatments)):
        ids = treatment_hillslopes[i] if i < len(treatment_hillslopes) else []
        treatment_id_sets.append(_to_int_set(ids))

    all_selected_ids = set().union(*treatment_id_sets) if treatment_id_sets else set()
    gdf_topaz_ids = _to_int_set(gdf_plot["_topaz_id"].dropna().tolist())
    gdf_wepp_ids = _to_int_set(gdf_plot["_wepp_id"].dropna().tolist())
    contrast_ids = set(contrast_to_topaz.keys())

    score_topaz = len(all_selected_ids.intersection(gdf_topaz_ids))
    score_wepp = len(all_selected_ids.intersection(gdf_wepp_ids))
    score_contrast = len(all_selected_ids.intersection(contrast_ids))

    if score_contrast > max(score_topaz, score_wepp):
        id_mode = "contrast"
    elif score_wepp > score_topaz:
        id_mode = "wepp"
    else:
        id_mode = "topaz"

    def _selected_mask(ids):
        if not ids:
            return pd.Series(False, index=gdf_plot.index)
        if id_mode == "contrast":
            topaz_ids = set()
            for cid in ids:
                topaz_ids.update(contrast_to_topaz.get(int(cid), []))
            return gdf_plot["_topaz_id"].isin(topaz_ids)
        if id_mode == "wepp":
            return gdf_plot["_wepp_id"].isin(ids)
        return gdf_plot["_topaz_id"].isin(ids)

    gdf_plot["treatment"] = "Untreated"
    for idx, treatment in enumerate(treatments):
        mask = _selected_mask(treatment_id_sets[idx])
        gdf_plot.loc[mask, "treatment"] = treatment

    poly_mask = gdf_plot.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    gdf_poly = gdf_plot[poly_mask].copy()

    def _exterior_only(geom):
        if geom is None or geom.is_empty:
            return None
        geom = geom.buffer(0)
        if geom.geom_type == "Polygon":
            return Polygon(geom.exterior)
        if geom.geom_type == "MultiPolygon":
            return MultiPolygon([Polygon(p.exterior) for p in geom.geoms if not p.is_empty])
        return None

    all_group_unions = []
    if include_group_borders and id_mode == "contrast" and contrast_to_topaz:
        for group_ids in contrast_to_topaz.values():
            group_geoms = gdf_poly[gdf_poly["_topaz_id"].isin(group_ids)].geometry
            if not group_geoms.empty:
                shell = _exterior_only(group_geoms.unary_union)
                if shell is not None and not shell.is_empty:
                    all_group_unions.append(shell)

    def _ids_to_unions(raw_ids):
        unions = []
        if not raw_ids:
            return unions
        if id_mode == "contrast":
            for rid in raw_ids:
                group_ids = contrast_to_topaz.get(int(rid), [])
                group_geoms = gdf_poly[gdf_poly["_topaz_id"].isin(group_ids)].geometry
                if not group_geoms.empty:
                    shell = _exterior_only(group_geoms.unary_union)
                    if shell is not None and not shell.is_empty:
                        unions.append(shell)
        elif id_mode == "wepp":
            group_geoms = gdf_poly[gdf_poly["_wepp_id"].isin(raw_ids)].geometry
            if not group_geoms.empty:
                shell = _exterior_only(group_geoms.unary_union)
                if shell is not None and not shell.is_empty:
                    unions.append(shell)
        else:
            group_geoms = gdf_poly[gdf_poly["_topaz_id"].isin(raw_ids)].geometry
            if not group_geoms.empty:
                shell = _exterior_only(group_geoms.unary_union)
                if shell is not None and not shell.is_empty:
                    unions.append(shell)
        return unions

    untreatable_other_unions = []
    untreatable_increase_unions = []
    if include_untreatable and untreatable_sdyd is not None and hasattr(untreatable_sdyd, "empty") and not untreatable_sdyd.empty:
        untreatable_id_col = next((c for c in untreatable_sdyd.columns if c != "final_Sdyd"), None)
        if untreatable_id_col is not None:
            untreatable_ids = _to_int_set(untreatable_sdyd[untreatable_id_col].tolist())

            increase_ids = set()
            if untreatable_sdyd_increase is not None and hasattr(untreatable_sdyd_increase, "empty") and not untreatable_sdyd_increase.empty:
                increase_id_col = next((c for c in untreatable_sdyd_increase.columns if c != "final_Sdyd"), untreatable_id_col)
                if increase_id_col in untreatable_sdyd_increase.columns:
                    increase_ids = _to_int_set(untreatable_sdyd_increase[increase_id_col].tolist())
            else:
                # Fallback classification from final_data when explicit increase class is unavailable.
                treat_cols = [f"Sdyd post-treat {t}" for t in treatments if f"Sdyd post-treat {t}" in final_df.columns]
                if treat_cols and "Sdyd post-fire" in final_df.columns:
                    id_col_for_increase = None
                    if id_mode == "contrast":
                        id_col_for_increase = final_contrast_col
                    elif id_mode == "wepp":
                        id_col_for_increase = final_wepp_col
                    else:
                        id_col_for_increase = final_topaz_col

                    if id_col_for_increase in final_df.columns:
                        inc_df = final_df[[id_col_for_increase, "Sdyd post-fire"] + treat_cols].copy()
                        inc_df["Sdyd post-fire"] = pd.to_numeric(inc_df["Sdyd post-fire"], errors="coerce")
                        for col in treat_cols:
                            inc_df[col] = pd.to_numeric(inc_df[col], errors="coerce")
                        inc_mask = inc_df[treat_cols].gt(inc_df["Sdyd post-fire"], axis=0).all(axis=1)
                        increase_ids = _to_int_set(inc_df.loc[inc_mask, id_col_for_increase].tolist())

            increase_untreatable_ids = untreatable_ids.intersection(increase_ids)
            other_untreatable_ids = untreatable_ids.difference(increase_untreatable_ids)

            untreatable_increase_unions = _ids_to_unions(increase_untreatable_ids)
            untreatable_other_unions = _ids_to_unions(other_untreatable_ids)

    palette = ["#c9ebac", "#57af51", "#066106", "#1f7a8c", "#ffb703", "#9c6644"]
    color_map = {t: palette[i % len(palette)] for i, t in enumerate(treatments)}

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xticks([])
    ax.set_yticks([])

    for treatment_val, color in [("Untreated", "#f5f5f5")] + [(t, color_map[t]) for t in treatments]:
        layer = gdf_poly[gdf_poly["treatment"] == treatment_val]
        if not layer.empty:
            layer.plot(ax=ax, color=color, edgecolor="#888888", linewidth=0.5, alpha=1.0, zorder=1)

    if all_group_unions:
        all_groups_gdf = gpd.GeoDataFrame(geometry=all_group_unions, crs=gdf_poly.crs)
        all_groups_gdf.boundary.plot(ax=ax, color="#555555", linewidth=1.0, zorder=3)

    if untreatable_other_unions:
        untreatable_other_gdf = gpd.GeoDataFrame(geometry=untreatable_other_unions, crs=gdf_poly.crs)
        untreatable_other_gdf.boundary.plot(ax=ax, color="#ffd60a", linewidth=2.0, zorder=4)

    if untreatable_increase_unions:
        untreatable_inc_gdf = gpd.GeoDataFrame(geometry=untreatable_increase_unions, crs=gdf_poly.crs)
        untreatable_inc_gdf.boundary.plot(ax=ax, color="red", linewidth=2.2, zorder=5)

    if gdf_channels is not None and not gdf_channels.empty:
        gdf_channels.plot(ax=ax, color="#2f86c7", linewidth=1.4, alpha=1.0, zorder=6)

    legend_patches = [mpatches.Patch(facecolor="#f5f5f5", edgecolor="#888888", label="Untreated")]
    for t in treatments:
        legend_patches.append(mpatches.Patch(facecolor=color_map[t], edgecolor="#888888", label=f"Mulch: {t}"))
    if all_group_unions:
        legend_patches.append(mpatches.Patch(facecolor="none", edgecolor="#555555", linewidth=1.5, label="Hillslope Group Border"))
    if untreatable_other_unions:
        legend_patches.append(mpatches.Patch(facecolor="none", edgecolor="#ffd60a", linewidth=2.0, label="Sdyd Threshold Not Met"))
    if untreatable_increase_unions:
        legend_patches.append(mpatches.Patch(facecolor="none", edgecolor="red", linewidth=2.2, label="Increase in Sdyd"))

    ax.legend(handles=legend_patches, loc="lower right", fontsize=10)

    title_parts = [title_prefix.strip()] if title_prefix else []
    if pd.notna(total_cost) and pd.notna(final_sddc):
        title_parts.append(f"Total Cost: ${float(total_cost):,.2f}   Final Sddc: {float(final_sddc):,.2f} tons")
    elif pd.notna(total_cost):
        title_parts.append(f"Total Cost: ${float(total_cost):,.2f}")
    elif pd.notna(final_sddc):
        title_parts.append(f"Final Sddc: {float(final_sddc):,.2f} tons")

    ax.set_title("\n".join(title_parts) if title_parts else "Treatment Selection Map", fontsize=12)
    plt.tight_layout()
    plt.show()

    return fig, ax


def plot_sddc_vs_cost(results_df, sdyd_threshold=200, sddc_threshold=200, ax=None, figsize=(10, 6)):
    """
    Plot Sddc threshold vs total cost from results_df for a fixed Sdyd threshold.

    Parameters
    - results_df: DataFrame with columns ['sddc_threshold','sdyd_threshold','total_cost']
    - sdyd_threshold: int/float, the Sdyd threshold to filter on (default 200)
    - ax: matplotlib.axes.Axes (optional). If None, a new figure is created.
    - figsize: tuple for figure size when ax is None.

    Returns
    - ax: matplotlib axes containing the plot
    """
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    df_plot = results_df[results_df['sdyd_threshold'] ==sdyd_threshold].copy()
    if df_plot.empty:
        raise ValueError(f"No rows found in results_df for sdyd_threshold == {sdyd_threshold}")

    # ensure correct dtypes and sort
    df_plot['sddc_threshold'] = df_plot['sddc_threshold'].astype(float)
    df_plot['total_cost'] = df_plot['total_cost'].astype(float)
    df_plot = df_plot.sort_values('sddc_threshold')

    x = df_plot['sddc_threshold'].values
    y = df_plot['total_cost'].values
    y_plot = y
    ylabel = 'Total Cost ($)'
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    ax.plot(x, y_plot, linestyle='-', color='C0', label=f'Sdyd = {sdyd_threshold}')
    ax.set_xlabel('Sddc Threshold (t)')
    ax.set_ylabel(ylabel)
    ax.set_title(f'Total Cost vs Sediment Discharge Threshold (Sdyd threshold (t/ac) = {sdyd_threshold})', fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.6)

    #Indicate the location of the specified sdyd_threshold with arrow and dot
    corresponding_cost = y_plot[x==sddc_threshold][0]

    return ax


def plot_sdyd_vs_cost(results_df, sdyd_threshold=200, sddc_threshold=200, ax=None, figsize=(10, 6)):
    """
    Plot Sdyd threshold vs total cost from results_df for a fixed Sddc threshold.

    Parameters
    - results_df: DataFrame with columns ['sddc_threshold','sdyd_threshold','total_cost']
    - sdyd_threshold: int/float, the Sdyd threshold to highlight on the plot (default 200)
    - sddc_threshold: int/float, the Sddc threshold to filter on (default 200)
    - ax: matplotlib.axes.Axes (optional). If None, a new figure is created.
    - figsize: tuple for figure size when ax is None.

    Returns
    - ax: matplotlib axes containing the plot
    """
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    # Find the closest Sddc threshold in the data
    sddc_thresholds = results_df['sddc_threshold'].unique()
    closest_sddc = min(sddc_thresholds, key=lambda x: abs(x - sddc_threshold))

    df_plot = results_df[results_df['sddc_threshold'] == sddc_threshold].copy()
    if df_plot.empty:
        raise ValueError(f"No rows found in results_df for sddc_threshold == {sddc_threshold}")

    # Ensure correct dtypes and sort
    df_plot['sdyd_threshold'] = df_plot['sdyd_threshold'].astype(float)
    df_plot['total_cost'] = df_plot['total_cost'].astype(float)
    df_plot = df_plot.sort_values('sdyd_threshold')

    x = df_plot['sdyd_threshold'].values
    y = df_plot['total_cost'].values
    y_plot = y
    ylabel = 'Total Cost ($)'
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)


    ax.plot(x, y_plot, linestyle='-', color='C0', label=f'Sddc = {sddc_threshold}')
    ax.set_xlabel('Sdyd Threshold (t/ac)')
    ax.set_ylabel(ylabel)
    ax.set_title(f'Total Cost vs Sediment Yield Threshold (Sddc threshold (t) = {sddc_threshold})', fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.6)

    # Indicate the location of the specified sdyd_threshold with arrow and dot
    corresponding_cost = y_plot[x==sdyd_threshold][0]

    return ax
