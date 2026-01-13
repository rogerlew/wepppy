import contextlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import ash_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ash_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(ash_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(ash_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_ash(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyAsh:
        def parse_inputs(self, payload) -> None:
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

    monkeypatch.setattr(ash_routes.Ash, "getInstance", lambda wd: DummyAsh())


def test_run_ash_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-55")
    _stub_prep(monkeypatch)
    _stub_ash(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-55"


def test_run_ash_requires_depth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-ash", json={})

    assert response.status_code == 400
    payload = response.json()
    assert (
        payload["error"]["message"]
        == "ash_depth_mode is required (0=loads, 1=depths, 2=maps)"
    )
