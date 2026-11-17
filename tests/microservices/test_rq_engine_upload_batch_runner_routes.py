import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_batch_runner_routes
from wepppy.microservices import vector_upload_normalization
from wepppy.nodb.base import NoDbAlreadyLockedError


pytestmark = pytest.mark.microservice

@pytest.fixture(autouse=True)
def feature_accounts(monkeypatch):
    from tests.factories.feature_access import stub_feature_accounts
    stub_feature_accounts(monkeypatch)


class _Reservation:
    reservation_id = "route-test-reservation"

    def commit(self, exact_bytes: int) -> None:
        self.exact_bytes = exact_bytes

    def release_prewrite(self) -> None:
        self.released = True


class _Ledger:
    def reserve(self, **kwargs: Any) -> _Reservation:
        return _Reservation()


class _Lease:
    def __init__(self) -> None:
        self.owned = True

    def assert_owned(self) -> None:
        assert self.owned

    def release(self) -> None:
        self.owned = False


@pytest.fixture(autouse=True)
def bounded_vector_normalizer(monkeypatch: pytest.MonkeyPatch) -> None:
    real_prepare = vector_upload_normalization.prepare_vector_upload

    def prepare(**kwargs):
        return real_prepare(
            **kwargs,
            ledger=_Ledger(),
            scope_lease_factory=lambda _scope: _Lease(),
        )

    monkeypatch.setattr(upload_batch_runner_routes, "prepare_vector_upload", prepare)


def _polygon_bytes(*, label: str = "one") -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": label},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-116.0, 46.0], [-115.9, 46.0], [-115.9, 46.1], [-116.0, 46.0]]
                        ],
                    },
                }
            ],
        },
        separators=(",", ":"),
    ).encode()



