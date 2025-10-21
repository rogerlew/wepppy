from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import DebugUndefined, Environment, FileSystemLoader

TEMPLATE_ROOT = Path("wepppy/weppcloud/templates")
PURE_TEMPLATES = [
    "controls/path_cost_effective_pure.htm",
]


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_ROOT)), undefined=DebugUndefined)
    stub_user = SimpleNamespace(has_role=lambda role: False, roles=[])
    env.globals.update(
        url_for=lambda *args, **kwargs: "",
        url_for_run=lambda *args, **kwargs: "",
        site_prefix="",
        user=stub_user,
        current_user=stub_user,
        ron=SimpleNamespace(mods=set()),
    )
    return env


@pytest.mark.parametrize("template_name", PURE_TEMPLATES)
def test_pure_control_renders(template_name: str, jinja_env: Environment) -> None:
    template = jinja_env.get_template(template_name)
    template.render()
