#!/usr/bin/env python3
"""Execute the bounded Topanga peak-flow Phase 2A pilot.

The authoritative /wc1 scenario trees are read-only.  All execution products
are content-addressed under an external evidence root; only compact contracts
and summaries are written to the work-package artifact directory.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import pandas as pd

from tools.peakflow_phase1_replay import packetize, replay, verify_packet


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "docs/work-packages/20260808_peakflow_phase2a_pilot"
ARTIFACTS = PACKAGE / "artifacts"
PHASE1_ARTIFACTS = REPO / "docs/work-packages/20260808_peakflow_phase1/artifacts"
RUN_ROOT = Path("/wc1/runs/ha/hand-to-mouth-drought")
SCENARIOS = {
    "burned": RUN_ROOT / "wepp",
    "undisturbed": RUN_ROOT / "_pups/omni/scenarios/undisturbed/wepp",
}
TOPOGRAPHY = RUN_ROOT / "watershed/hillslopes.parquet"
CHANNELS = RUN_ROOT / "watershed/channels.parquet"
SOURCE_COMMIT = "ea25ad79ef7dab20206bca095b2958786f5ae317"
OBSERVER_BUILD_ID = "wepp-ea25ad79-gate21-observer"
SCHEMA_VERSION = "1.0.0"
HILLSLOPE_IDS = tuple(range(1, 141))
CHANNEL_IDS = tuple(range(141, 202))
OUTLET_ID = 201
EVENT_KEY = ["scenario", "hillslope_id", "year", "day", "ofe", "ordinal"]
SURPLUS_FLOOR = 1.0e-10
PEAK_FLOOR = 1.0e-7
RUNOFF_FLOOR = 1.0e-5
SURPLUS_RATE_FLOOR = 1.0e-8


SCHEMAS: dict[str, dict[str, Any]] = {
    "scenario-manifest": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schema_version", "source_commit", "observer_sha256", "scenarios"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "source_commit": {"const": SOURCE_COMMIT},
            "observer_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "scenarios": {
                "type": "object",
                "required": list(SCENARIOS),
                "additionalProperties": {
                    "type": "object",
                    "required": ["authority", "input_tree_sha256", "hillslope_count"],
                },
            },
        },
    },
    "pilot-selection": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schema_version", "selection_frozen_before_mutations", "hillslopes"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "selection_frozen_before_mutations": {"const": True},
            "hillslopes": {
                "type": "array", "minItems": 8, "maxItems": 8,
                "contains": {"type": "object", "properties": {"hillslope_id": {"const": 106}}},
            },
        },
    },
    "terminal-ledger": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schema_version", "requested_trials", "terminal_trials", "statuses"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "requested_trials": {"const": 64},
            "terminal_trials": {"const": 64},
            "statuses": {"type": "object"},
        },
    },
    "exit-report": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["schema_version", "criteria", "full_census_authorized"],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "criteria": {
                "type": "array", "minItems": 10, "maxItems": 10,
                "items": {
                    "type": "object",
                    "required": ["criterion", "status", "evidence"],
                    "properties": {"status": {"enum": ["pass", "fail"]}},
                },
            },
            "full_census_authorized": {"type": "boolean"},
        },
    },
}


@dataclass(frozen=True)
class Trial:
    scenario: str
    hillslope_id: int
    family: str
    direction: str

    @property
    def trial_id(self) -> str:
        return f"{self.scenario}-h{self.hillslope_id:03d}-{self.family}-{self.direction}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def tree_hash(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def storage_artifact(path: Path, external_root: Path) -> dict[str, Any]:
    return {
        "name": path.relative_to(external_root).as_posix(),
        "locator": str(path),
        "format": "parquet" if path.suffix == ".parquet" else "wepp-channel-text",
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "retention": "retain",
    }


def validate_storage_manifest(manifest: dict[str, Any]) -> None:
    for artifact in manifest["artifacts"]:
        path = Path(artifact["locator"])
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != artifact["bytes"]:
            raise ValueError(f"external artifact size mismatch: {path}")
        if sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"external artifact hash mismatch: {path}")


def write_schemas() -> None:
    schema_dir = ARTIFACTS / "schemas"
    for name, schema in SCHEMAS.items():
        write_json(schema_dir / f"{name}.schema.json", schema)


def parse_topology(path: Path) -> tuple[dict[int, dict[str, Any]], dict[int, list[int]]]:
    rows: dict[int, dict[str, Any]] = {}
    for offset, line in enumerate(path.read_text().splitlines()[1:], start=141):
        values = [int(value) for value in line.split()]
        if len(values) != 10 or values[0] != 2:
            raise ValueError(f"unexpected routing row for channel {offset}: {line}")
        rows[offset] = {
            "channel_id": offset,
            "hillslopes": [value for value in values[1:4] if value],
            "upstream_channels": [value for value in values[4:7] if value],
            "impoundments": [value for value in values[7:10] if value],
        }
    if tuple(rows) != CHANNEL_IDS:
        raise ValueError("routing topology does not cover channel elements 141..201")
    downstream: dict[int, int] = {}
    for channel_id, row in rows.items():
        for upstream in row["upstream_channels"]:
            if upstream in downstream:
                raise ValueError(f"channel {upstream} has multiple downstream channels")
            downstream[upstream] = channel_id
    closures: dict[int, list[int]] = {}
    for hillslope_id in HILLSLOPE_IDS:
        direct = [channel for channel, row in rows.items() if hillslope_id in row["hillslopes"]]
        if len(direct) != 1:
            raise ValueError(f"hillslope {hillslope_id} maps to {len(direct)} channels")
        closure = [direct[0]]
        while closure[-1] != OUTLET_ID:
            if closure[-1] not in downstream:
                raise ValueError(f"channel {closure[-1]} does not reach outlet")
            closure.append(downstream[closure[-1]])
        closures[hillslope_id] = closure
    return rows, closures


def soil_fields(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    marker = lines.index("Any comments:")
    horizon_rows: list[tuple[int, list[str]]] = []
    description = ""
    for index, line in enumerate(lines[marker + 1 :], start=marker + 1):
        tokens = line.split()
        if line.lstrip().startswith("'") and len(tokens) >= 8:
            description = line
        if len(tokens) >= 10:
            try:
                [float(value) for value in tokens]
            except ValueError:
                continue
            horizon_rows.append((index, tokens))
    if not horizon_rows:
        raise ValueError(f"no soil horizons in {path}")
    depths = [float(tokens[0]) for _, tokens in horizon_rows]
    ksats = [float(tokens[2]) for _, tokens in horizon_rows]
    thicknesses = [depths[0], *[later - earlier for earlier, later in zip(depths, depths[1:])]]
    harmonic = sum(thicknesses) / sum(thickness / ksat for thickness, ksat in zip(thicknesses, ksats))
    return {
        "description": description.strip(),
        "surface_ksat_mm_h": ksats[0],
        "profile_ksat_harmonic_mm_h": harmonic,
        "first_horizon_line": horizon_rows[0][0],
        "horizon_count": len(horizon_rows),
    }


def cover_fields(path: Path) -> dict[str, float | int]:
    lines = path.read_text().splitlines()
    marker = next(index for index, line in enumerate(lines) if "Initial Condition Section" in line)
    for index, line in enumerate(lines[marker + 1 :], start=marker + 1):
        tokens = line.split()
        if len(tokens) != 6:
            continue
        try:
            values = [float(value) for value in tokens]
        except ValueError:
            continue
        if 0.0 <= values[5] <= 1.0:
            rill_index = index + 3
            rill_values = [float(value) for value in lines[rill_index].split()]
            if len(rill_values) == 5 and 0.0 <= rill_values[2] <= 1.0:
                return {
                    "inrcov": values[5], "rilcov": rill_values[2],
                    "inrcov_line": index, "rilcov_line": rill_index,
                }
    raise ValueError(f"initial cover block not found in {path}")


def adapt_run_deck(text: str) -> str:
    occurrences = text.count(".pass.dat")
    if occurrences != 1:
        raise ValueError(f"expected one legacy pass suffix, found {occurrences}")
    return text.replace(".pass.dat", ".hbp")


def parse_trace(path: Path, scenario: str, hillslope_id: int) -> pd.DataFrame:
    scalars: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    with path.open(newline="") as stream:
        for fields in csv.reader(stream):
            record_type = fields[0]
            if record_type == "SCALAR":
                key = tuple(int(value) for value in fields[1:5])
                numeric = [float(value) for value in fields[5:18]]
                scalars[key] = {
                    "scenario": scenario,
                    "hillslope_id": hillslope_id,
                    "year": key[0], "day": key[1], "ofe": key[2], "ordinal": key[3],
                    **dict(zip(
                        ["runoff_pre_m", "runoff_post_m", "surdra_raw_m", "surdra_realized_m",
                         "positive_excess_duration_s", "assignment_duration_s", "remax_m_s",
                         "postmax_m_s", "added_rate_m_s", "tp2_s", "alpha", "m", "length_m"],
                        numeric,
                    )),
                    "forcing_steps": int(fields[18]),
                    "forcing_mode": int(fields[19]),
                }
            elif record_type == "RESULT":
                key = tuple(int(value) for value in fields[1:5])
                if key not in scalars:
                    raise ValueError(f"result without scalar in {path}: {key}")
                row = scalars.pop(key)
                row["solver"] = fields[5]
                row["peak_m_s"] = float(fields[6])
                rows.append(row)
    if scalars:
        raise ValueError(f"trace has {len(scalars)} unterminated solver calls: {path}")
    if not rows:
        raise ValueError(f"trace contains no solver results: {path}")
    return pd.DataFrame(rows)


def _copy_hillslope_inputs(source: Path, destination: Path, hillslope_id: int) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for suffix in ("cli", "man", "slp", "sol"):
        shutil.copy2(source / f"p{hillslope_id}.{suffix}", destination)
    run_text = (source / f"p{hillslope_id}.run").read_text()
    (destination / f"p{hillslope_id}.run").write_text(adapt_run_deck(run_text))
    for optional in ("gwcoeff.txt", "pmetpara.txt", "snow.txt", "wepp_ui.txt"):
        candidate = source / optional
        if candidate.exists():
            shutil.copy2(candidate, destination / optional)


def _run_observer(job: dict[str, Any]) -> dict[str, Any]:
    scenario = job["scenario"]
    hillslope_id = job["hillslope_id"]
    source = Path(job["source"])
    run_dir = Path(job["run_dir"])
    output_dir = run_dir.parent / "output"
    binary = Path(job["binary"])
    _copy_hillslope_inputs(source, run_dir, hillslope_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "peak_diag.on").touch()
    started = time.perf_counter()
    with (run_dir / f"p{hillslope_id}.run").open("rb") as stdin:
        completed = subprocess.run(binary, cwd=run_dir, stdin=stdin, capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    trace = run_dir / "peak_diag.csv"
    hbp = output_dir / f"H{hillslope_id}.hbp"
    success = (
        completed.returncode == 0
        and b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" in completed.stdout
        and trace.exists() and hbp.exists()
    )
    return {
        "scenario": scenario, "hillslope_id": hillslope_id,
        "status": "complete" if success else "failed", "returncode": completed.returncode,
        "runtime_s": elapsed, "trace": str(trace), "hbp": str(hbp),
        "stdout": str(stdout_path), "stderr": str(stderr_path),
    }


def provenance(observer: Path) -> tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, list[int]]]:
    observer_hash = sha256_file(observer)
    phase1 = json.loads((PHASE1_ARTIFACTS / "observer-build-manifest.json").read_text())
    if observer_hash != phase1["executable_sha256"]:
        raise ValueError("observer binary hash differs from accepted Phase 1 manifest")
    rows, closures = parse_topology(SCENARIOS["burned"] / "runs/pw0.str")
    scenario_records: dict[str, Any] = {}
    for name, wepp in SCENARIOS.items():
        runs = wepp / "runs"
        inputs = [
            path for path in runs.iterdir()
            if path.is_file() and (path.name.startswith("p") or path.name.startswith("pw0"))
        ]
        scenario_records[name] = {
            "authority": str(wepp), "input_tree_sha256": tree_hash(inputs, runs),
            "hillslope_count": sum((runs / f"p{value}.run").exists() for value in HILLSLOPE_IDS),
        }
    manifest = {
        "schema_version": SCHEMA_VERSION, "source_commit": SOURCE_COMMIT,
        "observer_build_id": OBSERVER_BUILD_ID, "observer_sha256": observer_hash,
        "routing_topology_sha256": sha256_file(SCENARIOS["burned"] / "runs/pw0.str"),
        "scenarios": scenario_records,
    }
    jsonschema.validate(manifest, SCHEMAS["scenario-manifest"])
    return manifest, rows, closures


def _baseline_jobs(observer: Path, evidence: Path) -> list[dict[str, Any]]:
    return [
        {
            "scenario": scenario, "hillslope_id": hillslope_id,
            "source": str(root / "runs"), "binary": str(observer),
            "run_dir": str(evidence / "baseline" / scenario / f"h{hillslope_id:03d}" / "runs"),
        }
        for scenario, root in SCENARIOS.items() for hillslope_id in HILLSLOPE_IDS
    ]


def _quantile_label(value: float, low: float, high: float, prefix: str) -> str:
    if value <= low:
        return f"{prefix}_low"
    if value >= high:
        return f"{prefix}_high"
    return f"{prefix}_mid"


def select_hillslopes(inventory: pd.DataFrame) -> dict[str, Any]:
    feasible_by_hill = inventory.assign(
        cover_probe_feasible=(inventory.inrcov.between(0.01, 0.99) & inventory.rilcov.between(0.01, 0.99))
    ).groupby("hillslope_id").cover_probe_feasible.all()
    eligible = {int(hillslope_id) for hillslope_id, feasible in feasible_by_hill.items() if feasible}
    if 106 not in eligible:
        raise ValueError("Hill 106 is not eligible for symmetric cover probes")
    aggregate = inventory.groupby("hillslope_id", as_index=False).agg(
        surface_ksat_mm_h=("surface_ksat_mm_h", "mean"),
        profile_ksat_harmonic_mm_h=("profile_ksat_harmonic_mm_h", "mean"),
        cover=("inrcov", "mean"), elevation=("elevation", "first"),
        slope=("slope_scalar", "first"), path_length_m=("path_length_m", "first"),
        surdra_fraction=("surdra_fraction", "mean"),
        appmth_count=("appmth_count", "sum"), hdrive_count=("hdrive_count", "sum"),
        no_surplus_count=("no_surplus_count", "sum"),
    )
    quantile_fields = ["surface_ksat_mm_h", "cover", "elevation", "slope", "path_length_m", "surdra_fraction"]
    thresholds = {
        field: (float(aggregate[field].quantile(0.25)), float(aggregate[field].quantile(0.75)))
        for field in quantile_fields
    }
    categories: dict[int, set[str]] = {}
    for row in aggregate.itertuples(index=False):
        covered = {
            _quantile_label(float(getattr(row, field)), *thresholds[field], field)
            for field in quantile_fields
        }
        if row.appmth_count:
            covered.add("solver_APPMTH")
        if row.hdrive_count:
            covered.add("solver_HDRIVE")
        if row.no_surplus_count:
            covered.add("observer_no_surplus")
        categories[int(row.hillslope_id)] = covered
    required = {
        f"{field}_{band}" for field in quantile_fields for band in ("low", "high")
    } | {"solver_APPMTH", "solver_HDRIVE", "observer_no_surplus"}
    selected = [106]
    covered = categories[106] & required
    scaled = aggregate.set_index("hillslope_id")[quantile_fields].copy()
    for field in quantile_fields:
        span = float(scaled[field].max() - scaled[field].min())
        scaled[field] = 0.0 if span == 0.0 else (scaled[field] - scaled[field].min()) / span
    while len(selected) < 8:
        candidates = []
        for hillslope_id in sorted(eligible):
            if hillslope_id in selected:
                continue
            gain = len((categories[hillslope_id] & required) - covered)
            distances = [
                math.sqrt(float(((scaled.loc[hillslope_id] - scaled.loc[chosen]) ** 2).sum()))
                for chosen in selected
            ]
            candidates.append((-gain, -min(distances), hillslope_id))
        _, _, choice = min(candidates)
        selected.append(choice)
        covered |= categories[choice] & required
    missing = sorted(required - covered)
    if missing:
        raise ValueError(f"eight-hillslope selection misses required categories: {missing}")
    records = []
    for rank, hillslope_id in enumerate(selected, start=1):
        row = aggregate.loc[aggregate.hillslope_id == hillslope_id].iloc[0]
        records.append({
            "rank": rank, "hillslope_id": hillslope_id,
            "forced_control": hillslope_id == 106,
            "categories": sorted(categories[hillslope_id] & required),
            "baseline_covariates": {
                field: float(row[field]) for field in quantile_fields
            },
        })
    selection = {
        "schema_version": SCHEMA_VERSION,
        "selection_frozen_before_mutations": True,
        "algorithm": "forced_h106_then_greedy_maximum_coverage_with_maximin_numeric_tiebreak",
        "required_categories": sorted(required), "missing_categories": missing,
        "eligibility": {
            "rule": "both_scenarios_allow_unclipped_inrcov_and_rilcov_plus_or_minus_0.01",
            "eligible_count": len(eligible),
            "excluded_hillslopes": sorted(set(HILLSLOPE_IDS) - eligible),
        },
        "thresholds": {field: {"q25": low, "q75": high} for field, (low, high) in thresholds.items()},
        "hillslopes": records,
    }
    selection["selection_id"] = sha256_json(selection)[:16]
    return selection


def inventory_command(args: argparse.Namespace) -> None:
    observer = args.observer.resolve()
    manifest, routing_rows, closures = provenance(observer)
    pilot_id = sha256_json(manifest)[:16]
    evidence = args.evidence_root.resolve() / pilot_id
    evidence.mkdir(parents=True, exist_ok=True)
    write_schemas()
    write_json(ARTIFACTS / "scenario-manifest.json", manifest)
    write_json(ARTIFACTS / "routing-topology.json", {
        "schema_version": SCHEMA_VERSION, "topology_sha256": manifest["routing_topology_sha256"],
        "outlet_id": OUTLET_ID, "channels": list(routing_rows.values()),
        "closures": {str(key): value for key, value in closures.items()},
    })
    jobs = _baseline_jobs(observer, evidence)
    inventory_path = evidence / "baseline-inventory.parquet"
    existing_runtime: dict[tuple[str, int], float] = {}
    if inventory_path.exists():
        existing = pd.read_parquet(inventory_path, columns=["scenario", "hillslope_id", "observer_runtime_s"])
        existing_runtime = {
            (str(row.scenario), int(row.hillslope_id)): float(row.observer_runtime_s)
            for row in existing.itertuples(index=False)
        }
    pending = [job for job in jobs if not Path(job["run_dir"]).joinpath("peak_diag.csv").exists()]
    results: list[dict[str, Any]] = []
    if pending:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for result in pool.map(_run_observer, pending):
                if result["status"] != "complete":
                    raise RuntimeError(f"baseline observer failed: {result}")
                results.append(result)
                print(f"baseline {result['scenario']} H{result['hillslope_id']} {result['runtime_s']:.2f}s", flush=True)
    result_by_key = {(item["scenario"], item["hillslope_id"]): item for item in results}
    topography = pd.read_parquet(TOPOGRAPHY).set_index("wepp_id")
    channel_table = pd.read_parquet(CHANNELS).set_index("wepp_id")
    inventory_rows: list[dict[str, Any]] = []
    event_frames: list[pd.DataFrame] = []
    for job in jobs:
        scenario = job["scenario"]
        hillslope_id = job["hillslope_id"]
        run_dir = Path(job["run_dir"])
        trace = run_dir / "peak_diag.csv"
        frame = parse_trace(trace, scenario, hillslope_id)
        event_frames.append(frame)
        soil = soil_fields(SCENARIOS[scenario] / "runs" / f"p{hillslope_id}.sol")
        cover = cover_fields(SCENARIOS[scenario] / "runs" / f"p{hillslope_id}.man")
        topo = topography.loc[hillslope_id]
        closure = closures[hillslope_id]
        path_length = float(channel_table.loc[closure, "length"].sum())
        inventory_rows.append({
            "scenario": scenario, "hillslope_id": hillslope_id,
            "soil_description": soil["description"],
            "surface_ksat_mm_h": soil["surface_ksat_mm_h"],
            "profile_ksat_harmonic_mm_h": soil["profile_ksat_harmonic_mm_h"],
            "inrcov": cover["inrcov"], "rilcov": cover["rilcov"],
            "slope_scalar": float(topo.slope_scalar), "elevation": float(topo.elevation),
            "hillslope_length_m": float(topo.length), "area_m2": float(topo.area),
            "path_length_m": path_length, "path_channel_count": len(closure),
            "surdra_event_count": int((frame.surdra_raw_m > SURPLUS_FLOOR).sum()),
            "surdra_fraction": float((frame.surdra_raw_m > SURPLUS_FLOOR).mean()),
            "appmth_count": int((frame.solver == "APPMTH").sum()),
            "hdrive_count": int((frame.solver == "HDRIVE").sum()),
            "no_surplus_count": int((frame.surdra_realized_m <= SURPLUS_FLOOR).sum()),
            "event_count": len(frame),
            "observer_runtime_s": float(
                result_by_key.get((scenario, hillslope_id), {}).get(
                    "runtime_s", existing_runtime.get((scenario, hillslope_id), math.nan)
                )
            ),
            "trace_sha256": sha256_file(trace),
            "hbp_sha256": sha256_file(run_dir.parent / "output" / f"H{hillslope_id}.hbp"),
        })
    inventory = pd.DataFrame(inventory_rows).sort_values(["scenario", "hillslope_id"])
    events = pd.concat(event_frames, ignore_index=True).sort_values(EVENT_KEY)
    event_path = evidence / "baseline-events.parquet"
    inventory.to_parquet(inventory_path, index=False)
    events.to_parquet(event_path, index=False, compression="zstd")
    selection = select_hillslopes(inventory)
    selection["pilot_id"] = pilot_id
    selection["inventory_sha256"] = sha256_file(inventory_path)
    selection["baseline_events_sha256"] = sha256_file(event_path)
    jsonschema.validate(selection, SCHEMAS["pilot-selection"])
    write_json(ARTIFACTS / "pilot-selection.json", selection)
    inventory[inventory.hillslope_id.isin([item["hillslope_id"] for item in selection["hillslopes"]])].to_csv(
        ARTIFACTS / "selected-baseline-inventory.csv", index=False
    )
    storage = {
        "schema_version": SCHEMA_VERSION, "pilot_id": pilot_id,
        "external_root": str(evidence),
        "artifacts": [
            {"name": path.name, "locator": str(path), "format": "parquet",
             "bytes": path.stat().st_size, "sha256": sha256_file(path), "retention": "retain"}
            for path in (inventory_path, event_path)
        ],
    }
    write_json(ARTIFACTS / "artifact-storage-baseline.json", storage)
    print(json.dumps({"pilot_id": pilot_id, "selection": [item["hillslope_id"] for item in selection["hillslopes"]]}, indent=2))


def _replace_token(line: str, token_index: int, new_value: float) -> str:
    spans = list(__import__("re").finditer(r"\S+", line))
    if token_index >= len(spans):
        raise ValueError("mutation token index exceeds line token count")
    target = spans[token_index]
    rendered = f"{new_value:.15g}"
    return line[: target.start()] + rendered + line[target.end() :]


def apply_mutation(run_dir: Path, trial: Trial) -> dict[str, Any]:
    if trial.family == "ksat":
        path = run_dir / f"p{trial.hillslope_id}.sol"
        fields = soil_fields(path)
        line_index = int(fields["first_horizon_line"])
        lines = path.read_text().splitlines(keepends=True)
        original = float(lines[line_index].split()[2])
        factor = 0.99 if trial.direction == "minus" else 1.01
        realized = original * factor
        ending = "\n" if lines[line_index].endswith("\n") else ""
        lines[line_index] = _replace_token(lines[line_index].rstrip("\n"), 2, realized) + ending
        path.write_text("".join(lines))
        reread = soil_fields(path)["surface_ksat_mm_h"]
        if reread == original or not math.isclose(float(reread), realized, rel_tol=1e-10):
            raise ValueError(f"Ksat mutation was erased for {trial.trial_id}")
        return {"file": path.name, "parameter": "first_horizon_ksat_mm_h",
                "requested": realized, "before": original, "realized": reread,
                "line": line_index + 1, "token": 3}
    if trial.family == "cover":
        path = run_dir / f"p{trial.hillslope_id}.man"
        fields = cover_fields(path)
        delta = -0.01 if trial.direction == "minus" else 0.01
        lines = path.read_text().splitlines(keepends=True)
        before_inr = float(fields["inrcov"])
        before_rill = float(fields["rilcov"])
        realized_inr = before_inr + delta
        realized_rill = before_rill + delta
        if not (0.0 <= realized_inr <= 1.0 and 0.0 <= realized_rill <= 1.0):
            raise ValueError(f"cover mutation would clip for {trial.trial_id}")
        for line_index, token_index, value in (
            (int(fields["inrcov_line"]), 5, realized_inr),
            (int(fields["rilcov_line"]), 2, realized_rill),
        ):
            ending = "\n" if lines[line_index].endswith("\n") else ""
            lines[line_index] = _replace_token(lines[line_index].rstrip("\n"), token_index, value) + ending
        path.write_text("".join(lines))
        reread = cover_fields(path)
        if reread["inrcov"] == before_inr or reread["rilcov"] == before_rill:
            raise ValueError(f"cover mutation was erased for {trial.trial_id}")
        return {"file": path.name, "parameter": "paired_inrcov_rilcov",
                "requested_delta": delta,
                "before": {"inrcov": before_inr, "rilcov": before_rill},
                "realized": {"inrcov": reread["inrcov"], "rilcov": reread["rilcov"]},
                "lines": [int(fields["inrcov_line"]) + 1, int(fields["rilcov_line"]) + 1],
                "tokens": [6, 3]}
    raise ValueError(f"unsupported mutation family: {trial.family}")


def set_surface_ksat(path: Path, value: float) -> dict[str, Any]:
    fields = soil_fields(path)
    line_index = int(fields["first_horizon_line"])
    lines = path.read_text().splitlines(keepends=True)
    before = float(lines[line_index].split()[2])
    ending = "\n" if lines[line_index].endswith("\n") else ""
    lines[line_index] = _replace_token(lines[line_index].rstrip("\n"), 2, value) + ending
    path.write_text("".join(lines))
    realized = float(soil_fields(path)["surface_ksat_mm_h"])
    if not math.isclose(realized, value, rel_tol=1e-10):
        raise ValueError(f"custom Ksat {value} was not realized in {path}")
    return {"before": before, "requested": value, "realized": realized, "line": line_index + 1, "token": 3}


def _run_mutation(job: dict[str, Any]) -> dict[str, Any]:
    trial = Trial(**job["trial"])
    source = Path(job["source"])
    run_dir = Path(job["run_dir"])
    output_dir = run_dir.parent / "output"
    binary = Path(job["binary"])
    _copy_hillslope_inputs(source, run_dir, trial.hillslope_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    before = {path.name: sha256_file(path) for path in run_dir.iterdir() if path.is_file()}
    mutation = apply_mutation(run_dir, trial)
    after = {path.name: sha256_file(path) for path in run_dir.iterdir() if path.is_file()}
    changed = sorted(name for name in before if before[name] != after[name])
    if changed != [mutation["file"]]:
        raise ValueError(f"mutation isolation failure for {trial.trial_id}: {changed}")
    (run_dir / "peak_diag.on").touch()
    started = time.perf_counter()
    with (run_dir / f"p{trial.hillslope_id}.run").open("rb") as stdin:
        completed = subprocess.run(binary, cwd=run_dir, stdin=stdin, capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    (run_dir / "stdout.log").write_bytes(completed.stdout)
    (run_dir / "stderr.log").write_bytes(completed.stderr)
    trace = run_dir / "peak_diag.csv"
    hbp = output_dir / f"H{trial.hillslope_id}.hbp"
    success = completed.returncode == 0 and b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" in completed.stdout and trace.exists() and hbp.exists()
    return {
        "schema_version": SCHEMA_VERSION, "trial_id": trial.trial_id,
        **job["trial"], "status": "complete" if success else "failed",
        "returncode": completed.returncode, "runtime_s": elapsed,
        "mutation": mutation, "changed_inputs": changed,
        "input_hashes_before": before, "input_hashes_after": after,
        "trace": str(trace), "trace_sha256": sha256_file(trace) if trace.exists() else None,
        "hbp": str(hbp), "hbp_sha256": sha256_file(hbp) if hbp.exists() else None,
    }


def pair_events(baseline: pd.DataFrame, mutant: pd.DataFrame, trial: Trial) -> pd.DataFrame:
    keys = ["year", "day", "ofe", "ordinal"]
    columns = keys + [
        "runoff_post_m", "surdra_raw_m", "surdra_realized_m", "added_rate_m_s",
        "forcing_mode", "solver", "peak_m_s",
    ]
    paired = baseline[columns].merge(mutant[columns], on=keys, how="outer", suffixes=("_baseline", "_mutant"), indicator=True)
    paired.insert(0, "trial_id", trial.trial_id)
    paired.insert(1, "scenario", trial.scenario)
    paired.insert(2, "hillslope_id", trial.hillslope_id)
    paired.insert(3, "family", trial.family)
    paired.insert(4, "direction", trial.direction)
    paired["baseline_event_present"] = paired._merge.isin(["both", "left_only"])
    paired["mutant_event_present"] = paired._merge.isin(["both", "right_only"])
    both = paired._merge == "both"
    peak_abs = (paired.peak_m_s_mutant - paired.peak_m_s_baseline).abs()
    peak_denominator = paired.peak_m_s_baseline.abs().clip(lower=PEAK_FLOOR)
    peak_ratio = paired.peak_m_s_mutant / peak_denominator
    runoff_abs = (paired.runoff_post_m_mutant - paired.runoff_post_m_baseline).abs()
    runoff_denominator = paired.runoff_post_m_baseline.abs().clip(lower=RUNOFF_FLOOR)
    runoff_fraction = runoff_abs / runoff_denominator
    base_rate = paired.added_rate_m_s_baseline.abs()
    mutant_rate = paired.added_rate_m_s_mutant.abs()
    rate_max = pd.concat([base_rate, mutant_rate], axis=1).max(axis=1)
    rate_min = pd.concat([base_rate, mutant_rate], axis=1).min(axis=1)
    paired["event_presence_changed"] = paired._merge != "both"
    paired["solver_changed"] = both & (paired.solver_baseline != paired.solver_mutant)
    paired["forcing_mode_changed"] = both & (paired.forcing_mode_baseline != paired.forcing_mode_mutant)
    paired["surplus_depth_changed"] = both & ((paired.surdra_realized_m_mutant - paired.surdra_realized_m_baseline).abs() > RUNOFF_FLOOR)
    paired["peak_gt25pct_runoff_lt5pct"] = both & (peak_abs > PEAK_FLOOR) & ((peak_abs / peak_denominator) > 0.25) & (runoff_fraction < 0.05)
    paired["peak_twofold"] = both & (peak_abs > PEAK_FLOOR) & ((peak_ratio >= 2.0) | (peak_ratio <= 0.5))
    paired["surplus_rate_twofold"] = both & (rate_max > SURPLUS_RATE_FLOOR) & ((rate_min <= SURPLUS_RATE_FLOOR) | ((rate_max / rate_min.clip(lower=SURPLUS_RATE_FLOOR)) > 2.0))
    signed_peak_change = paired.peak_m_s_mutant - paired.peak_m_s_baseline
    if trial.direction == "plus":
        paired["expected_response_reversal"] = both & (signed_peak_change > PEAK_FLOOR)
    else:
        paired["expected_response_reversal"] = both & (signed_peak_change < -PEAK_FLOOR)
    paired["candidate"] = paired[[
        "event_presence_changed", "solver_changed", "peak_gt25pct_runoff_lt5pct",
        "peak_twofold", "surplus_rate_twofold", "expected_response_reversal",
    ]].any(axis=1)
    return paired.drop(columns="_merge")


def mutations_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    pilot_id = selection["pilot_id"]
    evidence = args.evidence_root.resolve() / pilot_id
    observer = args.observer.resolve()
    provenance(observer)
    hillslopes = [item["hillslope_id"] for item in selection["hillslopes"]]
    trials = [
        Trial(scenario, hillslope, family, direction)
        for scenario in SCENARIOS for hillslope in hillslopes
        for family in ("ksat", "cover") for direction in ("minus", "plus")
    ]
    if len(trials) != 64:
        raise AssertionError("initial mutation matrix must contain 64 trials")
    jobs = [
        {"trial": trial.__dict__, "source": str(SCENARIOS[trial.scenario] / "runs"),
         "binary": str(observer), "run_dir": str(evidence / "mutations" / selection["selection_id"] / trial.trial_id / "runs")}
        for trial in trials
    ]
    pending = [job for job in jobs if not Path(job["run_dir"]).joinpath("terminal.json").exists()]
    fresh_results: dict[str, dict[str, Any]] = {}
    if pending:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for result in pool.map(_run_mutation, pending):
                write_json(Path(next(job["run_dir"] for job in pending if job["trial"]["scenario"] == result["scenario"] and Trial(**job["trial"]).trial_id == result["trial_id"])) / "terminal.json", result)
                fresh_results[result["trial_id"]] = result
                print(f"mutation {result['trial_id']} {result['status']} {result['runtime_s']:.2f}s", flush=True)
    terminals: list[dict[str, Any]] = []
    pairs: list[pd.DataFrame] = []
    baseline_events = pd.read_parquet(evidence / "baseline-events.parquet")
    for job, trial in zip(jobs, trials):
        terminal_path = Path(job["run_dir"]) / "terminal.json"
        terminal = json.loads(terminal_path.read_text()) if terminal_path.exists() else fresh_results[trial.trial_id]
        terminals.append(terminal)
        if terminal["status"] != "complete":
            continue
        mutant = parse_trace(Path(terminal["trace"]), trial.scenario, trial.hillslope_id)
        baseline = baseline_events[(baseline_events.scenario == trial.scenario) & (baseline_events.hillslope_id == trial.hillslope_id)]
        pairs.append(pair_events(baseline, mutant, trial))
    terminal_frame = pd.json_normalize(terminals)
    pair_frame = pd.concat(pairs, ignore_index=True)
    terminal_path = evidence / "terminal-ledger.parquet"
    pair_path = evidence / "event-pairs.parquet"
    terminal_frame.to_parquet(terminal_path, index=False)
    pair_frame.to_parquet(pair_path, index=False, compression="zstd")
    statuses = terminal_frame.status.value_counts().to_dict()
    summary = {
        "schema_version": SCHEMA_VERSION, "pilot_id": pilot_id,
        "requested_trials": 64, "terminal_trials": len(terminals), "statuses": statuses,
        "exact_one_input_diff_trials": int((terminal_frame.changed_inputs.map(len) == 1).sum()),
        "outer_join_rows": len(pair_frame),
        "baseline_only_rows": int((pair_frame.baseline_event_present & ~pair_frame.mutant_event_present).sum()),
        "mutant_only_rows": int((~pair_frame.baseline_event_present & pair_frame.mutant_event_present).sum()),
        "candidate_rows": int(pair_frame.candidate.sum()),
        "candidate_trials": int(pair_frame.loc[pair_frame.candidate, "trial_id"].nunique()),
        "terminal_ledger": {"locator": str(terminal_path), "sha256": sha256_file(terminal_path), "bytes": terminal_path.stat().st_size},
        "event_pairs": {"locator": str(pair_path), "sha256": sha256_file(pair_path), "bytes": pair_path.stat().st_size},
        "runtime_s": {"sum": float(terminal_frame.runtime_s.sum()), "median": float(terminal_frame.runtime_s.median()), "max": float(terminal_frame.runtime_s.max())},
    }
    jsonschema.validate(summary, SCHEMAS["terminal-ledger"])
    write_json(ARTIFACTS / "mutation-terminal-summary.json", summary)
    candidate_summary = pair_frame.loc[pair_frame.candidate].copy()
    candidate_summary.to_csv(ARTIFACTS / "candidate-events.csv", index=False)
    write_json(ARTIFACTS / "artifact-storage-mutations.json", {
        "schema_version": SCHEMA_VERSION, "pilot_id": pilot_id,
        "external_root": str(evidence),
        "artifacts": [
            {"name": path.name, "locator": str(path), "format": "parquet", "bytes": path.stat().st_size,
             "sha256": sha256_file(path), "retention": "retain"} for path in (terminal_path, pair_path)
        ],
    })
    print(json.dumps(summary, indent=2, sort_keys=True))


def _custom_ksat_run(
    observer: Path, evidence: Path, scenario: str, hillslope_id: int, value: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    label = f"ksat-{value:.12f}".rstrip("0").rstrip(".").replace(".", "p")
    run_dir = evidence / "bracket" / label / "runs"
    terminal_path = run_dir / "terminal.json"
    if terminal_path.exists():
        terminal = json.loads(terminal_path.read_text())
        return terminal, parse_trace(Path(terminal["trace"]), scenario, hillslope_id)
    output_dir = run_dir.parent / "output"
    _copy_hillslope_inputs(SCENARIOS[scenario] / "runs", run_dir, hillslope_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    mutation = set_surface_ksat(run_dir / f"p{hillslope_id}.sol", value)
    (run_dir / "peak_diag.on").touch()
    started = time.perf_counter()
    with (run_dir / f"p{hillslope_id}.run").open("rb") as stdin:
        completed = subprocess.run(observer, cwd=run_dir, stdin=stdin, capture_output=True, check=False)
    runtime = time.perf_counter() - started
    (run_dir / "stdout.log").write_bytes(completed.stdout)
    (run_dir / "stderr.log").write_bytes(completed.stderr)
    trace = run_dir / "peak_diag.csv"
    hbp = output_dir / f"H{hillslope_id}.hbp"
    if completed.returncode or b"WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in completed.stdout or not trace.exists() or not hbp.exists():
        raise RuntimeError(f"adaptive bracket run failed at Ksat={value}")
    terminal = {
        "schema_version": SCHEMA_VERSION, "scenario": scenario, "hillslope_id": hillslope_id,
        "surface_ksat_mm_h": value, "mutation": mutation, "status": "complete",
        "runtime_s": runtime, "trace": str(trace), "trace_sha256": sha256_file(trace),
        "hbp": str(hbp), "hbp_sha256": sha256_file(hbp),
    }
    write_json(terminal_path, terminal)
    return terminal, parse_trace(trace, scenario, hillslope_id)


def _event_row(frame: pd.DataFrame, year: int, day: int) -> pd.Series:
    rows = frame[(frame.year == year) & (frame.day == day) & (frame.ofe == 1) & (frame.ordinal == 1)]
    if len(rows) != 1:
        raise ValueError(f"expected one event for {year}/{day}, found {len(rows)}")
    return rows.iloc[0]


def _packet_and_replay(
    trace: Path, packet_path: Path, report_path: Path, replay_binary: Path,
    *, year: int, day: int, event_id: str, run_id: str, hillslope_id: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = packetize(trace, year, day, OBSERVER_BUILD_ID, event_id, run_id, str(hillslope_id), 1, 1)
    verify_packet(packet)
    packet_schema = json.loads((PHASE1_ARTIFACTS / "schemas/event-packet.schema.json").read_text())
    jsonschema.validate(packet, packet_schema)
    write_json(packet_path, packet)
    report = replay(packet_path, replay_binary)
    replay_schema = json.loads((PHASE1_ARTIFACTS / "schemas/replay-report.schema.json").read_text())
    jsonschema.validate(report, replay_schema)
    write_json(report_path, report)
    return packet, report


def adjudicate_command(args: argparse.Namespace) -> None:
    observer = args.observer.resolve()
    manifest, _, _ = provenance(observer)
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    pilot_id = selection["pilot_id"]
    selection_id = selection["selection_id"]
    evidence = args.evidence_root.resolve() / pilot_id
    adjudication_root = evidence / "adjudication" / selection_id
    adjudication_root.mkdir(parents=True, exist_ok=True)
    if args.replay_binary is None:
        raise ValueError("adjudicate requires --replay-binary from the accepted Phase 1 build")
    replay_binary = args.replay_binary.resolve()
    expected_replay_hash = json.loads((PHASE1_ARTIFACTS / "replay-build-manifest.json").read_text())["executable_sha256"]
    if sha256_file(replay_binary) != expected_replay_hash:
        raise ValueError("replay binary hash differs from accepted Phase 1 manifest")
    retained_replay = adjudication_root / "peak_replay"
    shutil.copy2(replay_binary, retained_replay)

    no_surplus_trace = evidence / "baseline/burned/h031/runs/peak_diag.csv"
    no_surplus_packet_path = ARTIFACTS / "event-packets/topanga-h031-1980-day045-no-surplus.json"
    no_surplus_report_path = ARTIFACTS / "replay-reports/topanga-h031-1980-day045-no-surplus.json"
    no_surplus_packet, no_surplus_report = _packet_and_replay(
        no_surplus_trace, no_surplus_packet_path, no_surplus_report_path, retained_replay,
        year=1980, day=45, event_id="topanga-burned-h031-1980-day045-no-surplus",
        run_id="phase2a-burned-h031-baseline", hillslope_id=31,
    )
    if no_surplus_packet["scalars"]["surplus_depth_m"] != 0.0:
        raise ValueError("selected no-surplus packet has nonzero surplus")

    scenario = "undisturbed"
    hillslope_id = 106
    year = 1986
    day = 46
    low_value = 34.65
    high_value = 35.0
    bracket_root = adjudication_root / "h106-1986-day046"
    low_terminal, low_frame = _custom_ksat_run(observer, bracket_root, scenario, hillslope_id, low_value)
    high_terminal, high_frame = _custom_ksat_run(observer, bracket_root, scenario, hillslope_id, high_value)
    low_peak = float(_event_row(low_frame, year, day).peak_m_s)
    high_peak = float(_event_row(high_frame, year, day).peak_m_s)
    if max(low_peak, high_peak) / max(min(low_peak, high_peak), PEAK_FLOOR) < 2.0:
        raise ValueError("known-positive endpoints do not reproduce a twofold response")
    bracket_rows = [
        {"iteration": 0, "surface_ksat_mm_h": low_value, "peak_m_s": low_peak,
         "regime": "low_ksat_response", "solver": str(_event_row(low_frame, year, day).solver),
         "trace": low_terminal["trace"]},
        {"iteration": 0, "surface_ksat_mm_h": high_value, "peak_m_s": high_peak,
         "regime": "high_ksat_response", "solver": str(_event_row(high_frame, year, day).solver),
         "trace": high_terminal["trace"]},
    ]
    low_log = math.log(max(low_peak, PEAK_FLOOR))
    high_log = math.log(max(high_peak, PEAK_FLOOR))
    endpoint_records = {low_value: (low_terminal, low_frame), high_value: (high_terminal, high_frame)}
    for iteration in range(1, 13):
        midpoint = (low_value + high_value) / 2.0
        terminal, frame = _custom_ksat_run(observer, bracket_root, scenario, hillslope_id, midpoint)
        row = _event_row(frame, year, day)
        peak = float(row.peak_m_s)
        log_peak = math.log(max(peak, PEAK_FLOOR))
        if abs(log_peak - low_log) <= abs(log_peak - high_log):
            regime = "low_ksat_response"
            low_value, low_peak, low_log = midpoint, peak, log_peak
        else:
            regime = "high_ksat_response"
            high_value, high_peak, high_log = midpoint, peak, log_peak
        endpoint_records[midpoint] = (terminal, frame)
        bracket_rows.append({
            "iteration": iteration, "surface_ksat_mm_h": midpoint, "peak_m_s": peak,
            "regime": regime, "solver": str(row.solver), "trace": terminal["trace"],
        })
    bracket_frame = pd.DataFrame(bracket_rows).sort_values("surface_ksat_mm_h")
    bracket_frame.to_csv(ARTIFACTS / "h106-1986-day046-adaptive-bracket.csv", index=False)
    packet_dir = ARTIFACTS / "event-packets"
    replay_dir = ARTIFACTS / "replay-reports"
    endpoint_reports: dict[str, Any] = {}
    for label, value in (("low", low_value), ("high", high_value)):
        terminal, _ = endpoint_records[value]
        packet, report = _packet_and_replay(
            Path(terminal["trace"]), packet_dir / f"h106-1986-day046-bracket-{label}.json",
            replay_dir / f"h106-1986-day046-bracket-{label}.json", retained_replay,
            year=year, day=day, event_id=f"topanga-{scenario}-h106-1986-day046-bracket-{label}",
            run_id=f"phase2a-{selection_id}-bracket-{label}", hillslope_id=hillslope_id,
        )
        endpoint_reports[label] = {
            "surface_ksat_mm_h": value, "packet_sha256": packet["payload_sha256"],
            "selected_solver": packet["production"]["selected_solver"],
            "surplus_assignment_mode": packet["scalars"]["surplus_assignment_mode"],
            "surplus_added_rate_m_s": packet["scalars"]["surplus_added_rate_m_s"],
            "selected_method_delta_m_s": report["selected_method_delta_m_s"],
            "hdrive_fraction_legacy": report["legacy_input_replay"]["hdrive_final_routed_volume_fraction"],
            "hdrive_fraction_harmonized": report["harmonized_forcing_diagnostic"]["hdrive_final_routed_volume_fraction"],
        }
    all_fractions = [
        report[family]["hdrive_final_routed_volume_fraction"]
        for report in [no_surplus_report] + [json.loads((replay_dir / f"h106-1986-day046-bracket-{label}.json").read_text()) for label in ("low", "high")]
        for family in ("legacy_input_replay", "harmonized_forcing_diagnostic")
    ]
    stopped = [fraction for fraction in all_fractions if fraction < 0.95]
    result = {
        "schema_version": SCHEMA_VERSION, "pilot_id": pilot_id, "selection_id": selection_id,
        "observer_sha256": manifest["observer_sha256"], "replay_sha256": sha256_file(retained_replay),
        "no_surplus_packet": {
            "event_id": no_surplus_packet["event_id"], "surplus_depth_m": no_surplus_packet["scalars"]["surplus_depth_m"],
            "selected_solver": no_surplus_packet["production"]["selected_solver"],
            "packet_sha256": no_surplus_packet["payload_sha256"],
        },
        "known_positive": {
            "event": {"scenario": scenario, "hillslope_id": hillslope_id, "year": year, "day": day},
            "initial_bracket_mm_h": [34.65, 35.0], "final_bracket_mm_h": [low_value, high_value],
            "final_width_mm_h": high_value - low_value, "iterations": 12,
            "endpoint_peak_ratio": max(low_peak, high_peak) / max(min(low_peak, high_peak), PEAK_FLOOR),
            "evidence_state": "mechanism_traced",
            "mechanism": "surplus_assignment_mode_changes from positive_excess to storm while APPMTH remains selected",
            "endpoint_replays": endpoint_reports,
        },
        "hdrive_replays": {
            "total": len(all_fractions), "below_0_95": len(stopped),
            "disposition": "stopped_excluded_from_candidate_statistics" if stopped else "all_complete",
            "fractions": all_fractions,
        },
    }
    write_json(ARTIFACTS / "candidate-adjudication.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


def _prepare_watershed_lane(
    evidence: Path, selection_id: str, scenario: str, lane_id: str,
    target_hillslope: int | None = None, mutant_hbp: Path | None = None,
    channel_mode: int = 1, channel_ids: tuple[int, ...] = CHANNEL_IDS,
) -> tuple[Path, dict[int, str]]:
    lane = evidence / "routing" / selection_id / scenario / lane_id
    runs = lane / "runs"
    output = lane / "output"
    runs.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    source = SCENARIOS[scenario] / "runs"
    for path in source.glob("pw0.*"):
        shutil.copy2(path, runs / path.name)
    for name in ("chntyp.txt", "gwcoeff.txt", "pmetpara.txt", "snow.txt", "tc.txt", "wepp_ui.txt"):
        candidate = source / name
        if candidate.exists():
            shutil.copy2(candidate, runs / name)
    run_deck = runs / "pw0.run"
    text = run_deck.read_text()
    if text.count(".pass.dat") != 140:
        raise ValueError("watershed run deck does not name exactly 140 legacy pass files")
    adapted_lines = text.replace(".pass.dat", ".hbp").splitlines()
    final_hbp_index = adapted_lines.index("../output/H140.hbp")
    minimal_watershed_tail = [
        "No",  # impoundments
        "No",  # initial-condition scenario output
        "0", "../output/loss_pw0.txt",
        "No",  # water balance
        "No",  # crop
        "No",  # soil
        "No",  # channel erosion plotting
        "No",  # watershed large graphics
        "No",  # event-by-event
        "No",  # final summary
        "No",  # daily winter
        "No",  # plant yield
        "pw0.str", "pw0.chn", "pw0.man", "pw0.slp", "pw0.cli", "pw0.sol",
        "0", "45",
    ]
    run_deck.write_text("\n".join(adapted_lines[: final_hbp_index + 1] + minimal_watershed_tail) + "\n")
    (runs / "chan.inp").write_text(
        f"{channel_mode} 600\n0\n{len(channel_ids)}\n"
        + " ".join(str(value) for value in channel_ids) + "\n"
    )
    hbp_hashes: dict[int, str] = {}
    for hillslope_id in HILLSLOPE_IDS:
        source_hbp = evidence / "baseline" / scenario / f"h{hillslope_id:03d}" / "output" / f"H{hillslope_id}.hbp"
        if hillslope_id == target_hillslope:
            if mutant_hbp is None:
                raise ValueError("target hillslope requires a mutant HBP")
            source_hbp = mutant_hbp
        destination = output / f"H{hillslope_id}.hbp"
        if destination.exists():
            destination.unlink()
        os.link(source_hbp, destination)
        hbp_hashes[hillslope_id] = sha256_file(source_hbp)
    return lane, hbp_hashes


def _run_watershed(binary: Path, lane: Path) -> dict[str, Any]:
    runs = lane / "runs"
    terminal_path = runs / "routing-terminal.json"
    if terminal_path.exists():
        prior = json.loads(terminal_path.read_text())
        if prior["status"] == "complete":
            return prior
        terminal_path.unlink()
    started = time.perf_counter()
    with (runs / "pw0.run").open("rb") as stdin:
        completed = subprocess.run(binary, cwd=runs, stdin=stdin, capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    (runs / "stdout.log").write_bytes(completed.stdout)
    (runs / "stderr.log").write_bytes(completed.stderr)
    terminal = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete" if completed.returncode == 0 and b"WEPP COMPLETED WATERSHED SIMULATION" in completed.stdout else "failed",
        "returncode": completed.returncode, "runtime_s": elapsed,
        "chan_out": str(runs / "chan.out"), "chanwb_out": str(runs / "chanwb.out"),
        "stdout": str(runs / "stdout.log"), "stderr": str(runs / "stderr.log"),
    }
    write_json(terminal_path, terminal)
    return terminal


def _route_trial(job: dict[str, Any]) -> dict[str, Any]:
    trial = Trial(**job["trial"])
    evidence = Path(job["evidence"])
    mutant_hbp = Path(job["mutant_hbp"])
    lane, hashes = _prepare_watershed_lane(
        evidence, job["selection_id"], trial.scenario, trial.trial_id,
        trial.hillslope_id, mutant_hbp,
    )
    baseline_hashes = {
        hillslope_id: sha256_file(
            evidence / "baseline" / trial.scenario / f"h{hillslope_id:03d}" / "output" / f"H{hillslope_id}.hbp"
        )
        for hillslope_id in HILLSLOPE_IDS
    }
    changed = [hillslope_id for hillslope_id in HILLSLOPE_IDS if hashes[hillslope_id] != baseline_hashes[hillslope_id]]
    if any(hillslope_id != trial.hillslope_id for hillslope_id in changed):
        raise ValueError(f"routing lane changes an unmutated HBP: {trial.trial_id} {changed}")
    terminal = _run_watershed(Path(job["binary"]), lane)
    manifest = {
        "schema_version": SCHEMA_VERSION, "trial_id": trial.trial_id,
        "scenario": trial.scenario, "hillslope_id": trial.hillslope_id,
        "status": terminal["status"], "runtime_s": terminal["runtime_s"],
        "changed_hillslope_passes": changed, "unchanged_hillslope_passes": 140 - len(changed),
        "hbp_tree_sha256": sha256_json(hashes),
        "chan_out": terminal["chan_out"], "chanwb_out": terminal["chanwb_out"],
    }
    write_json(lane / "runs/route-manifest.json", manifest)
    return manifest


def _data_records(path: Path, field_count: int) -> Iterable[list[str]]:
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if len(fields) == field_count and fields[0].isdigit():
                yield fields


def compare_channel_outputs(
    baseline_chan: Path, mutant_chan: Path, baseline_wb: Path, mutant_wb: Path,
    closure: set[int], trial_id: str,
) -> dict[str, Any]:
    peak_changes = 0
    wb_changes = 0
    offpath_changes = 0
    invalid_timestamps = 0
    negative_flows = 0
    max_peak_delta = 0.0
    max_outflow_delta = 0.0
    peak_base = _data_records(baseline_chan, 6)
    peak_mutant = _data_records(mutant_chan, 6)
    for baseline, mutant in zip(peak_base, peak_mutant, strict=True):
        if baseline[:4] != mutant[:4]:
            raise ValueError(f"channel peak key drift for {trial_id}: {baseline[:4]} != {mutant[:4]}")
        year, day, element = int(mutant[0]), int(mutant[1]), int(mutant[2])
        time_s, peak = float(mutant[4]), float(mutant[5])
        if not (1980 <= year <= 2024 and 1 <= day <= 366 and 0.0 <= time_s <= 86400.0):
            invalid_timestamps += 1
        if peak < 0.0:
            negative_flows += 1
        if [float(value) for value in baseline[4:]] != [float(value) for value in mutant[4:]]:
            peak_changes += 1
            max_peak_delta = max(max_peak_delta, abs(float(mutant[5]) - float(baseline[5])))
            if element not in closure:
                offpath_changes += 1
    wb_base = _data_records(baseline_wb, 10)
    wb_mutant = _data_records(mutant_wb, 10)
    max_balance_error = 0.0
    for baseline, mutant in zip(wb_base, wb_mutant, strict=True):
        if baseline[:4] != mutant[:4]:
            raise ValueError(f"channel water-balance key drift for {trial_id}: {baseline[:4]} != {mutant[:4]}")
        element = int(mutant[2])
        values = [float(value) for value in mutant[4:]]
        if values[0] < 0.0 or values[1] < 0.0 or values[3] < 0.0:
            negative_flows += 1
        max_balance_error = max(max_balance_error, abs(values[5]))
        if [float(value) for value in baseline[4:]] != [float(value) for value in mutant[4:]]:
            wb_changes += 1
            max_outflow_delta = max(max_outflow_delta, abs(float(mutant[5]) - float(baseline[5])))
            if element not in closure:
                offpath_changes += 1
    return {
        "trial_id": trial_id, "peak_changed_records": peak_changes,
        "water_balance_changed_records": wb_changes, "offpath_changed_records": offpath_changes,
        "invalid_timestamp_records": invalid_timestamps, "negative_flow_records": negative_flows,
        "max_peak_delta_m3_s": max_peak_delta, "max_outflow_delta_m3": max_outflow_delta,
        "max_reported_balance_error_m3": max_balance_error,
    }


def route_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    evidence = args.evidence_root.resolve() / selection["pilot_id"]
    watershed_binary = args.watershed.resolve()
    if not watershed_binary.exists():
        raise FileNotFoundError(watershed_binary)
    baseline_terminals: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS:
        lane, hashes = _prepare_watershed_lane(evidence, selection["selection_id"], scenario, "baseline")
        terminal = _run_watershed(watershed_binary, lane)
        baseline_terminals[scenario] = terminal
        terminal["hbp_count"] = len(hashes)
        terminal["hbp_tree_sha256"] = sha256_json(hashes)
        print(json.dumps({"scenario": scenario, **terminal}, indent=2, sort_keys=True), flush=True)
        if terminal["status"] != "complete":
            raise RuntimeError(f"baseline watershed routing failed for {scenario}")
    hillslopes = [item["hillslope_id"] for item in selection["hillslopes"]]
    trials = [
        Trial(scenario, hillslope, family, direction)
        for scenario in SCENARIOS for hillslope in hillslopes
        for family in ("ksat", "cover") for direction in ("minus", "plus")
    ]
    jobs: list[dict[str, Any]] = []
    for trial in trials:
        mutation_terminal = evidence / "mutations" / selection["selection_id"] / trial.trial_id / "runs/terminal.json"
        mutation = json.loads(mutation_terminal.read_text())
        jobs.append({
            "trial": trial.__dict__, "evidence": str(evidence), "selection_id": selection["selection_id"],
            "mutant_hbp": mutation["hbp"], "binary": str(watershed_binary),
        })
    route_manifests: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.routing_workers) as pool:
        for result in pool.map(_route_trial, jobs):
            if result["status"] != "complete":
                raise RuntimeError(f"watershed routing failed: {result['trial_id']}")
            route_manifests.append(result)
            print(f"routing {result['trial_id']} complete {result['runtime_s']:.1f}s", flush=True)
    topology = json.loads((ARTIFACTS / "routing-topology.json").read_text())
    validations: list[dict[str, Any]] = []
    for trial in trials:
        baseline_runs = evidence / "routing" / selection["selection_id"] / trial.scenario / "baseline/runs"
        mutant_runs = evidence / "routing" / selection["selection_id"] / trial.scenario / trial.trial_id / "runs"
        validations.append(compare_channel_outputs(
            baseline_runs / "chan.out", mutant_runs / "chan.out",
            baseline_runs / "chanwb.out", mutant_runs / "chanwb.out",
            set(topology["closures"][str(trial.hillslope_id)]), trial.trial_id,
        ))
        print(f"validated routing {trial.trial_id}", flush=True)
    validation_frame = pd.DataFrame(validations)
    validation_frame.to_csv(ARTIFACTS / "routing-trial-validation.csv", index=False)
    raw_paths = [
        Path(manifest[key]) for manifest in route_manifests
        for key in ("chan_out", "chanwb_out")
    ] + [
        Path(baseline_terminals[scenario][key]) for scenario in SCENARIOS
        for key in ("chan_out", "chanwb_out")
    ]
    summary = {
        "schema_version": SCHEMA_VERSION, "pilot_id": selection["pilot_id"],
        "selection_id": selection["selection_id"], "routing_trials": len(route_manifests),
        "complete_trials": sum(item["status"] == "complete" for item in route_manifests),
        "trials_with_exactly_139_unchanged_hillslopes": sum(item["unchanged_hillslope_passes"] == 139 for item in route_manifests),
        "trials_with_140_unchanged_hillslopes": sum(item["unchanged_hillslope_passes"] == 140 for item in route_manifests),
        "offpath_changed_records": int(validation_frame.offpath_changed_records.sum()),
        "invalid_timestamp_records": int(validation_frame.invalid_timestamp_records.sum()),
        "negative_flow_records": int(validation_frame.negative_flow_records.sum()),
        "closure_peak_changed_records": int(validation_frame.peak_changed_records.sum()),
        "closure_water_balance_changed_records": int(validation_frame.water_balance_changed_records.sum()),
        "runtime_s": {
            "baseline_sum": sum(float(item["runtime_s"]) for item in baseline_terminals.values()),
            "trial_sum": sum(float(item["runtime_s"]) for item in route_manifests),
            "trial_median": float(pd.Series([item["runtime_s"] for item in route_manifests]).median()),
        },
        "raw_routing_bytes": sum(path.stat().st_size for path in raw_paths),
        "raw_artifact_count": len(raw_paths),
        "retention": "external_retain",
    }
    write_json(ARTIFACTS / "routing-validation-summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


def _interval_route_job(job: dict[str, Any]) -> dict[str, Any]:
    evidence = Path(job["evidence"])
    lane, hashes = _prepare_watershed_lane(
        evidence, job["selection_id"], "undisturbed", job["lane_id"],
        106, Path(job["hbp"]), channel_mode=3,
        channel_ids=tuple(job["closure"]),
    )
    terminal = _run_watershed(Path(job["binary"]), lane)
    return {"lane_id": job["lane_id"], "hbp_tree_sha256": sha256_json(hashes), **terminal}


def hydrographs_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    adjudication = json.loads((ARTIFACTS / "candidate-adjudication.json").read_text())
    topology = json.loads((ARTIFACTS / "routing-topology.json").read_text())
    evidence = args.evidence_root.resolve() / selection["pilot_id"]
    bracket_root = evidence / "adjudication" / selection["selection_id"] / "h106-1986-day046/bracket"
    jobs: list[dict[str, Any]] = []
    for label in ("low", "high"):
        value = adjudication["known_positive"]["endpoint_replays"][label]["surface_ksat_mm_h"]
        run_label = f"ksat-{value:.12f}".rstrip("0").rstrip(".").replace(".", "p")
        terminal = json.loads((bracket_root / run_label / "runs/terminal.json").read_text())
        jobs.append({
            "evidence": str(evidence), "selection_id": selection["selection_id"],
            "lane_id": f"candidate-h106-{label}-interval", "hbp": terminal["hbp"],
            "closure": topology["closures"]["106"], "binary": str(args.watershed.resolve()),
        })
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_interval_route_job, jobs))
    for result in results:
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        if result["status"] != "complete":
            raise RuntimeError(f"interval route failed: {result['lane_id']}")
    write_json(ARTIFACTS / "interval-routing-terminals.json", {
        "schema_version": SCHEMA_VERSION, "pilot_id": selection["pilot_id"],
        "selection_id": selection["selection_id"], "lanes": results,
    })
    event_rows: list[dict[str, Any]] = []
    volume_rows: list[dict[str, Any]] = []
    invalid_timestamps = 0
    negative_flows = 0
    expected_channels = set(topology["closures"]["106"])
    for result in results:
        lane_id = result["lane_id"]
        previous_time: dict[int, float] = {}
        integrals: dict[int, float] = {}
        observed_channels: set[int] = set()
        for fields in _data_records(Path(result["chan_out"]), 6):
            year, day, element, channel = (int(value) for value in fields[:4])
            if year != 1986 or day != 46:
                continue
            time_s, discharge = float(fields[4]), float(fields[5])
            observed_channels.add(element)
            prior = previous_time.get(element, 0.0)
            if time_s <= prior or time_s > 86400.0 or not math.isclose((time_s - prior) % 600.0, 0.0, abs_tol=1e-6):
                invalid_timestamps += 1
            if discharge < 0.0:
                negative_flows += 1
            integrals[element] = integrals.get(element, 0.0) + discharge * (time_s - prior)
            previous_time[element] = time_s
            event_rows.append({
                "lane_id": lane_id, "year": year, "day": day, "element_id": element,
                "channel_id": channel, "time_s": time_s, "discharge_m3_s": discharge,
            })
        if observed_channels != expected_channels:
            raise ValueError(f"interval route closure mismatch for {lane_id}: {sorted(observed_channels)}")
        if any(not math.isclose(value, 86400.0) for value in previous_time.values()):
            raise ValueError(f"interval route does not end at 86400 seconds: {lane_id}")
        water_balance: dict[int, float] = {}
        for fields in _data_records(Path(result["chanwb_out"]), 10):
            if int(fields[0]) == 1986 and int(fields[1]) == 46:
                water_balance[int(fields[2])] = float(fields[5])
        if set(water_balance) != expected_channels:
            raise ValueError(f"water-balance closure mismatch for {lane_id}")
        for element in sorted(expected_channels):
            integrated = integrals[element]
            reported = water_balance[element]
            difference = integrated - reported
            relative = abs(difference) / max(abs(reported), 1.0)
            volume_rows.append({
                "lane_id": lane_id, "element_id": element,
                "integrated_interval_volume_m3": integrated,
                "reported_outflow_volume_m3": reported,
                "difference_m3": difference, "relative_error": relative,
                "within_5pct_or_0_1m3": abs(difference) <= max(0.1, 0.05 * abs(reported)),
            })
    event_frame = pd.DataFrame(event_rows)
    volume_frame = pd.DataFrame(volume_rows)
    external_series = evidence / "hydrograph-h106-1986-day046.parquet"
    event_frame.to_parquet(external_series, index=False, compression="zstd")
    event_frame.to_csv(ARTIFACTS / "h106-1986-day046-hydrograph.csv", index=False)
    volume_frame.to_csv(ARTIFACTS / "h106-1986-day046-volume-check.csv", index=False)
    low_times = event_frame[event_frame.lane_id.str.contains("low")][["element_id", "time_s"]].reset_index(drop=True)
    high_times = event_frame[event_frame.lane_id.str.contains("high")][["element_id", "time_s"]].reset_index(drop=True)
    summary = {
        "schema_version": SCHEMA_VERSION, "pilot_id": selection["pilot_id"],
        "event": {"scenario": "undisturbed", "hillslope_id": 106, "year": 1986, "day": 46},
        "closure": sorted(expected_channels), "lanes": [item["lane_id"] for item in results],
        "interval_rows": len(event_frame), "invalid_timestamp_records": invalid_timestamps,
        "negative_flow_records": negative_flows, "lane_timestamps_compatible": low_times.equals(high_times),
        "volume_checks": len(volume_frame),
        "volume_mismatches": int((~volume_frame.within_5pct_or_0_1m3).sum()),
        "max_relative_volume_error": float(volume_frame.relative_error.max()),
        "series": {"locator": str(external_series), "bytes": external_series.stat().st_size,
                   "sha256": sha256_file(external_series), "format": "parquet", "retention": "retain"},
    }
    write_json(ARTIFACTS / "hydrograph-validation-summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


def _count_negative_route_flow(job: dict[str, str]) -> tuple[str, int]:
    count = 0
    for fields in _data_records(Path(job["chan_out"]), 6):
        if float(fields[5]) < 0.0:
            count += 1
    for fields in _data_records(Path(job["chanwb_out"]), 10):
        values = [float(value) for value in fields[4:8]]
        if values[0] < 0.0 or values[1] < 0.0 or values[3] < 0.0:
            count += 1
    return job["trial_id"], count


def routing_flow_recheck_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    evidence = args.evidence_root.resolve() / selection["pilot_id"]
    frame = pd.read_csv(ARTIFACTS / "routing-trial-validation.csv")
    jobs = []
    for trial_id in frame.trial_id:
        scenario = str(trial_id).split("-", 1)[0]
        runs = evidence / "routing" / selection["selection_id"] / scenario / str(trial_id) / "runs"
        jobs.append({"trial_id": str(trial_id), "chan_out": str(runs / "chan.out"), "chanwb_out": str(runs / "chanwb.out")})
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.routing_workers) as pool:
        counts = dict(pool.map(_count_negative_route_flow, jobs))
    frame["negative_flow_records"] = frame.trial_id.map(counts)
    frame.to_csv(ARTIFACTS / "routing-trial-validation.csv", index=False)
    summary_path = ARTIFACTS / "routing-validation-summary.json"
    summary = json.loads(summary_path.read_text())
    summary["negative_flow_records"] = int(frame.negative_flow_records.sum())
    write_json(summary_path, summary)
    print(json.dumps({"trials": len(frame), "negative_flow_records": summary["negative_flow_records"]}, indent=2))


def report_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    mutation = json.loads((ARTIFACTS / "mutation-terminal-summary.json").read_text())
    routing = json.loads((ARTIFACTS / "routing-validation-summary.json").read_text())
    hydrograph = json.loads((ARTIFACTS / "hydrograph-validation-summary.json").read_text())
    adjudication = json.loads((ARTIFACTS / "candidate-adjudication.json").read_text())
    evidence = args.evidence_root.resolve() / selection["pilot_id"]
    full_trials = 140 * 2 * 4
    scale = full_trials / 64.0
    hillslope_runtime = mutation["runtime_s"]["sum"] * scale
    routing_runtime = routing["runtime_s"]["trial_sum"] * scale
    routing_bytes = routing["raw_routing_bytes"] * scale
    projection = {
        "schema_version": SCHEMA_VERSION, "pilot_id": selection["pilot_id"],
        "pilot_trials": 64, "full_census_trials": full_trials, "scale_factor": scale,
        "projected_hillslope_runtime_s_sequential": hillslope_runtime,
        "projected_routing_runtime_s_sequential": routing_runtime,
        "projected_routing_wall_s_at_8_workers": routing_runtime / 8.0,
        "projected_raw_routing_bytes": routing_bytes,
        "partitioning": "scenario/selection_id/trial_id with immutable terminal manifests",
        "retention": "raw external retain; compact schemas, ledgers, hashes, and summaries committed",
        "acceptable": routing_bytes <= 300_000_000_000 and routing_runtime / 8.0 <= 8 * 3600,
        "acceptance_bounds": {"raw_routing_bytes_max": 300_000_000_000, "wall_s_at_8_workers_max": 28800},
    }
    write_json(ARTIFACTS / "storage-runtime-projection.json", projection)
    criteria = [
        {
            "criterion": "mutation_manifest_realization_terminal_and_input_diff",
            "status": "pass" if mutation["terminal_trials"] == 64 and mutation["exact_one_input_diff_trials"] == 64 and mutation["statuses"] == {"complete": 64} else "fail",
            "evidence": "mutation-terminal-summary.json",
        },
        {
            "criterion": "outer_join_preserves_absence_distinct_from_zero",
            "status": "pass" if mutation["outer_join_rows"] and mutation["baseline_only_rows"] and mutation["mutant_only_rows"] else "fail",
            "evidence": "mutation-terminal-summary.json and event-pairs.parquet",
        },
        {
            "criterion": "real_observer_no_surplus_packet_validates",
            "status": "pass" if adjudication["no_surplus_packet"]["surplus_depth_m"] == 0.0 else "fail",
            "evidence": "event-packets/topanga-h031-1980-day045-no-surplus.json",
        },
        {
            "criterion": "unmutated_hillslopes_unchanged",
            "status": "pass" if routing["trials_with_exactly_139_unchanged_hillslopes"] + routing["trials_with_140_unchanged_hillslopes"] == 64 else "fail",
            "evidence": "routing-validation-summary.json and external route manifests",
        },
        {
            "criterion": "offpath_channels_unchanged",
            "status": "pass" if routing["offpath_changed_records"] == 0 else "fail",
            "evidence": "routing-trial-validation.csv",
        },
        {
            "criterion": "every_changed_channel_record_is_on_declared_path",
            "status": "pass" if routing["offpath_changed_records"] == 0 else "fail",
            "evidence": "routing-trial-validation.csv and routing-topology.json",
        },
        {
            "criterion": "hydrograph_timestamps_nonnegative_flow_and_volume_consistency",
            "status": "pass" if hydrograph["invalid_timestamp_records"] == 0 and hydrograph["negative_flow_records"] == 0 and hydrograph["lane_timestamps_compatible"] and hydrograph["volume_mismatches"] == 0 else "fail",
            "evidence": "hydrograph-validation-summary.json and h106-1986-day046-volume-check.csv",
        },
        {
            "criterion": "known_positive_adaptive_bracket_and_frozen_replay",
            "status": "pass" if adjudication["known_positive"]["evidence_state"] == "mechanism_traced" and all(item["selected_method_delta_m_s"] == 0.0 for item in adjudication["known_positive"]["endpoint_replays"].values()) else "fail",
            "evidence": "candidate-adjudication.json and h106-1986-day046-adaptive-bracket.csv",
        },
        {
            "criterion": "storage_partitioning_and_retention_acceptable",
            "status": "pass" if projection["acceptable"] else "fail",
            "evidence": "storage-runtime-projection.json and artifact-storage-*.json",
        },
        {
            "criterion": "incomplete_hdrive_replays_stopped_and_dispositioned",
            "status": "pass" if adjudication["hdrive_replays"]["below_0_95"] > 0 and adjudication["hdrive_replays"]["disposition"] == "stopped_excluded_from_candidate_statistics" else "fail",
            "evidence": "candidate-adjudication.json",
        },
    ]
    authorized = all(item["status"] == "pass" for item in criteria)
    report = {
        "schema_version": SCHEMA_VERSION, "pilot_id": selection["pilot_id"],
        "selection_id": selection["selection_id"],
        "selected_hillslopes": [item["hillslope_id"] for item in selection["hillslopes"]],
        "requested_mutation_trials": 64, "terminal_mutation_trials": mutation["terminal_trials"],
        "candidate_rows": mutation["candidate_rows"], "candidate_trials": mutation["candidate_trials"],
        "adjudicated_known_positive": "undisturbed Hill 106, 1986 day 46",
        "criteria": criteria, "full_census_authorized": authorized,
        "disposition": "authorize_full_topanga_census" if authorized else "withhold_full_topanga_census",
        "smallest_remediation": [
            "Remove shared/event-global channel transmission-loss effects so a one-hillslope HBP mutation cannot alter sibling off-path channels.",
            "Make interval chan.out discharge integrate to the same authoritative outflow volume reported by chanwb.out, then rerun routing criteria 5-7.",
        ] if not authorized else [],
    }
    jsonschema.validate(report, SCHEMAS["exit-report"])
    write_json(ARTIFACTS / "phase2a-exit-report.json", report)
    markdown = [
        "# Phase 2A Pilot Exit Report", "",
        f"**Disposition**: {'FULL CENSUS AUTHORIZED' if authorized else 'FULL CENSUS WITHHELD'}", "",
        f"Selection `{selection['selection_id']}` covers Hills " + ", ".join(str(value) for value in report["selected_hillslopes"]) + ".",
        f"All 64 mutation trials completed; {mutation['candidate_rows']} event rows across {mutation['candidate_trials']} trials screened as candidates.", "",
        "## Automatic Exit Criteria", "",
        "| # | Criterion | Status | Evidence |", "| --- | --- | --- | --- |",
    ]
    for index, item in enumerate(criteria, start=1):
        markdown.append(f"| {index} | `{item['criterion']}` | **{item['status'].upper()}** | {item['evidence']} |")
    markdown.extend(["", "## Disposition", ""])
    if authorized:
        markdown.append("Every automatic criterion passed. The full Topanga census is authorized.")
    else:
        markdown.extend([
            f"The full census remains withheld because criteria {', '.join(str(index + 1) for index, item in enumerate(criteria) if item['status'] == 'fail')} failed.", "",
            "Smallest remediation:", "",
            *[f"{index}. {value}" for index, value in enumerate(report["smallest_remediation"], start=1)],
        ])
    markdown.extend(["", "## Cost Projection", "", f"The 1,120-trial initial census projects to {routing_bytes / 1e9:.1f} GB of raw daily routing output and {routing_runtime / 3600:.1f} sequential routing hours ({routing_runtime / 8 / 3600:.1f} hours at eight workers).", ""])
    (ARTIFACTS / "phase2a-exit-report.md").write_text("\n".join(markdown))
    print(json.dumps(report, indent=2, sort_keys=True))


def storage_command(args: argparse.Namespace) -> None:
    selection = json.loads((ARTIFACTS / "pilot-selection.json").read_text())
    evidence = args.evidence_root.resolve() / selection["pilot_id"]
    raw_paths = sorted(
        path
        for path in evidence.glob("routing/**/runs/*")
        if path.name in {"chan.out", "chanwb.out"}
    )
    if len(raw_paths) < 132:
        raise ValueError(f"expected at least 132 retained routing outputs, found {len(raw_paths)}")
    hydrograph = evidence / "hydrograph-h106-1986-day046.parquet"
    if not hydrograph.is_file():
        raise FileNotFoundError(hydrograph)
    artifacts = [storage_artifact(path, evidence) for path in [*raw_paths, hydrograph]]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pilot_id": selection["pilot_id"],
        "external_root": str(evidence),
        "artifact_count": len(artifacts),
        "bytes": sum(item["bytes"] for item in artifacts),
        "artifacts": artifacts,
    }
    write_json(ARTIFACTS / "artifact-storage-routing.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("pilot_id", "artifact_count", "bytes")}, indent=2))


def validate_command(args: argparse.Namespace) -> None:
    for name, schema in SCHEMAS.items():
        jsonschema.validators.validator_for(schema).check_schema(schema)
        path = ARTIFACTS / "schemas" / f"{name}.schema.json"
        if not path.exists() or json.loads(path.read_text()) != schema:
            raise ValueError(f"generated schema drift: {path}")
    jsonschema.validate(json.loads((ARTIFACTS / "scenario-manifest.json").read_text()), SCHEMAS["scenario-manifest"])
    jsonschema.validate(json.loads((ARTIFACTS / "pilot-selection.json").read_text()), SCHEMAS["pilot-selection"])
    if (ARTIFACTS / "mutation-terminal-summary.json").exists():
        jsonschema.validate(json.loads((ARTIFACTS / "mutation-terminal-summary.json").read_text()), SCHEMAS["terminal-ledger"])
    if (ARTIFACTS / "phase2a-exit-report.json").exists():
        jsonschema.validate(json.loads((ARTIFACTS / "phase2a-exit-report.json").read_text()), SCHEMAS["exit-report"])
    if args.verify_external:
        storage_paths = sorted(ARTIFACTS.glob("artifact-storage-*.json"))
        if len(storage_paths) != 3:
            raise ValueError(f"expected three external storage manifests, found {len(storage_paths)}")
        for path in storage_paths:
            validate_storage_manifest(json.loads(path.read_text()))
    print("Phase 2A schemas and committed compact artifacts validate")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observer", type=Path, default=Path("/home/workdir/wepp-forest_260430_baseline/src/wepp_hill"))
    parser.add_argument("--evidence-root", type=Path, default=Path("/home/workdir/peakflow-phase2a-evidence"))
    parser.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 1))
    parser.add_argument("--replay-binary", type=Path)
    parser.add_argument("--watershed", type=Path, default=Path("/home/workdir/wepp-forest_260430_baseline/src/wepp"))
    parser.add_argument("--routing-workers", type=int, default=8)
    parser.add_argument("--verify-external", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inventory").set_defaults(func=inventory_command)
    subparsers.add_parser("mutations").set_defaults(func=mutations_command)
    subparsers.add_parser("adjudicate").set_defaults(func=adjudicate_command)
    subparsers.add_parser("route").set_defaults(func=route_command)
    subparsers.add_parser("hydrographs").set_defaults(func=hydrographs_command)
    subparsers.add_parser("report").set_defaults(func=report_command)
    subparsers.add_parser("storage").set_defaults(func=storage_command)
    subparsers.add_parser("routing-flow-recheck").set_defaults(func=routing_flow_recheck_command)
    subparsers.add_parser("validate").set_defaults(func=validate_command)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
