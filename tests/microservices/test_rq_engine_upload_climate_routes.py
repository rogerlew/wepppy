from pathlib import Path
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_climate_routes
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upload_climate_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(upload_climate_routes, "authorize_run_access", lambda claims, runid: None)


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

    monkeypatch.setattr(upload_climate_routes, "Queue", DummyQueue)
    monkeypatch.setattr(upload_climate_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(upload_climate_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_upload_cli_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda wd, root, callback, purpose="nodir-mutation": callback(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"


def test_upload_cli_propagates_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)

    def _raise_nodir(wd, root, callback, purpose="nodir-mutation"):
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(upload_climate_routes, "mutate_root", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"


def test_upload_cli_rejects_archive_form_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())
    monkeypatch.setattr(
        upload_climate_routes,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)
    monkeypatch.setattr(
        upload_climate_routes,
        "mutate_root",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("mutate_root should not run")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_ARCHIVE_ACTIVE"
