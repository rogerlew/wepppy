from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import upload_huc_fire_routes
from wepppy.weppcloud.user_preferences import (
    CreationActor,
    RunRegistrationReceipt,
)


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
    expected_cfg_parts: tuple[str, ...] = (),
    absent_cfg_parts: tuple[str, ...] = (),
    token_class: str = "user",
    preference_error: Exception | None = None,
    create_run_error: Exception | None = None,
    delete_error: Exception | None = None,
    cleanup_error: Exception | None = None,
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
        lambda request, required_scopes=None: {"token_class": token_class},
    )

    snapshot = (
        CreationActor(
            user_id=42,
            email="tester@example.com",
        )
        if token_class == "user"
        else None
    )
    if preference_error is None:
        monkeypatch.setattr(
            upload_huc_fire_routes,
            "resolve_creation_actor",
            lambda claims: snapshot,
        )
    else:
        monkeypatch.setattr(
            upload_huc_fire_routes,
            "resolve_creation_actor",
            lambda claims: (_ for _ in ()).throw(preference_error),
        )
    receipt = RunRegistrationReceipt(7, "new-run", "disturbed9002", 42)
    monkeypatch.setattr(
        upload_huc_fire_routes,
        "register_owned_run",
        lambda *args: (
            receipt
            if token_class == "user"
            else (_ for _ in ()).throw(
                AssertionError("service/MCP creation must remain ownerless")
            )
        ),
    )
    monkeypatch.setattr(
        upload_huc_fire_routes,
        "delete_registered_run",
        lambda *args: (
            (_ for _ in ()).throw(delete_error)
            if delete_error is not None
            else None
        ),
    )
    monkeypatch.setattr(
        upload_huc_fire_routes,
        "cleanup_new_run_directory",
        lambda *args: (
            (_ for _ in ()).throw(cleanup_error)
            if cleanup_error is not None
            else None
        ),
    )

    import importlib

    run_0_bp_module = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")
    monkeypatch.setattr(
        run_0_bp_module,
        "create_run_dir",
        lambda user: (
            (_ for _ in ()).throw(create_run_error)
            if create_run_error is not None
            else ("new-run", str(run_dir))
        ),
    )

    captured: dict[str, str] = {}

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            self.wd = wd
            self.cfg = cfg
            captured["cfg"] = cfg

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

    for expected_part in expected_cfg_parts:
        assert expected_part in captured["cfg"]
    for absent_part in absent_cfg_parts:
        assert absent_part not in captured["cfg"]
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


def test_huc_fire_does_not_apply_account_preferences_to_durable_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        absent_cfg_parts=(
            "unitizer:is_english",
            "watershed.wbt:boundary_touch_behavior",
        ),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("token_class", ("service", "mcp"))
def test_huc_fire_service_and_mcp_creation_remain_config_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    token_class: str,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        token_class=token_class,
    )

    assert response.status_code == 200
    assert response.json()["runid"] == "new-run"


def test_huc_fire_rejects_session_token_before_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        token_class="session",
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == (
        "Session token not allowed for this endpoint"
    )


def test_huc_fire_unknown_actor_fails_before_run_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        preference_error=upload_huc_fire_routes.PreferenceIdentityError(
            "unknown /private/db user"
        ),
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "run_ownership_failed"
    assert payload["error_id"]
    assert "/private/db" not in response.text


def test_huc_fire_unexpected_failure_does_not_disclose_path_or_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    response, _run_dir = _post_upload_sbs(
        monkeypatch,
        tmp_path,
        apply_nodir=False,
        create_run_error=RuntimeError(
            "Traceback at /private/weppcloud/secret.py"
        ),
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Could not save file."
    assert payload["error_id"]
    assert "Traceback" not in response.text
    assert "/private/weppcloud" not in response.text


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


def test_huc_fire_upload_sbs_validation_errors_are_sanitized(
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
    assert payload["error"]["message"] == "SBS validation failed."
    assert payload["error"]["details"] == (
        "The uploaded SBS raster did not pass validation."
    )
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]
    assert "boom" not in response.text


@pytest.mark.parametrize(
    ("delete_error", "cleanup_error", "expected_messages"),
    (
        (
            SQLAlchemyError("sql cleanup failed"),
            None,
            {"rq-engine huc-fire SQL cleanup failed"},
        ),
        (
            None,
            OSError("filesystem cleanup failed"),
            {"rq-engine huc-fire directory cleanup failed"},
        ),
        (
            SQLAlchemyError("sql cleanup failed"),
            OSError("filesystem cleanup failed"),
            {
                "rq-engine huc-fire SQL cleanup failed",
                "rq-engine huc-fire directory cleanup failed",
            },
        ),
    ),
)
def test_huc_fire_cleanup_logs_use_response_error_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    delete_error: Exception | None,
    cleanup_error: Exception | None,
    expected_messages: set[str],
) -> None:
    with caplog.at_level("ERROR", logger=upload_huc_fire_routes.__name__):
        response, _run_dir = _post_upload_sbs(
            monkeypatch,
            tmp_path,
            apply_nodir=False,
            validate_error=RuntimeError("validation failed"),
            delete_error=delete_error,
            cleanup_error=cleanup_error,
        )

    error_id = response.json()["error_id"]
    cleanup_records = [
        record
        for record in caplog.records
        if record.getMessage() in expected_messages
    ]
    assert {record.getMessage() for record in cleanup_records} == expected_messages
    assert all(record.error_id == error_id for record in cleanup_records)
    assert all(record.runid == "new-run" for record in cleanup_records)


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
