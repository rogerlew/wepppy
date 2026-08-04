#!/usr/bin/env python3
"""Plot the paired legacy-ET burn matrix and write its Markdown sidecar."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
FIGURES = HERE.parent / "figures" / "legacy-et-ablation"
SEVERITIES = ("low", "moderate", "high")
TARGETS = {
    "low": ((0.65, 0.80), (0.15, 0.30)),
    "moderate": ((0.50, 0.70), (0.25, 0.40)),
    "high": ((0.40, 0.60), (0.30, 0.45)),
}
COLORS = {"Ep": "#3b7d23", "Es": "#d99032", "Er": "#5795c6"}


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    with gzip.open(HERE / "legacy-et-ablation-annual.csv.gz", "rt", newline="",
                   encoding="utf-8") as stream:
        annual = list(csv.DictReader(stream))
    with (HERE / "legacy-et-ablation-summary.csv").open(newline="", encoding="utf-8") as stream:
        summary = {row["severity"]: row for row in csv.DictReader(stream)}

    ratio_data = [[float(row["et_ratio"]) for row in annual if row["severity"] == severity]
                  for severity in SEVERITIES]
    es_data = [[float(row["es_fraction"]) for row in annual if row["severity"] == severity]
               for severity in SEVERITIES]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    positions = np.arange(1, 4)
    for ax, values, title, target_index in (
        (axes[0], ratio_data, "Burned / undisturbed total ET", 0),
        (axes[1], es_data, "Burned soil evaporation / total ET", 1),
    ):
        boxes = ax.boxplot(values, positions=positions, widths=0.55, patch_artist=True,
                           showfliers=False, medianprops={"color": "black", "linewidth": 1.6})
        for box, color in zip(boxes["boxes"], ("#78b66d", "#e1ad58", "#cf635d"), strict=True):
            box.set_facecolor(color)
            box.set_alpha(0.8)
        for position, severity in zip(positions, SEVERITIES, strict=True):
            low, high = TARGETS[severity][target_index]
            ax.fill_between((position - 0.38, position + 0.38), low, high,
                            color="#777777", alpha=0.18, zorder=0)
        ax.set_xticks(positions, [name.title() for name in SEVERITIES])
        ax.set_title(title)
        ax.set_ylabel("Fraction")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylim(0.3, 1.1)
    axes[1].set_ylim(0, 0.62)

    x = np.arange(6)
    labels = []
    bottom = np.zeros(6)
    for component in ("Ep", "Es", "Er"):
        values = []
        for severity in SEVERITIES:
            row = summary[severity]
            values.extend((float(row[f"median_undisturbed_{component.lower()}_mm"]),
                           float(row[f"median_{component.lower()}_mm"])))
        axes[2].bar(x, values, bottom=bottom, color=COLORS[component], label=component)
        bottom += np.asarray(values)
    for severity in SEVERITIES:
        labels.extend((f"{severity.title()}\nreference", f"{severity.title()}\nburned"))
    axes[2].set_xticks(x, labels, rotation=30, ha="right")
    axes[2].set_ylabel("Median annual depth (mm)")
    axes[2].set_title("Legacy-ET component magnitudes")
    axes[2].legend(frameon=False, ncol=3, loc="upper right")
    axes[2].grid(axis="y", alpha=0.25)
    fig.suptitle("Stevens Canyon burn matrix without PMET", fontsize=15, weight="bold")
    fig.subplots_adjust(top=0.84, bottom=0.22, left=0.06, right=0.98, wspace=0.30)
    stem = "legacy-et-burn-matrix"
    fig.savefig(FIGURES / f"{stem}.png", dpi=180)
    plt.close(fig)

    rows = summary
    result_lines = []
    for severity in SEVERITIES:
        row = rows[severity]
        result_lines.append(
            f"- {severity.title()}: median ET ratio `{float(row['median_et_ratio']):.3f}` "
            f"(target `{TARGETS[severity][0][0]:.2f}-{TARGETS[severity][0][1]:.2f}`); "
            f"median `Es/ET={float(row['median_es_fraction']):.3f}` "
            f"(target `{TARGETS[severity][1][0]:.2f}-{TARGETS[severity][1][1]:.2f}`)."
        )
    (FIGURES / f"{stem}.md").write_text(f"""# Legacy-ET Burn Matrix

![Stevens Canyon legacy-ET burn matrix](legacy-et-burn-matrix.png)

## Caption

Paired 100-year annual distributions after removing `pmetpara.txt` from both
burned and undisturbed hillslope lanes. Gray rectangles in the first two panels
are the severity-specific diagnostic target envelopes. The right panel shows
median absolute annual `Ep`, `Es`, and `Er`; each severity's undisturbed
reference uses the same area-weighted hillslope set as its burned treatment.

## Results

{chr(10).join(result_lines)}

No severity has a year inside both target envelopes. The legacy routine assigns
the undisturbed forest median `324 mm/year` entirely to `Ep`, with zero `Es`
and `Er`. Low- and moderate-severity ET remains effectively equal to the
undisturbed reference. High-severity ET declines, but not nearly enough, and
its soil-evaporation fraction remains above target.

## Extended Interpretation

Removing PMET changes the bookkeeping substantially but does not reproduce the
expected fire-severity response. In legacy WEPP, dense undisturbed forest
reaches the LAI rule's all-plant-side limit, while fire-reduced canopy and
residue transfer demand into `Es` and `Er`. Because potential ET is still
largely consumed, the low- and moderate-severity total-ET ratios remain near
one. This is evidence that selecting the legacy routine is not a defensible
post-fire correction by itself. It also shows the excessive post-fire ET
response is not unique to PMET: both routines encode canopy loss mainly as a
partition change, with too little reduction in total annual ET.

The target bands are diagnostic calibration goals, not site observations.
These results are hillslope-scale, area-weighted simulations; runoff was not
used in scoring and no watershed routing was run.

## Reproducibility

- [`legacy-et-ablation-summary.csv`](../../artifacts/legacy-et-ablation-summary.csv)
- [`legacy-et-ablation-annual.csv.gz`](../../artifacts/legacy-et-ablation-annual.csv.gz)
- [`run_legacy_et_ablation.py`](../../artifacts/run_legacy_et_ablation.py)
- [`plot_legacy_et_ablation.py`](../../artifacts/plot_legacy_et_ablation.py)
""", encoding="utf-8")
    (FIGURES / "README.md").write_text("""# Legacy-ET Ablation Figures

This directory contains the paired 100-year burn matrix produced with WEPP's
legacy ET routine selected by the absence of `pmetpara.txt`.

- [Legacy-ET burn matrix](legacy-et-burn-matrix.md)
""", encoding="utf-8")
    print(f"generated {FIGURES / (stem + '.png')} and sidecar")


if __name__ == "__main__":
    main()
