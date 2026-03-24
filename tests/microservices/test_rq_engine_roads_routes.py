import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import roads_routes
from wepppy.nodb.redis_prep import TaskEnum


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(roads_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(roads_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "roads-job-1"):
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

    monkeypatch.setattr(roads_routes, "Queue", DummyQueue)
    monkeypatch.setattr(roads_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return captured


def _stub_prep(monkeypatch: pytest.MonkeyPatch):
    state = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            state["jobs"].append((key, job_id))

    monkeypatch.setattr(roads_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


def test_prepare_roads_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="roads-prepare-7")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(roads_routes, "acquire_roads_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(roads_routes, "release_roads_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(roads_routes, "ensure_no_active_roads_job", lambda _runid, _prep, _redis_conn: None)
    monkeypatch.setattr(roads_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/prepare-roads", json={})

    assert response.status_code == 202
    assert response.json() == {"job_id": "roads-prepare-7"}
    assert captured["args"][0] is roads_routes.run_roads_prepare_rq
    assert prep_state["removed"] == [TaskEnum.run_roads]
    assert prep_state["jobs"] == [("run_roads_prepare_rq", "roads-prepare-7")]


def test_run_roads_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    captured = _stub_queue(monkeypatch, job_id="roads-run-9")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(roads_routes, "acquire_roads_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(roads_routes, "release_roads_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(roads_routes, "ensure_no_active_roads_job", lambda _runid, _prep, _redis_conn: None)
    monkeypatch.setattr(roads_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-roads", json={})

    assert response.status_code == 202
    assert response.json() == {"job_id": "roads-run-9"}
    assert captured["args"][0] is roads_routes.run_roads_rq
    assert prep_state["removed"] == [TaskEnum.run_roads]
    assert prep_state["jobs"] == [("run_roads_rq", "roads-run-9")]


def test_prepare_roads_returns_409_when_singleflight_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="roads-prepare-7")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(roads_routes, "acquire_roads_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(roads_routes, "release_roads_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(
        roads_routes,
        "ensure_no_active_roads_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            roads_routes.RoadsSingleFlightConflict("Roads job already active for this run.")
        ),
    )
    monkeypatch.setattr(roads_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/prepare-roads", json={})

    assert response.status_code == 409
    payload = response.json()
    assert "already active" in payload["error"]["message"]
