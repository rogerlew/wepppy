import hashlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import debug_routes, session_routes
from wepppy.weppcloud.utils import auth_tokens


pytestmark = pytest.mark.microservice


def _issue_token(monkeypatch: pytest.MonkeyPatch, *, runs: list[str] | None = None) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "tester",
        scopes=["rq:status"],
        audience="rq-engine",
        runs=runs,
        extra_claims={"jti": "test-jti", "token_class": "user"},
    )
    return payload["token"]


def test_session_token_issues_with_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    token = _issue_token(monkeypatch, runs=["run-1"])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"
    assert payload["config"] == "cfg"
    assert payload["token"]
    assert "set-cookie" in response.headers
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Path=/weppcloud/runs/run-1/cfg/" in response.headers["set-cookie"]


def test_session_token_uses_grouped_cookie_key_and_safe_path_for_grouped_runid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    grouped_runid = "upset-reckoning;;omni;;undisturbed"
    grouped_runid_url = "upset-reckoning%3B%3Bomni%3B%3Bundisturbed"
    config = "disturbed9002"
    token = _issue_token(monkeypatch, runs=[grouped_runid])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{grouped_runid_url}/{config}/session-token",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    cookie_header = response.headers["set-cookie"]
    digest = hashlib.sha256(f"{grouped_runid}\n{config}".encode("utf-8")).hexdigest()[:16]
    expected_key = f"{session_routes.DEFAULT_BROWSE_JWT_COOKIE_NAME}_{digest}"
    assert cookie_header.startswith(f"{expected_key}=")
    assert "Path=/weppcloud/runs/" in cookie_header
    assert "%3B" not in cookie_header


def test_session_token_rejects_wrong_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    token = _issue_token(monkeypatch, runs=["run-2"])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_session_token_cookie_sets_secure_for_forwarded_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    token = _issue_token(monkeypatch, runs=["run-1"])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Authorization": f"Bearer {token}", "X-Forwarded-Proto": "https"},
        )

    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_session_token_cookie_secure_can_be_disabled_with_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_SESSION_COOKIE_SECURE", "false")

    token = _issue_token(monkeypatch, runs=["run-1"])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Authorization": f"Bearer {token}", "X-Forwarded-Proto": "https"},
        )

    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


def test_session_token_rejects_service_token_without_run_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    token = auth_tokens.issue_token(
        "service-client",
        scopes=["rq:status"],
        audience="rq-engine",
        extra_claims={"token_class": "service", "jti": "service-no-run-claim"},
    )["token"]

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_session_token_issues_with_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_routes, "_resolve_session_id_from_cookie", lambda request: "sid-1")
    monkeypatch.setattr(session_routes, "_session_exists", lambda session_id: None)
    monkeypatch.setattr(
        session_routes,
        "_session_payload",
        lambda session_id: {"_user_id": "42", "_roles_mask": ["User", "Root"]},
    )
    monkeypatch.setattr(session_routes, "_session_user_authorized_for_run", lambda runid, user_id, roles: True)
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: False)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            cookies={"session": "signed"},
            headers={"Origin": "http://testserver"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["session_id"] == "sid-1"
    assert payload["user_id"] == 42
    assert payload["roles"] == ["User", "Root"]
    claims = auth_tokens.decode_token(payload["token"], audience="rq-engine")
    assert claims["user_id"] == 42
    assert claims["roles"] == ["User", "Root"]


def test_session_token_allows_public_run_without_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_cookie(_: object) -> str:
        raise session_routes.AuthError("Missing session cookie", status_code=401)

    monkeypatch.setattr(session_routes, "_resolve_session_id_from_cookie", missing_cookie)
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Origin": "http://testserver"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"


def test_session_token_private_run_requires_authenticated_cookie_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_resolve_session_id_from_cookie", lambda request: "sid-1")
    monkeypatch.setattr(session_routes, "_session_exists", lambda session_id: None)
    monkeypatch.setattr(session_routes, "_session_payload", lambda session_id: {})
    monkeypatch.setattr(
        session_routes,
        "_session_user_authorized_for_run",
        lambda runid, user_id, roles: False,
    )
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: False)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            cookies={"session": "signed"},
            headers={"Origin": "http://testserver"},
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert payload["error"]["message"] == "Session not authorized for run"


def test_session_token_stale_remember_cookie_includes_relogin_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_resolve_session_id_from_cookie", lambda request: "sid-1")
    monkeypatch.setattr(session_routes, "_session_exists", lambda session_id: None)
    monkeypatch.setattr(session_routes, "_session_payload", lambda session_id: {})
    monkeypatch.setattr(
        session_routes,
        "_session_user_authorized_for_run",
        lambda runid, user_id, roles: False,
    )
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: False)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            cookies={"session": "signed", "remember_token": "remembered"},
            headers={"Origin": "http://testserver"},
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "Log out and sign in again, then retry." in payload["error"]["message"]


def test_session_token_cookie_path_blocks_missing_origin_and_referer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/session-token")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_token_cookie_path_allows_same_origin_fetch_metadata_without_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Sec-Fetch-Site": "same-origin"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"


def test_session_token_cookie_path_blocks_cross_site_fetch_metadata_without_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Sec-Fetch-Site": "cross-site"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_token_cookie_path_blocks_cross_origin_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_token_cookie_path_rejects_untrusted_forwarded_origin_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={
                "Origin": "https://external.example",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "external.example",
            },
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_session_token_cookie_path_can_opt_in_to_forwarded_origin_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv(session_routes.TRUST_FORWARDED_ORIGIN_HEADERS_ENV, "true")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={
                "Origin": "https://external.example",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "external.example",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"


def test_session_token_cookie_path_allows_configured_external_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_HOST", "external.example")
    monkeypatch.setenv("OAUTH_REDIRECT_SCHEME", "https")
    auth_tokens.get_jwt_config.cache_clear()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={"Origin": "https://external.example"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"


def test_session_token_bearer_path_ignores_cross_origin_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    token = _issue_token(monkeypatch, runs=["run-1"])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://evil.example",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "evil.example",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_class"] == "session"
    assert payload["runid"] == "run-1"


def test_hello_world_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyJob:
        id = "job-123"
        exc_info = None
        is_failed = False

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(debug_routes, "Queue", DummyQueue)
    monkeypatch.setattr(debug_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/hello-world")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
