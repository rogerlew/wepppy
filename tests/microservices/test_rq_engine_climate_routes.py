import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import climate_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(climate_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(climate_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(climate_routes, "Queue", DummyQueue)
    monkeypatch.setattr(climate_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(climate_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_build_climate_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"

        def parse_inputs(self, payload) -> None:
            raise ValueError("bad payload")

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Error parsing climate inputs"


def test_build_climate_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-88")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-88"
