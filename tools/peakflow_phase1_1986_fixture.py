#!/usr/bin/env python3
"""Verify the frozen 1986 Topanga canopy and ground-cover anomalies."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from peakflow_phase1_fixture import event_values


EXPECTED = {
    "baseline": {"runoff_post_reconciliation_mm": 43.466, "production_peak_mm_h": 3.563},
    "dense-canopy": {"runoff_post_reconciliation_mm": 44.053, "production_peak_mm_h": 294.416},
    "lower-ground-cover": {"runoff_post_reconciliation_mm": 43.408, "production_peak_mm_h": 312.292},
}


def run_lane(binary: Path, fixture: Path, lane: str, root: Path) -> dict[str, float]:
    destination = root / lane
    runs = destination / "runs"
    shutil.copytree(fixture / lane / "runs", runs)
    (destination / "output").mkdir()
    with (runs / "p106.run").open("rb") as stdin:
        result = subprocess.run([binary], cwd=runs, stdin=stdin, capture_output=True, check=False)
    if result.returncode or b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in result.stdout:
        raise RuntimeError(f"WEPP failed for {lane}")
    return event_values(destination / "output", date(1986, 2, 15))


def verify(fixture: Path, binary: Path) -> dict[str, object]:
    baseline = fixture / "baseline/runs"
    for lane in ("dense-canopy", "lower-ground-cover"):
        for path in baseline.iterdir():
            if path.name != "p106.man" and path.read_bytes() != (fixture / lane / "runs" / path.name).read_bytes():
                raise AssertionError(f"unexpected {lane} input difference: {path.name}")
    with tempfile.TemporaryDirectory(prefix="topanga-h106-1986-") as temporary:
        actual = {lane: run_lane(binary, fixture, lane, Path(temporary)) for lane in EXPECTED}
    for lane, expected in EXPECTED.items():
        for field, value in expected.items():
            if abs(actual[lane][field] - value) > 0.003:
                raise AssertionError(f"{lane} {field}: {actual[lane][field]} != {value}")
    result: dict[str, object] = {
        "status": "pass",
        "mechanism_status": "mechanism_unresolved",
        "event": "1986-02-15",
        "lanes": actual,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.fixture.resolve(), args.binary.resolve())
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
