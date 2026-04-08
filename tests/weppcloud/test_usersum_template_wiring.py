from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

flask = pytest.importorskip("flask")
flask_login = pytest.importorskip("flask_login")

from wepppy.weppcloud.routes.usersum import usersum_bp


pytestmark = pytest.mark.unit


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_usersum_app() -> flask.Flask:
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
    return app


def _set_current_user(monkeypatch: pytest.MonkeyPatch, *, roles: tuple[str, ...], is_authenticated: bool = True) -> None:
    role_items = [SimpleNamespace(name=role) for role in roles]
    current_user = SimpleNamespace(is_authenticated=is_authenticated, roles=role_items)
    monkeypatch.setattr(flask_login, "current_user", current_user)


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
    assert "url_for_run('weppcloud_site.index')" in contents
    assert "url_for_run('usersum.usersum_search')" in contents
    assert "usersum-header-search" in contents
    assert "SEARCH" in contents
    assert "{% include 'header/_theme_switcher.htm' %}" in contents
    assert "usersum-header-role" in contents
    assert "wc-theme-switcher__select wc-run-header__input" in contents
    assert 'onchange="if (this.form.requestSubmit) { this.form.requestSubmit(); } else { this.form.submit(); }"' in contents


def test_usersum_view_template_reports_active_doc_role() -> None:
    root = Path(__file__).resolve().parents[2]
    view = root / "wepppy" / "weppcloud" / "routes" / "usersum" / "templates" / "usersum" / "view.htm"
    contents = _read(view)

    assert "wc-usersum-doc-role" in contents
    assert "active_doc.min_role" in contents


def test_wepp_reports_template_links_to_wepp_run_results_usersum_doc() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "controls" / "wepp_reports.htm"
    contents = _read(template)

    assert "wepp-run-results.md" in contents
    assert "WEPP Run Results guidance" in contents


def test_theme_switcher_labels_aa_checked_and_sensory_preference_themes() -> None:
    root = Path(__file__).resolve().parents[2]
    header = root / "wepppy" / "weppcloud" / "templates" / "header" / "_theme_switcher.htm"
    contents = _read(header)

    assert "AA checked" in contents
    assert "Sensory preference" in contents


def test_usersum_index_renders_weppcloud_header_and_theme_switcher() -> None:
    app = _build_usersum_app()

    with app.test_client() as client:
        response = client.get("/usersum/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "WEPPcloud" in html
    assert "data-theme-select" in html
    assert "/static/js/theme.js" in html
    assert "Browse the sections below or use the navigation tree on the left" in html
    assert "Module guides marked as source stubs" not in html
    assert 'id="usersum-header-role"' not in html


def test_usersum_header_role_selector_hidden_for_basic_authenticated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_current_user(monkeypatch, roles=("User",), is_authenticated=True)
    app = _build_usersum_app()

    with app.test_client() as client:
        response = client.get("/usersum/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="usersum-header-role"' not in html


@pytest.mark.parametrize(
    ("roles", "expected_options", "unexpected_options"),
    [
        (("PowerUser",), ("user", "operator"), ("developer", "internal")),
        (("Admin",), ("user", "operator", "developer"), ("internal",)),
        (("Root",), ("user", "operator", "developer", "internal"), ()),
    ],
)
def test_usersum_header_role_selector_options_by_weppcloud_role(
    monkeypatch: pytest.MonkeyPatch,
    roles: tuple[str, ...],
    expected_options: tuple[str, ...],
    unexpected_options: tuple[str, ...],
) -> None:
    _set_current_user(monkeypatch, roles=roles, is_authenticated=True)
    app = _build_usersum_app()

    with app.test_client() as client:
        response = client.get("/usersum/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="usersum-header-role"' in html
    for option in expected_options:
        assert f'<option value="{option}"' in html
    for option in unexpected_options:
        assert f'<option value="{option}"' not in html
