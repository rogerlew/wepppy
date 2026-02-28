from __future__ import annotations

import errno
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


class _PrepStub:
    def __init__(self) -> None:
        self.cleared = 0

    def clear_archive_job_id(self) -> None:
        self.cleared += 1


@pytest.fixture()
def archive_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import wepppy.rq.project_rq as project

    published: list[tuple[str, str]] = []
    prep_by_run: dict[str, _PrepStub] = {}

    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-archive"))
    monkeypatch.setattr(project, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(project.RedisPrep, "getInstanceFromRunID", lambda runid: prep_by_run.setdefault(runid, _PrepStub()))
    monkeypatch.setattr(project, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(project, "clear_nodb_file_cache", lambda runid: [])
    monkeypatch.setattr(
        project.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=2_000_000_000, used=100_000_000, free=1_900_000_000),
    )

    return project, tmp_path, published, prep_by_run


def test_archive_rq_fails_fast_when_nodb_files_are_locked(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)
    (run_dir / "input.txt").write_text("input", encoding="utf-8")

    monkeypatch.setattr(project, "lock_statuses", lambda runid: {"watershed.nodb": True})

    with pytest.raises(RuntimeError, match="Cannot archive while files are locked"):
        project.archive_rq("demo", comment="snapshot")

    assert prep_by_run["demo"].cleared == 1


def test_archive_rq_checks_disk_headroom_before_writing_archive(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)
    (run_dir / "input.bin").write_bytes(b"x" * 1024)

    monkeypatch.setattr(
        project.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=1024, used=1024, free=0),
    )

    with pytest.raises(OSError) as exc_info:
        project.archive_rq("demo", comment="snapshot")

    assert exc_info.value.errno == errno.ENOSPC
    assert prep_by_run["demo"].cleared == 1
    assert not (run_dir / "archives").exists()


def test_archive_rq_preserves_nodir_cache_entries(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)

    (run_dir / "input.txt").write_text("input", encoding="utf-8")
    (run_dir / ".nodir" / "cache" / "watershed" / "123").mkdir(parents=True)
    (run_dir / ".nodir" / "cache" / "watershed" / "123" / "entry.bin").write_bytes(b"cache")
    (run_dir / ".nodir" / "projections").mkdir(parents=True)
    (run_dir / ".nodir" / "projections" / "read.json").write_text("{}", encoding="utf-8")

    project.archive_rq("demo", comment="snapshot")

    archive_paths = sorted((run_dir / "archives").glob("*.zip"))
    assert len(archive_paths) == 1

    with zipfile.ZipFile(archive_paths[0], mode="r") as zf:
        names = set(zf.namelist())

    assert "input.txt" in names
    assert ".nodir/projections/read.json" in names
    assert ".nodir/cache/watershed/123/entry.bin" in names
    assert prep_by_run["demo"].cleared == 1


def test_calculate_run_payload_bytes_includes_nodir_cache(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)

    (run_dir / "included.txt").write_bytes(b"abc")
    (run_dir / ".nodir" / "cache" / "watershed" / "123").mkdir(parents=True)
    (run_dir / ".nodir" / "cache" / "watershed" / "123" / "ignored.bin").write_bytes(b"x" * 100)

    total_bytes, file_count = project._calculate_run_payload_bytes(run_dir)
    assert total_bytes == 103
    assert file_count == 2


def test_restore_archive_rq_validates_zip_integrity_before_removing_existing_files(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)

    current_file = run_dir / "current.txt"
    current_file.write_text("keep-me", encoding="utf-8")

    archive_path = archives_dir / "demo.20260218T000000Z.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")

    monkeypatch.setattr(project.zipfile.ZipFile, "testzip", lambda self: "restored.txt")

    with pytest.raises(zipfile.BadZipFile, match="Archive integrity check failed"):
        project.restore_archive_rq("demo", archive_path.name)

    assert current_file.exists()
    assert current_file.read_text(encoding="utf-8") == "keep-me"
    assert prep_by_run["demo"].cleared == 1


def test_restore_archive_rq_restores_nodir_cache_entries(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)

    archive_path = archives_dir / "demo.20260218T000000Z.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")
        zf.writestr(".nodir/cache/watershed/123/entry.bin", "cache")

    project.restore_archive_rq("demo", archive_path.name)

    assert (run_dir / "restored.txt").read_text(encoding="utf-8") == "value"
    assert (run_dir / ".nodir" / "cache" / "watershed" / "123" / "entry.bin").read_text(encoding="utf-8") == "cache"
    assert prep_by_run["demo"].cleared == 1


def test_restore_archive_rq_checks_disk_headroom_before_removing_existing_files(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)

    current_file = run_dir / "current.txt"
    current_file.write_text("keep-me", encoding="utf-8")

    archive_path = archives_dir / "demo.20260218T000000Z.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")

    monkeypatch.setattr(
        project.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=1024, used=1024, free=0),
    )

    with pytest.raises(OSError) as exc_info:
        project.restore_archive_rq("demo", archive_path.name)

    assert exc_info.value.errno == errno.ENOSPC
    assert current_file.exists()
    assert current_file.read_text(encoding="utf-8") == "keep-me"
    assert prep_by_run["demo"].cleared == 1


def test_restore_archive_rq_fails_when_nodb_cache_clear_fails(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)

    (run_dir / "old.txt").write_text("old", encoding="utf-8")

    archive_path = archives_dir / "demo.20260218T000000Z.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("new.txt", "new")

    monkeypatch.setattr(project, "clear_nodb_file_cache", lambda runid: (_ for _ in ()).throw(RuntimeError("cache clear failed")))

    with pytest.raises(RuntimeError, match="cache clear failed"):
        project.restore_archive_rq("demo", archive_path.name)

    assert (run_dir / "new.txt").exists()
    assert prep_by_run["demo"].cleared == 1
    assert any("Failed to clear NoDb cache after restore" in message for _, message in published)
