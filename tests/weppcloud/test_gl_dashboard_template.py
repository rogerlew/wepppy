from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask, render_template

pytestmark = pytest.mark.unit


def _make_template_app() -> Flask:
    template_root = Path(__file__).resolve().parents[2] / "wepppy" / "weppcloud" / "templates"
    app = Flask(__name__, template_folder=str(template_root))

    @app.get("/", endpoint="weppcloud_site.index")
    def _index() -> str:
        return ""

    # Keep the template render self-contained.
    app.jinja_env.globals["static_url"] = lambda path: f"/static/{path}"
    return app


def test_gl_dashboard_renders_with_omni_scenarios_without_contrasts() -> None:
    """Regression test: gl_dashboard.htm must not iterate over None omni_contrasts."""

    app = _make_template_app()
    omni_scenarios = [{"name": "treated", "path": "_pups/omni/scenarios/treated"}]

    with app.test_request_context("/"):
        rendered = render_template(
            "gl_dashboard.htm",
            runid="run-123",
            config="cfg",
            site_prefix="",
            tile_url="https://example.com/{z}/{x}/{y}.png",
            map_extent=None,
            map_center=None,
            map_zoom=None,
            climate_context=None,
            omni_scenarios=omni_scenarios,
            omni_contrasts=None,
            is_omni_child=False,
            mode="run",
            batch=None,
            batch_mode_enabled=False,
        )

    assert '<option value="_pups/omni/scenarios/treated">treated</option>' in rendered

