#!/usr/bin/env python3
"""Run compact day-203 htcs ensembles and retain only compact evidence."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


REACHES = {169, 172, 173, 193}


def selected_rows(path: Path, expected_columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        fields = line.split()
        if (
            len(fields) == expected_columns
            and fields[0].isdigit()
            and int(fields[0]) == 1
            and int(fields[1]) == 203
            and int(fields[2]) in REACHES
        ):
            rows.append(fields)
    if len(rows) != len(REACHES):
        raise ValueError(f"expected four selected rows in {path}, found {len(rows)}")
    return rows


def branch_audit(output_dir: Path) -> tuple[int, int, int, int]:
    active = rectangular = clamp_low = clamp_high = 0
    for path in output_dir.glob("H*.pass.dat"):
        for line in path.read_text(encoding="ascii").splitlines():
            fields = line.split()
            if len(fields) < 13 or fields[0] != "EVENT" or int(fields[1]) != 1:
                continue
            duration = float(fields[3])
            htcs_seconds = float(fields[4]) * 3600.0
            volume = float(fields[7])
            peak = float(fields[12])
            if volume >= peak * duration - 1.0e-6:
                rectangular += 1
            else:
                active += 1
                if htcs_seconds <= 0.001 * duration:
                    clamp_low += 1
                if htcs_seconds >= 0.999 * duration:
                    clamp_high += 1
    return active, rectangular, clamp_low, clamp_high


def run_lane(task: tuple[int, float, str, str, str, str]) -> list[dict[str, object]]:
    seed, cv, fixture, binary, runner, temp_root = task
    lane = Path(temp_root) / f"cv{cv:.2f}-seed{seed:03d}"
    command = [
        "python3",
        runner,
        "--fixture",
        fixture,
        "--lane",
        str(lane),
        "--binary",
        binary,
        "--source-year",
        "34",
        "--seed",
        str(seed),
        "--cv",
        str(cv),
    ]
    try:
        subprocess.run(command, check=True)
        normalization = dict(
            line.split("=", 1)
            for line in (lane / "normalization.txt").read_text().splitlines()
        )
        active, rectangular, clamp_low, clamp_high = branch_audit(
            lane / "wepp" / "output"
        )
        peaks = {
            int(row[2]): (float(row[4]), float(row[5]))
            for row in selected_rows(lane / "wepp" / "runs" / "chan.out", 6)
        }
        balances = {
            int(row[2]): tuple(float(value) for value in row[4:10])
            for row in selected_rows(lane / "wepp" / "runs" / "chanwb.out", 10)
        }
        result: list[dict[str, object]] = []
        for reach in sorted(REACHES):
            inflow, outflow, storage, baseflow, loss, balance = balances[reach]
            result.append(
                {
                    "seed": seed,
                    "cv": cv,
                    "wepp_id": reach,
                    "peak_time_s": peaks[reach][0],
                    "peak_m3_s": peaks[reach][1],
                    "inflow_m3": inflow,
                    "outflow_m3": outflow,
                    "storage_m3": storage,
                    "baseflow_m3": baseflow,
                    "loss_m3": loss,
                    "balance_m3": balance,
                    "active_records": active,
                    "rectangular_records": rectangular,
                    "clamp_low_records": clamp_low,
                    "clamp_high_records": clamp_high,
                    "area_weighted_factor_mean": float(
                        normalization["normalized_area_weighted_mean"]
                    ),
                }
            )
        return result
    finally:
        if lane.exists():
            shutil.rmtree(lane)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--temp-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.temp_root.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    tasks = [
        (seed, cv, args.fixture, args.binary, args.runner, str(args.temp_root))
        for cv in (0.10, 0.25, 0.50)
        for seed in range(1, args.seeds + 1)
    ]
    rows: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_lane, task): task for task in tasks}
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.extend(future.result())
            print(f"completed={completed}/{len(tasks)}", flush=True)

    rows.sort(key=lambda row: (float(row["cv"]), int(row["seed"]), int(row["wepp_id"])))
    with args.output.open("w", newline="", encoding="ascii") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
