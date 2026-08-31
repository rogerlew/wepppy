from __future__ import annotations

import errno
from configparser import RawConfigParser
from datetime import datetime, timezone
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.project_config_reader import load_project_config
from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot, resolve_preset_snapshot
from wepppy.nodb.project_config_update import (
    JOURNAL_NAME,
    apply_project_config_update,
    preview_project_config_update,
)
from wepppy.project_config_sanitization import scan_archive
from wepppy.project_config_serialization import parse_config_text, serialize_config

pytestmark = pytest.mark.unit


class _PrepStub:
    def __init__(self) -> None:
        self.cleared = 0

    def clear_archive_job_id(self) -> None:
        self.cleared += 1


def _owned_project(root: Path) -> tuple[Path, Path, tuple[str, str]]:
    candidate = resolve_preset_snapshot(
        "disturbed9002_wbt",
        {},
        source_revision="deployment-a",
        resolved_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    materialize_preset_snapshot(root, candidate)
    config_path = root / candidate.config_filename
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    target = ("unitizer", "is_english")
    del config[target[0]][target[1]]
    config_bytes = serialize_config(config)
    config_path.write_bytes(config_bytes)
    manifest_path = root / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    import hashlib
    manifest["config"]["sha256"] = hashlib.sha256(config_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return config_path, manifest_path, target


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


def test_archive_recovers_pending_update_and_preserves_one_pair(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)
    config_path, manifest_path, target = _owned_project(run_dir)
    preview = preview_project_config_update(run_dir)

    def _stop_after_config(stage: str) -> None:
        if stage == "config_replaced":
            raise RuntimeError("simulated stop")

    with pytest.raises(RuntimeError, match="simulated stop"):
        apply_project_config_update(
            run_dir,
            preview.preview_id or "",
            trigger_section=target[0],
            trigger_option=target[1],
            application_revision="wp10-test",
            fault_hook=_stop_after_config,
        )
    assert (run_dir / JOURNAL_NAME).exists()

    project.archive_rq("demo", comment="consistent")

    assert not (run_dir / JOURNAL_NAME).exists()
    archive_path = next((run_dir / "archives").glob("*.zip"))
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
        assert zf.read(config_path.name) == config_path.read_bytes()
        assert zf.read(manifest_path.name) == manifest_path.read_bytes()
    assert JOURNAL_NAME not in names
    assert ".config-amendment.lock" not in names
    assert scan_archive(archive_path) == ()


def test_archive_restore_preserves_owned_config_and_manifest_bytes(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    run_dir.mkdir(parents=True)
    config_path, manifest_path, _target = _owned_project(run_dir)
    expected_config = config_path.read_bytes()
    expected_manifest = manifest_path.read_bytes()

    project.archive_rq("demo", comment="owned bytes")
    archive_path = next((run_dir / "archives").glob("*.zip"))
    config_path.write_text("[changed]\nvalue = true\n", encoding="utf-8")
    manifest_path.write_text("{}\n", encoding="utf-8")

    project.restore_archive_rq("demo", archive_path.name)

    assert config_path.read_bytes() == expected_config
    assert manifest_path.read_bytes() == expected_manifest
    assert not (run_dir / JOURNAL_NAME).exists()
    loaded = load_project_config(
        wd=run_dir,
        config_token=config_path.stem,
        parent_wd=None,
        config_dir=run_dir,
        defaults_resolver=lambda _wd: str(run_dir / "unused.cfg"),
        parser_factory=RawConfigParser,
        run_id="demo",
    )
    assert loaded.status.mode == "flattened"
    assert loaded.status.manifest_valid is True


def test_restore_legacy_archive_ignores_transaction_files_and_uses_fallback(
    archive_rq_environment,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    archive_path = archives_dir / "legacy.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("legacy.txt", "legacy")
        zf.writestr("legacy.cfg", "[local]\nvalue = retained\n")
        zf.writestr(JOURNAL_NAME, "untrusted transaction state")
        zf.writestr(".config-amendment.lock", "")
    defaults_path = tmp_path / "shared-defaults.cfg"
    defaults_path.write_text("[legacy]\nvalue = shared\n", encoding="utf-8")

    project.restore_archive_rq("demo", archive_path.name)

    assert not (run_dir / JOURNAL_NAME).exists()
    loaded = load_project_config(
        wd=run_dir,
        config_token="legacy",
        parent_wd=None,
        config_dir=run_dir,
        defaults_resolver=lambda _wd: str(defaults_path),
        parser_factory=RawConfigParser,
        run_id="demo",
    )
    assert loaded.status.mode == "legacy"
    assert loaded.parser.get("legacy", "value") == "shared"
    assert loaded.parser.get("local", "value") == "retained"


@pytest.mark.parametrize(
    ("manifest_change", "warning_code"),
    [
        (lambda manifest: manifest.update({"schema_version": 999}), "manifest_schema_newer"),
        (lambda manifest: manifest.update({"parent_chain": []}), "manifest_invalid"),
    ],
)
def test_restore_degraded_manifest_remains_readable_with_updates_disabled(
    archive_rq_environment,
    manifest_change,
    warning_code: str,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    config_path, manifest_path, _target = _owned_project(source_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_change(manifest)
    archive_path = archives_dir / "degraded.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr(config_path.name, config_path.read_bytes())
        zf.writestr(
            manifest_path.name,
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        )

    project.restore_archive_rq("demo", archive_path.name)
    loaded = load_project_config(
        wd=run_dir,
        config_token=config_path.stem,
        parent_wd=None,
        config_dir=run_dir,
        defaults_resolver=lambda _wd: str(run_dir / "unused.cfg"),
        parser_factory=RawConfigParser,
        run_id="demo",
    )
    assert loaded.status.mode == "flattened"
    assert loaded.status.updates_enabled is False
    assert [warning.code for warning in loaded.status.warnings] == [warning_code]


def test_archive_composite_run_uses_top_level_config_authority(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    parent = tmp_path / "run-1"
    child = parent / "_pups" / "omni" / "scenarios" / "treated"
    child.mkdir(parents=True)
    (child / "child.txt").write_text("child", encoding="utf-8")
    runid = "run-1;;omni;;treated"
    monkeypatch.setattr(
        project,
        "get_wd",
        lambda value: str(child if value == runid else parent),
    )
    guarded: list[Path] = []
    real_guard = project.project_config_lifecycle_guard

    def _guard(path):
        guarded.append(Path(path))
        return real_guard(path)

    monkeypatch.setattr(project, "project_config_lifecycle_guard", _guard)

    project.archive_rq(runid, comment=None)

    assert guarded == [parent]


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


def test_restore_archive_rq_rechecks_locks_before_removing_existing_files(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    current_file = run_dir / "current.txt"
    current_file.write_text("keep-me", encoding="utf-8")
    archive_path = archives_dir / "snapshot.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")

    monkeypatch.setattr(project, "lock_statuses", lambda runid: {"watershed.nodb": True})

    with pytest.raises(RuntimeError, match="Cannot restore while NoDb files are locked"):
        project.restore_archive_rq("demo", archive_path.name)

    assert current_file.read_text(encoding="utf-8") == "keep-me"
    assert prep_by_run["demo"].cleared == 1


def test_restore_archive_rq_ignores_false_lock_entries(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, _prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    archive_path = archives_dir / "snapshot.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")

    monkeypatch.setattr(project, "lock_statuses", lambda runid: {"watershed.nodb": False})

    project.restore_archive_rq("demo", archive_path.name)
    assert (run_dir / "restored.txt").read_text(encoding="utf-8") == "value"


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


def test_restore_archive_rq_retries_directory_cleanup_after_permission_error(
    archive_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, tmp_path, _published, prep_by_run = archive_rq_environment
    run_dir = tmp_path / "demo"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)

    stale_export_dir = run_dir / "export" / "features" / "artifacts" / "artifact-1"
    stale_export_dir.mkdir(parents=True)
    (stale_export_dir / "features_export.gdb").write_text("stale", encoding="utf-8")

    archive_path = archives_dir / "demo.20260218T000000Z.zip"
    with zipfile.ZipFile(archive_path, mode="w") as zf:
        zf.writestr("restored.txt", "value")

    real_rmtree = project._archive_helpers.shutil.rmtree
    raised_once = {"value": False}

    def _flaky_rmtree(path: str | Path, *args: object, **kwargs: object) -> None:
        if Path(path) == run_dir / "export" and not raised_once["value"]:
            raised_once["value"] = True
            raise PermissionError(errno.EACCES, "permission denied", str(path))
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(project._archive_helpers.shutil, "rmtree", _flaky_rmtree)

    project.restore_archive_rq("demo", archive_path.name)

    assert raised_once["value"]
    assert not (run_dir / "export").exists()
    assert (run_dir / "restored.txt").read_text(encoding="utf-8") == "value"
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
