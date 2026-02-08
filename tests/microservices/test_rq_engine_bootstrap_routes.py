import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import bootstrap_routes
from wepppy.nodb.redis_prep import TaskEnum

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-1") -> None:
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

    monkeypatch.setattr(bootstrap_routes, "Queue", DummyQueue)
    monkeypatch.setattr(bootstrap_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch, tasks: list[TaskEnum]) -> None:
    class DummyPrep:
        def remove_timestamp(self, task: TaskEnum) -> None:
            tasks.append(task)

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(bootstrap_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_bootstrap_run_wepp_npprep_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert set(tasks) == {
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_path_cost_effective,
    }


def test_bootstrap_run_swat_noprep_rejects_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-swat-noprep")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Bootstrap is not enabled for this run"
