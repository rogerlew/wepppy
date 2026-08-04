#!/usr/bin/env python3
"""Run an isolated PMET kcb/rawp grid for forest fire severities."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np


SOURCE = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
WORK_ROOT = Path("/wc1/ablation/stevens-canyon-pmet-calibration-20260804")
HERE = Path(__file__).resolve().parent
BINARY = SOURCE / "bin" / "wepp_260803_hill"
SIDECARS = ("gwcoeff.txt", "snow.txt", "wepp_ui.txt", "chntyp.txt", "tc.txt", "chan.inp")
AREAS = {
    50: 80.10, 51: 140.22, 52: 210.33, 53: 81.90, 54: 64.71,
    55: 73.44, 56: 82.62, 58: 256.68, 59: 83.07, 60: 2.34, 61: 4.68,
}
SEVERITIES = {
    "low": ("burned", (50, 56, 58, 60, 61), (0.65, 0.80), (0.15, 0.30), 0.70, 0.22),
    "moderate": ("burned", (51, 52, 53, 54, 55, 59), (0.50, 0.70), (0.25, 0.40), 0.60, 0.33),
    "high": ("high_severity", (50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61),
             (0.40, 0.60), (0.30, 0.45), 0.50, 0.38),
}
KCB_VALUES = tuple(round(value, 2) for value in np.arange(0.35, 0.951, 0.10))
RAWP_VALUES = tuple(round(value, 2) for value in np.arange(0.30, 0.801, 0.10))
COLUMNS = ("ofe", "day", "year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
           "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water",
           "snow_water", "QOFE", "tile", "irrigation", "area",
           "soil_water_total", "profile_depth", "porosity_capacity",
           "field_capacity", "wilting_point")


@dataclass(frozen=True)
class Task:
    severity: str
    source_scenario: str
    hill: int
    kcb: float
    rawp: float


def parse_annual(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(COLUMNS):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    values = np.asarray(rows)
    if values.shape != (36_525, len(COLUMNS)) or not np.isfinite(values).all():
        raise ValueError(f"invalid water balance {path}: {values.shape}")
    result = []
    for name in ("Ep", "Es", "Er"):
        column = values[:, COLUMNS.index(name)]
        years = values[:, COLUMNS.index("year")].astype(int)
        result.append(np.asarray([column[years == year].sum() for year in range(1, 101)]))
    return result[0], result[1], result[2]


def plant_name(man_path: Path) -> str:
    text = man_path.read_text(encoding="utf-8")
    match = re.search(r"\n1 # ncrop\n([^\n]+)", text)
    if match is None:
        raise ValueError(f"cannot identify plant name in {man_path}")
    return match.group(1).strip()


def disable_graphics(run_path: Path) -> None:
    lines = run_path.read_text(encoding="utf-8").splitlines()
    if lines[16] == "Yes":
        lines[16] = "No"
        lines.pop(17)
    if lines[16] != "No":
        raise ValueError(f"unexpected graphics control in {run_path}")
    run_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute(task: Task) -> tuple[Task, np.ndarray, np.ndarray, np.ndarray]:
    lane = WORK_ROOT / "lanes" / f"{task.severity}_k{task.kcb:.2f}_r{task.rawp:.2f}_h{task.hill}"
    runs = lane / "runs"
    output = lane / "output"
    runs.mkdir(parents=True)
    output.mkdir()
    source = SOURCE / task.source_scenario / "wepp" / "runs"
    try:
        for extension in ("run", "man", "slp", "cli", "sol"):
            shutil.copy2(source / f"p{task.hill}.{extension}", runs / f"p{task.hill}.{extension}")
        for sidecar in SIDECARS:
            shutil.copy2(source / sidecar, runs / sidecar)
        disable_graphics(runs / f"p{task.hill}.run")
        crop = plant_name(runs / f"p{task.hill}.man")
        (runs / "pmetpara.txt").write_text(
            f"1\n{crop},{task.kcb},{task.rawp},1,{task.severity}_calibration\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [str(BINARY)],
            cwd=runs,
            stdin=(runs / f"p{task.hill}.run").open("rb"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0 or result.stderr:
            raise RuntimeError(
                f"{task} failed rc={result.returncode}: {result.stderr.decode(errors='replace')}"
            )
        ep, es, er = parse_annual(output / f"H{task.hill}.wat.dat")
        return task, ep, es, er
    finally:
        shutil.rmtree(lane, ignore_errors=True)


def undisturbed_reference(hills: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = np.asarray([AREAS[hill] for hill in hills], dtype=float)
    weights /= weights.sum()
    components = []
    for index in range(3):
        values = [parse_annual(SOURCE / "undisturbed" / "wepp" / "output" / f"H{hill}.wat.dat")[index]
                  for hill in hills]
        components.append(np.average(np.vstack(values), axis=0, weights=weights))
    return components[0], components[1], components[2]


def score_distance(value: float, bounds: tuple[float, float], center: float) -> float:
    half_width = (bounds[1] - bounds[0]) / 2
    central = abs(value - center) / half_width
    outside = max(bounds[0] - value, 0.0, value - bounds[1]) / half_width
    return central + 2 * outside


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    args = parser.parse_args()
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    (WORK_ROOT / "lanes").mkdir(parents=True)

    tasks = [
        Task(severity, config[0], hill, kcb, rawp)
        for severity, config in SEVERITIES.items()
        for kcb in KCB_VALUES
        for rawp in RAWP_VALUES
        for hill in config[1]
    ]
    grouped: dict[tuple[str, float, float], dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]] = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(execute, task) for task in tasks]
        for future in as_completed(futures):
            task, ep, es, er = future.result()
            grouped.setdefault((task.severity, task.kcb, task.rawp), {})[task.hill] = (ep, es, er)
            completed += 1
            if completed % 50 == 0 or completed == len(tasks):
                print(f"completed {completed}/{len(tasks)}", flush=True)

    summary_rows = []
    annual_rows = []
    for severity, config in SEVERITIES.items():
        _, hills, et_bounds, es_bounds, et_center, es_center = config
        weights = np.asarray([AREAS[hill] for hill in hills], dtype=float)
        weights /= weights.sum()
        ref_components = undisturbed_reference(hills)
        ref_et = sum(ref_components)
        for kcb in KCB_VALUES:
            for rawp in RAWP_VALUES:
                hill_results = grouped[(severity, kcb, rawp)]
                components = [
                    np.average(np.vstack([hill_results[hill][index] for hill in hills]), axis=0, weights=weights)
                    for index in range(3)
                ]
                ep, es, er = components
                et = ep + es + er
                et_ratio = et / ref_et
                es_fraction = np.divide(es, et, out=np.zeros_like(es), where=et > 0)
                joint = (et_ratio >= et_bounds[0]) & (et_ratio <= et_bounds[1]) & \
                        (es_fraction >= es_bounds[0]) & (es_fraction <= es_bounds[1])
                median_ratio = float(np.median(et_ratio))
                median_fraction = float(np.median(es_fraction))
                score = score_distance(median_ratio, et_bounds, et_center) + \
                        score_distance(median_fraction, es_bounds, es_center)
                summary_rows.append((severity, kcb, rawp, score, median_ratio,
                                     np.percentile(et_ratio, 10), np.percentile(et_ratio, 90),
                                     median_fraction, np.percentile(es_fraction, 10),
                                     np.percentile(es_fraction, 90), joint.mean(),
                                     np.median(ep), np.median(es), np.median(er), np.median(et),
                                     np.median(ref_et)))
                for year in range(100):
                    annual_rows.append((severity, kcb, rawp, year + 1, ep[year], es[year], er[year],
                                        et[year], ref_et[year], et_ratio[year], es_fraction[year],
                                        int(joint[year])))

    summary_rows.sort(key=lambda row: (row[0], row[3], row[1], row[2]))
    summary_path = HERE / "pmet-calibration-summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("severity", "kcb", "rawp", "score", "median_et_ratio", "p10_et_ratio",
                         "p90_et_ratio", "median_es_fraction", "p10_es_fraction", "p90_es_fraction",
                         "joint_pass_fraction", "median_ep_mm", "median_es_mm", "median_er_mm",
                         "median_et_mm", "median_undisturbed_et_mm"))
        writer.writerows(summary_rows)
    annual_path = HERE / "pmet-calibration-annual.csv.gz"
    with annual_path.open("wb") as raw_stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(("severity", "kcb", "rawp", "year", "ep_mm", "es_mm", "er_mm",
                                 "et_mm", "undisturbed_et_mm", "et_ratio", "es_fraction",
                                 "joint_pass"))
                writer.writerows(annual_rows)
    shutil.rmtree(WORK_ROOT / "lanes")
    print(f"wrote {summary_path}")
    print(f"wrote {annual_path}")


if __name__ == "__main__":
    main()
