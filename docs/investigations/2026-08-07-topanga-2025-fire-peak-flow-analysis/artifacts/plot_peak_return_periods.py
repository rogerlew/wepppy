#!/usr/bin/env python3
"""Plot corrected burned and undisturbed peak-discharge return periods."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "no-restriction-kcb12-peak-return-periods.csv"
OUTPUT = HERE / "no-restriction-kcb12-peak-return-periods.svg"


def main() -> None:
    results = pd.read_csv(SOURCE)
    figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    axis.plot(
        results["return_period_years"],
        results["burned_peak_m3s"],
        marker="o",
        linewidth=2,
        label="Burned",
    )
    axis.plot(
        results["return_period_years"],
        results["undisturbed_peak_m3s"],
        marker="o",
        linewidth=2,
        label="Undisturbed Omni",
    )
    axis.set_xlabel("Return period (years)")
    axis.set_ylabel("Peak discharge (m³/s)")
    axis.set_title("No restrictive layer; natural Kcb 1.20")
    axis.set_xticks(results["return_period_years"])
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.savefig(OUTPUT)


if __name__ == "__main__":
    main()
