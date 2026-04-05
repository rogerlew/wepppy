from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Blueprint, Flask

from wepppy.weppcloud.routes._security import oauth as oauth_module

pytestmark = pytest.mark.routes


def test_google_callback_access_denied_redirects_without_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        OAUTH_PROVIDERS={"google": {"enabled": True}},
        SECURITY_LOGIN_ERROR_VIEW="security_ui.login",
    )

    security_ui_bp = Blueprint("security_ui", __name__)

    @security_ui_bp.get("/login")
    def login():
        return "login"

    app.register_blueprint(security_ui_bp)
    app.register_blueprint(oauth_module.security_oauth_bp)

    def _unexpected_client_lookup(*_args, **_kwargs):
        raise AssertionError("OAuth client lookup should be skipped for callback errors.")

    monkeypatch.setattr(oauth_module, "ensure_oauth_client", _unexpected_client_lookup)

    with app.test_client() as client:
        with client.session_transaction() as session_state:
            session_state[oauth_module._SESSION_PKCE_KEY] = {"google": "pkce-value"}
            session_state[oauth_module._SESSION_NEXT_KEY] = {"google": "/runs/demo/cfg"}

        response = client.get(
            "/oauth/google/callback?error=access_denied&state=abc123",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

        with client.session_transaction() as session_state:
            assert oauth_module._SESSION_PKCE_KEY not in session_state
            assert oauth_module._SESSION_NEXT_KEY not in session_state
            assert ("warning", "Sign-in was canceled.") in session_state.get("_flashes", [])
