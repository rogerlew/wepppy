from __future__ import annotations

from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.project_bp as project_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def project_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Provide a Flask client with project blueprint dependencies stubbed out."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(project_module.project_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DummyContext:
        def __init__(self, root_path: str) -> None:
            self.active_root = root_path

    def fake_load_run_context(runid: str, config: str) -> DummyContext:
        assert runid == RUN_ID
        assert config == CONFIG
        return DummyContext(str(run_dir))

    monkeypatch.setattr(project_module, "load_run_context", fake_load_run_context)

    class DummyRon:
        _instances: Dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.name: str = ""
            self.scenario: str = ""
            self.public: bool = False
            self.readonly: bool = False
            self._mods: list[str] = []

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(project_module, "Ron", DummyRon)

    dispatched: Dict[str, Any] = {}

    def fake_redis_connection_kwargs(db):
        dispatched["redis_db"] = db
        return {"url": "redis://test"}

    monkeypatch.setattr(project_module, "redis_connection_kwargs", fake_redis_connection_kwargs)

    class DummyRedis:
        def __init__(self, **kwargs):
            dispatched["redis_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(project_module.redis, "Redis", DummyRedis)

    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class DummyQueue:
        def __init__(self, connection: Any) -> None:
            dispatched["queue_connection"] = connection

        def enqueue_call(self, func, args, timeout):
            dispatched["enqueue_call"] = {"func": func, "args": args, "timeout": timeout}
            return DummyJob("job-123")

    monkeypatch.setattr(project_module, "Queue", DummyQueue)

    project_rq = __import__("wepppy.rq.project_rq", fromlist=["set_run_readonly_rq"])
    monkeypatch.setattr(project_rq, "set_run_readonly_rq", lambda runid, state: None)
    monkeypatch.setattr(project_rq, "TIMEOUT", 42)

    with app.test_client() as client:
        yield client, DummyRon, dispatched, str(run_dir)

    DummyRon._instances.clear()


def test_setname_accepts_json_payload(project_client):
    client, DummyRon, _, run_dir = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setname/",
        json={"name": " Watershed Scenario "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"name": "Watershed Scenario"}}

    controller = DummyRon.getInstance(run_dir)
    assert controller.name == "Watershed Scenario"


def test_setname_defaults_to_untitled_when_blank(project_client):
    client, DummyRon, _, run_dir = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setname/",
        json={"name": "   "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"name": "Untitled"}}

    controller = DummyRon.getInstance(run_dir)
    assert controller.name == "Untitled"


def test_setscenario_handles_form_payload(project_client):
    client, DummyRon, _, run_dir = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setscenario/",
        data={"scenario": "  fire response  "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"scenario": "fire response"}}

    controller = DummyRon.getInstance(run_dir)
    assert controller.scenario == "fire response"


def test_set_public_accepts_boolean_variants(project_client):
    client, DummyRon, _, run_dir = project_client

    response_json = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        json={"public": True},
    )
    assert response_json.status_code == 200
    payload_json = response_json.get_json()
    assert payload_json == {"Success": True, "Content": {"public": True}}
    assert DummyRon.getInstance(run_dir).public is True

    response_form = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        data={"public": "off"},
    )
    assert response_form.status_code == 200
    payload_form = response_form.get_json()
    assert payload_form == {"Success": True, "Content": {"public": False}}
    assert DummyRon.getInstance(run_dir).public is False


def test_set_public_rejects_non_boolean_token(project_client):
    client, DummyRon, _, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        json={"public": "maybe"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "state must be boolean"


def test_set_readonly_enqueues_background_job(project_client):
    client, _, dispatched, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_readonly",
        json={"readonly": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "job_id": "job-123", "readonly": True}

    assert dispatched["redis_db"] == project_module.RedisDB.RQ
    assert dispatched["redis_kwargs"] == {"url": "redis://test"}
    assert "queue_connection" in dispatched
    project_rq = __import__("wepppy.rq.project_rq", fromlist=["set_run_readonly_rq"])
    assert dispatched["enqueue_call"]["func"] is project_rq.set_run_readonly_rq
    assert dispatched["enqueue_call"]["args"] == (RUN_ID, True)
    assert dispatched["enqueue_call"]["timeout"] == 42
