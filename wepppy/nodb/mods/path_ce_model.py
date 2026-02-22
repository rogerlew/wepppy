# Author: Jackson Nakae
# Date: October 2025

import numpy as np
import pandas as pd

from pulp import LpMaximize, LpMinimize, LpProblem, LpStatus, LpVariable, PulpSolverError

SEVERITY_BY_LANDUSE = {
    105: "High",
    119: "High",
    129: "High",
    118: "Moderate",
    120: "Moderate",
    130: "Moderate",
    106: "Low",
    121: "Low",
    131: "Low",
}

OUTLET_SCENARIO_BY_RATE = {
    "0.5 tons/acre": "mulch_15_sbs_map",
    "1 tons/acre": "mulch_30_sbs_map",
    "2 tons/acre": "mulch_60_sbs_map",
}

REQUIRED_HILLSLOPE_COLUMNS = (
    "WeppID",
    "TopazID",
    "Landuse",
    "Soil",
    "Length (m)",
    "Hillslope Area (ha)",
    "Runoff (mm)",
    "Lateral Flow (mm)",
    "Baseflow (mm)",
    "Soil Loss (kg/ha)",
    "Sediment Deposition (kg/ha)",
    "Sediment Yield (kg/ha)",
    "scenario",
    "Runoff (m^3)",
    "Lateral Flow (m^3)",
    "Baseflow (m^3)",
    "Soil Loss (t)",
    "Sediment Deposition (t)",
    "Sediment Yield (t)",
    "NTU (g/L)",
)

REQUIRED_OUTLET_COLUMNS = (
    "key",
    "v",
    "units",
    "control_scenario",
    "contrast_topaz_id",
    "contrast",
    "_contrast_name",
    "contrast_id",
    "control_v",
    "control_units",
    "control-contrast_v",
)

REQUIRED_HILLSLOPE_CHAR_COLUMNS = (
    "slope_scalar",
    "length",
    "width",
    "direction",
    "aspect",
    "area",
    "elevation",
    "centroid_px",
    "centroid_py",
    "centroid_lon",
    "centroid_lat",
    "wepp_id",
    "TopazID",
)


def _calculate_sddc_reduction_threshold(total_sddc_postfire, sddc_threshold):
    threshold = total_sddc_postfire - sddc_threshold
    if threshold < 0:
        print("Alert: Sddc threshold already met.")
        return 0
    return threshold


def _filter_solver_data(data, slope_range, bs_threshold):
    filtered = data
    if slope_range is not None:
        min_slope, max_slope = slope_range
        filtered = filtered.loc[
            (filtered["slope_deg"] >= min_slope) & (filtered["slope_deg"] <= max_slope)
        ]
    if bs_threshold is not None:
        filtered = filtered[filtered["Burn severity"].isin(bs_threshold)]
    return filtered.reset_index(drop=True)


def _extract_solver_benefits(data):
    water_quality = data.filter(regex="NTU reduction")
    soil_erosion = data.filter(regex="Sdyd reduction")
    benefits = [water_quality, soil_erosion]
    if any(df.empty for df in benefits):
        shape = benefits[0].shape
        benefits = [pd.DataFrame(np.zeros(shape)) if df.empty else df for df in benefits]
    return benefits[0], benefits[1]


def _build_solver_variables(treatments, num_sites, x_prefix, b_prefix):
    x_vars = {
        treatment: [LpVariable(f"{x_prefix}_{treatment}_{i}", 0, 1, cat="Binary") for i in range(num_sites)]
        for treatment in treatments
    }
    b_vars = {treatment: LpVariable(f"{b_prefix}_{treatment}", 0, 1, cat="Binary") for treatment in treatments}
    return x_vars, b_vars


def _add_sdyd_constraints(model, x_vars, treatments, num_sites, soil_erosion, sediment_yield_reduction_thresholds):
    for i in range(num_sites):
        max_reduction = max(soil_erosion.iloc[i, :])
        threshold = sediment_yield_reduction_thresholds[i]
        if max_reduction > threshold:
            model += (
                sum(
                    x_vars[t][i] * soil_erosion.iloc[:, n].values[i]
                    for n, t in enumerate(treatments)
                )
                >= threshold
            )
        else:
            model += (
                sum(
                    x_vars[t][i] * soil_erosion.iloc[:, n].values[i]
                    for n, t in enumerate(treatments)
                )
                == max_reduction
            )


