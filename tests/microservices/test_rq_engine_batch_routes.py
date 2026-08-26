import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import batch_routes


pytestmark = pytest.mark.microservice


class _DummyLock:
    def acquire(self, **kwargs) -> bool:
        return True

    def release(self) -> None:
        return None

    def extend(self, *args, **kwargs) -> bool:
        return True


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


def test_run_batch_invalid_name_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/ab/run-batch")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "invalid_batch_name"


def test_run_batch_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyBatchRunner:
        def set_rq_job_id(self, key: str, job_id: str) -> None:
            assert (key, job_id) == ("run_batch_rq", "job-123")

    class DummyJob:
        id = "job-123"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def set(self, *args, **kwargs): return True

        def lock(self, *args, **kwargs):
            return _DummyLock()

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
        lambda batch_name: DummyBatchRunner(),
    )
    monkeypatch.setattr(batch_routes, "new_rq_job_id", lambda: "job-123")
    monkeypatch.setattr(batch_routes, "Queue", DummyQueue)
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        batch_routes,
        "reconcile_deferred_batch_jobs",
        lambda batch_name, redis_conn=None, **_kwargs: [],
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/run-batch")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"


def test_run_batch_busy_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(
        batch_routes,
        "reconcile_deferred_batch_jobs",
        lambda batch_name, redis_conn=None, **_kwargs: ["job-1:started:run_batch_rq"],
    )

    class DummyRedis:
        def set(self, *args, **kwargs): return True

        def lock(self, *args, **kwargs):
            return _DummyLock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/run-batch")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "batch_busy"
    assert "Active jobs" in payload["error"]["details"]


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
        "reconcile_deferred_batch_jobs",
        lambda batch_name, redis_conn=None, **_kwargs: ["job-1:started:run_batch_rq"],
    )

    class DummyRedis:
        def set(self, *args, **kwargs): return True

        def lock(self, *args, **kwargs):
            return _DummyLock()

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
        def set(self, *args, **kwargs): return True

        def lock(self, *args, **kwargs):
            return _DummyLock()

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
        "reconcile_deferred_batch_jobs",
        lambda batch_name, redis_conn=None, **_kwargs: [],
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
        def set(self, *args, **kwargs): return True

        def lock(self, *args, **kwargs):
            return _DummyLock()

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
        "reconcile_deferred_batch_jobs",
        lambda batch_name, redis_conn=None, **_kwargs: [],
    )
    monkeypatch.setattr(
        batch_routes.BatchRunner,
        "getInstanceFromBatchName",
        lambda batch_name: DummyBatchRunner(),
    )
    monkeypatch.setattr(batch_routes, "new_rq_job_id", lambda: "job-123")
    monkeypatch.setattr(batch_routes, "Queue", DummyQueue)
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/batch/_/demo/delete-batch")

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-123"


@pytest.mark.parametrize(
    ("path", "receipt_key", "success_code"),
    (
        ("run-batch", "run_batch_rq", 200),
        ("delete-batch", "delete_batch_rq", 202),
    ),
)
@pytest.mark.parametrize("prior_state", ("deferred", "queued", "started", "scheduled"))
def test_batch_actual_producers_apply_deferred_and_active_contract(
    path: str,
    receipt_key: str,
    success_code: int,
    prior_state: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple] = []

    class Runner:
        def set_rq_job_id(self, key, job_id):
            events.append(("hint", key, job_id))

    class Redis:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def lock(self, *_args, **_kwargs): return _DummyLock()
        def set(self, key, value): events.append(("redis-hint", key, value))

    class Queue:
        def __init__(self, *_args, **_kwargs): pass
        def enqueue_call(self, *_args, **kwargs):
            events.append(("enqueue", kwargs["job_id"]))
            return type("Job", (), {"id": kwargs["job_id"]})()

    monkeypatch.setattr(batch_routes, "require_jwt", lambda *_args, **_kwargs: {"roles": ["Admin"]})
    monkeypatch.setattr(batch_routes.BatchRunner, "getInstanceFromBatchName", lambda _name: Runner())
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **_kwargs: Redis())
    monkeypatch.setattr(batch_routes, "Queue", Queue)
    monkeypatch.setattr(batch_routes, "new_rq_job_id", lambda: "replacement-batch")
    monkeypatch.setattr(
        batch_routes,
        "reconcile_deferred_batch_jobs",
        lambda *_args, **_kwargs: (
            [] if prior_state == "deferred" else [f"old-job:{prior_state}"]
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(f"/api/batch/_/demo/{path}")

    if prior_state == "deferred":
        assert response.status_code == success_code
        assert ("hint", receipt_key, "replacement-batch") in events
        assert ("enqueue", "replacement-batch") in events
    else:
        assert response.status_code == 409
        assert not any(event[0] in {"hint", "enqueue"} for event in events)


@pytest.mark.parametrize("path", ("run-batch", "delete-batch"))
@pytest.mark.parametrize("failure", ("cleanup", "hint-save", "enqueue"))
def test_batch_actual_producer_failure_postconditions(
    path: str, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple] = []

    class Runner:
        def set_rq_job_id(self, key, job_id):
            if failure == "hint-save":
                raise OSError("receipt save failed")
            events.append(("hint", key, job_id))

    class Redis:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def lock(self, *_args, **_kwargs): return _DummyLock()
        def set(self, key, value): events.append(("redis-hint", key, value))

    class Queue:
        def __init__(self, *_args, **_kwargs): pass
        def enqueue_call(self, *_args, **kwargs):
            events.append(("enqueue", kwargs["job_id"]))
            if failure == "enqueue":
                raise batch_routes.redis.RedisError("enqueue failed")
            return type("Job", (), {"id": kwargs["job_id"]})()

    monkeypatch.setattr(batch_routes, "require_jwt", lambda *_args, **_kwargs: {"roles": ["Admin"]})
    monkeypatch.setattr(batch_routes.BatchRunner, "getInstanceFromBatchName", lambda _name: Runner())
    monkeypatch.setattr(batch_routes.redis, "Redis", lambda **_kwargs: Redis())
    monkeypatch.setattr(batch_routes, "Queue", Queue)
    monkeypatch.setattr(batch_routes, "new_rq_job_id", lambda: "replacement-batch")

    def reconcile(*_args, **_kwargs):
        if failure == "cleanup":
            raise batch_routes.redis.RedisError("cleanup failed")
        return []

    monkeypatch.setattr(batch_routes, "reconcile_deferred_batch_jobs", reconcile)

    with TestClient(rq_engine.app) as client:
        response = client.post(f"/api/batch/_/demo/{path}")

    assert response.status_code == 500
    if failure in {"cleanup", "hint-save"}:
        assert not any(event[0] == "enqueue" for event in events)
    else:
        assert ("enqueue", "replacement-batch") in events
