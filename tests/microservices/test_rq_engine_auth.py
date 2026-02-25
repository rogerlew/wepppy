from __future__ import annotations

import re

import pytest

from wepppy.microservices.rq_engine import auth


pytestmark = pytest.mark.microservice
_CORRELATION_HEADER = "X-Correlation-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def test_authorize_run_access_rejects_service_without_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "service"}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "run scope" in exc_info.value.message.lower()


def test_rq_engine_health_emits_correlation_id_header() -> None:
    testclient = pytest.importorskip("fastapi.testclient")
    from wepppy.microservices import rq_engine

    with testclient.TestClient(rq_engine.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    correlation_id = response.headers.get(_CORRELATION_HEADER)
    assert correlation_id is not None
    assert _CORRELATION_ID_PATTERN.match(correlation_id)


def test_rq_engine_health_echoes_valid_correlation_id_header() -> None:
    testclient = pytest.importorskip("fastapi.testclient")
    from wepppy.microservices import rq_engine

    inbound_correlation_id = "cid-rq-engine-auth-01"
    with testclient.TestClient(rq_engine.app) as client:
        response = client.get("/health", headers={_CORRELATION_HEADER: inbound_correlation_id})

    assert response.status_code == 200
    assert response.headers.get(_CORRELATION_HEADER) == inbound_correlation_id


def test_authorize_run_access_rejects_mcp_without_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "mcp"}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "run scope" in exc_info.value.message.lower()


def test_authorize_run_access_allows_service_with_matching_run_scope() -> None:
    auth.authorize_run_access({"token_class": "service", "runs": ["run-1", "run-2"]}, "run-1")


def test_authorize_run_access_rejects_service_with_wrong_run_scope() -> None:
    with pytest.raises(auth.AuthError) as exc_info:
        auth.authorize_run_access({"token_class": "service", "runs": ["run-2"]}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "not authorized" in exc_info.value.message.lower()


def test_require_session_marker_returns_unauthorized_when_marker_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingMarkerRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def exists(self, key: str) -> bool:
            return False

    monkeypatch.setattr(auth.redis, "Redis", lambda **kwargs: MissingMarkerRedis())

    with pytest.raises(auth.AuthError) as exc_info:
        auth.require_session_marker(
            {
                "token_class": "session",
                "session_id": "sid-1",
                "runid": "run-1",
            },
            "run-1",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "unauthorized"
    assert "session token invalid or expired" in exc_info.value.message.lower()


def test_require_roles_accepts_mixed_role_shapes() -> None:
    claims = {"roles": ["Admin", {"name": "PowerUser"}, "Dev"]}

    auth.require_roles(claims, ["admin"])
    auth.require_roles(claims, ["PowerUser"])


def test_require_roles_rejects_when_required_role_missing() -> None:
    claims = {"roles": ["User", {"name": "Dev"}]}

    with pytest.raises(auth.AuthError) as exc_info:
        auth.require_roles(claims, ["Admin"])

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "required role" in exc_info.value.message.lower()


def test_authorize_user_claims_allows_admin_without_owner_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "get_wd", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unused")))
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: (_ for _ in ()).throw(AssertionError("unused")))

    auth._authorize_user_claims({"roles": ["Admin"], "sub": "42"}, "run-1")


def test_authorize_user_claims_allows_root_without_owner_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "get_wd", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unused")))
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: (_ for _ in ()).throw(AssertionError("unused")))

    auth._authorize_user_claims({"roles": ["root"], "sub": "42"}, "run-1")


def test_authorize_user_claims_allows_public_run_for_non_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    class Owner:
        id = 99
        email = "owner@example.com"

    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/run-1")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [Owner()])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: True))

    auth._authorize_user_claims({"roles": [], "sub": "12", "email": "other@example.com"}, "run-1")


def test_authorize_user_claims_allows_owner_match_by_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    class Owner:
        id = 42
        email = "owner@example.com"

    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/run-1")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [Owner()])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    auth._authorize_user_claims({"roles": [], "sub": "42"}, "run-1")


def test_authorize_user_claims_allows_owner_match_by_email(monkeypatch: pytest.MonkeyPatch) -> None:
    class Owner:
        id = 77
        email = "owner@example.com"

    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/run-1")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [Owner()])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    auth._authorize_user_claims({"roles": [], "sub": "55", "email": "owner@example.com"}, "run-1")


