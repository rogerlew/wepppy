from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import DebugUndefined, Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "templates"
COMMAND_BAR_TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "command_bar" / "templates"
RUN_0_TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "run_0" / "templates"
PURE_TEMPLATES = [
    "controls/path_cost_effective_pure.htm",
    "controls/omni_contrasts_pure.htm",
    "controls/features_export_pure.htm",
    "controls/roads_pure.htm",
    "reports/storm_event_analyzer.htm",
    "run_0/rq-migration-status.htm",
]

pytestmark = pytest.mark.routes


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(
            [
                str(TEMPLATE_ROOT),
                str(COMMAND_BAR_TEMPLATE_ROOT),
                str(RUN_0_TEMPLATE_ROOT),
            ]
        ),
        undefined=DebugUndefined,
    )
    stub_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    stub_unitizer = SimpleNamespace(is_english=False, preferences={})
    stub_migration_status = SimpleNamespace(
        needs_migration=True,
        migrations=[
            SimpleNamespace(
                would_apply=True,
                name="migration_001",
                description="Test migration",
                message="Pending",
            )
        ],
    )
    stub_omni = SimpleNamespace(
        contrast_selection_mode="cumulative",
        control_scenario="uniform_low",
        contrast_scenario="mulch",
        contrast_object_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        contrast_hill_min_slope=None,
        contrast_hill_max_slope=None,
        contrast_select_burn_severities=[],
        contrast_select_topaz_ids=[],
        contrast_pairs=[],
        contrast_geojson_path=None,
        contrast_geojson_name_key="",
        contrast_order_reduction_passes=1,
    )
    stub_watershed = SimpleNamespace(delineation_backend_is_wbt=True)
    env.filters.setdefault("tojson", lambda value: json.dumps(value))
    env.globals.update(
        url_for=lambda *args, **kwargs: "",
        url_for_run=lambda *args, **kwargs: "",
        static_url=lambda *args, **kwargs: "",
        site_prefix="",
        user=stub_user,
        current_user=stub_user,
        ron=SimpleNamespace(mods=set(), runid="test-run", config_stem="test-config", name="", scenario=""),
        current_ron=SimpleNamespace(
            runid="test-run",
            config_stem="test-config",
            nodb_version=None,
            name="",
            scenario="",
            readonly=False,
            public=False,
            pup_relpath=None,
        ),
        get_last_modified=lambda runid: None,
        pup_relpath=None,
        runid="test-run",
        config="test-config",
        unitizer_nodb=stub_unitizer,
        precisions={},
        cls_units=lambda value: value,
        str_units=lambda value: value,
        omni_scenarios=[],
        features_export_submit_url="/rq-engine/api/runs/test-run/test-config/export/features",
        features_export_download_url_template="/runs/test-run/test-config/download/__ARTIFACT_RELPATH__",
        features_export_catalog_payload={"metadata": {}, "family_order": [], "family_labels": {}, "layers": [], "load_error": None},
        features_export_bootstrap_payload={
            "defaults": {"format": "geopackage", "units": "project", "crs": "wgs", "output_scopes": ["baseline"]},
            "profiles": {"gpkg_adjacent": {"layers": []}},
            "omni": {"scenarios": [], "contrasts": []},
            "swat": {"preferred_run_id": "latest", "runs": [], "tables_by_run": {}, "all_tables": []},
        },
        features_export_utm_epsg=None,
        omni=stub_omni,
        watershed=stub_watershed,
        base_scenario_label="Base",
        migration_status=stub_migration_status,
        can_migrate=True,
        is_readonly=False,
        is_owner=True,
        is_admin=False,
    )
    return env


@pytest.mark.parametrize("template_name", PURE_TEMPLATES)
def test_pure_control_renders(template_name: str, jinja_env: Environment) -> None:
    template = jinja_env.get_template(template_name)
    template.render()


