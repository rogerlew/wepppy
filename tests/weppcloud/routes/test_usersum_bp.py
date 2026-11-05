from __future__ import annotations

from dataclasses import replace
from html import escape
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Blueprint, Flask

from wepppy.weppcloud.routes.usersum import usersum_bp
from wepppy.weppcloud.routes.usersum import usersum as usersum_routes
from wepppy.weppcloud.usersum_docs import runtime_catalog

pytestmark = pytest.mark.routes

_ROLE_RANK = {"user": 0, "operator": 1, "developer": 2, "internal": 3}


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


@pytest.fixture()
def set_usersum_current_user(monkeypatch: pytest.MonkeyPatch):
    import flask_login

    def _set(*, roles: tuple[str, ...] = (), is_authenticated: bool = True, **attrs: object) -> SimpleNamespace:
        role_items = [SimpleNamespace(name=role) for role in roles]
        user = SimpleNamespace(is_authenticated=is_authenticated, roles=role_items, **attrs)
        monkeypatch.setattr(flask_login, "current_user", user)
        return user

    return _set


def test_usersum_view_rewrites_repo_markdown_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/weppcloud/mods-overview.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'href="/usersum/doc/usersum.source.openet"' in body
    assert 'href="../../../../nodb/mods/openet/README.md"' not in body


@pytest.mark.parametrize("roles,authenticated,query", [
    ((), False, ""),
    ((), False, "?role=internal"),
    (("User",), True, ""),
    (("PowerUser",), True, "?role=user"),
    (("Root",), True, "?role=internal"),
])
def test_feature_catalog_public_complete_real_registries(
    usersum_client, set_usersum_current_user, roles, authenticated, query,
) -> None:
    from wepppy.weppcloud.feature_registry.runtime import load_config_registry, load_feature_registry

    set_usersum_current_user(roles=roles, is_authenticated=authenticated)
    response = usersum_client.get("/usersum/features/" + query)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    for prefix, entries in (("feature", load_feature_registry()), ("config", load_config_registry())):
        rows = re.findall(r'<tr id="' + prefix + r'-([^"]+)">(.*?)</tr>', body, re.S)
        assert [row_id for row_id, _ in rows] == [entry.id for entry in entries]
        for (_, row), entry in zip(rows, entries):
            assert escape(entry.label) in row
            assert f'Maturity: {entry.maturity.capitalize()}' in row
            if entry.internal_reason:
                assert entry.internal_reason.replace("_", " ") in row
            if entry.embargo_until:
                assert entry.embargo_until in row
            if getattr(entry, "access_mode", None) == "group_only":
                assert f'Group only: <code>{entry.access_group}</code>' in row
                assert "Roles alone do not grant access." in row
                assert "role policy" not in row
            elif getattr(entry, "access_mode", None) == "role_or_group":
                assert f'Or membership in <code>{entry.access_group}</code>' in row
            elif entry.min_role == "user":
                assert "Includes anonymous users; operation and launch permissions still apply." in row
    roads_row = re.search(r'<tr id="feature-roads">(.*?)</tr>', body, re.S).group(1)
    assert "Experimental" in roads_row
    assert "PowerUser role policy" in roads_row
    assert ('id="usersum-header-role"' in body) == (roles in (("PowerUser",), ("Root",)))


def test_feature_catalog_links_use_site_prefix(usersum_client) -> None:
    usersum_client.application.config["SITE_PREFIX"] = "/weppcloud"
    index = usersum_client.get("/usersum/").get_data(as_text=True)
    assert 'href="/weppcloud/usersum/features/"' in index
    response = usersum_client.get("/usersum/features")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'href="/weppcloud/usersum/"' in body
    assert 'href="/weppcloud/usersum/view/weppcloud/user-guide.md#feature-maturity-labels"' in body


