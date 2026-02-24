import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import openet_ts_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openet_ts_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(openet_ts_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(openet_ts_routes, "require_roles", lambda claims, required_roles: None)


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

    monkeypatch.setattr(openet_ts_routes, "Queue", DummyQueue)
    monkeypatch.setattr(openet_ts_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(openet_ts_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_acquire_openet_ts_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-66")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(openet_ts_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/acquire-openet-ts",
            json={"force_refresh": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-66"
    assert payload["payload"] == {"force_refresh": True}


def test_acquire_openet_ts_requires_admin_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openet_ts_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(openet_ts_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/acquire-openet-ts",
            json={"force_refresh": True},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert "required role" in payload["error"]["message"].lower()