class DummyBatchRunner:
    def __init__(self, wd: Path) -> None:
        self.batch_name = "demo"
        self.base_config = "cfg"
        self.runid = "batch;;demo"
        self.wd = str(wd)
        self.resources_dir = str(wd / "resources")
        self.run_directives = {}
        self._geojson_state = None
        self._runid_template_state = None
        self._sbs_resource = None
        self.sbs_grouped_update_calls: list[tuple[str | None, dict | None]] = []

    def sbs_resource_state(self):
        return self._sbs_resource

    def register_geojson(self, collection, metadata=None) -> None:
        self.geojson_state = collection.analysis_results

    @contextmanager
    def locked(self):
        yield self

    @property
    def geojson_state(self):
        return self._geojson_state

    @geojson_state.setter
    def geojson_state(self, value) -> None:
        self._geojson_state = value

    @property
    def runid_template_state(self):
        return self._runid_template_state

    @runid_template_state.setter
    def runid_template_state(self, value) -> None:
        self._runid_template_state = value

    def apply_sbs_resource_update(self, *, sbs_map: str | None = None, metadata: dict | None = None) -> None:
        self.sbs_grouped_update_calls.append((sbs_map, metadata))
        resource = dict(metadata or {})
        if sbs_map is not None:
            resource["relative_path"] = sbs_map
        self._sbs_resource = resource

    @property
    def sbs_map(self) -> str | None:
        return None

    @sbs_map.setter
    def sbs_map(self, value: str) -> None:
        raise AssertionError("Legacy sbs_map setter path should not be used")

    @property
    def sbs_map_metadata(self) -> dict | None:
        return None

    @sbs_map_metadata.setter
    def sbs_map_metadata(self, value: dict) -> None:
        raise AssertionError("Legacy sbs_map_metadata setter path should not be used")


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
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(upload_batch_runner_routes, "require_feature_access", lambda claims, feature: None)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "http://shape-converter.test/convert")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", _polygon_bytes())},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "GeoJSON uploaded successfully."
    canonical = tmp_path / "resources" / "data.geojson"
    assert canonical.read_bytes() == _polygon_bytes()
    attempt = next((tmp_path / "resources" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    original = next((attempt / "original").iterdir())
    assert original.read_bytes() == _polygon_bytes()
    assert receipt["status"] == "accepted"
    assert receipt["canonical_path"] == "resources/data.geojson"


def test_exact_converter_formats_cross_batch_http_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    fixture_root_value = os.getenv("VECTOR_UPLOAD_INTEGRATION_FIXTURES")
    if not converter_url or not fixture_root_value:
        pytest.skip("exact converter integration environment is not configured")
    batch_runner = DummyBatchRunner(tmp_path)
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", converter_url)
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda *_args, **_kwargs: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(upload_batch_runner_routes, "require_feature_access", lambda *_args: None)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)
    fixture_root = Path(fixture_root_value)
    semantics: list[dict[str, object]] = []
    with TestClient(rq_engine.app) as client:
        for suffix, fixture_suffix in (("geojson", "geojson"), ("zip", "zip"), ("parquet", "parquet"), ("geoparquet", "parquet")):
            response = client.post(
                "/api/batch/_/demo/upload-geojson",
                files={"geojson_file": (f"polygon.{suffix}", (fixture_root / f"polygon.{fixture_suffix}").read_bytes())},
            )
            assert response.status_code == 200
            payload = json.loads((tmp_path / "resources" / "polygon.geojson").read_text())
            semantics.append({"geometry": payload["features"][0]["geometry"], "properties": payload["features"][0]["properties"]})
    from shapely.geometry import shape
    baseline = shape(semantics[0]["geometry"])
    assert all(item["properties"] == semantics[0]["properties"] for item in semantics[1:])
    assert all(baseline.equals(shape(item["geometry"])) for item in semantics[1:])


def test_upload_geojson_rejects_oversize_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
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
    assert payload["error"]["message"] == "Uploaded vector exceeds the endpoint size limit."
    assert payload["error"]["details"] == "Uploaded vector exceeds the endpoint size limit."
    assert payload["error"]["code"] == "vector_limit_exceeded"
    assert payload["error_id"]


def test_upload_geojson_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
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
    assert payload["error"]["message"] == "Upload a GeoJSON, Shapefile ZIP, or GeoParquet file."
    assert payload["error"]["details"] == "Upload a GeoJSON, Shapefile ZIP, or GeoParquet file."
    assert payload["error"]["code"] == "unsupported_vector"
    assert payload["error_id"]


def test_upload_geojson_normalizes_binary_and_publishes_converter_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    batch_runner = DummyBatchRunner(tmp_path)
    canonical = _polygon_bytes(label="converted")
    converter_calls: list[str] = []

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {
            "token_class": "user",
            "user_id": 7,
            "sub": "7",
            "roles": ["Admin"],
            "email": "must-not-enter-receipt@example.test",
        },
    )
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "http://shape-converter.test/convert")
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(upload_batch_runner_routes, "require_feature_access", lambda claims, feature: None)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    def convert(**kwargs):
        converter_calls.append(kwargs["submitted_name"])
        return canonical, {
            "request_id": "converter-request",
            "source_size": kwargs["source_size"],
            "source_sha256": kwargs["source_sha256"],
            "canonical_size": len(canonical),
            "canonical_sha256": vector_upload_normalization.hashlib.sha256(canonical).hexdigest(),
            "parser_provenance": {
                "binary_name": "shape_parser_cli",
                "binary_version": "test",
                "binary_sha256": "a" * 64,
                "cargo_lock_sha256": "b" * 64,
                "source_revision": "test-revision",
            },
        }

    monkeypatch.setattr(vector_upload_normalization, "_converter_payload", convert)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.zip", b"bounded archive bytes")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    assert converter_calls == ["data.zip"]
    assert (tmp_path / "resources" / "data.geojson").exists()
    attempt = next((tmp_path / "resources" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    original = next((attempt / "original").iterdir())
    assert original.read_bytes() == b"bounded archive bytes"
    assert receipt["detected_format"] == "shapefile"
    assert receipt["parser_provenance"]["binary_name"] == "shape_parser_cli"
    assert receipt["actor"] == {"kind": "human", "user_id": 7}
    assert "email" not in json.dumps(receipt)


def test_upload_geojson_registration_failure_restores_previous_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)
    accepted = tmp_path / "resources" / "data.geojson"
    accepted.parent.mkdir()
    previous = _polygon_bytes(label="previous")
    accepted.write_bytes(previous)
    previous_state = {"filename": "data.geojson", "marker": "previous"}
    batch_runner.geojson_state = previous_state

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    def fail_registration(collection, metadata=None) -> None:
        raise RuntimeError("registration failed")

    monkeypatch.setattr(batch_runner, "register_geojson", fail_registration)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", _polygon_bytes(label="replacement"))},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 500
    assert accepted.read_bytes() == previous
    assert batch_runner.geojson_state == previous_state
    attempt = next((tmp_path / "resources" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert receipt["status"] == "rejected"
    assert receipt["error_code"] == "workflow_publication_failed"


def test_upload_geojson_receipt_failure_restores_previous_file_and_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)
    accepted = tmp_path / "resources" / "data.geojson"
    accepted.parent.mkdir()
    previous = _polygon_bytes(label="previous")
    accepted.write_bytes(previous)
    previous_state = {"filename": "data.geojson", "marker": "previous"}
    batch_runner.geojson_state = previous_state
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)
    monkeypatch.setattr(
        vector_upload_normalization.PreparedVectorUpload,
        "_complete_publication",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("receipt fsync failed")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", _polygon_bytes(label="replacement"))},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 500
    assert accepted.read_bytes() == previous
    assert batch_runner.geojson_state == previous_state
    attempt = next((tmp_path / "resources" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert receipt["status"] == "rejected"


def test_upload_geojson_rejects_point_before_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)
    accepted = tmp_path / "resources" / "data.geojson"
    accepted.parent.mkdir()
    previous = _polygon_bytes(label="previous")
    accepted.write_bytes(previous)
    previous_state = {"filename": "data.geojson", "marker": "previous"}
    batch_runner.geojson_state = previous_state
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "WatershedCollection", DummyCollection)
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)
    point = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Point", "coordinates": [-116.0, 46.0]},
            }],
        }
    ).encode()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-geojson",
            files={"geojson_file": ("data.geojson", point)},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_vector"
    assert accepted.read_bytes() == previous
    assert batch_runner.geojson_state == previous_state


