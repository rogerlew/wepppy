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
    assert 'href="/usersum/doc/usersum.source.openet"' in body
    assert 'href="../../../../nodb/mods/openet/README.md"' not in body


def test_usersum_view_rewrites_cross_category_markdown_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/db/climate_file.parameters.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'href="/usersum/doc/usersum.input_file_specifications.cligenparms"' in body


def test_usersum_view_footer_exposes_doc_source_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/db/climate_file.parameters.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "wepppy/weppcloud/routes/usersum/db/climate_file.parameters.md" in body
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
    assert "wepppy/nodb/mods/openet/README.md" in body
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


def test_usersum_view_legacy_wepp_forest_change_log_alias_renders(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/wepp-forest-change-log.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "WEPP-Forest Change Log" in body
    assert "Canonical WEPP build/version history for" in body
    assert "wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md" in body


def test_usersum_doc_route_renders_disturbed_enduser_guide(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.source.disturbed")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Dominant hillslope severity" in body
    assert "wepppy/nodb/mods/disturbed/ENDUSER.md" in body


def test_usersum_doc_route_renders_omni_enduser_guide(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.source.omni")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "GL-Dashboard and Storm Event Analyzer" in body
    assert "wepppy/nodb/mods/omni/ENDUSER.md" in body


def test_usersum_doc_route_renders_runs_directory_structure(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.weppcloud_runs_directory_structure")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "ron.nodb" in body
    assert "wepp/output/interchange/" in body
    assert "saved project state that WEPPcloud uses for modeling" in body


def test_usersum_doc_route_renders_wepp_interchange(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.wepp_interchange")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "H.wat.parquet" in body
    assert "loss_pw0.out.parquet" in body


def test_usersum_doc_route_renders_wepp_run_results(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.wepp_run_results")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "which result should I open first?" in body
    assert "Fork Project and Run Undisturbed" in body
    assert "wepppy/weppcloud/routes/usersum/weppcloud/wepp-run-results.md" in body


def test_usersum_doc_route_renders_weppcloud_calibration_guidance(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.calibration_guidance")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Start with the most defensible hydrologic controls" in body
    assert "WEPPcloud Calibration Guidance" in body
    assert "wepppy/weppcloud/routes/usersum/weppcloud/weppcloud-calibration-guidance.md" in body


def test_usersum_doc_route_renders_undisturbed_earth(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.undisturbed_earth")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "outside the current United States, Europe, and Australia regional interfaces" in body
    assert "Copernicus DEM 30 m" in body
    assert "WEPPcloud-WBT" in body
    assert "wepppy/weppcloud/routes/usersum/weppcloud/undisturbed-earth.md" in body


def test_usersum_doc_route_renders_sbs_map_preparation(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.sbs_map_preparation")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "single-band integer file" in body
    assert "Map has non-integer classes" in body


def test_usersum_index_lists_nested_markdown_documents(usersum_client) -> None:
    response = usersum_client.get("/usersum/")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "/usersum/doc/usersum.weppcloud.mods_overview" in body
    assert "/usersum/doc/usersum.weppcloud.controls.channel_delineation" not in body
    assert "Provides the fastest path from a new run to a working project with core controls explained." in body
    assert "Explains how OpenET-derived evapotranspiration data are incorporated into climate and analysis workflows." in body

    disturbed_idx = body.index("/usersum/doc/usersum.source.disturbed")
    climate_idx = body.index("/usersum/doc/usersum.weppcloud.climate_options")
    wepp_idx = body.index("/usersum/doc/usersum.weppcloud.wepp_model")
    advanced_idx = body.index("/usersum/doc/usersum.weppcloud.wepp_advanced_options")
    run_results_idx = body.index("/usersum/doc/usersum.weppcloud.wepp_run_results")
    omni_idx = body.index("/usersum/doc/usersum.source.omni")
    calibration_guidance_idx = body.index("/usersum/doc/usersum.weppcloud.calibration_guidance")
    bootstrap_idx = body.index("/usersum/doc/usersum.weppcloud.bootstrap")
    observed_idx = body.index("/usersum/doc/usersum.weppcloud.observed_model_fitting")
    disturbed_lookup_idx = body.index("/usersum/doc/usersum.weppcloud.disturbed_land_soil_lookup")
    calibration_idx = body.index("WEPP Calibration")
    assert disturbed_idx < climate_idx < wepp_idx < advanced_idx < run_results_idx < omni_idx < calibration_idx
    assert calibration_idx < calibration_guidance_idx < bootstrap_idx < observed_idx < disturbed_lookup_idx

    faq_idx = body.index("/usersum/doc/usersum.weppcloud.faq")
    getting_started_idx = body.index("/usersum/doc/usersum.weppcloud.getting_started")
    quick_start_idx = body.index("/usersum/doc/usersum.weppcloud.quick_start")
    mods_overview_idx = body.index("/usersum/doc/usersum.weppcloud.mods_overview")
    earth_idx = body.index("/usersum/doc/usersum.weppcloud.undisturbed_earth")
    assert faq_idx < getting_started_idx < quick_start_idx
    assert mods_overview_idx < earth_idx

    project_files_idx = body.index("Project Files and Maps")
    runs_dir_idx = body.index("/usersum/doc/usersum.weppcloud.weppcloud_runs_directory_structure")
    interchange_idx = body.index("/usersum/doc/usersum.weppcloud.wepp_interchange")
    sbs_idx = body.index("/usersum/doc/usersum.weppcloud.sbs_map_preparation")
    assert project_files_idx < runs_dir_idx < interchange_idx < sbs_idx


def test_usersum_links_include_site_prefix_when_configured() -> None:
    root = Path(__file__).resolve().parents[3]
    app_templates = root / "wepppy" / "weppcloud" / "templates"

    app = Flask(__name__, template_folder=str(app_templates))
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"
    app.jinja_env.globals["static_url"] = lambda filename: f"/static/{filename}"

    site_bp = Blueprint("weppcloud_site", __name__)

    @site_bp.route("/", endpoint="index")
    def site_index():
        return "ok"

    app.register_blueprint(site_bp)
    app.register_blueprint(usersum_bp)

    with app.test_client() as client:
        response = client.get("/usersum/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '/weppcloud/usersum/doc/usersum.weppcloud.mods_overview' in body
    assert 'href="/weppcloud/usersum/doc/usersum.weppcloud.getting_started"' in body
    assert 'href="/usersum/doc/usersum.weppcloud.getting_started"' not in body


def test_usersum_api_search_requires_query(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search")
    assert response.status_code == 400
    assert response.get_json() == {"error": {"message": 'Search query "q" is required.'}}


def test_usersum_api_search_rejects_unauthorized_role_filter(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search?q=openet&role=operator")
    assert response.status_code == 403
    assert "Requested role filter is not allowed" in response.get_json()["error"]["message"]


def test_usersum_api_search_rejects_invalid_limit(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search?q=openet&limit=999")
    assert response.status_code == 400
    assert 'Query parameter "limit" must be <= 100.' in response.get_json()["error"]["message"]


def test_usersum_api_search_returns_results_payload(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search?q=openet")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["total"] >= 1
    assert payload["limit"] == 20
    assert payload["offset"] == 0
    assert payload["results"]

    first = payload["results"][0]
    assert set(first.keys()) == {
        "doc_id",
        "title",
        "rel_path",
        "min_role",
        "category",
        "snippet",
        "score",
        "breadcrumb",
    }
    assert first["min_role"] == "user"


def test_usersum_api_search_returns_html_snippets(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search?q=openet")
    assert response.status_code == 200

    payload = response.get_json()
    snippets = [result["snippet"] for result in payload["results"] if result.get("snippet")]
    assert snippets
    assert snippets[0].strip().startswith("<p>")
    assert "&lt;p&gt;" not in snippets[0]


def test_usersum_api_search_filters_category(usersum_client) -> None:
    response = usersum_client.get("/usersum/api/search?q=mods&category=weppcloud")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["total"] >= 1
    assert any(
        result["rel_path"].endswith("weppcloud/routes/usersum/weppcloud/mods-overview.md")
        for result in payload["results"]
    )


def test_usersum_search_page_renders_results(usersum_client) -> None:
    response = usersum_client.get("/usersum/search?q=openet")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Usersum Search" in body
    assert "/usersum/doc/usersum.weppcloud.mods_overview" in body


def test_usersum_doc_route_renders_markdown(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.mods_overview")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Mods Overview" in body
    assert "wepppy/weppcloud/routes/usersum/weppcloud/mods-overview.md" in body


def test_usersum_vendor_route_renders_markdown(usersum_client) -> None:
    response = usersum_client.get(
        "/usersum/vendor/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md"
    )
    assert response.status_code == 404
