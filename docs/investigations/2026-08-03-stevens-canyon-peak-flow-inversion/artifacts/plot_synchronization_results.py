#!/usr/bin/env python3
"""Generate synchronization-sensitivity figures from compact channel results."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "artifacts/synchronization-results/channel_peaks_selected.csv.gz"
FIGURES = ROOT / "figures"
REACHES = [169, 172, 173, 193]
LANES = ["baseline", "dispersion_low", "dispersion_medium", "dispersion_high"]
LABELS = {
    "baseline": "Fixed timing",
    "dispersion_low": "Low (10%)",
    "dispersion_medium": "Medium (20%)",
    "dispersion_high": "High (30%)",
}
COLORS = ["#4c566a", "#5e81ac", "#d08770", "#bf616a"]


def load() -> pd.DataFrame:
    frame = pd.read_csv(DATA)
    return frame.set_index(["year", "julian", "wepp_id", "lane"]).sort_index()


def day203(frame: pd.DataFrame) -> None:
    rows = frame.xs((34, 203), level=("year", "julian")).reset_index()
    peaks = rows.pivot(index="wepp_id", columns="lane", values="peak_m3_s").loc[REACHES]
    burned = np.array([0.000746, 9.60, 9.32, 150.0])
    x = np.arange(len(REACHES))
    width = 0.16
    fig, ax = plt.subplots(figsize=(9.2, 5.2), constrained_layout=True)
    ax.bar(x - 2 * width, burned, width, label="Burned comparator", color="#a3be8c")
    for index, lane in enumerate(LANES):
        ax.bar(x + (index - 1) * width, peaks[lane], width,
               label=LABELS[lane], color=COLORS[index])
    ax.set_xticks(x, ["169", "172", "173", "Outlet 193"])
    ax.set_ylabel("Peak discharge (m³/s)")
    ax.set_title("Day 203 inversion persists under one timing realization")
    ax.legend(ncols=2, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(FIGURES / "figure-1-day203-peak-sensitivity.png", dpi=180)
    plt.close(fig)

    output = peaks.copy()
    output.insert(0, "burned", burned)
    output.to_csv(ROOT / "artifacts/synchronization-results/day203_peaks.csv")


def record_response(frame: pd.DataFrame) -> None:
    wide = frame.reset_index().pivot(
        index=["year", "julian", "wepp_id"], columns="lane", values="peak_m3_s"
    )
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True,
                             constrained_layout=True)
    summary = []
    for ax, reach in zip(axes.flat, REACHES):
        subset = wide.xs(reach, level="wepp_id")
        mask = subset["baseline"] >= 0.01
        for lane, color in zip(LANES[1:], COLORS[1:]):
            change = 100 * (subset.loc[mask, lane] / subset.loc[mask, "baseline"] - 1)
            ax.scatter(subset.loc[mask, "baseline"], change, s=7, alpha=0.25,
                       color=color, label=LABELS[lane])
            summary.append({
                "wepp_id": reach,
                "lane": lane,
                "events": int(mask.sum()),
                "median_percent_change": float(change.median()),
                "p05_percent_change": float(change.quantile(0.05)),
                "p95_percent_change": float(change.quantile(0.95)),
            })
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_ylim(-60, 60)
        ax.set_title(f"WEPP_ID {reach}")
        ax.grid(alpha=0.2)
    axes[1, 0].set_xlabel("Baseline peak discharge (m³/s, log scale)")
    axes[1, 1].set_xlabel("Baseline peak discharge (m³/s, log scale)")
    axes[0, 0].set_ylabel("Peak change (%)")
    axes[1, 0].set_ylabel("Peak change (%)")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Timing dispersion can either attenuate or amplify event peaks")
    fig.savefig(FIGURES / "figure-2-full-record-peak-response.png", dpi=180)
    plt.close(fig)
    pd.DataFrame(summary).to_csv(
        ROOT / "artifacts/synchronization-results/full_record_summary.csv", index=False
    )


def timing_inputs() -> None:
    hills = np.arange(49, 62)
    z = np.array([0.25, -1.25, 1.0, -0.5, 1.5, -0.25, -1.0,
                  0.75, 0.0, -1.5, 0.5, 1.25, -0.75])
    baseline = np.full(13, 4068 / 2.67)
    medium = baseline * (1 + 0.20 * z)
    htcs = np.array([np.nan, 1887, 1506, 1481, 1545, 1542, 1916,
                     np.nan, 3499, np.nan, 1489, 892, 1121])
    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    ax.plot(hills, baseline / 60, "o-", label="Fixed td/2.67", color=COLORS[0])
    ax.plot(hills, medium / 60, "o-", label="Medium duration scaling", color=COLORS[2])
    ax.scatter(hills, htcs / 60, marker="x", s=55, label="Computed htcs", color="#5e81ac")
    ax.set_xticks(hills)
    ax.set_xlabel("Hillslope")
    ax.set_ylabel("Nominal time to peak / htcs (minutes)")
    ax.set_title("The baseline synchronizes day-203 nominal hillslope peak times")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(FIGURES / "figure-3-day203-hillslope-timing-inputs.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = load()
    day203(data)
    record_response(data)
    timing_inputs()
