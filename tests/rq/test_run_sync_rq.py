from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

import pytest

import wepppy.rq.run_sync_rq as run_sync

pytestmark = pytest.mark.unit


def test_run_sync_rq_records_provenance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(run_sync.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))

    job = SimpleNamespace(id="job-42", meta={})

    def _save() -> None:
        job.meta["_saved"] = True

    job.save = _save  # type: ignore[attr-defined]
    monkeypatch.setattr(run_sync, "get_current_job", lambda: job)
    monkeypatch.setattr(run_sync, "lock_statuses", lambda runid: {})

    spec_file = tmp_path / "spec.aria2"
    monkeypatch.setattr(
        run_sync,
        "_download_spec",
        lambda url, headers: spec_file.write_text("url", encoding="utf-8") or spec_file,
    )

    def fake_aria2(input_file: Path, target_dir: Path, headers: dict[str, str] | None) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    monkeypatch.setattr(run_sync, "_run_aria2c", fake_aria2)
    monkeypatch.setattr(run_sync, "_verify_download", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_sync, "read_version", lambda path: 999)

    upserts: list[tuple] = []
    monkeypatch.setattr(
        run_sync,
        "_upsert_migration_row",
        lambda *args, **kwargs: upserts.append((args, kwargs)),
    )

    target_root = tmp_path / "runs"
    result = run_sync.run_sync_rq(
        "demo-run",
        "wepp.cloud",
        "owner@example.com",
        str(target_root),
        None,
    )

    run_root = target_root / "demo-run" / "cfg"
    provenance_path = run_root / ".provenance.json"
    assert provenance_path.exists()

    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert payload["runid"] == "demo-run"
    assert payload["config"] == "cfg"
    assert payload["source_host"] == "wepp.cloud"
    assert payload["owner_email"] == "owner@example.com"
    assert payload["version_at_pull"] == 999

    assert job.meta["runid"] == "demo-run"
    assert any("DOWNLOADING" in message for _, message in published)
    assert any("REGISTERED" in message for _, message in published)
    assert result["local_path"] == str(run_root)
    statuses = [args[7] for args, _ in upserts]
    assert "DOWNLOADING" in statuses
    assert "REGISTERED" in statuses
