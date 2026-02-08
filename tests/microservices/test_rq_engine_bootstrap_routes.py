from __future__ import annotations

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import bootstrap_routes
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.weppcloud.bootstrap.enable_jobs import BootstrapLockBusyError

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch, *, claims: dict | None = None) -> None:
    resolved_claims = claims or {"sub": "7", "email": "user@example.com"}
    monkeypatch.setattr(
        bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: resolved_claims,
    )
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-1") -> None:
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

    monkeypatch.setattr(bootstrap_routes, "Queue", DummyQueue)
    monkeypatch.setattr(bootstrap_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch, tasks: list[TaskEnum]) -> None:
    class DummyPrep:
        def remove_timestamp(self, task: TaskEnum) -> None:
            tasks.append(task)

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(bootstrap_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_bootstrap_enable_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes, "_ensure_bootstrap_eligibility", lambda runid, require_owner: None)
    monkeypatch.setattr(
        bootstrap_routes,
        "enqueue_bootstrap_enable",
        lambda runid, actor: (
            {"enabled": False, "queued": True, "job_id": "enable-1", "message": "Bootstrap enable job enqueued."},
            202,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 202
    assert response.json() == {
        "enabled": False,
        "queued": True,
        "job_id": "enable-1",
        "message": "Bootstrap enable job enqueued.",
        "status_url": "/rq-engine/api/jobstatus/enable-1",
    }


def test_bootstrap_enable_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes, "_ensure_bootstrap_eligibility", lambda runid, require_owner: None)

    def _raise_busy(runid: str, actor: str):
        raise BootstrapLockBusyError("bootstrap lock busy")

    monkeypatch.setattr(bootstrap_routes, "enqueue_bootstrap_enable", _raise_busy)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_mint_token_requires_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"token_class": "session", "sub": "session-1"})
    monkeypatch.setattr(bootstrap_routes, "_ensure_bootstrap_eligibility", lambda runid, require_owner: None)
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "User identity claims are required to mint bootstrap tokens"


def test_bootstrap_mint_token_returns_clone_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "42", "email": "owner@example.com"})
    monkeypatch.setattr(bootstrap_routes, "_ensure_bootstrap_eligibility", lambda runid, require_owner: None)

    class DummyWepp:
        bootstrap_enabled = True

        def mint_bootstrap_jwt(self, user_email: str, user_id: str) -> str:
            return f"https://{user_id}:token@example.test/git/ru/run-1/.git"

    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: DummyWepp())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 200
    assert response.json() == {"clone_url": "https://42:token@example.test/git/ru/run-1/.git"}


def test_bootstrap_checkout_requires_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "sha required"


def test_bootstrap_checkout_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes, "_ensure_bootstrap_eligibility", lambda runid, require_owner: None)
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        bootstrap_routes.Wepp,
        "getInstance",
        lambda wd: type("W", (), {"bootstrap_enabled": True, "checkout_bootstrap_commit": lambda self, sha: True})(),
    )
    monkeypatch.setattr(bootstrap_routes, "acquire_bootstrap_git_lock", lambda *args, **kwargs: None)

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(bootstrap_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={"sha": "abc1234"})

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_run_wepp_npprep_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": True})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert set(tasks) == {
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_path_cost_effective,
    }


def test_bootstrap_run_swat_noprep_rejects_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-swat-noprep")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Bootstrap is not enabled for this run"
