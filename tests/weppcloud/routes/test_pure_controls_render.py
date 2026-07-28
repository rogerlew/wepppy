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
    "controls/ag_fields_pure.htm",
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


def test_base_pure_renders_document_metadata_blocks_and_assets(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% extends "base_pure.htm" %}
        {% block title %}Contract fixture{% endblock %}
        {% block head_extras %}<meta name="fixture-head" content="ready">{% endblock %}
        {% block body %}<div id="fixture-body">Body</div>{% endblock %}
        {% block footer %}<footer id="fixture-footer">Footer</footer>{% endblock %}
        {% block script_extras %}<script id="fixture-script"></script>{% endblock %}
        """
    )
    rendered = template.render(
        csrf_token=lambda: "csrf-fixture",
        static_url=lambda path: f"/static/{path}",
        current_user=SimpleNamespace(is_authenticated=True),
        site_prefix="/fixture",
        controllers_gl_expected_build_id="build-fixture",
    )

    for token in (
        '<html lang="en" class="wc-page">',
        '<meta name="csrf-token" content="csrf-fixture"',
        'data-user-authenticated="true"',
        'data-site-prefix="/fixture"',
        'data-controllers-gl-expected-build-id="build-fixture"',
        "<title>Contract fixture</title>",
        'name="fixture-head"',
        'id="fixture-body"',
        'id="fixture-footer"',
        'id="fixture-script"',
        '/static/vendor/purecss/pure-min.css',
        "/static/css/ui-foundation.css",
        "/static/css/themes/all-themes.css",
        "/static/js/csrf_bootstrap.js",
        "/static/js/theme.js",
        "/static/js/session_heartbeat.js",
        "/static/js/button_tab_order.js",
    ):
        assert token in rendered


def test_pure_control_shell_renders_form_and_lifecycle_contract(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% import "controls/_pure_macros.html" as ui with context %}
        {% call ui.control_shell(
          "fixture_form",
          "Fixture control",
          collapsible=false,
          description="<p>Fixture description</p>",
          toolbar="<button id='fixture-action'>Run</button>",
          form_class="fixture-form",
          form_attrs={"data-controller": "fixture", "novalidate": true},
          status_panel_options={"job_id": "fixture_job", "braille_id": "fixture_braille",
                                "log_id": "fixture_status"},
          summary_panel_options={"summary_id": "fixture_info"},
          stacktrace_panel_options={"body_id": "fixture_stacktrace"}
        ) %}
          <input id="fixture_input" name="fixture_value" value="ready">
          {{ ui.job_hint("fixture_hint", attrs={"data-job-kind": "fixture"}) }}
        {% endcall %}
        """
    )
    rendered = template.render()

    for token in (
        'form id="fixture_form"',
        'action="javascript:void(0);"',
        'enctype="multipart/form-data"',
        "fixture-form",
        'data-controller="fixture"',
        "novalidate",
        'id="fixture_input"',
        'name="fixture_value"',
        'value="ready"',
        'data-status-panel',
        'id="fixture_job"',
        'id="fixture_braille"',
        'id="fixture_status"',
        'data-status-log',
        'id="fixture_info"',
        'data-stacktrace-panel',
        'id="fixture_stacktrace"',
        'id="fixture_hint"',
        'data-job-hint',
        'data-job-kind="fixture"',
    ):
        assert token in rendered

    assert rendered.index('id="fixture_input"') < rendered.index("data-status-panel")


def test_pure_field_macros_preserve_identity_values_state_and_aria(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% import "controls/_pure_macros.html" as ui with context %}
        {{ ui.text_field("fixture_text", "Text", value="alpha", help="Text help",
                         error="Text error", attrs={"data-parser-key": "text_key"}) }}
        {{ ui.select_field("fixture_select", "Select", [("a", "Alpha"), ("b", "Beta")],
                           selected="b", field_name="select_value") }}
        {{ ui.numeric_field("fixture_number", "Number", value=2.5, precision=0.5,
                            min=0, max=5, required=true, nullable=true,
                            unit_label="m", unit_category="length", unit_name="meter") }}
        {{ ui.file_upload("fixture_file", "File", accept=".csv", field_name="upload_value",
                          current_filename="existing.csv") }}
        {{ ui.textarea_field("fixture_notes", "Notes", value="saved notes", rows=6,
                             placeholder="Enter notes") }}
        """
    )
    rendered = template.render()

    assert re.search(
        r'id="fixture_text"[^>]*name="fixture_text"[^>]*value="alpha"'
        r'[^>]*aria-invalid="true"[^>]*aria-describedby="fixture_text_help fixture_text_error"',
        rendered,
    )
    assert 'data-parser-key="text_key"' in rendered
    assert re.search(r'<option value="b" selected>Beta</option>', rendered)
    assert re.search(r'id="fixture_select"[^>]*name="select_value"', rendered)
    assert re.search(
        r'id="fixture_number"[^>]*name="fixture_number"[^>]*type="number"'
        r'[^>]*value="2.5"[^>]*step="0.5"[^>]*min="0"[^>]*max="5"'
        r'[^>]*required[^>]*data-nullable="true"',
        rendered,
    )
    assert 'data-unitizer-category="length"' in rendered
    assert 'data-unitizer-unit="meter"' in rendered
    assert re.search(
        r'id="fixture_file"[^>]*name="upload_value"[^>]*type="file"[^>]*accept="\.csv"',
        rendered,
    )
    assert "existing.csv" in rendered
    assert re.search(
        r'id="fixture_notes"[^>]*name="fixture_notes"[^>]*rows="6"'
        r'[^>]*placeholder="Enter notes"[^>]*>saved notes</textarea>',
        rendered,
    )


def test_pure_choice_and_structural_macros_preserve_state_and_targets(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% import "controls/_pure_macros.html" as ui with context %}
        {{ ui.radio_group(
          "fixture_mode", label="Mode", layout="grid", grid_columns=2,
          options=[
            {"id": "fixture_mode_a", "value": "a", "label": "Alpha", "selected": true},
            {"id": "fixture_mode_b", "value": "b", "label": "Beta", "disabled": true}
          ],
          help="Choose a mode", mode_help={"a": "<strong>Alpha help</strong>"}
        ) }}
        {{ ui.checkbox_field("fixture_enabled", "Enabled", checked=true, help="Toggle help") }}
        {{ ui.tabset([
          {"id": "fixture_tab_a", "label": "First", "content": "<p>A</p>"},
          {"id": "fixture_tab_b", "label": "Second", "content": "<p>B</p>", "active": true}
        ]) }}
        {{ ui.table_block(
          [{"key": "name", "label": "Name"}, {"key": "value", "label": "Value"}],
          [{"name": "row-a", "value": "42"}],
          caption="Fixture table"
        ) }}
        {{ ui.dynamic_slot("fixture_slot", help="Dynamic help",
                           attrs={"data-slot-kind": "fixture"}) }}
        {{ ui.color_scale("fixture_range", "fixture_canvas", "fixture_min", "fixture_max",
                          label="Scale", units_id="fixture_units",
                          range_attrs={"min": 1, "max": 9, "value": 4}) }}
        """
    )
    rendered = template.render()

    assert re.search(
        r'id="fixture_mode_a"[^>]*name="fixture_mode"[^>]*value="a"[^>]*checked',
        rendered,
    )
    assert re.search(
        r'id="fixture_mode_b"[^>]*name="fixture_mode"[^>]*value="b"'
        r'[^>]*disabled[^>]*aria-disabled="true"',
        rendered,
    )
    assert 'data-choice-help-root="fixture_mode"' in rendered
    assert 'data-choice-help-target="a"' in rendered
    assert re.search(r'id="fixture_enabled"[^>]*name="fixture_enabled"[^>]*checked', rendered)
    assert re.search(
        r'id="fixture_tab_b_tab"[\s\S]*?aria-selected="true"[\s\S]*?tabindex="0"',
        rendered,
    )
    assert re.search(r'id="fixture_tab_a"[\s\S]*?role="tabpanel"[\s\S]*?hidden', rendered)
    assert "<caption>Fixture table</caption>" in rendered
    assert "<td>\n            \n              \n            \n            row-a" in rendered
    assert 'id="fixture_slot"' in rendered
    assert 'data-slot-kind="fixture"' in rendered
    for target in ("fixture_range", "fixture_canvas", "fixture_min", "fixture_max", "fixture_units"):
        assert f'id="{target}"' in rendered
    assert re.search(r'id="fixture_range"[\s\S]*?min="1"[\s\S]*?max="9"[\s\S]*?value="4"', rendered)


