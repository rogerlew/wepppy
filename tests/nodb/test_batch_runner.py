from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.nodb.batch_runner import BatchRunner, BatchRunnerManifest
from wepppy.weppcloud.routes.batch_runner.batch_runner_bp import (
    _create_batch_project,
    _validate_batch_name,
)


def test_manifest_defaults_are_sane():
    manifest = BatchRunnerManifest()
    assert manifest.version == 2
    assert manifest.selected_tasks == []
    assert manifest.runs == {}
    assert manifest.history == []
    assert manifest.base_config is None
    assert manifest.batch_config is None


def test_batch_runner_initialises_manifest(tmp_path: Path):
    wd = tmp_path / "batch" / "example"
    wd.mkdir(parents=True)

    wd = str(wd)
    BatchRunner(wd, "batch/default_batch.cfg", "disturbed9002_wbt.cfg")
    runner = BatchRunner.getInstance(wd)

    # Manifest should be created with default values
    manifest = runner.manifest
    assert manifest.batch_name is None
    assert manifest.version == 2
    assert manifest.base_config == "disturbed9002_wbt"
    assert manifest.batch_config == "default_batch"
    assert manifest.config == "disturbed9002_wbt"

    # Updates should set known attributes and tuck unknowns into metadata
    runner.update_manifest(batch_name="demo", foo="bar")
    assert runner.manifest.batch_name == "demo"
    assert runner.manifest.metadata.get("foo") == "bar"

    # Reset brings us back to defaults
    runner.reset_manifest()
    assert runner.manifest.batch_name is None
    assert runner.manifest.metadata == {}
    assert runner.manifest.base_config == "disturbed9002_wbt"
    assert runner.manifest.batch_config == "default_batch"


def test_validate_batch_name_rules():
    assert _validate_batch_name("batch_123") == "batch_123"

    with pytest.raises(ValueError):
        _validate_batch_name(" ")

    with pytest.raises(ValueError):
        _validate_batch_name("bad name")

    with pytest.raises(ValueError):
        _validate_batch_name("_base")


def test_initialize_batch_project_scaffolds_directories(tmp_path: Path):
    batch_root = tmp_path / "batch"

    result = _create_batch_project(
        batch_name="demo_batch",
        base_config="disturbed9002_wbt",
        created_by="tester@example.com",
        batch_config="default_batch",
        batch_root=batch_root,
    )

    batch_dir = batch_root / "demo_batch"
    assert batch_dir.exists()
    assert (batch_dir / "_base").is_dir()
    assert (batch_dir / "resources").is_dir()

    manifest_path = batch_dir / "batch_runner.nodb"
    assert manifest_path.exists()

    manifest = result["manifest"]
    assert manifest["batch_name"] == "demo_batch"
    assert manifest["base_config"].endswith("disturbed9002_wbt")
    assert manifest["config"] == "disturbed9002_wbt"
    assert manifest["batch_config"] == "default_batch"
    assert manifest["created_by"] == "tester@example.com"
    assert manifest["history"][0]["event"] == "created"


def test_initialize_batch_project_duplicate(tmp_path: Path):
    batch_root = tmp_path / "batch"

    _create_batch_project(
        batch_name="duplicate",
        base_config="disturbed9002_wbt",
        created_by="tester@example.com",
        batch_config="default_batch",
        batch_root=batch_root,
    )

    with pytest.raises(FileExistsError):
        _create_batch_project(
            batch_name="duplicate",
            base_config="disturbed9002_wbt",
            created_by="tester@example.com",
            batch_config="default_batch",
            batch_root=batch_root,
        )


def test_initialize_batch_project_missing_config(tmp_path: Path):
    batch_root = tmp_path / "batch"

    with pytest.raises(FileNotFoundError):
        _create_batch_project(
            batch_name="missing_config",
            base_config="not_real_config",
            created_by="tester@example.com",
            batch_config="default_batch",
            batch_root=batch_root,
        )


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "batch_runner"


def test_analyse_geojson_extracts_metadata():
    sample_path = DATA_DIR / "simple.geojson"
    metadata = BatchRunner.analyse_geojson(sample_path)

    assert metadata["feature_count"] == 3
    assert metadata["epsg"] == "EPSG:4326"
    assert metadata["attribute_schema"]["NumericId"] == "integer"
    assert metadata["properties"] == ["HucName", "NumericId", "Region"]
    assert metadata["bbox"][0] < metadata["bbox"][2]


def test_validate_template_detects_duplicates_and_errors():
    payload = json.loads((DATA_DIR / "simple.geojson").read_text())
    features = payload["features"]

    valid = BatchRunner.validate_template("{slug(properties['HucName'])}", features)
    assert valid["summary"]["is_valid"] is True
    assert valid["duplicates"] == []

    duplicate = BatchRunner.validate_template("{'constant'}", features)
    assert duplicate["summary"]["is_valid"] is False
    assert duplicate["duplicates"][0]["run_id"] == "constant"

    missing = BatchRunner.validate_template("{properties['missing']}", features)
    assert missing["summary"]["is_valid"] is False
    assert missing["errors"]


def test_register_resource_marks_validation_stale(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(BatchRunner, "_init_base_project", lambda self: None)

    wd = tmp_path / "batch" / "unit"
    wd.mkdir(parents=True)

    runner = BatchRunner(str(wd), "batch/default_batch.cfg", "disturbed9002_wbt.cfg")

    validation_payload = {
        "template": "{index}",
        "template_hash": "hash",
        "resource_id": BatchRunner.RESOURCE_WATERSHED,
        "resource_checksum": "abc",
        "summary": {
            "total_features": 3,
            "valid_run_ids": 3,
            "unique_run_ids": 3,
            "duplicate_run_ids": 0,
            "errors": 0,
            "is_valid": True,
        },
        "duplicates": [],
        "errors": [],
        "preview": [],
        "validation_hash": "vh",
        "status": "ok",
    }

    runner.record_template_validation(validation_payload, user="tester@example.com")

    resource_metadata = {
        "resource_type": "geojson",
        "filename": "simple.geojson",
        "relative_path": "resources/simple.geojson",
        "size_bytes": 1024,
        "checksum": "new",
        "feature_count": 3,
        "bbox": [-116.91234, 46.7321, -116.7021, 46.8013],
    }

    stored = runner.register_resource(
        BatchRunner.RESOURCE_WATERSHED,
        resource_metadata,
        user="tester@example.com",
    )

    assert stored["resource_id"] == BatchRunner.RESOURCE_WATERSHED
    assert runner.manifest.resources[BatchRunner.RESOURCE_WATERSHED]["checksum"] == "new"
    validation_state = runner.manifest.metadata["template_validation"]
    assert validation_state["status"] == "stale"
