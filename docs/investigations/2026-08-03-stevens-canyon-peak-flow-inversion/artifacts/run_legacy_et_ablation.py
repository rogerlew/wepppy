#!/usr/bin/env python3
"""Run the Stevens Canyon burn matrix with WEPP's legacy ET routine."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np


SOURCE = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
WORK_ROOT = Path("/wc1/ablation/stevens-canyon-legacy-et-ablation-20260804")
HERE = Path(__file__).resolve().parent
BINARY = SOURCE / "bin" / "wepp_260803_hill"
SIDECARS = ("gwcoeff.txt", "snow.txt", "wepp_ui.txt", "chntyp.txt", "tc.txt", "chan.inp")
HILLS = (50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61)
AREAS = {
    50: 80.10, 51: 140.22, 52: 210.33, 53: 81.90, 54: 64.71,
    55: 73.44, 56: 82.62, 58: 256.68, 59: 83.07, 60: 2.34, 61: 4.68,
}
SEVERITIES = {
    "low": ("burned", (50, 56, 58, 60, 61), (0.65, 0.80), (0.15, 0.30)),
    "moderate": ("burned", (51, 52, 53, 54, 55, 59), (0.50, 0.70), (0.25, 0.40)),
    "high": ("high_severity", HILLS, (0.40, 0.60), (0.30, 0.45)),
}
COLUMNS = ("ofe", "day", "year", "P", "RM", "Q", "Ep", "Es", "Er", "Dp",
           "UpStrmQ", "SubRIn", "latqcc", "soil_water", "frozen_water",
           "snow_water", "QOFE", "tile", "irrigation", "area",
           "soil_water_total", "profile_depth", "porosity_capacity",
           "field_capacity", "wilting_point")
PMET_MARKER = "FAO Penman-Monteith ET Method Implemented"


@dataclass(frozen=True)
class Task:
    scenario: str
    hill: int


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
    years = values[:, COLUMNS.index("year")].astype(int)
    return tuple(
        np.asarray([values[years == year, COLUMNS.index(name)].sum()
                    for year in range(1, 101)])
        for name in ("Ep", "Es", "Er")
    )


def disable_graphics(run_path: Path) -> None:
    lines = run_path.read_text(encoding="utf-8").splitlines()
    if lines[16] == "Yes":
        lines[16] = "No"
        lines.pop(17)
    if lines[16] != "No":
        raise ValueError(f"unexpected graphics control in {run_path}")
    run_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute(task: Task) -> tuple[Task, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    lane = WORK_ROOT / "lanes" / f"{task.scenario}_h{task.hill}"
    runs = lane / "runs"
    output = lane / "output"
    runs.mkdir(parents=True)
    output.mkdir()
    source = SOURCE / task.scenario / "wepp" / "runs"
    try:
        for extension in ("run", "man", "slp", "cli", "sol"):
            shutil.copy2(source / f"p{task.hill}.{extension}", runs / f"p{task.hill}.{extension}")
        for sidecar in SIDECARS:
            shutil.copy2(source / sidecar, runs / sidecar)
        disable_graphics(runs / f"p{task.hill}.run")
        if (runs / "pmetpara.txt").exists():
            raise RuntimeError(f"PMET sidecar unexpectedly present in {runs}")
        result = subprocess.run(
            [str(BINARY)], cwd=runs,
            stdin=(runs / f"p{task.hill}.run").open("rb"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        stdout = result.stdout.decode(errors="replace")
        stderr = result.stderr.decode(errors="replace")
        if result.returncode != 0 or stderr:
            raise RuntimeError(f"{task} failed rc={result.returncode}: {stderr}")
        if PMET_MARKER in stdout:
            raise RuntimeError(f"{task} selected PMET despite absent pmetpara.txt")
        return task, parse_annual(output / f"H{task.hill}.wat.dat")
    finally:
        shutil.rmtree(lane, ignore_errors=True)


def aggregate(
    values: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]],
    scenario: str,
    hills: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = np.asarray([AREAS[hill] for hill in hills], dtype=float)
    weights /= weights.sum()
    return tuple(
        np.average(np.vstack([values[(scenario, hill)][index] for hill in hills]),
                   axis=0, weights=weights)
        for index in range(3)
    )


def fixture_pmet(scenario: str, hills: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = {
        (scenario, hill): parse_annual(SOURCE / scenario / "wepp" / "output" / f"H{hill}.wat.dat")
        for hill in hills
    }
    return aggregate(values, scenario, hills)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    args = parser.parse_args()
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    (WORK_ROOT / "lanes").mkdir(parents=True)

    tasks = [Task(scenario, hill) for scenario in ("undisturbed", "burned", "high_severity")
             for hill in HILLS]
    results: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(execute, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            task, components = future.result()
            results[(task.scenario, task.hill)] = components
            print(f"completed {completed}/{len(tasks)}: {task.scenario} H{task.hill}", flush=True)

    annual_rows = []
    summary_rows = []
    for severity, (scenario, hills, et_bounds, es_bounds) in SEVERITIES.items():
        burned = aggregate(results, scenario, hills)
        undisturbed = aggregate(results, "undisturbed", hills)
        pmet_burned = fixture_pmet(scenario, hills)
        pmet_undisturbed = fixture_pmet("undisturbed", hills)
        ep, es, er = burned
        uep, ues, uer = undisturbed
        et = ep + es + er
        uet = uep + ues + uer
        pmet_et = sum(pmet_burned)
        pmet_uet = sum(pmet_undisturbed)
        ratio = et / uet
        es_fraction = np.divide(es, et, out=np.zeros_like(es), where=et > 0)
        undisturbed_es_fraction = np.divide(ues, uet, out=np.zeros_like(ues), where=uet > 0)
        pmet_ratio = pmet_et / pmet_uet
        pmet_es_fraction = np.divide(pmet_burned[1], pmet_et,
                                     out=np.zeros_like(pmet_et), where=pmet_et > 0)
        joint = ((ratio >= et_bounds[0]) & (ratio <= et_bounds[1]) &
                 (es_fraction >= es_bounds[0]) & (es_fraction <= es_bounds[1]))
        summary_rows.append((
            severity, len(hills), np.median(ratio), np.percentile(ratio, 10),
            np.percentile(ratio, 90), np.median(es_fraction),
            np.percentile(es_fraction, 10), np.percentile(es_fraction, 90), joint.mean(),
            np.median(ep), np.median(es), np.median(er), np.median(et),
            np.median(uep), np.median(ues), np.median(uer), np.median(uet),
            np.median(undisturbed_es_fraction), np.median(pmet_ratio),
            np.median(pmet_es_fraction), np.median(pmet_et), np.median(pmet_uet),
        ))
        for year in range(100):
            annual_rows.append((severity, year + 1, ep[year], es[year], er[year], et[year],
                                uep[year], ues[year], uer[year], uet[year], ratio[year],
                                es_fraction[year], undisturbed_es_fraction[year],
                                pmet_ratio[year], pmet_es_fraction[year], int(joint[year])))

    summary_path = HERE / "legacy-et-ablation-summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("severity", "hillslopes", "median_et_ratio", "p10_et_ratio",
                         "p90_et_ratio", "median_es_fraction", "p10_es_fraction",
                         "p90_es_fraction", "joint_pass_fraction", "median_ep_mm",
                         "median_es_mm", "median_er_mm", "median_et_mm",
                         "median_undisturbed_ep_mm", "median_undisturbed_es_mm",
                         "median_undisturbed_er_mm", "median_undisturbed_et_mm",
                         "median_undisturbed_es_fraction", "pmet_median_et_ratio",
                         "pmet_median_es_fraction", "pmet_median_et_mm",
                         "pmet_median_undisturbed_et_mm"))
        writer.writerows(summary_rows)
    annual_path = HERE / "legacy-et-ablation-annual.csv.gz"
    with annual_path.open("wb") as raw_stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(("severity", "year", "ep_mm", "es_mm", "er_mm", "et_mm",
                                 "undisturbed_ep_mm", "undisturbed_es_mm", "undisturbed_er_mm",
                                 "undisturbed_et_mm", "et_ratio", "es_fraction",
                                 "undisturbed_es_fraction", "pmet_et_ratio",
                                 "pmet_es_fraction", "joint_pass"))
                writer.writerows(annual_rows)
    shutil.rmtree(WORK_ROOT)
    print(f"wrote {summary_path}")
    print(f"wrote {annual_path}")


if __name__ == "__main__":
    main()
