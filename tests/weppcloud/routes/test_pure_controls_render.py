from __future__ import annotations

import json
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
