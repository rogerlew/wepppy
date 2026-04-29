import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import soils_routes
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(soils_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(soils_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(soils_routes, "Queue", DummyQueue)
    monkeypatch.setattr(soils_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    state: dict[str, list[object]] = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task, *args, **kwargs) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key, job_id, *args, **kwargs) -> None:
            state["jobs"].append((key, job_id))

    monkeypatch.setattr(soils_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


def test_build_soils_requires_initial_sat(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(soils_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-soils", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "initial_sat must be numeric"


def test_build_soils_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(soils_routes, "get_wd", lambda runid: "/tmp/run")

    class DummySoils:
        run_group = "default"
        mods: set[str] = set()
        initial_sat = None

    monkeypatch.setattr(
        soils_routes.Soils,
        "getInstance",
        lambda wd: DummySoils(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-soils",
            json={"initial_sat": 0.42},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert prep_state["removed"] == [
        soils_routes.TaskEnum.build_soils,
        soils_routes.TaskEnum.run_geneva,
    ]
    assert prep_state["jobs"] == [("build_soils_rq", "job-77")]


def test_build_soils_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(soils_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _rel: str, *, view: str = "effective"):
        raise NoDirError(http_status=500, code="NODIR_INVALID_ARCHIVE", message="invalid")

    monkeypatch.setattr(soils_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-soils", json={"initial_sat": 0.5})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "NODIR_INVALID_ARCHIVE"