def test_feature_catalog_empty_and_escaped_metadata(usersum_client, monkeypatch) -> None:
    features = usersum_routes.load_feature_registry()
    monkeypatch.setattr(usersum_routes, "load_feature_registry", lambda: ())
    monkeypatch.setattr(usersum_routes, "load_config_registry", lambda: ())
    body = usersum_client.get("/usersum/features/").get_data(as_text=True)
    assert "No registered features." in body
    assert "No registered interface configurations." in body

    entry = replace(features[0], label='<script>alert("catalog")</script>',
                    internal_reason=None, embargo_until=None, requires_features=())
    monkeypatch.setattr(usersum_routes, "load_feature_registry", lambda: (entry,))
    body = usersum_client.get("/usersum/features/").get_data(as_text=True)
    assert '<script>alert("catalog")</script>' not in body
    assert '&lt;script&gt;alert(&#34;catalog&#34;)&lt;/script&gt;' in body
    assert "Reason:" not in body
    assert "Embargo until:" not in body


def test_feature_catalog_registry_error_is_not_partial_success(usersum_client, monkeypatch) -> None:
    from wepppy.weppcloud.feature_registry.schema import FeatureRegistryValidationError

    def invalid_registry():
        raise FeatureRegistryValidationError("Invalid registry")

    monkeypatch.setattr(usersum_routes, "load_config_registry", invalid_registry)
    with pytest.raises(FeatureRegistryValidationError, match="Invalid registry"):
        usersum_client.get("/usersum/features/")


def test_usersum_view_rewrites_cross_category_markdown_links(usersum_client) -> None:
    response = usersum_client.get("/usersum/view/db/climate_file.parameters.md")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'href="/usersum/doc/usersum.input_file_specifications.cligenparms"' in body


def test_usersum_view_renders_wbt_channel_delineation_alias(usersum_client) -> None:
    usersum_routes._catalog.cache_clear()
    try:
        response = usersum_client.get(
            "/usersum/view/weppcloud/wbt-channel-delineation.md"
        )
    finally:
        usersum_routes._catalog.cache_clear()

    assert response.status_code == 200
    assert "WBT Channel Delineation" in response.get_data(as_text=True)


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


def test_usersum_src_route_rejects_noncanonical_path_variant(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("Admin",))

    canonical = usersum_client.get("/usersum/src/wepppy/weppcloud/routes/usersum/weppcloud/enduser-authoring-guide.md")
    assert canonical.status_code == 200

    noncanonical = usersum_client.get(
        "/usersum/src/wepppy/weppcloud/routes/usersum/weppcloud/../weppcloud/enduser-authoring-guide.md"
    )
    assert noncanonical.status_code == 404


def test_usersum_raw_route_rejects_noncanonical_path_variant(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("Admin",))

    canonical = usersum_client.get("/usersum/raw/wepppy/weppcloud/routes/usersum/weppcloud/enduser-authoring-guide.md")
    assert canonical.status_code == 200
    assert "ENDUSER.md Authoring Guide" in canonical.get_data(as_text=True)

    noncanonical = usersum_client.get(
        "/usersum/raw/wepppy/weppcloud/routes/usersum/weppcloud/../weppcloud/enduser-authoring-guide.md"
    )
    assert noncanonical.status_code == 404


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
    assert (
        'href="/usersum/src/wepppy/weppcloud/routes/usersum/vendor/wepp-forest/'
        'release/wepp_261026_release_notes.md"'
    ) in body

    assert (
        'href="/weppcloud/static/reports/wepp/release-notes/wepp_261029/'
        'wepp_261029_release-notes-consolidated-ed1.pdf"'
    ) in body


