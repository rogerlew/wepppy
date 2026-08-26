#!/usr/bin/env python3
"""Plot paired Topanga mutant sediment delivery against baseline delivery."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D


PLAN_ID = "b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de"
CENSUS = Path("/home/workdir/peakflow-topanga-census-evidence") / PLAN_ID
BASELINE = Path("/home/workdir/peakflow-phase2a-evidence/8162d509d69cb4da/baseline")
EVENT_LEDGER = CENSUS / "ledgers/event-pairs.parquet"
OUTPUT = Path(__file__).with_name("topanga-mutant-vs-baseline-erosion.png")
START_YEAR = 1980
COLORS = {"burned": "#e67e22", "undisturbed": "#238b57"}
LABELS = {"burned": "Burned", "undisturbed": "Unburned (undisturbed)"}
MARKERS = {
    ("ksat", "minus"): "v",
    ("ksat", "plus"): "^",
    ("cover", "minus"): "<",
    ("cover", "plus"): ">",
}
MUTATION_LABELS = {
    ("ksat", "minus"): "Ksat -1%",
    ("ksat", "plus"): "Ksat +1%",
    ("cover", "minus"): "Cover -0.01",
    ("cover", "plus"): "Cover +0.01",
}
EBE_COLUMNS = [
    "month_day",
    "month",
    "simulation_year",
    "precip_mm",
    "runoff_mm",
    "interrill_detachment_kg_m2",
    "average_detachment_kg_m2",
    "maximum_detachment_kg_m2",
    "maximum_detachment_point_m",
    "average_deposition_kg_m2",
    "maximum_deposition_kg_m2",
    "maximum_deposition_point_m",
    "sediment_delivery_kg_m",
    "enrichment_ratio",
]


def read_event_delivery(path: Path) -> pd.DataFrame:
    """Read WEPP event sediment delivery and return calendar event keys."""
    frame = pd.read_csv(
        path,
        sep=r"\s+",
        skiprows=3,
        names=EBE_COLUMNS,
        usecols=["month_day", "month", "simulation_year", "sediment_delivery_kg_m"],
        dtype=float,
    )
    frame["year"] = START_YEAR + frame.simulation_year.astype(int) - 1
    dates = pd.to_datetime(
        {"year": frame.year, "month": frame.month, "day": frame.month_day},
        errors="raise",
    )
    frame["day"] = dates.dt.dayofyear
    return frame[["year", "day", "sediment_delivery_kg_m"]]


def build_plot_frame() -> tuple[pd.DataFrame, dict[str, int]]:
    """Pair baseline and mutant EBE delivery using census trial identities."""
    trials = pd.read_parquet(
        EVENT_LEDGER,
        columns=["scenario", "hillslope_id", "family", "direction"],
    ).drop_duplicates()
    baseline_cache: dict[tuple[str, int], pd.DataFrame] = {}
    pieces: list[pd.DataFrame] = []
    for trial in trials.itertuples(index=False):
        key = (trial.scenario, trial.hillslope_id)
        if key not in baseline_cache:
            baseline_path = (
                BASELINE
                / trial.scenario
                / f"h{trial.hillslope_id:03d}"
                / "output"
                / f"H{trial.hillslope_id}.ebe.dat"
            )
            baseline_cache[key] = read_event_delivery(baseline_path).rename(
                columns={"sediment_delivery_kg_m": "baseline_kg_m"}
            )
        mutant_path = (
            CENSUS
            / trial.scenario
            / f"h{trial.hillslope_id}"
            / f"{trial.family}-{trial.direction}"
            / "output"
            / f"H{trial.hillslope_id}.ebe.dat"
        )
        mutant = read_event_delivery(mutant_path).rename(
            columns={"sediment_delivery_kg_m": "mutant_kg_m"}
        )
        paired = baseline_cache[key].merge(mutant, on=["year", "day"], how="outer")
        paired["scenario"] = trial.scenario
        paired["family"] = trial.family
        paired["direction"] = trial.direction
        pieces.append(paired)

    all_events = pd.concat(pieces, ignore_index=True)
    baseline_positive = all_events.baseline_kg_m.fillna(0).gt(0)
    mutant_positive = all_events.mutant_kg_m.fillna(0).gt(0)
    counts = {
        "all": len(all_events),
        "paired_positive": int((baseline_positive & mutant_positive).sum()),
        "baseline_only_positive": int((baseline_positive & ~mutant_positive).sum()),
        "mutant_only_positive": int((~baseline_positive & mutant_positive).sum()),
        "neither_positive": int((~baseline_positive & ~mutant_positive).sum()),
    }
    return all_events.loc[baseline_positive & mutant_positive].copy(), counts


def congruent_mask(subset: pd.DataFrame) -> pd.Series:
    """Classify inverse parameter/delivery responses as congruent."""
    delivery_increased = subset.mutant_kg_m.gt(subset.baseline_kg_m)
    delivery_decreased = subset.mutant_kg_m.lt(subset.baseline_kg_m)
    return (
        subset.direction.eq("plus") & delivery_decreased
    ) | (
        subset.direction.eq("minus") & delivery_increased
    )


def response_edgecolors(subset: pd.DataFrame, color: str) -> np.ndarray:
    opacity = np.where(congruent_mask(subset), 0.2, 0.6)
    colors = np.tile(to_rgba(color), (len(subset), 1))
    colors[:, 3] = opacity
    return colors


def main() -> None:
    frame, counts = build_plot_frame()
    values = frame[["baseline_kg_m", "mutant_kg_m"]].to_numpy()
    lower = 10 ** np.floor(np.log10(values.min()))
    upper = 10 ** np.ceil(np.log10(values.max()))
    limits = np.array([lower, upper])

    figure, axes = plt.subplots(1, 2, figsize=(15.6, 7.4), dpi=180, sharex=True, sharey=True)
    figure.patch.set_facecolor("#fbfaf7")
    for axis, scenario in zip(axes, ("undisturbed", "burned")):
        axis.set_facecolor("#fbfaf7")
        for factor, style, width, label in (
            (2, "--", 0.9, "2x / 0.5x"),
            (0.5, "--", 0.9, None),
            (5, ":", 0.85, "5x / 0.2x"),
            (0.2, ":", 0.85, None),
        ):
            axis.plot(limits, limits * factor, color="#888888", linewidth=width,
                      linestyle=style, zorder=1, label=label)
        for mutation, marker in MARKERS.items():
            family, direction = mutation
            subset = frame.loc[
                frame.scenario.eq(scenario)
                & frame.family.eq(family)
                & frame.direction.eq(direction)
            ]
            axis.scatter(
                subset.baseline_kg_m,
                subset.mutant_kg_m,
                marker=marker,
                s=10,
                linewidths=0.45,
                facecolors="none",
                edgecolors=response_edgecolors(subset, COLORS[scenario]),
                rasterized=True,
                zorder=2,
            )
        axis.plot(limits, limits, color="#4a4a4a", linewidth=0.7,
                  zorder=3, label="1:1")
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlim(limits)
        axis.set_ylim(limits)
        axis.set_aspect("equal", adjustable="box")
        axis.grid(which="major", color="#555555", alpha=0.13, linewidth=0.7)
        axis.grid(which="minor", color="#555555", alpha=0.045, linewidth=0.5)
        axis.set_title(
            f"{LABELS[scenario]} (n={frame.scenario.eq(scenario).sum():,})",
            color=COLORS[scenario], fontsize=12, weight="semibold", pad=9,
        )
        axis.set_xlabel("Baseline event sediment delivery (kg/m)", fontsize=11, labelpad=8)
        for spine in axis.spines.values():
            spine.set_color("#777777")
            spine.set_alpha(0.35)

    figure.suptitle(
        "Topanga Paired Positive Event Sediment Delivery: Mutant versus Baseline",
        fontsize=15.2,
        weight="semibold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.922,
        "Congruent response α=0.2; incongruent α=0.6 (Ksat and cover inverse)",
        ha="center",
        fontsize=10.2,
        color="#555555",
    )
    axes[0].set_ylabel("Mutant event sediment delivery (kg/m)", fontsize=11, labelpad=8)
    handles, labels = axes[0].get_legend_handles_labels()
    handles.extend(
        Line2D([], [], marker="x", linestyle="none", color=COLORS[scenario],
               alpha=0.75,
               label=f"{LABELS[scenario]} (n={frame.scenario.eq(scenario).sum():,})")
        for scenario in ("undisturbed", "burned")
    )
    handles.extend(
        Line2D([], [], marker=marker, linestyle="none", markerfacecolor="none",
               markeredgecolor="#444444", label=MUTATION_LABELS[mutation])
        for mutation, marker in MARKERS.items()
    )
    handles.extend([
        Line2D([], [], marker="x", linestyle="none", color="#444444", alpha=0.2,
               label="Congruent: parameter / delivery opposite (α=0.2)"),
        Line2D([], [], marker="x", linestyle="none", color="#444444", alpha=0.6,
               label="Incongruent: same direction or unchanged (α=0.6)"),
    ])
    labels.extend(handle.get_label() for handle in handles[len(labels):])
    axes[1].legend(handles=handles, labels=labels, loc="upper left",
                bbox_to_anchor=(1.04, 1.0), borderaxespad=0.0, frameon=True,
                facecolor="#fbfaf7", framealpha=0.94, edgecolor="#bbbbbb",
                fontsize=9.5)
    figure.text(
        0.99,
        0.012,
        "Source: frozen Phase 2A baseline and Topanga census WEPP event outputs",
        ha="right",
        fontsize=8.5,
        color="#666666",
    )
    figure.subplots_adjust(left=0.07, right=0.76, bottom=0.12, top=0.86, wspace=0.10)
    figure.savefig(OUTPUT, dpi=220, bbox_inches="tight", facecolor=figure.get_facecolor())

    ratios = frame.mutant_kg_m / frame.baseline_kg_m
    print(f"plotted={len(frame):,}")
    print(f"counts={counts}")
    print(f"outside_2x={((ratios < 0.5) | (ratios > 2)).sum():,}")
    print(f"outside_5x={((ratios < 0.2) | (ratios > 5)).sum():,}")
    print(f"congruent={congruent_mask(frame).sum():,}")
    for family in ("ksat", "cover"):
        subset = frame.loc[frame.family.eq(family)]
        ratio = subset.mutant_kg_m / subset.baseline_kg_m
        print(
            family,
            f"n={len(subset):,}",
            f"congruent={congruent_mask(subset).sum():,}",
            f"outside_2x={((ratio < 0.5) | (ratio > 2)).sum():,}",
            f"outside_5x={((ratio < 0.2) | (ratio > 5)).sum():,}",
        )


if __name__ == "__main__":
    main()
