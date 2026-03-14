import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import polaris_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(polaris_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(polaris_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(polaris_routes, "Queue", DummyQueue)
    monkeypatch.setattr(polaris_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(polaris_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_acquire_polaris_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(polaris_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/acquire-polaris",
            json={
                "force_refresh": True,
                "keep_source_intermediates": False,
                "layers": ["sand_mean_0_5", "clay_mean_0_5"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-77"
    assert payload["payload"]["force_refresh"] is True
    assert payload["payload"]["keep_source_intermediates"] is False
    assert payload["payload"]["layers"] == ["sand_mean_0_5", "clay_mean_0_5"]


def test_acquire_polaris_auth_error_returns_canonical_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def _reject(request, required_scopes=None):
        raise polaris_routes.AuthError("denied", status_code=403, code="forbidden")

    monkeypatch.setattr(polaris_routes, "require_jwt", _reject)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/acquire-polaris", json={})

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "denied"
