from __future__ import annotations

from pathlib import Path

import pytest

flask = pytest.importorskip("flask")

from wepppy.weppcloud.routes.usersum import usersum_bp


pytestmark = pytest.mark.unit


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_usersum_layout_inherits_base_pure_for_theme_bootstrap() -> None:
    root = Path(__file__).resolve().parents[2]
    layout = root / "wepppy" / "weppcloud" / "routes" / "usersum" / "templates" / "usersum" / "layout.j2"
    contents = _read(layout)

    assert '{% extends "base_pure.htm" %}' in contents
    assert '{% include "usersum/header.htm" %}' in contents
    assert "static_url('css/markdown-theme.css')" in contents


def test_usersum_header_has_weppcloud_brand_and_theme_switcher() -> None:
    root = Path(__file__).resolve().parents[2]
    header = root / "wepppy" / "weppcloud" / "routes" / "usersum" / "templates" / "usersum" / "header.htm"
    contents = _read(header)

    assert "WEPPcloud" in contents
    assert "url_for('weppcloud_site.index')" in contents
    assert "{% include 'header/_theme_switcher.htm' %}" in contents


def test_usersum_index_renders_weppcloud_header_and_theme_switcher() -> None:
    root = Path(__file__).resolve().parents[2]
    app_templates = root / "wepppy" / "weppcloud" / "templates"
    app = flask.Flask(__name__, template_folder=str(app_templates))
    app.config["TESTING"] = True
    app.jinja_env.globals["static_url"] = lambda filename: f"/static/{filename}"

    site_bp = flask.Blueprint("weppcloud_site", __name__)

    @site_bp.route("/", endpoint="index")
    def site_index():
        return "ok"

    app.register_blueprint(site_bp)
    app.register_blueprint(usersum_bp)

    with app.test_client() as client:
        response = client.get("/usersum/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "WEPPcloud" in html
    assert "data-theme-select" in html
    assert "/static/js/theme.js" in html
