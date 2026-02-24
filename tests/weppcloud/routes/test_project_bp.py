from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.project_bp as project_module

from tests.factories.singleton import LockedMixin, singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"

pytestmark = pytest.mark.routes


@pytest.fixture()
def project_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
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

    def remove_mod(self, mod_name: str) -> None:
        if mod_name in self._mods:
            self._mods.remove(mod_name)

    RonStub = singleton_factory(
        "RonStub",
        attrs={
            "name": "",
            "scenario": "",
            "public": False,
            "readonly": False,
            "_mods": [],
        },
        methods={
            "remove_mod": remove_mod,
            "mods": property(lambda self: self._mods),
        },
        mixins=(LockedMixin,),
    )

    monkeypatch.setattr(project_module, "Ron", RonStub)
    monkeypatch.setattr(project_module, "iter_nodb_mods_subclasses", lambda: [])

    dispatched: Dict[str, Any] = {}

    def fake_redis_connection_kwargs(db):
        dispatched["redis_db"] = db
        return {"url": "redis://test"}

    monkeypatch.setattr(project_module, "redis_connection_kwargs", fake_redis_connection_kwargs)

    env = rq_environment
    queue_cls = env.queue_class(default_job_id="job-123")
    monkeypatch.setattr(project_module, "Queue", queue_cls)

    redis_client_cls = env.redis_client_class()
    monkeypatch.setattr(project_module.redis, "Redis", redis_client_cls)

    project_rq = __import__("wepppy.rq.project_rq", fromlist=["set_run_readonly_rq"])
    monkeypatch.setattr(project_rq, "set_run_readonly_rq", lambda runid, state: None)
    monkeypatch.setattr(project_rq, "TIMEOUT", 42)

    with app.test_client() as client:
        yield client, RonStub, dispatched, str(run_dir), env

    RonStub.reset_instances()


def test_setname_accepts_json_payload(project_client):
    client, RonStub, _, run_dir, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setname/",
        json={"name": " Watershed Scenario "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"name": "Watershed Scenario"}}

    controller = RonStub.getInstance(run_dir)
    assert controller.name == "Watershed Scenario"


def test_setname_defaults_to_untitled_when_blank(project_client):
    client, RonStub, _, run_dir, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setname/",
        json={"name": "   "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"name": "Untitled"}}

    controller = RonStub.getInstance(run_dir)
    assert controller.name == "Untitled"


def test_setscenario_handles_form_payload(project_client):
    client, RonStub, _, run_dir, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/setscenario/",
        data={"scenario": "  fire response  "},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"scenario": "fire response"}}

    controller = RonStub.getInstance(run_dir)
    assert controller.scenario == "fire response"


def test_set_public_accepts_boolean_variants(project_client):
    client, RonStub, _, run_dir, _ = project_client

    response_json = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        json={"public": True},
    )
    assert response_json.status_code == 200
    payload_json = response_json.get_json()
    assert payload_json == {"Content": {"public": True}}
    assert RonStub.getInstance(run_dir).public is True

    response_form = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        data={"public": "off"},
    )
    assert response_form.status_code == 200
    payload_form = response_form.get_json()
    assert payload_form == {"Content": {"public": False}}
    assert RonStub.getInstance(run_dir).public is False


def test_set_public_rejects_non_boolean_token(project_client):
    client, RonStub, _, _, _ = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_public",
        json={"public": "maybe"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "state must be boolean"


def test_set_readonly_enqueues_background_job(project_client):
    client, _, dispatched, _, env = project_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_readonly",
        json={"readonly": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"readonly": True, "job_id": "job-123"}}

    assert dispatched["redis_db"] == project_module.RedisDB.RQ
    client_entry = next(entry for entry in env.recorder.redis_entries if isinstance(entry, tuple))
    assert client_entry[1] == {"url": "redis://test"}
    queue_connection = env.recorder.queue_connections[0]
    assert getattr(queue_connection, "kwargs", {}) == {"url": "redis://test"}

    queue_call = env.recorder.queue_calls[0]
    project_rq = __import__("wepppy.rq.project_rq", fromlist=["set_run_readonly_rq"])
    assert queue_call.func is project_rq.set_run_readonly_rq
    assert queue_call.args == (RUN_ID, True)
    assert queue_call.timeout == 42


