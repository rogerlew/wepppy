#!/usr/bin/env python3
"""Compare Hill 106 burned, Ksat-mutated burned, and undisturbed runs."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


ELEMENT_COLUMNS = [
    "ofe", "day", "month", "year", "precip", "runoff", "eff_int", "peak_ro",
    "eff_dur", "enrich", "keff", "sm", "leaf_area", "can_hgt", "can_cov",
    "int_cov", "ril_cov", "live_bio", "dead_bio", "ki", "kr", "tcrit",
    "ril_width", "sed_leave", "q_rain", "q_snow",
]

WATER_COLUMNS = [
    "ofe", "julian_day", "year", "precip", "rain_melt", "runoff", "ep", "es",
    "er", "deep_perc", "upstream_q", "subsurface_in", "lateral", "legacy_soil_water",
    "frozen_water", "snow_water", "q_ofe", "tile", "irrigation", "area",
    "soil_water", "profile_depth", "porosity_capacity", "field_capacity_store",
    "wilting_point_store", "interception_storage",
]


def parse_numeric_rows(path: Path, minimum_fields: int) -> list[list[float]]:
    rows: list[list[float]] = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) < minimum_fields:
            continue
        try:
            rows.append([float(field) for field in fields])
        except ValueError:
            continue
    return rows


def read_element(path: Path, first_calendar_year: int) -> pd.DataFrame:
    rows = parse_numeric_rows(path, 24)
    width = max(len(row) for row in rows)
    columns = ELEMENT_COLUMNS[:width]
    frame = pd.DataFrame([row[:width] for row in rows], columns=columns)
    calendar_year = first_calendar_year + frame.year.astype(int) - 1
    frame["date"] = pd.to_datetime(
        {"year": calendar_year, "month": frame.month.astype(int), "day": frame.day.astype(int)}
    )
    return frame.set_index("date")


def read_water(path: Path) -> pd.DataFrame:
    required_width = WATER_COLUMNS.index("soil_water") + 1
    rows = parse_numeric_rows(path, required_width)
    width = min(max(len(row) for row in rows), len(WATER_COLUMNS))
    frame = pd.DataFrame([row[:width] for row in rows], columns=WATER_COLUMNS[:width])
    frame["date"] = [
        date(int(year), 1, 1) + timedelta(days=int(day) - 1)
        for year, day in zip(frame.year, frame.julian_day, strict=True)
    ]
    frame["date"] = pd.to_datetime(frame.date)
    return frame.set_index("date")


def add_antecedent_metrics(events: pd.DataFrame, water: pd.DataFrame, prefix: str) -> None:
    previous = water["soil_water"].shift(1)
    events[f"{prefix}_pre_event_soil_water_mm"] = previous.reindex(events.index)
    for field in ("ep", "es", "er"):
        prior_30_days = water[field].shift(1).rolling(30, min_periods=1).sum()
        events[f"{prefix}_prior30_{field}_mm"] = prior_30_days.reindex(events.index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--burned", type=Path, required=True)
    parser.add_argument("--burned-ksat35", type=Path, required=True)
    parser.add_argument("--undisturbed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roots = {
        "burned": args.burned,
        "burned_ksat35": args.burned_ksat35,
        "undisturbed": args.undisturbed,
    }
    waters = {name: read_water(root / "output/H106.wat.dat") for name, root in roots.items()}
    elements = {
        name: read_element(
            root / "output/H106.element.dat", int(waters[name].year.min())
        )
        for name, root in roots.items()
    }

    all_dates = elements["burned"].index.union(elements["burned_ksat35"].index).union(
        elements["undisturbed"].index
    )
    events = pd.DataFrame(index=all_dates.sort_values())
    hydrology = ("precip", "runoff", "eff_int", "peak_ro", "eff_dur", "keff", "sm")
    for name, frame in elements.items():
        for field in hydrology:
            events[f"{name}_{field}"] = frame[field].reindex(events.index).fillna(0.0)
        add_antecedent_metrics(events, waters[name], name)

    events = events.loc[
        (events["burned_runoff"] > 0)
        | (events["burned_ksat35_runoff"] > 0)
        | (events["undisturbed_runoff"] > 0)
    ].copy()
    events["undisturbed_minus_burned_peak_ro"] = (
        events.undisturbed_peak_ro - events.burned_peak_ro
    )
    events["undisturbed_minus_burned_ksat35_peak_ro"] = (
        events.undisturbed_peak_ro - events.burned_ksat35_peak_ro
    )
    events["burned_ksat35_minus_burned_peak_ro"] = (
        events.burned_ksat35_peak_ro - events.burned_peak_ro
    )
    events.index.name = "event_date"
    events.to_csv(args.output, float_format="%.6f")

    for name in roots:
        print(
            name,
            f"runoff_sum_mm={waters[name].runoff.sum():.3f}",
            f"peak_max_mm_h={events[f'{name}_peak_ro'].max():.3f}",
            f"ep_sum_mm={waters[name].ep.sum():.3f}",
            f"es_sum_mm={waters[name].es.sum():.3f}",
            f"mean_soil_water_mm={waters[name].soil_water.mean():.3f}",
        )
    valid = (events.burned_peak_ro > 0) & (events.undisturbed_peak_ro > 0)
    print("paired_positive_peak_dates", int(valid.sum()))
    print(
        "undisturbed_peak_gt_burned",
        int((events.loc[valid, "undisturbed_peak_ro"] > events.loc[valid, "burned_peak_ro"]).sum()),
    )
    print(
        "undisturbed_peak_gt_burned_ksat35",
        int(
            (
                events.loc[valid, "undisturbed_peak_ro"]
                > events.loc[valid, "burned_ksat35_peak_ro"]
            ).sum()
        ),
    )
    largest = events.nlargest(12, "undisturbed_minus_burned_peak_ro")
    display = [
        "burned_runoff", "burned_peak_ro", "burned_eff_dur",
        "burned_ksat35_runoff", "burned_ksat35_peak_ro", "burned_ksat35_eff_dur",
        "undisturbed_runoff", "undisturbed_peak_ro", "undisturbed_eff_dur",
        "burned_ksat35_pre_event_soil_water_mm", "undisturbed_pre_event_soil_water_mm",
        "burned_ksat35_prior30_ep_mm", "undisturbed_prior30_ep_mm",
        "burned_ksat35_prior30_es_mm", "undisturbed_prior30_es_mm",
    ]
    print(largest[display].round(3).to_string())


if __name__ == "__main__":
    main()
