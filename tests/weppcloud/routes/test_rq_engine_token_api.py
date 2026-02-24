from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.weppcloud_site as weppcloud_site_module
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.routes


def _build_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")
    return app


def test_issue_rq_engine_token_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-token")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Authentication required."


def test_issue_rq_engine_token_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"token": "rq-user-token"}


def test_issue_rq_engine_token_blocks_cross_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_issue_rq_engine_token_accepts_default_https_port_equivalence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={
                "Origin": "https://localhost",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "localhost:443",
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"token": "rq-user-token"}


def test_issue_rq_engine_token_accepts_configured_external_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    app.config["OAUTH_REDIRECT_SCHEME"] = "https"
    app.config["OAUTH_REDIRECT_HOST"] = "wc.bearhive.duckdns.org"
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "https://wc.bearhive.duckdns.org"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"token": "rq-user-token"}


def test_issue_rq_engine_token_uses_expected_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        is_anonymous = False
        id = 42
        email = "user@example.com"
        roles = [SimpleNamespace(name="Admin"), SimpleNamespace(name="Hydrologist")]

        @staticmethod
        def get_id() -> str:
            return "42"

    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        DummyUser(),
        raising=False,
    )

    captured: dict[str, object] = {}

    def _fake_issue_token(subject: str, **kwargs):
        captured["subject"] = subject
        captured["kwargs"] = kwargs
        return {"token": "issued-token"}

    monkeypatch.setattr(weppcloud_site_module.auth_tokens, "issue_token", _fake_issue_token)

    token = weppcloud_site_module._issue_rq_engine_token()

    assert token == "issued-token"
    assert captured["subject"] == "42"
    kwargs = captured["kwargs"]
    assert kwargs["scopes"] == ["rq:enqueue", "rq:status", "rq:export"]
    assert kwargs["audience"] == "rq-engine"
    extra_claims = kwargs["extra_claims"]
    assert extra_claims["token_class"] == "user"
    assert extra_claims["email"] == "user@example.com"
    assert extra_claims["roles"] == ["Admin", "Hydrologist"]
    assert isinstance(extra_claims["jti"], str)
    assert extra_claims["jti"]


def test_issue_rq_engine_token_handles_jwt_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    def _raise_config_error():
        raise auth_tokens.JWTConfigurationError("missing secret")

    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        _raise_config_error,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "JWT configuration error: missing secret"


def test_session_heartbeat_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/session-heartbeat")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Authentication required."


def test_session_heartbeat_blocks_cross_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_heartbeat_accepts_configured_external_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    app.config["OAUTH_REDIRECT_SCHEME"] = "https"
    app.config["OAUTH_REDIRECT_HOST"] = "wc.bearhive.duckdns.org"
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={"Origin": "https://wc.bearhive.duckdns.org"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True


def test_session_heartbeat_updates_session(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={"Origin": "http://localhost"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["ok"] is True
        assert isinstance(payload["heartbeat_at"], int)

        with client.session_transaction() as sess:
            assert isinstance(sess.get("_heartbeat_ts"), int)


def test_issue_rq_engine_token_blocks_missing_origin_and_referer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-token")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_issue_rq_engine_token_allows_same_origin_fetch_metadata_without_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Sec-Fetch-Site": "same-origin"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"token": "rq-user-token"}


def test_issue_rq_engine_token_blocks_cross_site_fetch_metadata_without_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Sec-Fetch-Site": "cross-site"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_heartbeat_blocks_missing_origin_and_referer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/session-heartbeat")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."

def test_reset_browser_state_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/reset-browser-state",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Authentication required."


def test_reset_browser_state_blocks_cross_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/reset-browser-state",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_reset_browser_state_blocks_missing_origin_and_referer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/reset-browser-state")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_reset_browser_state_accepts_same_origin_referer_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["custom"] = "present"

        response = client.post(
            "/weppcloud/api/auth/reset-browser-state",
            headers={"Referer": "http://localhost/weppcloud/profile"},
        )

        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert len(sess.keys()) == 0


def test_reset_browser_state_clears_session_and_auth_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    app.config["SESSION_COOKIE_NAME"] = "wc_session"
    app.config["SESSION_COOKIE_PATH"] = "/weppcloud/"
    app.config["SESSION_COOKIE_DOMAIN"] = None
    app.config["REMEMBER_COOKIE_NAME"] = "remember_me"
    app.config["REMEMBER_COOKIE_PATH"] = "/weppcloud"
    app.config["REMEMBER_COOKIE_DOMAIN"] = ".example.com"

    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "123"
            sess["custom"] = "present"

        response = client.post(
            "/weppcloud/api/auth/reset-browser-state",
            headers={"Origin": "http://localhost"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["ok"] is True
        assert payload["login_url"] == "/login"
        assert payload["cleared_session_keys"] >= 1

        with client.session_transaction() as sess:
            assert len(sess.keys()) == 0

    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    set_cookie_headers = response.headers.getlist("Set-Cookie")

    assert any(header.startswith("wc_session=;") for header in set_cookie_headers)
    assert any(header.startswith("remember_me=;") for header in set_cookie_headers)

    wc_session_headers = [
        header for header in set_cookie_headers if header.startswith("wc_session=;")
    ]
    assert any("Path=/weppcloud" in header for header in wc_session_headers)
    assert any("Path=/weppcloud/" in header for header in wc_session_headers)
    remember_headers = [
        header for header in set_cookie_headers if header.startswith("remember_me=;")
    ]
    assert any("Domain=example.com" in header for header in remember_headers)
    assert any("Path=/weppcloud" in header for header in remember_headers)
    assert any("Path=/weppcloud/" in header for header in remember_headers)
    assert len(remember_headers) >= 2