def test_usersum_src_route_renders_vendored_wepp_forest_release_notes(usersum_client) -> None:
    response = usersum_client.get(
        "/usersum/src/wepppy/weppcloud/routes/usersum/vendor/wepp-forest/release/wepp_260514_release_notes.md"
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "WEPP Release" in body
    assert "wepp_260514_hill" in body
    assert "wepppy/weppcloud/routes/usersum/vendor/wepp-forest/release/wepp_260514_release_notes.md" in body


def test_usersum_doc_route_renders_disturbed_enduser_guide(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.source.disturbed")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Dominant hillslope severity" in body
    assert "wepppy/nodb/mods/disturbed/ENDUSER.md" in body


def test_disturbed_guide_links_to_current_rankings_report(usersum_client) -> None:
    guide = usersum_client.get('/usersum/doc/usersum.source.disturbed')
    target = '/usersum/doc/usersum.source.disturbed_rankings'
    assert f'href="{target}"' in guide.get_data(as_text=True)
    usersum_client.application.config['USERSUM_REQUIRE_MANIFEST_FOR_SRC'] = 'true'
    report = usersum_client.get(target)
    assert report.status_code == 200
    body = report.get_data(as_text=True)
    assert 'Disturbed Parameterization: Current Canonical Results' in body
    assert 'wepp_261010' in body
    assert 'Full-Record Totals and One-Sided Events' in body
    assert usersum_client.get('/usersum/src/tests/disturbed/analysis_results_current.md').status_code == 200


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


def test_usersum_doc_route_renders_run_ttl_deletion_guide_from_manifest(
    usersum_client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runtime_catalog, "_doc_index_path", lambda _base_dir: tmp_path / "missing-index.json")
    usersum_routes._catalog.cache_clear()
    try:
        response = usersum_client.get("/usersum/doc/usersum.weppcloud.run_ttl_deletion")
    finally:
        usersum_routes._catalog.cache_clear()

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Keep your project from being automatically deleted" in body
    assert "Last Modified" in body


def test_usersum_doc_route_renders_run_ttl_deletion_guide_for_privileged_user(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("PowerUser",))

    response = usersum_client.get("/usersum/doc/usersum.weppcloud.run_ttl_deletion")

    assert response.status_code == 200
    assert "Keep your project from being automatically deleted" in response.get_data(as_text=True)


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
    assert "Requested role filter ceiling is not allowed" in response.get_json()["error"]["message"]


def test_usersum_api_search_role_threshold_includes_lower_roles(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("PowerUser",))

    response = usersum_client.get("/usersum/api/search?q=openet&role=operator")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["total"] >= 1
    assert payload["results"]
    assert any(result["min_role"] == "user" for result in payload["results"])
    assert all(_ROLE_RANK[result["min_role"]] <= _ROLE_RANK["operator"] for result in payload["results"])


def test_usersum_api_search_omitted_role_defaults_to_user_ceiling_for_admin(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("Admin",))

    response = usersum_client.get("/usersum/api/search?q=delineation")
    assert response.status_code == 200

    payload = response.get_json()
    assert all(result["min_role"] == "user" for result in payload["results"])


def test_usersum_api_search_repeated_role_values_use_highest_ceiling(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("Admin",))

    response = usersum_client.get("/usersum/api/search?q=delineation&role=user,developer")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["total"] >= 1
    assert any(result["min_role"] == "operator" for result in payload["results"])


def test_usersum_api_search_poweruser_ceiling_mapping(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("PowerUser",))

    allowed = usersum_client.get("/usersum/api/search?q=openet&role=operator")
    assert allowed.status_code == 200

    forbidden = usersum_client.get("/usersum/api/search?q=openet&role=developer")
    assert forbidden.status_code == 403


def test_usersum_api_search_admin_ceiling_mapping(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("Admin",))

    allowed = usersum_client.get("/usersum/api/search?q=authoring&role=developer")
    assert allowed.status_code == 200

    forbidden = usersum_client.get("/usersum/api/search?q=openet&role=internal")
    assert forbidden.status_code == 403


def test_usersum_api_search_root_ceiling_mapping(
    usersum_client,
    set_usersum_current_user,
) -> None:
    set_usersum_current_user(roles=("Root",))

    response = usersum_client.get("/usersum/api/search?q=openet&role=internal")
    assert response.status_code == 200


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
    assert "<title>Search help</title>" in body
    assert "<h1>Search help</h1>" in body
    assert "/usersum/doc/usersum.weppcloud.mods_overview" in body


def test_usersum_search_page_preserves_selected_role(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("Admin",))

    response = usersum_client.get("/usersum/search?q=openet&role=developer")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'id="usersum-header-role"' in body
    assert '<option value="developer" selected' in body
    assert 'type="hidden" name="role" value="developer"' in body


def test_usersum_shell_nav_respects_selected_role_ceiling(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("Root",))

    user_response = usersum_client.get("/usersum/?role=user")
    assert user_response.status_code == 200
    user_body = user_response.get_data(as_text=True)
    assert "/usersum/doc/usersum.weppcloud.rq_engine" not in user_body
    assert "/usersum/doc/usersum.weppcloud.enduser_authoring_guide" not in user_body

    operator_response = usersum_client.get("/usersum/?role=operator")
    assert operator_response.status_code == 200
    operator_body = operator_response.get_data(as_text=True)
    assert "/usersum/doc/usersum.weppcloud.rq_engine" in operator_body
    assert "/usersum/doc/usersum.weppcloud.enduser_authoring_guide" not in operator_body

    developer_response = usersum_client.get("/usersum/?role=developer")
    assert developer_response.status_code == 200
    developer_body = developer_response.get_data(as_text=True)
    assert "/usersum/doc/usersum.weppcloud.rq_engine" in developer_body
    assert "/usersum/doc/usersum.weppcloud.enduser_authoring_guide" in developer_body


def test_usersum_search_page_uses_error_path_for_unauthorized_role(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("PowerUser",))

    response = usersum_client.get("/usersum/search?q=openet&role=developer")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Requested role filter ceiling is not allowed" in body


def test_usersum_doc_route_renders_markdown(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.mods_overview")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Mods Overview" in body
    assert "wepppy/weppcloud/routes/usersum/weppcloud/mods-overview.md" in body


def test_usersum_doc_route_reports_doc_role_below_breadcrumb(usersum_client) -> None:
    response = usersum_client.get("/usersum/doc/usersum.weppcloud.mods_overview")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    breadcrumb_idx = body.index('class="wc-usersum-breadcrumbs"')
    role_idx = body.index('class="wc-usersum-doc-role"')
    assert breadcrumb_idx < role_idx
    assert "Role: <code>user</code>" in body


def test_usersum_doc_route_reports_operator_role_for_operator_doc(usersum_client, set_usersum_current_user) -> None:
    set_usersum_current_user(roles=("Admin",))

    response = usersum_client.get("/usersum/doc/usersum.weppcloud.rq_engine")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Role: <code>operator</code>" in body


def test_usersum_vendor_route_renders_markdown(usersum_client) -> None:
    response = usersum_client.get(
        "/usersum/vendor/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md"
    )
    assert response.status_code == 404


@pytest.mark.parametrize("query", ["latqcc", "QOFE", "SUBEVENT", "deep percolation", "ET", "H.wat", "H.pass"])
def test_water_guides_are_user_visible_in_fresh_catalog(usersum_client, monkeypatch, tmp_path, query):
    from wepppy.weppcloud.usersum_docs.docs_contracts import load_and_validate_contracts
    from wepppy.weppcloud.usersum_docs.docs_index import build_generated_index, write_generated_index

    root = Path(__file__).resolve().parents[3]
    base = root / "wepppy/weppcloud/routes/usersum"
    contracts = load_and_validate_contracts(base_dir=base, repo_root=root, require_local_files=True, require_vendor_files=True)
    index_path = tmp_path / "docs_index.json"
    write_generated_index(build_generated_index(contracts, repo_root=root), index_path)
    monkeypatch.setattr(runtime_catalog, "_doc_index_path", lambda _base: index_path)
    usersum_client.application.config["USERSUM_SEARCH_DISABLE_POSTGRES"] = "true"
    runtime_catalog.load_runtime_catalog.cache_clear()
    usersum_routes._catalog.cache_clear()
    try:
        response = usersum_client.get("/usersum/api/search", query_string={"q": query, "role": "user"})
        assert response.status_code == 200
        ids = {row["doc_id"] for row in response.get_json()["results"]}
        assert "usersum.weppcloud.water_pass_variables" in ids
        for doc_id in ("water_pass_variables", "water_balance_and_runoff"):
            response = usersum_client.get("/usersum/doc/usersum.weppcloud." + doc_id)
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert "Role:" in body
            assert runtime_catalog.load_runtime_catalog(usersum_base_dir=base, repo_root=root).docs_by_id["usersum.weppcloud." + doc_id]["min_role"] == "user"
            assert "Understanding water balance and runoff" in body
    finally:
        usersum_routes._catalog.cache_clear()
        runtime_catalog.load_runtime_catalog.cache_clear()


@pytest.mark.parametrize('query', ['keep my project', 'stop deletion', 'how long are projects saved'])
def test_automatic_deletion_help_is_discoverable_by_user_task(usersum_client, monkeypatch, tmp_path, query):
    from wepppy.weppcloud.usersum_docs.docs_contracts import load_and_validate_contracts
    from wepppy.weppcloud.usersum_docs.docs_index import build_generated_index, write_generated_index

    root = Path(__file__).resolve().parents[3]
    base = root / 'wepppy/weppcloud/routes/usersum'
    contracts = load_and_validate_contracts(base_dir=base, repo_root=root, require_local_files=True, require_vendor_files=True)
    index_path = tmp_path / 'docs_index.json'
    write_generated_index(build_generated_index(contracts, repo_root=root), index_path)
    monkeypatch.setattr(runtime_catalog, '_doc_index_path', lambda _base: index_path)
    usersum_client.application.config['USERSUM_SEARCH_DISABLE_POSTGRES'] = 'true'
    runtime_catalog.load_runtime_catalog.cache_clear()
    usersum_routes._catalog.cache_clear()
    try:
        response = usersum_client.get('/usersum/api/search', query_string={'q': query, 'role': 'user'})
        assert response.status_code == 200
        assert 'usersum.weppcloud.run_ttl_deletion' in {row['doc_id'] for row in response.json['results']}
        response = usersum_client.get('/usersum/doc/usersum.weppcloud.run_ttl_deletion')
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'Managing projects' in body
        assert 'Disable automatic deletion' in body
        assert 'Automatic deletion is disabled' in body
        assert 'WEPPcloud Help' in body
        assert 'Search help' in body
    finally:
        usersum_routes._catalog.cache_clear()
        runtime_catalog.load_runtime_catalog.cache_clear()


@pytest.fixture()
def adr_root(tmp_path, monkeypatch):
    monkeypatch.setattr(usersum_routes, "_REPO_ROOT", tmp_path)
    root = tmp_path / "docs" / "adrs"
    root.mkdir(parents=True)
    return root


def _adr_links(body):
    return re.findall(r'<a href="[^"]*/usersum/adrs/(ADR-[^"]+\.md)">', body)


def test_adr_catalog_chronology_duplicates_and_freshness(usersum_client, adr_root):
    records = {
        "ADR-0029-old.md": "# Older\nDate: 2026-07-28\n",
        "ADR-0028-new.md": "# Newer\n**Date**: 2026-08-31\n",
        "ADR-0028-tie.md": "# Tie\nStatus: accepted. **Date:** 2026-08-31 UTC\n",
        "ADR-9999-invalid.md": "# Invalid\nDate: 2026-02-30\nDate: 2026-12-31\n",
        "ADR-0001-legacy.md": "Legacy text\nReview Date: 2026-12-31\n## Provenance\nDate: 2026-12-31\n",
    }
    for filename, source in records.items():
        (adr_root / filename).write_text(source)
    body = usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    assert _adr_links(body) == [
        'ADR-0028-tie.md', 'ADR-0028-new.md', 'ADR-0029-old.md',
        'ADR-9999-invalid.md', 'ADR-0001-legacy.md',
    ]
    assert body.count('Date unavailable') == 2
    assert 'Newest recorded date first; undated records last' in body
    added = adr_root / 'ADR-0002-added.md'
    added.write_text('# Added\n- Date: 2026-11-05 Pacific / 2026-11-06 UTC\n')
    assert _adr_links(usersum_client.get('/usersum/adrs').get_data(as_text=True))[0] == added.name
    added.write_text('# Changed\nDate: 2026-01-01\n')
    body = usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    assert 'Changed' in body and _adr_links(body)[3] == added.name
    added.unlink()
    assert added.name not in usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    assert usersum_client.get('/usersum/adrs/' + added.name).status_code == 404


@pytest.mark.parametrize('roles,authenticated', [((), False), (('User',), True), (('PowerUser',), True), (('Root',), True)])
def test_adr_public_rendering_strict_mode_and_prefix(
    usersum_client, adr_root, set_usersum_current_user, roles, authenticated,
):
    set_usersum_current_user(roles=roles, is_authenticated=authenticated)
    app = usersum_client.application
    app.config.update(USERSUM_REQUIRE_MANIFEST_FOR_SRC='true', SITE_PREFIX='/weppcloud')
    name = 'ADR-0001-example.md'
    source = '# Example\nDate: 2026-11-05\n\n## Details\n\nFull **content**.\n\n[Next](ADR-0002-next.md?x=1#details)\n'
    (adr_root / name).write_text(source)
    (adr_root / 'ADR-0002-next.md').write_text('# Next\n\n## Details\n')
    body = usersum_client.get('/usersum/adrs/?role=internal').get_data(as_text=True)
    assert f'href="/weppcloud/usersum/adrs/{name}"' in body
    response = usersum_client.get('/usersum/adrs/' + name + '?role=user')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<strong>content</strong>' in body and 'id="details"' in body
    assert 'href="/weppcloud/usersum/adrs/ADR-0002-next.md?x=1#details"' in body
    assert 'href="/weppcloud/usersum/adrs/"' in body
    assert f'https://github.com/rogerlew/wepppy/blob/master/docs/adrs/{name}' in body
    assert f'href="/weppcloud/usersum/raw/docs/adrs/{name}"' in body
    assert usersum_client.get('/usersum/raw/docs/adrs/' + name).get_data(as_text=True) == source
    assert usersum_client.get('/usersum/src/docs/adrs/' + name).status_code == 404
    assert 'href="/weppcloud/usersum/adrs/"' in usersum_client.get('/usersum/').get_data(as_text=True)


def test_adr_empty_missing_and_hostile_paths(usersum_client, adr_root):
    assert 'No Architecture Decision Records are available.' in usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    outside = adr_root.parent / 'ADR-9999-outside.md'
    outside.write_text('# Private sentinel\n')
    (adr_root / 'ADR-0001-symlink.md').symlink_to(outside)
    (adr_root / 'ADR-0002-directory.md').mkdir()
    (adr_root / 'README.md').write_text('# Ignore\n')
    (adr_root / 'ADR-template.md').write_text('# Ignore\n')
    nested = adr_root / 'nested'
    nested.mkdir()
    (nested / 'ADR-0003-nested.md').write_text('# Ignore\n')
    body = usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    assert not _adr_links(body) and 'Private sentinel' not in body
    for filename in ('ADR-0001-symlink.md', 'ADR-0002-directory.md', 'README.md', 'ADR-template.md',
                     '../ADR-9999-outside.md', '%2e%2e%2fADR-9999-outside.md', 'nested/ADR-0003-nested.md'):
        assert usersum_client.get('/usersum/adrs/' + filename).status_code == 404
    adr_root.rename(adr_root.with_name('saved'))
    assert usersum_client.get('/usersum/adrs/').status_code == 200
    adr_root.symlink_to(adr_root.with_name('saved'), target_is_directory=True)
    assert not _adr_links(usersum_client.get('/usersum/adrs/').get_data(as_text=True))
    assert usersum_client.get('/usersum/adrs/ADR-0001-symlink.md').status_code == 404


def test_adr_title_escape_and_errors(usersum_client, adr_root, monkeypatch):
    path = adr_root / 'ADR-0001-title.md'
    path.write_text('# <script>alert("x")</script> & title\n')
    body = usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    assert '<script>alert("x")</script>' not in body
    assert '&lt;script&gt;' in body and '&amp; title' in body
    path.write_bytes(b'\xff')
    for route in ('/usersum/adrs/', '/usersum/adrs/' + path.name):
        with pytest.raises(UnicodeDecodeError):
            usersum_client.get(route)
    original = Path.read_text
    def denied(self, *args, **kwargs):
        if self == path:
            raise PermissionError('fixture denial')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', denied)
    with pytest.raises(PermissionError, match='fixture denial'):
        usersum_client.get('/usersum/adrs/')


def test_adr_catalog_renders_every_repository_record(usersum_client):
    root = usersum_routes._REPO_ROOT / 'docs' / 'adrs'
    files = sorted(p for p in root.iterdir() if re.fullmatch(r'ADR-[0-9]+-.+\.md', p.name) and p.is_file() and not p.is_symlink())
    response = usersum_client.get('/usersum/adrs/')
    assert response.status_code == 200
    links = _adr_links(response.get_data(as_text=True))
    assert sorted(links) == [p.name for p in files]
    assert len(links) == len(set(links))
    assert links.index('ADR-0028-gridmet-download-retry-concurrency.md') < links.index('ADR-0029-omni-contrast-wepp-executable-inheritance.md')
    for path in files:
        response = usersum_client.get('/usersum/adrs/' + path.name)
        assert response.status_code == 200, path.name
        with usersum_client.application.test_request_context():
            expected = usersum_routes._rewrite_markdown_links(path, usersum_routes._add_heading_anchors(usersum_routes.markdown_to_html(path.read_text())))
        assert expected in response.get_data(as_text=True), path.name


@pytest.mark.parametrize('metadata,expected', [
    ('Date: 2024-02-29', '2024-02-29'),
    ('**Date**: 2026-08-07', '2026-08-07'),
    ('**Date:** 2026-08-07', '2026-08-07'),
    ('- Date: 2026-10-30', '2026-10-30'),
    ('Status: accepted; implemented 2026-10-13. Date: 2026-10-13.', '2026-10-13'),
    ('Date: 2026-10-31 Pacific / 2026-11-01 UTC.', '2026-10-31'),
    ('Date: 2025-02-29\nDate: 2026-01-01', None),
    ('Date: unknown\nDate: 2026-01-01', None),
    ('Review Date: 2026-12-31', None),
    ('Status: Accepted. Review Date: 2027-01-01', None),
    ('Status: Accepted. **Review Date:** 2027-01-01', None),
    ('Status: accepted 2026-10-13', None),
    ('## Provenance\nDate: 2026-01-01', None),
    ('Provenance\n----------\nDate: 2026-01-01', None),
    ('```markdown\nDate: 2026-01-01\n```', None),
])
def test_adr_recorded_date_metadata(usersum_client, adr_root, metadata, expected):
    (adr_root / 'ADR-0001-date.md').write_text('# Date example\n' + metadata + '\n')
    body = usersum_client.get('/usersum/adrs/').get_data(as_text=True)
    if expected:
        assert f'<time datetime="{expected}">{expected}</time>' in body
    else:
        assert 'Date unavailable' in body


def test_adr_link_rewrite_keeps_manifest_precedence(usersum_client, monkeypatch):
    path = usersum_routes._REPO_ROOT / 'docs/adrs/ADR-0001-soil-k-ksat-freeze.md'
    catalog = usersum_routes._catalog()
    doc = next(iter(catalog.docs_by_id.values()))
    monkeypatch.setitem(catalog.docs_by_rel_path, 'docs/adrs/' + path.name, doc)
    with usersum_client.application.test_request_context():
        assert usersum_routes._route_for_repo_markdown(path) == usersum_routes._doc_route_url(doc)
