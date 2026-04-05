from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, Flask, redirect as flask_redirect
from requests.exceptions import RequestException
from werkzeug.exceptions import Forbidden, NotFound

from wepppy.weppcloud.routes._security import oauth as oauth_module

pytestmark = pytest.mark.routes


class DummyResponse:
    def __init__(
        self,
        *,
        ok: bool = True,
        status_code: int = 200,
        payload: object | None = None,
        json_error: bool = False,
    ) -> None:
        self.ok = ok
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("invalid json")
        return self._payload


class QueryStub:
    def __init__(self, result) -> None:
        self._result = result
        self.last_filter_by = None

    def filter_by(self, **kwargs):
        self.last_filter_by = kwargs
        return self

    def first(self):
        return self._result


def _set_current_user(
    monkeypatch: pytest.MonkeyPatch,
    *,
    is_authenticated: bool,
    user_id: int = 7,
    password: str | None = "password",
    oauth_count: int = 2,
):
    current_user = SimpleNamespace(
        id=user_id,
        is_authenticated=is_authenticated,
        password=password,
        oauth_accounts=SimpleNamespace(count=lambda: oauth_count),
    )
    monkeypatch.setattr(oauth_module, "current_user", current_user, raising=False)
    return current_user


def _set_callback_session(
    client,
    *,
    provider: str = "google",
    code_verifier: str = "pkce-code-verifier",
    next_url: str | None = None,
) -> None:
    with client.session_transaction() as session_state:
        session_state[oauth_module._SESSION_PKCE_KEY] = {provider: code_verifier}
        if next_url is not None:
            session_state[oauth_module._SESSION_NEXT_KEY] = {provider: next_url}


def _get_flashes(client) -> list[tuple[str, str]]:
    with client.session_transaction() as session_state:
        return list(session_state.get("_flashes", []))


def _configure_callback_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token: dict | None = None,
    token_exc: Exception | None = None,
    userinfo_response: DummyResponse | None = None,
    userinfo_exc: Exception | None = None,
) -> dict[str, object]:
    calls: dict[str, object] = {}

    class CallbackClient:
        def authorize_access_token(self, **kwargs):
            calls["code_verifier"] = kwargs.get("code_verifier")
            if token_exc is not None:
                raise token_exc
            return token if token is not None else {"access_token": "token", "token_type": "Bearer"}

        def get(self, endpoint, headers=None):
            calls["userinfo_endpoint"] = endpoint
            calls["userinfo_headers"] = headers
            if userinfo_exc is not None:
                raise userinfo_exc
            if userinfo_response is not None:
                return userinfo_response
            return DummyResponse(
                payload={
                    "sub": "provider-user-123",
                    "email": "person@example.com",
                    "email_verified": True,
                }
            )

    client = CallbackClient()
    monkeypatch.setattr(oauth_module, "ensure_oauth_client", lambda *_args, **_kwargs: client)
    return calls


