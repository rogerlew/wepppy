from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest
from flask import Flask
from jinja2 import DebugUndefined, Environment, FileSystemLoader

import wepppy.weppcloud.routes.weppcloud_site as site_module

pytestmark = [pytest.mark.routes, pytest.mark.unit]


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    templates = Path(__file__).resolve().parents[3] / "wepppy" / "weppcloud" / "templates"
    environment = Environment(loader=FileSystemLoader(str(templates)), undefined=DebugUndefined)
    environment.globals.update(csrf_token=lambda: "csrf", controllers_gl_expected_build_id="test")
    return environment


def test_config_builder_route_is_distinct_and_authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.config.update(TESTING=True, LOGIN_DISABLED=True, SECRET_KEY="test")
    app.register_blueprint(site_module.weppcloud_site_bp)
    captured: dict[str, object] = {}

    def render(template_name: str, **context: object) -> str:
        captured.update(template_name=template_name, context=context)
        return "ok"

    monkeypatch.setattr(site_module, "render_template", render)
    monkeypatch.setattr(site_module, "current_user", SimpleNamespace(is_authenticated=True))
    with app.test_client() as client:
        response = client.get("/config-builder/")

    assert response.status_code == 200
    assert captured["template_name"] == "config_builder.htm"
    rules = {(rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()}
    assert ("/interfaces/", "weppcloud_site.interfaces") in rules
    assert ("/config-builder/", "weppcloud_site.config_builder") in rules


def test_config_builder_template_has_one_page_accessible_contract(jinja_env: Environment) -> None:
    template = jinja_env.get_template("config_builder.htm")
    user = SimpleNamespace(is_authenticated=True)
    rendered = template.render(
        user=user,
        current_user=user,
        url_for=lambda endpoint, **_values: f"/{endpoint}/",
        static_url=lambda path: f"/static/{path}",
    )

    assert rendered.count("<form") == 1
    assert 'data-description-url="/rq-engine/api/project-config/builder"' in rendered
    assert 'data-validation-url="/rq-engine/api/project-config/builder/validate"' in rendered
    assert 'data-creation-url="/rq-engine/api/project-config/builder/create"' in rendered
    for field in (
        "locale", "dem", "delineation_backend", "watershed_representation",
        "wepp_binary",
        "soil", "landuse", "climate",
    ):
        assert f'for="builder-{field}"' in rendered
        assert f'name="{field}"' in rendered
        assert f'data-builder-field-error="{field}"' in rendered
    assert 'data-builder-error-summary role="alert" tabindex="-1"' in rendered
    assert 'data-builder-status role="status" aria-live="polite" tabindex="-1"' in rendered
    assert "Review selections" not in rendered
    assert "data-builder-validate" not in rendered
    assert 'data-builder-review hidden' in rendered
    assert 'data-builder-create disabled' in rendered
    assert "@media (max-width: 48rem)" in rendered
    assert 'name="config"' not in rendered
    assert 'name="filename"' not in rendered
    assert 'name="rq_token"' not in rendered
    assert "config-manifest.json" in rendered


@pytest.mark.parametrize("role", ["PowerUser", "Dev", "Admin", "Root"])
def test_interfaces_template_keeps_named_creation_and_poweruser_builder_menu_link(
    jinja_env: Environment,
    role: str,
) -> None:
    template = jinja_env.get_template("interfaces.htm")
    user = SimpleNamespace(
        is_authenticated=True,
        has_role=lambda candidate: candidate == role,
    )
    rendered = template.render(
        user=user,
        current_user=user,
        url_for=lambda endpoint, **values: (
            "/config-builder/" if endpoint == "weppcloud_site.config_builder"
            else f"/static/{values.get('filename', '')}" if endpoint == "static"
            else f"/{endpoint}/"
        ),
        static_url=lambda path: f"/static/{path}",
        visible_config_ids={"disturbed9002"},
        config_registry_map={"disturbed9002": SimpleNamespace(id="disturbed9002")},
        config_maturity_labels={"disturbed9002": "Stable"},
        maturity_definition_href="/guide#maturity",
    )

    assert 'href="/config-builder/"' in rendered
    assert ">\n          Config Builder\n        </a>" in rendered
    assert 'id="config-builder-entry-heading"' not in rendered
    assert 'method="post" action="/rq-engine/create/"' in rendered
    assert 'name="config" value="disturbed9002"' in rendered


@pytest.mark.parametrize("roles", [set(), {"User"}])
def test_interfaces_template_hides_builder_discovery_from_ordinary_users(
    jinja_env: Environment,
    roles: set[str],
) -> None:
    template = jinja_env.get_template("interfaces.htm")
    user = SimpleNamespace(
        is_authenticated=True,
        has_role=lambda role: role in roles,
    )
    rendered = template.render(
        user=user,
        current_user=user,
        url_for=lambda endpoint, **values: (
            "/config-builder/" if endpoint == "weppcloud_site.config_builder"
            else f"/static/{values.get('filename', '')}" if endpoint == "static"
            else f"/{endpoint}/"
        ),
        static_url=lambda path: f"/static/{path}",
        visible_config_ids={"disturbed9002"},
        config_registry_map={"disturbed9002": SimpleNamespace(id="disturbed9002")},
        config_maturity_labels={"disturbed9002": "Stable"},
        maturity_definition_href="/guide#maturity",
    )

    assert 'href="/config-builder/"' not in rendered
    assert 'id="config-builder-entry-heading"' not in rendered
