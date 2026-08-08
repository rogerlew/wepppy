#!/usr/bin/env python3
"""Create immutable WEPP event packets and replay peak solvers out of process."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def packetize(trace: Path, year: int, day: int, build_id: str, event_id: str) -> dict[str, Any]:
    rows = [line.split(",") for line in trace.read_text().splitlines()]
    prefix = (str(year), str(day), "1")
    scalar = next(row for row in rows if row[0] == "SCALAR" and tuple(row[1:4]) == prefix)
    result = next(row for row in rows if row[0] == "RESULT" and tuple(row[1:4]) == prefix)
    pre = [row for row in rows if row[0] == "PRE" and tuple(row[1:4]) == prefix]
    post = [row for row in rows if row[0] == "POST" and tuple(row[1:4]) == prefix]
    assignment_modes = {0: "none", 1: "positive_excess", 2: "storm_or_upstream", 3: "fallback_24h"}
    payload = {
        "event_id": event_id,
        "source_build_id": build_id,
        "scalars": {
            "calendar_year": year,
            "model_day": day,
            "ofe": 1,
            "runoff_post_reconciliation_m": float(scalar[4]),
            "surplus_depth_m": float(scalar[5]),
            "positive_excess_duration_s": float(scalar[6]),
            "surplus_assignment_duration_s": float(scalar[7]),
            "remax_pre_surplus_m_s": float(scalar[8]),
            "forcing_max_post_surplus_m_s": float(scalar[9]),
            "surplus_added_rate_m_s": float(scalar[10]),
            "tp2_s": float(scalar[11]),
            "alpha": float(scalar[12]),
            "m": float(scalar[13]),
            "effective_length_m": float(scalar[14]),
            "ns": int(scalar[15]),
            "surplus_assignment_mode": assignment_modes[int(scalar[16])],
        },
        "pre_surplus_forcing": [],
        "post_surplus_forcing": [
            {"point_ordinal": int(row[4]), "time_s": float(row[5]), "rate_m_s": float(row[6])}
            for row in post
        ],
        "production": {"selected_solver": result[4], "peak_m_s": float(result[5])},
    }
    positive_pre = {
        int(row[4]): (float(row[5]), float(row[6]), float(row[7])) for row in pre
    }
    post_points = payload["post_surplus_forcing"]
    for index, point in enumerate(post_points[:-1], start=1):
        start, end, rate = positive_pre.get(
            index,
            (point["time_s"], post_points[index]["time_s"], 0.0),
        )
        payload["pre_surplus_forcing"].append({
            "interval_ordinal": index,
            "start_s": start,
            "end_s": end,
            "rate_m_s": rate,
        })
    return {"schema_version": SCHEMA_VERSION, "payload_sha256": canonical_sha256(payload), **payload}


def verify_packet(packet: dict[str, Any]) -> None:
    payload = {key: value for key, value in packet.items() if key not in {"schema_version", "payload_sha256"}}
    if packet["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported packet schema")
    if canonical_sha256(payload) != packet["payload_sha256"]:
        raise ValueError("event packet content hash mismatch")


def app_diagnostics(
    scalars: dict[str, Any], remax: float, runoff: float | None = None, duration: float | None = None
) -> dict[str, Any]:
    runoff = scalars["runoff_post_reconciliation_m"] if runoff is None else runoff
    duration = scalars["surplus_assignment_duration_s"] if duration is None else duration
    vave = runoff / duration
    m = scalars["m"]
    te = (scalars["effective_length_m"] / (scalars["alpha"] * vave ** (m - 1.0))) ** (1.0 / m)
    tstar = te / duration
    vstar = vave / remax
    if tstar >= 1.0:
        branch = "partial_equilibrium"
    elif vstar < 1.0:
        a = 0.6 * (1.0 - vstar)
        tc = (1.0 - math.sqrt(1.0 - 4.0 * a * vstar)) / (2.0 * a)
        branch = "quasi_equilibrium_a" if tstar > tc else "quasi_equilibrium_b"
    else:
        branch = "constant_or_out_of_domain"
        tc = None
    return {
        "vave_m_s": vave,
        "vstar": vstar,
        "tstar": tstar,
        "tc": tc if "tc" in locals() else None,
        "equation_branch": branch,
        "within_documented_vstar_domain": 0.0 < vstar <= 1.0,
        "within_documented_tstar_domain": math.isfinite(tstar) and tstar > 0.0,
        "finite_result": all(math.isfinite(value) for value in (vave, vstar, tstar)),
    }


def run_driver(
    binary: Path,
    packet: dict[str, Any],
    remax: float,
    runoff: float | None = None,
    duration: float | None = None,
) -> dict[str, Any]:
    scalars = packet["scalars"]
    points = packet["post_surplus_forcing"]
    header = [
        scalars["alpha"], scalars["m"], scalars["effective_length_m"],
        scalars["runoff_post_reconciliation_m"] if runoff is None else runoff,
        remax,
        scalars["surplus_assignment_duration_s"] if duration is None else duration,
        scalars["ns"],
    ]
    text = " ".join(map(str, header)) + "\n"
    text += "".join(f"{point['time_s']} {point['rate_m_s']}\n" for point in points)
    completed = subprocess.run([binary], input=text, text=True, capture_output=True, check=True)
    fields = completed.stdout.split()
    return {
        "appmth_peak_m_s": float(fields[0]),
        "hdrive_peak_m_s": float(fields[1]),
        "hdrive_nqt": int(fields[2]),
        "hdrive_nq": int(fields[3]),
        "hdrive_final_routed_volume_fraction": float(fields[4]),
    }


def replay(packet_path: Path, binary: Path) -> dict[str, Any]:
    packet = json.loads(packet_path.read_text())
    verify_packet(packet)
    scalars = packet["scalars"]
    legacy_remax = scalars["remax_pre_surplus_m_s"]
    points = packet["post_surplus_forcing"]
    intervals = list(zip(points, points[1:]))
    harmonized_remax = max(point["rate_m_s"] for point in points)
    harmonized_runoff = sum(
        left["rate_m_s"] * (right["time_s"] - left["time_s"])
        for left, right in intervals
    )
    harmonized_duration = sum(
        right["time_s"] - left["time_s"]
        for left, right in intervals
        if left["rate_m_s"] > 1e-9
    )
    legacy = run_driver(binary, packet, legacy_remax)
    harmonized = run_driver(
        binary, packet, harmonized_remax, harmonized_runoff, harmonized_duration
    )
    selected_key = "appmth_peak_m_s" if packet["production"]["selected_solver"] == "APPMTH" else "hdrive_peak_m_s"
    selected_delta = abs(legacy[selected_key] - packet["production"]["peak_m_s"])
    if selected_delta > 5e-11:
        raise AssertionError(f"selected replay mismatch: {selected_delta} m/s")
    termination = "95_percent_volume"
    if legacy["hdrive_nqt"] >= scalars["ns"] + 201:
        termination = "ns_plus_200_limit"
    report = {
        "schema_version": SCHEMA_VERSION,
        "event_id": packet["event_id"],
        "packet_sha256": packet["payload_sha256"],
        "replay_process": "standalone_peak_replay_executable",
        "selected_method_delta_m_s": selected_delta,
        "legacy_input_replay": {**legacy, "appmth": app_diagnostics(scalars, legacy_remax)},
        "harmonized_forcing_diagnostic": {
            **harmonized,
            "forcing_integral_m": harmonized_runoff,
            "positive_support_duration_s": harmonized_duration,
            "appmth": app_diagnostics(
                scalars, harmonized_remax, harmonized_runoff, harmonized_duration
            ),
        },
        "hdrive_stopping_condition": termination,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("packetize")
    create.add_argument("trace", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--year", type=int, required=True)
    create.add_argument("--day", type=int, required=True)
    create.add_argument("--build-id", required=True)
    create.add_argument("--event-id", required=True)
    run = subparsers.add_parser("replay")
    run.add_argument("packet", type=Path)
    run.add_argument("--binary", type=Path, required=True)
    run.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "packetize":
        result = packetize(args.trace, args.year, args.day, args.build_id, args.event_id)
    else:
        result = replay(args.packet, args.binary)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if getattr(args, "output", None):
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
