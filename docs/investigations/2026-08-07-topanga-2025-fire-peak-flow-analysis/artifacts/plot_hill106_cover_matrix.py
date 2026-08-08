#!/usr/bin/env python3
"""Plot selected-event peak-flow response surfaces for the Hill 106 cover matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input, dtype={"event_date": str})
    dates = sorted(data["event_date"].unique())
    figure, axes = plt.subplots(3, 4, figsize=(13.2, 10.2), constrained_layout=True)

    minimum = data["peak_ro_mm_h"].min()
    maximum = data["peak_ro_mm_h"].max()
    normalization = LogNorm(vmin=minimum, vmax=maximum)
    image = None

    for axis, event_date in zip(axes.flat, dates, strict=True):
        event = data[data["event_date"] == event_date]
        peak = event.pivot(
            index="initial_canopy_cover",
            columns="initial_ground_cover",
            values="peak_ro_mm_h",
        ).sort_index(ascending=False)
        image = axis.imshow(peak, cmap="viridis", norm=normalization, aspect="auto")
        axis.set_title(event_date)
        axis.set_xticks(range(len(peak.columns)), [f"{value:.2f}" for value in peak.columns])
        axis.set_yticks(range(len(peak.index)), [f"{value:.2f}" for value in peak.index])
        for row in range(peak.shape[0]):
            for column in range(peak.shape[1]):
                value = peak.iloc[row, column]
                color = "white" if value < 20 or value > 180 else "black"
                axis.text(column, row, f"{value:.0f}", ha="center", va="center", fontsize=6.8, color=color)

    for axis in axes[-1, :]:
        axis.set_xlabel("Initial ground cover")
    for axis in axes[:, 0]:
        axis.set_ylabel("Initial canopy cover")
    assert image is not None
    colorbar = figure.colorbar(image, ax=axes, shrink=0.85, pad=0.02)
    colorbar.set_label("Peak runoff rate (mm h$^{-1}$; logarithmic color scale)")
    figure.suptitle(
        "Hill 106 undisturbed cover matrix: selected-event peak runoff",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, format="svg")


if __name__ == "__main__":
    main()
