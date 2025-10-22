from __future__ import annotations

import io
import json
from pathlib import Path

import importlib

import pytest
from flask import Flask

from wepppy.nodb.batch_runner import BatchRunner

try:
    bp_module = importlib.import_module("wepppy.weppcloud.routes.batch_runner.batch_runner_bp")
except ImportError:
    pytest.skip("Batch runner blueprint dependencies missing", allow_module_level=True)

if not hasattr(bp_module, "_current_user_email"):
    pytest.skip("Batch runner blueprint not fully configured in this environment", allow_module_level=True)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "batch_runner"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(BatchRunner, "_init_base_project", lambda self: None)
    monkeypatch.setattr(bp_module, "_current_user_email", lambda: "tester@example.com")

    application = Flask(__name__)
    application.config.update(
        TESTING=True,
        SECRET_KEY="testing-secret",
        WTF_CSRF_ENABLED=False,
        SITE_PREFIX="",
        BATCH_RUNNER_ENABLED=True,
        BATCH_RUNNER_ROOT=str(tmp_path / "batches"),
        BATCH_GEOJSON_MAX_MB=2,
    )

    application.register_blueprint(bp_module.batch_runner_bp)

    def _unwrap(endpoint: str) -> None:
        view = application.view_functions[endpoint]
        while hasattr(view, "__wrapped__"):
            view = view.__wrapped__  # type: ignore[attr-defined]
        application.view_functions[endpoint] = view

    _unwrap("batch_runner.upload_geojson")
    _unwrap("batch_runner.validate_template")
    _unwrap("batch_runner.update_run_directives")

    with application.app_context():
        root = Path(application.config["BATCH_RUNNER_ROOT"])
        root.mkdir(parents=True, exist_ok=True)
        batch_dir = root / "demo"
        batch_dir.mkdir(parents=True, exist_ok=True)
        BatchRunner(str(batch_dir), "batch/default_batch.cfg", "dummy_base.cfg")

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _read_state(app: Flask):
    with app.app_context():
        root = Path(app.config["BATCH_RUNNER_ROOT"])
        runner = BatchRunner.getInstance(str(root / "demo"))
        return runner.state_dict()


def test_upload_geojson_success(client, app):
    with (DATA_DIR / "simple.geojson").open("rb") as handle:
        response = client.post(
            "/batch/_/demo/upload-geojson",
            data={"geojson_file": (handle, "sample.geojson")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["resource"]["feature_count"] == 3

    state = _read_state(app)
    resource = state["resources"][BatchRunner.RESOURCE_WATERSHED]
    assert resource["filename"] == "sample.geojson"
    assert resource["feature_count"] == 3


def test_upload_geojson_rejects_invalid_geojson(client):
    with (DATA_DIR / "invalid.geojson").open("rb") as handle:
        response = client.post(
            "/batch/_/demo/upload-geojson",
            data={"geojson_file": (handle, "invalid.geojson")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "FeatureCollection" in payload["error"]


def test_upload_geojson_respects_size_limit(client, monkeypatch):
    monkeypatch.setattr(bp_module, "_max_geojson_size_bytes", lambda: 32)

    content = json.dumps({"type": "FeatureCollection", "features": [{}]}).encode("utf-8")

    response = client.post(
        "/batch/_/demo/upload-geojson",
        data={"geojson_file": (io.BytesIO(content), "oversize.geojson")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_validate_template_requires_resource(client, app):
    response = client.post(
        "/batch/_/demo/validate-template",
        json={"template": "{slug(properties['HucName'])}"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "Upload a GeoJSON" in payload["error"]


def test_validate_template_reports_duplicates(client, app):
    with (DATA_DIR / "simple.geojson").open("rb") as handle:
        client.post(
            "/batch/_/demo/upload-geojson",
            data={"geojson_file": (handle, "sample.geojson")},
            content_type="multipart/form-data",
        )

    response = client.post(
        "/batch/_/demo/validate-template",
        json={"template": "{'constant'}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["summary"]["is_valid"] is False
    assert payload["validation"]["duplicates"]
    assert payload["stored"]["status"] == "invalid"


def test_validate_template_success_path(client, app):
    with (DATA_DIR / "simple.geojson").open("rb") as handle:
        client.post(
            "/batch/_/demo/upload-geojson",
            data={"geojson_file": (handle, "sample.geojson")},
            content_type="multipart/form-data",
        )

    response = client.post(
        "/batch/_/demo/validate-template",
        json={"template": "{slug(properties['HucName'])}-{zfill(one_based_index, 3)}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["summary"]["is_valid"] is True
    assert payload["stored"]["status"] == "ok"
    state = _read_state(app)
    assert state["runid_template"] == "{slug(properties['HucName'])}-{zfill(one_based_index, 3)}"


def test_update_run_directives_accepts_booleans(client, app):
    response = client.post(
        "/batch/_/demo/run-directives",
        json={
            "run_directives": {
                "fetch_dem": True,
                "build_channels": False,
            }
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    directives = {entry["slug"]: entry["enabled"] for entry in payload["run_directives"]}
    assert directives["fetch_dem"] is True
    assert directives["build_channels"] is False

    state = _read_state(app)
    state_directives = {entry["slug"]: entry["enabled"] for entry in state["run_directives"]}
    assert state_directives["fetch_dem"] is True
    assert state_directives["build_channels"] is False


def test_update_run_directives_coerces_string_booleans(client, app):
    response = client.post(
        "/batch/_/demo/run-directives",
        json={
            "run_directives": {
                "fetch_dem": "false",
                "build_channels": "true",
            }
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    directives = {entry["slug"]: entry["enabled"] for entry in payload["run_directives"]}
    assert directives["fetch_dem"] is False
    assert directives["build_channels"] is True

    state = _read_state(app)
    state_directives = {entry["slug"]: entry["enabled"] for entry in state["run_directives"]}
    assert state_directives["fetch_dem"] is False
    assert state_directives["build_channels"] is True


def test_update_run_directives_rejects_non_mapping(client):
    response = client.post(
        "/batch/_/demo/run-directives",
        json={
            "run_directives": ["invalid", "payload"],
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
