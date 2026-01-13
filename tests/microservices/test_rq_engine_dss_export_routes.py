import contextlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import dss_export_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dss_export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(dss_export_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(dss_export_routes, "Queue", DummyQueue)
    monkeypatch.setattr(dss_export_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(dss_export_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _stub_wepp_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyWepp:
        dss_excluded_channel_orders = [1, 2]

        @contextlib.contextmanager
        def locked(self):
            yield self

    monkeypatch.setattr(dss_export_routes.Wepp, "getInstance", lambda wd: DummyWepp())
    monkeypatch.setattr(dss_export_routes.Watershed, "getInstance", lambda wd: object())


def test_post_dss_export_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-55")
    _stub_prep(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(dss_export_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/post-dss-export-rq",
            json={
                "dss_export_mode": 1,
                "dss_export_channel_ids": [12, 34],
                "dss_start_date": "01/01/2001",
                "dss_end_date": "01/31/2001",
            },
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-55"


def test_post_dss_export_invalid_date(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_wepp_stack(monkeypatch)
    monkeypatch.setattr(dss_export_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/post-dss-export-rq",
            json={
                "dss_export_mode": 1,
                "dss_start_date": "bad-date",
                "dss_end_date": "01/31/2001",
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Invalid DSS start date; use MM/DD/YYYY."
