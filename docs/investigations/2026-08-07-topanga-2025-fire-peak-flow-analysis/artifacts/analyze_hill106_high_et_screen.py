#!/usr/bin/env python3
"""Summarize the Hill 106 undisturbed high-ET screening matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analyze_hill106_ksat_mutation import read_element, read_water


CASES = {
    "baseline-kcb1p20": ("baseline", 1.20),
    "baseline-kcb1p30": ("baseline", 1.30),
    "baseline-kcb1p40": ("baseline", 1.40),
    "dense-kcb1p20": ("dense", 1.20),
    "dense-kcb1p30": ("dense", 1.30),
    "dense-kcb1p40": ("dense", 1.40),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--selected-dates", type=Path, required=True)
    parser.add_argument("--selected-output", type=Path, required=True)
    args = parser.parse_args()

    summary_rows: list[dict[str, float | str]] = []
    selected = pd.read_csv(args.selected_dates, usecols=["event_date"])
    selected_dates = pd.to_datetime(selected.event_date.unique())
    selected_frame = pd.DataFrame(index=selected_dates)
    selected_frame.index.name = "event_date"

    for case, (management, kcb) in CASES.items():
        output = args.root / case / "output"
        water = read_water(output / "H106.wat.dat")
        first_year = int(water.year.min())
        element = read_element(output / "H106.element.dat", first_year)
        year_2020 = water.loc[water.year == 2020]

        summary_rows.append(
            {
                "case": case,
                "management": management,
                "kcb": kcb,
                "initial_canopy_cover": 0.70 if management == "baseline" else 0.90,
                "maximum_lai": 5.0 if management == "baseline" else 6.0,
                "runoff_2020_mm": year_2020.runoff.sum(),
                "lateral_2020_mm": year_2020.lateral.sum(),
                "combined_runoff_2020_mm": year_2020.runoff.sum() + year_2020.lateral.sum(),
                "plant_transpiration_2020_mm": year_2020.ep.sum(),
                "soil_evaporation_2020_mm": year_2020.es.sum(),
                "residue_evaporation_2020_mm": year_2020.er.sum(),
                "total_et_2020_mm": year_2020[["ep", "es", "er"]].sum().sum(),
                "mean_soil_water_2020_mm": year_2020.soil_water.mean(),
                "minimum_soil_water_2020_mm": year_2020.soil_water.min(),
                "maximum_peak_ro_mm_h": element.peak_ro.max(),
                "median_positive_peak_ro_mm_h": element.loc[element.peak_ro > 0, "peak_ro"].median(),
                "runoff_45yr_mm": water.runoff.sum(),
                "lateral_45yr_mm": water.lateral.sum(),
                "total_et_45yr_mm": water[["ep", "es", "er"]].sum().sum(),
            }
        )

        selected_frame[f"{case}_runoff_mm"] = element.runoff.reindex(selected_frame.index).fillna(0.0)
        selected_frame[f"{case}_peak_ro_mm_h"] = element.peak_ro.reindex(selected_frame.index).fillna(0.0)
        selected_frame[f"{case}_eff_int_mm_h"] = element.eff_int.reindex(selected_frame.index).fillna(0.0)
        selected_frame[f"{case}_eff_dur_h"] = element.eff_dur.reindex(selected_frame.index).fillna(0.0)
        selected_frame[f"{case}_pre_event_soil_water_mm"] = (
            water.soil_water.shift(1).reindex(selected_frame.index)
        )

    summary = pd.DataFrame(summary_rows)
    baseline_peak = selected_frame["baseline-kcb1p20_peak_ro_mm_h"]
    for case in CASES:
        selected_frame[f"{case}_peak_change_pct"] = (
            100.0
            * (selected_frame[f"{case}_peak_ro_mm_h"] - baseline_peak)
            / baseline_peak.where(baseline_peak != 0)
        )

    summary.to_csv(args.summary, index=False, float_format="%.6f")
    selected_frame.sort_index().to_csv(args.selected_output, float_format="%.6f")
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
