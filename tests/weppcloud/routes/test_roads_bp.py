from __future__ import annotations

import hashlib
import io
import logging
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.roads_bp as roads_module
from wepppy.rq import submission_recovery
from wepppy.weppcloud.utils import cap_guard
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


class RoadsStub(LockedMixin):
    _instances: Dict[str, "RoadsStub"] = {}

    def __init__(self, wd: str, cfg_fn: str) -> None:
        super().__init__()
        self.wd = wd
        self.cfg_fn = cfg_fn
        self._enabled = False
        self._params: Dict[str, Any] = {
            "tolerance_m": 0.5,
            "surface_default": "gravel",
            "traffic_default": "low",
            "attribute_field_map": {
                "design": None,
                "surface": None,
                "traffic": None,
            },
        }
        self._parameterization_state = None
        self._attribute_field_map: Dict[str, Any] = dict(self._params["attribute_field_map"])
        self._attribute_catalog: Optional[Dict[str, Any]] = None
        self._uploaded_geojson_relpath: Optional[str] = None
        self._status = "idle"
        self._errors: list[str] = []
        self._prepare_summary: Optional[Dict[str, Any]] = None
        self._run_summary: Optional[Dict[str, Any]] = None
        self._roads_segments_payload: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.0, 46.0], [-117.001, 46.001]]},
                    "properties": {
                        "segment_id": "roads-seg-000101",
                        "design": "inslope_bd",
                        "surface": "gravel",
                        "traffic": "low",
                    },
                }
            ],
        }
        self._segment_detail_payloads: Dict[str, Dict[str, Any]] = {
            "roads-seg-000101": {
                "segment_id": "roads-seg-000101",
                "design": "inslope_bd",
                "surface": "gravel",
                "traffic": "low",
                "soil_texture": "loam",
                "rfg_pct": 12.0,
                "road_width_m": 4.5,
                "segment_length_m": 210.0,
                "slope_pct_raw": 6.1,
                "slope_pct_clamped": 6.1,
                "routing_mode": "channel_associated",
                "execution_status": "completed",
            }
        }
        self._segments_not_prepared = False
        self._segment_missing_ids: set[str] = set()
        type(self)._instances[wd] = self

    @classmethod
    def getInstance(cls, wd: str) -> "RoadsStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd, "roads.cfg")
            cls._instances[wd] = instance
        return instance

    @classmethod
    def tryGetInstance(cls, wd: str) -> Optional["RoadsStub"]:
        return cls._instances.get(wd)

    @classmethod
    def initial_parameterization_preview(cls):
        return {"status": "unbound", "baseline_id": "preview", "overrides": {}, "groups": []}

    @classmethod
    def reset_instances(cls) -> None:
        cls._instances.clear()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def roads_upload_dir(self) -> str:
        path = Path(self.wd) / "roads"
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def set_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "attribute_field_map" in payload and isinstance(payload["attribute_field_map"], dict):
            self._attribute_field_map.update(payload["attribute_field_map"])
            self._params["attribute_field_map"] = dict(self._attribute_field_map)
        self._params.update({key: value for key, value in payload.items() if key != "parameterization"})
        if "parameterization" in payload:
            self._parameterization_state = {"status": "bound", "overrides": payload["parameterization"].get("overrides", {})}
        return dict(self._params)

    def set_uploaded_geojson(self, src_path: str, *, publication_commit=None) -> Dict[str, Any]:
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Roads input file not found: {src}")
        payload = json.loads(src.read_text(encoding="utf-8"))
        rel = "roads/roads.uploaded.geojson"
        dst = Path(self.wd) / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        field_names = sorted(
            {
                key
                for feature in payload.get("features", [])
                for key in (feature.get("properties") or {}).keys()
                if isinstance(key, str)
            }
        )
        self._attribute_catalog = {
            "field_names": field_names,
            "field_count": len(field_names),
            "total_feature_count": len(payload.get("features", [])),
            "profiled_feature_count": len(payload.get("features", [])),
            "profile_truncated": False,
            "field_profiles": [],
        }
        self._attribute_field_map = {
            "design": "DESIGN" if "DESIGN" in field_names else None,
            "surface": "SURFACE" if "SURFACE" in field_names else None,
            "traffic": "TRAFFIC" if "TRAFFIC" in field_names else None,
        }
        self._params["attribute_field_map"] = dict(self._attribute_field_map)
        self._uploaded_geojson_relpath = rel
        if publication_commit is not None:
            publication_commit()
        return {
            "uploaded_geojson_relpath": rel,
            "feature_count": len(payload.get("features", [])),
            "discovered_attribute_catalog": self._attribute_catalog,
            "attribute_field_map": dict(self._attribute_field_map),
        }

    def prepare_segments(self) -> Dict[str, Any]:
        self._status = "prepared"
        self._prepare_summary = {"prepared": True}
        return dict(self._prepare_summary)

    def run_roads_wepp(self) -> Dict[str, Any]:
        self._status = "completed"
        self._run_summary = {
            "status": "completed",
            "roads_log_relpath": "wepp/roads/roads.log",
            "roads_output_relpath": "wepp/roads/output",
            "segment_pass_manifest_relpath": "wepp/roads/segments/roads.segment.pass.manifest.json",
            "roads_report_resources": {
                "status": "ready",
                "required_relpaths": [
                    "wepp/roads/output/interchange/H.pass.parquet",
                    "wepp/roads/output/interchange/H.wat.parquet",
                    "wepp/roads/output/interchange/loss_pw0.out.parquet",
                    "wepp/roads/output/interchange/loss_pw0.hill.parquet",
                    "wepp/roads/output/interchange/loss_pw0.chn.parquet",
                    "wepp/roads/output/interchange/totalwatsed3.parquet",
                    "wepp/roads/output/interchange/ebe_pw0.parquet",
                    "wepp/roads/output/interchange/README.md",
                    "wepp/roads/output/interchange/roads_segment_loss_summary.parquet",
                ],
                "missing_relpaths": [],
                "roads_segment_loss_summary_relpath": "wepp/roads/output/interchange/roads_segment_loss_summary.parquet",
            },
        }
        return dict(self._run_summary)

    def query_status(self) -> Dict[str, Any]:
        return {"enabled": self._enabled, "status": self._status, "errors": list(self._errors)}

    def query_summary(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "roads_params": dict(self._params),
            "attribute_field_map": dict(self._attribute_field_map),
            "discovered_attribute_catalog": self._attribute_catalog,
            "uploaded_geojson_relpath": self._uploaded_geojson_relpath,
            "parameterization": self._parameterization_state,
            "last_prepare_summary": self._prepare_summary,
            "last_run_summary": self._run_summary,
            "status": self._status,
            "errors": list(self._errors),
        }

    def query_map_segments_geojson(self) -> Dict[str, Any]:
        if self._segments_not_prepared:
            raise FileNotFoundError("Prepared roads segments not found. Run prepare_segments first.")
        return self._roads_segments_payload

    def query_segment_detail(self, segment_id: str) -> Dict[str, Any]:
        segment_key = str(segment_id).strip()
        if not segment_key:
            raise ValueError("segment_id is required.")
        if self._segments_not_prepared:
            raise FileNotFoundError("Prepared roads segments not found. Run prepare_segments first.")
        if segment_key in self._segment_missing_ids:
            raise KeyError(f"Road segment {segment_key!r} was not found in prepared roads artifacts.")
        payload = self._segment_detail_payloads.get(segment_key)
        if payload is None:
            raise KeyError(f"Road segment {segment_key!r} was not found in prepared roads artifacts.")
        return dict(payload)


