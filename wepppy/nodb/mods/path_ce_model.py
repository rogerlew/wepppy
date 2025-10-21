# Author: Jackson Nakae
# Date: October 2025

import pandas as pd
import numpy as np

from pulp import (
    LpProblem,
    lpSum,
    LpMaximize,
    LpMinimize,
    LpVariable,
    value,
    PulpSolverError,
    LpStatus,
    LpConstraint,
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
    # Total sediment discharge post-fire
    # total_Sddc_postfire = data['Sddc post-fire'].sum()
    total_Sddc_postfire = data["NTU post-fire"].sum()

    # Calculate the total sediment discharge post-fire minus the user defined threshold
    # This is the amount of sediment discharge that needs to be reduced to meet the threshold
    Sddc_reduction_threshold = total_Sddc_postfire - sddc_threshold
    if Sddc_reduction_threshold < 0:
        print("Alert: Sddc threshold already met.")
        Sddc_reduction_threshold = 0

    # filter data acoording to the slope and burn severity
    if slope_range is not None:
        min_slope, max_slope = slope_range
        data = data.loc[
            (data["slope_deg"] >= min_slope) & (data["slope_deg"] <= max_slope)
        ]
    if bs_threshold is not None:
        data = data[data["Burn severity"].isin(bs_threshold)]
    data = data.reset_index(drop=True)

    # Filter for columns related to water quality and soil erosion
    water_quality = data.filter(regex="NTU reduction")
    # water_quality = data.filter(regex='Sddc reduction')
    soil_erosion = data.filter(regex="Sdyd reduction")
    benefits = [water_quality, soil_erosion]

    # Check if any DataFrame in benefits is empty and fill with zeros if so
    if any(df.empty for df in benefits):
        shape = benefits[0].shape
        benefits = [
            pd.DataFrame(np.zeros(shape)) if df.empty else df for df in benefits
        ]
    water_quality, soil_erosion = benefits

    # Store slope, burn severity, and hillslope ID values
    # slope = data['slope'].values
    # burn_severity = data['Burn severity'].values
    hillslope = data["wepp_id"].values

    # Calculate the sediment yield reduction needed for each hillslope to meet the threshold
    # If the sediment yield post-fire is below the threshold, then no reduction is needed (
    sediment_yield_reduction_thresholds = data["Sdyd post-fire"] - sdyd_threshold
    sediment_yield_reduction_thresholds = sediment_yield_reduction_thresholds.clip(
        lower=0
    )

    # store the number of hillslopes and treatments as variables
    num_sites = len(data)
    num_treatments = len(treatments)

    # convert and store the cost of treatment on each hillslope for each treatment type
    # cost is in $/acre, area is in hectares, so we need to convert
    treatment_cost_vectors = {
        treatment: data["area"] * cost * quant
        for treatment, cost, quant in zip(
            treatments, treatment_cost, treatment_quantity
        )
    }

    # Define the LP model variables
    # x[t][i] is a binary variable that indicates whether treatment t is applied to site i
    # B[t] is a binary variable that indicates whether treatment t was used thus applying any fixed costs related to treatment t
    model_primary = LpProblem("Select_Sites", LpMinimize)
    x = {
        t: [LpVariable(f"x_{t}_{i}", 0, 1, cat="Binary") for i in range(num_sites)]
        for t in treatments
    }

    B = {t: LpVariable(f"B_{t}", 0, 1, cat="Binary") for t in treatments}

    # Define Objective function: Minimize cost(treatment cost + fixed cost)
    model_primary += sum(
        x[t][i] * treatment_cost_vectors[t][i]
        for t in treatments
        for i in range(num_sites)
    ) + sum(B[t] * fixed_cost[n] for n, t in enumerate(treatments))

    # Constraints
    # Constraint 1: One treatment per hillslope
    for i in range(num_sites):
        model_primary += sum(x[t][i] for t in treatments) <= 1

    # Constraint 2: Fixed cost constraint linking (if a treatment is applied, the fixed cost is incurred)
    for t in treatments:
        for i in range(num_sites):
            model_primary += B[t] >= x[t][i]

    # Constraint 3: The model must select hillslopes and treatments that reduce sediment discharge to meet the user defined threshold
    model_primary += (
        sum(
            x[t][i] * water_quality.iloc[:, n].values[i]
            for n, t in enumerate(treatments)
            for i in range(num_sites)
        )
        >= Sddc_reduction_threshold
    )
    # Constraint 4: Per-hillslope sediment yield (Sdyd) threshold
    for i in range(num_sites):
        if max(soil_erosion.iloc[i, :]) > sediment_yield_reduction_thresholds[i]:
            model_primary += (
                sum(
                    x[t][i] * soil_erosion.iloc[:, n].values[i]
                    for n, t in enumerate(treatments)
                )
                >= sediment_yield_reduction_thresholds[i]
            )
        # Ensure the most effective treatment is selected if no treatment can reduce Sdyd below threshold
        else:
            model_primary += sum(
                x[t][i] * soil_erosion.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
            ) == max(soil_erosion.iloc[i, :])

    # Feasibility check
    try:
        status = model_primary.solve()
        if LpStatus[model_primary.status] != "Optimal":
            print(
                "Warning: No optimal solution found for given thresholds. Second best solution will be returned"
            )
            # Second best solution
            # The second model maximizes sediment discharge reduction while meeting constraints 1 2 and 4 of the first model.
            model_secondary = LpProblem("Select_Sites_Secondary", LpMaximize)
            x_2 = {
                t: [
                    LpVariable(f"x_2_{t}_{i}", 0, 1, cat="Binary")
                    for i in range(num_sites)
                ]
                for t in treatments
            }

            B_2 = {t: LpVariable(f"B_2_{t}", 0, 1, cat="Binary") for t in treatments}

            # Objective function: Maximize the total sediment discharge reduction
            model_secondary += sum(
                x_2[t][i] * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            # Constraint 1: One treatment per hillslope
            for i in range(num_sites):
                model_secondary += sum(x_2[t][i] for t in treatments) == 1

            # Constraint 2: Fixed cost constraint linking (if a treatment is applied, the fixed cost is incurred)
            for t in treatments:
                for i in range(num_sites):
                    model_secondary += B_2[t] >= x_2[t][i]

            # Constraint 3: Per-hillslope sediment yield (Sdyd) threshold
            for i in range(num_sites):
                if (
                    max(soil_erosion.iloc[i, :])
                    > sediment_yield_reduction_thresholds[i]
                ):
                    model_secondary += (
                        sum(
                            x_2[t][i] * soil_erosion.iloc[:, n].values[i]
                            for n, t in enumerate(treatments)
                        )
                        >= sediment_yield_reduction_thresholds[i]
                    )
                # Ensure the most effective treatment is selected if no treatment can reduce Sdyd below threshold
                else:
                    model_secondary += sum(
                        x_2[t][i] * soil_erosion.iloc[:, n].values[i]
                        for n, t in enumerate(treatments)
                    ) == max(soil_erosion.iloc[i, :])

            # Secondary model feasibility check
            status_secondary = model_secondary.solve()
            if LpStatus[model_secondary.status] != "Optimal":
                print("Warning: No second best solution found for given thresholds")
                return None
            # Outputs for the second best solution
            # Selected sites based on the selected treatments
            selected_sites = [
                [i for i in range(num_sites) if x_2[t][i].varValue == 1]
                for t in treatments
            ]
            selected = [
                i
                for t in treatments
                for i in range(num_sites)
                if x_2[t][i].varValue == 1
            ]

            # Selected hillslopes based on the selected sites
            selected_hillslopes = [hillslope[i] for i in selected]

            # The selected hillslopes grouped by treatment
            treatment_hillslopes = []
            for i in range(len(selected_sites)):
                treatment_hillslopes.append(hillslope[selected_sites[i]].tolist())

            # The total cost of the selected hillslopes
            total_cost = sum(
                treatment_cost_vectors[t][i]
                for n, t in enumerate(treatments)
                for i in selected_sites[n]
            )

            # The total fixed cost of the selected hillslopes
            total_fixed_cost = sum(
                B_2[t].varValue * fixed_cost[n] for n, t in enumerate(treatments)
            )

            # Total sediment discharge reduction as a result of the selected treatments
            total_Sddc_reduction = sum(
                x_2[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )

            # Final sediment discharge after treatment
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            # create a list that contains the wepp_id and the sediment yield of every hillslope after treatment or post-fire if no treatment was applied
            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x[t][i].varValue == 1:
                        hillslope = data["wepp_id"][i]
                        sdyd_value = data[f"Sdyd post-treat {t}"][i]
                        hillslopes_sdyd.append([hillslope, sdyd_value])
            for i in range(num_sites):
                if all(x[t][i].varValue == 0 for t in treatments):
                    hillslope = data["wepp_id"][i]
                    sdyd_value = data["Sdyd post-fire"][i]
                    hillslopes_sdyd.append([hillslope, sdyd_value])
            sdyd_df = pd.DataFrame(hillslopes_sdyd, columns=["wepp_id", "final_Sdyd"])
            untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold]

            # add back in the hillslopes that were not included in the optimization because they were filtered out by slope or burn severity
            missing_hillslopes = all_data[~all_data["wepp_id"].isin(data["wepp_id"])]
            if not missing_hillslopes.empty:
                missing_sdyd = missing_hillslopes[["wepp_id", "Sdyd post-fire"]].rename(
                    columns={"Sdyd post-fire": "final_Sdyd"}
                )
                sdyd_df = pd.concat([sdyd_df, missing_sdyd], ignore_index=True)

            sdyd_df = sdyd_df.sort_values(by="wepp_id").reset_index(drop=True)

        else:
            print("Optimal solution found")
            # Outputs

            selected_sites = [
                [i for i in range(num_sites) if x[t][i].varValue == 1]
                for t in treatments
            ]
            selected = [
                i for t in treatments for i in range(num_sites) if x[t][i].varValue == 1
            ]

            # Selected hillslopes based on the selected sites
            selected_hillslopes = [hillslope[i] for i in selected]

            # The selected hillslopes grouped by treatment
            treatment_hillslopes = []
            for i in range(len(selected_sites)):
                treatment_hillslopes.append(hillslope[selected_sites[i]].tolist())

            # the total cost of the selected hillslopes
            # treatment_cost_vectors[t][i] is the cost of treatment t on site i
            total_cost = sum(
                treatment_cost_vectors[t][i]
                for n, t in enumerate(treatments)
                for i in selected_sites[n]
            )

            # the total fixed cost of the selected hillslopes
            # B[t].varValue is 1 if treatment t was used, 0 otherwise
            total_fixed_cost = sum(
                B[t].varValue * fixed_cost[n] for n, t in enumerate(treatments)
            )

            # total_sddc is the total sediment discharge of the selected hillslopes
            total_Sddc_reduction = sum(
                x[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            # create a list that contains the wepp_id and the sediment yield of every hillslope after treatment or post-fire if no treatment was applied
            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x[t][i].varValue == 1:
                        hillslope = data["wepp_id"][i]
                        sdyd_value = data[f"Sdyd post-treat {t}"][i]
                        hillslopes_sdyd.append([hillslope, sdyd_value])
            for i in range(num_sites):
                if all(x[t][i].varValue == 0 for t in treatments):
                    hillslope = data["wepp_id"][i]
                    sdyd_value = data["Sdyd post-fire"][i]
                    hillslopes_sdyd.append([hillslope, sdyd_value])
            sdyd_df = pd.DataFrame(hillslopes_sdyd, columns=["wepp_id", "final_Sdyd"])
            untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold]

            # add back in the hillslopes that were not included in the optimization because they were filtered out by slope or burn severity
            missing_hillslopes = all_data[~all_data["wepp_id"].isin(data["wepp_id"])]
            if not missing_hillslopes.empty:
                missing_sdyd = missing_hillslopes[["wepp_id", "Sdyd post-fire"]].rename(
                    columns={"Sdyd post-fire": "final_Sdyd"}
                )
                sdyd_df = pd.concat([sdyd_df, missing_sdyd], ignore_index=True)

            sdyd_df = sdyd_df.sort_values(by="wepp_id").reset_index(drop=True)

            x = np.array(x)

    except PulpSolverError:
        print("Solver failed!")
        return None

    return (
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

    # return selected_hillslopes, treatment_hillslopes, untreatable_info, untreatable_sdyd, hillslopes_sdyd, total_cost, total_fixed_cost


def path_data_ag(hillslope_data, outlet_data, hillslope_char_data):
    """
    Function that does the following:
      Checks for missing values, empty files, correct column names, and correct data types.
      Calculates and adds the reduction in sediment yield and NTU for each hillslope.
      Checks the Simplifying assumption is met (i.e., the sum of the outlet sediment data attributed to each hillslope is >= total outlet sediment)
      Imports and aggregates the hillslope data, outlet data, and hillslope characteristics data into a single dataframe final_data

    Parameters:
    hillslope_data (str): Path to the hillslope data file.
    outlet_data (str): Path to the outlet data file.
    hillslope_char_data (str): Path to the hillslope characteristics data file.

    Returns: final_data (pd.DataFrame): Dataframe containing the aggregated data.
    """

    # Load the data
    hillslope_data = pd.read_csv(hillslope_data)
    outlet_data = pd.read_csv(outlet_data)
    hillslope_char_data = pd.read_csv(hillslope_char_data)

    # Check for empty files
    if hillslope_data.empty:
        raise ValueError("Hillslope data file is empty.")
    if outlet_data.empty:
        raise ValueError("Outlet data file is empty.")
    if hillslope_char_data.empty:
        raise ValueError("Hillslope characteristics data file is empty.")

    # Check for correct column names
    required_hillslope_columns = [
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
    ]
    required_outlet_data_columns = [
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
    ]
    required_hillslope_char_columns = [
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
    ]

    if not all(col in hillslope_data.columns for col in required_hillslope_columns):
        raise ValueError("Hillslope data file is missing required columns.")
    if not all(col in outlet_data.columns for col in required_outlet_data_columns):
        raise ValueError("Outlet data file is missing required columns.")
    if not all(
        col in hillslope_char_data.columns for col in required_hillslope_char_columns
    ):
        raise ValueError(
            "Hillslope characteristics data file is missing required columns."
        )

    # Check for missing values
    if hillslope_data.isnull().values.any():
        raise ValueError("Missing values found in hillslope data.")
    if outlet_data[["v", "control_v"]].isnull().values.any():
        raise ValueError("Missing values found in outlet data.")
    if hillslope_char_data.isnull().values.any():
        raise ValueError("Missing values found in hillslope characteristics data.")

    # combine all data into a single dataframe
    hillslope_char_data.drop(columns=["topaz_id"], inplace=True)

    out_mulch_60 = outlet_data.loc[
        (outlet_data["key"] == "Avg. Ann. sediment discharge from outlet")
        & (outlet_data["contrast"].str.endswith("mulch_60_sbs_map"))
    ].reset_index(drop=True)
    out_mulch_30 = outlet_data.loc[
        (outlet_data["key"] == "Avg. Ann. sediment discharge from outlet")
        & (outlet_data["contrast"].str.endswith("mulch_30_sbs_map"))
    ].reset_index(drop=True)
    out_mulch_15 = outlet_data.loc[
        (outlet_data["key"] == "Avg. Ann. sediment discharge from outlet")
        & (outlet_data["contrast"].str.endswith("mulch_15_sbs_map"))
    ].reset_index(drop=True)

    mulch_15 = hillslope_data[
        hillslope_data["scenario"] == "mulch_15_sbs_map"
    ].reset_index(drop=True)
    mulch_30 = hillslope_data[
        hillslope_data["scenario"] == "mulch_30_sbs_map"
    ].reset_index(drop=True)
    mulch_60 = hillslope_data[
        hillslope_data["scenario"] == "mulch_60_sbs_map"
    ].reset_index(drop=True)
    sbs_map = hillslope_data[hillslope_data["scenario"] == "sbs_map"].reset_index(
        drop=True
    )
    undisturbed = hillslope_data[
        hillslope_data["scenario"] == "undisturbed"
    ].reset_index(drop=True)

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

    # data_piv['NTU post-treat None'] = data_piv['NTU post-fire']
    # data_piv['Sdyd post-treat None'] = data_piv['Sdyd post-fire']

    # NTU_reduction_none = data_piv['NTU post-fire'] - data_piv['NTU post-treat None']
    Sddc_reduction_15 = (
        data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 0.5 tons/acre"]
    )
    Sddc_reduction_30 = (
        data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 1 tons/acre"]
    )
    Sddc_reduction_60 = (
        data_piv["Sddc post-fire"] - data_piv["Sddc post-treat 2 tons/acre"]
    )

    # Sdyd_reduction_none = data_piv['Sdyd post-fire'] - data_piv['Sdyd post-treat None']
    Sdyd_reduction_15 = (
        data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 0.5 tons/acre"]
    )
    Sdyd_reduction_30 = (
        data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 1 tons/acre"]
    )
    Sdyd_reduction_60 = (
        data_piv["Sdyd post-fire"] - data_piv["Sdyd post-treat 2 tons/acre"]
    )

    ntu_reduction_15 = (
        data_piv["NTU post-fire"] - data_piv["NTU post-treat 0.5 tons/acre"]
    )
    ntu_reduction_30 = (
        data_piv["NTU post-fire"] - data_piv["NTU post-treat 1 tons/acre"]
    )
    ntu_reduction_60 = (
        data_piv["NTU post-fire"] - data_piv["NTU post-treat 2 tons/acre"]
    )

    # data_piv['NTU reduction none'] = NTU_reduction_none
    data_piv["Sddc reduction 0.5 tons/acre"] = Sddc_reduction_15
    data_piv["Sddc reduction 1 tons/acre"] = Sddc_reduction_30
    data_piv["Sddc reduction 2 tons/acre"] = Sddc_reduction_60

    # data_piv['Sdyd reduction none'] = Sdyd_reduction_none
    data_piv["Sdyd reduction 0.5 tons/acre"] = Sdyd_reduction_15
    data_piv["Sdyd reduction 1 tons/acre"] = Sdyd_reduction_30
    data_piv["Sdyd reduction 2 tons/acre"] = Sdyd_reduction_60

    data_piv["NTU reduction 0.5 tons/acre"] = ntu_reduction_15
    data_piv["NTU reduction 1 tons/acre"] = ntu_reduction_30
    data_piv["NTU reduction 2 tons/acre"] = ntu_reduction_60

    # convert area from sqm to hectares
    data_piv["area"] = data_piv["area"] * 0.0001

    # convert landuse to integers
    data_piv["Landuse"] = data_piv["Landuse"].astype(int)

    # create a severity column based on landuse
    high_severity = [105, 119, 129]
    mod_severity = [118, 120, 130]
    low_severity = [106, 121, 131]
    data_piv["Burn severity"] = "NaN"
    for i in range(len(data_piv)):
        if data_piv["Landuse"][i] in high_severity:
            data_piv.at[i, "Burn severity"] = "High"
        elif data_piv["Landuse"][i] in mod_severity:
            data_piv.at[i, "Burn severity"] = "Moderate"
        elif data_piv["Landuse"][i] in low_severity:
            data_piv.at[i, "Burn severity"] = "Low"

    # slope to degrees
    data_piv["slope_deg"] = np.degrees(np.arctan(data_piv["slope_scalar"]))
    # drop all rows that contain a NaN value
    final_data = data_piv.dropna()
    final_data.reset_index(drop=True, inplace=True)

    return final_data
