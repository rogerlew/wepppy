#!/usr/bin/env python3
"""Build and run deterministic routing-only htcs ensemble fixtures.

The script copies an existing WEPP routing fixture and retains one selected
source year in every legacy text pass shard, including any fixed-format
continuation lines. It can multiply each selected-year EVENT-record htcs by a
deterministic lognormal factor. Runoff duration, runoff volume, and supplied
peak discharge are never changed in the selected year.
"""

from __future__ import annotations

import argparse
import math
import random
import re
import shutil
import subprocess
from pathlib import Path


DAY_RE = re.compile(r"^(NO EVENT|SUBEVENT|EVENT)(\s+)(\d+)(\s+)(\d+)(.*)$")
HTCS_RE = re.compile(
    r"^(EVENT\s+\d+\s+\d+\s+\S+\s+)(\S+)(.*)$"
)


def hillslope_factor(hillslope: int, seed: int, cv: float) -> float:
    """Return a deterministic, mean-one lognormal hillslope multiplier."""
    if cv == 0.0:
        return 1.0
    sigma = math.sqrt(math.log1p(cv * cv))
    rng = random.Random((seed << 20) ^ hillslope)
    z_value = rng.gauss(0.0, 1.0)
    return math.exp(sigma * z_value - 0.5 * sigma * sigma)


def pass_area(path: Path) -> float:
    lines = path.read_text(encoding="ascii").splitlines()
    if len(lines) < 3:
        raise ValueError(f"pass shard is too short: {path}")
    return float(lines[2])


def rewrite_pass(path: Path, source_year: int, cv: float, factor: float) -> None:
    lines = path.read_text(encoding="ascii").splitlines(keepends=True)
    if len(lines) < 6:
        raise ValueError(f"pass shard is too short: {path}")
    hill_match = re.fullmatch(r"H(\d+)\.pass\.dat", path.name)
    if hill_match is None:
        raise ValueError(f"unexpected pass shard name: {path.name}")
    header = lines[:5]
    header_tokens = header[1].split()
    if len(header_tokens) != 2:
        raise ValueError(f"unexpected pass header: {path}: {header[1]!r}")
    header[1] = f"{1:5d}{int(header_tokens[1]):10d}\n"
    records: list[list[str]] = []
    for line in lines[5:]:
        if DAY_RE.match(line) is not None:
            records.append([line])
        elif records:
            records[-1].append(line)
        else:
            raise ValueError(f"orphan pass continuation: {path}: {line!r}")

    selected: list[str] = []
    selected_record_count = 0
    for record in records:
        line = record[0]
        match = DAY_RE.match(line)
        if match is None:
            raise AssertionError("record grouping lost its daily-record leader")
        record_year = int(match.group(3))
        record_day = int(match.group(5))
        if record_year != source_year:
            continue
        selected_record_count += 1
        rewritten = (
            f"{match.group(1)}{match.group(2)}"
            f"{1:>{len(match.group(3))}}{match.group(4)}"
            f"{record_day:>{len(match.group(5))}}{match.group(6)}"
        )
        relabeled = rewritten
        if match.group(1) == "EVENT" and cv > 0.0:
            htcs_match = HTCS_RE.match(rewritten)
            if htcs_match is None:
                raise ValueError(f"unable to locate htcs: {path}: {rewritten!r}")
            htcs = float(htcs_match.group(2)) * factor
            rewritten = f"{htcs_match.group(1)}{htcs:11.5E}{htcs_match.group(3)}"
        if line.endswith("\n"):
            rewritten += "\n"
        if match.group(1) == "EVENT" and cv > 0.0:
            expected_fields = relabeled.split()
            actual_fields = rewritten.split()
            expected_fields[4] = actual_fields[4]
            if actual_fields != expected_fields:
                raise AssertionError(f"non-htcs EVENT field changed: {path}")
            if len(rewritten.rstrip("\n")) != len(relabeled):
                raise AssertionError(f"fixed-format EVENT width changed: {path}")
        elif rewritten.rstrip("\n") != relabeled:
            raise AssertionError(f"unperturbed selected-year record changed: {path}")
        selected.append(rewritten)
        selected.extend(record[1:])

    if selected_record_count not in (365, 366):
        raise ValueError(
            f"unexpected selected-year record count in {path}: {selected_record_count}"
        )
    path.write_text("".join(header + selected), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--lane", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--source-year", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cv", type=float, default=0.0)
    args = parser.parse_args()

    if args.cv < 0.0:
        parser.error("--cv must be nonnegative")
    if args.lane.exists():
        parser.error(f"lane already exists: {args.lane}")

    shutil.copytree(args.fixture, args.lane / "wepp")
    pass_paths = sorted((args.lane / "wepp" / "output").glob("H*.pass.dat"))
    if len(pass_paths) != 138:
        parser.error(f"expected 138 pass shards, found {len(pass_paths)}")
    raw_factors = {
        path: hillslope_factor(
            int(path.name[1 : -len(".pass.dat")]), args.seed, args.cv
        )
        for path in pass_paths
    }
    areas = {path: pass_area(path) for path in pass_paths}
    weighted_mean = sum(areas[p] * raw_factors[p] for p in pass_paths) / sum(
        areas.values()
    )
    factors: list[tuple[int, float, float, float]] = []
    for pass_path in pass_paths:
        hill = int(pass_path.name[1 : -len(".pass.dat")])
        factor = raw_factors[pass_path] / weighted_mean
        rewrite_pass(pass_path, args.source_year, args.cv, factor)
        factors.append((hill, areas[pass_path], raw_factors[pass_path], factor))

    (args.lane / "factors.csv").write_text(
        "hillslope,area_m2,raw_factor,normalized_factor\n"
        + "".join(
            f"{hill},{area:.12g},{raw:.12g},{factor:.12g}\n"
            for hill, area, raw, factor in factors
        ),
        encoding="ascii",
    )
    achieved_mean = sum(area * factor for _, area, _, factor in factors) / sum(
        area for _, area, _, _ in factors
    )
    (args.lane / "normalization.txt").write_text(
        f"raw_area_weighted_mean={weighted_mean:.17g}\n"
        f"normalized_area_weighted_mean={achieved_mean:.17g}\n",
        encoding="ascii",
    )
    run_dir = args.lane / "wepp" / "runs"
    with (run_dir / "pw0.run").open("rb") as stdin_file, (
        args.lane / "stdout.txt"
    ).open("wb") as stdout_file, (args.lane / "stderr.txt").open("wb") as stderr_file:
        completed = subprocess.run(
            [str(args.binary)],
            cwd=run_dir,
            stdin=stdin_file,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
        )
    stdout_text = (args.lane / "stdout.txt").read_text(
        encoding="ascii", errors="replace"
    )
    stderr_text = (args.lane / "stderr.txt").read_text(
        encoding="ascii", errors="replace"
    )
    failures: list[str] = []
    if completed.returncode != 0:
        failures.append(f"model return code was {completed.returncode}")
    if stderr_text:
        failures.append("model stderr was not empty")
    if "WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY" not in stdout_text:
        failures.append("watershed success marker was absent")
    if "->WEPP hourly water seepage update set (UI code)" not in stdout_text:
        failures.append("hourly-water-balance marker was absent")
    if "Program stop" in stdout_text or "Fortran runtime error" in stdout_text:
        failures.append("model stdout contained a runtime failure marker")
    if failures:
        raise RuntimeError("; ".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
