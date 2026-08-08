#!/usr/bin/env python3
"""Run and verify the compact Topanga Hill 106 Ksat fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any


INPUT_NAMES = (
    "gwcoeff.txt", "p106.cli", "p106.man", "p106.run", "p106.slp",
    "p106.sol", "pmetpara.txt", "snow.txt", "wepp_ui.txt",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _numeric_rows(path: Path, minimum_fields: int) -> list[list[float]]:
    rows: list[list[float]] = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) < minimum_fields:
            continue
        try:
            rows.append([float(field) for field in fields])
        except ValueError:
            continue
    return rows


def event_values(output_dir: Path, target: date = date(1980, 2, 14)) -> dict[str, float]:
    water_rows = _numeric_rows(output_dir / "H106.wat.dat", 21)
    first_year = int(min(row[2] for row in water_rows))
    prior_target = target - timedelta(days=1)
    prior_water = next(
        row for row in water_rows
        if date(int(row[2]), 1, 1) + timedelta(days=int(row[1]) - 1) == prior_target
    )
    element_rows = _numeric_rows(output_dir / "H106.element.dat", 24)
    event = next(
        row for row in element_rows
        if date(first_year + int(row[3]) - 1, int(row[2]), int(row[1])) == target
    )
    return {
        "precip_mm": event[4],
        "runoff_post_reconciliation_mm": event[5],
        "effective_intensity_mm_h": event[6],
        "production_peak_mm_h": event[7],
        "rectangular_effective_duration_h": event[8],
        "effective_surface_ksat_mm_h": event[10],
        "antecedent_profile_water_mm": prior_water[20],
    }


def assert_single_ksat_difference(fixture: Path) -> str:
    baseline = fixture / "baseline-ksat20/runs"
    mutant = fixture / "mutant-ksat35/runs"
    for name in INPUT_NAMES:
        if name == "p106.sol":
            continue
        if (baseline / name).read_bytes() != (mutant / name).read_bytes():
            raise AssertionError(f"unexpected differing input: {name}")
    left = (baseline / "p106.sol").read_text().splitlines()
    right = (mutant / "p106.sol").read_text().splitlines()
    differences = [(index + 1, a, b) for index, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]
    if len(differences) != 1:
        raise AssertionError(f"expected one soil line difference, found {len(differences)}")
    line, before, after = differences[0]
    before_fields = before.split()
    after_fields = after.split()
    changed = [(i, a, b) for i, (a, b) in enumerate(zip(before_fields, after_fields, strict=True)) if a != b]
    if changed != [(2, "20", "35")]:
        raise AssertionError(f"unexpected soil token difference: {changed}")
    return f"p106.sol:{line}: first-horizon Ksat 20 -> 35 mm/h"


def run_lane(binary: Path, source_runs: Path, destination: Path) -> dict[str, float]:
    runs = destination / "runs"
    output = destination / "output"
    shutil.copytree(source_runs, runs)
    output.mkdir()
    with (runs / "p106.run").open("rb") as stdin, (runs / "stdout.txt").open("wb") as stdout, (runs / "stderr.txt").open("wb") as stderr:
        completed = subprocess.run([binary], cwd=runs, stdin=stdin, stdout=stdout, stderr=stderr, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"WEPP failed for {source_runs}: {completed.returncode}")
    if b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in (runs / "stdout.txt").read_bytes():
        raise RuntimeError(f"WEPP success marker missing for {source_runs}")
    return event_values(output)


def assert_expected(actual: dict[str, float], expected: dict[str, Any]) -> None:
    for field, contract in expected.items():
        if not isinstance(contract, dict) or "value" not in contract:
            continue
        tolerance = float(contract.get("absolute_tolerance", 0.0))
        delta = abs(actual[field] - float(contract["value"]))
        if delta > tolerance:
            raise AssertionError(f"{field}: actual={actual[field]} expected={contract['value']} tolerance={tolerance}")


def verify(fixture: Path, binary: Path) -> dict[str, Any]:
    difference = assert_single_ksat_difference(fixture)
    expected = json.loads((fixture / "expected-event.json").read_text())
    if sha256(binary) != expected["executable_sha256"]:
        raise AssertionError("executable SHA-256 does not match expected-event.json")
    with tempfile.TemporaryDirectory(prefix="topanga-h106-1980-ksat-") as temporary:
        root = Path(temporary)
        actual = {
            lane: run_lane(binary, fixture / lane / "runs", root / lane)
            for lane in ("baseline-ksat20", "mutant-ksat35")
        }
    for lane, values in actual.items():
        assert_expected(values, expected["lanes"][lane]["published_output"])
    result = {"status": "pass", "input_difference": difference, "lanes": actual}
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    verify(args.fixture.resolve(), args.binary.resolve())


if __name__ == "__main__":
    main()