@pytest.fixture()
def roads_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "roads-route-test")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(roads_module.roads_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path / "lifecycle"))

    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(roads_module, "load_run_context", lambda runid, cfg: context)
    monkeypatch.setattr(roads_module, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(roads_module, "Roads", RoadsStub)

    def _fake_url_for_run(endpoint: str, **values: Any) -> str:
        runid = values.get("runid", RUN_ID)
        config = values.get("config", CONFIG)
        scope = values.get("output_scope")
        suffixes = {
            "wepp.report_wepp_loss": "report/wepp/summary",
            "wepp.report_wepp_return_periods": "report/wepp/return_periods",
            "wepp.report_wepp_yearly_watbal": "report/wepp/yearly_watbal",
            "wepp.report_wepp_avg_annual_watbal": "report/wepp/avg_annual_watbal",
            "wepp.plot_wepp_streamflow": "plot/wepp/streamflow",
            "gl_dashboard.gl_dashboard": "gl-dashboard",
            "storm_event_analyzer.storm_event_analyzer": "storm-event-analyzer",
            "download.download_with_subpath": "download",
        }
        if endpoint == "browse.browse_tree":
            subpath = str(values.get("subpath", "")).lstrip("/")
            return f"/runs/{runid}/{config}/browse/{subpath}"
        if endpoint == "download.download_with_subpath":
            subpath = str(values.get("subpath", "")).lstrip("/")
            return f"/runs/{runid}/{config}/download/{subpath}"
        suffix = suffixes.get(endpoint, endpoint)
        path = f"/runs/{runid}/{config}/{suffix}"
        if scope:
            path = f"{path}?output_scope={scope}"
        if values.get("roads"):
            path += "&roads=" + values["roads"]
        return path

    monkeypatch.setattr(roads_module, "url_for_run", _fake_url_for_run)

    RonStub = singleton_factory("RonStub", attrs={"mods": ["roads"], "logger": logging.getLogger("test.roads.ron")}, mixins=(LockedMixin,))
    monkeypatch.setattr(roads_module, "Ron", RonStub)

    conn_factory = rq_environment.redis_conn_factory(label="roads-redis")
    monkeypatch.setattr(roads_module.redis, "Redis", lambda **kwargs: conn_factory())
    monkeypatch.setattr(roads_module, "ensure_no_active_roads_job", lambda _runid, _prep, _redis_conn: None)

    queue_class = rq_environment.queue_class(default_job_id="roads-job-1")
    monkeypatch.setattr(roads_module, "Queue", queue_class)

    class RedisPrepStub:
        _instances: Dict[str, "RedisPrepStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.job_ids: list[tuple[str, str]] = []
            self.removed: list[object] = []

        @classmethod
        def getInstance(cls, wd: str) -> "RedisPrepStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @classmethod
        def tryGetInstance(cls, wd: str) -> "RedisPrepStub":
            return cls.getInstance(wd)

        @classmethod
        def reset_instances(cls) -> None:
            cls._instances.clear()

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.job_ids.append((key, job_id))

        def get_rq_job_id(self, key: str) -> str | None:
            return next(
                (job_id for saved_key, job_id in reversed(self.job_ids) if saved_key == key),
                None,
            )

        def remove_timestamp(self, task) -> None:
            self.removed.append(task)

    monkeypatch.setattr(roads_module, "RedisPrep", RedisPrepStub)

    class Reservation:
        reservation_id = "roads-test-reservation"

        def commit(self, _exact_bytes: int) -> None:
            return None

        def release_prewrite(self) -> None:
            return None

    class Ledger:
        def reserve(self, **_kwargs):
            return Reservation()

    class Lease:
        def __init__(self) -> None:
            self.owned = True

        def assert_owned(self) -> None:
            assert self.owned

        def release(self) -> None:
            self.owned = False

    real_prepare = roads_module.prepare_vector_upload
    monkeypatch.setattr(
        roads_module,
        "prepare_vector_upload",
        lambda **kwargs: real_prepare(
            **kwargs,
            ledger=Ledger(),
            scope_lease_factory=lambda _key: Lease(),
        ),
    )
    RoadsStub.getInstance(str(run_dir)).set_enabled(True)

    with app.test_client() as client:
        yield client, RoadsStub, RonStub, RedisPrepStub, rq_environment, str(run_dir)

    RoadsStub.reset_instances()
    RonStub.reset_instances()
    RedisPrepStub.reset_instances()
    rq_environment.recorder.reset()


def test_upload_geojson_multipart_file(roads_client):
    client, RoadsStub, _RonStub, RedisPrepStub, _rq_environment, run_dir = roads_client
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                    "properties": {},
                }
            ],
        }
    ).encode("utf-8")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(payload), "roads.geojson")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["feature_count"] == 1
    controller = RoadsStub.getInstance(run_dir)
    assert controller.query_summary()["uploaded_geojson_relpath"] == "roads/roads.uploaded.geojson"
    prep = RedisPrepStub.tryGetInstance(run_dir)
    assert prep.removed == [roads_module.TaskEnum.run_roads]


