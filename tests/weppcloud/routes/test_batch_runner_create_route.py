from __future__ import annotations

import importlib

import pytest

pytest.importorskip("flask")
from flask import Flask

batch_runner_module = importlib.import_module("wepppy.weppcloud.routes.batch_runner.batch_runner_bp")

pytestmark = pytest.mark.routes


@pytest.fixture()
def batch_create_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["BATCH_RUNNER_ENABLED"] = True
    app.config["BATCH_RUNNER_SKIP_AUTH"] = True
    app.register_blueprint(batch_runner_module.batch_runner_bp)

    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(batch_runner_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured


def test_create_batch_sorts_available_configs(batch_create_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, captured = batch_create_client
    monkeypatch.setattr(
        batch_runner_module,
        "get_configs",
        lambda: ["zeta_wbt", "Alpha_wbt", "beta_wbt"],
    )

    response = client.get("/batch/create/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "create.htm"
    kwargs = captured["kwargs"]
    assert kwargs["available_configs"] == ["Alpha_wbt", "beta_wbt", "zeta_wbt"]
    assert kwargs["form_state"]["base_config"] == "Alpha_wbt"


def test_create_batch_prefers_disturbed_default(batch_create_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, captured = batch_create_client
    monkeypatch.setattr(
        batch_runner_module,
        "get_configs",
        lambda: ["zeta_wbt", "disturbed9002_wbt", "alpha_wbt"],
    )

    response = client.get("/batch/create/")

    assert response.status_code == 200
    kwargs = captured["kwargs"]
    assert kwargs["available_configs"] == ["alpha_wbt", "disturbed9002_wbt", "zeta_wbt"]
    assert kwargs["form_state"]["base_config"] == "disturbed9002_wbt"
