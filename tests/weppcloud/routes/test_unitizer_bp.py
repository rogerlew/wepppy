from __future__ import annotations

from typing import Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.unitizer_bp as unitizer_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def unitizer_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(unitizer_module.unitizer_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    class DummyContext:
        def __init__(self, root_path: str) -> None:
            self.active_root = root_path

    def fake_load_run_context(runid: str, config: str) -> DummyContext:
        assert runid == RUN_ID
        assert config == CONFIG
        return DummyContext(str(run_dir))

    monkeypatch.setattr(unitizer_module, "load_run_context", fake_load_run_context)

    class DummyUnitizer:
        _instances: Dict[str, "DummyUnitizer"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.preferences: Dict[str, str] = {}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyUnitizer":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def set_preferences(self, kwds):
            self.preferences.update(kwds)
            return dict(self.preferences)

    monkeypatch.setattr(unitizer_module, "Unitizer", DummyUnitizer)

    with app.test_client() as client:
        yield client, DummyUnitizer, str(run_dir)

    DummyUnitizer._instances.clear()


def test_set_unit_preferences_accepts_json(unitizer_client):
    client, DummyUnitizer, run_dir = unitizer_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_unit_preferences/",
        json={"discharge": "metric"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"preferences": {"discharge": "metric"}}}

    controller = DummyUnitizer.getInstance(run_dir)
    assert controller.preferences == {"discharge": "metric"}


def test_set_unit_preferences_accepts_form_payload(unitizer_client):
    client, DummyUnitizer, run_dir = unitizer_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_unit_preferences/",
        data={"discharge": "units-english"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"preferences": {"discharge": "units-english"}}}

    controller = DummyUnitizer.getInstance(run_dir)
    assert controller.preferences == {"discharge": "units-english"}
