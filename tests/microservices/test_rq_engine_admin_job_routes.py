import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import admin_job_routes

pytestmark = pytest.mark.microservice


def test_recently_completed_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_job_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["User"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/admin/recently-completed-jobs")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_jobs_detail_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_job_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["User"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/admin/jobs-detail")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_recently_completed_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_job_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(
        admin_job_routes,
        "list_recently_completed_jobs",
        lambda redis_conn, queue_names=None, lookback_seconds=None, scan_limit=None: [{"job_id": "job-1"}],
    )
    monkeypatch.setattr(admin_job_routes, "_hydrate_submitter_fields", lambda jobs: None)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/admin/recently-completed-jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"] == [{"job_id": "job-1"}]
    assert payload["lookback_seconds"] == admin_job_routes.DEFAULT_RECENT_LOOKBACK_SECONDS


def test_jobs_detail_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_job_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(
        admin_job_routes,
        "list_active_jobs",
        lambda redis_conn, queue_names=None: [{"job_id": "job-1", "state": "started"}],
    )
    monkeypatch.setattr(admin_job_routes, "_hydrate_submitter_fields", lambda jobs: None)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/admin/jobs-detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"] == [{"job_id": "job-1", "state": "started"}]

