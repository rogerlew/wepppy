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


def _reset_operator_rate_limit_state() -> None:
    with weppcloud_site_module._OPERATOR_TOKEN_RATE_LIMIT_LOCK:
        weppcloud_site_module._OPERATOR_TOKEN_RATE_LIMIT_BUCKETS.clear()


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
    assert payload["error_id"]


def test_issue_rq_engine_token_handles_unexpected_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    def _raise_unexpected_error():
        raise RuntimeError("boom")

    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        _raise_unexpected_error,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "Failed to issue rq-engine token."
    assert payload["error_id"]


def test_issue_rq_engine_operator_token_requires_bearer_auth() -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-operator-token")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Bearer token required."


def test_issue_rq_engine_operator_token_handles_jwt_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()

    def _raise_config_error(_token: str, audience: str | None = None):
        raise auth_tokens.JWTConfigurationError("missing secret")

    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        _raise_config_error,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "JWT configuration error: missing secret"
    assert payload["error_id"]


def test_issue_rq_engine_operator_token_rejects_missing_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "token_class": "service",
            "jti": "jti-1",
            "scope": "rq:read",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Bearer token missing subject claim."


def test_issue_rq_engine_operator_token_rejects_missing_jti(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "svc-1",
            "token_class": "service",
            "scope": "rq:read",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Bearer token missing jti claim."


def test_issue_rq_engine_operator_token_rejects_disallowed_token_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "session-1",
            "token_class": "session",
            "jti": "jti-1",
            "scope": "rq:read",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 403
    assert response.get_json()["error"]["message"] == "Bearer token class not authorized for operator bootstrap."


def test_issue_rq_engine_operator_token_rejects_revoked_token(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "svc-1",
            "token_class": "service",
            "jti": "revoked-jti",
            "scope": "rq:read",
        },
    )
    monkeypatch.setattr(weppcloud_site_module, "_operator_token_is_revoked", lambda jti: True)

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 403
    assert response.get_json()["error"]["message"] == "Bearer token has been revoked."


def test_issue_rq_engine_operator_token_handles_revocation_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "svc-1",
            "token_class": "service",
            "jti": "revocation-jti",
            "scope": "rq:read",
        },
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_operator_token_is_revoked",
        lambda jti: (_ for _ in ()).throw(weppcloud_site_module.redis.RedisError("redis down")),
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
        )

    assert response.status_code == 503
    assert response.get_json()["error"]["message"] == "Token revocation service unavailable. Retry with backoff."
    assert response.headers.get("Retry-After") == "5"


def test_issue_rq_engine_operator_token_rejects_invalid_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: (_ for _ in ()).throw(auth_tokens.JWTDecodeError("bad token")),
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer invalid"},
        )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Invalid bearer token."


def test_issue_rq_engine_operator_token_rejects_non_json_body_with_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token", "Content-Type": "text/plain"},
            data="requested_scopes=rq:read",
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "Operator token bootstrap request body must use application/json."


def test_issue_rq_engine_operator_token_rejects_malformed_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token", "Content-Type": "application/json"},
            data="{bad-json",
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "Malformed JSON request body."


def test_issue_rq_engine_operator_token_rejects_non_object_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token", "Content-Type": "application/json"},
            data='["rq:read"]',
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "JSON request body must be an object."


def test_issue_rq_engine_operator_token_defaults_to_read_scope_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status rq:enqueue",
            "email": "user@example.com",
            "roles": ["Admin"],
            "groups": ["ops"],
        },
    )

    captured: dict[str, object] = {}

    def _fake_issue_token(subject: str, **kwargs):
        captured["subject"] = subject
        captured["kwargs"] = kwargs
        return {
            "token": "operator-token",
            "claims": {
                "token_class": "user",
                "aud": "rq-engine",
                "iat": 1700000000,
                "exp": 1700000900,
            },
        }

    monkeypatch.setattr(weppcloud_site_module.auth_tokens, "issue_token", _fake_issue_token)

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["requested_scopes"] == ["rq:read"]
    assert payload["granted_scopes"] == ["rq:read"]
    assert payload["token"] == "operator-token"
    assert response.headers.get("Cache-Control") == "no-store"

    assert captured["subject"] == "42"
    kwargs = captured["kwargs"]
    assert kwargs["scopes"] == ["rq:read"]
    assert kwargs["audience"] == "rq-engine"


def test_issue_rq_engine_operator_token_rejects_unknown_requested_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={"requested_scopes": ["rq:read", "rq:bogus"]},
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert "Unknown requested scope(s): rq:bogus." == payload["error"]["message"]


def test_issue_rq_engine_operator_token_rejects_unauthorized_requested_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:status",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={"requested_scopes": ["rq:enqueue"]},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Unauthorized requested scope(s): rq:enqueue."


def test_issue_rq_engine_operator_token_requires_explicit_requested_scope_when_read_default_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "svc-1",
            "token_class": "service",
            "jti": "jti-1",
            "scope": "rq:enqueue",
        },
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={},
        )

    assert response.status_code == 403
    assert response.get_json()["error"]["message"] == "No authorized scopes available for operator bootstrap."


def test_issue_rq_engine_operator_token_rate_limits_repeat_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setenv("RQ_ENGINE_OPERATOR_TOKEN_RATE_LIMIT_COUNT", "1")
    monkeypatch.setenv("RQ_ENGINE_OPERATOR_TOKEN_RATE_LIMIT_WINDOW_SECONDS", "60")

    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "42",
            "token_class": "user",
            "jti": "jti-1",
            "scope": "rq:read rq:status",
        },
    )
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "issue_token",
        lambda subject, **kwargs: {
            "token": "operator-token",
            "claims": {
                "token_class": "user",
                "aud": "rq-engine",
                "iat": 1700000000,
                "exp": 1700000900,
            },
        },
    )

    with app.test_client() as client:
        first = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={},
        )
        second = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    payload = second.get_json()
    assert "Rate limit exceeded:" in payload["error"]["message"]


def test_issue_rq_engine_operator_token_preserves_service_run_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app()
    _reset_operator_rate_limit_state()
    monkeypatch.setattr(
        weppcloud_site_module.auth_tokens,
        "decode_token",
        lambda token, audience=None: {
            "sub": "svc-1",
            "token_class": "service",
            "jti": "jti-1",
            "scope": "rq:status rq:read",
            "runs": ["run-1"],
            "service_groups": ["admin-run-token"],
        },
    )

    captured: dict[str, object] = {}

    def _fake_issue_token(subject: str, **kwargs):
        captured["subject"] = subject
        captured["kwargs"] = kwargs
        return {
            "token": "operator-token",
            "claims": {
                "token_class": "service",
                "aud": "rq-engine",
                "iat": 1700000000,
                "exp": 1700000900,
            },
        }

    monkeypatch.setattr(weppcloud_site_module.auth_tokens, "issue_token", _fake_issue_token)

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-operator-token",
            headers={"Authorization": "Bearer source-token"},
            json={"requested_scopes": ["rq:status"]},
        )

    assert response.status_code == 200
    assert captured["subject"] == "svc-1"
    kwargs = captured["kwargs"]
    assert kwargs["runs"] == ["run-1"]
    assert kwargs["scopes"] == ["rq:status"]


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
