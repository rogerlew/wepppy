#!/usr/bin/env python3
"""Summarize area-weighted Stevens Canyon hillslope water balances."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


ROOT = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
HERE = Path(__file__).resolve().parent
SCENARIOS = ("burned", "undisturbed", "high_severity")
FLUXES = ("Q", "latqcc", "Dp", "Ep", "Es", "Er")
COLUMNS = ("ofe", "day", "year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
           "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water",
           "snow_water", "QOFE", "tile", "irrigation", "area",
           "soil_water_total", "profile_depth", "porosity_capacity",
           "field_capacity", "wilting_point")
AREAS_HA = {
    49: 22.50, 50: 80.10, 51: 140.22, 52: 210.33, 53: 81.90,
    54: 64.71, 55: 73.44, 56: 82.62, 57: 176.94, 58: 256.68,
    59: 83.07, 60: 2.34, 61: 4.68,
}
REACHES = {169: (59, 60, 61), 172: tuple(range(51, 59)), 173: tuple(range(49, 62))}
WINDOWS = {
    "day203": lambda d: (d["year"] == 34) & (d["day"] == 203),
    "prior7": lambda d: (d["year"] == 34) & (d["day"] >= 196) & (d["day"] <= 202),
    "prior30": lambda d: (d["year"] == 34) & (d["day"] >= 173) & (d["day"] <= 202),
    "year34": lambda d: d["year"] == 34,
}


def read_wat(path: Path) -> dict[str, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(COLUMNS):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    values = np.asarray(rows)
    if values.shape != (36_525, len(COLUMNS)) or not np.isfinite(values).all():
        raise ValueError(f"invalid water-balance table: {path} {values.shape}")
    return {name: values[:, index] for index, name in enumerate(COLUMNS)}


def aggregate(hills: tuple[int, ...], scenario_data: dict[int, dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    weights = np.asarray([AREAS_HA[hill] for hill in hills], dtype=float)
    weights /= weights.sum()
    result = {"day": scenario_data[hills[0]]["day"], "year": scenario_data[hills[0]]["year"]}
    for field in ("P", "RM", *FLUXES, "soil_water_total", "porosity_capacity"):
        result[field] = np.average(
            np.vstack([scenario_data[hill][field] for hill in hills]), axis=0, weights=weights
        )
    return result


def fmt_fluxes(data: dict[str, np.ndarray], mask: np.ndarray) -> str:
    return ", ".join(f"{flux}={data[flux][mask].sum():.2f}" for flux in FLUXES)


def main() -> None:
    source = {
        scenario: {
            hill: read_wat(ROOT / scenario / "wepp" / "output" / f"H{hill}.wat.dat")
            for hill in AREAS_HA
        }
        for scenario in SCENARIOS
    }
    data = {
        reach: {scenario: aggregate(hills, source[scenario]) for scenario in SCENARIOS}
        for reach, hills in REACHES.items()
    }

    csv_path = HERE / "water-balance-attribution.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("reach", "scenario", "window", "flux", "value_mm"))
        for reach, scenarios in data.items():
            for scenario, values in scenarios.items():
                for window, selector in WINDOWS.items():
                    mask = selector(values)
                    for flux in FLUXES:
                        writer.writerow((reach, scenario, window, flux, f"{values[flux][mask].sum():.6f}"))
                for flux in FLUXES:
                    writer.writerow((reach, scenario, "annual_mean_100y", flux,
                                     f"{values[flux].sum() / 100:.6f}"))

    lines = [
        "# Area-Weighted Hillslope Water-Balance Attribution", "",
        "All values are area-weighted depths in millimeters. `Q` is surface runoff;",
        "`latqcc` is lateral subsurface flow; `Dp` is deep percolation; and `Ep`,",
        "`Es`, and `Er` are plant-side, soil, and residue evaporation.", "",
        "## Focal Event and Antecedent Windows", "",
    ]
    for reach, scenarios in data.items():
        lines.extend((f"### Reach {reach}", ""))
        for window in ("day203", "prior7", "prior30"):
            lines.append(f"- **{window}:**")
            for scenario, values in scenarios.items():
                lines.append(f"  - {scenario}: {fmt_fluxes(values, WINDOWS[window](values))}.")
        lines.append("")

    lines.extend(("## Full-Record Classification", "",
                  "A runoff-excess day has undisturbed area-weighted `Q` greater than",
                  "burned `Q`; equal days are retained separately. The composite columns",
                  "are mean undisturbed-minus-burned daily differences on excess days.", "",
                  "| Reach | U > B days | B > U days | Equal days | Mean ΔQ | Mean ΔEp | Mean ΔEs | Mean Δlatqcc |",
                  "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"))
    classifications = {}
    for reach, scenarios in data.items():
        burned, undisturbed = scenarios["burned"], scenarios["undisturbed"]
        delta_q = undisturbed["Q"] - burned["Q"]
        u_mask, b_mask, equal = delta_q > 1e-9, delta_q < -1e-9, np.abs(delta_q) <= 1e-9
        classifications[reach] = (int(u_mask.sum()), int(b_mask.sum()), int(equal.sum()))
        means = {flux: float((undisturbed[flux] - burned[flux])[u_mask].mean()) for flux in FLUXES}
        lines.append(
            f"| {reach} | {u_mask.sum()} | {b_mask.sum()} | {equal.sum()} | "
            f"{means['Q']:+.3f} | {means['Ep']:+.3f} | {means['Es']:+.3f} | "
            f"{means['latqcc']:+.3f} |"
        )

    lines.extend(("", "## Annual-Mean Partition", "",
                  "| Reach | Scenario | Q | latqcc | Dp | Ep | Es | Er | Total ET |",
                  "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"))
    for reach, scenarios in data.items():
        for scenario, values in scenarios.items():
            totals = {flux: float(values[flux].sum() / 100) for flux in FLUXES}
            et = totals["Ep"] + totals["Es"] + totals["Er"]
            lines.append(f"| {reach} | {scenario} | {totals['Q']:.2f} | {totals['latqcc']:.2f} | "
                         f"{totals['Dp']:.2f} | {totals['Ep']:.2f} | {totals['Es']:.2f} | "
                         f"{totals['Er']:.2f} | {et:.2f} |")

    lines.extend(("", "## High-Severity Annual Diagnostics", "",
                  "Ratios pair each of the 100 climate years. Reach 169 is the clean",
                  "high-severity comparison because all three contributing hillslopes are",
                  "treated; reaches 172 and 173 retain their unchanged controls.", "",
                  "| Reach | Median high/undisturbed ET | P10-P90 | Median high Es/ET | Years in 0.40-0.60 ET target |",
                  "| ---: | ---: | ---: | ---: | ---: |"))
    for reach, scenarios in data.items():
        yearly = {}
        for scenario in ("undisturbed", "high_severity"):
            values = scenarios[scenario]
            yearly[scenario] = np.asarray([
                sum(values[flux][values["year"] == year].sum() for flux in ("Ep", "Es", "Er"))
                for year in range(1, 101)
            ])
        high = scenarios["high_severity"]
        high_es = np.asarray([high["Es"][high["year"] == year].sum() for year in range(1, 101)])
        ratio = yearly["high_severity"] / yearly["undisturbed"]
        es_fraction = high_es / yearly["high_severity"]
        inside = ((ratio >= 0.40) & (ratio <= 0.60)).sum()
        lines.append(f"| {reach} | {np.median(ratio):.3f} | {np.percentile(ratio, 10):.3f}-"
                     f"{np.percentile(ratio, 90):.3f} | {np.median(es_fraction):.3f} | {inside}/100 |")

    lines.extend(("", "## Interpretation", "",
                  "The daily classification diagnoses runoff production, not subdaily peak",
                  "timing. It should therefore be read alongside the channel peak-timing",
                  "analysis rather than treated as a replacement for it. Positive composite",
                  "differences show which fluxes covary with undisturbed runoff-excess days;",
                  "they do not alone prove a causal threshold.", "", "## Provenance", "",
                  f"Generated by `{Path(__file__).name}` from `{ROOT}`.",
                  "Machine-readable totals are in `water-balance-attribution.csv`."))
    (HERE / "water-balance-attribution.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {csv_path}")
    print(f"wrote {HERE / 'water-balance-attribution.md'}")
    print(classifications)


if __name__ == "__main__":
    main()
