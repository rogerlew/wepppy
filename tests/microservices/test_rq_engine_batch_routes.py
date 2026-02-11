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


def test_delete_batch_requires_admin_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["User"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/delete-batch")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_delete_batch_invalid_name_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/ab/delete-batch")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "invalid_batch_name"


def test_delete_batch_busy_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )
    monkeypatch.setattr(
        batch_routes,
        "_active_batch_job_summaries",
        lambda batch_name, redis_conn=None: ["job-1:started:run_batch_rq"],
    )

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/delete-batch")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "batch_busy"
    assert "Active jobs" in payload["error"]["details"]


def test_delete_batch_missing_batch_still_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
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
        batch_routes,
        "_active_batch_job_summaries",
        lambda batch_name, redis_conn=None: [],
    )
    monkeypatch.setattr(
        batch_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )
    monkeypatch.setattr(batch_routes, "Queue", DummyQueue)
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/missing/delete-batch")

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-123"


def test_delete_batch_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyBatchRunner:
        def set_rq_job_id(self, key: str, job_id: str) -> None:
            assert key == "delete_batch_rq"
            assert job_id == "job-123"

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
        batch_routes,
        "_active_batch_job_summaries",
        lambda batch_name, redis_conn=None: [],
    )
    monkeypatch.setattr(
        batch_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: DummyBatchRunner(),
    )
    monkeypatch.setattr(batch_routes, "Queue", DummyQueue)
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/delete-batch")

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-123"
