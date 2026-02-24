from __future__ import annotations

import os
from pathlib import Path

import importlib
import jsonpickle

import pytest
from flask import Flask

from wepppy.nodb.batch_runner import BatchRunner
from wepppy.topo.watershed_collection.watershed_collection import WatershedCollection

try:
    bp_module = importlib.import_module("wepppy.weppcloud.routes.batch_runner.batch_runner_bp")
except ImportError:
    pytest.skip("Batch runner blueprint dependencies missing", allow_module_level=True)

if not hasattr(bp_module, "_current_user_email"):
    pytest.skip("Batch runner blueprint not fully configured in this environment", allow_module_level=True)

pytestmark = pytest.mark.routes

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

    _unwrap("batch_runner.validate_template")
    _unwrap("batch_runner.update_run_directives")
    _unwrap("batch_runner.runstate")

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

def _register_geojson(app: Flask, source_path: Path) -> None:
    with app.app_context():
        root = Path(app.config["BATCH_RUNNER_ROOT"])
        runner = BatchRunner.getInstance(str(root / "demo"))
        collection = WatershedCollection(str(source_path))
        runner.register_geojson(collection)


def test_validate_template_requires_resource(client, app):
    response = client.post(
        "/batch/_/demo/validate-template",
        json={"template": "{slug(properties['HucName'])}"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "Upload a GeoJSON" in payload["error"]["message"]


def test_validate_template_reports_duplicates(client, app):
    _register_geojson(app, DATA_DIR / "simple.geojson")

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
    _register_geojson(app, DATA_DIR / "simple.geojson")

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


def test_validate_template_refreshes_after_external_geojson_update_same_mtime(client, app):
    with app.app_context():
        root = Path(app.config["BATCH_RUNNER_ROOT"])
        runner = BatchRunner.getInstance(str(root / "demo"))
        nodb_path = root / "demo" / BatchRunner.filename
        original_mtime = os.path.getmtime(nodb_path)
        original_size = os.path.getsize(nodb_path)

        detached_runner = BatchRunner.load_detached(str(root / "demo"))
        collection = WatershedCollection(str(DATA_DIR / "simple.geojson"))
        detached_runner._geojson_state = dict(collection.analysis_results)
        detached_runner._geojson_state["_size_probe"] = "x" * 4096

        encoded = jsonpickle.encode(detached_runner)
        with nodb_path.open("w", encoding="utf-8") as fp:
            fp.write(encoded)
            fp.flush()
            os.fsync(fp.fileno())
        assert os.path.getsize(nodb_path) != original_size
        os.utime(nodb_path, (original_mtime, original_mtime))
        runner._nodb_mtime = original_mtime

    response = client.post(
        "/batch/_/demo/validate-template",
        json={"template": "{slug(properties['HucName'])}-{zfill(one_based_index, 3)}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["summary"]["is_valid"] is True


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
    assert "error" not in payload

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
    assert "error" not in payload

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
    assert "error" in payload


def test_runstate_reports_empty_state(client):
    response = client.get("/batch/_/demo/runstate")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "empty"
    assert "report" in payload
