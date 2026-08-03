#!/usr/bin/env python3
"""Plot three-scenario year-34 daily water fluxes from hillslope replays."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
DOC_ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = DOC_ROOT / "figures" / "hillslope-water-fluxes"
FLUXES = ("Q", "latqcc", "Dp", "Ep", "Es", "Er")
LABELS = ("Surface runoff", "Lateral subsurface", "Deep percolation",
          "Plant transpiration", "Soil evaporation", "Residue evaporation")
COLORS = ("#2166ac", "#67a9cf", "#74c476", "#238b45", "#fdae61", "#d73027")
COLUMNS = ("ofe", "day", "year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
           "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water",
           "snow_water", "QOFE", "tile", "irrigation", "area",
           "soil_water_total", "profile_depth", "porosity_capacity",
           "field_capacity", "wilting_point")


def read_water_balance(path: Path) -> dict[str, np.ndarray]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(COLUMNS):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    data = np.asarray(rows, dtype=float)
    if data.shape != (36_525, len(COLUMNS)):
        raise ValueError(f"{path}: expected 36525 daily rows, found {data.shape}")
    result = {name: data[:, index] for index, name in enumerate(COLUMNS)}
    calendar = np.column_stack((result["year"], result["day"]))
    if np.unique(calendar, axis=0).shape[0] != 36_525:
        raise ValueError(f"{path}: duplicate daily calendar keys")
    if not np.isfinite(data).all():
        raise ValueError(f"{path}: non-finite value")
    return result


def total_text(data: dict[str, np.ndarray], start: int, end: int) -> str:
    mask = (data["year"] == 34) & (data["day"] >= start) & (data["day"] <= end)
    return ", ".join(f"{name}={data[name][mask].sum():.2f}" for name in FLUXES)


def differences(burned: dict[str, np.ndarray], undisturbed: dict[str, np.ndarray],
                start: int, end: int) -> dict[str, float]:
    def sums(data: dict[str, np.ndarray]) -> dict[str, float]:
        mask = (data["year"] == 34) & (data["day"] >= start) & (data["day"] <= end)
        return {name: float(data[name][mask].sum()) for name in FLUXES}
    burned_sums, undisturbed_sums = sums(burned), sums(undisturbed)
    return {name: undisturbed_sums[name] - burned_sums[name] for name in FLUXES}


def write_sidecar(hill: int, burned: dict[str, np.ndarray],
                  undisturbed: dict[str, np.ndarray],
                  high_severity: dict[str, np.ndarray]) -> None:
    path = FIGURE_DIR / f"h{hill}-year34-water-fluxes.md"
    event_b = total_text(burned, 203, 203)
    event_u = total_text(undisturbed, 203, 203)
    event_h = total_text(high_severity, 203, 203)
    seven_b = total_text(burned, 196, 202)
    seven_u = total_text(undisturbed, 196, 202)
    seven_h = total_text(high_severity, 196, 202)
    thirty_b = total_text(burned, 173, 202)
    thirty_u = total_text(undisturbed, 173, 202)
    thirty_h = total_text(high_severity, 173, 202)
    year_b = total_text(burned, 1, 365)
    year_u = total_text(undisturbed, 1, 365)
    year_h = total_text(high_severity, 1, 365)
    event_delta = differences(burned, undisturbed, 203, 203)
    year_delta = differences(burned, undisturbed, 1, 365)
    event_ranked = sorted(event_delta.items(), key=lambda item: abs(item[1]), reverse=True)
    year_ranked = sorted(year_delta.items(), key=lambda item: abs(item[1]), reverse=True)
    event_signal = ", ".join(f"{name}={value:+.2f} mm" for name, value in event_ranked[:3])
    year_signal = ", ".join(f"{name}={value:+.2f} mm" for name, value in year_ranked[:3])
    path.write_text(f"""# H{hill}: Simulation-Year-34 Water Fluxes

![H{hill} paired water fluxes](h{hill}-year34-water-fluxes.png)

## Caption

Daily outgoing water fluxes for burned, undisturbed, and canonical high-severity
H{hill}. Areas are
stacked in millimeters over the hillslope. Input lines show precipitation and
rainfall plus irrigation plus snowmelt. All three panels use the same axes; the
vertical line marks Julian day 203.

## Flux Totals

Values below are millimeters and use `Q`, `latqcc`, `Dp`, `Ep`, `Es`, and `Er`
for surface runoff, lateral subsurface flow, deep percolation, plant
transpiration, soil evaporation, and residue evaporation.

