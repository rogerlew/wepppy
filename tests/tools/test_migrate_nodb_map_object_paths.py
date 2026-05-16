from __future__ import annotations

from pathlib import Path
import runpy

import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/migrate_nodb_map_object_paths.py"))


def test_migrate_nodb_text_rewrites_legacy_map_path() -> None:
    module = _module()
    migrate_nodb_text = module["migrate_nodb_text"]

    original = (
        '{"py/object":"wepppy.nodb.core.map.Map","_map":{"py/object":"wepppy.nodb.core.map.Map"}}'
    )
    migrated, replacements = migrate_nodb_text(original)

    assert replacements == 2
    assert "wepppy.nodb.core.map.Map" not in migrated
    assert migrated.count("wepppy.nodb.core.map_object.Map") == 2


def test_run_migration_dry_run_reports_without_writing(tmp_path: Path) -> None:
    module = _module()
    run_migration = module["run_migration"]

    run_root = tmp_path / "runs"
    target = run_root / "demo" / "ron.nodb"
    target.parent.mkdir(parents=True, exist_ok=True)
    original = '{"py/object":"wepppy.nodb.core.map.Map"}'
    target.write_text(original, encoding="utf-8")

    results = run_migration(root=run_root, write=False)
    assert len(results) == 1
    result = results[0]
    assert result.replacements == 1
    assert result.updated is False
    assert result.error is None
    assert target.read_text(encoding="utf-8") == original


def test_run_migration_write_updates_files_and_backup(tmp_path: Path) -> None:
    module = _module()
    run_migration = module["run_migration"]

    run_root = tmp_path / "runs"
    target = run_root / "demo" / "watershed.nodb"
    target.parent.mkdir(parents=True, exist_ok=True)
    original = (
        '{"py/object":"wepppy.nodb.core.map.Map","items":["wepppy.nodb.core.map.Map"]}'
    )
    target.write_text(original, encoding="utf-8")

    results = run_migration(root=run_root, write=True, backup_ext=".bak")
    assert len(results) == 1
    result = results[0]
    assert result.replacements == 2
    assert result.updated is True
    assert result.error is None

    migrated = target.read_text(encoding="utf-8")
    assert "wepppy.nodb.core.map.Map" not in migrated
    assert migrated.count("wepppy.nodb.core.map_object.Map") == 2
    assert Path(f"{target}.bak").read_text(encoding="utf-8") == original
