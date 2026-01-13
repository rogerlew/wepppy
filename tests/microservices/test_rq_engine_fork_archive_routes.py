import contextlib

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import fork_archive_routes


pytestmark = pytest.mark.microservice


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

        def close(self) -> None:
            return None

    monkeypatch.setattr(fork_archive_routes, "Queue", DummyQueue)
    monkeypatch.setattr(fork_archive_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

        def get_archive_job_id(self) -> str | None:
            return None

        def set_archive_job_id(self, *args, **kwargs) -> None:
            return None

        def clear_archive_job_id(self) -> None:
            return None

    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_fork_requires_cap_for_anonymous(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "_ensure_anonymous_access", lambda runid, wd: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fork")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["message"] == "CAPTCHA token is required."


def test_fork_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(fork_archive_routes, "_resolve_bearer_claims", lambda request: {"token_class": "user"})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(fork_archive_routes, "has_archive", lambda runid: False)
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(
        fork_archive_routes.awesome_codename,
        "generate_codename",
        lambda: "new-run",
    )

    class DummyUserDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (object(), DummyUserDatastore(), DummyApp()),
    )

    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "true"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-42"
    assert payload["new_runid"] == "new-run"
    assert payload["undisturbify"] is True


def test_fork_failure_returns_stacktrace(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(fork_archive_routes, "has_archive", lambda runid: False)
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(
        fork_archive_routes.awesome_codename,
        "generate_codename",
        lambda: "new-run",
    )

    def _raise_prep(_wd: str):
        raise RuntimeError("prep failed")

    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", _raise_prep)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fork", data={"undisturbify": "true"})

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error forking project"
    details = payload["error"].get("details")
    assert isinstance(details, str)
    assert "RuntimeError: prep failed" in details


def test_archive_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})

    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            headers={"Authorization": "Bearer token"},
            json={"comment": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-99"