- Day 203 burned: {event_b}.
- Day 203 undisturbed: {event_u}.
- Day 203 high severity: {event_h}.
- Days 196-202 burned: {seven_b}.
- Days 196-202 undisturbed: {seven_u}.
- Days 196-202 high severity: {seven_h}.
- Days 173-202 burned: {thirty_b}.
- Days 173-202 undisturbed: {thirty_u}.
- Days 173-202 high severity: {thirty_h}.
- Year 34 burned: {year_b}.
- Year 34 undisturbed: {year_u}.
- Year 34 high severity: {year_h}.

## Interpretation and Limitations

The largest undisturbed-minus-burned differences on day 203 are {event_signal}.
The largest year-34 differences are {year_signal}. Positive values indicate a
larger undisturbed flux. These rankings identify the dominant accounting
contrasts for H{hill}; they do not establish that the largest annual component
controls the event peak.

The common scale supports direct visual comparison. The stack describes daily
water partitioning but does not by itself prove causation or determine channel
peak synchronization. `RM` can lag `P` where snow stores and later releases
water. Fluxes are daily totals, so subdaily peak timing is not represented.

## Source Data

- `{ROOT}/burned/wepp/output/H{hill}.wat.dat`
- `{ROOT}/undisturbed/wepp/output/H{hill}.wat.dat`
- `{ROOT}/high_severity/wepp/output/H{hill}.wat.dat`
""", encoding="utf-8")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    for hill in range(49, 62):
        scenarios = {
            name: read_water_balance(ROOT / name / "wepp" / "output" / f"H{hill}.wat.dat")
            for name in ("burned", "undisturbed", "high_severity")
        }
        reference_calendar = np.column_stack(
            (scenarios["burned"]["year"], scenarios["burned"]["day"])
        )
        for name, data in scenarios.items():
            calendar = np.column_stack((data["year"], data["day"]))
            if not np.array_equal(reference_calendar, calendar):
                raise ValueError(f"H{hill}: {name} calendar differs")
        year = {name: {key: values[data["year"] == 34] for key, values in data.items()}
                for name, data in scenarios.items()}
        ymax = max(sum(year[name][key] for key in FLUXES).max() for name in year) * 1.08
        input_max = max(year[name]["P"].max() for name in year) * 1.08
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, sharey=True)
        input_axes = []
        for ax, name, title in zip(
            axes,
            ("burned", "undisturbed", "high_severity"),
            ("Burned", "Undisturbed", "High severity"),
            strict=True,
        ):
            data = year[name]
            ax.stackplot(data["day"], *(data[key] for key in FLUXES),
                         labels=LABELS, colors=COLORS, alpha=0.9)
            input_ax = ax.twinx()
            input_axes.append(input_ax)
            input_ax.plot(data["day"], data["P"], color="black", lw=0.8,
                          label="Precipitation")
            input_ax.plot(data["day"], data["RM"], color="#984ea3", lw=0.8,
                          ls="--", label="Rain + melt")
            input_ax.set_ylim(0, input_max)
            input_ax.set_ylabel("Input (mm/day)")
            ax.axvline(203, color="#7f0000", ls=":", lw=1.2)
            ax.set_ylim(0, ymax)
            ax.set_ylabel("Outgoing flux (mm/day)")
            ax.set_title(title, loc="left", weight="bold")
            ax.grid(axis="y", alpha=0.2)
        axes[-1].set_xlabel("Julian day, simulation year 34")
        handles, labels = axes[0].get_legend_handles_labels()
        input_handles, input_labels = input_axes[0].get_legend_handles_labels()
        fig.legend(handles + input_handles, labels + input_labels, ncol=4,
                   loc="lower center", frameon=False)
        fig.suptitle(f"H{hill} daily water-flux partitioning", weight="bold")
        fig.tight_layout(rect=(0, 0.1, 1, 0.96))
        fig.savefig(FIGURE_DIR / f"h{hill}-year34-water-fluxes.png", dpi=180)
        plt.close(fig)
        write_sidecar(
            hill,
            scenarios["burned"],
            scenarios["undisturbed"],
            scenarios["high_severity"],
        )
        generated += 1
    links = "\n".join(
        f"- [H{hill}](h{hill}-year34-water-fluxes.md)"
        for hill in range(49, 62)
    )
    (FIGURE_DIR / "README.md").write_text(f"""# Hillslope Water-Flux Figures

These three-panel figures use daily hillslope outputs. Each burned,
undisturbed, and high-severity comparison shares axes and shows year 34 with Julian
day 203 marked. Outgoing fluxes are stacked; precipitation and rain-plus-melt
are separate input lines.

{links}

The 13 hillslopes are the full contributing set for WEPP_ID 173 and contain the
nested contributing sets for WEPP_IDs 169 and 172. See the individual
sidecars for focal-event, antecedent-window, and annual flux totals.
""", encoding="utf-8")
    print(f"generated {generated} figure/sidecar pairs in {FIGURE_DIR}")


if __name__ == "__main__":
    main()
