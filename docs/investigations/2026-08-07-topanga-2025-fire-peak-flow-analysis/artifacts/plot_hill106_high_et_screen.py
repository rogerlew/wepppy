#!/usr/bin/env python3
"""Plot the Hill 106 high-ET screening responses."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "hill106-high-et-screen-summary.csv"
OUTPUT = HERE / "hill106-high-et-screen.svg"


def main() -> None:
    data = pd.read_csv(SOURCE)
    figure, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    styles = {"baseline": ("o", "Undisturbed management"), "dense": ("s", "Dense canopy")}

    for management, (marker, label) in styles.items():
        subset = data.loc[data.management == management].sort_values("kcb")
        axes[0].plot(subset.kcb, subset.combined_runoff_2020_mm, marker=marker, label=label)
        axes[1].plot(subset.kcb, subset.total_et_2020_mm, marker=marker, label=label)
        axes[2].plot(subset.kcb, subset.maximum_peak_ro_mm_h, marker=marker, label=label)

    axes[0].axhline(6.2, color="black", linestyle="--", linewidth=1, label="Reported 6.2 mm")
    axes[0].set_ylabel("2020 combined runoff (mm)")
    axes[1].set_ylabel("2020 ET (mm)")
    axes[2].set_ylabel("45-year maximum PeakRO (mm/h)")
    for axis in axes:
        axis.set_xlabel("PMET Kcb")
        axis.set_xticks([1.2, 1.3, 1.4])
        axis.grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    figure.suptitle("Hill 106 undisturbed high-ET screen; wepp_260803")
    figure.savefig(OUTPUT)


if __name__ == "__main__":
    main()
