import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import landuse_routes
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(landuse_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(landuse_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_build_landuse_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-42"


def test_build_landuse_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            raise ValueError("bad payload")

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "bad payload"


def test_build_landuse_requires_mapping_for_user_defined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "landuse_management_mapping_selection must be provided"


def test_build_landuse_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _rel: str, *, view: str = "effective"):
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(landuse_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"


def test_build_landuse_user_defined_propagates_mutation_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"
        mapping = None
        user_defined_landcover_fn = "existing.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    def _raise_nodir(
        wd: str,
        root: str,
        callback,
        *,
        purpose: str = "nodir-mutation",
    ):
        raise NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")

    monkeypatch.setattr(landuse_routes, "mutate_root", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            json={"landuse_management_mapping_selection": "default"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NODIR_LOCKED"