def test_set_mod_enables_simple_module(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    assert controller.mods == []

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "rap_ts", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "rap_ts"
    assert payload["Content"]["enabled"] is True
    assert "rap_ts" in controller.mods


def test_set_mod_openet_requires_admin(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    assert controller.mods == []

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "openet_ts", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "restricted to Admin users" in payload["error"]["message"]
    assert controller.mods == []


def test_set_mod_openet_allows_admin(project_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, RonStub, _, run_dir, _ = project_client
    monkeypatch.setattr(project_module, "_openet_admin_enabled", lambda: True)

    controller = RonStub.getInstance(run_dir)
    assert controller.mods == []

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "openet_ts", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "openet_ts"
    assert payload["Content"]["enabled"] is True
    assert "openet_ts" in controller.mods


def test_set_mod_disables_module_when_no_guards(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    controller._mods = ["rap_ts"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "rap_ts", "enabled": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["enabled"] is False
    assert controller.mods == []


def test_set_mod_blocks_dependency_violation(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    controller._mods = ["omni", "treatments"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "treatments", "enabled": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "Disable Omni" in payload["error"]["message"]
    assert controller.mods == ["omni", "treatments"]


def test_set_mod_rejects_unknown_module(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    assert controller.mods == []

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "unknown", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "Unknown module" in payload["error"]["message"]
    assert controller.mods == []


def test_set_mod_disable_moves_nodb_to_backup(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    controller._mods = ["rap_ts"]
    nodb_path = Path(run_dir) / "rap_ts.nodb"
    nodb_path.write_text("state-data")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "rap_ts", "enabled": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "rap_ts"
    assert payload["Content"]["enabled"] is False
    backup_path = Path(run_dir) / "rap_ts.bak"
    assert not nodb_path.exists()
    assert backup_path.exists()
    assert backup_path.read_text() == "state-data"


def test_set_mod_enable_restores_backup(project_client):
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    controller._mods = []
    backup_path = Path(run_dir) / "rap_ts.bak"
    backup_path.write_text("restored-state")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "rap_ts", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "rap_ts"
    assert payload["Content"]["enabled"] is True
    nodb_path = Path(run_dir) / "rap_ts.nodb"
    assert nodb_path.exists()
    assert nodb_path.read_text() == "restored-state"
    assert not backup_path.exists()


def test_set_mod_imports_missing_mod_class(project_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, RonStub, _, run_dir, _ = project_client
    controller = RonStub.getInstance(run_dir)
    assert controller.mods == []

    created = {"called": False}

    class DebrisFlowStub(project_module.NoDbBase):
        filename = "debris_flow.nodb"

        def __init__(self, wd: str, cfg_fn: str, run_group=None, group_name=None) -> None:
            created["called"] = True
            Path(wd).joinpath(self.filename).write_text("stub")

    calls = {"iter": 0, "imported": 0}

    def fake_iter():
        calls["iter"] += 1
        if calls["iter"] == 1:
            return iter([])
        return iter([("debris_flow", DebrisFlowStub)])

    def fake_import(mod_name: str) -> None:
        calls["imported"] += 1

    monkeypatch.setattr(project_module, "iter_nodb_mods_subclasses", fake_iter)
    monkeypatch.setattr(project_module.NoDbBase, "_import_mod_module", fake_import)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_mod",
        json={"mod": "debris_flow", "enabled": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "debris_flow"
    assert payload["Content"]["enabled"] is True
    assert "debris_flow" in controller.mods
    assert calls["imported"] == 1
    assert created["called"] is True
    assert Path(run_dir).joinpath("debris_flow.nodb").exists()
