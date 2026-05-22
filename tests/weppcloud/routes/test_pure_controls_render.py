from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import DebugUndefined, Environment, FileSystemLoader

from wepppy.weppcloud.feature_registry.runtime import (
    config_maturity_badge,
    load_config_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "templates"
COMMAND_BAR_TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "command_bar" / "templates"
RUN_0_TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "run_0" / "templates"
PURE_TEMPLATES = [
    "controls/path_cost_effective_pure.htm",
    "controls/omni_contrasts_pure.htm",
    "controls/geneva_pure.htm",
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
        usersum_doc_link=lambda category, filename, label, *args, **kwargs: (
            f'<a href="/usersum/view/{category}/{filename}" target="_blank" rel="noopener">📄 {label}</a>'
        ),
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
        features_export_profile_resolve_url="/rq-engine/api/runs/test-run/test-config/export/features/profile/resolve",
        features_export_download_url_template="/runs/test-run/test-config/download/__ARTIFACT_RELPATH__",
        features_export_catalog_payload={"metadata": {}, "family_order": [], "family_labels": {}, "layers": [], "load_error": None},
        features_export_bootstrap_payload={
            "defaults": {"format": "geopackage", "units": "project", "crs": "wgs", "output_scopes": ["baseline"]},
            "profiles": {"post_wepp": {"layers": []}},
            "profile_buttons": [{"key": "post_wepp", "label": "Post Wepp"}],
            "default_profile_key": "post_wepp",
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


@pytest.mark.parametrize(
    ("template_name", "title_text", "run_link_class"),
    [
        ("controls/landuse_user_defined.htm", "User-Defined Landuse Catalog", "lu-catalog__run-link"),
        ("controls/landuse_map.htm", "Landuse Map Editor", "lu-map__run-link"),
    ],
)
def test_landuse_editor_templates_render_run_link_in_title_meta(
    template_name: str,
    title_text: str,
    run_link_class: str,
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template(template_name)
    rendered = template.render(
        runid="demo-run",
        config="demo-config",
        url_for_run=lambda endpoint, **kwargs: f"/runs/{kwargs['runid']}/{kwargs['config']}",
        list_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/catalog",
        upload_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/upload",
        delete_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/delete",
        update_description_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/update-description",
        snapshot_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/snapshot",
        save_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/save",
        clear_override_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/clear-override",
        session_token_url="/rq-engine/api/runs/demo-run/demo-config/session-token",
        catalog_items=[],
        snapshot={"rows": [], "management_options": [], "lookup_sha256": None},
    )

    assert title_text in rendered
    assert f'class="{run_link_class}"' in rendered
    assert ">demo-run</a>" in rendered
    assert 'href="/runs/demo-run/demo-config"' in rendered


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


def test_geneva_template_renders_parameterized_controls_and_standard_button_row(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/geneva_pure.htm")
    rendered = template.render()

    assert '<form id="geneva_form"' in rendered
    assert "Configure Geneva runoff parameters" in rendered
    assert 'id="geneva_controller_data"' in rendered
    assert 'data-geneva-config' in rendered
    assert 'id="geneva_save_config"' not in rendered
    assert 'id="geneva_refresh_state"' not in rendered
    assert 'id="geneva_prepare_hrus"' not in rendered
    assert 'id="geneva_build_frequency_panel"' not in rendered
    assert 'id="geneva_run_batch"' in rendered
    assert 'id="hint_run_geneva_run_workflow"' in rendered
    assert 'id="hint_run_geneva"' in rendered
    assert 'id="geneva_results"' not in rendered
    assert 'id="geneva-results"' in rendered
    assert "Edit Geneva CN Table" in rendered
    assert "Query Geneva Summary" in rendered
    assert "View Geneva Report" in rendered
    assert "Geneva enabled" not in rendered
    assert "pure-button-primary" in rendered
    assert "wc-button-row--full" not in rendered

    source = (TEMPLATE_ROOT / "controls/geneva_pure.htm").read_text(encoding="utf-8")
    assert "button_row(full_width=True)" not in source
    assert '"state_url": rq_base ~ "/geneva/state"' in source
    assert '"run_workflow_url": rq_base ~ "/geneva/run-workflow"' in source
    assert '{% set rq_base = "/rq-engine/api/runs/" ~ (runid | urlencode) ~ "/" ~ (config | urlencode) %}' in source
    assert 'data-geneva-action="run-workflow"' in source


def test_geneva_summary_report_template_embeds_single_json_payload(jinja_env: Environment) -> None:
    template = jinja_env.get_template("reports/geneva/summary.htm")
    summary_payload = {
        "schema_version": 1,
        "filters": {
            "datasource_id": "all",
            "ari_years": [10],
            "measure": "peak_discharge",
        },
        "filter_options": {
            "datasource_ids": ["all", "cligen_freq", "noaa14_pds"],
            "datasource_availability": {"cligen_freq": True, "noaa14_pds": False},
            "ari_years": [10, 25],
            "measures": ["peak_discharge", "runoff_depth", "runoff_volume"],
            "duration_minutes": [30, 60],
        },
        "assumptions": {
            "arc_condition": "arc_ii",
            "storm_distribution_assumption": "neh4_type_b",
            "uniform_rainfall_assumed": True,
        },
        "chart": {
            "x_axis": "intensity_mm_per_hr",
            "y_axis": "selected_measure",
            "series_grouping": "ari_years",
            "marker_grouping": "duration_minutes",
            "series": [],
        },
        "selected_storm_id": None,
        "event_table": [],
        "warnings": [],
        "errors": [],
    }
    rendered = template.render(
        runid="run-1",
        config="cfg",
        summary_payload=summary_payload,
    )

    assert rendered.count('id="geneva-summary-payload"') == 1
    assert 'type="application/json"' in rendered
    assert '"storm_distribution_assumption": "neh4_type_b"' in rendered
    assert 'id="geneva-summary-datasource"' in rendered
    assert 'id="geneva-summary-ari"' in rendered
    assert 'id="geneva-summary-measure"' in rendered
    assert 'data-query-url="/runs/run-1/cfg/query/geneva/summary"' in rendered
    assert 'class="wc-panel wc-stack"' in rendered
    assert 'data-geneva-summary-chart' in rendered
    assert 'data-geneva-summary-event-body' in rendered
    assert 'class="wc-table wc-table--dense sortable"' in rendered
    assert '<th scope="col">Status</th>' not in rendered
    assert 'data-sort-type="numeric">Intensity (mm/hr)</th>' in rendered
    assert 'data-sort-type="numeric">Peak Discharge</th>' in rendered


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


def test_landuse_template_disables_single_mode_for_mofe(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/landuse_pure.htm")
    rendered = template.render(
        landuse=SimpleNamespace(
            mode=SimpleNamespace(value=1),
            nlcd_db="nlcd/2024",
            single_selection="42",
            mofe_buffer_selection="42",
            user_defined_landcover_fn=None,
            mapping="disturbed",
        ),
        landuseoptions=[{"Key": "42", "Description": "Forest"}],
        landuse_management_mapping_options=[{"Key": "disturbed", "Description": "Disturbed"}],
        wepp=SimpleNamespace(multi_ofe=True),
        ron=SimpleNamespace(mods=set()),
    )

    assert 'class="wc-control__description"' in rendered
    assert "MOFE projects require a gridded landuse map; Single landuse for watershed is disabled." in rendered
    assert "MOFE requires a gridded landuse map." in rendered

    single_radio = re.search(r'id="landuse_mode1"[^>]*>', rendered)
    assert single_radio is not None
    assert "checked" in single_radio.group(0)
    assert "disabled" in single_radio.group(0)
    assert 'aria-disabled="true"' in single_radio.group(0)

    single_select = re.search(r'id="landuse_single_selection"[^>]*>', rendered)
    assert single_select is not None
    assert "disabled" in single_select.group(0)


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
            rosetta_wc_fc_from_disturbed_bd_override=True,
            initial_sat=0.75,
        )
    )

    assert "Clip Soils Maximum Depth" in rendered
    assert "Soils Maximum Depth" in rendered
    assert "Clip Soils Minimum Depth" in rendered
    assert "Soils Minimum Depth" in rendered
    assert "Estimate wc and fc using Rosetta when soils have bd override" in rendered
    assert 'id="clip_soils"' in rendered
    assert 'id="clip_soils_depth"' in rendered
    assert 'id="clip_soils_minimum"' in rendered
    assert 'id="clip_soils_minimum_depth"' in rendered
    assert 'id="rosetta_wc_fc_from_disturbed_bd_override"' in rendered


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


def test_poweruser_panel_no_longer_renders_disturbed_lookup_actions(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/poweruser_panel.htm")
    rendered = template.render(
        ron=SimpleNamespace(
            mods={"disturbed"},
            runid="test-run",
            config_stem="test-config",
            name="",
            scenario="",
            profile_recorder_assembler_enabled=False,
        ),
    )

    assert "Modify Disturbed Parameters" not in rendered
    assert "Reset Disturbed Parameters" not in rendered
    assert "Load Extended Disturbed Parameters" not in rendered
    assert "Disturbed Parameters Doc" not in rendered
    assert 'data-disturbed-action="reset-lookup"' not in rendered
    assert 'data-disturbed-action="load-extended-lookup"' not in rendered


def test_poweruser_panel_hides_run_token_controls_for_non_admin(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/poweruser_panel.htm")
    non_admin = SimpleNamespace(has_role=lambda role: False, roles=["User"], is_authenticated=True)
    rendered = template.render(current_user=non_admin, user=non_admin)

    assert "Mint Run Token" not in rendered
    assert 'data-run-token-root' not in rendered
    assert 'data-run-token-action="mint"' not in rendered


def test_poweruser_panel_renders_landuse_catalog_and_map_links(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/poweruser_panel.htm")

    def _url_for_run(endpoint: str, **values) -> str:
        return f"/runs/{values.get('runid', 'test-run')}/{values.get('config', 'test-config')}/{endpoint}"

    rendered = template.render(
        runid="test-run",
        config="test-config",
        url_for_run=_url_for_run,
    )

    assert "Landuse User-Defined" in rendered
    assert "Landuse Map" in rendered
    assert "/runs/test-run/test-config/landuse.view_landuse_user_defined" in rendered
    assert "/runs/test-run/test-config/landuse.view_landuse_map" in rendered


def test_poweruser_panel_shows_run_token_controls_for_admin(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/poweruser_panel.htm")
    admin_user = SimpleNamespace(
        has_role=lambda role: role in {"Admin", "Root"},
        roles=["Admin"],
        is_authenticated=True,
    )

    def _url_for_run(endpoint: str, **values) -> str:
        if endpoint == "user.mint_run_token":
            return f"/runs/{values['runid']}/{values['config']}/mint-run-token"
        return f"/mock/{endpoint}"

    rendered = template.render(
        current_user=admin_user,
        user=admin_user,
        runid="test-run",
        config="test-config",
        url_for_run=_url_for_run,
    )

    assert "Mint Run Token" in rendered
    assert 'data-run-token-root' in rendered
    assert 'data-mint-endpoint="/runs/test-run/test-config/mint-run-token"' in rendered
    assert 'data-run-token-action="mint"' in rendered
    assert 'data-run-token-action="copy-token"' in rendered


def test_disturbed_modal_renders_requested_controls(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/disturbed_modal.htm")
    rendered = template.render(
        runid="test-run",
        config="test-config",
        ron=SimpleNamespace(mods={"disturbed"}, runid="test-run", config_stem="test-config"),
    )

    assert 'id="disturbedModal"' in rendered
    assert "Landsoil Lookup Parameter Table" in rendered
    assert "Reset Base Landsoil Lookup Table" in rendered
    assert "Load Extended Landsoil Lookup Table" in rendered
    assert "Delete Extended Landsoil Lookup Table" in rendered
    assert 'data-disturbed-action="sync-base-to-extended-lookup"' in rendered
    assert 'data-disturbed-lookup-variant' in rendered
    assert rendered.count('data-disturbed-requires-extended="true"') >= 4
    assert "Extended" in rendered
    assert "Base uses the canonical lookup table." in rendered
    assert "Restore the base lookup CSV to default values." in rendered
    assert "Regenerate the extended table from the current base table values." in rendered
    assert "Modify Base Table" in rendered
    assert "Modify Extended Table" in rendered
    assert ".disturbed-panel__modify-link {" in rendered
    assert "width: 100%;" in rendered
    assert 'href="/usersum/view/weppcloud/disturbed-land-soil-lookup.md"' in rendered
    assert "📄 Disturbed Land Soil Lookup Table Guidance" in rendered


def test_base_report_uses_modal_manager_hooks_for_disturbed_controls(jinja_env: Environment) -> None:
    template = jinja_env.get_template("reports/_base_report.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"disturbed"}, runid="test-run", config_stem="test-config", name="", scenario=""),
        request=SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"}),
    )

    assert 'data-modal-open="puModal"' in rendered
    assert 'data-modal-open="disturbedModal"' in rendered
    assert 'data-modal-open="unitizerModal"' in rendered
    assert 'data-command="open-poweruser"' not in rendered
    assert 'data-command="open-disturbed"' not in rendered
    assert 'data-command="open-unitizer"' not in rendered
    assert "toggleLegacyModal(" not in rendered


def test_page_container_includes_disturbed_modal(jinja_env: Environment) -> None:
    template = jinja_env.get_template("reports/_page_container.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"disturbed"}, runid="test-run", config_stem="test-config", name="", scenario=""),
        current_ron=SimpleNamespace(
            mods={"disturbed"},
            runid="test-run",
            config_stem="test-config",
            nodb_version=None,
            name="",
            scenario="",
            readonly=False,
            public=False,
            pup_relpath=None,
        ),
    )

    assert 'id="disturbedModal"' in rendered


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
        rq_engine_token="token",
    )

    assert "Login to Bypass Captchas" not in rendered
    assert 'href="/login?next=/interfaces/"' not in rendered
    assert 'name="rq_token"' not in rendered


def test_interfaces_template_renders_earth_launch_card(jinja_env: Environment) -> None:
    template = jinja_env.get_template("interfaces.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return f"/static/{values.get('filename', '')}"
        return f"/mock/{endpoint}"

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        url_for=_url_for,
        rq_engine_token="token",
    )

    assert "WEPPcloud-(Un)Disturbed-Earth" in rendered
    assert "images/interfaces/earth-interface.png" in rendered
    assert 'name="config" value="earth"' in rendered
    assert "Earth interface guidance" in rendered
    assert "WEPPcloud-WBT" in rendered
    assert rendered.index("WEPPcloud-AU") < rendered.index("WEPPcloud-(Un)Disturbed-Earth") < rendered.index("WEPPcloud-RHEM")


def test_interfaces_template_renders_registry_maturity_badges(jinja_env: Environment) -> None:
    template = jinja_env.get_template("interfaces.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return f"/static/{values.get('filename', '')}"
        return f"/mock/{endpoint}"

    config_entries = load_config_registry()
    config_registry_map = {
        entry.id: SimpleNamespace(id=entry.id)
        for entry in config_entries
    }
    config_maturity_labels = {
        entry.id: config_maturity_badge(entry)
        for entry in config_entries
    }

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        url_for=_url_for,
        rq_engine_token="token",
        config_registry_map=config_registry_map,
        config_maturity_labels=config_maturity_labels,
    )

    assert rendered.count('aria-label="Interface maturity:') == 9
    assert rendered.count('href="/mock/usersum.view_markdown#feature-maturity-labels"') == 9
    assert 'name="config" value="disturbed9002_wbt"' in rendered

    disturbed_section = re.search(
        r'<section class="wc-panel" aria-labelledby="section-disturbed">(.|\n)*?</section>',
        rendered,
    )
    assert disturbed_section is not None
    assert disturbed_section.group(0).count('aria-label="Interface maturity:') == 1

    reveg_section = re.search(
        r'<section class="wc-panel" aria-labelledby="section-revegetation">(.|\n)*?</section>',
        rendered,
    )
    assert reveg_section is not None
    assert reveg_section.group(0).count('aria-label="Interface maturity:') == 1

    legacy_section = re.search(
        r'<section class="wc-panel wc-stack" aria-labelledby="section-legacy">(.|\n)*?</section>',
        rendered,
    )
    assert legacy_section is not None
    assert legacy_section.group(0).count('aria-label="Interface maturity:') == 2


def test_interfaces_template_applies_visible_config_filter(jinja_env: Environment) -> None:
    template = jinja_env.get_template("interfaces.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return f"/static/{values.get('filename', '')}"
        return f"/mock/{endpoint}"

    config_entries = load_config_registry()
    config_registry_map = {
        entry.id: SimpleNamespace(id=entry.id)
        for entry in config_entries
    }
    config_maturity_labels = {
        entry.id: config_maturity_badge(entry)
        for entry in config_entries
    }

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        url_for=_url_for,
        rq_engine_token="token",
        config_registry_map=config_registry_map,
        config_maturity_labels=config_maturity_labels,
        visible_config_ids={"disturbed9002_wbt"},
    )

    assert 'name="config" value="disturbed9002_wbt"' in rendered
    assert 'name="config" value="disturbed9002"' not in rendered
    assert 'name="config" value="reveg"' not in rendered


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


def test_run_header_renders_registry_maturity_badges(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: role == "Admin", roles=["Admin"], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=["openet_ts", "disturbed"],
        run_config_maturity_label="Stable",
        run_config_maturity_href="/mock/usersum.view_markdown#feature-maturity-labels",
        header_mod_options=[
            {"id": "openet_ts", "label": "OpenET Time Series", "maturity_badge": "Preview"},
            {"id": "rusle", "label": "RUSLE", "maturity_badge": "Preview"},
        ],
    )

    assert "OpenET Time Series" in rendered
    assert "RUSLE" in rendered
    assert "Preview" in rendered
    assert "Stable" in rendered
    assert 'href="/mock/usersum.view_markdown#feature-maturity-labels"' in rendered


def test_feature_control_shell_renders_maturity_pill_next_to_label(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/rap_ts_pure.htm")
    rendered = template.render(
        rap_schedule=[],
        feature_maturity_labels={"rap_ts": "Stable"},
        maturity_definition_href="/mock/usersum.view_markdown#feature-maturity-labels",
    )

    assert "RAP Time Series Acquisition" in rendered
    assert "Stable" in rendered
    assert 'href="/mock/usersum.view_markdown#feature-maturity-labels"' in rendered


def test_feature_control_shell_defaults_maturity_pill_link(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/rap_ts_pure.htm")
    rendered = template.render(
        rap_schedule=[],
        feature_maturity_labels={"rap_ts": "Stable"},
    )

    assert "Stable" in rendered
    assert 'href="#feature-maturity-labels"' in rendered


def test_run_header_hides_rusle_mod_when_disturbed_not_enabled(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
        header_mod_options=[{"id": "features_export", "label": "Features Export"}],
    )

    assert 'data-project-mod="rusle"' not in rendered
    assert 'data-modal-open="disturbedModal"' not in rendered


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
        header_mod_options=[
            {"id": "rusle", "label": "RUSLE", "maturity_badge": "Preview"},
        ],
    )

    assert 'data-project-mod="rusle"' in rendered
    assert 'data-modal-open="disturbedModal"' in rendered


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


def test_runs0_template_places_geneva_between_roads_and_features_export() -> None:
    template_path = RUN_0_TEMPLATE_ROOT / "runs0_pure.htm"
    source = template_path.read_text(encoding="utf-8")

    roads_nav_index = source.index('<a href="#roads" class="nav-link">Roads</a>')
    geneva_nav_index = source.index('<a href="#geneva" class="nav-link">Geneva</a>')
    features_nav_index = source.index('<a href="#features-export" class="nav-link">Features Export</a>')
    assert roads_nav_index < geneva_nav_index < features_nav_index

    roads_section_index = source.index('<div data-mod-section="roads"')
    geneva_section_index = source.index('<div data-mod-section="geneva"')
    features_section_index = source.index('<div data-mod-section="features_export"')
    assert roads_section_index < geneva_section_index < features_section_index


def test_run_header_includes_features_export_mod_toggle(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
        header_mod_options=[{"id": "features_export", "label": "Features Export"}],
    )

    assert 'data-project-mod="features_export"' in rendered


def test_run_header_includes_geneva_mod_toggle(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
        header_mod_options=[{"id": "geneva", "label": "Geneva"}],
    )

    assert 'data-project-mod="geneva"' in rendered


def test_features_export_template_exposes_required_dom_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/features_export_pure.htm")
    rendered = template.render(
        features_export_submit_url="/rq-engine/api/runs/test-run/test-config/export/features",
        features_export_profile_resolve_url="/rq-engine/api/runs/test-run/test-config/export/features/profile/resolve",
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
            "profiles": {"post_wepp": {"layers": []}},
            "profile_buttons": [{"key": "post_wepp", "label": "Post Wepp"}],
            "default_profile_key": "post_wepp",
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
        'data-features-export-group="catalog"',
        'data-features-export-group="scenario-catalog"',
        'data-features-export-group="scopes"',
        'data-features-export-group="temporal"',
        'data-features-export-group="omni"',
        'data-features-export-group="swat"',
        'data-features-export-group="summary"',
        'data-features-export-group="actions"',
        'data-features-export-action="load-profile-preset"',
        'data-features-export-action="load-profile-text"',
        'data-features-export-field="profile-text"',
        'data-features-export-field="tabular-concatenate-tables"',
        'data-features-export-field="tabular-temporal-layout"',
        'data-features-export-tabular-options',
        'data-features-export-geometry-options',
        'data-features-export-validation-alert',
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
    assert "data-features-export-temporal-year-options hidden" not in rendered
    assert "Temporal mode is selected per dataset row." not in rendered

    summary_group_index = rendered.index('data-features-export-group="summary"')
    export_button_index = rendered.index('id="btn_run_features_export"')
    assert summary_group_index < export_button_index
    assert "Unitizer Selections" in rendered
    assert "Unitzer Selections" not in rendered


def test_report_templates_use_semantic_copy_buttons() -> None:
    template_paths = [
        TEMPLATE_ROOT / "reports/wepp/prep_details.htm",
        TEMPLATE_ROOT / "reports/wepp/frq_flood.htm",
        TEMPLATE_ROOT / "reports/wepp/_return_period_simple_table.htm",
        TEMPLATE_ROOT / "reports/wepp/_return_period_extraneous_table.htm",
        TEMPLATE_ROOT / "reports/rhem/return_periods.htm",
        TEMPLATE_ROOT / "reports/rhem/avg_annual_summary.htm",
    ]

    for template_path in template_paths:
        source = template_path.read_text(encoding="utf-8")
        assert '<a onclick="javascript:copytable(' not in source
        assert 'onclick="copytable(' in source
        assert "aria-label=\"Copy " in source


def test_map_templates_do_not_use_application_role_for_canvas() -> None:
    map_template = (TEMPLATE_ROOT / "controls/map_pure_gl.htm").read_text(encoding="utf-8")
    runs_template = (TEMPLATE_ROOT / "user/runs2.html").read_text(encoding="utf-8")

    assert 'id="mapid" class="wc-map__canvas" role="application"' not in map_template
    assert 'id="runs-map-canvas" class="wc-map__canvas" role="application"' not in runs_template
    assert 'id="mapid" class="wc-map__canvas" aria-label="Watershed map viewport"' in map_template
    assert 'id="runs-map-canvas" class="wc-map__canvas" aria-label="Runs map viewport"' in runs_template


def test_placeholder_only_controls_have_explicit_accessible_names() -> None:
    command_bar_source = (COMMAND_BAR_TEMPLATE_ROOT / "command-bar.htm").read_text(encoding="utf-8")
    browse_directory_source = (
        REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "browse" / "templates" / "browse" / "directory.htm"
    ).read_text(encoding="utf-8")
    browse_not_found_source = (
        REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "browse" / "templates" / "browse" / "not_found.htm"
    ).read_text(encoding="utf-8")

    assert 'placeholder="Enter command..."' in command_bar_source
    assert 'aria-label="Command bar input"' in command_bar_source
    assert 'placeholder="Ask Wojak about this run…"' in command_bar_source
    assert 'aria-label="Wojak chat input"' in command_bar_source
    assert 'id="runIdInput"' in browse_directory_source
    assert 'aria-label="Run ID to compare"' in browse_directory_source
    assert 'id="runIdInput"' in browse_not_found_source
    assert 'aria-label="Run ID to compare"' in browse_not_found_source


def test_standalone_templates_include_lang_and_iframe_titles() -> None:
    huc_fire_source = (TEMPLATE_ROOT / "huc-fire/index.html").read_text(encoding="utf-8")
    edit_csv_source = (TEMPLATE_ROOT / "controls/edit_csv.htm").read_text(encoding="utf-8")
    joh_source = (TEMPLATE_ROOT / "locations/joh/index.htm").read_text(encoding="utf-8")

    assert "<html lang=\"en\">" in huc_fire_source
    assert "<html lang=\"en\">" in edit_csv_source
    assert "Edit Disturbed Lookup CSV" in edit_csv_source

    iframe_count = joh_source.count("<iframe")
    iframe_titles = re.findall(r"<iframe\b[\s\S]*?\btitle=\"[^\"]+\"[\s\S]*?>", joh_source)
    assert iframe_count > 0
    assert len(iframe_titles) == iframe_count


def test_edit_csv_template_honors_theme_system_assets() -> None:
    edit_csv_source = (TEMPLATE_ROOT / "controls/edit_csv.htm").read_text(encoding="utf-8")

    assert 'class="wc-container wc-container--fluid wc-edit-csv"' in edit_csv_source
    assert "wc-edit-csv__run-link" in edit_csv_source
    assert "meta=editor_meta_html" in edit_csv_source
    assert "url_for_run('run_0.runs0', runid=runid, config=config)" in edit_csv_source
    assert "computeSpreadsheetColumnTargetWidth" in edit_csv_source
    assert "stretchColumnsToTargetWidth" in edit_csv_source
    assert "wc-jexcel-theme" in edit_csv_source
    assert "table.jexcel > thead > tr > td.selected" in edit_csv_source
    assert "table.jexcel > tbody > tr > td.highlight-selected" in edit_csv_source
    assert "table.jexcel > tbody > tr > td.jexcel_row" in edit_csv_source
    assert "table.jexcel > tbody > tr > td {" in edit_csv_source
    assert "controls/_pure_macros.html" in edit_csv_source
    assert "shared/console_macros.htm" in edit_csv_source
    assert "css/ui-foundation.css" in edit_csv_source
    assert "css/themes/all-themes.css" in edit_csv_source
    assert "js/theme.js" in edit_csv_source
    assert 'localStorage.getItem("wc-theme")' in edit_csv_source
    assert "pure-button pure-button-primary" in edit_csv_source
