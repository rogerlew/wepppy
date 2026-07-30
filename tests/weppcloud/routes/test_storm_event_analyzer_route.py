from __future__ import annotations

from dataclasses import dataclass

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.storm_event_analyzer as storm_module
import wepppy.weppcloud.utils.cap_guard as cap_guard_module

pytestmark = pytest.mark.routes

BASELINE_WEPP_PATHS = {
    "soil": "wepp/output/interchange/H.soil.parquet",
    "water": "wepp/output/interchange/H.wat.parquet",
    "outlet": "wepp/output/interchange/ebe_pw0.parquet",
    "hillEvents": "wepp/output/interchange/H.ebe.parquet",
    "tc": "wepp/output/interchange/tc_out.parquet",
}

ROADS_WEPP_PATHS = {
    "soil": "wepp/roads/output/interchange/H.soil.parquet",
    "water": "wepp/roads/output/interchange/H.wat.parquet",
    "outlet": "wepp/roads/output/interchange/ebe_pw0.parquet",
    "hillEvents": "wepp/roads/output/interchange/H.ebe.parquet",
    "tc": "wepp/roads/output/interchange/tc_out.parquet",
}


@pytest.fixture()
def storm_event_analyzer_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(storm_module.storm_event_analyzer_bp)

    @dataclass
    class DummyContext:
        active_root: str
        pup_relpath: str = ""

    class AuthUser:
        is_authenticated = True

    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(cap_guard_module, "current_user", AuthUser())
    monkeypatch.setattr(storm_module, "current_user", AuthUser())
    monkeypatch.setattr(storm_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(
        storm_module,
        "load_run_context",
        lambda runid, config: DummyContext(active_root=str(run_dir)),
    )
    monkeypatch.setattr(
        storm_module,
        "is_omni_child_run",
        lambda runid, wd=None, pup_relpath=None: False,
    )
    monkeypatch.setattr(storm_module, "_get_omni_scenarios", lambda wd: None)

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            return type("RonObj", (), {"has_sbs": False})()

    class DummyUnitizer:
        @staticmethod
        def getInstance(wd: str):
            return object()

    monkeypatch.setattr(storm_module, "Ron", DummyRon)
    monkeypatch.setattr(storm_module, "Unitizer", DummyUnitizer)
    monkeypatch.setattr(storm_module, "RonViewModel", lambda ron: object())

    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(storm_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured


def test_storm_event_analyzer_defaults_to_baseline_scope(storm_event_analyzer_client) -> None:
    client, captured = storm_event_analyzer_client

    response = client.get("/runs/run-123/cfg/storm-event-analyzer")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "reports/storm_event_analyzer.htm"
    kwargs = captured["kwargs"]
    assert kwargs["output_scope"] == "baseline"
    assert kwargs["wepp_paths"] == BASELINE_WEPP_PATHS


def test_storm_event_analyzer_supports_roads_scope(storm_event_analyzer_client) -> None:
    client, captured = storm_event_analyzer_client

    response = client.get("/runs/run-456/cfg/storm-event-analyzer?output_scope=roads")

    assert response.status_code == 200
    kwargs = captured["kwargs"]
    assert kwargs["output_scope"] == "roads"
    assert kwargs["wepp_paths"] == ROADS_WEPP_PATHS


def test_storm_event_analyzer_rejects_invalid_output_scope(storm_event_analyzer_client) -> None:
    client, _captured = storm_event_analyzer_client

    response = client.get("/runs/run-789/cfg/storm-event-analyzer?output_scope=invalid")

    assert response.status_code == 400
    payload = response.get_json()
    assert "Invalid output_scope" in payload["error"]["message"]
