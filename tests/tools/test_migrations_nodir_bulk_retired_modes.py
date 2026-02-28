from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.tools.migrations import nodir_bulk

pytestmark = pytest.mark.unit


def _last_audit_event(audit_log: Path) -> dict[str, object]:
    lines = [line for line in audit_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert isinstance(payload, dict)
    return payload


def test_archive_mode_reports_retired_error_instead_of_false_archived_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "landuse").mkdir()
    audit_log = tmp_path / "audit.jsonl"

    monkeypatch.setattr(nodir_bulk, "_active_run_lock_keys", lambda _runid: [])

    counters = nodir_bulk._process_run(
        wd=wd,
        roots=("landuse",),
        mode="archive",
        remove_archive_on_restore=False,
        dry_run=False,
        resume_pairs=set(),
        resume_enabled=False,
        audit_log=audit_log,
        verbose=False,
    )

    event = _last_audit_event(audit_log)
    assert event["status"] == "nodir_error"
    assert event["code"] == "NODIR_ARCHIVE_RETIRED"
    assert counters["failed"] == 1
    assert counters["completed"] == 0


def test_restore_mode_archive_only_root_surfaces_retired_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "landuse.nodir").write_bytes(b"archive")
    audit_log = tmp_path / "audit.jsonl"

    monkeypatch.setattr(nodir_bulk, "_active_run_lock_keys", lambda _runid: [])

    counters = nodir_bulk._process_run(
        wd=wd,
        roots=("landuse",),
        mode="restore",
        remove_archive_on_restore=False,
        dry_run=False,
        resume_pairs=set(),
        resume_enabled=False,
        audit_log=audit_log,
        verbose=False,
    )

    event = _last_audit_event(audit_log)
    assert event["status"] == "nodir_error"
    assert event["code"] == "NODIR_ARCHIVE_RETIRED"
    assert counters["failed"] == 1
    assert counters["completed"] == 0
