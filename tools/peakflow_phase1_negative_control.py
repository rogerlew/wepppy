#!/usr/bin/env python3
"""Run the version-9002 Ksat-factor inactive-parameter control."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(binary: Path, source: Path, destination: Path) -> Path:
    runs = destination / "runs"
    output = destination / "output"
    shutil.copytree(source, runs)
    output.mkdir()
    with (runs / "p106.run").open("rb") as stdin:
        result = subprocess.run([binary], cwd=runs, stdin=stdin, capture_output=True, check=False)
    if result.returncode or b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in result.stdout:
        raise RuntimeError("negative-control WEPP run failed")
    return output


def verify(fixture: Path, binary: Path) -> dict[str, object]:
    baseline_runs = fixture / "baseline-ksat20/runs"
    control_runs = fixture / "negative-control-ksatfac95/runs"
    changed_files = sorted(path.name for path in baseline_runs.iterdir() if path.read_bytes() != (control_runs / path.name).read_bytes())
    if changed_files != ["p106.sol"]:
        raise AssertionError(f"unexpected control input differences: {changed_files}")
    before = (baseline_runs / "p106.sol").read_text().splitlines()
    after = (control_runs / "p106.sol").read_text().splitlines()
    changes = [(index + 1, left, right) for index, (left, right) in enumerate(zip(before, after, strict=True)) if left != right]
    if len(changes) != 1 or " 1.3 " not in changes[0][1] or " 9.3 " not in changes[0][2]:
        raise AssertionError(f"unexpected Ksat-factor mutation: {changes}")
    diff_contract = f"p106.sol:{changes[0][0]}:ksatfac:1.3->9.3"
    diff_sha256 = hashlib.sha256(diff_contract.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="topanga-h106-negative-control-") as temporary:
        root = Path(temporary)
        baseline = run(binary, baseline_runs, root / "baseline")
        control = run(binary, control_runs, root / "control")
        names = sorted({path.name for path in baseline.iterdir()} | {path.name for path in control.iterdir()})
        files = []
        for name in names:
            left = baseline / name
            right = control / name
            files.append({
                "file": name,
                "byte_equal": left.exists() and right.exists() and left.read_bytes() == right.read_bytes(),
                "sha256": hashlib.sha256(left.read_bytes()).hexdigest() if left.exists() else None,
            })
    if not all(item["byte_equal"] for item in files):
        raise AssertionError("inactive Ksat-factor mutation changed WEPP output")
    result: dict[str, object] = {
        "status": "pass",
        "mutation": diff_contract,
        "input_diff_sha256": diff_sha256,
        "canonical_outputs_all_byte_equal": True,
        "files": files,
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
