import contextlib

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


def _stub_ash(monkeypatch: pytest.MonkeyPatch, *, run_group: str = "") -> None:
    class DummyAsh:
        run_group = ""
        _ash_load_fn = None

        def parse_inputs(self, payload) -> None:
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
