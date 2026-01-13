from __future__ import annotations

from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

pytestmark = pytest.mark.unit

import wepppy.weppcloud.routes.nodb_api.wepp_bp as wepp_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def wepp_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(wepp_module.wepp_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DummyContext:
        def __init__(self, root_path: str) -> None:
            self.active_root = root_path

    monkeypatch.setattr(wepp_module, "load_run_context", lambda runid, config: DummyContext(str(run_dir)))
    monkeypatch.setattr(wepp_module, "get_wd", lambda runid: str(run_dir))

    class DummyWepp:
        _instances: Dict[str, "DummyWepp"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.calls: Dict[str, Any] = {}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWepp":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def set_run_wepp_ui(self, value: bool) -> None:
            self.calls["wepp_ui"] = value

        def set_run_pmet(self, value: bool) -> None:
            self.calls["pmet"] = value

        def set_run_frost(self, value: bool) -> None:
            self.calls["frost"] = value

        def set_run_tcr(self, value: bool) -> None:
            self.calls["tcr"] = value

        def set_run_snow(self, value: bool) -> None:
            self.calls["snow"] = value

        def set_run_flowpaths(self, value: bool) -> None:
            self.calls["run_flowpaths"] = value

    monkeypatch.setattr(wepp_module, "Wepp", DummyWepp)

    with app.test_client() as client:
        yield client, DummyWepp, str(run_dir)

    DummyWepp._instances.clear()


@pytest.mark.parametrize(
    ("routine", "method_name"),
    [
        ("wepp_ui", "wepp_ui"),
        ("pmet", "pmet"),
        ("frost", "frost"),
        ("tcr", "tcr"),
        ("snow", "snow"),
        ("run_flowpaths", "run_flowpaths"),
    ],
)
def test_set_run_wepp_routine_accepts_json_boolean(wepp_client, routine, method_name):
    client, DummyWepp, run_dir = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": routine, "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Content": {"routine": routine, "state": True}}

    controller = DummyWepp.getInstance(run_dir)
    assert controller.calls[method_name] is True


def test_set_run_wepp_routine_rejects_non_boolean_state(wepp_client):
    client, DummyWepp, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "pmet", "state": "maybe"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "state must be boolean"


def test_set_run_wepp_routine_requires_known_routine(wepp_client):
    client, DummyWepp, _ = wepp_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_run_wepp_routine/",
        json={"routine": "unknown", "state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "routine not in" in payload["error"]["message"]

