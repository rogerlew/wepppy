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


def test_run_sync_passes_source_run_token_to_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_sync_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"roles": ["Admin"]},
    )

    enqueue_calls: list[tuple] = []

    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class CapturingQueue:
        counter = 0

        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            enqueue_calls.append((args, kwargs))
            CapturingQueue.counter += 1
            return DummyJob(f"job-{CapturingQueue.counter}")

        def get_job_ids(self):
            return []

    class DummyRedis:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}
            self.setex_calls: list[tuple[str, int, str]] = []

        def setex(self, key: str, ttl: int, value: str) -> None:
            self.values[key] = value
            self.setex_calls.append((key, ttl, value))

        def delete(self, key: str) -> int:
            return int(self.values.pop(key, None) is not None)

        def close(self) -> None:
            return None

    redis_conn = DummyRedis()
    monkeypatch.setattr(run_sync_routes, "Queue", CapturingQueue)
    monkeypatch.setattr(run_sync_routes.redis, "Redis", lambda **kwargs: redis_conn)
    monkeypatch.setattr(run_sync_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/run-sync",
            json={
                "runid": "run-1",
                "source_run_token": "  token-abc  ",
                "run_migrations": False,
            },
        )

    assert response.status_code == 200
    assert len(enqueue_calls) == 1

    call_args, call_kwargs = enqueue_calls[0]
    assert call_args[0] is run_sync_routes.run_sync_rq
    assert call_args[1] == ("run-1", "wepp.cloud", None, run_sync_routes.DEFAULT_TARGET_ROOT, None)
    assert call_kwargs["timeout"] == run_sync_routes.RUN_SYNC_TIMEOUT
    assert "meta" in call_kwargs
    assert call_kwargs["meta"]["source_run_token_key"].startswith(
        f"{run_sync_routes.SOURCE_RUN_TOKEN_KEY_PREFIX}:"
    )
    assert redis_conn.setex_calls == [
        (
            call_kwargs["meta"]["source_run_token_key"],
            run_sync_routes.SOURCE_RUN_TOKEN_TTL,
            "token-abc",
        )
    ]


def test_serialize_job_uses_source_host_from_args_position_one() -> None:
    class DummyJob:
        id = "job-1"
        meta = {}
        args = ("run-1", "wepp.cloud", "owner@example.com", "/wc1/runs", "cfg", "token-abc")
        enqueued_at = None
        started_at = None
        ended_at = None

        @staticmethod
        def get_status(refresh=False):
            return "queued"

    payload = run_sync_routes._serialize_job(DummyJob(), "queued")
    assert payload["runid"] == "run-1"
    assert payload["config"] == "cfg"
    assert payload["source_host"] == "wepp.cloud"


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
