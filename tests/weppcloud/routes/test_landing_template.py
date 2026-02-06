from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import DebugUndefined, Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPO_ROOT / "wepppy" / "weppcloud" / "templates"

pytestmark = pytest.mark.routes


def test_landing_template_uses_run_locations_endpoint() -> None:
    env = Environment(
        loader=FileSystemLoader([str(TEMPLATE_ROOT)]),
        undefined=DebugUndefined,
    )
    called: dict[str, int] = {}

    def url_for(endpoint: str, **_kwargs: object) -> str:
        called[endpoint] = called.get(endpoint, 0) + 1
        if endpoint == "weppcloud_site.landing_run_locations_root":
            return "/run-locations.json"
        if endpoint == "weppcloud_site.interfaces":
            return "/interfaces/"
        if endpoint == "weppcloud_site.about":
            return "/about/"
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    env.globals.update(url_for=url_for)
    template = env.get_template("landing.htm")
    rendered = template.render()

    assert "weppcloud_site.landing_run_locations_root" in called
    assert "RUN_DATA_URL" in rendered
    assert "/run-locations.json" in rendered
