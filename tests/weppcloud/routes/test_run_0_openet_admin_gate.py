from __future__ import annotations

import importlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask, render_template

pytestmark = pytest.mark.routes


class _RoleUser:
    def __init__(self, roles: set[str] | None = None) -> None:
        self._roles = set(roles or set())
        self.is_authenticated = True

    def has_role(self, role: str) -> bool:
        return role in self._roles


@pytest.fixture()
def run0_module():
    return importlib.reload(importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp"))


@pytest.fixture()
def run0_client(run0_module):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="run0-openet-test")
    app.register_blueprint(run0_module.run_0_bp)
    with app.test_client() as client:
        yield client, run0_module


@pytest.fixture()
def run0_template_app(run0_module):
    template_dir = Path(run0_module.__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config.update(TESTING=True, SECRET_KEY="run0-openet-template-test")
    return app


def _bootstrap_context(user_roles: set[str]) -> dict:
    user = _RoleUser(user_roles)
    return {
        "ron": SimpleNamespace(
            mods=["openet_ts"],
            boundary=None,
            runid="run-1",
            config_stem="cfg",
            readonly=False,
            cellsize=30,
            center0=[-117.0, 46.0],
            zoom0=10,
            has_sbs=False,
            has_dem=False,
            has_ash_results=False,
        ),
        "site_prefix": "/weppcloud",
        "current_user": user,
        "user": user,
        "current_ttl": None,
        "rq_job_ids": {},
        "playwright_load_all": False,
        "watershed": SimpleNamespace(has_channels=False, has_subcatchments=False, has_outlet=False),
        "landuse": SimpleNamespace(has_landuse=False, mode="none", single_selection=False),
        "soils": SimpleNamespace(has_soils=False, mode="none", single_dbselection=False),
        "climate": SimpleNamespace(
            precip_scaling_mode=None,
            has_station=False,
            has_climate=False,
            has_observed=False,
        ),
        "observed": SimpleNamespace(results=None),
        "rangeland_cover": SimpleNamespace(has_covers=False),
        "wepp": SimpleNamespace(
            has_run=False,
            dss_export_mode=0,
            has_dss_zip=False,
            bootstrap_enabled=False,
        ),
        "bootstrap_admin_disabled": False,
        "bootstrap_is_anonymous": True,
        "omni_has_ran_scenarios": False,
        "omni_has_ran_contrasts": False,
        "omni": None,
        "rhem": SimpleNamespace(has_run=False),
        "ash": SimpleNamespace(ash_depth_mode=None),
        "disturbed": SimpleNamespace(sbs_mode=0, uniform_severity=None),
        "baer": None,
        "toc_task_emojis": {},
        "disabled_controllers": [],
    }


def _extract_openet_flag(js_text: str) -> str:
    match = re.search(r'"openet_ts"\s*:\s*(true|false)', js_text)
    assert match is not None
    return match.group(1)


def test_view_mod_section_openet_denied_for_non_admin(
    run0_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module = run0_client
    monkeypatch.setattr(module, "_openet_admin_enabled", lambda *, playwright_load_all: False)

    response = client.get("/runs/run-1/cfg/view/mod/openet_ts")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["error"]["message"] == "OpenET Time Series is restricted to Admin users"


def test_view_mod_section_openet_allows_admin(
    run0_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module = run0_client
    monkeypatch.setattr(module, "_openet_admin_enabled", lambda *, playwright_load_all: True)
    monkeypatch.setattr(
        module,
        "_build_runs0_context",
        lambda runid, config, playwright_load_all=False: {
            "mod_visibility": {"openet_ts": True},
            "dummy": True,
        },
    )

    render_calls: list[str] = []

    def fake_render(template_name: str, **_kwargs) -> str:
        render_calls.append(template_name)
        return f"<{template_name}>"

    monkeypatch.setattr(module, "render_template", fake_render)

    response = client.get("/runs/run-1/cfg/view/mod/openet_ts")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["mod"] == "openet_ts"
    assert render_calls == [
        "controls/openet_ts_pure.htm",
        "run_0/mod_section_wrapper.htm",
    ]


def test_run_page_bootstrap_openet_flag_false_for_non_admin(run0_template_app) -> None:
    context = _bootstrap_context(set())
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_openet_flag(js) == "false"


def test_run_page_bootstrap_openet_flag_true_for_admin(run0_template_app) -> None:
    context = _bootstrap_context({"Admin"})
    with run0_template_app.app_context():
        js = render_template("run_page_bootstrap.js.j2", **context)
    assert _extract_openet_flag(js) == "true"
