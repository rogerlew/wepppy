"""Does slope partition the inverted hillslopes?

Cohort: the 27 honeyed-marathoner hillslopes whose burned (sbs_map) base soil
key is ``620333-loam-forest low sev fire`` (same mukey and disturbed class as
the three inverted hillslopes 118/122/264). Data joined from
``omni/scenarios.hillslope_summaries.parquet`` (slope, runoff depth, sediment
yield per scenario) and ``watershed/hillslopes.parquet`` (aspect). Inversion =
unburned sediment yield > burned sediment yield.

Reads ``slope_inversion_cohort.csv`` next to this script; writes
``slope_inversion_cohort.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "slope_inversion_cohort.csv")
inv = df[df["inverted"]]
non = df[~df["inverted"]]

# steep non-inverting hillslopes worth annotating as counterexamples to a clean
# slope cut, plus the inverted set.
LABEL = set(inv["wepp_id"]) | {148, 390, 256}

fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4))

# --- Panel A: slope vs unburned runoff -------------------------------------
ax = axes[0]
ax.scatter(non["slope"], non["unb_runoff_mm"], s=40, c="#9e9e9e",
           edgecolor="k", lw=0.4, label="no inversion", zorder=2)
ax.scatter(inv["slope"], inv["unb_runoff_mm"], s=170, marker="*",
           c="#d62728", edgecolor="k", lw=0.6, label="inverted", zorder=3)
# shade the joint corner that actually contains every inversion
ax.axvspan(inv["slope"].min(), df["slope"].max(), color="#ffe0b2", alpha=0.25, zorder=0)
ax.axhline(inv["unb_runoff_mm"].min(), color="#ff9800", lw=0.8, ls="--", zorder=1)
ax.axvline(inv["slope"].min(), color="#ff9800", lw=0.8, ls="--", zorder=1)
for _, r in df.iterrows():
    if r["wepp_id"] in LABEL:
        ax.annotate(int(r["wepp_id"]), (r["slope"], r["unb_runoff_mm"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=8)
ax.set_xlabel("Hillslope slope (m/m)")
ax.set_ylabel("Unburned annual runoff depth (mm/yr)")
ax.set_title("Slope vs unburned runoff\n(inversion needs high slope AND high runoff)")
ax.legend(loc="lower right", fontsize=8)

# --- Panel B: slope vs aspect ----------------------------------------------
ax = axes[1]
ax.scatter(non["slope"], non["aspect"], s=40, c="#9e9e9e",
           edgecolor="k", lw=0.4, label="no inversion", zorder=2)
ax.scatter(inv["slope"], inv["aspect"], s=170, marker="*",
           c="#d62728", edgecolor="k", lw=0.6, label="inverted", zorder=3)
ax.axhspan(135, 225, color="#fff9c4", alpha=0.5, zorder=0)  # south-facing band
ax.text(0.5, 180, "south-facing\n(max solar melt forcing)", fontsize=7,
        ha="center", va="center", color="#9e9d24")
ax.axhline(360, color="none")
for _, r in df.iterrows():
    if r["wepp_id"] in LABEL:
        ax.annotate(int(r["wepp_id"]), (r["slope"], r["aspect"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=8)
ax.set_xlabel("Hillslope slope (m/m)")
ax.set_ylabel("Aspect (deg from N)")
ax.set_ylim(0, 360)
ax.set_yticks([0, 90, 180, 270, 360])
ax.set_title("Slope vs aspect\n(steep non-inverting 148 is north-facing)")
ax.legend(loc="upper right", fontsize=8)

fig.suptitle("620333-loam forest low-sev-fire cohort (n=27, 3 inverted): "
             "slope does not cleanly partition inversions", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = HERE / "slope_inversion_cohort.png"
fig.savefig(out, dpi=130)
print(f"wrote {out}")
