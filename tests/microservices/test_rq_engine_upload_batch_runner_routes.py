from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_batch_runner_routes


pytestmark = pytest.mark.microservice


class DummyBatchRunner:
    def __init__(self, wd: Path) -> None:
        self.batch_name = "demo"
        self.base_config = "cfg"
        self.wd = str(wd)
        self.resources_dir = str(wd / "resources")
        self.run_directives = {}
        self.geojson_state = None
        self.runid_template_state = None
        self._sbs_resource = None

    def sbs_resource_state(self):
        return self._sbs_resource

    def register_geojson(self, collection, metadata=None) -> None:
        self.geojson_state = collection.analysis_results

    @property
    def sbs_map(self) -> str | None:
        return None

    @sbs_map.setter
    def sbs_map(self, value: str) -> None:
        self._sbs_resource = {"relative_path": value}

    @property
    def sbs_map_metadata(self) -> dict | None:
        return None

    @sbs_map_metadata.setter
    def sbs_map_metadata(self, value: dict) -> None:
        return None


class DummyCollection:
    def __init__(self, path: str) -> None:
        self._analysis = True
        self._analysis_results = {"feature_count": 1}

    @property
    def analysis_results(self) -> dict:
        return self._analysis_results

    def update_analysis_results(self, metadata: dict) -> dict:
        self._analysis_results.update(metadata)
        return self._analysis_results


def test_upload_geojson_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", b"{}")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "GeoJSON uploaded successfully."


def test_upload_geojson_rejects_oversize_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_geojson_max_bytes", lambda: 4)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", b"abcdef")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_upload_geojson_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.txt", b"{}")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Only .geojson or .json files are supported."
    assert payload["error"]["details"] == "Only .geojson or .json files are supported."
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


def test_upload_sbs_map_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "sbs_map_sanity_check", lambda path: (0, ""))
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-sbs-map",
            files={"sbs_map": ("map.tif", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "SBS map uploaded successfully."


def test_upload_sbs_map_rejects_oversize_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "SBS_MAP_MAX_BYTES", 4)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-sbs-map",
            files={"sbs_map": ("map.tif", b"abcdef")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_upload_sbs_map_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-sbs-map",
            files={"sbs_map": ("map.exe", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Only GeoTIFF/IMG/VRT rasters are supported."


def test_upload_geojson_load_error_redacts_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Failed to load batch runner"
    assert payload["error"]["details"] == "Failed to load batch runner"
    assert payload["error"]["code"] == "internal_error"
    assert payload["error_id"]
    assert "Traceback" not in payload["error"]["details"]
