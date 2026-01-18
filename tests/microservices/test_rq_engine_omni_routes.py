import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import omni_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(omni_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(omni_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(omni_routes, "Queue", DummyQueue)
    monkeypatch.setattr(omni_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(omni_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_omni(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyOmni:
        def parse_scenarios(self, scenarios) -> None:
            return None

        def parse_inputs(self, payload) -> None:
            return None

        def build_contrasts(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())


def test_run_omni_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-11")
    _stub_prep(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={"scenarios": [{"type": "uniform_low"}]},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-11"


def test_run_omni_requires_scenarios(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni",
            json={},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Missing scenarios data"


def test_run_omni_contrasts_requires_geojson_in_user_defined_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_omni(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            json={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "GeoJSON upload or path is required for user-defined contrasts."


def test_run_omni_contrasts_passes_geojson_upload_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-22")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(omni_routes, "get_wd", lambda runid: "/tmp/run")

    captured = {}

    class DummyOmni:
        def parse_inputs(self, payload) -> None:
            captured["payload"] = payload

        def build_contrasts(self, *args, **kwargs) -> None:
            captured["build"] = kwargs

    monkeypatch.setattr(omni_routes.Omni, "getInstance", lambda wd: DummyOmni())
    monkeypatch.setattr(omni_routes, "_save_upload", lambda *args, **kwargs: "/tmp/uploaded.geojson")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-omni-contrasts",
            data={
                "omni_contrast_selection_mode": "user_defined_areas",
                "omni_control_scenario": "uniform_low",
                "omni_contrast_scenario": "mulch",
            },
            files={"omni_contrast_geojson": ("areas.geojson", b"{}", "application/geo+json")},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-22"
    assert captured["payload"]["omni_contrast_geojson_path"] == "/tmp/uploaded.geojson"