def test_pure_card_and_empty_state_macros_render_structure(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% import "controls/_pure_macros.html" as ui with context %}
        {% call ui.card_shell("Shell card", collapsible=true, open=false,
                              attrs={"data-card-kind": "shell"}) %}
          {% call ui.fieldset("Fixture legend", "Fixture description") %}
            <span id="fieldset-content">Content</span>
          {% endcall %}
        {% endcall %}
        {% call ui.card("Content card", footer="<button id='card-footer'>Done</button>",
                        attrs={"data-card-kind": "content"}) %}
          {{ ui.text_display("Result", "<strong>Ready</strong>",
                             actions=["<a id='result-action'>Open</a>"]) }}
        {% endcall %}
        {{ ui.table_block([{"key": "name", "label": "Name"}], [],
                          empty_message="Nothing here") }}
        """
    )
    rendered = template.render()

    assert re.search(r'<details class="wc-control wc-control--collapsible"[^>]*data-card-kind="shell"', rendered)
    assert not re.search(r'<details class="wc-control wc-control--collapsible"[^>]*\sopen', rendered)
    assert "<legend class=\"wc-fieldset__legend\">Fixture legend</legend>" in rendered
    assert 'id="fieldset-content"' in rendered
    assert re.search(r'<section class="wc-card"[^>]*data-card-kind="content"', rendered)
    assert "card-footer" in rendered
    assert "<strong>Ready</strong>" in rendered
    assert "result-action" in rendered
    assert '<td colspan="1">' in rendered
    assert "<em>Nothing here</em>" in rendered


def test_shared_console_and_table_macros_render_actions_and_structure(jinja_env: Environment) -> None:
    template = jinja_env.from_string(
        """
        {% import "shared/console_macros.htm" as console %}
        {% import "shared/table_macros.htm" as tables %}
        {% call console.console_page(data_controller="fixture-console", classes="fixture-page") %}
          {{ console.console_header(
            run_link="/runs/fixture/config",
            run_label="fixture",
            title="Console",
            subtitle="Console subtitle",
            actions=[
              {"element": "button", "id": "console-refresh", "label": "Refresh",
               "variant": "pure-button-primary", "disabled": true},
              {"id": "console-help", "label": "Help", "href": "/help",
               "target": "_blank", "rel": "noopener"}
            ]
          ) }}
          {% call console.button_row(form_controls=true, full_width=true,
                                     extra_class="fixture-actions") %}
            <button id="console-submit" type="submit">Submit</button>
          {% endcall %}
        {% endcall %}
        {% call tables.table_page(title="Records", data_controller="fixture-table",
                                  classes="fixture-table-page") %}
          {% call tables.table_panel("Results", "Result description") %}
            <table id="fixture-table"><tbody><tr><td>ready</td></tr></tbody></table>
          {% endcall %}
        {% endcall %}
        """
    )
    rendered = template.render()

    for token in (
        'data-controller="fixture-console"',
        "fixture-page",
        'href="/runs/fixture/config"',
        'target="_blank"',
        'rel="noopener"',
        "Console subtitle",
        'id="console-refresh"',
        "pure-button-primary",
        "disabled",
        'id="console-help"',
        'href="/help"',
        "wc-controls-left",
        "wc-button-row--full",
        "fixture-actions",
        'id="console-submit"',
        'data-controller="fixture-table"',
        "wc-table-page",
        "fixture-table-page",
        "wc-table-wrapper",
        'id="fixture-table"',
    ):
        assert token in rendered


def test_shared_modal_and_theme_templates_render_accessible_hooks(jinja_env: Environment) -> None:
    team_modal = jinja_env.get_template("controls/team_modal.htm").render(
        modal_id="fixtureTeamModal",
        modal_title="Fixture team",
    )
    theme_switcher = jinja_env.get_template("header/_theme_switcher.htm").render()

    for token in (
        'id="fixtureTeamModal"',
        "data-modal",
        "hidden",
        "data-modal-dismiss",
        'role="dialog"',
        'aria-modal="true"',
        'aria-labelledby="fixtureTeamModalTitle"',
        'id="fixtureTeamModalTitle"',
        'aria-label="Close team manager"',
    ):
        assert token in team_modal

    assert 'id="wc-theme-switcher-select"' in theme_switcher
    assert "data-theme-select" in theme_switcher
    assert 'aria-label="Interface theme"' in theme_switcher
    for theme in ("default", "light-high-contrast", "ayu-mirage", "cursor-dark-midnight"):
        assert f'value="{theme}"' in theme_switcher


def test_generated_theme_bundle_matches_authoritative_source() -> None:
    source = (
        REPO_ROOT / "wepppy" / "weppcloud" / "controllers_js" / "theme.js"
    ).read_text(encoding="utf-8")
    generated = (
        REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "theme.js"
    ).read_text(encoding="utf-8")

    assert "Theme Switcher standalone bundle" in generated
    assert generated.endswith(source)


def test_soil_pure_template_renders_ssurgo_cache_checkbox(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/soil_pure.htm")
    rendered = template.render(
        soils=SimpleNamespace(
            mode=SimpleNamespace(value=0),
            initial_sat=0.75,
            single_selection=0,
            single_dbselection=None,
            ksflag=True,
            clear_ssurgo_cache_on_rebuild=True,
        ),
        soildboptions=["DB1"],
        disturbed=None,
    )

    assert 'id="clear_ssurgo_cache_on_rebuild"' in rendered
    assert 'name="clear_ssurgo_cache_on_rebuild"' in rendered
    assert "Clear SSURGO cache on rebuild" in rendered
    assert re.search(r'id="clear_ssurgo_cache_on_rebuild"[^>]*checked', rendered)
    for mode in ("0", "1", "2"):
        assert re.search(
            rf'<input[^>]*id="soil_mode{mode}"[^>]*name="soil_mode"'
            rf'[^>]*value="{mode}"',
            rendered,
        )
    assert re.search(
        r'<input[^>]*id="soil_initial_sat"[^>]*name="initial_sat"'
        r'[^>]*value="0.75"',
        rendered,
    )
    assert re.search(
        r'<input[^>]*id="soil_single_selection"[^>]*'
        r'name="soil_single_selection"[^>]*value="0"',
        rendered,
    )
    assert re.search(
        r'<select[^>]*id="soil_single_dbselection"[^>]*'
        r'name="soil_single_dbselection"',
        rendered,
    )
    assert re.search(
        r'<input[^>]*id="checkbox_ksflag"[^>]*name="checkbox_ksflag"'
        r'[^>]*checked',
        rendered,
    )
    assert 'id="btn_build_soil"' in rendered
    assert 'id="hint_build_soil"' in rendered
    assert 'id="soil_status_panel"' in rendered
    assert 'id="soil_stacktrace_panel"' in rendered


def test_climate_template_renders_catalog_station_and_build_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/climate_pure.htm")
    climate = SimpleNamespace(
        catalog_id="prism_stochastic",
        climate_mode=SimpleNamespace(value=5),
        climatestation_mode=SimpleNamespace(value=-1),
        climate_spatialmode=SimpleNamespace(value=0),
        uses_tenerife_station_catalog=False,
        is_single_storm=False,
        datasetMap={},
        input_years=30,
        observed_start_year=1981,
        observed_end_year=2024,
        future_start_year=2030,
        future_end_year=2060,
        cli_fn=None,
        orig_cli_fn=None,
        climate_daily_temp_ds="null",
        use_gridmet_wind_when_applicable=True,
        adjust_mx_pt5=False,
        silent_pass_observed_quality_guard=False,
        precip_scaling_mode=SimpleNamespace(value=0),
        precip_scale_factor=None,
        precip_monthly_scale_factors=None,
        precip_scale_reference=None,
        precip_scale_factor_map=None,
    )
    catalog = [
        {
            "catalog_id": "prism_stochastic",
            "label": "PRISM stochastic",
            "description": "Test catalog",
            "help_text": "Test help",
            "group": "Stochastic",
            "group_hint": "",
            "climate_mode": 5,
            "ui_exposed": True,
        }
    ]
    rendered = template.render(climate=climate, climate_catalog=catalog)

    assert 'id="climate_catalog_data"' in rendered
    assert 'id="climate_catalog_id"' in rendered
    assert 'name="climate_catalog_id"' in rendered
    assert 'id="climate_mode"' in rendered
    assert 'name="climate_mode"' in rendered
    assert 'id="climate_dataset_prism_stochastic"' in rendered
    assert 'data-climate-action="dataset"' in rendered
    assert 'id="climatestation_mode_auto"' in rendered
    assert 'name="climatestation_mode"' in rendered
    assert 'id="climate_station_selection"' in rendered
    assert 'name="climate_station_selection"' in rendered
    assert 'id="climate_spatialmode0"' in rendered
    assert 'name="climate_spatialmode"' in rendered
    assert 'id="input_years"' in rendered
    assert 'name="input_years"' in rendered
    assert 'id="btn_build_climate"' in rendered
    assert 'data-climate-action="build"' in rendered
    assert 'id="hint_build_climate"' in rendered
    assert 'id="climate_status_panel"' in rendered


def test_climate_template_renders_upload_and_scaling_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/climate_pure.htm")
    climate = SimpleNamespace(
        catalog_id="user_defined_cli",
        climate_mode=SimpleNamespace(value=12),
        climatestation_mode=SimpleNamespace(value=4),
        climate_spatialmode=SimpleNamespace(value=0),
        uses_tenerife_station_catalog=False,
        is_single_storm=False,
        datasetMap={},
        input_years=30,
        observed_start_year=1981,
        observed_end_year=2024,
        future_start_year=2030,
        future_end_year=2060,
        cli_fn="cli/custom.cli",
        orig_cli_fn=None,
        climate_daily_temp_ds="gridmet",
        use_gridmet_wind_when_applicable=True,
        adjust_mx_pt5=True,
        silent_pass_observed_quality_guard=True,
        precip_scaling_mode=SimpleNamespace(value=2),
        precip_scale_factor=1.1,
        precip_monthly_scale_factors=[1.0] * 12,
        precip_scale_reference="prism",
        precip_scale_factor_map=None,
    )
    catalog = [{
        "catalog_id": "user_defined_cli", "label": "User CLI", "description": "",
        "help_text": "", "group": "User-Defined", "group_hint": "",
        "climate_mode": 12, "ui_exposed": True,
    }]
    rendered = template.render(climate=climate, climate_catalog=catalog)

    assert 'id="input_upload_cli"' in rendered
    assert 'name="input_upload_cli"' in rendered
    assert 'id="btn_upload_cli"' in rendered
    assert 'data-climate-action="upload-cli"' in rendered
    assert 'id="hint_upload_cli"' in rendered
    assert 'id="checkbox_use_gridmet_wind_when_applicable"' in rendered
    assert 'id="checkbox_adjust_mx_pt5"' in rendered
    assert 'id="checkbox_silent_pass_observed_quality_guard"' in rendered
    assert 'id="climate_precipscaling_mode2"' in rendered
    assert 'name="precip_scaling_mode"' in rendered
    assert 'id="climate_precipscaling_mode2_controls"' in rendered
    assert 'id="precip_monthly_scale_factors_0"' in rendered
    assert 'name="precip_monthly_scale_factors_11"' in rendered


def test_observed_template_renders_model_fit_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/observed_pure.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"swat"}),
        observed=SimpleNamespace(model_source="swat"),
    )

    assert 'id="observed_form"' in rendered
    assert 'id="observed_text"' in rendered
    assert 'name="observed_text"' in rendered
    assert 'name="observed_model_source"' in rendered
    assert re.search(r'<input[^>]*name="observed_model_source"[^>]*value="swat"[^>]*checked', rendered)
    assert 'id="btn_run_observed"' in rendered
    assert 'data-action="observed-run"' in rendered
    assert 'id="hint_run_observed"' in rendered
    assert 'id="observed_status_panel"' in rendered
    assert 'id="observed_stacktrace_panel"' in rendered


def test_team_template_renders_collaboration_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/team_pure.htm")
    rendered = template.render()

    assert 'id="team_form"' in rendered
    assert 'id="adduser-email"' in rendered
    assert 'name="adduser-email"' in rendered
    assert 'data-team-field="email"' in rendered
    assert 'id="btn_adduser"' in rendered
    assert 'data-team-action="invite"' in rendered
    assert 'id="hint_run_team"' in rendered
    assert 'id="team_status_panel"' in rendered
    assert 'id="team_stacktrace_panel"' in rendered


def test_ash_template_submits_canonical_model_selector_names(jinja_env: Environment) -> None:
    def model_params(**overrides: float) -> SimpleNamespace:
        values: dict[str, float] = {
            "ini_bulk_den": 0.31,
            "fin_bulk_den": 0.62,
            "bulk_den_fac": 0.005,
            "par_den": 1.2,
            "decomp_fac": 0.00018,
            "ini_erod": 4.5,
            "fin_erod": 0.045,
            "roughness_limit": 1.0,
            "org_mat": 0.04,
            "initranscap": 2.0,
            "depletcoeff": 0.1,
        }
        values.update(overrides)
        return SimpleNamespace(**values, to_dict=lambda: dict(values))

    template = jinja_env.get_template("controls/ash_pure.htm")
    ash = SimpleNamespace(
            ash_depth_mode=1,
            fire_date="8/4",
            ini_black_ash_depth_mm=5.0,
            ini_white_ash_depth_mm=5.0,
            ini_black_ash_load=11_000.0,
            ini_white_ash_load=16_000.0,
            field_black_ash_bulkdensity=0.22,
            field_white_ash_bulkdensity=0.31,
            model="alex",
            available_models=[("multi", "Srivastava2023"), ("alex", "Watanabe2025")],
            transport_mode="static",
            run_wind_transport=False,
            anu_white_ash_model_pars=model_params(),
            anu_black_ash_model_pars=model_params(ini_bulk_den=0.22),
            alex_white_ash_model_pars=model_params(),
            alex_black_ash_model_pars=model_params(ini_bulk_den=0.22, org_mat=0.065),
    )
    rendered = template.render(ash=ash)

    assert re.search(
        r'<select[^>]*id="ash_model_select"[^>]*name="ash_model"',
        rendered,
        re.DOTALL,
    )
    assert re.search(
        r'<select[^>]*id="ash_transport_mode_select"[^>]*name="transport_mode"',
        rendered,
        re.DOTALL,
    )
    assert 'name="ash_model_select"' not in rendered
    assert 'name="ash_transport_mode_select"' not in rendered

    for field_name in (
        "fire_date",
        "ini_black_depth",
        "ini_white_depth",
        "ini_black_load",
        "ini_white_load",
        "input_upload_ash_load",
        "input_upload_ash_type_map",
        "field_black_bulkdensity",
        "field_white_bulkdensity",
        "checkbox_run_wind_transport",
        "white_ini_bulk_den",
        "black_ini_bulk_den",
        "white_fin_bulk_den",
        "black_fin_bulk_den",
        "white_initranscap",
        "black_initranscap",
        "white_depletcoeff",
        "black_depletcoeff",
    ):
        assert re.search(
            rf'<(?:input|select)[^>]*(?=id="{field_name}")'
            rf'(?=[^>]*name="{field_name}")[^>]*>',
            rendered,
            re.DOTALL,
        )

    assert re.search(r'<input[^>]*id="ash_depth_mode_depth"[^>]*checked', rendered)
    assert re.search(r'<option value="alex" selected>Watanabe2025</option>', rendered)
    assert re.search(r'<option value="static" selected>Static</option>', rendered)
    assert 'accept=".tif,.tiff,.img"' in rendered
    unchecked_wind = re.search(
        r'<input[^>]*id="checkbox_run_wind_transport"[^>]*>', rendered
    )
    assert unchecked_wind is not None
    assert "checked" not in unchecked_wind.group(0)

    ash.run_wind_transport = True
    rendered_with_wind = template.render(ash=ash)
    assert re.search(
        r'<input[^>]*id="checkbox_run_wind_transport"[^>]*checked',
        rendered_with_wind,
    )


def test_channel_template_submits_and_hydrates_channel_configuration(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/channel_delineation_pure.htm")
    rendered = template.render(
        watershed=SimpleNamespace(
            uploaded_dem_filename="uploaded-dem.tif",
            set_extent_mode=3,
            map_bounds_text="",
            delineation_backend_is_topaz=False,
            delineation_backend_is_wbt=True,
            mcl=61.0,
            csa=7.0,
            stream_pruning_method="remove_short_streams",
            wbt_fill_or_breach="breach_least_cost",
            wbt_blc_dist=777,
        )
    )

    for field_name in (
        "map_center",
        "map_zoom",
        "map_bounds",
        "map_distance",
        "map_bounds_text",
        "map_object",
        "input_upload_dem",
        "input_mcl",
        "input_csa",
        "stream_pruning_method",
        "input_wbt_fill_or_breach",
        "wbt_blc_dist",
    ):
        assert re.search(rf'<(?:input|select|textarea)[^>]*id="{field_name}"[^>]*>', rendered)

    for field_name in (
        "map_center",
        "map_zoom",
        "map_bounds",
        "map_distance",
        "map_bounds_text",
        "map_object",
        "input_upload_dem",
        "wbt_blc_dist",
    ):
        assert re.search(
            rf'<(?:input|textarea)[^>]*id="{field_name}"[^>]*name="{field_name}"',
            rendered,
        )

    assert re.search(r'<input[^>]*id="input_upload_dem"[^>]*name="input_upload_dem"', rendered)
    assert 'accept=".tif"' in rendered
    assert "uploaded-dem.tif" in rendered
    assert re.search(r'<input[^>]*id="set_extent_mode_upload_dem"[^>]*checked', rendered)
    assert re.search(r'<input[^>]*id="input_mcl"[^>]*name="input_mcl"[^>]*value="61"', rendered)
    assert re.search(r'<input[^>]*id="input_csa"[^>]*name="input_csa"[^>]*value="7"', rendered)
    assert re.search(
        r'<select[^>]*id="stream_pruning_method"[^>]*name="stream_pruning_method"',
        rendered,
    )
    assert re.search(r'<option value="remove_short_streams" selected>', rendered)
    assert re.search(
        r'<select[^>]*id="input_wbt_fill_or_breach"'
        r'[^>]*name="wbt_fill_or_breach"'
        r'[^>]*data-channel-role="wbt-fill"',
        rendered,
        re.DOTALL,
    )
    assert 'name="input_wbt_fill_or_breach"' not in rendered
    assert re.search(r'<option value="breach_least_cost" selected>Breach \(Least Cost\)</option>', rendered)
    assert re.search(r'<input[^>]*id="wbt_blc_dist"[^>]*name="wbt_blc_dist"[^>]*value="777"', rendered)


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


def test_landuse_catalog_template_renders_transport_and_upload_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/landuse_user_defined.htm")
    rendered = template.render(
        runid="demo-run",
        config="demo-config",
        list_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/catalog",
        upload_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/upload",
        delete_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/delete",
        update_description_url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/update-description",
        session_token_url="/rq-engine/api/runs/demo-run/demo-config/session-token",
        catalog_items=[{"filename": "forest.man", "description": "Forest"}],
    )

    assert 'id="landuse-user-defined-config"' in rendered
    assert 'data-list-url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/catalog"' in rendered
    assert 'data-upload-url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/upload"' in rendered
    assert 'data-delete-url="/rq-engine/api/runs/demo-run/demo-config/landuse-user-defined/delete"' in rendered
    assert (
        'data-update-description-url="/rq-engine/api/runs/demo-run/demo-config/'
        'landuse-user-defined/update-description"' in rendered
    )
    assert 'data-session-token-url="/rq-engine/api/runs/demo-run/demo-config/session-token"' in rendered
    assert '"filename": "forest.man"' in rendered
    assert re.search(
        r'<input[^>]*id="catalog-upload-input"[^>]*name="management_upload"'
        r'[^>]*type="file"[^>]*accept="\.man,\.zip"',
        rendered,
    )
    assert re.search(
        r'<input[^>]*id="catalog-upload-replace"[^>]*name="replace"'
        r'[^>]*type="checkbox"[^>]*value="true"',
        rendered,
    )
    assert 'id="catalog-refresh"' in rendered
    assert 'id="catalog-rows"' in rendered


def test_landuse_map_template_renders_snapshot_and_mutation_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/landuse_map.htm")
    rendered = template.render(
        runid="demo-run",
        config="demo-config",
        snapshot_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/snapshot",
        save_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/save",
        clear_override_url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/clear-override",
        session_token_url="/rq-engine/api/runs/demo-run/demo-config/session-token",
        snapshot={
            "rows": [{"key": "21", "management_file": "forest.man"}],
            "management_options": [{"management_file": "forest.man"}],
            "lookup_sha256": "sha-before-save",
        },
    )

    assert 'id="landuse-map-config"' in rendered
    assert 'data-snapshot-url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/snapshot"' in rendered
    assert 'data-save-url="/rq-engine/api/runs/demo-run/demo-config/landuse-map/save"' in rendered
    assert (
        'data-clear-override-url="/rq-engine/api/runs/demo-run/demo-config/'
        'landuse-map/clear-override"' in rendered
    )
    assert 'data-session-token-url="/rq-engine/api/runs/demo-run/demo-config/session-token"' in rendered
    assert '"lookup_sha256": "sha-before-save"' in rendered
    assert 'id="landuse-map-save"' in rendered
    assert 'id="landuse-map-refresh"' in rendered
    assert 'id="landuse-map-clear"' in rendered
    assert 'id="landuse-map-rows"' in rendered


def test_landuse_modifier_template_renders_selection_and_submit_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/modify_landuse.htm")
    rendered = template.render(
        landuseoptions=[
            {"Key": "42", "Description": "Forest"},
            {"Key": "202", "Description": "Developed"},
        ]
    )

    assert re.search(
        r'<input[^>]*id="checkbox_modify_landuse"[^>]*'
        r'name="checkbox_modify_landuse"[^>]*'
        r'data-landuse-modify-action="toggle-selection"',
        rendered,
    )
    assert re.search(
        r'<textarea[^>]*id="textarea_modify_landuse"[^>]*'
        r'name="textarea_modify_landuse"[^>]*'
        r'data-landuse-modify-field="topaz-ids"',
        rendered,
    )
    assert re.search(
        r'<select[^>]*id="selection_modify_landuse"[^>]*'
        r'name="selection_modify_landuse"[^>]*'
        r'data-landuse-modify-field="landuse-code"',
        rendered,
    )
    assert '<option value="202">202 — Developed</option>' in rendered
    assert 'id="btn_modify_landuse"' in rendered
    assert 'data-landuse-modify-action="submit"' in rendered
    assert 'id="modify_landuse_status_panel"' in rendered
    assert 'id="modify_landuse_stacktrace_panel"' in rendered


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


def test_wepp_reports_template_renders_ermit_export_link(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/wepp_reports.htm")
    rendered = template.render(
        climate=SimpleNamespace(is_single_storm=False, ss_batch_storms=None, mods=set()),
        prep=SimpleNamespace(has_sbs=False),
        runid="test-run",
        config="test-config",
        run_results_title="Run Results",
        totalwatsed3_exists=False,
        totalwatsed2_exists=False,
        ermit_export_download_url="/runs/test-run/test-config/download/ermit",
        prep_details_export_download_url=None,
        post_wepp_geopackage_export_download_url=None,
        post_wepp_geodatabase_export_download_url=None,
    )

    assert "Hillslope Input CSV for ERMiT and Disturbed WEPP" in rendered
    assert 'href="/runs/test-run/test-config/download/ermit"' in rendered


def test_ermit_export_download_template_exposes_rq_engine_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("reports/ermit_export_download.htm")
    rendered = template.render(
        runid="test-run",
        config="test-config",
        ermit_export_submit_url="/rq-engine/api/runs/test-run/test-config/export/ermit",
        ermit_export_session_token_url="/rq-engine/api/runs/test-run/test-config/session-token",
        ermit_export_return_url="/runs/test-run/test-config/report/wepp/results/",
    )

    assert "ERMiT and Disturbed WEPP Export" in rendered
    assert '"/rq-engine/api/runs/test-run/test-config/export/ermit"' in rendered
    assert '"/rq-engine/api/runs/test-run/test-config/session-token"' in rendered
    assert "Download ERMiT Export" in rendered


def test_omni_contrasts_template_shows_user_defined_limit_hint(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/omni_contrasts_pure.htm")
    rendered = template.render(omni_user_defined_contrast_limit=200)

    assert "capped at 200 total contrast runs (contrast pairs x groups)." in rendered
    for marker in (
        'form id="omni_contrasts_form"',
        'data-omni-contrast-role="selection-mode"',
        'data-omni-contrast-role="control-scenario"',
        'data-omni-contrast-role="contrast-scenario"',
        'name="omni_contrast_pairs"',
        'data-omni-contrast-action="add-pair"',
        'data-omni-contrast-role="geojson-path"',
        'data-omni-contrast-action="run-contrasts"',
        'data-omni-contrast-action="dry-run"',
        'data-omni-contrast-action="delete-contrasts"',
        'data-omni-contrast-action="confirm-delete-contrasts"',
    ):
        assert marker in rendered


def test_omni_scenarios_control_renders_actions_lifecycle_and_delete_modal(
    jinja_env: Environment,
) -> None:
    rendered = jinja_env.get_template("controls/omni_scenarios_pure.htm").render()

    for marker in (
        'form id="omni_form"',
        'id="scenario-container"',
        'data-omni-action="add-scenario"',
        'data-omni-action="delete-selected"',
        'data-omni-action="run-scenarios"',
        'id="hint_run_omni"',
        'id="omni-delete-modal"',
        'data-omni-role="delete-list"',
        'data-omni-action="confirm-delete"',
    ):
        assert marker in rendered


def test_rhem_control_renders_run_and_lifecycle_targets(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/rhem_pure.htm").render()

    for marker in (
        'form id="rhem_form"',
        'id="rhem_status_panel"',
        'id="rhem_stacktrace_panel"',
        'id="btn_run_rhem"',
        'data-rhem-action="run"',
        'id="hint_run_rhem"',
    ):
        assert marker in rendered


def test_path_ce_control_renders_thresholds_treatments_and_lifecycle(
    jinja_env: Environment,
) -> None:
    rendered = jinja_env.get_template("controls/path_cost_effective_pure.htm").render()

    for marker in (
        'form id="path_ce_form"',
        'name="sddc_threshold"',
        'name="sdyd_threshold"',
        'name="slope_min"',
        'name="slope_max"',
        'name="severity_filter"',
        '<option value="High">High</option>',
        'id="path_ce_treatments_table"',
        'data-pathce-action="add-treatment"',
        'id="path_ce_run"',
        'id="path_ce_results_panel"',
        'id="path_ce_stacktrace_panel"',
    ):
        assert marker in rendered


def test_rusle_control_renders_modes_defaults_and_build(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/rusle_pure.htm").render(
        rusle=None,
        rusle_rap_year_options=[2021, 2022],
    )

    for marker in (
        'form id="rusle_form"',
        'name="r_mode"',
        'value="cligen_static"',
        'value="momm2025_county_region"',
        'value="canonical_rusle2"',
        'name="c_mode"',
        'value="observed_rap"',
        'value="scenario_sbs"',
        'name="rap_year"',
        'name="rock_fraction_of_rap_bare"',
        'name="rock_fraction_of_sbs_bare"',
        'name="k_modes"',
        'value="polaris_nomograph"',
        'value="polaris_epic"',
        'data-rusle-input="max-slope-length"',
        'data-rusle-input="p-value"',
        'data-rusle-action="run"',
        'id="rusle-results"',
    ):
        assert marker in rendered


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


def test_landuse_template_renders_upload_build_fields_and_lifecycle(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/landuse_pure.htm")
    rendered = template.render(
        landuse=SimpleNamespace(
            mode=SimpleNamespace(value=4),
            nlcd_db="nlcd/2024",
            single_selection="42",
            mofe_buffer_selection="42",
            user_defined_landcover_fn="landcover.tif",
            mapping="disturbed",
        ),
        landuseoptions=[{"Key": "42", "Description": "Forest"}],
        landuse_management_mapping_options=[{"Key": "disturbed", "Description": "Disturbed"}],
        landcover_datasets=[SimpleNamespace(key="nlcd/2024", label="NLCD", description=None, management_file=None)],
        wepp=SimpleNamespace(multi_ofe=False),
        ron=SimpleNamespace(mods={"disturbed"}),
        disturbed=SimpleNamespace(burn_shrubs=True, burn_grass=False),
    )

    upload_mode = re.search(r'id="landuse_mode4"[^>]*>', rendered)
    assert upload_mode is not None
    assert 'name="landuse_mode"' in upload_mode.group(0)
    assert 'value="4"' in upload_mode.group(0)
    assert "checked" in upload_mode.group(0)
    assert 'id="input_upload_landuse"' in rendered
    assert 'name="input_upload_landuse"' in rendered
    assert 'accept=".img,.tif"' in rendered
    assert 'id="landuse_management_mapping_selection"' in rendered
    assert 'name="landuse_management_mapping_selection"' in rendered
    assert 'id="checkbox_burn_shrubs"' in rendered
    assert 'name="checkbox_burn_shrubs"' in rendered
    assert 'id="checkbox_burn_grass"' in rendered
    assert 'name="checkbox_burn_grass"' in rendered
    assert 'id="btn_build_landuse"' in rendered
    assert 'data-landuse-action="build"' in rendered
    assert 'id="hint_build_landuse"' in rendered


def test_subcatchments_template_preserves_wbt_and_mofe_build_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/subcatchments_pure.htm")
    rendered = template.render(
        watershed=SimpleNamespace(
            delineation_backend_is_topaz=False,
            delineation_backend_is_wbt=True,
            abstraction_backend_is_peridot=False,
            mofe_target_length=80,
            mofe_max_ofes=9,
            mofe_buffer=True,
            mofe_buffer_length=35,
        ),
        wepp=SimpleNamespace(multi_ofe=True),
    )

    assert 'id="build_subcatchments_form"' in rendered
    assert 'id="input_pkcsa" value="-1" name="pkcsa"' in rendered
    assert 'id="input_pkcsa_en" value="-1" name="pkcsa_en"' in rendered
    assert 'id="input_mofe_target_length"' in rendered
    assert 'name="mofe_target_length"' in rendered
    assert 'id="input_mofe_max_ofes"' in rendered
    assert 'name="mofe_max_ofes"' in rendered
    assert 'id="checkbox_mofe_buffer"' in rendered
    assert 'name="mofe_buffer"' in rendered
    assert 'id="input_mofe_buffer_length"' in rendered
    assert 'name="mofe_buffer_length"' in rendered
    assert 'id="btn_build_subcatchments"' in rendered
    assert 'data-subcatchment-action="build"' in rendered
    assert 'id="hint_build_subcatchments"' in rendered


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


def test_base_report_renders_run_readonly_navigation_and_runtime_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.from_string(
        """
        {% extends "reports/_base_report.htm" %}
        {% block report_title %}Fixture report{% endblock %}
        {% block report_content %}<article id="fixture-report-content">Ready</article>{% endblock %}
        """
    )
    auth_user = SimpleNamespace(
        has_role=lambda role: role in {"PowerUser", "Admin"},
        roles=["PowerUser", "Admin"],
        is_authenticated=True,
    )
    ron = SimpleNamespace(
        mods={"disturbed"},
        runid="fixture-run",
        config_stem="fixture-config",
        nodb_version=4,
        name="Fixture project",
        scenario="Readonly scenario",
        readonly=True,
        public=True,
        srid=32611,
    )

    def _url_for_run(endpoint: str, **values) -> str:
        return f"/run/{endpoint}/{values.get('runid', '')}/{values.get('config', '')}"

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return f"/static/{values['filename']}"
        return f"/mock/{endpoint}"

    rendered = template.render(
        ron=ron,
        current_ron=ron,
        user=auth_user,
        current_user=auth_user,
        request=SimpleNamespace(
            view_args={"runid": "fixture-run", "config": "fixture-config"},
        ),
        current_ttl=SimpleNamespace(user_disabled=True),
        pup_relpath=None,
        get_last_modified=lambda runid: SimpleNamespace(
            strftime=lambda fmt: "2026-07-28 12:34:56",
            timestamp=lambda: 1785267296,
        ),
        url_for_run=_url_for_run,
        url_for=_url_for,
        static_url=lambda path: f"/static/{path}",
        site_prefix="/weppcloud",
    )

    for token in (
        "<title>Fixture report - Fixture project</title>",
        "wc-container wc-container--fluid",
        'href="/run/run_0.runs0/fixture-run/fixture-config"',
        "fixture-run",
        "fixture-config",
        "NoDb v4",
        'data-project-projection="EPSG:32611"',
        'data-run-last-modified="1785267296"',
        'id="input_name"',
        'name="name"',
        'value="Fixture project"',
        'data-project-field="name"',
        'id="input_scenario"',
        'name="scenario"',
        'value="Readonly scenario"',
        'data-project-field="scenario"',
        "disable-readonly",
        'id="checkbox_readonly"',
        'id="checkbox_public"',
        'id="checkbox_ttl_disabled"',
        'data-modal-open="puModal"',
        'data-modal-open="disturbedModal"',
        'data-modal-open="unitizerModal"',
        'id="fixture-report-content"',
        'id="unitizerModal"',
        'id="disturbedModal"',
        "/static/js/controllers-gl.js",
        "/static/js/controllers_gl_stale_check.js",
        "/static/js/report_csv.js",
        "/static/js/link_target_pref.js",
        "/static/js/sorttable.js",
        "window.runid = runid",
        "window.runId = runid",
        "window.config = config",
    ):
        assert token in rendered

    assert re.search(r'id="checkbox_readonly"[^>]*checked', rendered)
    assert re.search(r'id="checkbox_public"[^>]*checked', rendered)
    assert re.search(r'id="checkbox_ttl_disabled"[^>]*checked', rendered)
    assert rendered.index("/static/js/controllers-gl.js") < rendered.index(
        'id="fixture-report-content"',
    )


def test_base_report_pup_context_hides_parent_actions_and_scopes_requests(
    jinja_env: Environment,
) -> None:
    template = jinja_env.from_string(
        """
        {% extends "reports/_base_report.htm" %}
        {% block report_title %}Child report{% endblock %}
        {% block report_content %}<p id="child-report">Child</p>{% endblock %}
        """
    )
    anon_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    ron = SimpleNamespace(
        mods=set(),
        runid="batch;;child",
        config_stem="cfg",
        nodb_version=4,
        name="",
        scenario="",
        readonly=False,
        public=False,
        srid=None,
    )
    rendered = template.render(
        ron=ron,
        current_ron=ron,
        user=anon_user,
        current_user=anon_user,
        request=SimpleNamespace(view_args={"runid": "batch;;child", "config": "cfg"}),
        pup_relpath="children/child",
        site_prefix="/weppcloud",
    )

    assert ">FORK</a>" not in rendered
    assert ">ARCHIVE</a>" not in rendered
    assert 'id="child-report"' in rendered
    assert 'const pupRelPath = "children/child"' in rendered
    assert "url.includes(';;')" in rendered
    assert "url.toLowerCase().includes('%3b%3b')" in rendered
    assert "url.includes('elevationquery')" in rendered
    assert "window.fetch = function(input, init)" in rendered
    assert "XMLHttpRequest.prototype.open = function" in rendered


def test_report_shell_falls_back_to_global_header_without_run_view(
    jinja_env: Environment,
) -> None:
    template = jinja_env.from_string(
        """
        {% extends "reports/_base_report.htm" %}
        {% block report_title %}Global report{% endblock %}
        {% block report_content %}<p id="global-report">Global</p>{% endblock %}
        """
    )
    anon_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    ron = SimpleNamespace(
        mods=set(),
        runid="fixture-run",
        config_stem="cfg",
        name="",
        scenario="",
    )
    rendered = template.render(
        ron=ron,
        current_ron=None,
        user=anon_user,
        current_user=anon_user,
        pup_relpath=None,
    )

    assert 'id="global-report"' in rendered
    assert '<header class="wc-header wc-run-header"' not in rendered
    assert '<header class="wc-header">' in rendered


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


def test_legacy_report_shell_renders_content_state_and_shared_runtime(
    jinja_env: Environment,
) -> None:
    template = jinja_env.from_string(
        """
        {% extends "reports/_page_container.htm" %}
        {% block report_title %}Legacy fixture{% endblock %}
        {% block report_content %}<article id="legacy-report-content">Legacy</article>{% endblock %}
        """
    )
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    ron = SimpleNamespace(
        mods={"disturbed"},
        runid="fixture-run",
        config_stem="cfg",
        nodb_version=3,
        name="Legacy project",
        scenario="Legacy scenario",
        readonly=True,
        public=True,
        srid=None,
        pup_relpath=None,
    )
    rendered = template.render(
        ron=ron,
        current_ron=ron,
        user=auth_user,
        current_user=auth_user,
        request=SimpleNamespace(view_args={"runid": "fixture-run", "config": "cfg"}),
        controllers_gl_expected_build_id="legacy-build",
        static_url=lambda path: f"/static/{path}",
    )

    for token in (
        '<html lang="en">',
        "<title>Legacy fixture - Legacy project</title>",
        'data-controllers-gl-expected-build-id="legacy-build"',
        "/static/js/controllers-gl.js",
        "/static/js/controllers_gl_stale_check.js",
        'id="input_name"',
        'data-project-field="name"',
        'id="checkbox_readonly"',
        'id="checkbox_public"',
        'id="legacy-report-content"',
        'id="unitizerModal"',
        'id="disturbedModal"',
        "/weppcloud/static/js/sorttable.js",
        "Project.getInstance()",
    ):
        assert token in rendered
    assert re.search(r'id="checkbox_readonly"[^>]*checked', rendered)
    assert re.search(r'id="checkbox_public"[^>]*checked', rendered)


def test_report_shell_consumer_inventory_has_explicit_content_blocks() -> None:
    consumers = {
        "reports/_base_report.htm": (
            "reports/ash/ash_contaminant.htm",
            "reports/ash/ash_hillslope.htm",
            "reports/ash/ash_watershed.htm",
            "reports/debris_flow.htm",
            "reports/geneva/summary.htm",
            "reports/storm_event_analyzer.htm",
            "reports/wepp/avg_annual_watbal.htm",
            "reports/wepp/avg_annuals_by_landuse.htm",
            "reports/wepp/daily_streamflow_graph.htm",
            "reports/wepp/observed.htm",
            "reports/wepp/return_periods.htm",
            "reports/wepp/sediment_characteristics.htm",
            "reports/wepp/summary.htm",
            "reports/wepp/yearly_watbal.htm",
        ),
        "reports/_page_container.htm": (
            "reports/rhem/avg_annual_summary.htm",
            "reports/rhem/return_periods.htm",
            "reports/wepp/frq_flood.htm",
            "reports/wepp/log.htm",
            "reports/wepp/prep_details.htm",
        ),
    }

    for parent, template_names in consumers.items():
        for template_name in template_names:
            source = (TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")
            assert f'{{% extends "{parent}" %}}' in source
            assert "{% block report_content %}" in source


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


@pytest.mark.parametrize("is_authenticated", [False, True])
def test_interfaces_template_links_diagnostics_from_more_menu_for_all_users(
    jinja_env: Environment,
    is_authenticated: bool,
) -> None:
    template = jinja_env.get_template("interfaces.htm")
    current_user = SimpleNamespace(
        has_role=lambda role: False,
        roles=[],
        is_authenticated=is_authenticated,
    )

    def _url_for(endpoint: str, **values) -> str:
        if endpoint == "weppcloud_site.diagnostics":
            return "/diagnostics/"
        return f"/mock/{endpoint}"

    rendered = template.render(
        user=current_user,
        current_user=current_user,
        url_for=_url_for,
        rq_engine_token="token",
    )

    assert '<summary class="wc-nav__menu-button">More</summary>' in rendered
    assert 'href="/diagnostics/"' in rendered
    assert re.search(r'href="/diagnostics/">\s*Diagnostics\s*</a>', rendered)
    if not is_authenticated:
        assert 'href="/mock/security.login">Login</a>' in rendered


@pytest.mark.parametrize(
    ("role", "present_entries", "absent_entries"),
    [
        (
            "Admin",
            ["RQ Info", "Run Sync", "Create Batch Run", "Runid Query", "Logout"],
            ["Usermod"],
        ),
        (
            "Root",
            ["RQ Info", "Usermod", "Runid Query", "Logout"],
            ["Run Sync", "Create Batch Run"],
        ),
        (
            "Dev",
            ["Runid Query", "Logout"],
            ["RQ Info", "Run Sync", "Create Batch Run", "Usermod"],
        ),
    ],
)
def test_interfaces_more_menu_retains_role_specific_entries(
    jinja_env: Environment,
    role: str,
    present_entries: list[str],
    absent_entries: list[str],
) -> None:
    template = jinja_env.get_template("interfaces.htm")
    current_user = SimpleNamespace(
        has_role=lambda requested: requested == role,
        roles=[SimpleNamespace(name=role)],
        is_authenticated=True,
    )
    rendered = template.render(
        user=current_user,
        current_user=current_user,
        url_for=lambda endpoint, **_values: f"/mock/{endpoint}",
        rq_engine_token="token",
    )
    menu = re.search(
        r'<details class="wc-nav__menu">(?P<body>.*?)</details>',
        rendered,
        re.DOTALL,
    )

    assert menu is not None
    menu_body = menu.group("body")
    for entry in present_entries:
        assert re.search(rf">\s*{re.escape(entry)}\s*</a>", menu_body)
    for entry in absent_entries:
        assert not re.search(rf">\s*{re.escape(entry)}\s*</a>", menu_body)


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


def test_run_header_renders_project_mutation_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    user = SimpleNamespace(has_role=lambda role: role == "PowerUser", roles=["PowerUser"], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})
    ron = SimpleNamespace(
        mods=["disturbed"], runid="test-run", config_stem="test-config",
        nodb_version=3, name="Project A", scenario="Baseline", readonly=True,
        public=True, srid=None,
    )
    rendered = template.render(
        user=user, current_user=user, request=request, current_ron=ron, ron=ron,
        current_ttl=SimpleNamespace(user_disabled=True),
        header_mod_options=[{"id": "disturbed", "label": "Disturbed"}],
    )

    assert 'id="input_name"' in rendered
    assert 'name="input_name"' in rendered
    assert 'data-project-field="name"' in rendered
    assert 'id="input_scenario"' in rendered
    assert 'name="input_scenario"' in rendered
    assert 'data-project-field="scenario"' in rendered
    assert 'data-project-mod="disturbed"' in rendered
    assert re.search(r'id="checkbox_readonly"[^>]*checked', rendered)
    assert re.search(r'id="checkbox_public"[^>]*checked', rendered)
    assert re.search(r'id="checkbox_ttl_disabled"[^>]*checked', rendered)


def test_run_header_renders_interface_maturity_badge_without_mod_dropdown_badges(jinja_env: Environment) -> None:
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
    assert "Feature maturity: Preview" not in rendered
    assert "Stable" in rendered
    assert rendered.count('href="/mock/usersum.view_markdown#feature-maturity-labels"') == 1


@pytest.mark.parametrize(
    "template_name",
    ("header/_run_header_fixed.htm", "reports/_base_report.htm"),
)
def test_run_header_shows_projection_pill_only_after_map_assignment(
    jinja_env: Environment,
    template_name: str,
) -> None:
    template = jinja_env.get_template(template_name)
    anon_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})
    base_ron = {
        "mods": [],
        "runid": "test-run",
        "config_stem": "test-config",
        "nodb_version": 3,
        "name": "",
        "scenario": "",
        "readonly": False,
        "public": False,
    }

    unassigned_ron = SimpleNamespace(**base_ron, srid=None)
    assigned_ron = SimpleNamespace(**base_ron, srid=32611)
    unassigned = template.render(
        user=anon_user,
        current_user=anon_user,
        request=request,
        current_ron=unassigned_ron,
        ron=unassigned_ron,
    )
    assigned = template.render(
        user=anon_user,
        current_user=anon_user,
        request=request,
        current_ron=assigned_ron,
        ron=assigned_ron,
    )

    assert "data-project-projection" not in unassigned
    assert 'data-project-projection="EPSG:32611"' in assigned
    assert ">EPSG:32611</span>" in assigned


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


def test_rap_ts_control_renders_acquisition_and_schedule_contract(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/rap_ts_pure.htm").render(
        rap_schedule=[{"year": 2020}],
    )
    assert 'id="rap_ts_form"' in rendered
    assert 'data-rap-action="run"' in rendered
    assert 'id="hint_build_rap_ts"' in rendered
    assert 'id="rap_ts_schedule_data"' in rendered
    assert '&#34;year&#34;: 2020' in rendered or '"year": 2020' in rendered


def test_openet_ts_control_renders_acquisition_contract(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/openet_ts_pure.htm").render(
        openet_ts=SimpleNamespace(first_year_available=2000, last_year_available=2025),
    )
    assert 'id="openet_ts_form"' in rendered
    assert 'data-openet-action="run"' in rendered
    assert 'id="hint_build_openet_ts"' in rendered
    assert "2000 - 2025" in rendered


def test_disturbed_baer_sbs_control_renders_joint_owner_contract(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/disturbed_sbs_pure.htm").render(
        disturbed=SimpleNamespace(sbs_mode=1, uniform_severity=2, disturbed_fn="sbs.tif", fire_date="05 01 24"),
        baer=None,
        ron=SimpleNamespace(mods={"disturbed"}),
        climate=SimpleNamespace(mods={"rap_ts"}),
    )
    for marker in ('name="sbs_mode"', 'name="input_upload_sbs"', 'data-sbs-action="remove"', 'data-sbs-uniform="2"', 'name="firedate"', 'data-sbs-action="set-firedate"'):
        assert marker in rendered


def test_rangeland_cover_control_renders_modes_defaults_and_build(jinja_env: Environment) -> None:
    cover = SimpleNamespace(mode=2, mods={"rap"}, rap_year=2022, bunchgrass_cover_default=1, forbs_cover_default=2, sodgrass_cover_default=3, shrub_cover_default=4, basal_cover_default=5, rock_cover_default=6, litter_cover_default=7, cryptogams_cover_default=8)
    rendered = jinja_env.get_template("controls/rangeland_cover_pure.htm").render(rangeland_cover=cover)
    for marker in ('name="rangeland_cover_mode"', 'name="rap_year"', 'name="input_bunchgrass_cover"', 'name="input_cryptogams_cover"', 'data-rangeland-action="build"'):
        assert marker in rendered


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


def test_runs0_template_places_ag_fields_between_observed_and_roads() -> None:
    template_path = RUN_0_TEMPLATE_ROOT / "runs0_pure.htm"
    source = template_path.read_text(encoding="utf-8")

    observed_nav_index = source.index('<a href="#observed" class="nav-link">Observed Data</a>')
    ag_fields_nav_index = source.index('<a href="#ag-fields" class="nav-link">Agricultural Fields</a>')
    roads_nav_index = source.index('<a href="#roads" class="nav-link">Roads</a>')
    assert observed_nav_index < ag_fields_nav_index < roads_nav_index

    observed_section_index = source.index('<div data-mod-section="observed"')
    ag_fields_section_index = source.index('<div data-mod-section="ag_fields"')
    roads_section_index = source.index('<div data-mod-section="roads"')
    assert observed_section_index < ag_fields_section_index < roads_section_index


def test_runs0_contrasts_fallback_fails_closed_without_explicit_visibility() -> None:
    source = (RUN_0_TEMPLATE_ROOT / "runs0_pure.htm").read_text(encoding="utf-8")
    assignment = next(
        line for line in source.splitlines()
        if line.startswith("{% set show_omni_contrasts =")
    )

    assert "else false" in assignment


def test_ag_fields_control_renders_required_dom_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/ag_fields_pure.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"ag_fields"}),
        feature_maturity_labels={"ag_fields": "Experimental"},
        wepp_bin_options=[("wepp_dcc52a6", "wepp_dcc52a6"), ("wepp_260606", "wepp_260606")],
    )

    for stage_id in (
        "agfields_stage_boundaries",
        "agfields_stage_subfields",
        "agfields_stage_managements",
        "agfields_stage_run",
        "agfields_stage_watershed",
    ):
        assert f'id="{stage_id}"' in rendered

    for role in (
        "geojson-input",
        "upload-button",
        "upload-status",
        "boundary-file-display",
        "boundary-filename",
        "boundary-summary",
        "duplicate-warning",
        "field-id-select",
        "accessor-display",
        "accessor-input",
        "accessor-resolution-body",
        "confirm-schema-button",
        "schema-status",
        "build-subfields-button",
        "subfields-status",
        "subfields-summary",
        "min-area-input",
        "mapping-chip",
        "open-mapping-button",
        "plantdb-input",
        "plantdb-upload-button",
        "plantdb-status",
        "plantfile-table-body",
        "mapping-table-body",
        "mapping-status",
        "mapping-save-button",
        "unused-mappings",
        "run-button",
        "run-status",
        "wepp-bin-select",
        "clear-runs-button",
        "results-links",
        "integration-scheme-select",
        "integration-run-button",
        "integration-status",
        "integration-clear-button",
        "integration-status-concept_1",
        "integration-results-concept_1",
        "integration-limitation-concept_1",
        "integration-status-concept_2",
        "integration-results-concept_2",
        "integration-limitation-concept_2",
        "integration-status-hybrid",
        "integration-results-hybrid",
        "integration-limitation-hybrid",
    ):
        assert f'data-role="{role}"' in rendered

    for value, label in (
        ("concept_1", "Field-aware hillslope routing (routes fields through downstream OFEs)"),
        (
            "concept_2",
            "Direct sub-field outlet injection (preserves independent sub-field results; no buffer routing)",
        ),
        (
            "hybrid",
            "Connectivity-aware mixed routing (injects channel-connected fields; routes other fields through OFEs)",
        ),
        ("all", "Run all routing schemes (writes three separate results for comparison)"),
    ):
        assert f'<option value="{value}"' in rendered
        assert label in rendered

    assert "Experimental" in rendered
    assert 'role="dialog"' in rendered
    assert 'aria-modal="true"' in rendered
    assert "rasterize" not in rendered.lower()
    assert "polygonize" not in rendered.lower()
    assert "Maximum workers" not in rendered
    assert "Show on Map" not in rendered
    assert "wepp_dcc52a6" in rendered
    assert 'class="pure-button button-error agfields-clear-button"' in rendered
    assert "Use the project UTM EPSG shown in the header for best precision" in rendered


def test_ag_fields_control_renders_boundary_schema_and_subfield_contract(
    jinja_env: Environment,
) -> None:
    """Keep the upload/schema/build browser vocabulary aligned with its route API."""
    template = jinja_env.get_template("controls/ag_fields_pure.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"ag_fields"}),
        feature_maturity_labels={"ag_fields": "Experimental"},
        wepp_bin_options=[],
    )

    assert 'id="agfields_geojson"' in rendered
    assert 'name="field_boundaries"' in rendered
    assert 'accept=".geojson,.json"' in rendered
    assert 'data-action="upload-boundaries"' in rendered
    assert 'id="agfields_field_id_key"' in rendered
    assert 'name="field_id_key"' in rendered
    assert 'id="agfields_rotation_accessor"' in rendered
    assert 'name="rotation_accessor"' in rendered
    assert 'data-action="confirm-schema"' in rendered
    assert 'id="agfields_min_area"' in rendered
    assert 'name="agfields_min_area"' in rendered
    assert 'data-action="build-subfields"' in rendered
    assert 'data-role="boundary-summary"' in rendered
    assert 'data-role="schema-status"' in rendered
    assert 'data-role="subfields-summary"' in rendered


def test_ag_fields_control_renders_plant_database_and_mapping_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/ag_fields_pure.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods={"ag_fields"}),
        feature_maturity_labels={"ag_fields": "Experimental"},
        wepp_bin_options=[],
    )

    assert 'id="agfields_plantdb"' in rendered
    assert 'name="plant_database"' in rendered
    assert 'accept=".zip"' in rendered
    assert 'data-action="upload-plantdb"' in rendered
    assert 'data-action="open-mapping"' in rendered
    assert 'id="agfields_rotation_modal"' in rendered
    assert 'data-role="mapping-table-body"' in rendered
    assert 'data-action="save-mapping"' in rendered
    assert 'data-role="unused-mappings"' in rendered


def test_wepp_control_renders_core_run_and_lifecycle_contract(jinja_env: Environment) -> None:
    class TemplateValue:
        def __getattr__(self, _name: str) -> "TemplateValue":
            return self

        def __bool__(self) -> bool:
            return False

        def __iter__(self):
            return iter(())

        def __round__(self, _ndigits=None) -> int:
            return 0

        def __int__(self) -> int:
            return 0

        def __float__(self) -> float:
            return 0.0

        def __str__(self) -> str:
            return ""

    jinja_env.globals["isfloat"] = lambda _value: False
    jinja_env.globals["hasattr"] = lambda _value, _name: False
    template = jinja_env.get_template("controls/wepp_pure.htm")
    rendered = template.render(
        wepp=TemplateValue(),
        soils=TemplateValue(),
        watershed=SimpleNamespace(clip_hillslopes=False, clip_hillslope_length=0),
        wepp_bin_options=[("wepp_260514", "WEPP 260514")],
        swat=False,
        reveg=False,
    )

    assert 'id="wepp_form"' in rendered
    assert 'id="btn_run_wepp"' in rendered
    assert 'data-wepp-action="run"' in rendered
    assert 'id="wepp_bin"' in rendered
    assert 'name="wepp_bin"' in rendered
    assert 'data-wepp-routine="wepp_watershed"' in rendered
    assert 'data-wepp-action="prep-watershed"' in rendered
    assert 'data-wepp-action="run-watershed"' in rendered
    assert 'id="hint_run_wepp"' in rendered
    assert 'id="wepp_status_panel"' in rendered
    assert 'id="wepp_stacktrace_panel"' in rendered


def test_pmet_advanced_template_renders_payload_and_routine_contract(
    jinja_env: Environment,
) -> None:
    jinja_env.globals["isfloat"] = lambda value: isinstance(value, (int, float))
    template = jinja_env.get_template("controls/wepp_pure_advanced_options/pmet.htm")
    rendered = template.render(
        ron=SimpleNamespace(mods=set()),
        wepp=SimpleNamespace(pmet_kcb=0.95, pmet_rawp=0.8, run_pmet=True),
    )

    assert 'id="pmet_kcb"' in rendered
    assert 'name="pmet_kcb"' in rendered
    assert 'id="pmet_rawp"' in rendered
    assert 'name="pmet_rawp"' in rendered
    assert 'id="checkbox_wepp_pmet"' in rendered
    assert 'data-wepp-routine="pmet"' in rendered


def test_revegetation_advanced_template_renders_cover_transform_contract(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("controls/wepp_pure_advanced_options/revegetation.htm")
    rendered = template.render(
        reveg=SimpleNamespace(
            cover_transform_fn="",
            user_defined_cover_transform=True,
            cover_transform_options=[("forest", "Forest")],
        )
    )

    assert 'id="reveg_scenario"' in rendered
    assert 'name="reveg_scenario"' in rendered
    assert 'id="user_defined_cover_transform_container"' in rendered
    assert 'data-wepp-action="upload-cover-transform"' in rendered


def test_bootstrap_control_renders_privileged_lifecycle_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/bootstrap_pure.htm")
    admin = SimpleNamespace(has_role=lambda role: role == "Admin")
    rendered = template.render(user=admin, swat=True)

    for marker in (
        'data-bootstrap-action="enable"', 'data-bootstrap-action="mint"',
        'data-bootstrap-action="checkout"', 'data-bootstrap-action="disable"',
        'data-wepp-action="run-noprep"', 'data-wepp-action="run-swat-noprep"',
        'id="bootstrap_clone_command"', 'id="bootstrap_commit_select"',
    ):
        assert marker in rendered


def test_dss_export_control_renders_mode_and_enqueue_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/dss_export_pure.htm")
    rendered = template.render(
        wepp=SimpleNamespace(dss_export_mode=2, dss_start_date="01/01/1", dss_end_date="", dss_export_channel_ids=[12], dss_excluded_channel_orders=[2, 4])
    )
    for marker in ('name="dss_export_mode"', 'name="dss_export_channel_ids"', 'name="dss_export_exclude_order_2"', 'data-action="dss-export-run"', 'id="hint_export_dss"'):
        assert marker in rendered


def test_treatments_control_renders_selection_upload_and_build_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/treatments_pure.htm")
    rendered = template.render(
        treatments=SimpleNamespace(mode=SimpleNamespace(value=4), treatments_lookup={"Thin": 1}),
        treatmentoptions=[{"Key": "thin", "Description": "Thin"}],
        landuse_management_mapping_options=[{"Key": "map", "Description": "Map"}],
        landuse=SimpleNamespace(mapping="map"),
    )
    for marker in ('name="treatments_mode"', 'name="input_upload_landuse"', 'accept=".tif,.img"', 'name="landuse_management_mapping_selection"', 'data-treatments-action="build"'):
        assert marker in rendered


def test_debris_flow_control_renders_override_and_run_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("controls/debris_flow_pure.htm")
    rendered = template.render(
        debris_flow=SimpleNamespace(volume=None, datasources=["NOAA"], datasource="NOAA"),
        soils=SimpleNamespace(clay_pct=12.5, liquid_limit=28.0),
    )
    for marker in ('name="clay_pct"', 'name="liquid_limit"', 'name="datasource"', 'data-debris-action="run"', 'id="hint_run_debris_flow"'):
        assert marker in rendered


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


def test_run_header_renders_unauthorized_omni_contrasts_reason_below_label(
    jinja_env: Environment,
) -> None:
    template = jinja_env.get_template("header/_run_header_fixed.htm")
    auth_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    request = SimpleNamespace(view_args={"runid": "test-run", "config": "test-config"})

    rendered = template.render(
        user=auth_user,
        current_user=auth_user,
        request=request,
        current_ron_mods=[],
        header_mod_options=[
            {
                "id": "omni_contrasts",
                "label": "Omni Contrasts",
                "authorized": False,
                "requires_features": ["omni"],
                "toggle_enabled": False,
                "disabled_reason": "Not Authorized",
            }
        ],
    )

    assert 'data-project-mod="omni_contrasts"' in rendered
    assert 'data-project-mod-authorized="false"' in rendered
    assert 'data-project-mod-requires="omni"' in rendered
    assert 'data-project-mod-reason="omni_contrasts"' in rendered
    assert "disabled" in rendered
    assert rendered.index("Omni Contrasts") < rendered.index("Not Authorized")


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


def test_wepp_return_period_template_reports_empty_core_measures(jinja_env: Environment) -> None:
    jinja_env.filters["sort_numeric"] = lambda values, reverse=False: sorted(values, key=float, reverse=reverse)
    jinja_env.globals["unitizer"] = lambda value, _units: value
    jinja_env.globals["unitizer_units"] = lambda units: units

    template = jinja_env.get_template("reports/wepp/return_periods.htm")
    report = SimpleNamespace(
        return_periods={
            "Precipitation Depth": {
                2: {"mo": 6, "da": 15, "year": 1, "Precipitation Depth": 32.0},
            },
            "Sediment Yield": {
                2: {"mo": 6, "da": 15, "year": 1, "Sediment Yield": 0.4},
            },
        },
        units_d={
            "Precipitation Depth": "mm",
            "Runoff": "mm",
            "Peak Discharge": "m^3/s",
            "Sediment Yield": "tonne",
        },
        intervals=[2],
        exclude_yr_indxs=None,
        years=4,
        num_events=12,
        y0=2020,
    )

    rendered = template.render(
        report=report,
        measure_order=["Precipitation Depth", "Runoff", "Peak Discharge", "Sediment Yield"],
        extraneous=False,
        gringorten_correction=False,
        method="cta",
        exclude_yr_indxs=None,
        exclude_months=[6],
        output_scope="baseline",
        chn_topaz_id_options=[],
        chn_topaz_id_of_interest=None,
    )

    assert '<h2 class="wc-heading__subtitle">Runoff</h2>' in rendered
    assert "For CTA, month exclusions define a seasonal analysis window." in rendered
    assert "recalculates the effective days per year from the remaining event counts" in rendered
    assert "Interpret CTA return periods as recurrence within the included season" in rendered
    assert "No runoff events are available for the current year and month selection." in rendered
    assert '<h2 class="wc-heading__subtitle">Peak Discharge</h2>' in rendered
    assert "No peak discharge events are available for the current year and month selection." in rendered
    assert 'data-report-table="runoff"' not in rendered
    assert 'data-report-table="peak-discharge"' not in rendered


def test_map_templates_do_not_use_application_role_for_canvas() -> None:
    map_template = (TEMPLATE_ROOT / "controls/map_pure_gl.htm").read_text(encoding="utf-8")
    runs_template = (TEMPLATE_ROOT / "user/runs2.html").read_text(encoding="utf-8")

    assert 'id="mapid" class="wc-map__canvas" role="application"' not in map_template
    assert 'id="runs-map-canvas" class="wc-map__canvas" role="application"' not in runs_template
    assert 'id="mapid" class="wc-map__canvas" aria-label="Watershed map viewport"' in map_template
    assert 'id="runs-map-canvas" class="wc-map__canvas" aria-label="Runs map viewport"' in runs_template


def test_map_template_renders_orchestration_actions_and_targets(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/map_pure_gl.htm").render()

    for token in (
        'form id="setloc_form"',
        'id="input_centerloc"',
        'name="input_centerloc"',
        'data-map-action="go"',
        'data-map-action="find-topaz"',
        'data-map-action="find-wepp"',
        'id="mapid" class="wc-map__canvas" aria-label="Watershed map viewport"',
        'id="drilldown"',
        'id="mouseelev"',
    ):
        assert token in rendered

    assert rendered.index('id="input_centerloc"') < rendered.index('data-map-action="go"')
    assert rendered.index('data-map-action="find-topaz"') < rendered.index('data-map-action="find-wepp"')


def test_map_template_renders_layer_defaults_and_legend_hosts(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/map_pure_gl.htm").render()

    assert '<input type="checkbox" id="sbs_color_shift_toggle">' in rendered
    assert 'id="sbs_color_shift_toggle" checked' not in rendered
    assert re.search(r'id="sub_cmap_radio_default"[^>]*checked', rendered)
    assert 'id="sub_legend" class="wc-map-legend" aria-live="polite"' in rendered
    assert 'id="sbs_legend" class="wc-map-legend" aria-live="polite"' in rendered


def test_outlet_template_renders_selection_modes_and_lifecycle_targets(jinja_env: Environment) -> None:
    rendered = jinja_env.get_template("controls/set_outlet_pure.htm").render()

    for token in (
        'form id="set_outlet_form"',
        'name="set_outlet_mode"',
        'id="set_outlet_mode_cursor"',
        'id="set_outlet_mode_entry"',
        'data-outlet-action="cursor-toggle"',
        'data-outlet-action="entry-submit"',
        'id="input_set_outlet_entry"',
        'data-outlet-entry-field=""',
        'id="hint_set_outlet_cursor"',
        'id="set_outlet_status_panel"',
        'id="set_outlet_stacktrace_panel"',
    ):
        assert token in rendered

    assert re.search(r'id="set_outlet_mode_cursor"[^>]*checked', rendered)
    assert 'id="set_outlet_mode_entry" checked' not in rendered
    assert re.search(r'id="set_outlet_mode1_controls"[^>]*hidden', rendered)


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
