import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import job_routes
from wepppy.weppcloud.utils import auth_tokens


pytestmark = pytest.mark.microservice


def test_health_returns_expected_payload() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "rq-engine"}


def test_jobstatus_returns_stubbed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_jobstatus(job_id: str) -> dict[str, str]:
        seen["job_id"] = job_id
        return {"status": "ok", "job_id": job_id}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", fake_jobstatus)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-123")

    assert response.json() == {"status": "ok", "job_id": "job-123"}
    assert seen["job_id"] == "job-123"


def test_jobstatus_not_found_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_jobstatus(job_id: str) -> dict[str, str]:
        return {"job_id": job_id, "status": "not_found"}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", fake_jobstatus)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Job not found" in payload["error"]["message"]
    assert "job-missing" in payload["error"]["details"]


def test_jobinfo_returns_stubbed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_jobinfo(job_id: str) -> dict[str, str]:
        seen["job_id"] = job_id
        return {"job_id": job_id, "status": "finished"}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_info", fake_jobinfo)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobinfo/job-abc")

    assert response.json() == {"job_id": "job-abc", "status": "finished"}
    assert seen["job_id"] == "job-abc"


def test_jobinfo_not_found_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_jobinfo(job_id: str) -> dict[str, str]:
        return {"job_id": job_id, "status": "not_found"}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_info", fake_jobinfo)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobinfo/job-missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Job not found" in payload["error"]["message"]
    assert "job-missing" in payload["error"]["details"]


def test_jobinfo_batch_preserves_order_and_filters_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = {}

    def fake_jobs_info(job_ids: list[str]) -> dict[str, dict[str, str]]:
        seen["job_ids"] = list(job_ids)
        return {"a": {"job_id": "a"}, "c": {"job_id": "c"}}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_jobs_info", fake_jobs_info)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/jobinfo", json={"job_ids": ["a", "b", "c"]})

    payload = response.json()
    assert seen["job_ids"] == ["a", "b", "c"]
    assert payload["jobs"] == {"a": {"job_id": "a"}, "c": {"job_id": "c"}}
    assert payload["job_ids"] == ["a", "c"]


def test_jobinfo_batch_uses_query_args_when_payload_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_jobs_info(job_ids: list[str]) -> dict[str, dict[str, str]]:
        return {job_id: {"job_id": job_id} for job_id in job_ids}

    monkeypatch.setattr(job_routes, "get_wepppy_rq_jobs_info", fake_jobs_info)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/jobinfo?job_id=job-99",
            data="{not-json}",
            headers={"content-type": "application/json"},
        )

    assert response.json() == {"jobs": {"job-99": {"job_id": "job-99"}}, "job_ids": ["job-99"]}


def test_jobinfo_error_returns_500_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(job_id: str) -> dict[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_info", explode)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobinfo/job-err")

    payload = response.json()
    assert response.status_code == 500
    assert isinstance(payload["error"]["message"], str)


def _issue_rq_token(
    monkeypatch: pytest.MonkeyPatch, *, scopes: list[str] | None = None
) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "tester",
        scopes=scopes or ["rq:status"],
        audience="rq-engine",
        extra_claims={"jti": "test-jti"},
    )
    return payload["token"]


def test_canceljob_requires_auth() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/canceljob/job-1")

    assert response.status_code == 401
    assert "error" in response.json()


def test_canceljob_rejects_missing_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = _issue_rq_token(monkeypatch, scopes=["runs:read"])

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-2",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_canceljob_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = _issue_rq_token(monkeypatch)

    def fake_cancel(job_id: str) -> dict[str, str]:
        return {"status": "ok", "job_id": job_id}

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )
    monkeypatch.setattr(job_routes, "cancel_jobs", fake_cancel)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-3",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "job_id": "job-3"}


def test_canceljob_rejects_revoked_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def revoked(_: str) -> None:
        raise rq_auth.AuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(rq_auth, "_check_revocation", revoked)
    token = _issue_rq_token(monkeypatch)

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-4",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_canceljob_rejects_session_without_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = auth_tokens.issue_token(
        "session-1",
        scopes=["rq:status"],
        audience="rq-engine",
        extra_claims={
            "token_class": "session",
            "session_id": "session-1",
            "runid": "run-1",
            "jti": "session-jti",
        },
    )["token"]

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )
    monkeypatch.setattr(
        rq_auth,
        "_check_session_marker",
        lambda session_id, runid: (_ for _ in ()).throw(
            rq_auth.AuthError("Session token expired", status_code=403, code="forbidden")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-5",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_canceljob_accepts_session_with_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = auth_tokens.issue_token(
        "session-2",
        scopes=["rq:status"],
        audience="rq-engine",
        extra_claims={
            "token_class": "session",
            "session_id": "session-2",
            "runid": "run-1",
            "jti": "session-jti-2",
        },
    )["token"]

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )
    monkeypatch.setattr(rq_auth, "_check_session_marker", lambda session_id, runid: None)
    monkeypatch.setattr(job_routes, "cancel_jobs", lambda job_id: {"status": "ok"})

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-6",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