def test_upload_geoparquet_retains_source_and_publishes_wgs84_candidate(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, _RedisPrepStub, _rq_environment, run_dir = roads_client
    source = b"PAR1roads-controlPAR1"
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-117.0, 46.0], [-117.1, 46.1]]},
                "properties": {"name": "control"},
            }
        ],
    }
    canonical = json.dumps(geojson, separators=(",", ":")).encode()

    class Response:
        status_code = 200
        headers = {}

        def iter_content(self, **_kwargs):
            yield json.dumps({
                "request_id": "roads-converter-request",
                "geojson": geojson,
                "metadata": {
                    "source_size": len(source),
                    "source_sha256": hashlib.sha256(source).hexdigest(),
                    "canonical_size": len(canonical),
                    "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
                    "parser_provenance": {
                        "binary_name": "geoparquet_parser_cli",
                        "binary_version": "geoparquet_parser_cli 0.0.0",
                        "binary_sha256": "1" * 64,
                        "cargo_lock_sha256": "2" * 64,
                        "source_revision": "3" * 40,
                    },
                },
            }).encode()

        def close(self):
            pass

    monkeypatch.setattr(
        "wepppy.microservices.vector_upload_normalization.requests.post",
        lambda *_args, **_kwargs: Response(),
    )
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "http://shape-converter.test/convert")
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(source), "roads.parquet")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    accepted = json.loads((Path(run_dir) / "roads" / "roads.uploaded.geojson").read_text())
    assert accepted["crs"]["properties"]["name"] == "EPSG:4326"
    attempt = next((Path(run_dir) / "roads" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert receipt["status"] == "accepted"
    assert receipt["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert next((attempt / "original").iterdir()).read_bytes() == source
    assert RoadsStub.getInstance(run_dir).query_summary()["uploaded_geojson_relpath"] == "roads/roads.uploaded.geojson"


def test_exact_converter_formats_cross_roads_http_boundary(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    fixture_root_value = os.getenv("VECTOR_UPLOAD_INTEGRATION_FIXTURES")
    if not converter_url or not fixture_root_value:
        pytest.skip("exact converter integration environment is not configured")
    client, _RoadsStub, _RonStub, _RedisPrepStub, _rq_environment, run_dir = roads_client
    monkeypatch.setenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", converter_url)
    fixture_root = Path(fixture_root_value)
    semantics: list[dict[str, Any]] = []
    for suffix, fixture_suffix in (("geojson", "geojson"), ("zip", "zip"), ("parquet", "parquet"), ("geoparquet", "parquet")):
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
            data={"file": (io.BytesIO((fixture_root / f"line.{fixture_suffix}").read_bytes()), f"line.{suffix}")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        payload = json.loads((Path(run_dir) / "roads" / "roads.uploaded.geojson").read_text())
        semantics.append({"geometry": payload["features"][0]["geometry"], "properties": payload["features"][0]["properties"]})
    assert semantics[1:] == semantics[:1] * 3


def test_upload_geometry_rejection_preserves_accepted_roads(roads_client):
    client, RoadsStub, _RonStub, _RedisPrepStub, _rq_environment, run_dir = roads_client
    accepted_payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                    "properties": {"name": "accepted"},
                }
            ],
        }
    ).encode()
    accepted_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(accepted_payload), "roads.geojson")},
        content_type="multipart/form-data",
    )
    canonical_path = Path(run_dir) / "roads" / "roads.uploaded.geojson"
    accepted_bytes = canonical_path.read_bytes()

    rejected_payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"name": "rejected"},
                }
            ],
        }
    ).encode()
    rejected_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(rejected_payload), "roads.json")},
        content_type="multipart/form-data",
    )

    assert accepted_response.status_code == 200
    assert rejected_response.status_code == 400
    assert rejected_response.get_json()["error"]["code"] == "invalid_vector"
    assert canonical_path.read_bytes() == accepted_bytes
    assert RoadsStub.getInstance(run_dir).query_summary()["uploaded_geojson_relpath"] == "roads/roads.uploaded.geojson"
    receipts = [
        json.loads(path.read_text())
        for path in (Path(run_dir) / "roads" / "vector_upload_attempts").glob("*/normalization.json")
    ]
    assert sorted(receipt["status"] for receipt in receipts) == ["accepted", "rejected"]


