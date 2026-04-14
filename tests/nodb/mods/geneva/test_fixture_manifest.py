from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "geneva"
        / "fixtures_manifest.json"
    )


def test_geneva_fixture_manifest_schema() -> None:
    manifest_path = _manifest_path()
    assert manifest_path.exists(), "fixtures_manifest.json must exist"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["dataset"] == "geneva"
    assert isinstance(payload["fixtures"], list)
    assert payload["fixtures"], "at least one fixture entry is required"

    fixture = payload["fixtures"][0]
    assert isinstance(fixture["fixture_id"], str) and fixture["fixture_id"]
    assert fixture["status"] in {"placeholder", "ready"}
    assert isinstance(fixture["inputs"], dict)
    assert isinstance(fixture["expected"], dict)
    assert "hru_rows_min" in fixture["expected"]
