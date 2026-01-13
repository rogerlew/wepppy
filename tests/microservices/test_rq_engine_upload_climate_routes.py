from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_climate_routes


pytestmark = pytest.mark.microservice


def test_upload_cli_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    cli_dir = run_dir / "cli"
    cli_dir.mkdir(parents=True)

    monkeypatch.setattr(upload_climate_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(upload_climate_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(upload_climate_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(upload_climate_routes.Ron, "getInstance", lambda wd: object())

    class DummyClimate:
        def __init__(self, cli_dir: Path) -> None:
            self.cli_dir = str(cli_dir)
            self.saved: str | None = None

        def set_user_defined_cli(self, name: str) -> None:
            self.saved = name

    climate = DummyClimate(cli_dir)
    monkeypatch.setattr(upload_climate_routes.Climate, "getInstance", lambda wd: climate)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cli/",
            files={"input_upload_cli": ("demo.cli", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    assert climate.saved == "demo.cli"
