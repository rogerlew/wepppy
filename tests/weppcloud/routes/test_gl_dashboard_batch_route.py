from __future__ import annotations

from dataclasses import dataclass
import importlib

import pytest

pytest.importorskip("flask")
from flask import Flask

batch_runner_module = importlib.import_module("wepppy.weppcloud.routes.batch_runner.batch_runner_bp")

pytestmark = pytest.mark.routes


@dataclass(frozen=True)
class _FeatureStub:
    runid: str


@pytest.fixture()
def batch_gl_dashboard_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["BATCH_RUNNER_ENABLED"] = True
    app.config["BATCH_RUNNER_SKIP_AUTH"] = True
    app.config["GL_DASHBOARD_BATCH_ENABLED"] = "true"
    app.register_blueprint(batch_runner_module.batch_runner_bp)

    class DummyBatchRunner:
        base_config = "cfg"

        def get_watershed_features_lpt(self):
            return [_FeatureStub("run-001"), _FeatureStub("run-002")]

    monkeypatch.setattr(
        batch_runner_module.BatchRunner,
        "getInstanceFromBatchName",
        staticmethod(lambda batch_name: DummyBatchRunner()),
    )

    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(batch_runner_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured, app


def test_batch_gl_dashboard_renders_with_batch_context(batch_gl_dashboard_client) -> None:
    client, captured, _app = batch_gl_dashboard_client

    response = client.get("/batch/_/spring-2025/gl-dashboard")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "gl_dashboard.htm"
    kwargs = captured["kwargs"]
    assert kwargs["mode"] == "batch"
    assert kwargs["batch_name"] == "spring-2025"
    assert kwargs["runid"] == "batch;;spring-2025;;_base"
    assert kwargs["config"] == "cfg"
    assert kwargs["batch_mode_enabled"] is True
    assert kwargs["batch"]["name"] == "spring-2025"
    assert kwargs["batch"]["runs"] == [
        {"runid": "batch;;spring-2025;;run-001", "leaf_runid": "run-001"},
        {"runid": "batch;;spring-2025;;run-002", "leaf_runid": "run-002"},
    ]


def test_batch_gl_dashboard_respects_disabled_flag(batch_gl_dashboard_client) -> None:
    client, _captured, app = batch_gl_dashboard_client
    app.config["GL_DASHBOARD_BATCH_ENABLED"] = "off"

    response = client.get("/batch/_/spring-2025/gl-dashboard")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "GL Dashboard batch mode is currently disabled."


def test_batch_gl_dashboard_requires_batch_runner_enabled(batch_gl_dashboard_client) -> None:
    client, _captured, app = batch_gl_dashboard_client
    app.config["BATCH_RUNNER_ENABLED"] = False

    response = client.get("/batch/_/spring-2025/gl-dashboard")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Batch Runner is currently disabled."
