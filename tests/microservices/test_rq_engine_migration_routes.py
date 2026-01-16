import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import migration_routes


pytestmark = pytest.mark.microservice


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
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

        def close(self) -> None:
            return None

    monkeypatch.setattr(migration_routes, "Queue", DummyQueue)
    monkeypatch.setattr(migration_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def get_rq_job_ids(self) -> dict[str, str]:
            return {}

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(migration_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_ron(monkeypatch: pytest.MonkeyPatch, *, readonly: bool = False) -> None:
    class DummyRon:
        def __init__(self, readonly_state: bool) -> None:
            self.readonly = readonly_state

    ron = DummyRon(readonly)
    monkeypatch.setattr(migration_routes.Ron, "getInstance", lambda wd: ron)


def test_migrate_run_requires_run_claim_for_service_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        migration_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "service"},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/migrate-run",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert "Token not authorized" in payload["error"]["details"]


def test_migrate_run_allows_admin_without_run_claim(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        migration_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "service", "roles": ["Admin"]},
    )
    monkeypatch.setattr(migration_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(migration_routes, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(migration_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    _stub_ron(monkeypatch, readonly=True)
    _stub_prep(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-55")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/migrate-run",
            headers={"Authorization": "Bearer token"},
            json={"create_archive": True},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-55"
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-55"
    assert payload["result"]["was_readonly"] is True


def test_migrate_run_allows_session_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    called = {"value": False}

    def _require_session_marker(claims: dict, runid: str) -> None:
        called["value"] = True
        assert claims.get("runid") == runid

    monkeypatch.setattr(
        migration_routes,
        "require_jwt",
        lambda request, required_scopes=None: {
            "token_class": "session",
            "runid": "run-1",
            "session_id": "session-1",
        },
    )
    monkeypatch.setattr(migration_routes, "require_session_marker", _require_session_marker)
    monkeypatch.setattr(migration_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(migration_routes, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(migration_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    _stub_ron(monkeypatch, readonly=False)
    _stub_prep(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-99")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/migrate-run",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-99"
    assert called["value"] is True


def test_migrate_run_returns_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "missing"

    monkeypatch.setattr(
        migration_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "service", "roles": ["Admin"]},
    )
    monkeypatch.setattr(migration_routes, "get_wd", lambda runid: str(run_dir))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/migrate-run",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Run run-1 not found" in payload["error"]["details"]
