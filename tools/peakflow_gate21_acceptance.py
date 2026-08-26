#!/usr/bin/env python3
"""Run the bounded Gate 2.1 observer/packet/replay acceptance workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

from peakflow_phase1_1986_fixture import verify as verify_1986
from peakflow_phase1_fixture import assert_single_ksat_difference
from peakflow_phase1_negative_control import verify as verify_negative_control
from peakflow_phase1_protocol import SCHEMAS
from peakflow_phase1_replay import packetize, replay, verify_packet


LANES = ("baseline-ksat20", "mutant-ksat35")
EVENT_IDS = {
    "baseline-ksat20": "topanga-h106-1980-02-14-ksat20",
    "mutant-ksat35": "topanga-h106-1980-02-14-ksat35",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_lane(binary: Path, source: Path, destination: Path, tracing: bool) -> tuple[Path, Path]:
    runs = destination / "runs"
    output = destination / "output"
    shutil.copytree(source, runs)
    output.mkdir()
    if tracing:
        (runs / "peak_diag.on").touch()
    with (runs / "p106.run").open("rb") as stdin:
        completed = subprocess.run(binary, cwd=runs, stdin=stdin, capture_output=True, check=False)
    if completed.returncode or b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in completed.stdout:
        raise RuntimeError(f"observer failed for {source.name}; stderr={completed.stderr.decode(errors='replace')}")
    return output, runs / "peak_diag.csv"


def output_hashes(output: Path) -> dict[str, str]:
    return {path.name: sha256(path) for path in sorted(output.iterdir()) if path.is_file()}


def validate_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    jsonschema.validate(manifest, SCHEMAS["build-manifest"])
    return manifest


def accept(args: argparse.Namespace) -> dict[str, Any]:
    fixture = args.fixture.resolve()
    artifacts = args.artifacts.resolve()
    observer_manifest = validate_manifest(args.observer_manifest)
    replay_manifest = validate_manifest(args.replay_manifest)
    if sha256(args.observer_binary) != observer_manifest["executable_sha256"]:
        raise AssertionError("observer executable does not match manifest")
    if sha256(args.replay_binary) != replay_manifest["executable_sha256"]:
        raise AssertionError("replay executable does not match manifest")
    assert_single_ksat_difference(fixture)
    expected = json.loads((fixture / "expected-event.json").read_text())

    parity: dict[str, Any] = {"schema_version": "1.0.0", "observer_marker_present": True, "lanes": {}}
    packets: dict[str, Any] = {}
    reports: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="peakflow-gate21-") as temporary:
        root = Path(temporary)
        for lane in LANES:
            inactive_output, _ = run_lane(args.observer_binary, fixture / lane / "runs", root / lane / "inactive", False)
            active_output, trace = run_lane(args.observer_binary, fixture / lane / "runs", root / lane / "active", True)
            inactive_hashes = output_hashes(inactive_output)
            active_hashes = output_hashes(active_output)
            if inactive_hashes != active_hashes:
                raise AssertionError(f"active tracing changed canonical output for {lane}")
            parity["lanes"][lane] = {"all_byte_equal": True, "files": active_hashes}
            packet = packetize(
                trace, 1980, 45, observer_manifest["build_id"], EVENT_IDS[lane],
                lane, "106", 1, 1,
            )
            verify_packet(packet)
            jsonschema.validate(packet, SCHEMAS["event-packet"])
            report = replay_packet(packet, args.replay_binary)
            jsonschema.validate(report, SCHEMAS["replay-report"])
            contract = expected["lanes"][lane]
            if packet["payload_sha256"] != contract["packet_sha256"]:
                raise AssertionError(f"full-precision packet mismatch for {lane}")
            if report["legacy_input_replay"] != contract["legacy_input_replay"]:
                raise AssertionError(f"legacy replay mismatch for {lane}")
            if report["harmonized_forcing_diagnostic"] != contract["harmonized_forcing_diagnostic"]:
                raise AssertionError(f"harmonized replay mismatch for {lane}")
            packets[lane] = packet
            reports[lane] = report

    fixture_1986 = verify_1986(args.fixture_1986.resolve(), args.observer_binary)
    negative = verify_negative_control(fixture, args.observer_binary)
    result = {
        "status": "pass",
        "scope": "gate_2_1_only",
        "phase_2_census_authorized": False,
        "observer_source_commit": observer_manifest["source_commit"],
        "active_trace_parity": parity,
        "event_packets": packets,
        "replay_reports": reports,
        "fixture_1986": fixture_1986,
        "negative_control": negative,
    }
    artifacts.mkdir(parents=True, exist_ok=True)
    packet_dir = artifacts / "event-packets"
    replay_dir = artifacts / "replay-reports"
    packet_dir.mkdir(exist_ok=True)
    replay_dir.mkdir(exist_ok=True)
    for lane in LANES:
        name = "topanga-h106-1980-ksat20.json" if lane == "baseline-ksat20" else "topanga-h106-1980-ksat35.json"
        (packet_dir / name).write_text(json.dumps(packets[lane], indent=2, sort_keys=True) + "\n")
        (replay_dir / name).write_text(json.dumps(reports[lane], indent=2, sort_keys=True) + "\n")
    (artifacts / "observer-parity-report.json").write_text(json.dumps(parity, indent=2, sort_keys=True) + "\n")
    (artifacts / "gate21-acceptance-report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def replay_packet(packet: dict[str, Any], binary: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="peakflow-packet-") as temporary:
        packet_path = Path(temporary) / "packet.json"
        packet_path.write_text(json.dumps(packet))
        return replay(packet_path, binary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--fixture-1986", type=Path, required=True)
    parser.add_argument("--observer-binary", type=Path, required=True)
    parser.add_argument("--observer-manifest", type=Path, required=True)
    parser.add_argument("--replay-binary", type=Path, required=True)
    parser.add_argument("--replay-manifest", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    accept(parser.parse_args())


if __name__ == "__main__":
    main()
