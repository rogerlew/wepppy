from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.unit

REQUIRED_INPUT_KEYS = {
    "bound_tif",
    "landuse_tif",
    "hydgrpdcd_tif",
    "burn_severity_tif",
    "metadata_json",
}

REQUIRED_EXPECTED_KEYS = {
    "hru_rows_min",
    "hru_rows_max",
    "required_hru_fields",
    "required_status_fields",
}

REQUIRED_HRU_FIELDS = {
    "hru_id",
    "area_m2",
    "landuse_class",
    "hsg_group",
    "burn_severity_class",
    "hydrophobic_class",
}

REQUIRED_STATUS_FIELDS = {"phase", "warnings", "artifacts"}
PLACEHOLDER_STATUS = "placeholder"


def _data_root() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "data"
        / "geneva"
    )


def _manifest_path() -> Path:
    return _data_root() / "fixtures_manifest.json"


def _load_manifest() -> dict[str, Any]:
    manifest_path = _manifest_path()
    assert manifest_path.exists(), "fixtures_manifest.json must exist"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_geneva_fixture_manifest_schema() -> None:
    payload = _load_manifest()
    assert payload["schema_version"] == 1
    assert payload["dataset"] == "geneva"
    assert isinstance(payload["fixtures"], list)
    assert payload["fixtures"], "at least one fixture entry is required"

    for fixture in payload["fixtures"]:
        assert isinstance(fixture["fixture_id"], str) and fixture["fixture_id"]
        assert fixture["status"] == "ready"
        assert isinstance(fixture["description"], str) and fixture["description"]
        assert isinstance(fixture["inputs"], dict)
        assert isinstance(fixture["metadata"], dict)
        assert isinstance(fixture["expected"], dict)


def test_geneva_fixture_catalog_has_ready_synthetic_fixture() -> None:
    payload = _load_manifest()
    fixtures = payload["fixtures"]

    fixture_ids = [fixture["fixture_id"] for fixture in fixtures]
    assert len(set(fixture_ids)) == len(fixture_ids), "fixture_id values must be unique"

    for fixture in fixtures:
        assert fixture["status"] != PLACEHOLDER_STATUS, (
            f"{fixture['fixture_id']} still marked as placeholder"
        )

    ready_synthetic = [
        fixture
        for fixture in fixtures
        if fixture["status"] == "ready" and fixture["metadata"].get("synthetic") is True
    ]
    assert ready_synthetic, "at least one ready synthetic Geneva fixture is required"


def test_geneva_fixture_inputs_exist() -> None:
    payload = _load_manifest()
    data_root = _data_root()

    for fixture in payload["fixtures"]:
        inputs = fixture["inputs"]
        assert REQUIRED_INPUT_KEYS.issubset(inputs.keys())

        for key in REQUIRED_INPUT_KEYS:
            relpath = inputs[key]
            assert isinstance(relpath, str) and relpath
            path = data_root / relpath
            assert path.exists(), f"{fixture['fixture_id']} missing input {key}: {path}"
            assert path.is_file(), f"{fixture['fixture_id']} input must be a file: {path}"


def test_geneva_fixture_metadata_schema() -> None:
    payload = _load_manifest()
    data_root = _data_root()

    for fixture in payload["fixtures"]:
        metadata = fixture["metadata"]
        assert metadata["synthetic"] is True
        assert isinstance(metadata["crs"], str) and metadata["crs"].startswith("EPSG:")

        grid = metadata["grid"]
        assert isinstance(grid["rows"], int) and grid["rows"] > 0
        assert isinstance(grid["cols"], int) and grid["cols"] > 0
        assert isinstance(grid["cell_size_m"], int | float) and grid["cell_size_m"] > 0

        fixture_metadata_path = data_root / fixture["inputs"]["metadata_json"]
        fixture_metadata = json.loads(fixture_metadata_path.read_text(encoding="utf-8"))
        assert fixture_metadata["fixture_id"] == fixture["fixture_id"]
        assert fixture_metadata["synthetic"] is True
        assert fixture_metadata["grid"] == grid
        assert fixture_metadata["crs"] == metadata["crs"]


def test_geneva_fixture_expected_contract_fields() -> None:
    payload = _load_manifest()

    for fixture in payload["fixtures"]:
        expected = fixture["expected"]
        assert REQUIRED_EXPECTED_KEYS.issubset(expected.keys())

        hru_rows_min = expected["hru_rows_min"]
        hru_rows_max = expected["hru_rows_max"]
        assert isinstance(hru_rows_min, int) and hru_rows_min >= 1
        assert isinstance(hru_rows_max, int) and hru_rows_max >= hru_rows_min

        required_hru_fields_values = expected["required_hru_fields"]
        assert isinstance(required_hru_fields_values, list) and required_hru_fields_values
        assert all(
            isinstance(field, str) and field for field in required_hru_fields_values
        )
        required_hru_fields = set(required_hru_fields_values)
        assert REQUIRED_HRU_FIELDS.issubset(required_hru_fields)

        required_status_fields_values = expected["required_status_fields"]
        assert isinstance(required_status_fields_values, list) and required_status_fields_values
        assert all(
            isinstance(field, str) and field for field in required_status_fields_values
        )
        required_status_fields = set(required_status_fields_values)
        assert REQUIRED_STATUS_FIELDS.issubset(required_status_fields)
