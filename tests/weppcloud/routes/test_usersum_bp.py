from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Blueprint, Flask

from wepppy.weppcloud.routes.usersum import usersum_bp

pytestmark = pytest.mark.routes


@pytest.fixture()
def usersum_client():
    root = Path(__file__).resolve().parents[3]
    app_templates = root / "wepppy" / "weppcloud" / "templates"

    app = Flask(__name__, template_folder=str(app_templates))
    app.config["TESTING"] = True
    app.jinja_env.globals["static_url"] = lambda filename: f"/static/{filename}"

    site_bp = Blueprint("weppcloud_site", __name__)

    @site_bp.route("/", endpoint="index")
    def site_index():
        return "ok"

    app.register_blueprint(site_bp)
    app.register_blueprint(usersum_bp)

    with app.test_client() as client:
        yield client


def test_usersum_view_rewrites_repo_markdown_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/mods-overview.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'href="/usersum/src/wepppy/nodb/mods/openet/README.md"' in body
    assert 'href="../../../../nodb/mods/openet/README.md"' not in body


def test_usersum_view_rewrites_cross_category_markdown_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/db/climate_file.parameters.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'href="/usersum/view/input-file-specifications/cligenparms.md"' in body


def test_usersum_view_footer_exposes_doc_source_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/db/climate_file.parameters.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "view:db/climate_file.parameters.md" in body
    assert (
        'href="https://github.com/rogerlew/wepppy/blob/master/'
        'wepppy/weppcloud/routes/usersum/db/climate_file.parameters.md"'
    ) in body
    assert 'href="/usersum/raw/wepppy/weppcloud/routes/usersum/db/climate_file.parameters.md"' in body


def test_usersum_src_legacy_double_slash_redirects(usersum_client) -> None:
    response = usersum_client.get(
        "/usersum/src//wepppy/nodb/mods/openet/README.md",
        follow_redirects=False,
    )
    assert response.status_code == 308
    assert response.headers["Location"].endswith("/usersum/src/wepppy/nodb/mods/openet/README.md")


def test_usersum_src_route_renders_markdown(usersum_client) -> None:
    response = usersum_client.get("/usersum/src/wepppy/nodb/mods/openet/README.md")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "OpenET Climate Engine Mod" in body
    assert "src:wepppy/nodb/mods/openet/README.md" in body
    assert 'href="/usersum/raw/wepppy/nodb/mods/openet/README.md"' in body


def test_usersum_raw_route_returns_markdown(usersum_client) -> None:
    response = usersum_client.get("/usersum/raw/wepppy/nodb/mods/openet/README.md")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/markdown")
    assert "OpenET Climate Engine Mod" in response.get_data(as_text=True)


def test_usersum_view_does_not_render_procedural_h1_title(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/disturbed-land-soil-lookup.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "<h1>Disturbed Land Soil Lookup</h1>" not in body


def test_usersum_view_adds_heading_ids_for_anchor_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/mods-overview.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert '<h1 id="mods-overview">Mods Overview</h1>' in body
    assert '<h2 id="openet-time-series-openet_ts">' in body


def test_usersum_view_renders_accessibility_statement(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/accessibility-statement.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Accessibility Statement" in body
    assert "Roger Lew" in body
    assert "ACR/VPAT" in body
