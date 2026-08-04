#!/usr/bin/env python3
"""Reproduce and decompose burned-PMET peak soil evaporation at two sites."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
STEVENS = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
PAL_RUNNER = REPO / "docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/run_four_cell_et.py"
STEVENS_AREAS = {
    49: 22.50, 50: 80.10, 51: 140.22, 52: 210.33, 53: 81.90,
    54: 64.71, 55: 73.44, 56: 82.62, 57: 176.94, 58: 256.68,
    59: 83.07, 60: 2.34, 61: 4.68,
}
WAT_COLUMNS = (
    "ofe", "julian", "sim_year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
    "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water", "snow_water",
    "QOFE", "tile", "irrigation", "reported_area", "soil_water_total",
    "profile_depth", "porosity_capacity", "field_capacity", "wilting_point",
)
FIELDS = ("P", "RM", "Ep", "Es", "Er", "soil_water", "soil_water_total")


def load_prior_runner():
    spec = importlib.util.spec_from_file_location("palisades_four_cell", PAL_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {PAL_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.WORK_ROOT = Path("/wc1/ablation/stevens-palisades-es-counterfactual-20260804")
    return module


def read_stevens(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(WAT_COLUMNS):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    values = np.asarray(rows, dtype=np.float64)
    if values.shape != (36_525, len(WAT_COLUMNS)) or not np.isfinite(values).all():
        raise ValueError(f"invalid Stevens output {path}: {values.shape}")
    dates = values[:, [WAT_COLUMNS.index("sim_year"), WAT_COLUMNS.index("julian")]].astype(np.int32)
    kept = values[:, [WAT_COLUMNS.index(name) for name in FIELDS]]
    return dates, kept


def run_palisades(workers: int, smoke: bool):
    module = load_prior_runner()
    hills = module.load_hills()
    module.prepare_undisturbed_managements(hills)
    selected = hills[:1] if smoke else hills
    module.WORK_ROOT.mkdir(parents=True, exist_ok=True)
    results = {}
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(module.run_hill, "burned_pmet", "burned", True, hill): hill
                for hill in selected
            }
            for count, future in enumerate(as_completed(futures), start=1):
                wepp_id, dates, values = future.result()
                indices = [module.KEEP_COLUMNS.index(name) for name in FIELDS]
                results[wepp_id] = (dates, values[:, indices])
                if count % 25 == 0 or count == len(selected):
                    print(f"Palisades completed {count}/{len(selected)}", flush=True)
    finally:
        shutil.rmtree(module.WORK_ROOT, ignore_errors=True)
    areas = {hill.wepp_id: hill.area_m2 for hill in selected}
    return results, areas


def aggregate(site: str, data, areas):
    hills = sorted(data)
    weights = np.asarray([areas[hill] for hill in hills], dtype=float)
    weights /= weights.sum()
    dates = data[hills[0]][0]
    arrays = []
    hill_rows = []
    for hill, weight in zip(hills, weights, strict=True):
        hill_dates, values = data[hill]
        if not np.array_equal(hill_dates, dates):
            raise ValueError(f"calendar mismatch at {site} H{hill}")
        arrays.append(values)
        es = values[:, FIELDS.index("Es")]
        idx = int(np.argmax(es))
        hill_rows.append({
            "site": site, "wepp_id": hill, "area_weight": weight,
            "max_es_mm": es[idx], "peak_year": int(dates[idx, 0]),
            "peak_julian": int(dates[idx, 1]),
        })
    cube = np.stack(arrays)
    weighted = np.average(cube, axis=0, weights=weights)
    es = weighted[:, FIELDS.index("Es")]
    peak = int(np.argmax(es))
    synchronized = float(sum(row["area_weight"] * row["max_es_mm"] for row in hill_rows))
    summary = {
        "site": site, "hillslopes": len(hills), "days": len(dates),
        "actual_peak_es_mm": float(es[peak]),
        "peak_year": int(dates[peak, 0]), "peak_julian": int(dates[peak, 1]),
        "p99_es_mm": float(np.percentile(es, 99)),
        "perfect_sync_peak_es_mm": synchronized,
        "synchronization_efficiency": float(es[peak] / synchronized),
    }
    for field in FIELDS:
        summary[f"peak_day_{field}"] = float(weighted[peak, FIELDS.index(field)])
    # Seven-day rain plus melt is an empirical surface-water recharge indicator.
    lo = max(0, peak - 6)
    summary["peak_prior7_RM_mm"] = float(weighted[lo:peak + 1, FIELDS.index("RM")].sum())
    summary["peak_prior7_P_mm"] = float(weighted[lo:peak + 1, FIELDS.index("P")].sum())
    top = np.argsort(es)[-100:][::-1]
    top_rows = []
    for rank, idx in enumerate(top, start=1):
        row = {"site": site, "rank": rank, "year": int(dates[idx, 0]),
               "julian": int(dates[idx, 1])}
        row.update({field: float(weighted[idx, FIELDS.index(field)]) for field in FIELDS})
        top_rows.append(row)
    return summary, hill_rows, top_rows, dates, weighted


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot(summaries, top_rows):
    by_site = {row["site"]: row for row in summaries}
    sites = ("Stevens Canyon", "Palisades")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    x = np.arange(2)
    actual = [by_site[s]["actual_peak_es_mm"] for s in sites]
    sync = [by_site[s]["perfect_sync_peak_es_mm"] for s in sites]
    axes[0].bar(x, sync, color="#d9d9d9", label="Perfect-synchronization bound")
    axes[0].bar(x, actual, color=("#d95f02", "#1b9e77"), label="Observed area-weighted peak")
    axes[0].set_xticks(x, sites)
    axes[0].set_ylabel("Soil evaporation (mm/day)")
    axes[0].set_title("Peak and synchronization bound")
    axes[0].legend(fontsize=8)
    for site, color in zip(sites, ("#d95f02", "#1b9e77"), strict=True):
        rows = [row for row in top_rows if row["site"] == site]
        axes[1].scatter([row["soil_water"] for row in rows], [row["Es"] for row in rows],
                        s=18, alpha=.65, label=site, color=color)
    axes[1].set_xlabel("Upper-layer soil water (mm)")
    axes[1].set_ylabel("Soil evaporation (mm/day)")
    axes[1].set_title("Top-100 Es days and evaporative-layer water")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    stem = "peak-es-counterfactual"
    fig.savefig(HERE / f"{stem}.png", dpi=200)
    plt.close(fig)
    (HERE / f"{stem}.md").write_text(
        "# Peak soil-evaporation counterfactual\n\n"
        f"![Peak soil-evaporation counterfactual]({stem}.png)\n\n"
        "## Caption\n\nObserved burned-PMET area-weighted peak `Es` and the exact upper bound obtained "
        "by placing every hillslope's own maximum on one day (left); realized `Es` versus "
        "upper evaporative-layer water on each site's 100 largest area-weighted `Es` days "
        "(right).\n\n## Interpretation\n\nThe gap between each paired bar is the maximum peak "
        "increase available from spatial synchronization alone. The scatter tests whether "
        "large Stevens values require water to remain available in WEPP's upper evaporative "
        "layer. It does not independently swap atmospheric forcing and water state, which "
        "co-evolve in a continuous simulation.\n\n## Limitations\n\nThe synchronization bar is an "
        "intentionally impossible upper bound, not a predicted watershed response. Cross-site "
        "differences combine climate, soils, vegetation, and record length unless a controlled "
        "model intervention separates them.\n\n## Provenance\n\nGenerated by `run_counterfactual.py` "
        "with `wepp_260803_hill`; all Palisades runs retained the production `wepp_ui.txt` and "
        "PMET sidecars.\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    pal_data, pal_areas = run_palisades(args.workers, args.smoke)
    if args.smoke:
        dates, values = read_stevens(STEVENS / "burned/wepp/output/H59.wat.dat")
        assert len(dates) == 36_525 and np.isfinite(values).all()
        print("smoke passed: Palisades H1 and Stevens H59")
        return
    stevens_data = {
        hill: read_stevens(STEVENS / f"burned/wepp/output/H{hill}.wat.dat")
        for hill in STEVENS_AREAS
    }
    results = [
        aggregate("Stevens Canyon", stevens_data, STEVENS_AREAS),
        aggregate("Palisades", pal_data, pal_areas),
    ]
    summaries = [result[0] for result in results]
    hills = [row for result in results for row in result[1]]
    top = [row for result in results for row in result[2]]
    write_csv(HERE / "site-summary.csv", summaries)
    write_csv(HERE / "hillslope-maxima.csv", hills)
    write_csv(HERE / "top-es-days.csv", top)
    ratio = summaries[0]["actual_peak_es_mm"] / summaries[1]["actual_peak_es_mm"]
    payload = {"observed_peak_ratio_stevens_to_palisades": ratio, "sites": summaries}
    (HERE / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    plot(summaries, top)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
