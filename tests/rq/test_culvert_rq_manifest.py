from __future__ import annotations

import json
from pathlib import Path

import pytest

import wepppy.rq.culvert_rq_manifest as manifest

pytestmark = pytest.mark.unit


class _DummyRedisConn:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _DummyRunner:
    payload_metadata = None
    DEFAULT_WATERSHEDS_REL_PATH = "culverts/watersheds.geojson"


def test_format_manifest_error_formats_mapping_and_fallback_values() -> None:
    assert (
        manifest._format_manifest_error({"type": "BoomError", "message": "bad input"})
        == "BoomError: bad input"
    )
    assert manifest._format_manifest_error({"type": "BoomError"}) == "BoomError"
    assert manifest._format_manifest_error("plain text") == "plain text"
    assert manifest._format_manifest_error(None) is None


def test_write_runs_manifest_includes_summary_and_run_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_root = tmp_path / "batch"
    run_wd = batch_root / "runs" / "1"
    run_wd.mkdir(parents=True)
    (run_wd / "run_metadata.json").write_text(
        json.dumps(
            {
                "runid": "culvert;;batch-1;;1",
                "point_id": "1",
                "status": "failed",
                "error": {"type": "RuntimeError", "message": "landuse fail"},
            }
        ),
        encoding="utf-8",
    )

    redis_conn = _DummyRedisConn()
    monkeypatch.setattr(manifest, "_get_rq_connection", lambda: redis_conn)
    monkeypatch.setattr(
        manifest,
        "_fetch_job_info",
        lambda _job_id, *, redis_conn: ("finished", "2026-02-20T01:00:00+00:00"),
    )

    runs = {
        "1": {
            "wd": str(run_wd),
            "job_id": "job-1",
            "validation_metrics": {
                "culvert_easting": 10.0,
                "culvert_northing": 20.0,
                "bounds_area_m2": 30.0,
            },
        }
    }
    summary = {"total": 1, "succeeded": 0, "failed": 1, "skipped_no_outlet": 0}

    manifest_path = manifest._write_runs_manifest(
        batch_root=batch_root,
        culvert_batch_uuid="batch-1",
        runs=runs,
        runner=_DummyRunner(),
        summary=summary,
    )

    assert manifest_path == batch_root / "runs_manifest.md"
    text = manifest_path.read_text(encoding="utf-8")
    assert "# Runs Manifest" in text
    assert "- total: 1" in text
    assert "culvert;;batch-1;;1" in text
    assert "finished" in text
    assert "RuntimeError: landuse fail" in text
    assert redis_conn.closed


@pytest.mark.parametrize("aware", [False, True])
def test_job_manifest_keeps_status_and_creation_wire_values(monkeypatch, aware):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from rq.job import JobStatus

    created = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc if aware else None)
    monkeypatch.setattr(manifest.Job, "fetch", lambda *args, **kwargs: SimpleNamespace(
        get_status=lambda: JobStatus.STARTED, created_at=created
    ))
    assert manifest._fetch_job_info("owned-job", redis_conn=object()) == (
        "started", "2026-10-27T12:00:00"
    )
