#!/usr/bin/env python3
"""Export an observed RQ dependency graph from enqueue trace records."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = Path("wepppy/rq/job-dependency-graph.observed.json")
TRACE_PATH_ENV = "WEPPPY_RQ_TRACE_PATH"
DEFAULT_TRACE_PATH = "/tmp/wepppy_rq_enqueue_trace.jsonl"


def _output_path(repo_root: Path | None = None) -> Path:
    root = (repo_root or REPO_ROOT).resolve()
    return root / OUTPUT_PATH


def _resolve_trace_path(trace_path: str | None) -> Path:
    if trace_path:
        return Path(trace_path)
    return Path(os.getenv(TRACE_PATH_ENV, DEFAULT_TRACE_PATH))


def load_trace_observations(trace_path: Path) -> list[dict[str, Any]]:
    if not trace_path.exists():
        return []

    observations: list[dict[str, Any]] = []
    for raw_line in trace_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            observations.append(payload)

    observations.sort(
        key=lambda item: (
            str(item.get("timestamp_utc", "")),
            str(item.get("parent_job_id", "")),
            str(item.get("child_job_id", "")),
            str(item.get("enqueue_target", "")),
        )
    )
    return observations


def aggregate_observed_edges(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: dict[tuple[Any, ...], dict[str, Any]] = {}
    for observation in observations:
        depends = list(observation.get("depends_on_job_ids") or [])
        key = (
            observation.get("parent_enqueue_target"),
            observation.get("enqueue_target"),
            observation.get("queue_name"),
            tuple(depends),
        )
        aggregate = aggregates.get(key)
        if aggregate is None:
            aggregate = {
                "parent_enqueue_target": observation.get("parent_enqueue_target"),
                "enqueue_target": observation.get("enqueue_target"),
                "queue_name": observation.get("queue_name"),
                "depends_on_job_ids": depends,
                "count": 0,
                "parent_job_ids": set(),
                "child_job_ids": set(),
            }
            aggregates[key] = aggregate

        aggregate["count"] += 1
        parent_job_id = observation.get("parent_job_id")
        child_job_id = observation.get("child_job_id")
        if parent_job_id:
            aggregate["parent_job_ids"].add(str(parent_job_id))
        if child_job_id:
            aggregate["child_job_ids"].add(str(child_job_id))

    rendered: list[dict[str, Any]] = []
    for key in sorted(
        aggregates,
        key=lambda item: (
            str(item[0] or ""),
            str(item[1] or ""),
            str(item[2] or ""),
            tuple(str(dep) for dep in item[3]),
        ),
    ):
        aggregate = aggregates[key]
        rendered.append(
            {
                "parent_enqueue_target": aggregate["parent_enqueue_target"],
                "enqueue_target": aggregate["enqueue_target"],
                "queue_name": aggregate["queue_name"],
                "depends_on_job_ids": aggregate["depends_on_job_ids"],
                "count": aggregate["count"],
                "parent_job_ids": sorted(aggregate["parent_job_ids"]),
                "child_job_ids": sorted(aggregate["child_job_ids"]),
            }
        )
    return rendered


def build_observed_graph_payload(*, trace_path: Path) -> dict[str, Any]:
    observations = load_trace_observations(trace_path)
    aggregated_edges = aggregate_observed_edges(observations)
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trace_path": str(trace_path),
        "observation_count": len(observations),
        "aggregated_edge_count": len(aggregated_edges),
        "aggregated_edges": aggregated_edges,
        "observations": observations,
    }


def serialize_observed_graph(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _comparison_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    # Generation time is expected to differ between runs and should not cause check drift.
    normalized.pop("generated_at_utc", None)
    return normalized


def _write_observed_graph(*, repo_root: Path | None = None, trace_path: Path) -> int:
    root = (repo_root or REPO_ROOT).resolve()
    output_path = _output_path(root)
    payload = build_observed_graph_payload(trace_path=trace_path)
    output_path.write_text(serialize_observed_graph(payload), encoding="utf-8")
    rel = output_path.relative_to(root).as_posix()
    print(f"wrote observed graph with {payload['observation_count']} observations to {rel}")
    return 0


def _check_observed_graph(*, repo_root: Path | None = None, trace_path: Path) -> int:
    root = (repo_root or REPO_ROOT).resolve()
    output_path = _output_path(root)
    expected_payload = build_observed_graph_payload(trace_path=trace_path)
    if not output_path.exists():
        rel = output_path.relative_to(root).as_posix()
        print("Observed RQ dependency graph drift detected:")
        print(f"- {rel}")
        return 1

    try:
        current_payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        rel = output_path.relative_to(root).as_posix()
        print("Observed RQ dependency graph drift detected:")
        print(f"- {rel}")
        return 1

    if _comparison_payload(current_payload) != _comparison_payload(expected_payload):
        rel = output_path.relative_to(root).as_posix()
        print("Observed RQ dependency graph drift detected:")
        print(f"- {rel}")
        return 1
    rel = output_path.relative_to(root).as_posix()
    print(f"Observed RQ dependency graph is up to date ({rel})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-path", help=f"Trace log path (default: ${TRACE_PATH_ENV} or {DEFAULT_TRACE_PATH}).")
    parser.add_argument("--write", action="store_true", help="Write observed graph JSON artifact.")
    parser.add_argument("--check", action="store_true", help="Fail if observed graph artifact is stale.")
    args = parser.parse_args(argv)

    trace_path = _resolve_trace_path(args.trace_path)

    if not args.write and not args.check:
        payload = build_observed_graph_payload(trace_path=trace_path)
        print(serialize_observed_graph(payload), end="")
        return 0

    if args.write:
        _write_observed_graph(repo_root=REPO_ROOT, trace_path=trace_path)
    if args.check:
        return _check_observed_graph(repo_root=REPO_ROOT, trace_path=trace_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
