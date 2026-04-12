from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_huc_fire_routes


pytestmark = pytest.mark.microservice


def _post_upload_sbs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    apply_nodir: bool,
    global_nodir_default: str | None = None,
    upload_filename: str = "sbs.tif",
    upload_bytes: bytes = b"data",
    validate_error: Exception | None = None,
    include_upload: bool = True,
) -> tuple[Any, Path]:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)

    if global_nodir_default is None:
        monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    else:
        monkeypatch.setenv("WEPP_NODIR_DEFAULT_NEW_RUNS", global_nodir_default)

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
            self.wd = wd
            self.cfg = cfg

        def config_get_bool(self, section: str, option: str, default: bool | None = None) -> bool:
            if section == "nodb" and option == "apply_nodir":
                return apply_nodir
            return False if default is None else bool(default)

    monkeypatch.setattr(upload_huc_fire_routes, "Ron", DummyRon)

    class DummyDisturbed:
        def __init__(self, base_dir: Path) -> None:
            self.disturbed_dir = str(base_dir)

        def validate(self, filename: str, mode: int = 0) -> None:
            if validate_error is not None:
                raise validate_error
            return None

    dummy_disturbed = DummyDisturbed(disturbed_dir)
    monkeypatch.setattr(upload_huc_fire_routes.Disturbed, "getInstance", lambda wd: dummy_disturbed)

    files = {"input_upload_sbs": (upload_filename, upload_bytes)} if include_upload else None

    with TestClient(rq_engine.app) as client:
        if files is None:
            response = client.post(
                "/api/huc-fire/tasks/upload-sbs/",
                headers={"Authorization": "Bearer token"},
            )
        else:
            response = client.post(
                "/api/huc-fire/tasks/upload-sbs/",
                files=files,
                headers={"Authorization": "Bearer token"},
            )

    return response, run_dir


def test_huc_fire_upload_sbs_creates_run_without_nodir_marker_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, run_dir = _post_upload_sbs(monkeypatch, tmp_path, apply_nodir=False)

    assert response.status_code == 200
    payload = response.json()
    assert payload["runid"] == "new-run"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_huc_fire_upload_sbs_does_not_create_nodir_marker_when_config_opted_in(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, run_dir = _post_upload_sbs(monkeypatch, tmp_path, apply_nodir=True)

    assert response.status_code == 200
    payload = response.json()
    assert payload["runid"] == "new-run"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_huc_fire_upload_sbs_opt_in_respects_global_nodir_env_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=True,
        global_nodir_default="0",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runid"] == "new-run"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_huc_fire_upload_sbs_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        upload_filename="bad.exe",
        upload_bytes=b"data",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"].startswith("Invalid file extension.")


def test_huc_fire_upload_sbs_rejects_oversize_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(upload_huc_fire_routes, "UPLOAD_HUC_FIRE_SBS_MAX_BYTES", 4)

    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        upload_filename="sbs.tif",
        upload_bytes=b"abcdef",
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_huc_fire_upload_sbs_validation_errors_include_specific_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        upload_filename="sbs.tif",
        upload_bytes=b"data",
        validate_error=RuntimeError("boom"),
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "SBS validation failed: boom"
    assert payload["error"]["details"] == "SBS validation failed: boom"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


def test_huc_fire_upload_sbs_requires_file_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        include_upload=False,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "input_upload_sbs must be provided"
    assert payload["error"]["details"] == "input_upload_sbs must be provided"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]
