from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.path_ce_bp as path_ce_module
from wepppy.nodb.mods.path_ce.path_cost_effective import _normalize_config
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


class PathCEStub(LockedMixin):
    """Stub that keeps the real config normalization contract."""

    _instances: Dict[str, "PathCEStub"] = {}

    def __init__(self, wd: str, cfg_fn: str) -> None:
        super().__init__()
        self.wd = wd
        self.cfg_fn = cfg_fn
        self._config: Dict[str, Any] = _normalize_config({})
        self.status = "idle"
        self.status_message = "Waiting"
        self.progress = 0.0
        self.results: Dict[str, Any] = {}

    @property
    def config(self) -> Dict[str, Any]:
        return dict(self._config)

    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        self._config = _normalize_config(value)

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

    DisturbedStub = singleton_factory("DisturbedStub", attrs={"has_sbs": True}, mixins=(LockedMixin,))
    monkeypatch.setattr(path_ce_module, "Disturbed", DisturbedStub)

    conn_factory = rq_environment.redis_conn_factory(label="redis-conn")
    monkeypatch.setattr(path_ce_module.redis, "Redis", lambda **kwargs: conn_factory())

    queue_class = rq_environment.queue_class(default_job_id="job-321")
    monkeypatch.setattr(path_ce_module, "Queue", queue_class)

    # no active prior job by default (dedup guard passes)
    monkeypatch.setattr(
        path_ce_module, "RedisPrep", SimpleNamespace(tryGetInstance=lambda wd: None)
    )

    with app.test_client() as client:
        yield client, PathCEStub, RonStub, DisturbedStub, rq_environment, str(run_dir)

    PathCEStub.reset_instances()
    RonStub.reset_instances()
    DisturbedStub.reset_instances()
    rq_environment.recorder.reset()


def test_get_config_returns_controller_payload(path_ce_client):
    client, PathCEStub, *_unused, run_dir = path_ce_client
    controller = PathCEStub.getInstance(run_dir)
    controller.config = {"sddc_threshold": 12.0}

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["config"]["sddc_threshold"] == 12.0
    # full schema surfaces defaults
    assert payload["config"]["treatments"][0]["scenario"] == "mulch_15_sbs_map"
    assert "render_reports" not in payload["config"]


