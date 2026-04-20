from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask

weppcloud_site_module = import_module("wepppy.weppcloud.routes.weppcloud_site")
weppcloud_site_bp = weppcloud_site_module.weppcloud_site_bp

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
DIAGNOSTICS_TEMPLATE = REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "diagnostics" / "diagnostics.htm"


def _build_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")
    return app


def test_diagnostics_route_renders_and_sets_no_store(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "<main>Diagnostics shell</main>"

    monkeypatch.setattr(weppcloud_site_module, "render_template", fake_render_template)

    with app.test_client() as client:
        response = client.get("/weppcloud/diagnostics/")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert "Diagnostics shell" in response.get_data(as_text=True)
    assert captured["template_name"] == "diagnostics/diagnostics.htm"


def test_diagnostics_route_without_trailing_slash_is_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()

    monkeypatch.setattr(
        weppcloud_site_module,
        "render_template",
        lambda *_args, **_kwargs: "<main>Diagnostics shell</main>",
    )

    with app.test_client() as client:
        response = client.get("/weppcloud/diagnostics")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"


def test_diagnostics_template_includes_base_and_noscript_blocker() -> None:
    source = DIAGNOSTICS_TEMPLATE.read_text(encoding="utf-8")

    assert '{% extends "base_pure.htm" %}' in source
    assert "<noscript>" in source
    assert "Blocking failure" in source
