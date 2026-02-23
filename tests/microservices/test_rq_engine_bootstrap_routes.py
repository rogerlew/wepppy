from __future__ import annotations

import time

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import bootstrap_routes
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.weppcloud.bootstrap.api_shared import BootstrapOperationError, BootstrapOperationResult
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch, *, claims: dict | None = None) -> None:
    resolved_claims = claims or {
        "sub": "7",
        "email": "user@example.com",
        "scope": " ".join(
            [
                bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE,
                bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE,
                bootstrap_routes.BOOTSTRAP_READ_SCOPE,
                bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE,
            ]
        ),
    }
    monkeypatch.setattr(
        bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: resolved_claims,
    )
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-1") -> None:
    class DummyJob:
        id = job_id

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

    monkeypatch.setattr(bootstrap_routes, "Queue", DummyQueue)
    monkeypatch.setattr(bootstrap_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch, tasks: list[TaskEnum]) -> None:
    class DummyPrep:
        def remove_timestamp(self, task: TaskEnum) -> None:
            tasks.append(task)

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(bootstrap_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _issue_rq_token(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scopes: list[str] | None = None,
    audience: str = "rq-engine",
    issued_at: int | None = None,
    expires_in: int = 3600,
    jti: str = "bootstrap-test-jti",
) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "7",
        scopes=scopes or [bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE],
        audience=audience,
        issued_at=issued_at,
        expires_in=expires_in,
        extra_claims={
            "jti": jti,
            "token_class": "user",
            "email": "user@example.com",
        },
    )
    return payload["token"]


def test_bootstrap_enable_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(
        bootstrap_routes,
        "enable_bootstrap_operation",
        lambda runid, actor: BootstrapOperationResult(
            payload={
                "enabled": False,
                "queued": True,
                "job_id": "enable-1",
                "message": "Bootstrap enable job enqueued.",
                "status_url": "/rq-engine/api/jobstatus/enable-1",
            },
            status_code=202,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 202
    assert response.json() == {
        "enabled": False,
        "queued": True,
        "job_id": "enable-1",
        "message": "Bootstrap enable job enqueued.",
        "status_url": "/rq-engine/api/jobstatus/enable-1",
    }


def test_bootstrap_enable_scope_only_token_works(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=[bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(
        bootstrap_routes,
        "enable_bootstrap_operation",
        lambda runid, actor: BootstrapOperationResult(payload={"queued": True, "job_id": "enable-2"}, status_code=202),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 202
    assert response.json() == {"queued": True, "job_id": "enable-2"}


def test_bootstrap_enable_rejects_rq_enqueue_without_bootstrap_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=["rq:enqueue"])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE in payload["error"]["message"]


def test_bootstrap_enable_rejects_missing_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=["runs:read"])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE in payload["error"]["message"]


def test_bootstrap_enable_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())
    token = _issue_rq_token(
        monkeypatch,
        issued_at=now - 120,
        expires_in=60,
    )
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "expired" in payload["error"]["message"].lower()


def test_bootstrap_enable_rejects_audience_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, audience="other-service")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "audience" in payload["error"]["message"].lower()


def test_bootstrap_enable_rejects_revoked_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, jti="revoked-jti")
    headers = {"Authorization": f"Bearer {token}"}

    def _raise_revoked(_jti: str) -> None:
        raise rq_auth.AuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(
        rq_auth,
        "_check_revocation",
        _raise_revoked,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Token has been revoked"


def test_bootstrap_enable_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    def _raise_busy(runid: str, actor: str):
        raise BootstrapOperationError("bootstrap lock busy", status_code=409, code="conflict")

    monkeypatch.setattr(bootstrap_routes, "enable_bootstrap_operation", _raise_busy)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_mint_token_requires_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"token_class": "session", "sub": "session-1", "scope": bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE})

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "User identity claims are required to mint bootstrap tokens"


def test_bootstrap_mint_token_returns_clone_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(
        monkeypatch,
        claims={"sub": "42", "email": "owner@example.com", "scope": bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE},
    )
    monkeypatch.setattr(
        bootstrap_routes,
        "mint_bootstrap_token_operation",
        lambda runid, user_email, user_id: BootstrapOperationResult(
            payload={"clone_url": f"https://{user_id}:token@example.test/git/ru/run-1/.git"},
            status_code=200,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 200
    assert response.json() == {"clone_url": "https://42:token@example.test/git/ru/run-1/.git"}


def test_bootstrap_checkout_requires_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE})
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "sha required"


def test_bootstrap_checkout_invalid_json_payload_falls_back_to_missing_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(
        monkeypatch,
        claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE},
    )
    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/bootstrap/checkout",
            data="{not-json}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "sha required"


def test_bootstrap_checkout_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE})

    monkeypatch.setattr(
        bootstrap_routes,
        "bootstrap_checkout_operation",
        lambda runid, sha, actor: (_ for _ in ()).throw(
            BootstrapOperationError("bootstrap lock busy", status_code=409, code="conflict")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={"sha": "abc1234"})

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_commits_allows_read_when_admin_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_READ_SCOPE})
    monkeypatch.setattr(
        bootstrap_routes,
        "bootstrap_commits_operation",
        lambda runid: BootstrapOperationResult(payload={"commits": [{"sha": "abc1234"}]}, status_code=200),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/bootstrap/commits")

    assert response.status_code == 200
    assert response.json() == {"commits": [{"sha": "abc1234"}]}


def test_bootstrap_run_wepp_npprep_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert set(tasks) == {
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_path_cost_effective,
    }


def test_bootstrap_run_swat_noprep_rejects_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-swat-noprep")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Bootstrap is not enabled for this run"