def test_authorize_user_claims_rejects_non_owner_private_run(monkeypatch: pytest.MonkeyPatch) -> None:
    class Owner:
        id = 77
        email = "owner@example.com"

    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/run-1")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [Owner()])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    with pytest.raises(auth.AuthError) as exc_info:
        auth._authorize_user_claims({"roles": [], "sub": "55", "email": "other@example.com"}, "run-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"


def test_authorize_user_claims_grouped_omni_runid_uses_parent_run_acl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Owner:
        id = 77
        email = "owner@example.com"

    wd_calls: list[str] = []
    owner_calls: list[str] = []

    def fake_get_wd(runid: str, **_kwargs: object) -> str:
        wd_calls.append(runid)
        return f"/tmp/{runid}"

    def fake_get_run_owners(runid: str):
        owner_calls.append(runid)
        return [Owner()]

    monkeypatch.setattr(auth, "get_wd", fake_get_wd)
    monkeypatch.setattr(auth, "get_run_owners_lazy", fake_get_run_owners)
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    with pytest.raises(auth.AuthError) as exc_info:
        auth._authorize_user_claims(
            {"roles": [], "sub": "55", "email": "other@example.com"},
            "decimal-pleasing;;omni;;treated",
        )

    assert exc_info.value.status_code == 403
    assert wd_calls == ["decimal-pleasing"]
    assert owner_calls == ["decimal-pleasing"]


def test_authorize_user_claims_grouped_batch_omni_runid_uses_parent_run_acl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Owner:
        id = 77
        email = "owner@example.com"

    wd_calls: list[str] = []
    owner_calls: list[str] = []

    def fake_get_wd(runid: str, **_kwargs: object) -> str:
        wd_calls.append(runid)
        return f"/tmp/{runid}"

    def fake_get_run_owners(runid: str):
        owner_calls.append(runid)
        return [Owner()]

    monkeypatch.setattr(auth, "get_wd", fake_get_wd)
    monkeypatch.setattr(auth, "get_run_owners_lazy", fake_get_run_owners)
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    with pytest.raises(auth.AuthError) as exc_info:
        auth._authorize_user_claims(
            {"roles": [], "sub": "55", "email": "other@example.com"},
            "batch;;spring-2025;;run-001;;omni;;treated",
        )

    assert exc_info.value.status_code == 403
    assert wd_calls == ["batch;;spring-2025;;run-001"]
    assert owner_calls == ["batch;;spring-2025;;run-001"]


def test_authorize_user_claims_rejects_private_batch_run_without_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/private-batch")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: False))

    with pytest.raises(auth.AuthError) as exc_info:
        auth._authorize_user_claims(
            {"roles": [], "sub": "55", "email": "other@example.com"},
            "batch;;spring-2025;;run-001",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"


def test_authorize_user_claims_allows_public_batch_run_without_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "get_wd", lambda _runid, **_kwargs: "/tmp/public-batch")
    monkeypatch.setattr(auth, "get_run_owners_lazy", lambda _runid: [])
    monkeypatch.setattr(auth.Ron, "ispublic", staticmethod(lambda _wd: True))

    auth._authorize_user_claims(
        {"roles": [], "sub": "55", "email": "other@example.com"},
        "batch;;spring-2025;;run-001",
    )


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"token_class": "user", "sub": "42"}, {"token_class": "user", "user_id": 42}),
        (
            {"token_class": "session", "session_id": "sid-1"},
            {"token_class": "session", "session_id": "sid-1"},
        ),
        (
            {"token_class": "service", "sub": "svc-1", "service_groups": ["alpha", "beta"]},
            {"token_class": "service", "sub": "svc-1", "service_groups": ["alpha", "beta"]},
        ),
        ({"token_class": "mcp", "sub": "mcp-1"}, {"token_class": "mcp", "sub": "mcp-1"}),
    ],
)
def test_sanitize_auth_actor_normalizes_supported_classes(claims, expected) -> None:
    assert auth._sanitize_auth_actor(claims) == expected


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"token_class": "user", "sub": "not-an-int"},
        {"token_class": "session"},
        {"token_class": "service"},
        {"token_class": "mcp"},
        {"token_class": "unknown", "sub": "x"},
    ],
)
def test_sanitize_auth_actor_rejects_malformed_claims(claims) -> None:
    assert auth._sanitize_auth_actor(claims) is None
