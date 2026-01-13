import contextlib
from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_huc_fire_routes


pytestmark = pytest.mark.microservice


def test_huc_fire_upload_sbs_creates_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)

    monkeypatch.setattr(
        upload_huc_fire_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "user"},
    )

    class DummyUser:
        email = "tester@example.com"

    class DummyDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    monkeypatch.setattr(
        upload_huc_fire_routes,
        "_resolve_user_from_claims",
        lambda claims: (DummyUser(), DummyDatastore(), DummyApp()),
    )

    import importlib

    run_0_bp_module = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")
    monkeypatch.setattr(run_0_bp_module, "create_run_dir", lambda user: ("new-run", str(run_dir)))

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            return None

    monkeypatch.setattr(upload_huc_fire_routes, "Ron", DummyRon)

    class DummyDisturbed:
        def __init__(self, base_dir: Path) -> None:
            self.disturbed_dir = str(base_dir)

        def validate(self, filename: str, mode: int = 0) -> None:
            return None

    dummy_disturbed = DummyDisturbed(disturbed_dir)
    monkeypatch.setattr(upload_huc_fire_routes.Disturbed, "getInstance", lambda wd: dummy_disturbed)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/huc-fire/tasks/upload-sbs/",
            files={"input_upload_sbs": ("sbs.tif", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runid"] == "new-run"
