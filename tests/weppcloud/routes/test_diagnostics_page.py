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
DIAGNOSTICS_CORE_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "core.js"
DIAGNOSTICS_AUTH_CHECKS_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "auth_checks.js"
DIAGNOSTICS_BANDWIDTH_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "bandwidth_checks.js"
DIAGNOSTICS_REALTIME_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "diagnostics-realtime.js"
DIAGNOSTICS_REPORT_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "report.js"
DIAGNOSTICS_PAGE_JS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "diagnostics" / "page.js"


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
    assert "data-diagnostics-root" in source
    assert "data-diagnostics-check-list" in source
    assert "data-diagnostics-copy-json" in source
    assert "static_url('js/diagnostics/core.js')" in source
    assert "static_url('js/diagnostics/auth_checks.js')" in source
    assert "static_url('js/diagnostics/bandwidth_checks.js')" in source
    assert "static_url('js/diagnostics/report.js')" in source
    assert "static_url('js/diagnostics/diagnostics-realtime.js')" in source
    assert "static_url('js/diagnostics/page.js')" in source

    core_idx = source.index("static_url('js/diagnostics/core.js')")
    auth_idx = source.index("static_url('js/diagnostics/auth_checks.js')")
    bandwidth_idx = source.index("static_url('js/diagnostics/bandwidth_checks.js')")
    report_idx = source.index("static_url('js/diagnostics/report.js')")
    realtime_idx = source.index("static_url('js/diagnostics/diagnostics-realtime.js')")
    page_idx = source.index("static_url('js/diagnostics/page.js')")
    assert core_idx < auth_idx < bandwidth_idx < report_idx < realtime_idx < page_idx


def test_diagnostics_core_js_uses_site_prefix_dataset_contract() -> None:
    source = DIAGNOSTICS_CORE_JS.read_text(encoding="utf-8")

    assert "document.body.dataset.sitePrefix" in source
    assert 'return "";' in source


def test_diagnostics_assets_include_core_report_page_modules() -> None:
    assert DIAGNOSTICS_CORE_JS.exists()
    assert DIAGNOSTICS_AUTH_CHECKS_JS.exists()
    assert DIAGNOSTICS_BANDWIDTH_JS.exists()
    assert DIAGNOSTICS_REALTIME_JS.exists()
    assert DIAGNOSTICS_REPORT_JS.exists()
    assert DIAGNOSTICS_PAGE_JS.exists()


def test_diagnostics_realtime_js_includes_service_health_reachability_checks() -> None:
    source = DIAGNOSTICS_REALTIME_JS.read_text(encoding="utf-8")

    assert "status-health-reachability" in source
    assert "preflight-health-reachability" in source
    assert "/weppcloud-microservices/status/health" in source
    assert "/weppcloud-microservices/preflight/health" in source
    assert 'severity: "degraded"' in source
