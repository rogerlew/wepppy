import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import landuse_soils_routes


pytestmark = pytest.mark.microservice


def test_landuse_and_soils_requires_extent() -> None:
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/landuse-and-soils", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Expecting extent"


def test_landuse_and_soils_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyJob:
        id = "job-123"

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

    monkeypatch.setattr(landuse_soils_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_soils_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/landuse-and-soils",
            json={"extent": [0, 1, 2, 3]},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"


def test_landuse_and_soils_download_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(landuse_soils_routes, "LANDUSE_ARCHIVE_ROOTS", (tmp_path,))

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/landuse-and-soils/missing.tar.gz")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["message"] == "File not found"
