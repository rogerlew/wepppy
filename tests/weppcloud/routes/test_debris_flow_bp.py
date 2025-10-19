from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.debris_flow_bp as debris_flow_module

RUN_ID = "test-run"
CONFIG = "main"


@pytest.fixture()
def debris_flow_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Provide a Flask client with stubbed dependencies for the debris flow blueprint."""

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    captured: Dict[str, Any] = {}

    def fake_get_wd(runid: str) -> str:
        assert runid == RUN_ID
        return str(run_dir)

    monkeypatch.setattr(debris_flow_module, "get_wd", fake_get_wd)

    class DummyRon:
        _instances: Dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(debris_flow_module, "Ron", DummyRon)

    class DummyDebrisFlow:
        _instances: Dict[str, "DummyDebrisFlow"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.report_invocations = 0

        @classmethod
        def getInstance(cls, wd: str) -> "DummyDebrisFlow":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            instance.report_invocations += 1
            return instance

    monkeypatch.setattr(debris_flow_module, "DebrisFlow", DummyDebrisFlow)

    class DummyUnitizer:
        _instances: Dict[str, "DummyUnitizer"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd

        @classmethod
        def getInstance(cls, wd: str) -> "DummyUnitizer":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(debris_flow_module, "Unitizer", DummyUnitizer)

    def fake_render_template(template: str, **context: Any) -> str:
        captured["template"] = template
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(debris_flow_module, "render_template", fake_render_template)

    monkeypatch.setattr(
        debris_flow_module.wepppy.nodb.unitizer, "precisions", {"depth": 2}, raising=False
    )
    monkeypatch.setattr(debris_flow_module, "current_user", SimpleNamespace(name="Tester"))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(debris_flow_module.debris_flow_bp)

    with app.test_client() as client:
        yield client, captured


def test_report_debris_flow_renders_template(debris_flow_client):
    client, captured = debris_flow_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/debris_flow/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"

    assert captured["template"] == "reports/debris_flow.htm"
    context = captured["context"]
    assert context["runid"] == RUN_ID
    assert context["config"] == CONFIG
    assert context["precisions"] == {"depth": 2}