def _build_lp_model(
    *,
    model_name,
    objective_sense,
    x_prefix,
    b_prefix,
    require_one_treatment,
    include_sddc_constraint,
    treatments,
    num_sites,
    treatment_cost_vectors,
    fixed_cost,
    water_quality,
    soil_erosion,
    sediment_yield_reduction_thresholds,
    sddc_reduction_threshold,
):
    model = LpProblem(model_name, objective_sense)
    x_vars, b_vars = _build_solver_variables(treatments, num_sites, x_prefix, b_prefix)

    if objective_sense == LpMinimize:
        model += sum(
            x_vars[t][i] * treatment_cost_vectors[t][i]
            for t in treatments
            for i in range(num_sites)
        ) + sum(b_vars[t] * fixed_cost[n] for n, t in enumerate(treatments))
    else:
        model += sum(
            x_vars[t][i] * water_quality.iloc[:, n].values[i]
            for n, t in enumerate(treatments)
            for i in range(num_sites)
        )

    for i in range(num_sites):
        if require_one_treatment:
            model += sum(x_vars[t][i] for t in treatments) == 1
        else:
            model += sum(x_vars[t][i] for t in treatments) <= 1

    for t in treatments:
        for i in range(num_sites):
            model += b_vars[t] >= x_vars[t][i]

    if include_sddc_constraint:
        model += (
            sum(
                x_vars[t][i] * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            >= sddc_reduction_threshold
        )

    _add_sdyd_constraints(
        model=model,
        x_vars=x_vars,
        treatments=treatments,
        num_sites=num_sites,
        soil_erosion=soil_erosion,
        sediment_yield_reduction_thresholds=sediment_yield_reduction_thresholds,
    )
    return model, x_vars, b_vars


def _summarize_solver_outputs(
    *,
    treatments,
    num_sites,
    hillslope_ids,
    selection_vars,
    fixed_vars,
    treatment_cost_vectors,
    fixed_cost,
    water_quality,
    total_sddc_postfire,
    data,
    all_data,
    sdyd_threshold,
):
    selected_sites = [
        [i for i in range(num_sites) if selection_vars[t][i].varValue == 1]
        for t in treatments
    ]
    selected_hillslopes = [
        hillslope_ids[i]
        for t in treatments
        for i in range(num_sites)
        if selection_vars[t][i].varValue == 1
    ]
    treatment_hillslopes = [hillslope_ids[site_ids].tolist() for site_ids in selected_sites]

    total_cost = sum(
        treatment_cost_vectors[t][i]
        for n, t in enumerate(treatments)
        for i in selected_sites[n]
    )
    total_fixed_cost = sum(fixed_vars[t].varValue * fixed_cost[n] for n, t in enumerate(treatments))
    total_sddc_reduction = sum(
        selection_vars[t][i].varValue * water_quality.iloc[:, n].values[i]
        for n, t in enumerate(treatments)
        for i in range(num_sites)
    )
    final_sddc = total_sddc_postfire - total_sddc_reduction

    hillslopes_sdyd = []
    for i in range(num_sites):
        for t in treatments:
            if selection_vars[t][i].varValue == 1:
                hillslope = data["wepp_id"][i]
                sdyd_value = data[f"Sdyd post-treat {t}"][i]
                hillslopes_sdyd.append([hillslope, sdyd_value])
    for i in range(num_sites):
        if all(selection_vars[t][i].varValue == 0 for t in treatments):
            hillslope = data["wepp_id"][i]
            sdyd_value = data["Sdyd post-fire"][i]
            hillslopes_sdyd.append([hillslope, sdyd_value])

    sdyd_df = pd.DataFrame(hillslopes_sdyd, columns=["wepp_id", "final_Sdyd"])
    untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold]

    missing_hillslopes = all_data[~all_data["wepp_id"].isin(data["wepp_id"])]
    if not missing_hillslopes.empty:
        missing_sdyd = missing_hillslopes[["wepp_id", "Sdyd post-fire"]].rename(
            columns={"Sdyd post-fire": "final_Sdyd"}
        )
        sdyd_df = pd.concat([sdyd_df, missing_sdyd], ignore_index=True)
    sdyd_df = sdyd_df.sort_values(by="wepp_id").reset_index(drop=True)

    return (
        selected_hillslopes,
        treatment_hillslopes,
        total_sddc_reduction,
        final_sddc,
        hillslopes_sdyd,
        sdyd_df,
        untreatable_sdyd,
        total_cost,
        total_fixed_cost,
    )


