import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import batch_routes


pytestmark = pytest.mark.microservice


def test_run_batch_requires_admin_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["User"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/run-batch")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_run_batch_missing_batch_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(
        batch_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/missing/run-batch")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["message"] == "missing"


def test_run_batch_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyJob:
        id = "job-123"

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

    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(
        batch_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: object(),
    )
    monkeypatch.setattr(batch_routes, "Queue", DummyQueue)
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/run-batch")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
