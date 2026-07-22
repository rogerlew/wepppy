#!/usr/bin/env python3
"""Run committed synthetic SSURGO local-donor adversarial scenarios.

This is deliberately an explicit release-evidence command rather than a pytest
test. It calls the production shallow-profile and vector-selection functions,
writes a JSON report, and returns nonzero if any fixture expectation changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from wepppy.soils.ssurgo.fallback import direct_shallow_profile, select_vector_donor


SCHEMA_VERSION = 1
DEFAULT_FIXTURE = (
    REPOSITORY_ROOT
    / "docs/work-packages/20260722_ssurgo_intelligent_fallback_rollout/fixtures"
    / "ssurgo_fallback_adversarial_cases.json"
)


def _profile(specification: Mapping[str, Any]) -> dict[str, Any]:
    if "layers" in specification:
        layers = specification["layers"]
        if not isinstance(layers, list):
            raise ValueError("profile layers must be a list")
        return direct_shallow_profile(layers)
    direct_values = specification.get("direct_values")
    if not isinstance(direct_values, Mapping):
        raise ValueError("profile must provide direct_values or layers")
    return {
        "horizon_index": specification.get("horizon_index", 0),
        "chkey": specification.get("chkey", "fixture"),
        "direct_values": dict(direct_values),
    }


def evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a fixture with the production first-supported-ring rule."""
    source_profile = _profile(case["source_profile"])
    profiles = {
        str(mukey): _profile(specification)
        for mukey, specification in case["candidate_profiles"].items()
    }
    global_mukey = str(case["global_mukey"])
    outcome: dict[str, Any] = {
        "case_id": str(case["case_id"]),
        "source_mukey": str(case["source_mukey"]),
        "policy": "watershed_global",
        "mukey": global_mukey,
        "radius_m": None,
        "fallback_reason": "no_comparable_local_donor",
    }
    for ring in case["rings"]:
        support = [(str(mukey), int(pixel_count)) for mukey, pixel_count in ring["support"]]
        if not support:
            continue
        candidates = [
            {
                "mukey": mukey,
                "pixel_support": pixel_count,
                "profile": profiles.get(
                    mukey,
                    {"horizon_index": None, "chkey": None, "direct_values": {}},
                ),
            }
            for mukey, pixel_count in support
        ]
        selected = select_vector_donor(source_profile, candidates)
        outcome["radius_m"] = float(ring["radius_m"])
        outcome["candidate_support"] = support
        if selected is not None:
            outcome.update(
                {
                    "policy": "ssurgo_local_vector_profile_v1",
                    "mukey": str(selected["mukey"]),
                    "fallback_reason": None,
                    "shared_fields": selected["shared_fields"],
                    "distance": selected["distance"],
                }
            )
        return outcome
    return outcome


def _assert_expected(case: Mapping[str, Any], outcome: Mapping[str, Any]) -> list[str]:
    expected = case["expected"]
    mismatches = []
    for key in ("policy", "mukey", "radius_m", "fallback_reason"):
        if outcome.get(key) != expected.get(key):
            mismatches.append(f"{key}: expected {expected.get(key)!r}, got {outcome.get(key)!r}")
    return mismatches


def run(fixture_path: Path) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {fixture.get('schema_version')!r}")
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture must contain at least one case")
    results = []
    failures = []
    for case in cases:
        outcome = evaluate_case(case)
        mismatches = _assert_expected(case, outcome)
        results.append({**outcome, "passed": not mismatches})
        if mismatches:
            failures.append({"case_id": outcome["case_id"], "mismatches": mismatches})
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture": str(fixture_path),
        "case_count": len(results),
        "passed_count": len(results) - len(failures),
        "failed_count": len(failures),
        "results": results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--report", type=Path, help="write the full JSON report to this path")
    arguments = parser.parse_args()
    report = run(arguments.fixture)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if arguments.report is not None:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    return 1 if report["failed_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
