from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Blueprint, Flask, url_for
from jinja2 import DictLoader, Environment, select_autoescape
from werkzeug.middleware.proxy_fix import ProxyFix

pytestmark = pytest.mark.routes

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_TEMPLATE = (
    REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "user" / "profile.html"
)


class _Accounts:
    def __init__(self, accounts: list[SimpleNamespace]) -> None:
        self._accounts = accounts

    def all(self) -> list[SimpleNamespace]:
        return self._accounts


class _User:
    def __init__(
        self,
        *,
        roles: tuple[str, ...] = (),
        accounts: list[SimpleNamespace] | None = None,
        first_name: str = "Test",
        last_name: str = "User",
        email: str = "user@example.test",
    ) -> None:
        self.id = 42
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.roles = [SimpleNamespace(name=name) for name in roles]
        self.oauth_accounts = _Accounts(accounts or [])

    def has_role(self, role: str) -> bool:
        return any(item.name == role for item in self.roles)


@pytest.fixture()
def profile_renderer() -> tuple[Flask, Environment]:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "profile-render-test"
    env = Environment(
        loader=DictLoader(
            {
                "security/_layout.html": "{% block content %}{% endblock %}",
                "security/_macros.html": (
                    "{% macro render_field_with_errors() %}{% endmacro %}"
                    "{% macro render_checkbox_with_errors() %}{% endmacro %}"
                    "{% macro render_field() %}{% endmacro %}"
                ),
                "user/profile.html": PROFILE_TEMPLATE.read_text(encoding="utf-8"),
            }
        ),
        autoescape=select_autoescape(("html",)),
    )
    env.globals.update(
        csrf_token=lambda: "csrf-value",
        url_for=lambda endpoint, **values: (
            {
                "security.logout": "/logout",
                "security.change_password": "/change",
                "security_oauth.disconnect": (
                    f"/oauth/disconnect/{values.get('provider', '')}"
                ),
                "weppcloud_site.diagnostics": "/diagnostics/",
                "user.mint_profile_token": "/profile/mint-token",
                "user.preferences": "/preferences",
            }[endpoint]
        ),
    )
    return app, env


def _render_profile(
    profile_renderer: tuple[Flask, Environment],
    user: _User,
    *,
    can_mint_profile_token: bool,
) -> str:
    app, env = profile_renderer
    with app.test_request_context("/profile"):
        return env.get_template("user/profile.html").render(
            user=user,
            oauth_providers={
                "github": SimpleNamespace(name="GitHub"),
                "google": SimpleNamespace(name="Google"),
            },
            can_mint_profile_token=can_mint_profile_token,
        )


def test_profile_renders_escaped_readonly_identity_and_owned_navigation(
    profile_renderer: tuple[Flask, Environment],
) -> None:
    hostile = '<img src=x onerror="window.pwned=true">'
    rendered = _render_profile(
        profile_renderer,
        _User(
            first_name=hostile,
            last_name="User",
            email=hostile,
            roles=(),
        ),
        can_mint_profile_token=False,
    )

    assert hostile not in rendered
    assert rendered.count("&lt;img src=x onerror=") == 2
    assert "window.pwned=true" in rendered
    assert "<dt class=\"wc-profile-details__label\">Roles</dt>" in rendered
    assert "None assigned" in rendered
    assert "No social providers linked." in rendered
    assert 'href="/change"' in rendered
    assert 'href="/logout"' in rendered
    assert 'href="/diagnostics/"' in rendered
    assert 'href="/preferences"' in rendered
    assert "data-profile-token-root" not in rendered


def test_profile_renders_provider_disconnect_and_privileged_token_contract(
    profile_renderer: tuple[Flask, Environment],
) -> None:
    rendered = _render_profile(
        profile_renderer,
        _User(
            roles=("Dev", "PowerUser"),
            accounts=[
                SimpleNamespace(provider="google", email="google@example.test"),
                SimpleNamespace(provider="github", email="github@example.test"),
            ],
        ),
        can_mint_profile_token=True,
    )

    assert rendered.index("GitHub") < rendered.index("Google")
    assert 'action="/oauth/disconnect/github"' in rendered
    assert 'action="/oauth/disconnect/google"' in rendered
    assert rendered.count('name="csrf_token" value="csrf-value"') == 2
    assert 'data-mint-endpoint="/profile/mint-token"' in rendered
    assert 'data-profile-token-action="mint"' in rendered
    assert 'data-profile-token-field="token"' in rendered
    assert "readonly" in rendered
    assert 'data-profile-token-action="copy-token"' in rendered
    assert "usermod_PowerUser_" not in rendered
    assert 'fetch("/tasks/usermod/"' not in rendered


def test_profile_escapes_role_provider_and_provider_email(
    profile_renderer: tuple[Flask, Environment],
) -> None:
    hostile = '<svg onload="window.pwned=true">'
    rendered = _render_profile(
        profile_renderer,
        _User(
            roles=(hostile,),
            accounts=[SimpleNamespace(provider=hostile, email=hostile)],
        ),
        can_mint_profile_token=False,
    )

    assert hostile not in rendered
    assert "&lt;svg onload=" in rendered
    assert "window.pwned=true" in rendered


def test_profile_password_link_uses_prefix_aware_security_endpoint() -> None:
    app = Flask(__name__)
    security = Blueprint("security", __name__)

    @security.get("/change", endpoint="change_password")
    def change_password() -> str:
        return "change"

    app.register_blueprint(security)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

    @app.get("/profile-link")
    def profile_link() -> str:
        return url_for("security.change_password")

    response = app.test_client().get(
        "/profile-link",
        headers={"X-Forwarded-Prefix": "/weppcloud"},
    )

    assert response.get_data(as_text=True) == "/weppcloud/change"
    source = PROFILE_TEMPLATE.read_text(encoding="utf-8")
    assert "url_for('security.change_password')" in source
    assert 'href="../change"' not in source
