from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.weppcloud_site as site_module
from wepppy.weppcloud.feature_registry.schema import ConfigSpec

pytestmark = [pytest.mark.routes, pytest.mark.unit]


class _User:
    def __init__(self, roles: set[str] | None = None) -> None:
        self._roles = set(roles or set())
        self.is_authenticated = True

    def has_role(self, role: str) -> bool:
        return role in self._roles


@pytest.fixture()
def interfaces_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(site_module.weppcloud_site_bp)

    current_user = _User(set())
    monkeypatch.setattr(site_module, "current_user", current_user)

    entries = (
        ConfigSpec(
            id="user-config",
            label="User Config",
            cfg_path="wepppy/nodb/configs/disturbed9002.cfg",
            maturity="stable",
            internal_reason=None,
            embargo_until=None,
            min_role="user",
            requires_backend="any",
            replaced_by=None,
        ),
        ConfigSpec(
            id="power-config",
            label="Power Config",
            cfg_path="wepppy/nodb/configs/disturbed9002.cfg",
            maturity="preview",
            internal_reason=None,
            embargo_until=None,
            min_role="poweruser",
            requires_backend="any",
            replaced_by=None,
        ),
        ConfigSpec(
            id="admin-config",
            label="Admin Config",
            cfg_path="wepppy/nodb/configs/disturbed9002.cfg",
            maturity="internal",
            internal_reason="beta",
            embargo_until=None,
            min_role="dev",
            requires_backend="any",
            replaced_by=None,
        ),
    )
    monkeypatch.setattr(site_module, "load_config_registry", lambda: entries)
    monkeypatch.setattr(site_module, "config_registry_by_id", lambda: {entry.id: entry for entry in entries})
    monkeypatch.setattr(
        site_module,
        "url_for",
        lambda endpoint, **values: "/usersum/view/weppcloud/user-guide.md",
    )

    captured: dict[str, object] = {}

    def _fake_render(template_name: str, **context):
        captured["template_name"] = template_name
        captured["context"] = context
        return "ok"

    monkeypatch.setattr(site_module, "render_template", _fake_render)

    with app.test_client() as client:
        yield client, captured, current_user


def test_interfaces_route_filters_visible_configs_for_regular_user(interfaces_client) -> None:
    client, captured, current_user = interfaces_client
    current_user._roles.clear()

    response = client.get("/interfaces/")

    assert response.status_code == 200
    assert captured["template_name"] == "interfaces.htm"
    visible_config_ids = captured["context"]["visible_config_ids"]
    assert visible_config_ids == {"user-config"}
    assert captured["context"]["config_maturity_labels"] == {
        "user-config": "Stable",
        "power-config": "Preview",
        "admin-config": "Internal",
    }
    assert captured["context"]["maturity_definition_href"].endswith("#feature-maturity-labels")


def test_interfaces_route_filters_visible_configs_for_root_user(interfaces_client) -> None:
    client, captured, current_user = interfaces_client
    current_user._roles = {"Root"}

    response = client.get("/interfaces/")

    assert response.status_code == 200
    assert captured["template_name"] == "interfaces.htm"
    visible_config_ids = captured["context"]["visible_config_ids"]
    assert visible_config_ids == {"user-config", "power-config", "admin-config"}
    assert captured["context"]["maturity_definition_href"].endswith("#feature-maturity-labels")
