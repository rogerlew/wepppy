import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import rusle_routes
from wepppy.nodb.redis_prep import TaskEnum


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rusle_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(rusle_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123"):
    captured: dict[str, object] = {}

    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(rusle_routes, "Queue", DummyQueue)
    monkeypatch.setattr(rusle_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return captured


def _stub_prep(monkeypatch: pytest.MonkeyPatch):
    state = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            state["jobs"].append((key, job_id))

    monkeypatch.setattr(rusle_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


def test_build_rusle_enqueues_job_with_filtered_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-77")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(rusle_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-rusle",
            json={
                "r_mode": "momm2025_county_region",
                "c_mode": "observed_rap",
                "k_modes": ["polaris_nomograph"],
                "default_k_mode": "polaris_nomograph",
                "rap_year": 2025,
                "max_slope_length_m": 250.5,
                "p_value": 0.85,
                "force_polaris_refresh": "true",
                "unexpected": "ignore-me",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-77"
    assert payload["payload"] == {
        "r_mode": "momm2025_county_region",
        "c_mode": "observed_rap",
        "k_modes": "polaris_nomograph",
        "default_k_mode": "polaris_nomograph",
        "rap_year": 2025,
        "max_slope_length_m": 250.5,
        "p_value": 0.85,
        "force_polaris_refresh": True,
    }

    enqueue_kwargs = captured["kwargs"]
    assert enqueue_kwargs["kwargs"] == {"payload": payload["payload"]}
    assert prep_state["removed"] == [TaskEnum.build_rusle]
    assert prep_state["jobs"] == [("build_rusle_rq", "job-77")]


def test_build_rusle_enqueues_job_without_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="job-11")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(rusle_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-rusle", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"job_id": "job-11"}

    enqueue_kwargs = captured["kwargs"]
    assert enqueue_kwargs["kwargs"] is None
    assert prep_state["removed"] == [TaskEnum.build_rusle]
    assert prep_state["jobs"] == [("build_rusle_rq", "job-11")]
