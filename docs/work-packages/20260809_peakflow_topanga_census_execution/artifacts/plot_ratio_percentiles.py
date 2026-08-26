#!/usr/bin/env python3
"""Plot Topanga mutant/baseline peak ratios against within-scenario percentile."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


EVIDENCE = Path(
    "/home/workdir/peakflow-topanga-census-evidence/"
    "b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de/"
    "ledgers/event-pairs.parquet"
)
OUTPUT = Path(__file__).with_name("topanga-mutant-baseline-ratio-percentiles.png")
PEAK_FLOOR_M_S = 1e-7
COLORS = {"burned": "#e67e22", "undisturbed": "#238b57"}
LABELS = {"burned": "Burned", "undisturbed": "Unburned (undisturbed)"}


def main() -> None:
    frame = pd.read_parquet(
        EVIDENCE,
        columns=[
            "scenario",
            "baseline_event_present",
            "mutant_event_present",
            "peak_m_s_baseline",
            "peak_m_s_mutant",
        ],
    )
    frame = frame.loc[
        frame.baseline_event_present
        & frame.mutant_event_present
        & frame.peak_m_s_baseline.ge(PEAK_FLOOR_M_S)
        & frame.peak_m_s_mutant.gt(0)
    ].copy()
    frame["ratio"] = frame.peak_m_s_mutant / frame.peak_m_s_baseline

    figure, axis = plt.subplots(figsize=(12, 7.2), dpi=180)
    figure.patch.set_facecolor("#fbfaf7")
    axis.set_facecolor("#fbfaf7")

    for scenario in ("burned", "undisturbed"):
        ratios = np.sort(frame.loc[frame.scenario.eq(scenario), "ratio"].to_numpy())
        percentiles = (np.arange(ratios.size) + 0.5) / ratios.size * 100
        tails = (ratios <= 0.5) | (ratios >= 2.0)
        axis.scatter(
            percentiles[~tails],
            ratios[~tails],
            marker="x",
            s=7,
            linewidths=0.35,
            alpha=0.045,
            color=COLORS[scenario],
            rasterized=True,
        )
        axis.scatter(
            percentiles[tails],
            ratios[tails],
            marker="x",
            s=15,
            linewidths=0.8,
            alpha=0.5,
            color=COLORS[scenario],
            rasterized=True,
            label=f"{LABELS[scenario]} (n={ratios.size:,})",
        )
        indices = np.linspace(0, ratios.size - 1, 1200).astype(int)
        axis.plot(
            percentiles[indices],
            ratios[indices],
            color=COLORS[scenario],
            linewidth=1.15,
            alpha=0.82,
        )

    axis.axhspan(0.5, 2.0, color="#777777", alpha=0.065, zorder=0)
    axis.axhline(1.0, color="#333333", linewidth=1.1, alpha=0.8)
    for threshold in (0.5, 2.0):
        axis.axhline(threshold, color="#666666", linewidth=0.8, linestyle="--", alpha=0.6)

    axis.set_yscale("log")
    axis.set_xlim(0, 100)
    axis.set_ylim(0.008, 130)
    axis.set_xticks(np.arange(0, 101, 10))
    axis.set_yticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100])
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}×"))
    axis.grid(axis="both", which="major", color="#555555", alpha=0.12, linewidth=0.7)
    axis.grid(axis="y", which="minor", color="#555555", alpha=0.05, linewidth=0.5)
    for spine in axis.spines.values():
        spine.set_color("#777777")
        spine.set_alpha(0.35)

    figure.suptitle(
        "Topanga Peak-Flow Response: Mutant / Baseline Ratio by Percentile",
        fontsize=16,
        weight="semibold",
        y=0.975,
    )
    figure.text(
        0.5,
        0.935,
        "Paired positive events with baseline peak ≥ 10⁻⁷ m/s; percentile ranked within scenario",
        ha="center",
        fontsize=10.5,
        color="#555555",
    )
    axis.set_xlabel("Percentile within scenario", fontsize=12, labelpad=9)
    axis.set_ylabel("Mutant peak / baseline peak (log scale)", fontsize=12, labelpad=9)
    axis.text(1.2, 1.18, "mutant higher", fontsize=9, color="#555555", va="bottom")
    axis.text(1.2, 0.82, "mutant lower", fontsize=9, color="#555555", va="top")
    axis.text(1.2, 1.0, "equal", fontsize=9, color="#333333", va="center")
    axis.text(1.2, 2.14, "≥2× outlier", fontsize=9, color="#555555", va="bottom")
    axis.text(1.2, 0.47, "≤0.5× outlier", fontsize=9, color="#555555", va="top")
    legend = axis.legend(
        loc="upper left",
        frameon=True,
        facecolor="#fbfaf7",
        framealpha=0.94,
        edgecolor="#bbbbbb",
        fontsize=10,
    )
    for handle in legend.legend_handles:
        handle.set_alpha(0.9)
    figure.text(
        0.99,
        0.012,
        "Source: frozen Topanga census event-pair ledger • ratios above preregistered baseline peak floor",
        ha="right",
        fontsize=8.5,
        color="#666666",
    )
    figure.subplots_adjust(left=0.105, right=0.985, bottom=0.12, top=0.89)
    figure.savefig(OUTPUT, dpi=220, bbox_inches="tight", facecolor=figure.get_facecolor())


if __name__ == "__main__":
    main()
