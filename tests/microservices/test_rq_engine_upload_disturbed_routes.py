from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_disturbed_routes


pytestmark = pytest.mark.microservice


def test_upload_sbs_returns_disturbed_fn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    baer_dir = run_dir / "baer"
    baer_dir.mkdir(parents=True)

    monkeypatch.setattr(upload_disturbed_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(upload_disturbed_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(upload_disturbed_routes, "get_wd", lambda runid: str(run_dir))

    class DummyRon:
        mods: set[str] = set()

    monkeypatch.setattr(upload_disturbed_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(upload_disturbed_routes, "secure_filename", lambda name: name)
    from wepppy.nodb.mods.baer import sbs_map as sbs_map_module

    monkeypatch.setattr(sbs_map_module, "sbs_map_sanity_check", lambda path: (0, ""))

    class DummyDisturbed:
        def __init__(self, base_dir: Path) -> None:
            self.baer_dir = str(base_dir)
            self.disturbed_fn = "disturbed.txt"

        def validate(self, filename: str, mode: int = 0) -> None:
            return None

    dummy_disturbed = DummyDisturbed(baer_dir)
    monkeypatch.setattr(upload_disturbed_routes.Disturbed, "getInstance", lambda wd: dummy_disturbed)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-sbs/",
            files={"input_upload_sbs": ("sbs.tif", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["disturbed_fn"] == "disturbed.txt"


def test_upload_cover_transform_returns_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(upload_disturbed_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(upload_disturbed_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(upload_disturbed_routes, "get_wd", lambda runid: str(run_dir))

    class DummyReveg:
        def validate_user_defined_cover_transform(self, name: str) -> dict[str, str]:
            return {"cover": name}

    import wepppy.nodb.mods.revegetation as revegetation_module

    monkeypatch.setattr(
        revegetation_module,
        "Revegetation",
        type("Revegetation", (), {"getInstance": lambda wd: DummyReveg()}),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/tasks/upload-cover-transform",
            files={"input_upload_cover_transform": ("cover.csv", b"data")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["cover"] == "cover.csv"
