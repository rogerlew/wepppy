#!/usr/bin/env python3
"""Plot paired Topanga mutant event runoff against baseline event runoff."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D


EVIDENCE = Path(
    "/home/workdir/peakflow-topanga-census-evidence/"
    "b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de/"
    "ledgers/event-pairs.parquet"
)
OUTPUT = Path(__file__).with_name("topanga-mutant-vs-baseline-runoff.png")
RUNOFF_FLOOR_M = 1e-5
M_TO_MM = 1e3
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


def response_edgecolors(subset: pd.DataFrame, color: str) -> np.ndarray:
    """Color inverse runoff responses faintly and other responses strongly."""
    runoff_increased = subset.runoff_post_m_mutant.gt(subset.runoff_post_m_baseline)
    runoff_decreased = subset.runoff_post_m_mutant.lt(subset.runoff_post_m_baseline)
    plus = subset.direction.eq("plus")
    minus = subset.direction.eq("minus")
    congruent = (plus & runoff_decreased) | (minus & runoff_increased)
    opacity = np.where(congruent, 0.2, 0.6)
    colors = np.tile(to_rgba(color), (len(subset), 1))
    colors[:, 3] = opacity
    return colors


def main() -> None:
    frame = pd.read_parquet(
        EVIDENCE,
        columns=[
            "scenario",
            "family",
            "direction",
            "baseline_event_present",
            "mutant_event_present",
            "runoff_post_m_baseline",
            "runoff_post_m_mutant",
        ],
    )
    frame = frame.loc[
        frame.baseline_event_present
        & frame.mutant_event_present
        & frame.runoff_post_m_baseline.ge(RUNOFF_FLOOR_M)
        & frame.runoff_post_m_mutant.gt(0)
    ].copy()
    frame["baseline_mm"] = frame.runoff_post_m_baseline * M_TO_MM
    frame["mutant_mm"] = frame.runoff_post_m_mutant * M_TO_MM

    figure, axes = plt.subplots(1, 2, figsize=(15.6, 7.4), dpi=180, sharex=True, sharey=True)
    figure.patch.set_facecolor("#fbfaf7")
    limits = np.array([0.008, 200.0])
    for axis, scenario in zip(axes, ("undisturbed", "burned")):
        axis.set_facecolor("#fbfaf7")
        axis.plot(limits, limits * 2, color="#777777", linewidth=0.9,
                  linestyle="--", zorder=1, label="2x / 0.5x")
        axis.plot(limits, limits * 0.5, color="#777777", linewidth=0.9,
                  linestyle="--", zorder=1)
        axis.plot(limits, limits * 5, color="#888888", linewidth=0.85,
                  linestyle=":", zorder=1, label="5x / 0.2x")
        axis.plot(limits, limits * 0.2, color="#888888", linewidth=0.85,
                  linestyle=":", zorder=1)
        for mutation, marker in MARKERS.items():
            family, direction = mutation
            subset = frame.loc[
                frame.scenario.eq(scenario)
                & frame.family.eq(family)
                & frame.direction.eq(direction)
            ]
            axis.scatter(
                subset["baseline_mm"],
                subset["mutant_mm"],
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
        axis.set_xlabel("Baseline event runoff depth (mm)", fontsize=11, labelpad=8)
        for spine in axis.spines.values():
            spine.set_color("#777777")
            spine.set_alpha(0.35)

    figure.suptitle(
        "Topanga Paired Positive Event Runoff: Mutant versus Baseline",
        fontsize=16,
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
    axes[0].set_ylabel("Mutant event runoff depth (mm)", fontsize=11, labelpad=8)
    handles, labels = axes[0].get_legend_handles_labels()
    handles.extend(
        Line2D(
            [],
            [],
            marker="x",
            linestyle="none",
            color=COLORS[scenario],
            alpha=0.75,
            label=f"{LABELS[scenario]} (n={frame.scenario.eq(scenario).sum():,})",
        )
        for scenario in ("undisturbed", "burned")
    )
    handles.extend(
        Line2D(
            [],
            [],
            marker=marker,
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor="#444444",
            label=MUTATION_LABELS[mutation],
        )
        for mutation, marker in MARKERS.items()
    )
    handles.extend(
        [
            Line2D(
                [],
                [],
                marker="x",
                linestyle="none",
                color="#444444",
                alpha=0.2,
                label="Congruent: parameter / runoff opposite (α=0.2)",
            ),
            Line2D(
                [],
                [],
                marker="x",
                linestyle="none",
                color="#444444",
                alpha=0.6,
                label="Incongruent: same direction or unchanged (α=0.6)",
            ),
        ]
    )
    labels.extend(handle.get_label() for handle in handles[len(labels) :])
    axes[1].legend(
        handles=handles,
        labels=labels,
        loc="upper left",
        bbox_to_anchor=(1.04, 1.0),
        borderaxespad=0.0,
        frameon=True,
        facecolor="#fbfaf7",
        framealpha=0.94,
        edgecolor="#bbbbbb",
        fontsize=9.5,
    )
    figure.text(
        0.99,
        0.012,
        "Source: frozen Topanga census event-pair ledger",
        ha="right",
        fontsize=8.5,
        color="#666666",
    )
    figure.subplots_adjust(left=0.07, right=0.76, bottom=0.12, top=0.86, wspace=0.10)
    figure.savefig(OUTPUT, dpi=220, bbox_inches="tight", facecolor=figure.get_facecolor())


if __name__ == "__main__":
    main()
