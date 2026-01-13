import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import run_sync_routes


pytestmark = pytest.mark.microservice


def _stub_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class DummyQueue:
        counter = 0

        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            DummyQueue.counter += 1
            return DummyJob(f"job-{DummyQueue.counter}")

        def get_job_ids(self):
            return []

    class DummyRedis:
        def close(self) -> None:
            return None

    monkeypatch.setattr(run_sync_routes, "Queue", DummyQueue)
    monkeypatch.setattr(run_sync_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def test_run_sync_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_sync_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["User"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/run-sync", json={"runid": "run-1"})

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_run_sync_enqueues_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_sync_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    _stub_queue(monkeypatch)
    monkeypatch.setattr(run_sync_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/run-sync",
            json={"runid": "run-1", "run_migrations": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_job_id"] == "job-1"
    assert payload["migration_job_id"] == "job-2"
    assert payload["job_ids"] == ["job-1", "job-2"]


def test_run_sync_status_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_sync_routes, "require_jwt", lambda request: {"roles": ["Admin"]})
    monkeypatch.setattr(run_sync_routes, "_collect_run_sync_jobs", lambda redis_conn: [{"id": "job-1"}])
    monkeypatch.setattr(run_sync_routes, "_load_migrations", lambda: [{"id": 1}])

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/run-sync/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"] == [{"id": "job-1"}]
    assert payload["migrations"] == [{"id": 1}]
