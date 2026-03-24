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
        self._params: Dict[str, Any] = {"tolerance_m": 0.5}
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
        self._uploaded_geojson_relpath = rel
        return {"uploaded_geojson_relpath": rel, "feature_count": len(payload.get("features", []))}

    def prepare_segments(self) -> Dict[str, Any]:
        self._status = "prepared"
        self._prepare_summary = {"prepared": True}
        return dict(self._prepare_summary)

    def run_roads_wepp(self) -> Dict[str, Any]:
        self._status = "completed"
        self._run_summary = {"completed": True}
        return dict(self._run_summary)

    def query_status(self) -> Dict[str, Any]:
        return {"enabled": self._enabled, "status": self._status, "errors": list(self._errors)}

    def query_summary(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "roads_params": dict(self._params),
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