def test_upload_geojson_rejects_json_path_mode(roads_client):
    client, *_rest = roads_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        json={"path": "/tmp/roads.geojson"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "multipart `file`" in payload["error"]["message"]
    assert payload["error"]["details"] == payload["error"]["message"]
    assert payload["error"]["code"] == "missing_upload_file"
    assert payload["error_id"]


def test_upload_geojson_rejects_invalid_extension(roads_client):
    client, *_rest = roads_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(b"{}"), "roads.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "GeoJSON, Shapefile ZIP, or GeoParquet" in payload["error"]["message"]
    assert payload["error"]["details"] == payload["error"]["message"]
    assert payload["error"]["code"] == "unsupported_vector"
    assert payload["error_id"]


def test_upload_geojson_rejects_oversize_payload(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, *_rest = roads_client
    monkeypatch.setattr(roads_module, "ROADS_UPLOAD_GEOJSON_MAX_BYTES", 4)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(b"abcdef"), "roads.geojson")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    payload = response.get_json()
    assert "endpoint size limit" in payload["error"]["message"]
    assert payload["error"]["details"] == payload["error"]["message"]
    assert payload["error"]["code"] == "vector_limit_exceeded"
    assert payload["error_id"]


def test_upload_geojson_server_fault_logs_error_id_correlation(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    client, *_rest = roads_client

    def _raise_os_error(*_args, **_kwargs):
        raise OSError("filesystem quota exceeded")

    monkeypatch.setattr(roads_module, "prepare_vector_upload", _raise_os_error)
    caplog.set_level("ERROR", logger="wepppy.weppcloud.utils.helpers")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(b"{}"), "roads.geojson")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Failed to persist Roads upload."
    assert payload["error"]["details"] == "filesystem quota exceeded"
    assert payload["error"]["code"] == "internal_error"
    assert payload["error_id"]

    correlated_records = [
        record
        for record in caplog.records
        if getattr(record, "error_id", None) == payload["error_id"]
    ]
    assert correlated_records
    assert any("OSError: filesystem quota exceeded" in record.getMessage() for record in correlated_records)


def test_set_params_updates_controller_state(roads_client):
    client, RoadsStub, _RonStub, RedisPrepStub, *_rest = roads_client
    run_dir = _rest[-1]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params",
        json={"tolerance_m": 0.25, "soil_texture_default": "loam"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["roads_params"]["tolerance_m"] == 0.25
    assert RoadsStub.getInstance(run_dir).query_summary()["roads_params"]["soil_texture_default"] == "loam"
    prep = RedisPrepStub.tryGetInstance(run_dir)
    assert prep.removed == [roads_module.TaskEnum.run_roads]


def test_roads_config_exposes_attribute_catalog_and_mapping(roads_client):
    client, _RoadsStub, _RonStub, _RedisPrepStub, _rq_environment, _run_dir = roads_client
    payload = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                    "properties": {"DESIGN": "Inslope_bd", "SURFACE": "gravel", "TRAFFIC": "low"},
                }
            ],
        }
    ).encode("utf-8")
    upload_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        data={"file": (io.BytesIO(payload), "roads.geojson")},
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 200

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/roads/config")
    assert response.status_code == 200
    body = response.get_json()
    assert body["discovered_attribute_catalog"]["field_count"] == 3
    assert body["attribute_field_map"]["design"] == "DESIGN"


