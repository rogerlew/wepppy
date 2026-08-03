#!/usr/bin/env python3
"""Summarize and plot the contributor-indexed htcs experiment."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INVESTIGATION = Path(__file__).resolve().parents[1]
FIGURES = INVESTIGATION / "figures"
RESULTS = INVESTIGATION / "artifacts" / "htcs-results"
ABLATION = Path("/wc1/ablation/stevens-canyon-htcs-ensemble-20260803")
CONTROL = ABLATION / "lanes/legacy-reader-parity-v2/wepp/runs/chan.out"
DIRECT = ABLATION / "lanes/full-direct-htcs/wepp/runs/chan.out"
CONTROL_WB = ABLATION / "lanes/legacy-reader-parity-v2/wepp/runs/chanwb.out"
COMPACT_DIRECT = ABLATION / "lanes/year34-compact-direct-htcs/wepp/runs/chan.out"
ENSEMBLE = ABLATION / "evidence/day203_htcs_ensemble.csv"
REACHES = [169, 172, 173, 193]
COLORS = {0.10: "#5e81ac", 0.25: "#d08770", 0.50: "#bf616a"}


def parse_chan(path: Path) -> pd.DataFrame:
    rows: list[tuple[int, int, int, float, float]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if (
            len(fields) == 6
            and fields[0].isdigit()
            and int(fields[2]) in REACHES
        ):
            rows.append(
                (
                    int(fields[0]),
                    int(fields[1]),
                    int(fields[2]),
                    float(fields[4]),
                    float(fields[5]),
                )
            )
    return pd.DataFrame(
        rows, columns=["year", "julian", "wepp_id", "peak_time_s", "peak_m3_s"]
    )


def parse_inflow(path: Path) -> pd.DataFrame:
    rows: list[tuple[int, int, int, float]] = []
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if (
            len(fields) == 10
            and fields[0].isdigit()
            and int(fields[2]) in REACHES
        ):
            rows.append((int(fields[0]), int(fields[1]), int(fields[2]), float(fields[4])))
    return pd.DataFrame(rows, columns=["year", "julian", "wepp_id", "control_inflow_m3"])


def paired_full_record() -> pd.DataFrame:
    control = parse_chan(CONTROL).rename(
        columns={"peak_time_s": "control_time_s", "peak_m3_s": "control_peak_m3_s"}
    )
    direct = parse_chan(DIRECT).rename(
        columns={"peak_time_s": "htcs_time_s", "peak_m3_s": "htcs_peak_m3_s"}
    )
    paired = control.merge(direct, on=["year", "julian", "wepp_id"], validate="one_to_one")
    paired = paired.merge(
        parse_inflow(CONTROL_WB), on=["year", "julian", "wepp_id"], validate="one_to_one"
    )
    paired["peak_change_pct"] = 100.0 * (
        paired["htcs_peak_m3_s"] / paired["control_peak_m3_s"] - 1.0
    )
    paired.loc[paired["control_peak_m3_s"] == 0.0, "peak_change_pct"] = np.nan
    paired["time_change_s"] = paired["htcs_time_s"] - paired["control_time_s"]
    return paired


def summarize_full_record(paired: pd.DataFrame) -> None:
    rows: list[dict[str, float | int]] = []
    focal = paired[(paired.year == 34) & (paired.julian == 203)].set_index("wepp_id")
    for reach in REACHES:
        subset = paired[(paired.wepp_id == reach) & (paired.control_peak_m3_s >= 0.01)]
        focal_inflow = float(focal.loc[reach, "control_inflow_m3"])
        matched = subset[
            subset.control_inflow_m3.between(0.75 * focal_inflow, 1.25 * focal_inflow)
        ]
        for cohort, frame in (
            ("all_ge_0.01", subset),
            ("within_25pct_focal_inflow", matched),
        ):
            rows.append(
                {
                    "wepp_id": reach,
                    "cohort": cohort,
                    "events": len(frame),
                    "median_peak_change_pct": frame.peak_change_pct.median(),
                    "p05_peak_change_pct": frame.peak_change_pct.quantile(0.05),
                    "p95_peak_change_pct": frame.peak_change_pct.quantile(0.95),
                    "fraction_peak_decreased": (frame.peak_change_pct < 0).mean(),
                    "fraction_peak_increased": (frame.peak_change_pct > 0).mean(),
                    "fraction_peak_earlier": (frame.time_change_s < 0).mean(),
                    "fraction_peak_later": (frame.time_change_s > 0).mean(),
                }
            )
    pd.DataFrame(rows).to_csv(RESULTS / "full_record_summary.csv", index=False)
    paired.to_csv(RESULTS / "full_record_selected_reaches.csv.gz", index=False)


def plot_full_record(paired: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=False, sharey=True,
                             constrained_layout=True)
    for ax, reach in zip(axes.flat, REACHES):
        subset = paired[(paired.wepp_id == reach) & (paired.control_peak_m3_s >= 0.01)]
        ax.scatter(
            subset.control_peak_m3_s,
            subset.peak_change_pct,
            s=8,
            alpha=0.28,
            color="#5e81ac",
        )
        focal = subset[(subset.year == 34) & (subset.julian == 203)]
        ax.scatter(
            focal.control_peak_m3_s,
            focal.peak_change_pct,
            s=65,
            marker="*",
            color="#bf616a",
            label="Year 34, day 203",
            zorder=3,
        )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_title(f"WEPP_ID {reach}")
        ax.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[1, 0].set_xlabel("Same-build control peak (m³/s, log scale)")
    axes[1, 1].set_xlabel("Same-build control peak (m³/s, log scale)")
    axes[0, 0].set_ylabel("Direct htcs peak change (%)")
    axes[1, 0].set_ylabel("Direct htcs peak change (%)")
    fig.suptitle("Computed htcs has event-dependent, usually small peak effects")
    fig.savefig(FIGURES / "figure-5-htcs-full-record-response.png", dpi=180)
    plt.close(fig)


def plot_matched_events(paired: pd.DataFrame) -> None:
    focal = paired[(paired.year == 34) & (paired.julian == 203)].set_index("wepp_id")
    data: list[np.ndarray] = []
    timing: list[np.ndarray] = []
    labels: list[str] = []
    for reach in REACHES:
        focal_inflow = float(focal.loc[reach, "control_inflow_m3"])
        matched = paired[
            (paired.wepp_id == reach)
            & paired.control_inflow_m3.between(0.75 * focal_inflow, 1.25 * focal_inflow)
            & (paired.control_peak_m3_s >= 0.01)
        ]
        data.append(matched.peak_change_pct.dropna().to_numpy())
        timing.append((matched.time_change_s / 60.0).to_numpy())
        labels.append(str(reach))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), constrained_layout=True)
    axes[0].boxplot(data, tick_labels=labels, showfliers=True)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_ylabel("Peak change (%)")
    axes[0].set_xlabel("WEPP_ID")
    axes[0].set_title("Events within ±25% of focal routed inflow")
    axes[1].boxplot(timing, tick_labels=labels, showfliers=True)
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_ylabel("Peak-time change (minutes)")
    axes[1].set_xlabel("WEPP_ID")
    axes[1].set_title("Timing response in the matched cohort")
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    fig.savefig(FIGURES / "figure-6-htcs-magnitude-matched-events.png", dpi=180)
    plt.close(fig)


def plot_ensemble() -> None:
    ensemble = pd.read_csv(ENSEMBLE)
    compact = parse_chan(COMPACT_DIRECT)
    compact = compact[(compact.year == 1) & (compact.julian == 203)].set_index("wepp_id")
    ensemble["direct_peak_m3_s"] = ensemble.wepp_id.map(compact.peak_m3_s)
    ensemble["peak_change_pct"] = 100.0 * (
        ensemble.peak_m3_s / ensemble.direct_peak_m3_s - 1.0
    )
    ensemble.to_csv(RESULTS / "day203_ensemble.csv.gz", index=False)
    summary = (
        ensemble.groupby(["cv", "wepp_id"])
        .agg(
            realizations=("seed", "count"),
            median_peak_m3_s=("peak_m3_s", "median"),
            p05_peak_m3_s=("peak_m3_s", lambda values: values.quantile(0.05)),
            p95_peak_m3_s=("peak_m3_s", lambda values: values.quantile(0.95)),
            median_peak_change_pct=("peak_change_pct", "median"),
            p05_peak_change_pct=("peak_change_pct", lambda values: values.quantile(0.05)),
            p95_peak_change_pct=("peak_change_pct", lambda values: values.quantile(0.95)),
            max_abs_balance_m3=("balance_m3", lambda values: values.abs().max()),
            max_factor_mean_error=(
                "area_weighted_factor_mean", lambda values: (values - 1.0).abs().max()
            ),
        )
        .reset_index()
    )
    summary.to_csv(RESULTS / "day203_ensemble_summary.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True,
                             constrained_layout=True)
    for ax, reach in zip(axes.flat, REACHES):
        groups = [
            ensemble[(ensemble.wepp_id == reach) & (ensemble.cv == cv)].peak_change_pct
            for cv in (0.10, 0.25, 0.50)
        ]
        boxes = ax.boxplot(groups, tick_labels=["0.10", "0.25", "0.50"], patch_artist=True)
        for patch, cv in zip(boxes["boxes"], (0.10, 0.25, 0.50)):
            patch.set_facecolor(COLORS[cv])
            patch.set_alpha(0.75)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"WEPP_ID {reach}")
        ax.grid(axis="y", alpha=0.2)
    axes[1, 0].set_xlabel("htcs multiplier CV")
    axes[1, 1].set_xlabel("htcs multiplier CV")
    axes[0, 0].set_ylabel("Peak change from direct htcs (%)")
    axes[1, 0].set_ylabel("Peak change from direct htcs (%)")
    fig.suptitle("Day-203 response to area-centered hillslope htcs variation")
    fig.savefig(FIGURES / "figure-4-day203-htcs-ensemble.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    paired = paired_full_record()
    summarize_full_record(paired)
    plot_full_record(paired)
    plot_matched_events(paired)
    plot_ensemble()


if __name__ == "__main__":
    main()