def test_upload_sbs_map_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tests.factories.raster import sbs_raster_bytes

    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "sbs_map_sanity_check", lambda path: (0, ""))
    monkeypatch.setattr(upload_batch_runner_routes, "SoilBurnSeverityMap", lambda path: SimpleNamespace(burn_class_counts={0: 1}))
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-sbs-map",
            files={"sbs_map": ("map.tif", sbs_raster_bytes(tmp_path / "source.tif"))},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "SBS map uploaded successfully."
    assert len(batch_runner.sbs_grouped_update_calls) == 1
    update_path, update_metadata = batch_runner.sbs_grouped_update_calls[0]
    assert update_path == "resources/map.tif"
    assert update_metadata is not None
    assert update_metadata["resource_type"] == "sbs_map"
    assert update_metadata["filename"] == "map.tif"
    assert payload["resource"]["relative_path"] == "resources/map.tif"


def test_upload_sbs_map_retries_grouped_update_after_lock_clear(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tests.factories.raster import sbs_raster_bytes

    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
    )
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(
        upload_batch_runner_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: batch_runner,
    )
    monkeypatch.setattr(upload_batch_runner_routes, "sbs_map_sanity_check", lambda path: (0, ""))
    monkeypatch.setattr(upload_batch_runner_routes, "SoilBurnSeverityMap", lambda path: SimpleNamespace(burn_class_counts={0: 1}))
    monkeypatch.setattr(upload_batch_runner_routes, "secure_filename", lambda name: name)

    clear_calls: list[str] = []
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "clear_locks",
        lambda runid: clear_calls.append(runid),
    )

    grouped_call_count = {"count": 0}
    original_update = batch_runner.apply_sbs_resource_update

    def flaky_grouped_update(*, sbs_map: str | None = None, metadata: dict | None = None) -> None:
        grouped_call_count["count"] += 1
        if grouped_call_count["count"] == 1:
            raise NoDbAlreadyLockedError()
        original_update(sbs_map=sbs_map, metadata=metadata)

    monkeypatch.setattr(batch_runner, "apply_sbs_resource_update", flaky_grouped_update)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/batch/_/demo/upload-sbs-map",
            files={"sbs_map": ("map.tif", sbs_raster_bytes(tmp_path / "source.tif"))},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "SBS map uploaded successfully."
    assert payload["resource"]["relative_path"] == "resources/map.tif"
    assert payload["resource"]["resource_type"] == "sbs_map"
    assert grouped_call_count["count"] == 2
    assert clear_calls == [batch_runner.runid]


