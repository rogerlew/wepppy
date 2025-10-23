from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.path_ce_bp as path_ce_module
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


class PathCEStub(LockedMixin):
    _instances: Dict[str, "PathCEStub"] = {}

    def __init__(self, wd: str, cfg_fn: str) -> None:
        super().__init__()
        self.wd = wd
        self.cfg_fn = cfg_fn
        self._config: Dict[str, Any] = {}
        self.status = "idle"
        self.status_message = "Waiting"
        self.progress = 0.0
        self.results: Dict[str, Any] = {}

    @property
    def config(self) -> Dict[str, Any]:
        return dict(self._config)

    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        self._config = dict(value)

    @classmethod
    def getInstance(cls, wd: str) -> "PathCEStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd, "path_ce.cfg")
            cls._instances[wd] = instance
        return instance

    @classmethod
    def tryGetInstance(cls, wd: str) -> Optional["PathCEStub"]:
        return cls._instances.get(wd)

    @classmethod
    def reset_instances(cls) -> None:
        cls._instances.clear()


@pytest.fixture()
def path_ce_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(path_ce_module.path_ce_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(path_ce_module, "load_run_context", lambda runid, cfg: context)
    monkeypatch.setattr(path_ce_module, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(path_ce_module, "PathCostEffective", PathCEStub)

    RonStub = singleton_factory("RonStub", attrs={"mods": ["path_ce"]}, mixins=(LockedMixin,))
    monkeypatch.setattr(path_ce_module, "Ron", RonStub)

    conn_factory = rq_environment.redis_conn_factory(label="redis-conn")
    monkeypatch.setattr(path_ce_module.redis, "Redis", lambda **kwargs: conn_factory())

    queue_class = rq_environment.queue_class(default_job_id="job-321")
    monkeypatch.setattr(path_ce_module, "Queue", queue_class)

    with app.test_client() as client:
        yield client, PathCEStub, RonStub, rq_environment, str(run_dir)

    PathCEStub.reset_instances()
    RonStub.reset_instances()
    rq_environment.recorder.reset()


def test_get_config_returns_controller_payload(path_ce_client):
    client, PathCEStub, _, _, run_dir = path_ce_client
    controller = PathCEStub.getInstance(run_dir)
    controller.config = {"sddc_threshold": 12.0}

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["config"]["sddc_threshold"] == 12.0


def test_update_config_normalizes_payload(path_ce_client):
    client, PathCEStub, _, _, run_dir = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={
            "sddc_threshold": "12",
            "sdyd_threshold": "4.5",
            "slope_min": "0.5",
            "slope_max": "8.25",
            "severity_filter": ["High", "Low", ""],
            "treatment_options": [
                {
                    "label": "Mulch",
                    "scenario": "sbs_map",
                    "quantity": "3",
                    "unit_cost": 120,
                    "fixed_cost": "42"
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    content = payload["Content"]["config"]
    assert content["sddc_threshold"] == 12.0
    assert content["sdyd_threshold"] == 4.5
    assert content["slope_range"] == [0.5, 8.25]
    assert content["severity_filter"] == ["High", "Low"]
    assert content["treatment_options"][0]["label"] == "Mulch"

    controller = PathCEStub.getInstance(run_dir)
    assert controller.config["slope_range"] == [0.5, 8.25]


def test_status_endpoint_handles_missing_instance(path_ce_client):
    client, PathCEStub, *_ = path_ce_client
    PathCEStub.reset_instances()

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "uninitialized",
        "status_message": "Module not configured.",
        "progress": 0.0,
    }


def test_run_enqueues_job(path_ce_client):
    client, PathCEStub, RonStub, rq_environment, run_dir = path_ce_client
    PathCEStub.getInstance(run_dir)  # ensure controller exists
    ron = RonStub.getInstance(run_dir)
    ron.mods = ["path_ce"]

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/path_cost_effective_run")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-321"

    queue_call = rq_environment.recorder.queue_calls[0]
    assert queue_call.func is path_ce_module.run_path_cost_effective_rq
    assert queue_call.args == (RUN_ID,)
