import contextlib
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import climate_routes
from wepppy.runtime_paths.errors import NoDirError


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


def _stub_prep(monkeypatch: pytest.MonkeyPatch):
    state = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task, *args, **kwargs) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key, job_id, *args, **kwargs) -> None:
            state["jobs"].append((key, job_id))

    monkeypatch.setattr(climate_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


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
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Validation failed"
    assert payload["errors"][0]["message"] == "Invalid climate field values."


def test_build_climate_parse_missing_field_key_error_returns_structured_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"

        def parse_inputs(self, payload) -> None:
            raise KeyError("future_start_year")

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"] == [
        {
            "field": "future_start_year",
            "code": "missing_required_field",
            "message": "Missing required field: future_start_year",
        }
    ]


def test_build_climate_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-88")
    prep_state = _stub_prep(monkeypatch)
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
    assert prep_state["removed"] == [
        climate_routes.TaskEnum.build_climate,
        climate_routes.TaskEnum.build_rusle,
    ]
    assert prep_state["jobs"] == [("build_climate_rq", "job-88")]


def test_build_climate_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _rel: str, *, view: str = "effective"):
        raise NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")

    monkeypatch.setattr(climate_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NODIR_LOCKED"


def test_build_climate_rejects_archive_form_root(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        climate_routes,
        "nodir_resolve",
        lambda _wd, _rel, view="effective": SimpleNamespace(form="archive"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_ARCHIVE_ACTIVE"


def test_build_climate_runtime_preflight_error_uses_generic_parse_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        climate_routes,
        "nodir_resolve",
        lambda _wd, _rel, view="effective": (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Error parsing climate inputs"


def test_build_climate_observed_year_bounds_validation_failure_returns_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"
        climate_mode = climate_routes.ClimateMode.ObservedPRISM

        def parse_inputs(self, payload) -> None:
            return None

        @contextlib.contextmanager
        def locked(self):
            yield

        def _require_observed_year_bounds_for_build(self) -> tuple[int, int]:
            raise ValueError("observed_start_year must be an integer year, got empty string")

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"][0]["code"] == "invalid_request"