def test_upload_sbs_map_rejects_oversize_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_runner = DummyBatchRunner(tmp_path)

    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
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
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
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
    assert payload["error"]["message"] == "Only GeoTIFF or self-contained IMG rasters are supported."


def test_upload_geojson_load_error_redacts_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        upload_batch_runner_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"sub": "2", "roles": ["Admin"]},
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


@pytest.mark.parametrize("operation", ["sbs_map_sanity_check", "SoilBurnSeverityMap"])
def test_upload_sbs_native_failure_is_not_published(monkeypatch, tmp_path, operation):
    from tests.factories.raster import sbs_raster_bytes

    runner = DummyBatchRunner(tmp_path)
    monkeypatch.setattr(upload_batch_runner_routes, "require_jwt", lambda *args, **kwargs: {"sub": "2", "roles": ["Admin"]})
    monkeypatch.setattr(upload_batch_runner_routes, "_batch_runner_feature_enabled", lambda: True)
    monkeypatch.setattr(upload_batch_runner_routes.BatchRunner, "getInstanceFromBatchName", lambda name: runner)
    monkeypatch.setattr(upload_batch_runner_routes, "sbs_map_sanity_check", lambda path: (0, ""))
    def fail(path):
        raise RuntimeError("native unavailable")
    monkeypatch.setattr(upload_batch_runner_routes, operation, fail)
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/upload-sbs-map", files={"sbs_map": ("map.tif", sbs_raster_bytes(tmp_path / "source.tif"))}, headers={"Authorization": "Bearer token"})
    assert response.status_code == 500
    assert response.json()["error"]["message"] == "SBS raster processing failed."
    assert runner.sbs_grouped_update_calls == []
    assert not (tmp_path / "resources" / "map.tif").exists()


def test_invalid_geojson_replacement_preserves_existing_source(monkeypatch, tmp_path):
    import json
    batch = DummyBatchRunner(tmp_path)
    resources = Path(batch.resources_dir); resources.mkdir()
    source = resources / 'source.geojson'
    source.write_bytes(b'accepted-source-sentinel')
    monkeypatch.setattr(upload_batch_runner_routes, 'require_jwt', lambda *a, **k: {'sub':'2'})
    monkeypatch.setattr(upload_batch_runner_routes, 'require_feature_access', lambda *a: None)
    monkeypatch.setattr(upload_batch_runner_routes, '_batch_runner_feature_enabled', lambda: True)
    monkeypatch.setattr(upload_batch_runner_routes.BatchRunner, 'getInstanceFromBatchName', lambda name: batch)
    with TestClient(rq_engine.app) as client:
        url = '/api/batch/_/demo/upload-geojson'
        response = client.post(url, files={'geojson_file':('source.geojson', b'{}')})
        assert response.status_code == 400
        assert source.read_bytes() == b'accepted-source-sentinel'
        assert batch.geojson_state is None
        valid = {'type':'FeatureCollection', 'features':[{'type':'Feature','properties':{},
            'geometry':{'type':'Polygon','coordinates':[[[-116,45],[-115,45],[-115,46],[-116,45]]]}}]}
        raw = json.dumps(valid).encode()
        response = client.post(url, files={'geojson_file':('source.geojson', raw)})
        assert response.status_code == 200, response.text
        assert source.read_bytes() == raw
        assert batch.geojson_state['_geojson_filepath'] == str(source)


def test_session_human_is_used_for_batch_retention() -> None:
    actor = upload_batch_runner_routes._retention_actor({
        "token_class": "session",
        "feature_access_principal": {"version": 1, "kind": "human", "id": 79},
        "session_id": "not-persisted",
    })
    assert actor.receipt_value() == {"kind": "human", "user_id": 79}
