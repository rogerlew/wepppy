import contextlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import wepp_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(wepp_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(wepp_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_wepp_stack(
    monkeypatch: pytest.MonkeyPatch,
    *,
    parse_error: bool = False,
    run_group: str = "",
) -> None:
    class DummyRon:
        mods = []

    class DummySoils:
        clip_soils = False
        clip_soils_depth = None
        initial_sat = None

    class DummyWatershed:
        clip_hillslopes = False
        clip_hillslope_length = None

    class DummyWepp:
        run_group = ""
        dss_excluded_channel_orders = [1, 2]

        def parse_inputs(self, payload) -> None:
            if parse_error:
                raise ValueError("bad payload")
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

    DummyWepp.run_group = run_group

    monkeypatch.setattr(wepp_routes.Soils, "getInstance", lambda wd: DummySoils())
    monkeypatch.setattr(wepp_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(wepp_routes.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(wepp_routes.Ron, "getInstance", lambda wd: DummyRon())


def test_run_wepp_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"


def test_run_wepp_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch, parse_error=True)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "bad payload"


def test_run_wepp_watershed_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-88")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.2},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-88"


def test_prep_wepp_watershed_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/prep-wepp-watershed",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.2},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-99"


def test_run_wepp_batch_returns_input_message_without_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_prep_wepp_watershed_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/prep-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_runid_base_suffix_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/batch%3B%3Bdemo_batch%3B%3B_base/cfg/run-wepp",
            json={"clip_soils": True, "clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_watershed_batch_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="batch")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_watershed_base_project_context_returns_input_message_without_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch, run_group="")
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(wepp_routes, "Queue", DummyQueue)
    monkeypatch.setattr(wepp_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/_base/run-wepp-watershed",
            json={"clip_hillslopes": True, "initial_sat": 0.3},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set wepp inputs for batch processing"
    assert queue_called["called"] is False


def test_run_wepp_setup_failure_returns_canonical_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(wepp_routes, "get_wd", lambda runid: "/tmp/run")

    class ExplodingSoils:
        @property
        def clip_soils(self):
            return False

        @clip_soils.setter
        def clip_soils(self, value):
            raise RuntimeError("soil write failed")

    monkeypatch.setattr(wepp_routes.Soils, "getInstance", lambda wd: ExplodingSoils())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-wepp",
            json={"clip_soils": True},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error preparing WEPP run request"
    assert "RuntimeError: soil write failed" in payload["error"]["details"]
