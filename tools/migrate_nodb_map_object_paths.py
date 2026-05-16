#!/usr/bin/env python3
"""Migrate NoDb Map jsonpickle paths from ``map.Map`` to ``map_object.Map``."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

LEGACY_MAP_CLASS_PATH = "wepppy.nodb.core.map.Map"
MAP_OBJECT_CLASS_PATH = "wepppy.nodb.core.map_object.Map"


@dataclass(frozen=True)
class FileMigrationResult:
    path: Path
    replacements: int
    updated: bool
    error: str | None = None


def iter_nodb_files(root: Path) -> Iterable[Path]:
    """Yield ``.nodb`` files under ``root`` (or ``root`` itself if it is a file)."""
    if root.is_file():
        if root.suffix == ".nodb":
            yield root
        return

    if not root.exists():
        return

    for candidate in root.rglob("*.nodb"):
        if candidate.is_file():
            yield candidate


def migrate_nodb_text(
    text: str,
    *,
    legacy_class_path: str = LEGACY_MAP_CLASS_PATH,
    new_class_path: str = MAP_OBJECT_CLASS_PATH,
) -> tuple[str, int]:
    """Return migrated text plus replacement count."""
    replacements = text.count(legacy_class_path)
    if replacements == 0:
        return text, 0
    return text.replace(legacy_class_path, new_class_path), replacements


def migrate_nodb_file(
    path: Path,
    *,
    write: bool,
    backup_ext: str = "",
    legacy_class_path: str = LEGACY_MAP_CLASS_PATH,
    new_class_path: str = MAP_OBJECT_CLASS_PATH,
) -> FileMigrationResult:
    """Migrate one ``.nodb`` file, optionally writing changes to disk."""
    try:
        original_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return FileMigrationResult(path=path, replacements=0, updated=False, error=str(exc))

    migrated_text, replacements = migrate_nodb_text(
        original_text,
        legacy_class_path=legacy_class_path,
        new_class_path=new_class_path,
    )
    if replacements == 0:
        return FileMigrationResult(path=path, replacements=0, updated=False)
    if not write:
        return FileMigrationResult(path=path, replacements=replacements, updated=False)

    try:
        if backup_ext:
            Path(f"{path}{backup_ext}").write_text(original_text, encoding="utf-8")
        path.write_text(migrated_text, encoding="utf-8")
    except OSError as exc:
        return FileMigrationResult(path=path, replacements=replacements, updated=False, error=str(exc))
    return FileMigrationResult(path=path, replacements=replacements, updated=True)


def run_migration(
    *,
    root: Path,
    write: bool,
    backup_ext: str = "",
    legacy_class_path: str = LEGACY_MAP_CLASS_PATH,
    new_class_path: str = MAP_OBJECT_CLASS_PATH,
) -> list[FileMigrationResult]:
    """Run migration for all ``.nodb`` files under root."""
    results: list[FileMigrationResult] = []
    for file_path in iter_nodb_files(root):
        results.append(
            migrate_nodb_file(
                file_path,
                write=write,
                backup_ext=backup_ext,
                legacy_class_path=legacy_class_path,
                new_class_path=new_class_path,
            )
        )
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite .nodb jsonpickle Map class paths from map.Map to map_object.Map.",
    )
    parser.add_argument(
        "--root",
        default="/wc1/runs",
        help="Root directory to scan for .nodb files (default: /wc1/runs).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write modifications in place. Without this flag, script runs in dry-run mode.",
    )
    parser.add_argument(
        "--backup-ext",
        default="",
        help="Optional backup suffix for original files when --write is used (example: .bak).",
    )
    return parser


def _print_summary(results: Sequence[FileMigrationResult], *, write: bool) -> int:
    scanned = len(results)
    matched = sum(1 for result in results if result.replacements > 0)
    updated = sum(1 for result in results if result.updated)
    replacement_total = sum(result.replacements for result in results)
    errored = [result for result in results if result.error is not None]

    mode = "WRITE" if write else "DRY-RUN"
    print(f"[{mode}] scanned={scanned} matched={matched} replacements={replacement_total} updated={updated}")
    for result in errored:
        print(f"ERROR {result.path}: {result.error}")
    return 1 if errored else 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    root = Path(args.root)
    results = run_migration(
        root=root,
        write=bool(args.write),
        backup_ext=str(args.backup_ext) if args.write else "",
    )
    return _print_summary(results, write=bool(args.write))


if __name__ == "__main__":
    raise SystemExit(main())
