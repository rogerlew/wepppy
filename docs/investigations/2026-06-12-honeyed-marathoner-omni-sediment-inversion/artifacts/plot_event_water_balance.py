"""Event water-balance figure for the honeyed-marathoner sediment inversion.

Daily water-balance state (snow water equivalent, surface saturation, soil
evaporation, runoff) is read from the preserved production WEPP outputs in the
fixture (``wat.dat`` / ``soil.dat``). These are daily because WEPP solves the
infiltration/runoff path once per day; it does not emit hourly soil-water state
for this event. Daily snowmelt and the hourly storm-day rain/melt are taken
from regenerated ``snow.dat`` (read from SNOW_ROOT) -- the hourly winter output
WEPP does emit. The figure shows the spring melt freshet: the open burned
canopy melts its snowpack out ~4 days earlier (radiation melt term scales with
1 - canopy cover), so the burned surface starts drying earlier and sits below
saturation when the 1992-06-16 storm arrives, while the unburned surface is
still near saturation and sheds the burst as saturation-excess runoff.

Usage::

    python plot_event_water_balance.py

Writes ``event_water_balance_H264.png`` and ``event_water_balance_H264.csv``
next to this script.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURE_ROOT = HERE.parent / "run_root"
# run_root lives under tests/; resolve via the committed fixture location.
FIXTURE_ROOT = (
    HERE.parents[3]
    / "tests"
    / "omni"
    / "fixtures"
    / "honeyed_marathoner_sediment_inversion"
    / "run_root"
)
# snow.dat (hourly) is regenerated in scratch; override with SNOW_ROOT env if needed.
import os  # noqa: E402

SNOW_ROOT = Path(os.environ.get("HM_SNOW_ROOT", "/tmp/hm_wb/run_root"))

HILLSLOPE = 264
YEAR = 1992
STORM_J = 168
WINDOW = range(115, 177)


def _out_dir(root: Path, scenario: str) -> Path:
    if scenario == "burned":
        return root / "wepp" / "output"
    return root / "_pups" / "omni" / "scenarios" / "undisturbed" / "wepp" / "output"


def _read_wat(path: Path) -> dict[int, dict[str, float]]:
    rows: dict[int, dict[str, float]] = {}
    for line in path.read_text(errors="replace").splitlines():
        p = line.split()
        if len(p) < 20 or not p[0].isdigit():
            continue
        if int(p[0]) != 1 or int(p[2]) != YEAR:
            continue
        j = int(p[1])
        rows[j] = {"precip": float(p[3]), "runoff": float(p[5]),
                   "soil_evap": float(p[7]), "swe": float(p[15])}
    return rows


def _read_daily_melt(path: Path) -> dict[int, float]:
    melt: dict[int, float] = {}
    for line in path.read_text(errors="replace").splitlines():
        p = line.split()
        if len(p) < 13 or not p[0].isdigit() or int(p[2]) != YEAR:
            continue
        melt[int(p[0])] = melt.get(int(p[0]), 0.0) + float(p[7])
    return melt


def _read_soil(path: Path) -> dict[int, dict[str, float]]:
    rows: dict[int, dict[str, float]] = {}
    for line in path.read_text(errors="replace").splitlines():
        p = line.split()
        if len(p) != 14 or not p[0].isdigit():
            continue
        if int(p[0]) != 1 or int(p[2]) != YEAR:
            continue
        j = int(p[1])
        rows[j] = {"suction": float(p[5]), "saturation": float(p[12]), "tsw": float(p[13])}
    return rows


def _read_snow_storm(path: Path) -> list[tuple[int, float, float]]:
    out: list[tuple[int, float, float]] = []
    for line in path.read_text(errors="replace").splitlines():
        p = line.split()
        if len(p) < 13 or not p[0].isdigit():
            continue
        if int(p[0]) != STORM_J or int(p[2]) != YEAR:
            continue
        out.append((int(p[1]), float(p[4]), float(p[7])))  # hour, rain, melt
    return out


def main() -> None:
    data = {}
    for scen in ("burned", "unburned"):
        wat = _read_wat(_out_dir(FIXTURE_ROOT, scen) / f"H{HILLSLOPE}.wat.dat")
        soil = _read_soil(_out_dir(FIXTURE_ROOT, scen) / f"H{HILLSLOPE}.soil.dat")
        snow_path = (_out_dir(SNOW_ROOT, scen) / f"H{HILLSLOPE}.snow.dat")
        melt = _read_daily_melt(snow_path) if snow_path.exists() else {}
        data[scen] = {"wat": wat, "soil": soil, "melt": melt}

    js = list(WINDOW)
    burned, unburned = data["burned"], data["unburned"]

    storm_hours = _read_snow_storm(_out_dir(SNOW_ROOT, "unburned") / f"H{HILLSLOPE}.snow.dat")

    fig, axes = plt.subplots(6, 1, figsize=(9.0, 12.5))
    cu, cb = "#1f77b4", "#d62728"  # unburned blue, burned red

    def series(scen: str, store: str, key: str) -> list[float]:
        return [data[scen][store].get(j, {}).get(key, float("nan"))
                if store != "melt" else data[scen]["melt"].get(j, 0.0) for j in js]

    # 1. precipitation (shared climate)
    ax = axes[0]
    ax.bar(js, [unburned["wat"].get(j, {}).get("precip", 0.0) for j in js],
           color="#4d4d4d", width=0.8)
    ax.set_ylabel("Precip\n(mm/day)")
    ax.set_title(f"H{HILLSLOPE} spring melt to {YEAR}-06-16 storm "
                 f"(Julian days {js[0]}-{js[-1]}, {YEAR})")

    # 2. snow water equivalent -- melt-out timing
    ax = axes[1]
    ax.plot(js, series("unburned", "wat", "swe"), color=cu, label="unburned")
    ax.plot(js, series("burned", "wat", "swe"), color=cb, label="burned")
    ax.set_ylabel("Snow water\n(mm)")
    ax.legend(loc="upper right", fontsize=8)

    # 3. daily snowmelt -- burned melts ~2.5x faster (radiation term ~ 1 - cancov)
    ax = axes[2]
    ax.plot(js, series("unburned", "melt", ""), color=cu)
    ax.plot(js, series("burned", "melt", ""), color=cb)
    ax.set_ylabel("Snowmelt\n(mm/day)")

    # 4. surface saturation -- each surface dries when its snow is gone
    ax = axes[3]
    ax.plot(js, series("unburned", "soil", "saturation"), color=cu)
    ax.plot(js, series("burned", "soil", "saturation"), color=cb)
    ax.axhline(1.0, color="k", lw=0.6, ls=":")
    ax.set_ylabel("Surface\nsaturation")

    # 5. daily runoff -- melt freshet in both, then the storm split
    ax = axes[4]
    ax.plot(js, series("unburned", "wat", "runoff"), color=cu, marker="o", ms=3)
    ax.plot(js, series("burned", "wat", "runoff"), color=cb, marker="o", ms=3)
    ax.set_ylabel("Runoff Q\n(mm/day)")
    ax.set_xlabel("Julian day")

    for ax in axes[:5]:
        ax.axvline(STORM_J, color="#888888", lw=1.0, ls="--")
        ax.set_xlim(js[0], js[-1])

    # 6. hourly storm day (genuine hourly WEPP output: rain + melt)
    ax = axes[5]
    if storm_hours:
        hrs = [h for h, _, _ in storm_hours]
        rain = [r for _, r, _ in storm_hours]
        melt = [m for _, _, m in storm_hours]
        ax.bar(hrs, rain, color="#4d4d4d", width=0.8, label="rain")
        ax.plot(hrs, melt, color=cb, marker="o", ms=3, label="snowmelt")
        ax.set_xlim(0.5, 24.5)
    ax.set_ylabel("Hourly\n(mm)")
    ax.set_xlabel(f"Hour of Julian day {STORM_J} (storm day) - hourly snow.dat output")
    ax.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    png = HERE / f"event_water_balance_H{HILLSLOPE}.png"
    fig.savefig(png, dpi=130)

    # tidy CSV of the daily window
    csv = HERE / f"event_water_balance_H{HILLSLOPE}.csv"
    with csv.open("w") as fp:
        fp.write("julian,precip_mm,unb_swe,brn_swe,unb_melt,brn_melt,"
                 "unb_soil_evap,brn_soil_evap,unb_saturation,brn_saturation,"
                 "unb_suction,brn_suction,unb_runoff,brn_runoff\n")
        for j in js:
            uw, bw = unburned["wat"].get(j, {}), burned["wat"].get(j, {})
            us, bs = unburned["soil"].get(j, {}), burned["soil"].get(j, {})
            fp.write(f"{j},{uw.get('precip', 0.0):.2f},{uw.get('swe', 0.0):.1f},"
                     f"{bw.get('swe', 0.0):.1f},{unburned['melt'].get(j, 0.0):.1f},"
                     f"{burned['melt'].get(j, 0.0):.1f},{uw.get('soil_evap', 0.0):.3f},"
                     f"{bw.get('soil_evap', 0.0):.3f},{us.get('saturation', float('nan')):.3f},"
                     f"{bs.get('saturation', float('nan')):.3f},{us.get('suction', float('nan')):.2f},"
                     f"{bs.get('suction', float('nan')):.2f},{uw.get('runoff', 0.0):.4f},"
                     f"{bw.get('runoff', 0.0):.4f}\n")
    print(f"wrote {png}")
    print(f"wrote {csv}")


if __name__ == "__main__":
    main()
