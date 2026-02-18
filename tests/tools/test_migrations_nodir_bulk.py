from __future__ import annotations

import json
import threading
import zipfile
from pathlib import Path

import pytest

from wepppy.tools.migrations import nodir_bulk

pytestmark = pytest.mark.unit


class _RedisLockStub:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):  # noqa: ARG002
        with self._lock:
            if nx and key in self._store:
                return False
            self._store[key] = value
            return True

    def get(self, key: str):
        with self._lock:
            return self._store.get(key)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)
            return 1

    def eval(self, script: str, numkeys: int, key: str, *args):  # noqa: ARG002
        expected = str(args[0]) if args else ""
        with self._lock:
            current = self._store.get(key)
            if "redis.call('del', KEYS[1])" in script:
                if current == expected:
                    self._store.pop(key, None)
                    return 1
                return 0
        raise AssertionError(f"unexpected eval script: {script}")


def _write_zip(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)


def _read_audit(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _make_run(scan_root: Path, runid: str) -> Path:
    wd = scan_root / runid[:2] / runid
    wd.mkdir(parents=True, exist_ok=False)
    (wd / "ron.nodb").write_text("{}", encoding="utf-8")
    return wd


@pytest.fixture(autouse=True)
def _patch_nodir_locks(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    monkeypatch.setattr(nodir_bulk, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(thaw_freeze_mod, "redis_lock_client", _RedisLockStub())


def test_crawl_runs_dry_run_supports_filters_limit_and_root(tmp_path: Path) -> None:
    scan_root = tmp_path / "runs"
    run_a = _make_run(scan_root, "aa-run")
    run_b = _make_run(scan_root, "bb-run")

    (run_a / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (run_a / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    (run_b / "soils").mkdir(parents=True, exist_ok=True)
    (run_b / "soils" / "soils.map").write_text("beta", encoding="utf-8")

    audit_log = tmp_path / "audit.jsonl"
    summary = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        runids=[],
        limit=1,
        dry_run=True,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert summary["runs"] == 1
    assert summary["processed"] == 1
    records = _read_audit(audit_log)
    assert len(records) == 1
    assert records[0]["runid"] == "aa-run"
    assert records[0]["root"] == "watershed"
    assert records[0]["status"] == "would_archive"


def test_crawl_runs_archives_root_and_resume_skips_completed(tmp_path: Path) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    audit_log = tmp_path / "audit.jsonl"
    first = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert first["failed"] == 0
    assert not (wd / "watershed").exists()
    assert (wd / "watershed.nodir").exists()
    first_records = _read_audit(audit_log)
    assert first_records[-1]["status"] == "archived"

    second = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert second["resumed"] == 1
    second_records = _read_audit(audit_log)
    assert second_records[-1]["status"] == "resume_skipped"


def test_crawl_runs_requires_readonly_before_mutation(tmp_path: Path) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    audit_log = tmp_path / "audit.jsonl"
    summary = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert summary["failed"] == 1
    assert (wd / "watershed").exists()
    assert not (wd / "watershed.nodir").exists()
    records = _read_audit(audit_log)
    assert records[-1]["status"] == "readonly_required"


def test_crawl_runs_fails_fast_when_run_has_active_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    monkeypatch.setattr(nodir_bulk, "lock_statuses", lambda runid: {"ron.nodb": True})

    audit_log = tmp_path / "audit.jsonl"
    summary = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert summary["failed"] == 1
    records = _read_audit(audit_log)
    assert records[-1]["status"] == "active_run_locked"
    assert records[-1]["active_locks"] == ["ron.nodb"]
    assert records[-1]["duration_ms"] == 0


def test_crawl_runs_propagates_canonical_nodir_error_status(tmp_path: Path) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")
    _write_zip(wd / "watershed.nodir", {"hillslopes/h001.slp": "zip"})

    audit_log = tmp_path / "audit.jsonl"
    summary = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert summary["failed"] == 1
    records = _read_audit(audit_log)
    assert records[-1]["status"] == "nodir_error"
    assert records[-1]["code"] == "NODIR_MIXED_STATE"


def test_crawl_runs_no_resume_reprocesses_completed_pairs(tmp_path: Path) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    audit_log = tmp_path / "audit.jsonl"
    first = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )
    assert first["failed"] == 0

    second = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=False,
        verbose=False,
    )

    assert second["failed"] == 0
    assert second["resumed"] == 0
    records = _read_audit(audit_log)
    assert records[-1]["status"] == "already_archive"
    assert records[-1]["duration_ms"] >= 0


def test_crawl_runs_reports_root_lock_failed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_root = tmp_path / "runs"
    wd = _make_run(scan_root, "aa-run")
    (wd / "READONLY").write_text("", encoding="utf-8")
    (wd / "watershed" / "hillslopes").mkdir(parents=True, exist_ok=True)
    (wd / "watershed" / "hillslopes" / "h001.slp").write_text("alpha", encoding="utf-8")

    from wepppy.nodir.errors import nodir_locked

    class _FailLock:
        def __enter__(self):
            raise nodir_locked("root lock busy")

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
            return False

    monkeypatch.setattr(
        nodir_bulk,
        "maintenance_lock",
        lambda wd, root, purpose: _FailLock(),  # noqa: ARG005
    )

    audit_log = tmp_path / "audit.jsonl"
    summary = nodir_bulk.crawl_runs(
        scan_roots=[scan_root],
        roots=["watershed"],
        dry_run=False,
        audit_log=audit_log,
        resume=True,
        verbose=False,
    )

    assert summary["failed"] == 1
    records = _read_audit(audit_log)
    assert records[-1]["status"] == "root_lock_failed"
    assert records[-1]["code"] == "NODIR_LOCKED"
    assert records[-1]["http_status"] == 503
    assert records[-1]["duration_ms"] >= 0