def test_set_params_returns_mapping_state(roads_client):
    client, _RoadsStub, _RonStub, _RedisPrepStub, _rq_environment, _run_dir = roads_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params",
        json={
            "attribute_field_map": {"surface": "SURF_A"},
            "surface_default": "paved",
            "traffic_default": "none",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["attribute_field_map"]["surface"] == "SURF_A"
    assert payload["Content"]["roads_params"]["surface_default"] == "paved"
    assert payload["Content"]["roads_params"]["traffic_default"] == "none"


def test_prepare_and_run_enqueue_jobs(roads_client):
    client, _RoadsStub, _RonStub, RedisPrepStub, rq_environment, run_dir = roads_client

    prepare_response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/prepare_segments")
    prep = RedisPrepStub.tryGetInstance(run_dir)
    prepare_receipts = list(prep.job_ids)
    prep.job_ids.clear()
    run_response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/run")

    assert prepare_response.status_code == 200
    assert run_response.status_code == 200
    prepare_job_id = prepare_response.get_json()["job_id"]
    run_job_id = run_response.get_json()["job_id"]

    funcs = [call.func for call in rq_environment.recorder.queue_calls]
    assert funcs == [roads_module.run_roads_prepare_rq, roads_module.run_roads_rq]

    assert prepare_receipts == [("run_roads_prepare_rq", prepare_job_id)]
    assert prep.job_ids == [
        ("run_roads_rq", run_job_id),
    ]


def test_prepare_segments_returns_409_when_roads_job_active(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, *_ = roads_client
    monkeypatch.setattr(
        roads_module,
        "ensure_no_active_roads_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            roads_module.RoadsSingleFlightConflict("Roads job already active for this run.")
        ),
    )

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/prepare_segments")

    assert response.status_code == 409
    payload = response.get_json()
    assert "already active" in payload["error"]["message"]


def test_roads_routes_require_mod_enabled(roads_client):
    client, RoadsStub, RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    RonStub.getInstance(run_dir).mods = []
    RoadsStub.getInstance(run_dir).set_enabled(False)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params",
        json={"tolerance_m": 0.25},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "not enabled" in payload["error"]["message"]


def test_report_roads_summary_includes_scoped_links_and_segment_exports(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller.run_roads_wepp()
    from tests.roads_lifecycle_fixtures import write_current_roads_fixture
    write_current_roads_fixture(run_dir)

    captured: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(roads_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/summary")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "reports/roads/summary.htm"
    kwargs = captured["kwargs"]
    links = kwargs["roads_report_links"]
    assert any(link["href"].endswith("/report/wepp/summary?output_scope=roads") for link in links)
    assert any(link["href"].endswith("/report/wepp/return_periods?output_scope=roads") for link in links)
    assert any(link["href"].endswith("/storm-event-analyzer?output_scope=roads") for link in links)
    assert any(
        link["href"].endswith("/browse/wepp/roads/output/interchange/roads_segment_loss_summary.parquet")
        for link in links
    )
    assert any(
        link["href"].endswith("/download/wepp/roads/output/interchange/roads_segment_loss_summary.parquet?as_csv=1")
        for link in links
    )
    resource_links = kwargs["roads_resource_links"]
    assert any(item["relpath"] == "wepp/roads/output/interchange/H.pass.parquet" for item in resource_links)
    assert any(item["href"].endswith("/browse/wepp/roads/output/interchange/README.md") for item in resource_links)


def test_report_roads_results_renders_run_results_panel(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller.run_roads_wepp()
    from tests.roads_lifecycle_fixtures import write_current_roads_fixture
    write_current_roads_fixture(run_dir)

    captured: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(roads_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/results")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "controls/roads_reports.htm"
    kwargs = captured["kwargs"]
    assert kwargs["run_results_title"] == "Run Results"
    links = kwargs["roads_report_links"]
    assert any(link["href"].endswith("/report/wepp/summary?output_scope=roads") for link in links)
    assert any(link["href"].endswith("/report/wepp/yearly_watbal?output_scope=roads") for link in links)
    assert any(link["href"].endswith("/gl-dashboard?output_scope=roads&roads=on") for link in links)
    assert any(
        link["href"].endswith("/download/wepp/roads/output/interchange/roads_segment_loss_summary.parquet?as_csv=1")
        for link in links
    )
    resource_links = kwargs["roads_resource_links"]
    assert any(item["relpath"] == "wepp/roads/output/interchange/README.md" for item in resource_links)
    assert any(item["href"].endswith("/browse/wepp/roads/output/interchange/H.pass.parquet") for item in resource_links)


def test_report_roads_results_hides_non_single_storm_links_when_resources_absent(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller._status = "completed"
    controller._run_summary = {
        "status": "completed",
        "roads_report_resources": {
            "status": "ready",
            "required_relpaths": [
                "wepp/roads/output/interchange/H.pass.parquet",
                "wepp/roads/output/interchange/ebe_pw0.parquet",
                "wepp/roads/output/interchange/README.md",
            ],
            "missing_relpaths": [],
            "roads_segment_loss_summary_relpath": None,
        },
    }

    captured: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(roads_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/results")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "controls/roads_reports.htm"
    links = captured["kwargs"]["roads_report_links"]
    hrefs = {link["href"] for link in links}
    assert f"/runs/{RUN_ID}/{CONFIG}/report/wepp/summary?output_scope=roads" not in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/report/wepp/return_periods?output_scope=roads" not in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/report/wepp/yearly_watbal?output_scope=roads" not in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/report/wepp/avg_annual_watbal?output_scope=roads" not in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/plot/wepp/streamflow?output_scope=roads" not in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/gl-dashboard?output_scope=roads&roads=on" in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/storm-event-analyzer?output_scope=roads" in hrefs


def test_resources_roads_geojson_returns_feature_collection(roads_client):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["properties"]["segment_id"] == "roads-seg-000101"


def test_resources_roads_geojson_returns_404_when_prepare_missing(roads_client):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller._segments_not_prepared = True

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json")

    assert response.status_code == 404
    payload = response.get_json()
    assert "prepare_segments" in payload["error"]["message"]


def test_query_roads_segment_detail_returns_payload(roads_client):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/roads/segment/roads-seg-000101")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["segment_id"] == "roads-seg-000101"
    assert payload["design"] == "inslope_bd"
    assert payload["surface"] == "gravel"
    assert payload["traffic"] == "low"


def test_query_roads_segment_detail_returns_404_when_missing(roads_client):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller._segment_missing_ids.add("roads-seg-009999")

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/roads/segment/roads-seg-009999")

    assert response.status_code == 404
    payload = response.get_json()
    assert "was not found" in payload["error"]["message"]


def test_report_roads_segment_summary_renders_template(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)

    captured: Dict[str, Any] = {}

    def _fake_render(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(roads_module, "render_template", _fake_render)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/segment_summary/roads-seg-000101")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "reports/roads/segment_summary.htm"
    assert captured["kwargs"]["d"]["segment_id"] == "roads-seg-000101"
    assert captured["kwargs"]["d"]["routing_mode"] == "channel_associated"


def test_report_roads_segment_summary_requires_cap_for_anonymous_users(
    roads_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)

    captured: Dict[str, Any] = {}

    monkeypatch.setattr(cap_guard, "current_user", SimpleNamespace(is_authenticated=False), raising=False)

    def _fake_cap_gate_response(next_url=None, reason=None):
        captured["next_url"] = next_url
        captured["reason"] = reason
        return "cap-gate"

    monkeypatch.setattr(cap_guard, "cap_gate_response", _fake_cap_gate_response)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/segment_summary/roads-seg-000101")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "cap-gate"
    assert captured["reason"] == "Complete verification to view WEPP reports."
    assert "next_url" in captured


def test_report_roads_segment_summary_returns_404_when_missing(roads_client):
    client, RoadsStub, _RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    controller._segment_missing_ids.add("roads-seg-000404")

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/roads/segment_summary/roads-seg-000404")

    assert response.status_code == 404
    payload = response.get_json()
    assert "was not found" in payload["error"]["message"]


def test_detachment_view_reads_real_artifacts_and_rejects_malformed_crs(roads_client):
    from tests.nodb.mods.test_roads_detachment_view import sources
    client, *_rest = roads_client
    root = Path(_rest[-1])
    folder = sources(root)
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json?view=detachment")
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.json['features'][0]['properties']['roads_detachment']['rate_t_ha_year'] == 2.75
    path = folder / 'roads.inslope.monotonic.geojson'
    data = json.loads(path.read_text())
    data['crs'] = {'type': 'name', 'properties': []}
    path.write_text(json.dumps(data))
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json?view=detachment")
    assert response.status_code == 422
    assert str(root) not in response.get_data(as_text=True)
    assert 'Traceback' not in response.get_data(as_text=True)


def test_detachment_view_absence_and_unknown_view(roads_client):
    client, *_ = roads_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json?view=detachment")
    assert response.status_code == 409
    assert response.headers['Cache-Control'] == 'no-store'
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json?view=unknown")
    assert response.status_code == 400


def test_detachment_authorization_precedes_view_and_artifact_access(roads_client):
    client, *_ = roads_client
    # Exercise the real authorization boundary with no login manager, outside
    # TESTING's explicit public-fixture bypass; no materializer stub is involved.
    client.application.config['TESTING'] = False
    client.application.register_error_handler(403, lambda exc: ('Forbidden', 403))
    for view in ('detachment', 'unknown'):
        response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/roads.json?view={view}")
        assert response.status_code == 403
        assert response.headers['Cache-Control'] == 'no-store'


def test_malformed_payload_route_matrix(roads_client, tmp_path):
    from tests.factories.request_payload import assert_malformed_routes
    assert_malformed_routes(roads_client[0], RUN_ID, CONFIG, tmp_path)


def test_parameterization_view_and_query_do_not_initialize_absent_roads(roads_client, monkeypatch):
    client, RoadsStub, RonStub, _prep, _rq, run_dir = roads_client
    RoadsStub._instances.pop(run_dir)
    contexts = []
    monkeypatch.setattr(roads_module, 'render_template', lambda template, **context: contexts.append(context) or 'view')
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/roads/parameterization')
    assert response.status_code == 200
    assert RoadsStub.tryGetInstance(run_dir) is None
    assert contexts[-1]['parameterization_state']['controller_present'] is False
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/query/roads/summary')
    assert response.status_code == 200
    assert response.json['parameterization']['status'] == 'unbound'
    assert RoadsStub.tryGetInstance(run_dir) is None
    RonStub.getInstance(run_dir).mods = []
    client.get(f'/runs/{RUN_ID}/{CONFIG}/roads/parameterization')
    assert contexts[-1]['parameterization_state']['enabled'] is False
    assert contexts[-1]['parameterization_state']['parameterization'] is None


def test_parameterization_save_returns_authoritative_query(roads_client, monkeypatch):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    controller = RoadsStub.getInstance(run_dir)
    original = controller.query_summary
    parameterization = {'status': 'bound', 'baseline_id': 'server-baseline', 'overrides': {}}
    monkeypatch.setattr(controller, 'query_summary', lambda: dict(original(), parameterization=parameterization))
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json={'parameterization': {'overrides': {}}})
    assert response.status_code == 200
    assert response.json['Content']['parameterization'] == parameterization


def test_parameterization_readonly_save_does_not_initialize(roads_client):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    RoadsStub._instances.pop(run_dir)
    Path(run_dir, 'READONLY').touch()
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json={'parameterization': {'overrides': {}}})
    assert response.status_code == 403
    assert RoadsStub.tryGetInstance(run_dir) is None


def test_parameterization_actual_template_fields_and_safe_seed(roads_client, monkeypatch):
    from jinja2 import FileSystemLoader

    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    templates = Path(roads_module.__file__).resolve().parents[2] / 'templates'
    client.application.jinja_loader = FileSystemLoader(str(templates))
    client.application.jinja_env.globals.update(
        static_url=lambda name: '/static/' + name,
        url_for=lambda *args, **kwargs: '/',
        url_for_run=lambda endpoint, **kwargs: '/runs/test/cfg/' + endpoint,
    )
    controller = RoadsStub.getInstance(run_dir)
    original = controller.query_summary
    monkeypatch.setattr(controller, 'query_summary', lambda: dict(original(), parameterization={
        'status': 'invalid', 'diagnostics': ['</script><script>alert(1)</script>'],
    }))
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/roads/parameterization')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('data-rp-row data-role=') == 12
    assert html.count('data-rp-mode disabled') == 12
    assert html.count('data-rp-value type="number"') == 12
    assert 'data-rp-leave-action="save"' in html
    assert 'data-rp-leave-action="discard"' in html
    assert 'data-rp-leave-action="stay"' in html
    assert '</script><script>alert(1)</script>' not in html
    assert r'\u003c/script\u003e' in html
    assert 'controllers-gl.js' in html


def test_parameterization_invalid_first_save_does_not_create_controller(roads_client, monkeypatch):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    RoadsStub._instances.pop(run_dir)
    def reject_initial(*args, **kwargs):
        raise ValueError('parameterization overrides must contain all roles')
    monkeypatch.setattr(RoadsStub, 'validate_initial_params', reject_initial, raising=False)
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json={'parameterization': {'overrides': {}}})
    assert 'error' in response.json
    assert RoadsStub.tryGetInstance(run_dir) is None


def test_parameterization_save_does_not_enable_existing_disabled_controller(roads_client):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(False)
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json={'parameterization': {'overrides': {}}})
    assert 'error' in response.json
    assert controller.enabled is False


def test_parameterization_valid_first_save_validates_before_initialization(roads_client, monkeypatch):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    RoadsStub._instances.pop(run_dir)
    calls = []
    def validate_initial(payload):
        assert RoadsStub.tryGetInstance(run_dir) is None
        calls.append(payload)
    monkeypatch.setattr(RoadsStub, 'validate_initial_params', validate_initial, raising=False)
    payload = {'parameterization': {'overrides': {'road': {}}}}
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json=payload)
    assert response.status_code == 200
    assert calls == [payload]
    assert RoadsStub.tryGetInstance(run_dir).enabled is True


def test_parameterization_config_alias_uses_same_preflight(roads_client, monkeypatch):
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    RoadsStub._instances.pop(run_dir)
    def reject_initial(payload):
        raise ValueError('invalid nested parameterization')
    monkeypatch.setattr(RoadsStub, 'validate_initial_params', reject_initial, raising=False)
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/api/roads/config', json={'parameterization': {}})
    assert 'invalid nested' in response.json['error']['message']
    assert RoadsStub.tryGetInstance(run_dir) is None


def test_parameterization_response_preserves_ordinary_params_roundtrip(roads_client):
    client, _roads, _ron, _prep, _rq, _run_dir = roads_client
    custom = {'road': {'ki_kg_s_m4': {'mode': 'multiply', 'value': 2}}}
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json={'parameterization': {'overrides': custom}})
    content = response.json['Content']
    assert 'parameterization' not in content['roads_params']
    assert content['parameterization']['overrides'] == custom
    response = client.post(f'/runs/{RUN_ID}/{CONFIG}/tasks/roads/set_params', json=content['roads_params'])
    assert response.json['Content']['parameterization']['overrides'] == custom
    assert 'parameterization' not in response.json['Content']['roads_params']


def test_parameterization_busy_get_renders_shell_without_scientific_admission(roads_client, monkeypatch):
    from wepppy.wepp.interchange import _roads_lifecycle
    client, RoadsStub, _ron, _prep, _rq, run_dir = roads_client
    from jinja2 import FileSystemLoader
    templates = Path(roads_module.__file__).resolve().parents[2] / 'templates'
    client.application.jinja_loader = FileSystemLoader(str(templates))
    client.application.jinja_env.globals.update(
        static_url=lambda name: '/static/' + name,
        url_for=lambda *args, **kwargs: '/',
        url_for_run=lambda endpoint, **kwargs: '/runs/test/cfg/' + endpoint,
    )
    controller = RoadsStub.getInstance(run_dir)
    controller.set_enabled(True)
    def busy_summary():
        raise _roads_lifecycle.RoadsResultsUnavailable('Roads is busy')
    monkeypatch.setattr(controller, 'query_summary', busy_summary)
    response = client.get(f'/runs/{RUN_ID}/{CONFIG}/roads/parameterization')
    assert response.status_code == 200
    assert 'text/html' in response.content_type
    assert 'data-parameterization-seed' in response.text
    assert '"busy": true' in response.text
    assert '"parameterization": null' in response.text


@pytest.fixture
def osm_access(monkeypatch):
    from wepppy.weppcloud.utils import feature_access_flask as admission
    from wepppy.weppcloud.utils.feature_access import FeatureResourceContext, VerifiedPrincipal

    monkeypatch.setattr(admission, "resource_context", lambda *args, **kwargs: FeatureResourceContext(
        existing_access_allowed=True, backend="wbt", enabled_features=frozenset({"roads"})))

    def select_role(role):
        principal = VerifiedPrincipal(kind="human", user_id=1, roles=frozenset({role}))
        monkeypatch.setattr(admission, "current_principal", lambda: principal)
    return select_role


def test_osm_download_edit_then_upload(roads_client, tmp_path, monkeypatch, osm_access):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    from wepppy.nodb.mods.roads.roads import Roads as RealRoads
    from urllib.parse import parse_qs

    client, _, ron_cls, _, _, wd = roads_client
    ron_cls.getInstance(wd).extent = [-117, 46, -116.9, 46.1]
    config = "disturbed9002-wbt-mofe"
    ron_cls.getInstance(wd).config_stem = config
    osm_access("PowerUser")
    tags = {"highway": "track", "surface": "dirt", "access": "private",
            "ref:USFS": "44", "DESIGN": "source value"}
    way = {"type": "way", "id": 56, "tags": tags, "geometry": [
        {"lon": -117.1, "lat": 46.05}, {"lon": -116.95, "lat": 46.05}]}
    queries = []

    class Interpreter(BaseHTTPRequestHandler):
        def do_POST(self):
            queries.append(parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())["data"][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"elements": [way]}).encode())

    with HTTPServer(("127.0.0.1", 0), Interpreter) as server:
        monkeypatch.setenv("WEPPPY_OSM_ROADS_OVERPASS_BASE_URL", f"http://127.0.0.1:{server.server_port}/")
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = client.post(f"/runs/{RUN_ID}/{config}/api/roads/osm.geojson")
        finally:
            server.shutdown()
            thread.join()
    assert response.status_code == 200
    assert response.mimetype == "application/geo+json"
    assert response.headers["Content-Disposition"].endswith('filename="osm-roads.geojson"')
    assert len(queries) == 1 and "service" in queries[0] and "out geom;" in queries[0]
    assert "(46,-117,46.1,-116.9)" in queries[0]
    assert not (Path(wd) / "roads.nodb").exists()
    data = response.get_json()
    feature, = data["features"]
    assert feature["geometry"]["coordinates"][0] == [-117, 46.05]
    props = feature["properties"]
    assert json.loads(props["osm_tags"]) == tags
    assert (props["DESIGN"], props["SURFACE"], props["TRAFFIC"]) == (None, "gravel", None)
    props.update(DESIGN="Inslope_bd", SURFACE="paved", TRAFFIC="low")
    edited = tmp_path / "edited.geojson"
    edited.write_text(json.dumps(data))
    from wepppy.nodb.core import Watershed
    (Path(wd) / "dem").mkdir()
    Watershed(wd, f"{config}.cfg")
    monkeypatch.setattr(roads_module, "Roads", RealRoads)
    uploaded = client.post(f"/runs/{RUN_ID}/{config}/tasks/roads/upload_geojson", data={
        "file": (io.BytesIO(edited.read_bytes()), "edited.geojson")})
    assert uploaded.status_code == 200, uploaded.get_json()
    summary = RealRoads.load_detached(wd).query_inputs()
    staged_bytes = (Path(wd) / summary["uploaded_geojson_relpath"]).read_bytes()
    staged = json.loads(staged_bytes)
    assert staged["features"][0]["properties"] == props
    assert summary["attribute_field_map"] == {"design": "DESIGN", "surface": "SURFACE", "traffic": "TRAFFIC"}

    # An empty download on a project with an edited upload preserves the active input.
    from wepppy.topo.osm_roads.overpass import OverpassClient
    monkeypatch.setattr(OverpassClient, "fetch_download_ways", lambda self, extent, *, process: process([]))
    repeat = client.post(f"/runs/{RUN_ID}/{config}/api/roads/osm.geojson")
    assert repeat.status_code == 200 and repeat.get_json()["features"] == []
    persisted = RealRoads.load_detached(wd).query_inputs()
    assert (Path(wd) / persisted["uploaded_geojson_relpath"]).read_bytes() == staged_bytes


