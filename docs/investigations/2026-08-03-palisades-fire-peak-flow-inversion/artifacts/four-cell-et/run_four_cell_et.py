#!/usr/bin/env python3
"""Execute and summarize the Palisades burned/undisturbed x PMET/legacy matrix."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from wepppy.wepp.management.managements import Management


RUN_ROOT = Path("/wc1/runs/up/upset-reckoning")
SOURCE_RUNS = RUN_ROOT / "wepp" / "runs"
LANDUSE_PARQUET = RUN_ROOT / "landuse" / "landuse.parquet"
SOILS_PARQUET = RUN_ROOT / "soils" / "soils.parquet"
AREA_PARQUET = RUN_ROOT / "wepp" / "output" / "interchange" / "pass_pw0.metadata.parquet"
MANAGEMENT_ROOT = Path("/workdir/wepppy/wepppy/wepp/management/data/UnDisturbed")
BINARY = Path(
    "/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/bin/wepp_260803_hill"
)
WORK_ROOT = Path("/wc1/ablation/palisades-four-cell-et-20260803")
HERE = Path(__file__).resolve().parent
INVESTIGATION = HERE.parent.parent
FIGURES = INVESTIGATION / "figures" / "four-cell-et"
FLAGGED_EVENTS = INVESTIGATION / "tmp_upset_reckoning_desync" / "flagged_events.csv"

SIDECARS = ("gwcoeff.txt", "snow.txt", "wepp_ui.txt", "chntyp.txt", "tc.txt", "chan.inp")
PMET_MARKER = "FAO Penman-Monteith ET Method Implemented"
EXPECTED_ROWS = 16_802
START_YEAR = 1980
KCB = 0.95
RAWP = 0.8

COLUMNS = (
    "ofe", "julian", "sim_year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
    "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water", "snow_water",
    "QOFE", "tile", "irrigation", "reported_area", "soil_water_total",
    "profile_depth", "porosity_capacity", "field_capacity", "wilting_point",
)
KEEP_COLUMNS = (
    "P", "RM", "Q", "Ep", "Es", "Er", "Dp", "latqcc", "soil_water",
    "soil_water_total", "porosity_capacity", "field_capacity", "wilting_point",
)
CELLS = (
    ("burned_pmet", "burned", True),
    ("undisturbed_pmet", "undisturbed", True),
    ("burned_legacy", "burned", False),
    ("undisturbed_legacy", "undisturbed", False),
)

UNDISTURBED_MANAGEMENT = {
    "forest": ("Old_Forest.man", "Tah_4899"),
    "shrub": ("Shrub.man", "Tah_9591"),
    "developed moderate intensity": ("Developed_Moderate_Intensity.man", "For_2276"),
    "developed low intensity": ("Developed_Low_Intensity.man", "For_2276"),
}
EXPANDED_UNDISTURBED: dict[Path, str] = {}


@dataclass(frozen=True)
class Hill:
    wepp_id: int
    topaz_id: int
    area_m2: float
    disturbed_class: str
    original_soil: Path
    undisturbed_man: Path
    undisturbed_plant: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_hills() -> list[Hill]:
    query = f"""
        SELECT l.wepp_id, l.topaz_id, a.area AS area_m2, l.disturbed_class,
               s.mukey
        FROM read_parquet('{LANDUSE_PARQUET}') l
        JOIN read_parquet('{SOILS_PARQUET}') s USING (wepp_id, topaz_id)
        JOIN read_parquet('{AREA_PARQUET}') a USING (wepp_id)
        ORDER BY l.wepp_id
    """
    records = duckdb.sql(query).fetchall()
    if len(records) != 278:
        raise ValueError(f"expected 278 hillslopes, found {len(records)}")
    hills: list[Hill] = []
    for wepp_id, topaz_id, area_m2, disturbed_class, mukey in records:
        cls = str(disturbed_class)
        base_class = "forest" if "forest" in cls else "shrub" if "shrub" in cls else cls
        try:
            man_name, plant = UNDISTURBED_MANAGEMENT[base_class]
        except KeyError as exc:
            raise ValueError(f"no undisturbed mapping for H{wepp_id}: {cls}") from exc
        soil_name = str(mukey).split("-", 1)[0] + ".sol"
        if cls == "developed moderate intensity":
            soil_name = "Developed_Moderate_Intensity.sol"
        elif cls == "developed low intensity":
            soil_name = "Developed_Low_Intensity.sol"
        original_soil = RUN_ROOT / "soils" / soil_name
        undisturbed_man = MANAGEMENT_ROOT / man_name
        if not original_soil.is_file() or not undisturbed_man.is_file():
            raise FileNotFoundError(f"missing reconstructed input for H{wepp_id}")
        hills.append(Hill(int(wepp_id), int(topaz_id), float(area_m2), cls,
                          original_soil, undisturbed_man, plant))
    return hills


def prepare_undisturbed_managements(hills: list[Hill]) -> None:
    for path in sorted({hill.undisturbed_man for hill in hills}):
        management = Management(
            Key=0,
            ManagementFile=path.name,
            ManagementDir=str(path.parent),
            Description=f"Palisades four-cell {path.stem}",
            Color=(0, 0, 0, 255),
        )
        EXPANDED_UNDISTURBED[path] = str(management.build_multiple_year_man(46))


def disable_graphics(run_path: Path) -> None:
    lines = run_path.read_text(encoding="utf-8").splitlines()
    if lines[16] == "Yes":
        lines[16] = "No"
        lines.pop(17)
    if lines[16] != "No":
        raise ValueError(f"unexpected graphics control in {run_path}")
    run_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_water_balance(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(COLUMNS):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    values = np.asarray(rows, dtype=np.float64)
    if values.shape != (EXPECTED_ROWS, len(COLUMNS)) or not np.isfinite(values).all():
        raise ValueError(f"invalid water balance {path}: {values.shape}")
    dates = values[:, [COLUMNS.index("sim_year"), COLUMNS.index("julian")]].astype(np.int32)
    kept = values[:, [COLUMNS.index(name) for name in KEEP_COLUMNS]]
    return dates, kept, values[:, COLUMNS.index("reported_area")]


def symlink(source: Path, destination: Path) -> None:
    destination.symlink_to(source)


def run_hill(cell: str, land_state: str, pmet: bool, hill: Hill) -> tuple[int, np.ndarray, np.ndarray]:
    lane = WORK_ROOT / "lanes" / f"{cell}_h{hill.wepp_id}"
    runs = lane / "runs"
    output = lane / "output"
    runs.mkdir(parents=True)
    output.mkdir()
    try:
        run_source = SOURCE_RUNS / f"p{hill.wepp_id}.run"
        shutil.copy2(run_source, runs / run_source.name)
        disable_graphics(runs / run_source.name)
        for extension in ("slp", "cli"):
            symlink(SOURCE_RUNS / f"p{hill.wepp_id}.{extension}", runs / f"p{hill.wepp_id}.{extension}")
        if land_state == "burned":
            man = SOURCE_RUNS / f"p{hill.wepp_id}.man"
            soil = SOURCE_RUNS / f"p{hill.wepp_id}.sol"
            plant = next(
                line.split(",", 1)[0]
                for line in (SOURCE_RUNS / "pmetpara.txt").read_text(encoding="utf-8").splitlines()[1:]
                if line.split(",")[3] == str(hill.wepp_id)
            )
        else:
            man = hill.undisturbed_man
            soil = hill.original_soil
            plant = hill.undisturbed_plant
        if land_state == "burned":
            symlink(man, runs / f"p{hill.wepp_id}.man")
        else:
            (runs / f"p{hill.wepp_id}.man").write_text(
                EXPANDED_UNDISTURBED[man], encoding="utf-8"
            )
        symlink(soil, runs / f"p{hill.wepp_id}.sol")
        for sidecar in SIDECARS:
            symlink(SOURCE_RUNS / sidecar, runs / sidecar)
        if pmet:
            (runs / "pmetpara.txt").write_text(
                f"1\n{plant},{KCB},{RAWP},1,{land_state}_h{hill.wepp_id}\n",
                encoding="utf-8",
            )
        if (runs / "wepp_ui.txt").read_bytes() != SOURCE_RUNS.joinpath("wepp_ui.txt").read_bytes():
            raise RuntimeError("wepp_ui.txt sidecar mismatch")
        with (runs / run_source.name).open("rb") as stdin:
            result = subprocess.run(
                [str(BINARY)], cwd=runs, stdin=stdin, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
        stdout = result.stdout.decode(errors="replace")
        stderr = result.stderr.decode(errors="replace")
        if result.returncode != 0 or stderr.strip():
            raise RuntimeError(
                f"{cell} H{hill.wepp_id} failed rc={result.returncode}: {stderr[-1000:]}"
            )
        if (PMET_MARKER in stdout) != pmet:
            raise RuntimeError(f"{cell} H{hill.wepp_id} ET selector marker mismatch")
        dates, values, reported_area = parse_water_balance(output / f"H{hill.wepp_id}.wat.dat")
        if np.ptp(reported_area) != 0:
            raise ValueError(f"reported area changed in {cell} H{hill.wepp_id}")
        return hill.wepp_id, dates, values
    finally:
        shutil.rmtree(lane, ignore_errors=True)


def run_cell(cell: str, land_state: str, pmet: bool, hills: list[Hill], workers: int) -> tuple[np.ndarray, np.ndarray]:
    total_area = sum(hill.area_m2 for hill in hills)
    by_id = {hill.wepp_id: hill for hill in hills}
    aggregate = np.zeros((EXPECTED_ROWS, len(KEEP_COLUMNS)), dtype=np.float64)
    canonical_dates: np.ndarray | None = None
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_hill, cell, land_state, pmet, hill) for hill in hills]
        for completed, future in enumerate(as_completed(futures), start=1):
            wepp_id, dates, values = future.result()
            if canonical_dates is None:
                canonical_dates = dates
            elif not np.array_equal(canonical_dates, dates):
                raise ValueError(f"calendar mismatch in {cell} H{wepp_id}")
            aggregate += values * (by_id[wepp_id].area_m2 / total_area)
            if completed % 25 == 0 or completed == len(hills):
                print(f"{cell}: completed {completed}/{len(hills)}", flush=True)
    assert canonical_dates is not None
    return canonical_dates, aggregate


def write_daily(cell_values: dict[str, tuple[np.ndarray, np.ndarray]]) -> Path:
    path = HERE / "four-cell-daily.csv.gz"
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(("cell", "date", "calendar_year", "julian", *KEEP_COLUMNS, "ET"))
                for cell, (dates, values) in cell_values.items():
                    for (sim_year, julian), row in zip(dates, values, strict=True):
                        calendar_year = int(sim_year) if int(sim_year) >= START_YEAR else START_YEAR + int(sim_year) - 1
                        iso_date = date(calendar_year, 1, 1) + timedelta(days=int(julian) - 1)
                        ep, es, er = (row[KEEP_COLUMNS.index(name)] for name in ("Ep", "Es", "Er"))
                        writer.writerow((cell, iso_date.isoformat(), calendar_year, int(julian), *row, ep + es + er))
    return path


def read_daily(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    grouped_dates: dict[str, list[tuple[int, int]]] = {cell: [] for cell, _, _ in CELLS}
    grouped_values: dict[str, list[list[float]]] = {cell: [] for cell, _, _ in CELLS}
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            cell = row["cell"]
            stored_year = int(row["calendar_year"])
            # Recover artifacts written by the first execution, which treated
            # WEPP's calendar year as a one-based simulation year.
            calendar_year = stored_year - START_YEAR + 1 if stored_year > 3000 else stored_year
            grouped_dates[cell].append((calendar_year, int(row["julian"])))
            grouped_values[cell].append([float(row[name]) for name in KEEP_COLUMNS])
    return {
        cell: (np.asarray(grouped_dates[cell], dtype=np.int32),
               np.asarray(grouped_values[cell], dtype=np.float64))
        for cell, _, _ in CELLS
    }


def annual_rows(cell_values: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for cell, (dates, values) in cell_values.items():
        for sim_year in sorted(set(dates[:, 0])):
            mask = dates[:, 0] == sim_year
            sums = values[mask].sum(axis=0)
            means = values[mask].mean(axis=0)
            row: dict[str, float | int | str] = {
                "cell": cell,
                "calendar_year": int(sim_year) if int(sim_year) >= START_YEAR else START_YEAR + int(sim_year) - 1,
            }
            for name in ("P", "Q", "Ep", "Es", "Er", "Dp", "latqcc"):
                row[f"{name}_mm"] = float(sums[KEEP_COLUMNS.index(name)])
            for name in ("soil_water", "soil_water_total", "porosity_capacity", "field_capacity", "wilting_point"):
                row[f"mean_{name}_mm"] = float(means[KEEP_COLUMNS.index(name)])
            row["ET_mm"] = float(row["Ep_mm"] + row["Es_mm"] + row["Er_mm"])
            row["Es_fraction"] = float(row["Es_mm"] / row["ET_mm"]) if row["ET_mm"] else 0.0
            rows.append(row)
    return rows


def write_dict_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty artifact: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(annual: list[dict[str, float | int | str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cell, _, _ in CELLS:
        subset = [row for row in annual if row["cell"] == cell]
        summary: dict[str, object] = {"cell": cell, "years": len(subset)}
        for key in ("Ep_mm", "Es_mm", "Er_mm", "ET_mm", "Es_fraction", "Q_mm", "mean_soil_water_total_mm"):
            values = np.asarray([float(row[key]) for row in subset])
            summary[f"median_{key}"] = float(np.median(values))
            summary[f"p10_{key}"] = float(np.percentile(values, 10))
            summary[f"p90_{key}"] = float(np.percentile(values, 90))
        rows.append(summary)
    return rows


def event_windows(cell_values: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[dict[str, object]]:
    with FLAGGED_EVENTS.open(newline="", encoding="utf-8") as stream:
        events = list(csv.DictReader(stream))
    rows: list[dict[str, object]] = []
    for event in events:
        event_date = date.fromisoformat(event["date"])
        for cell, (dates, values) in cell_values.items():
            calendar_dates = np.asarray([
                date(int(year) if int(year) >= START_YEAR else START_YEAR + int(year) - 1, 1, 1)
                + timedelta(days=int(day) - 1)
                for year, day in dates
            ], dtype=object)
            for window in (7, 30):
                mask = (calendar_dates < event_date) & (calendar_dates >= event_date - timedelta(days=window))
                if mask.sum() != window:
                    continue
                row: dict[str, object] = {"event_date": event_date.isoformat(), "cell": cell, "window_days": window}
                for name in ("Es", "Ep", "Er", "Q", "P"):
                    row[f"sum_{name}_mm"] = float(values[mask, KEEP_COLUMNS.index(name)].sum())
                row["mean_soil_water_total_mm"] = float(values[mask, KEEP_COLUMNS.index("soil_water_total")].mean())
                row["pre_event_soil_water_total_mm"] = float(values[calendar_dates == event_date - timedelta(days=1), KEEP_COLUMNS.index("soil_water_total")][0])
                rows.append(row)
    return rows


def interaction_rows(summary: list[dict[str, object]]) -> list[dict[str, object]]:
    indexed = {str(row["cell"]): row for row in summary}
    rows: list[dict[str, object]] = []
    for metric in ("Ep_mm", "Es_mm", "ET_mm", "Es_fraction", "Q_mm", "mean_soil_water_total_mm"):
        bp = float(indexed["burned_pmet"][f"median_{metric}"])
        bl = float(indexed["burned_legacy"][f"median_{metric}"])
        up = float(indexed["undisturbed_pmet"][f"median_{metric}"])
        ul = float(indexed["undisturbed_legacy"][f"median_{metric}"])
        rows.append({
            "metric": metric,
            "burned_pmet_effect": bp - bl,
            "undisturbed_pmet_effect": up - ul,
            "difference_in_differences": (bp - bl) - (up - ul),
            "burned_contrast_pmet": bp - up,
            "burned_contrast_legacy": bl - ul,
        })
    return rows


def plot_results(annual: list[dict[str, float | int | str]], summary: list[dict[str, object]], events: list[dict[str, object]]) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    labels = ("B-PMET", "U-PMET", "B-Legacy", "U-Legacy")
    indexed = {str(row["cell"]): row for row in summary}
    x = np.arange(len(CELLS))
    fig, ax = plt.subplots(figsize=(9.5, 5.6), constrained_layout=True)
    bottom = np.zeros(len(CELLS))
    colors = {"Ep": "#4c78a8", "Es": "#f2cf5b", "Er": "#72b7b2"}
    for component in ("Ep", "Es", "Er"):
        heights = np.asarray([float(indexed[cell][f"median_{component}_mm"]) for cell, _, _ in CELLS])
        ax.bar(x, heights, bottom=bottom, label=component, color=colors[component])
        bottom += heights
    ax.set_xticks(x, labels)
    ax.set_ylabel("Median annual flux (mm/year)")
    ax.set_title("Palisades four-cell evapotranspiration partition")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    stem = "four-cell-annual-et-partition"
    fig.savefig(FIGURES / f"{stem}.png", dpi=200)
    plt.close(fig)
    (FIGURES / f"{stem}.md").write_text(
        "# Palisades four-cell annual ET partition\n\n"
        f"![Four-cell annual ET partition]({stem}.png)\n\n"
        "## Caption\n\nMedian annual `Ep`, `Es`, and `Er` for all 278 production-derived "
        "hillslopes, area-weighted to the watershed. PMET and legacy cells differ only by "
        "the presence of `pmetpara.txt` within each land state.\n\n"
        "## Interpretation\n\nUse the change from legacy to PMET within burned and undisturbed bars to "
        "identify ET-method effects. A materially larger burned change is the factorial "
        "interaction that could amplify the burned-versus-undisturbed contrast. Total ET and "
        "partition must be interpreted together; redistribution from `Ep` to `Es` is not an "
        "increase in atmospheric water loss unless total ET also rises.\n\n"
        "## Provenance\n\nGenerated by `artifacts/four-cell-et/run_four_cell_et.py` from "
        "`/wc1/runs/up/upset-reckoning` using `wepp_260803_hill`.\n",
        encoding="utf-8",
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    for i, metric in enumerate(("Es_fraction", "Q_mm")):
        data = [[float(row[metric]) for row in annual if row["cell"] == cell] for cell, _, _ in CELLS]
        axes[i].boxplot(data, tick_labels=labels, showfliers=False)
        axes[i].set_title("Annual Es/ET" if metric == "Es_fraction" else "Annual hillslope runoff")
        axes[i].set_ylabel("Fraction" if metric == "Es_fraction" else "mm/year")
        axes[i].grid(axis="y", alpha=0.25)
    stem = "four-cell-es-fraction-and-runoff"
    fig.savefig(FIGURES / f"{stem}.png", dpi=200)
    plt.close(fig)
    (FIGURES / f"{stem}.md").write_text(
        "# Palisades four-cell Es fraction and runoff\n\n"
        f"![Four-cell Es fraction and runoff]({stem}.png)\n\n"
        "## Caption\n\nAnnual distributions of soil evaporation as a fraction of total ET and "
        "daily hillslope runoff accumulated by year. Boxes cover the 46 climate years.\n\n"
        "## Interpretation\n\nThe left panel shows whether PMET substantially reallocates ET toward soil "
        "evaporation. The right panel tests the hydrologically consequential link: whether that "
        "reallocation changes runoff generation differently in burned and undisturbed states. "
        "This figure does not measure channel routing or sub-daily peak shape.\n\n"
        "## Provenance\n\nValues are in `artifacts/four-cell-et/four-cell-annual.csv`.\n",
        encoding="utf-8",
    )

    event_7 = [row for row in events if row["window_days"] == 7]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    for i, metric in enumerate(("sum_Es_mm", "pre_event_soil_water_total_mm")):
        data = [[float(row[metric]) for row in event_7 if row["cell"] == cell] for cell, _, _ in CELLS]
        axes[i].boxplot(data, tick_labels=labels, showfliers=False)
        axes[i].set_title(
            "Seven-day antecedent Es"
            if metric == "sum_Es_mm"
            else "Pre-event full-profile soil water",
            fontsize=14,
        )
        axes[i].set_ylabel("mm")
        axes[i].grid(axis="y", alpha=0.25)
    stem = "four-cell-flagged-event-antecedent-state"
    fig.savefig(FIGURES / f"{stem}.png", dpi=200)
    plt.close(fig)
    (FIGURES / f"{stem}.md").write_text(
        "# Palisades four-cell flagged-event antecedent state\n\n"
        f"![Four-cell flagged-event antecedent state]({stem}.png)\n\n"
        "## Caption\n\nSeven-day antecedent soil evaporation and full-profile soil water on the day "
        "before each of the 22 previously flagged outlet inversion events.\n\n"
        "## Interpretation\n\nA PMET mechanism capable of suppressing burned event runoff through excessive "
        "soil evaporation should produce both a larger burned `Es` increment and lower burned "
        "pre-event storage. If PMET changes `Es` without producing that storage response, its "
        "partition is diagnostically questionable but is not carrying the inversion through "
        "antecedent drying.\n\n"
        "## Limitations\n\nThe event dates come from routed watershed results, while these four cells are "
        "hillslope-only replays. They diagnose antecedent/runoff-generation sensitivity, not "
        "channel synchronization.\n",
        encoding="utf-8",
    )


def write_manifest(hills: list[Hill]) -> None:
    paths = [BINARY, LANDUSE_PARQUET, SOILS_PARQUET, AREA_PARQUET, SOURCE_RUNS / "wepp_ui.txt"]
    paths.extend(sorted({hill.undisturbed_man for hill in hills}))
    manifest = {
        "run_id": "upset-reckoning",
        "binary": str(BINARY),
        "cells": [cell for cell, _, _ in CELLS],
        "hillslopes": len(hills),
        "expected_rows_per_run": EXPECTED_ROWS,
        "pmet": {"kcb": KCB, "rawp": RAWP},
        "sidecars": list(SIDECARS),
        "hashes": {str(path): _sha256(path) for path in paths},
        "undisturbed_reconstruction": {
            "management_mapping": {key: value[0] for key, value in UNDISTURBED_MANAGEMENT.items()},
            "soil_rule": "original production soil file before the first disturbance suffix",
        },
    }
    (HERE / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    parser.add_argument("--smoke", action="store_true", help="run H1 in all four cells without writing results")
    parser.add_argument("--analyze-only", action="store_true", help="reload retained daily output without rerunning WEPP")
    args = parser.parse_args()
    hills = load_hills()
    prepare_undisturbed_managements(hills)
    selected = hills[:1] if args.smoke else hills
    if args.analyze_only:
        cell_values = read_daily(HERE / "four-cell-daily.csv.gz")
        write_daily(cell_values)
        annual = annual_rows(cell_values)
        write_dict_csv(HERE / "four-cell-annual.csv", annual)
        summary = summarize(annual)
        write_dict_csv(HERE / "four-cell-summary.csv", summary)
        write_dict_csv(HERE / "four-cell-interactions.csv", interaction_rows(summary))
        events = event_windows(cell_values)
        write_dict_csv(HERE / "four-cell-flagged-event-windows.csv", events)
        write_manifest(hills)
        plot_results(annual, summary, events)
        print("analysis-only regeneration complete")
        return
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    (WORK_ROOT / "lanes").mkdir(parents=True)
    try:
        cell_values: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for cell, land_state, pmet in CELLS:
            print(f"starting {cell}", flush=True)
            cell_values[cell] = run_cell(cell, land_state, pmet, selected, args.workers)
        if args.smoke:
            print("smoke passed: four cells x H1")
            return
        HERE.mkdir(parents=True, exist_ok=True)
        daily_path = write_daily(cell_values)
        annual = annual_rows(cell_values)
        write_dict_csv(HERE / "four-cell-annual.csv", annual)
        summary = summarize(annual)
        write_dict_csv(HERE / "four-cell-summary.csv", summary)
        interactions = interaction_rows(summary)
        write_dict_csv(HERE / "four-cell-interactions.csv", interactions)
        events = event_windows(cell_values)
        write_dict_csv(HERE / "four-cell-flagged-event-windows.csv", events)
        write_manifest(hills)
        plot_results(annual, summary, events)
        print(f"wrote {daily_path}")
        print(f"wrote {HERE / 'four-cell-summary.csv'}")
    finally:
        shutil.rmtree(WORK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
