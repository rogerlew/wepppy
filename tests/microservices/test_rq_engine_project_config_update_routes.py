from __future__ import annotations

from dataclasses import dataclass
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import project_config_update_routes as routes
from wepppy.nodb.project_config_update import ConfigUpdateAddition, ConfigUpdatePreview

pytestmark = pytest.mark.microservice


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def set(self, key, value, *, nx=False, ex=None):
        if nx and key in self.values: return False
        self.values[key] = value; return True
    def get(self, key): return self.values.get(key)
    def delete(self, key): return int(self.values.pop(key, None) is not None)


@dataclass
class Enqueued:
    id: str


class FakeQueue:
    calls: list[dict] = []

    def __init__(self, **_kwargs): pass
    def enqueue_call(self, func, *, args, timeout, job_id):
        self.calls.append({"func": func, "args": args, "timeout": timeout, "job_id": job_id})
        return Enqueued(job_id)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    claims = {"token_class": "user", "sub": "42"}
    preview = ConfigUpdatePreview(
        True, "pcu1-preview", (ConfigUpdateAddition("new", "option", "true", "preset", "rev-2"),),
        "config.cfg", "a" * 64,
    )
    redis_client = FakeRedis()
    FakeQueue.calls = []
    monkeypatch.setattr(routes, "require_jwt", lambda *_a, **_k: claims)
    monkeypatch.setattr(routes, "authorize_run_access", lambda *_a, **_k: None)
    monkeypatch.setattr(routes, "authorize_run_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(routes, "get_wd", lambda _runid: "/wc1/runs/run-1")
    monkeypatch.setattr(routes, "preview_project_config_update", lambda _wd: preview)
    monkeypatch.setattr(routes, "project_config_update_enabled", lambda: True)
    monkeypatch.setattr(routes.redis, "Redis", lambda **_kwargs: redis_client)
    monkeypatch.setattr(routes, "Queue", FakeQueue)
    monkeypatch.setattr(routes, "new_rq_job_id", lambda: "job-update-1")
    with TestClient(rq_engine.app) as http:
        yield http, claims, preview, redis_client


def test_availability_and_preview_are_synchronous_and_complete(client) -> None:
    http, _claims, preview, _redis = client
    availability = http.get("/api/runs/run-1/config/project-config/update-availability")
    response = http.get("/api/runs/run-1/config/project-config/update-preview")

    assert availability.status_code == 200
    assert availability.json() == {"available": True}
    assert response.status_code == 200
    assert response.json()["preview_id"] == preview.preview_id
    assert response.json()["additions"] == [{
        "section": "new", "option": "option", "value": "true",
        "source_id": "preset", "source_revision": "rev-2",
    }]


def test_apply_rejects_stale_preview_without_enqueue(client) -> None:
    http, _claims, _preview, _redis = client
    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={"preview_id": "pcu1-stale", "trigger": {"section": "new", "option": "option"}},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_config_preview"
    assert FakeQueue.calls == []


def test_apply_enqueues_once_and_reports_active_conflict(client) -> None:
    http, _claims, preview, _redis = client
    body = {"preview_id": preview.preview_id, "trigger": {"section": "new", "option": "option"}}
    accepted = http.post("/api/runs/run-1/config/project-config/update-apply", json=body)
    conflict = http.post("/api/runs/run-1/config/project-config/update-apply", json=body)

    assert accepted.status_code == 202
    assert accepted.json() == {"job_id": "job-update-1"}
    assert len(FakeQueue.calls) == 1
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "config_update_in_progress"


def test_preview_requires_mutation_authority(client, monkeypatch: pytest.MonkeyPatch) -> None:
    http, _claims, _preview, _redis = client

    def reject(*_args, **_kwargs):
        raise routes.AuthError("owner required", status_code=403, code="forbidden")

    monkeypatch.setattr(routes, "authorize_run_mutation", reject)
    response = http.get("/api/runs/run-1/config/project-config/update-preview")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_disabled_backend_returns_no_availability_and_no_enqueue(client, monkeypatch: pytest.MonkeyPatch) -> None:
    http, _claims, _preview, _redis = client
    monkeypatch.setattr(routes, "project_config_update_enabled", lambda: False)
    availability = http.get("/api/runs/run-1/config/project-config/update-availability")
    apply = http.post("/api/runs/run-1/config/project-config/update-apply", json={})
    assert availability.json() == {"available": False, "reason": "updates_disabled"}
    assert apply.status_code == 409
    assert FakeQueue.calls == []
