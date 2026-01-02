from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import DebugUndefined, Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "templates"
COMMAND_BAR_TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "command_bar" / "templates"
PURE_TEMPLATES = [
    "controls/path_cost_effective_pure.htm",
    "reports/storm_event_analyzer.htm",
]


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader([str(TEMPLATE_ROOT), str(COMMAND_BAR_TEMPLATE_ROOT)]),
        undefined=DebugUndefined,
    )
    stub_user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=False)
    stub_unitizer = SimpleNamespace(is_english=False, preferences={})
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
    )
    return env


@pytest.mark.parametrize("template_name", PURE_TEMPLATES)
def test_pure_control_renders(template_name: str, jinja_env: Environment) -> None:
    template = jinja_env.get_template(template_name)
    template.render()