def ce_select_sites_2(
    data,
    treatments,
    treatment_cost,
    treatment_quantity,
    fixed_cost,
    sdyd_threshold,
    sddc_threshold,
    slope_range=(None),
    bs_threshold=(None),
):
    all_data = data.copy()
    total_sddc_postfire = data["NTU post-fire"].sum()
    sddc_reduction_threshold = _calculate_sddc_reduction_threshold(total_sddc_postfire, sddc_threshold)

    data = _filter_solver_data(data, slope_range, bs_threshold)
    water_quality, soil_erosion = _extract_solver_benefits(data)
    hillslope_ids = data["wepp_id"].values
    sediment_yield_reduction_thresholds = (data["Sdyd post-fire"] - sdyd_threshold).clip(lower=0)

    num_sites = len(data)
    treatment_cost_vectors = {
        t: data["area"] * c * q
        for t, c, q in zip(treatments, treatment_cost, treatment_quantity)
    }

    model_primary, x_primary, b_primary = _build_lp_model(
        model_name="Select_Sites",
        objective_sense=LpMinimize,
        x_prefix="x",
        b_prefix="B",
        require_one_treatment=False,
        include_sddc_constraint=True,
        treatments=treatments,
        num_sites=num_sites,
        treatment_cost_vectors=treatment_cost_vectors,
        fixed_cost=fixed_cost,
        water_quality=water_quality,
        soil_erosion=soil_erosion,
        sediment_yield_reduction_thresholds=sediment_yield_reduction_thresholds,
        sddc_reduction_threshold=sddc_reduction_threshold,
    )

    try:
        model_primary.solve()
        if LpStatus[model_primary.status] == "Optimal":
            print("Optimal solution found")
            selection_vars, fixed_vars = x_primary, b_primary
        else:
            print(
                "Warning: No optimal solution found for given thresholds. Second best solution will be returned"
            )
            model_secondary, x_secondary, b_secondary = _build_lp_model(
                model_name="Select_Sites_Secondary",
                objective_sense=LpMaximize,
                x_prefix="x_2",
                b_prefix="B_2",
                require_one_treatment=True,
                include_sddc_constraint=False,
                treatments=treatments,
                num_sites=num_sites,
                treatment_cost_vectors=treatment_cost_vectors,
                fixed_cost=fixed_cost,
                water_quality=water_quality,
                soil_erosion=soil_erosion,
                sediment_yield_reduction_thresholds=sediment_yield_reduction_thresholds,
                sddc_reduction_threshold=sddc_reduction_threshold,
            )
            model_secondary.solve()
            if LpStatus[model_secondary.status] != "Optimal":
                print("Warning: No second best solution found for given thresholds")
                return None
            selection_vars, fixed_vars = x_secondary, b_secondary
    except PulpSolverError:
        print("Solver failed!")
        return None

    (
        selected_hillslopes,
        treatment_hillslopes,
        total_sddc_reduction,
        final_sddc,
        hillslopes_sdyd,
        sdyd_df,
        untreatable_sdyd,
        total_cost,
        total_fixed_cost,
    ) = _summarize_solver_outputs(
        treatments=treatments,
        num_sites=num_sites,
        hillslope_ids=hillslope_ids,
        selection_vars=selection_vars,
        fixed_vars=fixed_vars,
        treatment_cost_vectors=treatment_cost_vectors,
        fixed_cost=fixed_cost,
        water_quality=water_quality,
        total_sddc_postfire=total_sddc_postfire,
        data=data,
        all_data=all_data,
        sdyd_threshold=sdyd_threshold,
    )

    return (
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
    )


def _require_columns(df, required_columns, error_message):
    if not all(column in df.columns for column in required_columns):
        raise ValueError(error_message)


def _extract_outlet_scenario(outlet_data, scenario_name):
    return outlet_data.loc[
        (outlet_data["key"] == "Avg. Ann. sediment discharge from outlet")
        & (outlet_data["contrast"].str.endswith(scenario_name))
    ].reset_index(drop=True)


