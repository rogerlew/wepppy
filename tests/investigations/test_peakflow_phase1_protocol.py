from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.peakflow_phase1_protocol import SCHEMAS, SCHEMA_VERSION


pytestmark = pytest.mark.unit


SCHEMA_DIR = (
    Path(__file__).parents[2]
    / "docs/work-packages/20260808_peakflow_phase1/artifacts/schemas"
)
ARTIFACT_DIR = SCHEMA_DIR.parent


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_committed_schema_matches_generator(name: str) -> None:
    committed = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())
    assert committed == SCHEMAS[name]
    jsonschema.Draft7Validator.check_schema(committed)


def test_mutation_requires_requested_and_realized_values() -> None:
    validator = jsonschema.Draft7Validator(SCHEMAS["mutation-manifest"])
    invalid = {
        "schema_version": SCHEMA_VERSION,
        "mutation_id": "m1",
        "target": "h106",
        "parameter": "ksat",
        "requested_value": 35.0,
        "units": "mm/h",
    }
    assert any(error.validator == "required" for error in validator.iter_errors(invalid))


def test_event_presence_is_explicit() -> None:
    validator = jsonschema.Draft7Validator(SCHEMAS["event-scalar"])
    invalid = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "e1",
        "run_id": "r1",
        "hillslope_id": "106",
        "ofe": 1,
        "model_day": 1,
        "solver_call_ordinal": 1,
    }
    assert any(error.validator == "required" for error in validator.iter_errors(invalid))


@pytest.mark.parametrize("name", ["observer-build-manifest.json", "replay-build-manifest.json"])
def test_build_manifests_conform(name: str) -> None:
    jsonschema.validate(json.loads((ARTIFACT_DIR / name).read_text()), SCHEMAS["build-manifest"])


@pytest.mark.parametrize("name", ["topanga-h106-1980-ksat20.json", "topanga-h106-1980-ksat35.json"])
def test_replay_reports_conform(name: str) -> None:
    report = json.loads((ARTIFACT_DIR / "replay-reports" / name).read_text())
    jsonschema.validate(report, SCHEMAS["replay-report"])
