from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.roads_bp as roads_module
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
        self._attribute_field_map: Dict[str, Any] = dict(self._params["attribute_field_map"])
        self._attribute_catalog: Optional[Dict[str, Any]] = None
        self._uploaded_geojson_relpath: Optional[str] = None
        self._status = "idle"
        self._errors: list[str] = []
        self._prepare_summary: Optional[Dict[str, Any]] = None
        self._run_summary: Optional[Dict[str, Any]] = None
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
        self._params.update(payload)
        return dict(self._params)

    def set_uploaded_geojson(self, src_path: str) -> Dict[str, Any]:
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Roads input file not found: {src}")
        payload = json.loads(src.read_text(encoding="utf-8"))
        rel = "roads/roads.uploaded.geojson"
        dst = Path(self.wd) / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload), encoding="utf-8")
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
            "last_prepare_summary": self._prepare_summary,
            "last_run_summary": self._run_summary,
            "status": self._status,
            "errors": list(self._errors),
        }


@pytest.fixture()
def roads_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(roads_module.roads_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

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
        return path

    monkeypatch.setattr(roads_module, "url_for_run", _fake_url_for_run)

    RonStub = singleton_factory("RonStub", attrs={"mods": ["roads"]}, mixins=(LockedMixin,))
    monkeypatch.setattr(roads_module, "Ron", RonStub)

    conn_factory = rq_environment.redis_conn_factory(label="roads-redis")
    monkeypatch.setattr(roads_module.redis, "Redis", lambda **kwargs: conn_factory())
    monkeypatch.setattr(roads_module, "acquire_roads_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(roads_module, "release_roads_submit_lock", lambda _runid, _owner: None)
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

        def remove_timestamp(self, task) -> None:
            self.removed.append(task)

    monkeypatch.setattr(roads_module, "RedisPrep", RedisPrepStub)

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


def test_upload_geojson_rejects_json_path_mode(roads_client):
    client, *_rest = roads_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/upload_geojson",
        json={"path": "/tmp/roads.geojson"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "multipart `file`" in payload["error"]["message"]


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
    run_response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/roads/run")

    assert prepare_response.status_code == 200
    assert run_response.status_code == 200
    assert prepare_response.get_json()["job_id"] == "roads-job-1"
    assert run_response.get_json()["job_id"] == "roads-job-1"

    funcs = [call.func for call in rq_environment.recorder.queue_calls]
    assert funcs == [roads_module.run_roads_prepare_rq, roads_module.run_roads_rq]

    prep = RedisPrepStub.tryGetInstance(run_dir)
    assert prep.job_ids == [
        ("run_roads_prepare_rq", "roads-job-1"),
        ("run_roads_rq", "roads-job-1"),
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
    client, _RoadsStub, RonStub, *_rest = roads_client
    run_dir = _rest[-1]
    RonStub.getInstance(run_dir).mods = []

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
    assert any(link["href"].endswith("/gl-dashboard?output_scope=roads") for link in links)
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
    assert f"/runs/{RUN_ID}/{CONFIG}/gl-dashboard?output_scope=roads" in hrefs
    assert f"/runs/{RUN_ID}/{CONFIG}/storm-event-analyzer?output_scope=roads" in hrefs