def _extract_hillslope_scenario(hillslope_data, scenario_name):
    return hillslope_data[hillslope_data["scenario"] == scenario_name].reset_index(drop=True)


def path_data_ag(hillslope_data, outlet_data, hillslope_char_data):
    """Load, validate, and aggregate PATH CE hillslope/outlet inputs."""
    hillslope_data = pd.read_csv(hillslope_data)
    outlet_data = pd.read_csv(outlet_data)
    hillslope_char_data = pd.read_csv(hillslope_char_data)

    if hillslope_data.empty:
        raise ValueError("Hillslope data file is empty.")
    if outlet_data.empty:
        raise ValueError("Outlet data file is empty.")
    if hillslope_char_data.empty:
        raise ValueError("Hillslope characteristics data file is empty.")

    _require_columns(
        hillslope_data,
        REQUIRED_HILLSLOPE_COLUMNS,
        "Hillslope data file is missing required columns.",
    )
    _require_columns(
        outlet_data,
        REQUIRED_OUTLET_COLUMNS,
        "Outlet data file is missing required columns.",
    )
    _require_columns(
        hillslope_char_data,
        REQUIRED_HILLSLOPE_CHAR_COLUMNS,
        "Hillslope characteristics data file is missing required columns.",
    )

    if hillslope_data.isnull().values.any():
        raise ValueError("Missing values found in hillslope data.")
    if outlet_data[["v", "control_v"]].isnull().values.any():
        raise ValueError("Missing values found in outlet data.")
    if hillslope_char_data.isnull().values.any():
        raise ValueError("Missing values found in hillslope characteristics data.")

    hillslope_char_data.drop(columns=["topaz_id"], inplace=True)

    out_mulch_15 = _extract_outlet_scenario(outlet_data, OUTLET_SCENARIO_BY_RATE["0.5 tons/acre"])
    out_mulch_30 = _extract_outlet_scenario(outlet_data, OUTLET_SCENARIO_BY_RATE["1 tons/acre"])
    out_mulch_60 = _extract_outlet_scenario(outlet_data, OUTLET_SCENARIO_BY_RATE["2 tons/acre"])

    mulch_15 = _extract_hillslope_scenario(hillslope_data, OUTLET_SCENARIO_BY_RATE["0.5 tons/acre"])
    mulch_30 = _extract_hillslope_scenario(hillslope_data, OUTLET_SCENARIO_BY_RATE["1 tons/acre"])
    mulch_60 = _extract_hillslope_scenario(hillslope_data, OUTLET_SCENARIO_BY_RATE["2 tons/acre"])
    sbs_map = _extract_hillslope_scenario(hillslope_data, "sbs_map")
    undisturbed = _extract_hillslope_scenario(hillslope_data, "undisturbed")

    combined_sdyd_df = pd.DataFrame(
        {
            "wepp_id": sbs_map["WeppID"],
            "TopazID": sbs_map["TopazID"],
            "Landuse": sbs_map["Landuse"],
            "Sdyd post-treat 0.5 tons/acre": mulch_15["Sediment Yield (t)"],
            "Sdyd post-treat 1 tons/acre": mulch_30["Sediment Yield (t)"],
            "Sdyd post-treat 2 tons/acre": mulch_60["Sediment Yield (t)"],
            "Sdyd post-fire": sbs_map["Sediment Yield (t)"],
            "Sdyd undisturbed": undisturbed["Sediment Yield (t)"],
        }
    )
    combined_runoff_df = pd.DataFrame(
        {
            "wepp_id": sbs_map["WeppID"],
            "TopazID": sbs_map["TopazID"],
            "Landuse": sbs_map["Landuse"],
            "Runoff 0.5 tons/acre": mulch_15["Runoff (mm)"],
            "Runoff post-treat 1 tons/acre": mulch_30["Runoff (mm)"],
            "Runoff post-treat 2 tons/acre": mulch_60["Runoff (mm)"],
            "Runoff post-fire": sbs_map["Runoff (mm)"],
            "Runoff undisturbed": undisturbed["Runoff (mm)"],
        }
    )
    combined_lateralflow_df = pd.DataFrame(
        {
            "wepp_id": sbs_map["WeppID"],
            "TopazID": sbs_map["TopazID"],
            "Landuse": sbs_map["Landuse"],
            "Lateralflow post-treat 0.5 tons/acre": mulch_15["Lateral Flow (mm)"],
            "Lateralflow post-treat 1 tons/acre": mulch_30["Lateral Flow (mm)"],
            "Lateralflow post-treat 2 tons/acre": mulch_60["Lateral Flow (mm)"],
            "Lateralflow post-fire": sbs_map["Lateral Flow (mm)"],
            "Lateralflow undisturbed": undisturbed["Lateral Flow (mm)"],
        }
    )
    combined_baseflow_df = pd.DataFrame(
        {
            "wepp_id": sbs_map["WeppID"],
            "TopazID": sbs_map["TopazID"],
            "Landuse": sbs_map["Landuse"],
            "Baseflow post-treat 0.5 tons/acre": mulch_15["Baseflow (mm)"],
            "Baseflow post-treat 1 tons/acre": mulch_30["Baseflow (mm)"],
            "Baseflow post-treat 2 tons/acre": mulch_60["Baseflow (mm)"],
            "Baseflow post-fire": sbs_map["Baseflow (mm)"],
            "Baseflow undisturbed": undisturbed["Baseflow (mm)"],
        }
    )
    combined_ntu_df = pd.DataFrame(
        {
            "wepp_id": sbs_map["WeppID"],
            "TopazID": sbs_map["TopazID"],
            "Landuse": sbs_map["Landuse"],
            "NTU post-treat 0.5 tons/acre": mulch_15["NTU (g/L)"],
            "NTU post-treat 1 tons/acre": mulch_30["NTU (g/L)"],
            "NTU post-treat 2 tons/acre": mulch_60["NTU (g/L)"],
            "NTU post-fire": sbs_map["NTU (g/L)"],
            "NTU undisturbed": undisturbed["NTU (g/L)"],
        }
    )
    combined_sddc_df = pd.DataFrame(
        {
            "TopazID": out_mulch_15["contrast_topaz_id"],
            "Sddc post-treat 0.5 tons/acre": out_mulch_15["v"],
            "Sddc post-treat 1 tons/acre": out_mulch_30["v"],
            "Sddc post-treat 2 tons/acre": out_mulch_60["v"],
            "Sddc post-fire": out_mulch_15["control_v"],
        }
    )

    data_piv = (
        pd.merge(combined_sdyd_df, combined_sddc_df, on=["TopazID"], how="outer")
        .merge(combined_runoff_df, on=["wepp_id", "TopazID", "Landuse"], how="outer")
        .merge(combined_lateralflow_df, on=["wepp_id", "TopazID", "Landuse"])
        .merge(combined_baseflow_df, on=["wepp_id", "TopazID", "Landuse"])
        .merge(combined_ntu_df, on=["wepp_id", "TopazID", "Landuse"], how="outer")
        .merge(hillslope_char_data, on=["wepp_id", "TopazID"])
    )

    data_piv["Sddc reduction 0.5 tons/acre"] = data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 0.5 tons/acre"]
    data_piv["Sddc reduction 1 tons/acre"] = data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 1 tons/acre"]
    data_piv["Sddc reduction 2 tons/acre"] = data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 2 tons/acre"]

    data_piv["Sdyd reduction 0.5 tons/acre"] = data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 0.5 tons/acre"]
    data_piv["Sdyd reduction 1 tons/acre"] = data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 1 tons/acre"]
    data_piv["Sdyd reduction 2 tons/acre"] = data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 2 tons/acre"]

    data_piv["NTU reduction 0.5 tons/acre"] = data_piv["NTU post-fire"] - data_piv["NTU post-treat 0.5 tons/acre"]
    data_piv["NTU reduction 1 tons/acre"] = data_piv["NTU post-fire"] - data_piv["NTU post-treat 1 tons/acre"]
    data_piv["NTU reduction 2 tons/acre"] = data_piv["NTU post-fire"] - data_piv["NTU post-treat 2 tons/acre"]

    data_piv["area"] = data_piv["area"] * 0.0001
    data_piv["Landuse"] = data_piv["Landuse"].astype(int)
    data_piv["Burn severity"] = data_piv["Landuse"].map(SEVERITY_BY_LANDUSE).fillna("NaN")

    data_piv["slope_deg"] = np.degrees(np.arctan(data_piv["slope_scalar"]))
    final_data = data_piv.dropna()
    final_data.reset_index(drop=True, inplace=True)
    return final_data
