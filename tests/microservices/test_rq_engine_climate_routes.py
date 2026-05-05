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


def _stub_queue(
    monkeypatch: pytest.MonkeyPatch,
    *,
    job_id: str = "job-123",
) -> dict[str, list[object]]:
    state: dict[str, list[object]] = {"calls": [], "jobs": []}

    class DummyJob:
        def __init__(self) -> None:
            self.id = job_id
            self.meta: dict[str, object] = {}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            state["calls"].append((args, kwargs))
            job = DummyJob()
            if isinstance(kwargs.get("meta"), dict):
                job.meta = dict(kwargs["meta"])
            state["jobs"].append(job)
            return job

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(climate_routes, "Queue", DummyQueue)
    monkeypatch.setattr(climate_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return state


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
            "message": "Future start year is required.",
        }
    ]


def test_build_climate_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    queue_state = _stub_queue(monkeypatch, job_id="job-88")
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

    request_payload = {
        "climate_mode": "9",
        "climate_catalog_id": "observed_daymet",
        "observed_start_year": "1985",
        "observed_end_year": "2024",
    }
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-climate", json=request_payload)

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-88"
    assert prep_state["removed"] == [
        climate_routes.TaskEnum.build_climate,
        climate_routes.TaskEnum.build_rusle,
        climate_routes.TaskEnum.run_geneva,
    ]
    assert prep_state["jobs"] == [("build_climate_rq", "job-88")]
    enqueue_args, enqueue_kwargs = queue_state["calls"][0]
    assert enqueue_args[0] is climate_routes.build_climate_rq
    assert enqueue_args[1] == ("run-1",)
    assert "kwargs" not in enqueue_kwargs
    assert enqueue_kwargs["meta"] == {"build_payload": request_payload}
    queued_job = queue_state["jobs"][0]
    assert getattr(queued_job, "meta") == {"build_payload": request_payload}


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
    assert payload["errors"] == [
        {
            "field": "observed_start_year",
            "code": "missing_required_field",
            "message": "Observed start year is required.",
        }
    ]


def test_build_climate_observed_year_assertion_failure_returns_year_specific_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"
        climate_mode = climate_routes.ClimateMode.ObservedPRISM

        def parse_inputs(self, payload) -> None:
            raise AssertionError()

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-climate",
            json={
                "climate_mode": str(climate_routes.ClimateMode.ObservedPRISM.value),
                "observed_start_year": "1980",
                "observed_end_year": "1944",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"] == [
        {
            "field": "observed_end_year",
            "code": "year_out_of_range",
            "message": "Observed end year must be 1980 or later.",
        }
    ]


def test_build_climate_observed_year_order_failure_returns_comparison_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(climate_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyClimate:
        run_group = "default"
        climate_mode = climate_routes.ClimateMode.ObservedPRISM

        def parse_inputs(self, payload) -> None:
            raise AssertionError()

    monkeypatch.setattr(
        climate_routes.Climate,
        "getInstance",
        lambda wd: DummyClimate(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-climate",
            json={
                "climate_mode": str(climate_routes.ClimateMode.ObservedPRISM.value),
                "observed_start_year": "1981",
                "observed_end_year": "1980",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["errors"] == [
        {
            "field": "observed_end_year",
            "code": "year_order",
            "message": "Observed end year must be greater than or equal to observed start year (received 1980 < 1981).",
        }
    ]