def test_osm_download_denial_and_absent_extent(roads_client, osm_access):
    client, _, ron_cls, _, _, wd = roads_client
    url = f"/runs/{RUN_ID}/{CONFIG}/api/roads/osm.geojson"
    osm_access("User")
    assert client.post(url).status_code == 403
    assert client.get(url).status_code == 405
    osm_access("PowerUser")
    ron = ron_cls.getInstance(wd)
    ron.extent = None
    assert client.post(url).status_code == 422
    ron.mods = []
    assert client.post(url).status_code == 403


@pytest.mark.parametrize(("statuses", "remark", "retry_after", "expected_status", "expected_code"), [
    ([502, 200], None, None, 200, None),
    ([502, 502], None, None, 503, "upstream_http_error"),
    ([200], "runtime error: Query timed out", None, 504, "upstream_timeout"),
    ([429], None, "90", 503, "upstream_http_error"),
    ([400], None, None, 503, "upstream_http_error"),
    ([502, 200], "malformed-way", None, 502, "upstream_invalid_response"),
])
def test_download_retry_and_failure_evidence(
    roads_client, osm_access, monkeypatch, statuses, remark, retry_after, expected_status, expected_code
):
    import json
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    client, _, ron_cls, _, _, wd = roads_client
    ron_cls.getInstance(wd).extent = [-117, 46, -116.9, 46.1]
    osm_access("PowerUser")
    times = []

    class Interpreter(BaseHTTPRequestHandler):
        def do_POST(self):
            status = statuses[len(times)]
            times.append(time.monotonic())
            self.send_response(status)
            if retry_after:
                self.send_header("Retry-After", retry_after)
            self.end_headers()
            payload = {"elements": [{}]} if remark == "malformed-way" else {"elements": [], "remark": remark}
            self.wfile.write(json.dumps(payload).encode())

    with HTTPServer(("127.0.0.1", 0), Interpreter) as upstream:
        monkeypatch.setenv("WEPPPY_OSM_ROADS_OVERPASS_BASE_URL", f"http://127.0.0.1:{upstream.server_port}/")
        thread = Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        try:
            response = client.post(f"/runs/{RUN_ID}/{CONFIG}/api/roads/osm.geojson")
        finally:
            upstream.shutdown()
            thread.join()
    assert len(times) == len(statuses)
    if len(times) == 2:
        assert 4 <= times[1] - times[0] < 10
    assert response.status_code == expected_status
    if expected_code:
        error = response.json["error"]
        assert response.json["error_id"]
        assert error["code"] == expected_code
        assert error["details"]["retryable"] is (statuses[-1] in (429, 502) or expected_code == "upstream_timeout")
        assert error["details"]["attempts"] == len(times)
        assert error["details"]["upstream_status"] == statuses[-1]
        if retry_after:
            assert error["details"]["retry_after_seconds"] == 90
    else:
        assert response.json["type"] == "FeatureCollection"
