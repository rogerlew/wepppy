import contextlib
import json
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import ash_routes
from wepppy.runtime_paths.errors import NoDirError


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


def _stub_ash(
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_group: str = "",
    parsed_payload: dict | None = None,
) -> None:
    class DummyAsh:
        run_group = ""
        _ash_load_fn = None

        def parse_inputs(self, payload) -> None:
            if parsed_payload is not None:
                parsed_payload.update(payload)
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

        @property
        def ash_load_fn(self):
            return self._ash_load_fn

    DummyAsh.run_group = run_group
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


def test_run_ash_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch, run_group="batch")
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

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
    assert response.json()["message"] == "Set ash inputs for batch processing"
    assert queue_called["called"] is False


def test_run_ash_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch, run_group="")
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for _base runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set ash inputs for batch processing"
    assert queue_called["called"] is False


def test_run_ash_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch, run_group="")
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for runid ;;_base runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set ash inputs for batch processing"
    assert queue_called["called"] is False


def test_run_ash_batch_multipart_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch, run_group="batch")
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used for batch runs")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            data={
                "ash_depth_mode": "2",
                "ini_black_depth": "1.2",
                "ini_white_depth": "2.3",
            },
            files={
                "input_upload_ash_load": (
                    "ash-load.tif",
                    b"fake-tif-bytes",
                    "image/tiff",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set ash inputs for batch processing"
    assert queue_called["called"] is False


def test_run_ash_normalizes_legacy_selector_names_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    class ParsingAsh:
        run_group = "batch"
        _model = "multi"
        _field_black_ash_bulkdensity = 0.22
        _field_white_ash_bulkdensity = 0.31
        _alex_white_ash_model_pars = SimpleNamespace(
            ini_bulk_den=0.31,
            fin_bulk_den=0.62,
            bulk_den_fac=0.005,
            par_den=1.2,
            decomp_fac=0.00018,
            roughness_limit=1.0,
            org_mat=0.04,
            transport_mode="dynamic",
            initranscap=0.8,
            depletcoeff=0.009,
        )
        _alex_black_ash_model_pars = SimpleNamespace(
            ini_bulk_den=0.22,
            fin_bulk_den=0.62,
            bulk_den_fac=0.005,
            par_den=1.2,
            decomp_fac=0.00018,
            roughness_limit=1.0,
            org_mat=0.065,
            transport_mode="dynamic",
            initranscap=0.8,
            depletcoeff=0.009,
        )

        @property
        def model(self) -> str:
            return self._model

        @contextlib.contextmanager
        def locked(self):
            yield self

        parse_inputs = ash_routes.Ash.parse_inputs

    ash = ParsingAsh()
    monkeypatch.setattr(ash_routes.Ash, "getInstance", lambda wd: ash)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            data={
                "fire_date": "8/4",
                "ash_depth_mode": "1",
                "ini_black_depth": "5",
                "ini_white_depth": "5",
                "ash_model_select": "alex",
                "ash_transport_mode_select": "static",
                "white_initranscap": "2.0",
                "black_initranscap": "2.0",
                "white_depletcoeff": "0.1",
                "black_depletcoeff": "0.1",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set ash inputs for batch processing"
    assert ash.model == "alex"
    assert ash._alex_white_ash_model_pars.transport_mode == "static"
    assert ash._alex_black_ash_model_pars.transport_mode == "static"
    assert ash._alex_white_ash_model_pars.initranscap == 2.0
    assert ash._alex_black_ash_model_pars.initranscap == 2.0
    assert ash._alex_white_ash_model_pars.depletcoeff == 0.1
    assert ash._alex_black_ash_model_pars.depletcoeff == 0.1


@pytest.mark.parametrize(
    ("selector_fields", "message"),
    [
        ({"ash_model_select": "bogus"}, "ash_model must be one of: multi, alex"),
        (
            {"ash_transport_mode_select": "bogus"},
            "transport_mode must be one of: dynamic, static",
        ),
        (
            {"ash_model": "alex", "ash_model_select": "multi"},
            "ash_model conflicts with legacy field ash_model_select",
        ),
        (
            {"transport_mode": "static", "ash_transport_mode_select": "dynamic"},
            "transport_mode conflicts with legacy field ash_transport_mode_select",
        ),
    ],
)
def test_run_ash_rejects_invalid_or_conflicting_selector_fields(
    monkeypatch: pytest.MonkeyPatch,
    selector_fields: dict[str, str],
    message: str,
) -> None:
    _stub_auth(monkeypatch)
    parsed_payload: dict = {}
    _stub_ash(monkeypatch, run_group="batch", parsed_payload=parsed_payload)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            data={
                "ash_depth_mode": "1",
                "ini_black_depth": "5",
                "ini_white_depth": "5",
                **selector_fields,
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == message
    assert parsed_payload == {}


def test_run_ash_rejects_conflicting_selector_array_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    parsed_payload: dict = {}
    _stub_ash(monkeypatch, run_group="batch", parsed_payload=parsed_payload)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 5,
                "ini_white_depth": 5,
                "ash_model": ["alex", "bogus"],
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "ash_model contains conflicting values"
    assert parsed_payload == {}


def test_run_ash_collapses_identical_selector_array_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    parsed_payload: dict = {}
    _stub_ash(monkeypatch, run_group="batch", parsed_payload=parsed_payload)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 5,
                "ini_white_depth": 5,
                "ash_model": ["alex", "alex"],
                "transport_mode": ["static", "static"],
            },
        )

    assert response.status_code == 200
    assert parsed_payload["ash_model"] == "alex"
    assert parsed_payload["transport_mode"] == "static"


@pytest.mark.parametrize("invalid_value", [None, {}, []])
def test_run_ash_rejects_empty_or_non_string_selector_values(
    monkeypatch: pytest.MonkeyPatch,
    invalid_value: object,
) -> None:
    _stub_auth(monkeypatch)
    parsed_payload: dict = {}
    _stub_ash(monkeypatch, run_group="batch", parsed_payload=parsed_payload)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 5,
                "ini_white_depth": 5,
                "ash_model": invalid_value,
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "ash_model must be a non-empty string"
    assert parsed_payload == {}


def test_run_ash_rejects_invalid_upload_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: str(tmp_path / "run"))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            data={"ash_depth_mode": "2"},
            files={
                "input_upload_ash_load": (
                    "ash-load.exe",
                    b"fake-bytes",
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"].startswith("Invalid file extension.")


def test_run_ash_rejects_oversize_upload_with_413(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch)
    monkeypatch.setattr(ash_routes, "ASH_MAX_BYTES", 4)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: str(tmp_path / "run"))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            data={"ash_depth_mode": "2"},
            files={
                "input_upload_ash_load": (
                    "ash-load.tif",
                    b"abcdef",
                    "image/tiff",
                )
            },
        )

    assert response.status_code == 413
    payload = response.json()
    assert "maximum allowed size" in payload["error"]["message"]


def test_run_ash_auth_boundary_error_does_not_include_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_auth_error(request, required_scopes=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(ash_routes, "require_jwt", _raise_auth_error)
    monkeypatch.setattr(ash_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["message"] == "Failed to authorize request"
    assert "traceback" not in json.dumps(payload).lower()


def test_run_ash_enqueue_boundary_error_does_not_include_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_ash(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            raise RuntimeError("queue exploded")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error Running Ash Transport"
    assert "traceback" not in json.dumps(payload).lower()


@pytest.mark.parametrize(
    ("http_status", "code"),
    [
        (409, "NODIR_MIXED_STATE"),
        (500, "NODIR_INVALID_ARCHIVE"),
        (503, "NODIR_LOCKED"),
    ],
)
def test_run_ash_propagates_nodir_preflight_errors_and_skips_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    code: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(ash_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _root: str, *, view: str = "effective") -> None:
        raise NoDirError(http_status=http_status, code=code, message="blocked")

    queue_called = {"called": False}

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            queue_called["called"] = True

        def enqueue_call(self, *args, **kwargs):
            raise AssertionError("Queue should not be used when NoDir preflight fails")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ash_routes, "nodir_resolve", _raise_nodir)
    monkeypatch.setattr(ash_routes, "Queue", DummyQueue)
    monkeypatch.setattr(ash_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-ash",
            json={
                "ash_depth_mode": 1,
                "ini_black_depth": 1.2,
                "ini_white_depth": 2.3,
            },
        )

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code
    assert queue_called["called"] is False
