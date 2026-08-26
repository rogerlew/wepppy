#!/usr/bin/env python3
"""Plot the archived OpenET Hill 106 monthly observations."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "openet-hill-106-monthly-2016-2025.csv"
OUTPUT = HERE / "openet-hill-106-pre-post-fire.svg"


def main() -> None:
    observations = pd.read_csv(SOURCE, parse_dates=["date"])
    observations["year"] = observations["date"].dt.year
    observations["month"] = observations["date"].dt.month

    annual = observations.groupby("year", as_index=False)["et_mm"].sum()
    prefire = observations[observations["year"].between(2016, 2024)]
    climatology = prefire.groupby("month", as_index=False).agg(
        et_mm=("et_mm", "mean"),
        ndvi=("ndvi", "mean"),
    )
    postfire = observations[observations["year"] == 2025]

    figure, axes = plt.subplots(3, 1, figsize=(9, 10), constrained_layout=True)

    colors = ["#4477aa" if year < 2025 else "#cc3311" for year in annual["year"]]
    axes[0].bar(annual["year"], annual["et_mm"], color=colors)
    axes[0].axhline(
        annual.loc[annual["year"] < 2025, "et_mm"].mean(),
        color="#222222",
        linestyle="--",
        linewidth=1,
        label="2016–2024 mean",
    )
    axes[0].set_ylabel("Annual ET (mm)")
    axes[0].set_title("OpenET Ensemble v2.1 at WEPP Hill 106 centroid")
    axes[0].legend(frameon=False)

    axes[1].plot(climatology["month"], climatology["et_mm"], marker="o", label="2016–2024 mean")
    axes[1].plot(postfire["month"], postfire["et_mm"], marker="o", color="#cc3311", label="2025")
    axes[1].set_ylabel("Monthly ET (mm)")
    axes[1].set_xticks(range(1, 13))
    axes[1].legend(frameon=False)

    axes[2].plot(climatology["month"], climatology["ndvi"], marker="o", label="2016–2024 mean")
    axes[2].plot(postfire["month"], postfire["ndvi"], marker="o", color="#cc3311", label="2025")
    axes[2].set_ylabel("NDVI")
    axes[2].set_xlabel("Month")
    axes[2].set_xticks(range(1, 13))
    axes[2].legend(frameon=False)

    figure.savefig(OUTPUT)


if __name__ == "__main__":
    main()