@pytest.fixture()
def oauth_app(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        OAUTH_PROVIDERS={
            "google": {
                "enabled": True,
                "name": "google",
                "userinfo_url": "userinfo",
            }
        },
        SECURITY_LOGIN_ERROR_VIEW="security_ui.login",
        SECURITY_POST_LOGIN_VIEW="security_ui.welcome",
    )

    security_ui_bp = Blueprint("security_ui", __name__)

    @security_ui_bp.get("/login")
    def login():
        return "login"

    @security_ui_bp.get("/welcome")
    def welcome():
        return "welcome"

    user_bp = Blueprint("user", __name__)

    @user_bp.get("/profile")
    def profile():
        return "profile"

    app.register_blueprint(security_ui_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(oauth_module.security_oauth_bp)

    _set_current_user(monkeypatch, is_authenticated=False)
    return app


def test_sanitize_next_url_rejects_external_without_allowlist(oauth_app: Flask) -> None:
    with oauth_app.app_context():
        assert oauth_module._sanitize_next_url("https://evil.example/path") is None


def test_sanitize_next_url_rejects_scheme_relative_urls(oauth_app: Flask) -> None:
    with oauth_app.app_context():
        assert oauth_module._sanitize_next_url("//evil.example/path") is None


def test_sanitize_next_url_accepts_allowlisted_host_with_port(oauth_app: Flask) -> None:
    oauth_app.config["OAUTH_REDIRECT_HOST"] = "auth.example.test"
    with oauth_app.app_context():
        sanitized = oauth_module._sanitize_next_url(
            "https://auth.example.test:443/runs/demo/cfg?tab=1#section",
        )
    assert sanitized == "/runs/demo/cfg?tab=1#section"


def test_sanitize_next_url_rejects_non_allowlisted_host(oauth_app: Flask) -> None:
    oauth_app.config["OAUTH_REDIRECT_HOST"] = "auth.example.test"
    with oauth_app.app_context():
        assert oauth_module._sanitize_next_url("https://other.example.test/runs/demo/cfg") is None


def test_oauth_login_returns_404_for_disabled_provider(oauth_app: Flask) -> None:
    oauth_app.config["OAUTH_PROVIDERS"]["google"]["enabled"] = False
    with oauth_app.test_client() as client:
        with pytest.raises(NotFound):
            client.get("/oauth/google/login")


def test_oauth_login_redirects_authenticated_user(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_current_user(monkeypatch, is_authenticated=True)
    with oauth_app.test_client() as client:
        response = client.get("/oauth/google/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/welcome")


def test_oauth_login_returns_404_when_oauth_client_is_missing(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oauth_module, "ensure_oauth_client", lambda *_args, **_kwargs: None)
    with oauth_app.test_client() as client:
        with pytest.raises(NotFound):
            client.get("/oauth/google/login")


def test_oauth_login_stores_pkce_and_next_before_redirect(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, object] = {}

    class LoginClient:
        def authorize_redirect(self, redirect_uri, **kwargs):
            calls["redirect_uri"] = redirect_uri
            calls["kwargs"] = kwargs
            return flask_redirect("/provider-auth")

    monkeypatch.setattr(oauth_module, "ensure_oauth_client", lambda *_args, **_kwargs: LoginClient())
    monkeypatch.setattr(oauth_module, "build_pkce_pair", lambda: ("verifier-123", "challenge-456"))

    with oauth_app.test_client() as client:
        response = client.get("/oauth/google/login?next=/runs/demo/cfg", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/provider-auth")
        assert str(calls["redirect_uri"]).endswith("/oauth/google/callback")
        assert calls["kwargs"] == {
            "code_challenge": "challenge-456",
            "code_challenge_method": "S256",
        }

        with client.session_transaction() as session_state:
            assert session_state[oauth_module._SESSION_PKCE_KEY]["google"] == "verifier-123"
            assert session_state[oauth_module._SESSION_NEXT_KEY]["google"] == "/runs/demo/cfg"


def test_oauth_login_handles_authorize_redirect_failure(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    class LoginClient:
        def authorize_redirect(self, _redirect_uri, **_kwargs):
            raise RequestException("oauth provider unavailable")

    monkeypatch.setattr(oauth_module, "ensure_oauth_client", lambda *_args, **_kwargs: LoginClient())
    monkeypatch.setattr(oauth_module, "build_pkce_pair", lambda: ("verifier-123", "challenge-456"))

    with oauth_app.test_client() as client:
        response = client.get("/oauth/google/login", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Unable to start OAuth login. Please try again later.") in _get_flashes(client)


def test_oauth_callback_returns_404_for_disabled_provider(oauth_app: Flask) -> None:
    oauth_app.config["OAUTH_PROVIDERS"]["google"]["enabled"] = False
    with oauth_app.test_client() as client:
        with pytest.raises(NotFound):
            client.get("/oauth/google/callback")


def test_oauth_callback_handles_non_access_denied_provider_error(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unexpected_client_lookup(*_args, **_kwargs):
        raise AssertionError("OAuth client lookup should not run when provider already returned an error.")

    monkeypatch.setattr(oauth_module, "ensure_oauth_client", _unexpected_client_lookup)

    with oauth_app.test_client() as client:
        _set_callback_session(client, next_url="/runs/demo/cfg")

        response = client.get(
            "/oauth/google/callback?error=temporarily_unavailable&error_description=maintenance",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Login failed at the identity provider.") in _get_flashes(client)

        with client.session_transaction() as session_state:
            assert oauth_module._SESSION_PKCE_KEY not in session_state
            assert oauth_module._SESSION_NEXT_KEY not in session_state


def test_oauth_callback_requires_pkce_session(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oauth_module, "ensure_oauth_client", lambda *_args, **_kwargs: object())

    with oauth_app.test_client() as client:
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("warning", "OAuth session expired. Please try again.") in _get_flashes(client)


def test_oauth_callback_handles_access_denied_token_exchange_error(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        token_exc=OAuthError(error="access_denied", description="Denied by user"),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("warning", "Sign-in was canceled.") in _get_flashes(client)


def test_oauth_callback_handles_token_exchange_failure(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(monkeypatch, token_exc=RequestException("token exchange failed"))

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Login failed while contacting the identity provider.") in _get_flashes(client)


def test_oauth_callback_handles_userinfo_request_exception(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(monkeypatch, userinfo_exc=RequestException("userinfo failed"))

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Login failed while retrieving profile information.") in _get_flashes(client)


def test_oauth_callback_handles_userinfo_non_ok_response(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        userinfo_response=DummyResponse(ok=False, status_code=502, payload={"error": "bad gateway"}),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Unable to retrieve your profile from the identity provider.") in _get_flashes(client)


def test_oauth_callback_handles_userinfo_non_json_response(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        userinfo_response=DummyResponse(ok=True, status_code=200, json_error=True),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "Unexpected response from the identity provider.") in _get_flashes(client)


def test_oauth_callback_requires_provider_uid(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        userinfo_response=DummyResponse(
            payload={"email": "person@example.com", "email_verified": True},
        ),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "The identity provider did not return a stable identifier.") in _get_flashes(client)


def test_oauth_callback_requires_verified_email(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        userinfo_response=DummyResponse(payload={"sub": "uid-1"}),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert (
            "error",
            "We could not determine your verified email address from the identity provider.",
        ) in _get_flashes(client)


def test_oauth_callback_blocks_unverified_email(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(
        monkeypatch,
        userinfo_response=DummyResponse(
            payload={
                "sub": "uid-1",
                "email": "person@example.com",
                "email_verified": False,
            }
        ),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert (
            "error",
            "Please verify your email address with the identity provider before continuing.",
        ) in _get_flashes(client)


def test_oauth_callback_handles_identity_link_conflict(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(monkeypatch)

    def _raise_conflict(*_args, **_kwargs):
        raise ValueError("identity already linked")

    monkeypatch.setattr(oauth_module, "_link_identity", _raise_conflict)

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
        assert ("error", "This identity is already linked to a different WEPPcloud account.") in _get_flashes(
            client
        )


def test_oauth_callback_success_redirects_to_session_next_and_logs_user_in(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _configure_callback_client(monkeypatch)
    linked_user = SimpleNamespace(id=91)
    login_calls = []

    monkeypatch.setattr(oauth_module, "_link_identity", lambda *_args, **_kwargs: linked_user)
    monkeypatch.setattr(
        oauth_module,
        "login_user",
        lambda user, remember=True: login_calls.append((user, remember)),
    )

    with oauth_app.test_client() as client:
        _set_callback_session(client, code_verifier="pkce-xyz", next_url="/runs/demo/cfg")
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"] == "/runs/demo/cfg"
        assert calls["code_verifier"] == "pkce-xyz"
        assert login_calls == [(linked_user, True)]

        with client.session_transaction() as session_state:
            assert oauth_module._SESSION_NEXT_KEY not in session_state


def test_oauth_callback_success_uses_query_next_fallback(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(monkeypatch)
    monkeypatch.setattr(oauth_module, "_link_identity", lambda *_args, **_kwargs: SimpleNamespace(id=92))
    monkeypatch.setattr(oauth_module, "login_user", lambda *_args, **_kwargs: None)

    with oauth_app.test_client() as client:
        _set_callback_session(client)
        response = client.get("/oauth/google/callback?next=/runs/query-next/cfg", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"] == "/runs/query-next/cfg"


def test_oauth_callback_success_redirects_to_post_login_view(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_callback_client(monkeypatch)
    monkeypatch.setattr(oauth_module, "_link_identity", lambda *_args, **_kwargs: SimpleNamespace(id=93))
    monkeypatch.setattr(oauth_module, "login_user", lambda *_args, **_kwargs: None)

    with oauth_app.test_client() as client:
        _set_callback_session(client, next_url=None)
        response = client.get("/oauth/google/callback", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/welcome")


def test_oauth_disconnect_requires_authenticated_user(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_current_user(monkeypatch, is_authenticated=False)

    with oauth_app.test_client() as client:
        with pytest.raises(Forbidden):
            client.post("/oauth/google/disconnect")


def test_oauth_disconnect_returns_404_when_account_missing(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _set_current_user(monkeypatch, is_authenticated=True, user_id=33)
    query_stub = QueryStub(result=None)
    oauth_account_model = SimpleNamespace(query=query_stub)
    monkeypatch.setattr(oauth_module, "_get_oauth_account_model", lambda: oauth_account_model)
    monkeypatch.setattr(oauth_module, "_get_user_datastore", lambda: SimpleNamespace(unlink_oauth_account=lambda *_args: None))

    with oauth_app.test_client() as client:
        with pytest.raises(NotFound):
            client.post("/oauth/google/disconnect")
    assert query_stub.last_filter_by == {"provider": "google", "user_id": user.id}


def test_oauth_disconnect_blocks_removing_only_sign_in_method(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_current_user(monkeypatch, is_authenticated=True, password=None, oauth_count=1)
    query_stub = QueryStub(result=SimpleNamespace(id=1001))
    oauth_account_model = SimpleNamespace(query=query_stub)
    unlink_calls = []

    monkeypatch.setattr(oauth_module, "_get_oauth_account_model", lambda: oauth_account_model)
    monkeypatch.setattr(
        oauth_module,
        "_get_user_datastore",
        lambda: SimpleNamespace(unlink_oauth_account=lambda *_args: unlink_calls.append(_args)),
    )

    with oauth_app.test_client() as client:
        response = client.post("/oauth/google/disconnect", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
        assert unlink_calls == []
        assert ("warning", "Cannot remove the only linked sign-in method.") in _get_flashes(client)


def test_oauth_disconnect_unlinks_account_and_redirects_to_profile(
    oauth_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    current_user = _set_current_user(monkeypatch, is_authenticated=True, password="has-password", oauth_count=1)
    query_stub = QueryStub(result=SimpleNamespace(id=1002))
    oauth_account_model = SimpleNamespace(query=query_stub)
    unlink_calls = []

    monkeypatch.setattr(oauth_module, "_get_oauth_account_model", lambda: oauth_account_model)
    monkeypatch.setattr(
        oauth_module,
        "_get_user_datastore",
        lambda: SimpleNamespace(unlink_oauth_account=lambda *args: unlink_calls.append(args)),
    )

    with oauth_app.test_client() as client:
        response = client.post("/oauth/google/disconnect", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
        assert unlink_calls == [(current_user, "google")]
        assert ("success", "Google account disconnected.") in _get_flashes(client)