def test_update_config_normalizes_payload(path_ce_client):
    client, PathCEStub, *_unused, run_dir = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={
            "sddc_threshold": "12",
            "sdyd_threshold": "4.5",
            "slope_min": "0.5",
            "slope_max": "8.25",
            "severity_filter": ["High", "Low", ""],
            "treatments": [
                {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
                 "unit_cost": "3000", "quantity": 2, "fixed_cost": "1500"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    content = payload["Content"]["config"]
    assert content["sddc_threshold"] == 12.0
    assert content["sdyd_threshold"] == 4.5
    assert content["slope_range"] == [0.5, 8.25]
    assert content["severity_filter"] == ["High", "Low"]
    assert content["treatments"] == [
        {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
         "unit_cost": 3000.0, "quantity": 2.0, "fixed_cost": 1500.0},
    ]

    controller = PathCEStub.getInstance(run_dir)
    assert controller.config["slope_range"] == [0.5, 8.25]
    assert controller.config["treatments"][0]["unit_cost"] == 3000.0


def test_update_config_is_partial_merge(path_ce_client):
    client, PathCEStub, *_unused, run_dir = path_ce_client
    controller = PathCEStub.getInstance(run_dir)
    controller.config = {
        "treatments": [
            {"label": "2 tons/acre", "scenario": "mulch_60_sbs_map",
             "unit_cost": 3000, "quantity": 2, "fixed_cost": 1500},
        ]
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={"sddc_threshold": 48.2},
    )

    assert response.status_code == 200
    config = PathCEStub.getInstance(run_dir).config
    assert config["sddc_threshold"] == 48.2
    # previously-set treatments survive a partial update
    assert len(config["treatments"]) == 1
    assert config["treatments"][0]["unit_cost"] == 3000.0


def test_update_config_rejects_invalid_treatments(path_ce_client):
    client, *_ = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={"treatments": [{"label": "", "scenario": "mulch_60_sbs_map"}]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "label" in payload["error"]["message"]


def test_status_endpoint_handles_missing_instance(path_ce_client):
    client, PathCEStub, *_ = path_ce_client
    PathCEStub.reset_instances()

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "uninitialized",
        "status_message": "Module not configured.",
        "progress": 0.0,
        "precondition_errors": [],
    }


def test_status_endpoint_propagates_failed_state(path_ce_client):
    client, PathCEStub, *_unused, run_dir = path_ce_client
    controller = PathCEStub.getInstance(run_dir)
    controller.status = "failed"
    controller.status_message = "controller exploded"
    controller.progress = 0.42

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "failed",
        "status_message": "controller exploded",
        "progress": 0.42,
        "precondition_errors": [],
    }


def test_run_enqueues_job(path_ce_client):
    client, PathCEStub, RonStub, DisturbedStub, rq_environment, run_dir = path_ce_client
    PathCEStub.getInstance(run_dir)  # ensure controller exists
    ron = RonStub.getInstance(run_dir)
    ron.mods = ["path_ce"]
    DisturbedStub.getInstance(run_dir).has_sbs = True

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/path_cost_effective_run")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["job_id"] == "job-321"

    queue_call = rq_environment.recorder.queue_calls[0]
    assert queue_call.func is path_ce_module.run_path_cost_effective_rq
    assert queue_call.args == (RUN_ID,)


def test_run_persists_config_before_enqueue(path_ce_client):
    client, PathCEStub, RonStub, DisturbedStub, rq_environment, run_dir = path_ce_client
    controller = PathCEStub.getInstance(run_dir)
    ron = RonStub.getInstance(run_dir)
    ron.mods = ["path_ce"]
    DisturbedStub.getInstance(run_dir).has_sbs = True

    payload = {
        "sddc_threshold": "12",
        "sdyd_threshold": "4.5",
        "slope_min": "1",
        "slope_max": "9",
        "severity_filter": ["High"],
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/path_cost_effective_run",
        json=payload,
    )

    assert response.status_code == 200
    # Config should be persisted on controller prior to enqueue
    assert controller.config["sddc_threshold"] == 12.0
    assert controller.config["slope_range"] == [1.0, 9.0]
    assert controller.config["severity_filter"] == ["High"]

    queue_call = rq_environment.recorder.queue_calls[0]
    assert queue_call.func is path_ce_module.run_path_cost_effective_rq
    assert queue_call.args == (RUN_ID,)


def test_update_config_rejects_nonnumeric_threshold(path_ce_client):
    """Invalid values must error, not silently coerce to 0.0."""
    client, PathCEStub, *_unused, run_dir = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={"sddc_threshold": "abc"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "error" in payload
    assert PathCEStub.getInstance(run_dir).config["sddc_threshold"] == 0.0  # unchanged default


def test_update_config_ignores_retired_render_flag(path_ce_client):
    # reports always render; render_reports is neither parsed nor persisted
    client, PathCEStub, *_unused, run_dir = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={"render_reports": "false", "sddc_threshold": "12"},
    )
    assert response.status_code == 200
    config = PathCEStub.getInstance(run_dir).config
    assert config["sddc_threshold"] == 12.0
    assert "render_reports" not in config


def test_update_config_rejects_empty_treatment_list(path_ce_client):
    client, *_ = path_ce_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/path_ce/config",
        json={"treatments": []},
    )
    payload = response.get_json()
    assert "at least one treatment" in payload["error"]["message"]


def test_run_rejected_while_job_active(path_ce_client, monkeypatch):
    client, PathCEStub, RonStub, DisturbedStub, _rq, run_dir = path_ce_client
    PathCEStub.getInstance(run_dir)
    RonStub.getInstance(run_dir).mods = ["path_ce"]
    DisturbedStub.getInstance(run_dir).has_sbs = True

    prep = SimpleNamespace(get_rq_job_id=lambda key: "job-live")
    monkeypatch.setattr(
        path_ce_module, "RedisPrep", SimpleNamespace(tryGetInstance=lambda wd: prep)
    )
    live_job = SimpleNamespace(get_status=lambda refresh=False: "started")
    monkeypatch.setattr(
        path_ce_module, "Job", SimpleNamespace(fetch=lambda job_id, connection: live_job)
    )

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/path_cost_effective_run")

    payload = response.get_json()
    assert "already in progress" in payload["error"]["message"]
    assert "job-live" in payload["error"]["message"]


def test_run_requires_sbs_map(path_ce_client):
    client, PathCEStub, RonStub, DisturbedStub, *_rest = path_ce_client
    run_dir = _rest[-1]
    PathCEStub.getInstance(run_dir)
    ron = RonStub.getInstance(run_dir)
    ron.mods = ["path_ce"]
    DisturbedStub.getInstance(run_dir).has_sbs = False

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/path_cost_effective_run")

    assert response.status_code == 200
    payload = response.get_json()
    assert "SBS map" in payload["error"]["message"]
