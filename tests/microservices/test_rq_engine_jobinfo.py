import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import job_routes
from wepppy.weppcloud.utils import auth_tokens


pytestmark = pytest.mark.microservice


@pytest.fixture(autouse=True)
def _reset_polling_state(monkeypatch: pytest.MonkeyPatch):
    job_routes._POLL_RATE_LIMIT_BUCKETS.clear()
    monkeypatch.delenv(job_routes.POLL_AUTH_MODE_ENV, raising=False)
    monkeypatch.delenv(job_routes.POLL_RATE_LIMIT_COUNT_ENV, raising=False)
    monkeypatch.delenv(job_routes.POLL_RATE_LIMIT_WINDOW_ENV, raising=False)


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


def test_jobstatus_unexpected_exception_returns_500_with_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(job_id: str) -> dict[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", explode)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-boom")

    assert response.status_code == 500
    payload = response.json()
    assert isinstance(payload["error"]["message"], str)
    assert "RuntimeError: boom" in payload["error"]["details"]


def test_polling_mode_required_rejects_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_routes.POLL_AUTH_MODE_ENV, "required")
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", lambda job_id: {"status": "ok", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-required")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_polling_mode_token_optional_accepts_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_routes.POLL_AUTH_MODE_ENV, "token_optional")
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", lambda job_id: {"status": "ok", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/jobstatus/job-optional")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-optional"


def test_polling_mode_token_optional_validates_token_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_routes.POLL_AUTH_MODE_ENV, "token_optional")
    seen = {"called": False}

    def _require_jwt(request, required_scopes=None):
        seen["called"] = True
        assert required_scopes == ["rq:status"]
        return {"sub": "u1", "scope": "rq:status"}

    monkeypatch.setattr(job_routes, "require_jwt", _require_jwt)
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", lambda job_id: {"status": "ok", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        response = client.get(
            "/api/jobstatus/job-optional-auth",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    assert seen["called"] is True


def test_polling_mode_required_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_routes.POLL_AUTH_MODE_ENV, "required")
    monkeypatch.setattr(job_routes, "require_jwt", lambda request, required_scopes=None: {"sub": "u2", "scope": "rq:status"})
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_info", lambda job_id: {"status": "finished", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        response = client.get(
            "/api/jobinfo/job-required-ok",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-required-ok"


def test_jobstatus_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(job_routes.POLL_RATE_LIMIT_COUNT_ENV, "1")
    monkeypatch.setenv(job_routes.POLL_RATE_LIMIT_WINDOW_ENV, "60")
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", lambda job_id: {"status": "ok", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        first = client.get("/api/jobstatus/job-rate", headers={"X-Forwarded-For": "1.2.3.4"})
        second = client.get("/api/jobstatus/job-rate", headers={"X-Forwarded-For": "1.2.3.4"})

    assert first.status_code == 200
    assert second.status_code == 429
    payload = second.json()
    assert payload["error"]["code"] == "rate_limited"
    assert "Rate limit exceeded" in payload["error"]["details"]


def test_jobstatus_audit_logging_includes_job_id_and_ip(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(job_routes, "get_wepppy_rq_job_status", lambda job_id: {"status": "ok", "job_id": job_id})

    with caplog.at_level("INFO"):
        with TestClient(rq_engine.app) as client:
            response = client.get("/api/jobstatus/job-audit", headers={"X-Forwarded-For": "5.6.7.8"})

    assert response.status_code == 200
    audit_lines = [record.message for record in caplog.records if "rq_engine_poll_audit" in record.message]
    assert audit_lines
    assert any("job_id=job-audit" in line for line in audit_lines)
    assert any("ip=5.6.7.8" in line for line in audit_lines)


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


def test_canceljob_accepts_culvert_submit_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = _issue_rq_token(monkeypatch, scopes=["culvert:batch:submit"])

    monkeypatch.setattr(
        job_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {"job_id": job_id, "status": "finished", "runid": "run-1"},
    )
    monkeypatch.setattr(job_routes, "cancel_jobs", lambda job_id: {"status": "ok", "job_id": job_id})

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/canceljob/job-culvert",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "job_id": "job-culvert"}


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


def test_canceljob_auth_unexpected_exception_returns_401_with_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(_request) -> dict[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(job_routes, "_authorize_cancel_request", explode)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/canceljob/job-auth-boom")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["message"] == "Failed to authorize request"
    assert "Traceback" in payload["error"]["details"]
    assert "RuntimeError: boom" in payload["error"]["details"]
