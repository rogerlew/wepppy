import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import treatments_routes
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(treatments_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(treatments_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(treatments_routes, "Queue", DummyQueue)
    monkeypatch.setattr(treatments_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(treatments_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_build_treatments_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(treatments_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyTreatments:
        mode = treatments_routes.TreatmentsMode.UserDefinedSelection

    class DummyLanduse:
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

    monkeypatch.setattr(
        treatments_routes.Treatments,
        "getInstance",
        lambda wd: DummyTreatments(),
    )
    monkeypatch.setattr(
        treatments_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-treatments", json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-42"


def test_build_treatments_requires_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(treatments_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyTreatments:
        mode = treatments_routes.TreatmentsMode.UserDefinedMap

    class DummyLanduse:
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

    monkeypatch.setattr(
        treatments_routes.Treatments,
        "getInstance",
        lambda wd: DummyTreatments(),
    )
    monkeypatch.setattr(
        treatments_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-treatments", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "landuse_management_mapping_selection must be provided"


@pytest.mark.parametrize(
    ("http_status", "code"),
    [
        (409, "NODIR_MIXED_STATE"),
        (500, "NODIR_INVALID_ARCHIVE"),
        (503, "NODIR_LOCKED"),
    ],
)
def test_build_treatments_propagates_nodir_preflight_errors_and_skips_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    code: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(treatments_routes, "get_wd", lambda runid: "/tmp/run")

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

    monkeypatch.setattr(treatments_routes, "nodir_resolve", _raise_nodir)
    monkeypatch.setattr(treatments_routes, "Queue", DummyQueue)
    monkeypatch.setattr(treatments_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-treatments", json={})

    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code
    assert queue_called["called"] is False
