from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
from pathlib import Path

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter import create_app
from wepppy.microservices.shape_converter.cleanup import (
    ActiveRequestScratchRegistry,
    cleanup_request_scratch_dir,
    create_request_scratch_dir,
    sweep_stale_request_dirs,
)

pytestmark = [pytest.mark.unit, pytest.mark.microservice]
shape_converter_app_module = importlib.import_module("wepppy.microservices.shape_converter.app")


def _scratch_children(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.iterdir())


def test_cleanup_request_scope_removes_request_artifacts_and_logs_without_payload_leak(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = ActiveRequestScratchRegistry()
    logger = logging.getLogger("tests.shape_converter.cleanup")
    caplog.set_level(logging.INFO, logger=logger.name)
    uploaded_content_marker = "alice-private-metadata"

    layout = create_request_scratch_dir(
        scratch_root=tmp_path,
        request_id="a" * 32,
        request_scope="inspect",
        registry=registry,
        logger=logger,
    )
    layout.extraction_root.mkdir(parents=True, exist_ok=True)
    layout.output_root.mkdir(parents=True, exist_ok=True)
    layout.upload_archive_path.write_text(uploaded_content_marker, encoding="utf-8")
    (layout.extraction_root / "roads.shp").write_text("shape-bytes", encoding="utf-8")
    (layout.output_root / "roads.geojson").write_text('{"type":"FeatureCollection"}', encoding="utf-8")

    cleaned = cleanup_request_scratch_dir(
        layout=layout,
        request_id="a" * 32,
        request_scope="inspect",
        cleanup_reason="success",
        registry=registry,
        logger=logger,
    )

    assert cleaned is True
    assert not layout.request_dir.exists()
    assert registry.snapshot() == frozenset()

    parsed_messages = [json.loads(record.message) for record in caplog.records if record.name == logger.name]
    assert any(message["event"] == "request_scratch_created" for message in parsed_messages)
    assert any(message["event"] == "request_scratch_cleaned" for message in parsed_messages)
    assert all(uploaded_content_marker not in record.message for record in caplog.records)


def test_janitor_removes_only_stale_owned_request_dirs(tmp_path: Path) -> None:
    registry = ActiveRequestScratchRegistry()
    logger = logging.getLogger("tests.shape_converter.janitor")

    stale_dir = tmp_path / "inspect-deadbeef-stale1"
    active_dir = tmp_path / "convert-deadbeef-active1"
    fresh_dir = tmp_path / "inspect-deadbeef-fresh1"
    foreign_dir = tmp_path / "keep-me"
    stale_dir.mkdir(parents=True)
    active_dir.mkdir(parents=True)
    fresh_dir.mkdir(parents=True)
    foreign_dir.mkdir(parents=True)

    active_dir_resolved = active_dir.resolve()
    registry.register(active_dir_resolved)

    now_epoch = 1_000_000.0
    os.utime(stale_dir, (now_epoch - 3_600, now_epoch - 3_600))
    os.utime(active_dir, (now_epoch - 3_600, now_epoch - 3_600))
    os.utime(fresh_dir, (now_epoch - 60, now_epoch - 60))

    result = sweep_stale_request_dirs(
        scratch_root=tmp_path,
        stale_after_seconds=300,
        registry=registry,
        logger=logger,
        now_epoch_seconds=now_epoch,
    )

    assert result.scanned == 3
    assert result.removed == 1
    assert result.skipped_active == 1
    assert result.skipped_fresh == 1
    assert result.skipped_non_owned >= 1
    assert result.failed == 0
    assert not stale_dir.exists()
    assert active_dir.exists()
    assert fresh_dir.exists()
    assert foreign_dir.exists()


def test_inspect_success_path_cleans_scratch(tmp_path: Path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="inspect-success"))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/inspect",
            files={"archive": ("inspect-success.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 200
    assert _scratch_children(tmp_path) == []


def test_convert_failure_path_cleans_scratch(tmp_path: Path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="convert-failure", include_prj=False))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("convert-failure.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_source_crs"
    assert _scratch_children(tmp_path) == []


def test_convert_success_path_cleans_scratch(tmp_path: Path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="convert-success"))

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("convert-success.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 200
    assert _scratch_children(tmp_path) == []


def test_convert_success_path_cleanup_failure_emits_error_signal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="convert-success-log-signal"))
    original_cleanup = shape_converter_app_module.cleanup_request_scratch_dir

    def _cleanup_reports_failure(**kwargs):  # noqa: ANN003
        original_cleanup(**kwargs)
        return False

    monkeypatch.setattr(shape_converter_app_module, "cleanup_request_scratch_dir", _cleanup_reports_failure)
    caplog.set_level(logging.ERROR, logger="wepppy.microservices.shape_converter.app")

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("convert-success-log-signal.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 200
    assert any(
        "request_scratch_cleanup_failed_after_success_response" in record.message
        for record in caplog.records
    )


def test_inspect_timeout_path_cleans_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="timeout"))

    async def _slow_inspect(*, archive, scratch, request_id):  # noqa: ANN001
        scratch.extraction_root.mkdir(parents=True, exist_ok=True)
        (scratch.extraction_root / "partial.txt").write_text("partial", encoding="utf-8")
        await asyncio.sleep(0.02)
        return {"request_id": request_id}

    monkeypatch.setattr(shape_converter_app_module, "_INSPECT_TIMEOUT_SECONDS", 0)
    monkeypatch.setattr(shape_converter_app_module, "inspect_uploaded_archive", _slow_inspect)

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/inspect",
            files={"archive": ("timeout.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 408
    assert response.json()["error"]["code"] == "request_timeout"
    assert _scratch_children(tmp_path) == []


def test_inspect_cancelled_path_cleans_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="cancel"))
    observed_cleanup_reasons: list[str] = []
    original_cleanup = shape_converter_app_module.cleanup_request_scratch_dir

    async def _cancelled_inspect(*, archive, scratch, request_id):  # noqa: ANN001
        scratch.extraction_root.mkdir(parents=True, exist_ok=True)
        (scratch.extraction_root / "partial.txt").write_text("partial", encoding="utf-8")
        raise asyncio.CancelledError()

    def _cleanup_spy(**kwargs):  # noqa: ANN003
        observed_cleanup_reasons.append(str(kwargs["cleanup_reason"]))
        return original_cleanup(**kwargs)

    monkeypatch.setattr(shape_converter_app_module, "inspect_uploaded_archive", _cancelled_inspect)
    monkeypatch.setattr(shape_converter_app_module, "cleanup_request_scratch_dir", _cleanup_spy)

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/inspect",
            files={"archive": ("cancel.zip", archive_bytes, "application/zip")},
        )

    assert response.status_code == 500
    assert "cancelled" in observed_cleanup_reasons
    assert _scratch_children(tmp_path) == []


def test_convert_disconnect_like_form_failure_still_cleans_scratch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    archive_bytes = build_zip_bytes(build_minimal_point_dataset(prefix="disconnect"))

    async def _disconnect_form(self):  # noqa: ANN001
        raise RuntimeError("Client disconnected during body read.")

    monkeypatch.setattr("starlette.requests.Request.form", _disconnect_form)

    with TestClient(create_app()) as client:
        client.app.state.scratch_root = tmp_path
        response = client.post(
            "/v1/convert",
            files={"archive": ("disconnect.zip", archive_bytes, "application/zip")},
            data={"output_format": "geojson", "target_crs": "wgs84"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_archive"
    assert _scratch_children(tmp_path) == []
