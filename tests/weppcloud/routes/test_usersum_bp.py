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
    assert "OpenET Climate Engine Mod" in response.get_data(as_text=True)


def test_usersum_view_does_not_render_procedural_h1_title(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/disturbed-land-soil-lookup.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "<h1>Disturbed Land Soil Lookup</h1>" not in body
