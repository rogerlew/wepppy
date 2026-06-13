"""Frost-routine (ksflag=1) sensitivity for H264.

Follow-on to the honeyed-marathoner inversion investigation. ``ksflag`` (the
second field on the line after ``Any comments:`` in the WEPP ``.sol`` file)
gates WEPP's internal Ksat adjustments AND the frost routine (``frostN``); it is
``0`` in the production soils. Here H264 was re-run for both scenarios with
``ksflag=1`` (frost + Ksat adjustments on) and ``ksflag=0`` (baseline), using
``wepp_dcc52a6_hill`` on a scratch copy of the fixture with the daily-winter
output enabled. The daily series were written to the two CSVs read here:

- ``event_water_balance_H264_ksflag1.csv`` (ksflag=1, burned vs unburned)
- ``frost_comparison_H264_burned.csv`` (burned, ksflag=0 vs ksflag=1)

Writes ``event_water_balance_H264_ksflag1.png`` and
``frost_runoff_comparison_H264.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
CU, CB = "#1f77b4", "#d62728"  # unburned blue, burned red
CK0, CK1 = "#7e57c2", "#ef6c00"  # ksflag0 purple, ksflag1 orange

# annual (1992) sediment leaving profile, kg, from loss.dat
SED = {("burned", "k0"): 0.0, ("burned", "k1"): 297.0,
       ("unburned", "k0"): 61.18, ("unburned", "k1"): 61.18}
RUNOFF = {("burned", "k0"): 169, ("burned", "k1"): 499,
          ("unburned", "k0"): 162, ("unburned", "k1"): 147}


def fig_ksflag1() -> None:
    df = pd.read_csv(HERE / "event_water_balance_H264_ksflag1.csv")
    j = df["julian"]
    fig, ax = plt.subplots(6, 1, figsize=(9.0, 12.0), sharex=True)
    ax[0].bar(j, df["precip_mm"], color="#4d4d4d", width=0.8)
    ax[0].set_ylabel("Precip\n(mm/d)")
    ax[0].set_title("H264 event water balance with ksflag=1 (frost + Ksat adjustments ON)")
    for a, ucol, bcol, lab in [
        (ax[1], "unb_swe", "brn_swe", "Snow water\n(mm)"),
        (ax[2], "unb_melt", "brn_melt", "Snowmelt\n(mm/d)"),
        (ax[3], "unb_frostdp", "brn_frostdp", "Frost depth\n(mm)"),
        (ax[4], "unb_saturation", "brn_saturation", "Surface\nsaturation"),
        (ax[5], "unb_runoff", "brn_runoff", "Runoff Q\n(mm/d)"),
    ]:
        a.plot(j, df[ucol], color=CU, label="unburned")
        a.plot(j, df[bcol], color=CB, label="burned")
        a.set_ylabel(lab)
    ax[1].legend(loc="upper right", fontsize=8)
    ax[4].axhline(1.0, color="k", lw=0.6, ls=":")
    ax[5].set_xlabel("Julian day (1992)")
    for a in ax:
        a.axvline(168, color="#888", lw=1.0, ls="--")
    fig.tight_layout()
    out = HERE / "event_water_balance_H264_ksflag1.png"
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


def fig_compare() -> None:
    df = pd.read_csv(HERE / "frost_comparison_H264_burned.csv")
    j = df["julian"]
    fig, ax = plt.subplots(5, 1, figsize=(9.0, 11.0))
    ax[0].bar(j, df["precip_mm"], color="#4d4d4d", width=0.8)
    ax[0].set_ylabel("Precip\n(mm/d)")
    ax[0].set_title("H264 burned scenario: frost OFF (ksflag=0) vs ON (ksflag=1)")
    ax[1].plot(j, df["swe_k0"], color=CK0, label="ksflag=0")
    ax[1].plot(j, df["swe_k1"], color=CK1, ls="--", label="ksflag=1")
    ax[1].set_ylabel("Snow water\n(mm)")
    ax[1].legend(loc="upper right", fontsize=8)
    ax[1].text(0.02, 0.1, "identical -> snow/melt unaffected by frost",
               transform=ax[1].transAxes, fontsize=8, color="#555")
    ax[2].plot(j, df["frostdp_k0"], color=CK0)
    ax[2].plot(j, df["frostdp_k1"], color=CK1, ls="--")
    ax[2].set_ylabel("Frost depth\n(mm)")
    ax[3].plot(j, df["runoff_k0"], color=CK0)
    ax[3].plot(j, df["runoff_k1"], color=CK1, ls="--")
    ax[3].set_ylabel("Runoff Q\n(mm/d)")
    ax[3].set_xlabel("Julian day (1992)")
    for a in ax[:4]:
        a.axvline(168, color="#888", lw=1.0, ls="--")
        a.set_xlim(j.min(), j.max())
    # annual totals bar
    a = ax[4]
    labels = ["burned\nrunoff (mm)", "burned\nsediment (kg)",
              "unburned\nrunoff (mm)", "unburned\nsediment (kg)"]
    k0 = [RUNOFF[("burned", "k0")], SED[("burned", "k0")],
          RUNOFF[("unburned", "k0")], SED[("unburned", "k0")]]
    k1 = [RUNOFF[("burned", "k1")], SED[("burned", "k1")],
          RUNOFF[("unburned", "k1")], SED[("unburned", "k1")]]
    x = range(len(labels))
    a.bar([i - 0.2 for i in x], k0, width=0.4, color=CK0, label="ksflag=0")
    a.bar([i + 0.2 for i in x], k1, width=0.4, color=CK1, label="ksflag=1")
    a.set_xticks(list(x))
    a.set_xticklabels(labels, fontsize=8)
    a.set_ylabel("annual 1992")
    a.set_title("Annual runoff and sediment (1992)", fontsize=9)
    a.legend(fontsize=8)
    for i, (v0, v1) in enumerate(zip(k0, k1)):
        a.text(i - 0.2, v0, f"{v0:g}", ha="center", va="bottom", fontsize=7)
        a.text(i + 0.2, v1, f"{v1:g}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    out = HERE / "frost_runoff_comparison_H264.png"
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    fig_ksflag1()
    fig_compare()
