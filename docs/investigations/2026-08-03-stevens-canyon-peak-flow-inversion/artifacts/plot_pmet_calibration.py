#!/usr/bin/env python3
"""Plot PMET calibration response surfaces and write Markdown sidecars."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
FIGURES = HERE.parent / "figures" / "pmet-calibration"
TARGETS = {
    "low": ((0.65, 0.80), (0.15, 0.30)),
    "moderate": ((0.50, 0.70), (0.25, 0.40)),
    "high": ((0.40, 0.60), (0.30, 0.45)),
}


def read_rows() -> list[dict[str, float | str]]:
    with (HERE / "pmet-calibration-summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    numeric = set(rows[0]) - {"severity"}
    return [{key: (value if key == "severity" else float(value)) for key, value in row.items()}
            for row in rows]


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    index_links = []
    for severity, targets in TARGETS.items():
        selected = [row for row in rows if row["severity"] == severity]
        kcbs = sorted({float(row["kcb"]) for row in selected})
        rawps = sorted({float(row["rawp"]) for row in selected})
        lookup = {(float(row["kcb"]), float(row["rawp"])): row for row in selected}
        ratio = np.asarray([[lookup[(kcb, rawp)]["median_et_ratio"] for rawp in rawps] for kcb in kcbs])
        fraction = np.asarray([[lookup[(kcb, rawp)]["median_es_fraction"] for rawp in rawps] for kcb in kcbs])
        best = min(selected, key=lambda row: float(row["score"]))
        passing = [row for row in selected if float(row["joint_pass_fraction"]) > 0]

        fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
        panels = ((ratio, "Median total ET / undisturbed ET", targets[0]),
                  (fraction, "Median soil evaporation / total ET", targets[1]))
        for ax, (values, title, bounds) in zip(axes, panels, strict=True):
            image = ax.imshow(values, origin="lower", aspect="auto",
                              extent=(min(rawps)-0.05, max(rawps)+0.05,
                                      min(kcbs)-0.05, max(kcbs)+0.05), cmap="viridis")
            visible_levels = [level for level in bounds if values.min() <= level <= values.max()]
            if visible_levels:
                contours = ax.contour(rawps, kcbs, values, levels=visible_levels, colors="white",
                                      linewidths=1.2)
                ax.clabel(contours, inline=True, fontsize=8, fmt="%.2f")
            ax.scatter(float(best["rawp"]), float(best["kcb"]), marker="*", s=170,
                       color="#d73027", edgecolor="white", linewidth=0.8, label="Best joint score")
            ax.set_xlabel("rawp")
            ax.set_ylabel("kcb")
            ax.set_title(title)
            location = "overlaps surface" if visible_levels else "outside surface"
            ax.text(0.02, 0.02, f"Target {bounds[0]:.2f}-{bounds[1]:.2f} ({location})",
                    transform=ax.transAxes, fontsize=8, color="white",
                    bbox={"facecolor": "black", "alpha": 0.45, "edgecolor": "none"})
            ax.set_xticks(rawps)
            ax.set_yticks(kcbs)
            ax.legend(loc="best", frameon=True)
            fig.colorbar(image, ax=ax, shrink=0.86)
        fig.suptitle(f"{severity.title()}-severity PMET calibration", weight="bold")
        fig.subplots_adjust(top=0.82, bottom=0.12, wspace=0.35)
        stem = f"{severity}-severity-pmet-calibration"
        fig.savefig(FIGURES / f"{stem}.png", dpi=180)
        plt.close(fig)

        pass_text = (f"{len(passing)} of {len(selected)} candidates produced at least one paired year "
                     "inside both envelopes." if passing else
                     f"None of the {len(selected)} candidates produced a paired year inside both envelopes.")
        (FIGURES / f"{stem}.md").write_text(f"""# {severity.title()}-Severity PMET Calibration

![{severity.title()} severity PMET response surfaces]({stem}.png)

## Caption

Median annual total-ET ratio and soil-evaporation fraction across 100 paired
climate years for the `kcb` and `rawp` grid. White contours mark the target
envelope boundaries. The red star is the minimum joint-distance candidate.

## Best Candidate

- `kcb={float(best['kcb']):.2f}`, `rawp={float(best['rawp']):.2f}`
- median ET ratio: `{float(best['median_et_ratio']):.3f}`; target
  `{targets[0][0]:.2f}-{targets[0][1]:.2f}`
- median `Es/ET`: `{float(best['median_es_fraction']):.3f}`; target
  `{targets[1][0]:.2f}-{targets[1][1]:.2f}`
- median annual `Ep={float(best['median_ep_mm']):.1f} mm`,
  `Es={float(best['median_es_mm']):.1f} mm`, and
  `ET={float(best['median_et_mm']):.1f} mm`
- paired years inside both envelopes: `{100 * float(best['joint_pass_fraction']):.0f}%`

## Interpretation

{pass_text} The surfaces test PMET coefficient sufficiency, not production
defaults. `kcb` and `rawp` remain physically provisional until independently
validated against observed post-fire ET components. Runoff was not included in
the score.

## Source Data

- [`pmet-calibration-summary.csv`](../../artifacts/pmet-calibration-summary.csv)
- [`pmet-calibration-annual.csv.gz`](../../artifacts/pmet-calibration-annual.csv.gz)
""", encoding="utf-8")
        index_links.append(f"- [{severity.title()} severity]({stem}.md)")

    (FIGURES / "README.md").write_text("""# PMET Fire-Severity Calibration Figures

The response surfaces show whether `kcb` and `rawp` can jointly reproduce the
post-fire annual total-ET ratio and `Es/ET` targets. Each figure uses 100 paired
climate years and the actual hillslope-area weights for its severity class.
Runoff is excluded from calibration.

""" + "\n".join(index_links) + "\n", encoding="utf-8")
    print(f"generated 3 figure/sidecar pairs in {FIGURES}")


if __name__ == "__main__":
    main()
