#!/usr/bin/env python3
"""Evaluate masked-valid SSURGO donor proposals without changing a run."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1


def _numeric_distance(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[float | None, list[str]]:
    fields = sorted(set(reference) & set(candidate))
    deltas: list[float] = []
    used: list[str] = []
    for field in fields:
        try:
            left, right = float(reference[field]), float(candidate[field])
        except (TypeError, ValueError):
            continue
        if math.isfinite(left) and math.isfinite(right):
            deltas.append(abs(left - right))
            used.append(field)
    return (sum(deltas) / len(deltas), used) if deltas else (None, used)


def evaluate_masked_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one precomputed local-support case deterministically."""
    withheld = str(case["withheld_mukey"])
    global_mukey = str(case["global_mukey"])
    support = [(str(mukey), int(count)) for mukey, count in case["candidate_support"]]
    support.sort(key=lambda item: (-item[1], int(item[0])))
    local_mukey = support[0][0] if support else None
    summaries = case.get("soil_summaries", {})
    reference = summaries.get(withheld, {})
    local_distance, fields = _numeric_distance(reference, summaries.get(local_mukey, {})) if local_mukey else (None, [])
    global_distance, _ = _numeric_distance(reference, summaries.get(global_mukey, {}))
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ssurgo_masked_valid_evaluation",
        "case_id": str(case["case_id"]),
        "withheld_mukey": withheld,
        "global_mukey": global_mukey,
        "local_majority_mukey": local_mukey,
        "candidate_support": support,
        "exact_local_recovery": local_mukey == withheld,
        "exact_global_recovery": global_mukey == withheld,
        "local_feature_distance": local_distance,
        "global_feature_distance": global_distance,
        "distance_fields": fields,
        "reason": "local_candidate" if local_mukey else "no_local_candidate",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    cases = json.loads(args.input.read_text(encoding="utf-8"))
    results = [evaluate_masked_case(case) for case in cases]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