def test_roads_template_uses_standard_control_shell_layout(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/roads_pure.htm")
    rendered = template.render()

    assert '<form id="roads_form"' in rendered
    assert 'class="wc-control' in rendered
    assert 'id="roads_geojson_file"' in rendered
    assert 'data-roads-action="upload"' in rendered
    assert 'id="roads_geojson_file-progress"' in rendered
    assert 'class="wc-upload-progress"' in rendered
    assert 'id="roads_upload_message"' in rendered
    assert 'id="roads_prepare_segments"' in rendered
    assert 'id="run_roads_wepp"' in rendered
    assert "Upload Roads GeoJSON" in rendered
    assert "Prepare Segment Candidates" in rendered
    assert "lowpoint decisions" in rendered
    assert 'id="roads-results"' in rendered
    assert 'id="run_roads_lock"' in rendered
    assert 'id="roads_status"' in rendered
    assert 'id="roads_info"' in rendered
    assert 'id="roads_stacktrace"' in rendered
    assert "pure-u-md-1-2" not in rendered


def test_roads_summary_report_template_renders_with_base_layout(jinja_env: Environment) -> None:
    template = jinja_env.get_template("reports/roads/summary.htm")
    rendered = template.render(
        roads_status={},
        roads_summary={},
        roads_run_summary={},
        roads_report_resources={},
        roads_report_links=[],
        roads_resource_links=[],
    )

    assert "Roads Run Results" in rendered
    assert "<!doctype html>" in rendered


def test_roads_reports_control_template_renders_with_link_panel(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/roads_reports.htm")
    rendered = template.render(
        roads_status={},
        roads_summary={},
        roads_run_summary={},
        roads_report_resources={},
        roads_report_links=[],
        roads_resource_links=[],
        run_results_title="Run Results",
    )

    assert "Roads Results" in rendered
    assert "Run Results" in rendered


def test_omni_contrasts_template_shows_user_defined_limit_hint(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/omni_contrasts_pure.htm")
    rendered = template.render(omni_user_defined_contrast_limit=200)

    assert "capped at 200 total contrast runs (contrast pairs x groups)." in rendered


def test_frost_advanced_template_renders_wepp_variable_labels(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/wepp_pure_advanced_options/frost.htm")
    wepp = SimpleNamespace(
        run_frost=True,
        frost_opts=SimpleNamespace(
            wintRed=1,
            fineTop=10,
            fineBot=10,
            ksnowf=1.0,
            kresf=1.0,
            ksoilf=1.0,
            kfactor1=0.00001,
            kfactor2=0.00001,
            kfactor3=0.5,
        ),
    )
    rendered = template.render(wepp=wepp)

    for label in (
        "wintRed",
        "fineTop",
        "fineBot",
        "ksnowf",
        "kresf",
        "ksoilf",
        "kfactor(1)",
        "kfactor(2)",
        "kfactor(3)",
    ):
        assert label in rendered

    for field_id in ("frost_opts_kfactor1", "frost_opts_kfactor2", "frost_opts_kfactor3"):
        match = re.search(rf'id="{field_id}"[^>]*>', rendered)
        assert match is not None
        assert "min=" not in match.group(0)


def test_interchange_advanced_template_renders_delete_after_interchange_checkbox(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/wepp_pure_advanced_options/interchange.htm")
    rendered = template.render(wepp=SimpleNamespace(delete_after_interchange=True))

    assert "Delete raw WEPP outputs after successful interchange conversion" in rendered
    assert 'id="delete_after_interchange"' in rendered
    assert "checked" in rendered


def test_clip_soils_advanced_template_renders_dual_depth_controls(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/wepp_pure_advanced_options/clip_soils_depth.htm")
    rendered = template.render(
        soils=SimpleNamespace(
            clip_soils=True,
            clip_soils_depth=300,
            clip_soils_minimum=True,
            clip_soils_minimum_depth=150,
            initial_sat=0.75,
        )
    )

    assert "Clip Soils Maximum Depth" in rendered
    assert "Soils Maximum Depth" in rendered
    assert "Clip Soils Minimum Depth" in rendered
    assert "Soils Minimum Depth" in rendered
    assert 'id="clip_soils"' in rendered
    assert 'id="clip_soils_depth"' in rendered
    assert 'id="clip_soils_minimum"' in rendered
    assert 'id="clip_soils_minimum_depth"' in rendered


def test_poweruser_panel_parquet_table_links_do_not_append_trailing_slash(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/poweruser_panel.htm")

    def _url_for_run(endpoint: str, **values) -> str:
        if endpoint != "browse.browse_tree":
            return f"/mock/{endpoint}"
        subpath = (values.get("subpath") or "").lstrip("/")
        base = f"/weppcloud/runs/{values['runid']}/{values['config']}/browse/"
        return f"{base}{subpath}" if subpath else base

    rendered = template.render(
        url_for_run=_url_for_run,
        runid="test-run",
        config="test-config",
        browse_watershed_hillslopes_parquet="watershed/hillslopes.parquet",
        browse_watershed_channels_parquet="watershed/channels.parquet",
        browse_landuse_parquet="landuse/landuse.parquet",
        browse_soils_parquet="soils/soils.parquet",
    )

    assert 'href="/weppcloud/runs/test-run/test-config/browse/watershed/hillslopes.parquet"' in rendered
    assert 'href="/weppcloud/runs/test-run/test-config/browse/watershed/channels.parquet"' in rendered
    assert 'href="/weppcloud/runs/test-run/test-config/browse/landuse/landuse.parquet"' in rendered
    assert 'href="/weppcloud/runs/test-run/test-config/browse/soils/soils.parquet"' in rendered


def test_run_header_hides_team_public_readonly_for_anonymous(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    anon_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=anon_user,
        current_user=anon_user,
        request=request,
    )

    assert 'data-modal-open="teamModal"' not in rendered
    assert 'id="checkbox_readonly"' not in rendered
    assert 'id="checkbox_public"' not in rendered


def test_interfaces_template_shows_login_bypass_banner_for_anonymous_user(jinja_env: Environment) -> None:
    template = jinja_env.get_template("interfaces.htm")
    anon_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "security.login":
            return f"/login?next={values.get('next', '')}"
        if endpoint == "weppcloud_site.interfaces":
            return "/interfaces/"
        return f"/mock/{endpoint}"

    rendered = template.render(
        user=anon_user,
        current_user=anon_user,
        url_for=_url_for,
        runs_counter=Counter(),
        commafy=lambda value: f"{value:,}",
        cap_base_url="/cap",
        cap_asset_base_url="/cap/assets",
        cap_site_key="test-site-key",
        rq_engine_token="token",
    )

    assert ">Login</a> to Bypass Captchas" in rendered
    assert 'href="/login?next=/interfaces/"' in rendered
    assert 'name="rq_token"' not in rendered


def test_interfaces_template_hides_login_bypass_banner_for_authenticated_user(jinja_env: Environment) -> None:
    template = jinja_env.get_template("interfaces.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "security.login":
            return f"/login?next={values.get('next', '')}"
        if endpoint == "weppcloud_site.interfaces":
            return "/interfaces/"
        return f"/mock/{endpoint}"

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        url_for=_url_for,
        runs_counter=Counter(),
        commafy=lambda value: f"{value:,}",
        rq_engine_token="token",
    )

    assert "Login to Bypass Captchas" not in rendered
    assert 'href="/login?next=/interfaces/"' not in rendered
    assert 'name="rq_token"' not in rendered


def test_run_header_shows_team_public_readonly_for_authenticated_user(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
    )

    assert 'data-modal-open="teamModal"' in rendered
    assert 'id="checkbox_readonly"' in rendered
    assert 'id="checkbox_public"' in rendered


def test_run_header_hides_rusle_mod_when_disturbed_not_enabled(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
    )

    assert 'data-project-mod="rusle"' not in rendered


def test_run_header_shows_rusle_mod_when_disturbed_enabled(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=["disturbed", "rusle"],
        watershed=SimpleNamespace(delineation_backend_is_wbt=True),
    )

    assert 'data-project-mod="rusle"' in rendered


def test_run_header_hides_rusle_mod_for_topaz_backend(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=["disturbed", "rusle"],
        watershed=SimpleNamespace(delineation_backend_is_wbt=False),
    )

    assert 'data-project-mod="rusle"' not in rendered


def test_runs0_template_places_rusle_after_wepp_sections() -> None:
    template_path = RUN_0_TEMPLATE_ROOT / "runs0_pure.htm"
    source = template_path.read_text(encoding="utf-8")

    wepp_nav_index = source.index('<a href="#wepp" class="nav-link">WEPP</a>')
    rusle_nav_index = source.index('<a href="#rusle" class="nav-link">Gridded RUSLE</a>')
    assert wepp_nav_index < rusle_nav_index

    wepp_section_index = source.index('<section id="wepp" class="wc-stack">')
    rusle_section_index = source.index('<div data-mod-section="rusle"')
    assert wepp_section_index < rusle_section_index


def test_runs0_template_places_roads_after_debris_flow() -> None:
    template_path = RUN_0_TEMPLATE_ROOT / "runs0_pure.htm"
    source = template_path.read_text(encoding="utf-8")

    debris_nav_index = source.index('<a href="#debris-flow" class="nav-link">Debris Flow</a>')
    roads_nav_index = source.index('<a href="#roads" class="nav-link">Roads</a>')
    dss_nav_index = source.index('<a href="#dss-export" class="nav-link">DSS Export</a>')
    assert debris_nav_index < roads_nav_index < dss_nav_index

    debris_section_index = source.index('<section id="debris-flow" class="wc-stack">')
    roads_section_index = source.index('<div data-mod-section="roads"')
    dss_section_index = source.index('<div data-mod-section="dss_export"')
    assert debris_section_index < roads_section_index < dss_section_index


def test_runs0_template_places_features_export_between_roads_and_dss() -> None:
    template_path = RUN_0_TEMPLATE_ROOT / "runs0_pure.htm"
    source = template_path.read_text(encoding="utf-8")

    roads_nav_index = source.index('<a href="#roads" class="nav-link">Roads</a>')
    features_nav_index = source.index('<a href="#features-export" class="nav-link">Features Export</a>')
    dss_nav_index = source.index('<a href="#dss-export" class="nav-link">DSS Export</a>')
    assert roads_nav_index < features_nav_index < dss_nav_index

    roads_section_index = source.index('<div data-mod-section="roads"')
    features_section_index = source.index('<div data-mod-section="features_export"')
    dss_section_index = source.index('<div data-mod-section="dss_export"')
    assert roads_section_index < features_section_index < dss_section_index


def test_run_header_includes_features_export_mod_toggle(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
    )

    assert 'data-project-mod="features_export"' in rendered


def test_features_export_template_exposes_required_dom_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/features_export_pure.htm")
    rendered = template.render(
        features_export_submit_url="/rq-engine/api/runs/test-run/test-config/export/features",
        features_export_download_url_template="/runs/test-run/test-config/download/__ARTIFACT_RELPATH__",
        features_export_catalog_payload={
            "metadata": {},
            "family_order": ["watershed"],
            "family_labels": {"watershed": "Watershed"},
            "layers": [],
            "load_error": None,
        },
        features_export_bootstrap_payload={
            "defaults": {"format": "geopackage", "units": "project", "crs": "wgs", "output_scopes": ["baseline"]},
            "profiles": {"gpkg_adjacent": {"layers": []}},
            "omni": {"scenarios": [], "contrasts": []},
            "swat": {"preferred_run_id": "latest", "runs": [], "tables_by_run": {}, "all_tables": []},
        },
        features_export_utm_epsg=None,
    )

    for token in (
        'form id="features_export_form"',
        'id="features_export_catalog_data"',
        'id="features_export_bootstrap_data"',
        'data-features-export-group="settings"',
        'data-features-export-group="summary"',
        'data-features-export-group="catalog"',
        'data-features-export-group="scopes"',
        'data-features-export-group="temporal"',
        'data-features-export-group="omni"',
        'data-features-export-group="swat"',
        'data-features-export-group="actions"',
        'data-features-export-action="load-defaults"',
        'id="features_export_results_panel"',
        'id="features_export_status_panel"',
        'id="features_export_status_log"',
        'class="wc-status-panel"',
        'class="wc-status-panel__log"',
        'id="features_export_stacktrace_panel"',
        'id="features_export_stacktrace"',
        'id="hint_run_features_export"',
    ):
        assert token in rendered

    crs_index = rendered.index('data-features-export-field="crs"')
    year_selection_index = rendered.index('for="features_export_temporal_year_selection"')
    temporal_group_index = rendered.index('data-features-export-group="temporal"')
    assert crs_index < year_selection_index < temporal_group_index
