#!/usr/bin/env python3
"""
Run migrations for a runid or working directory, skipping when already clean.

Usage:
    python -m wepppy.tools.migrations.migrate_run --runid <runid>
    python -m wepppy.tools.migrations.migrate_run --wd /wc1/runs/lt/lt_202012_foo
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from wepppy.tools.migrations.run_migrations import create_archive
from wepppy.tools.migrations.runner import check_migrations_needed, run_all_migrations
from wepppy.weppcloud.utils.helpers import get_wd


def _resolve_wd(runid: Optional[str], wd: Optional[str]) -> Path:
    if wd:
        return Path(wd).expanduser().resolve()
    if runid:
        return Path(get_wd(runid, prefer_active=False)).expanduser().resolve()
    raise ValueError("runid or wd is required")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run migrations for a runid or working directory.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--runid", help="Run identifier to migrate.")
    group.add_argument("--wd", help="Working directory to migrate.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what migrations would run without making changes.",
    )
    parser.add_argument(
        "--archive-before",
        action="store_true",
        help="Create an archive backup before running migrations.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run migrations even if check indicates nothing to do.",
    )
    parser.add_argument(
        "--only",
        action="append",
        dest="migrations",
        metavar="MIGRATION",
        help="Run only specific migration(s). Can be specified multiple times.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        run_path = _resolve_wd(args.runid, args.wd)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    if not run_path.exists():
        print(f"Error: working directory not found: {run_path}")
        return 1

    status = check_migrations_needed(str(run_path))
    if not status.get("needs_migration") and not args.force:
        print(f"No migrations needed for {run_path}")
        return 0

    if args.archive_before and not args.dry_run:
        archive_path = create_archive(str(run_path), verbose=args.verbose)
        if not archive_path:
            print("Warning: archive creation failed; continuing without backup")

    def progress_callback(migration_name: str, message: str) -> None:
        if args.verbose or args.dry_run:
            print(f"{migration_name}: {message}")

    result = run_all_migrations(
        str(run_path),
        dry_run=args.dry_run,
        migrations=args.migrations,
        on_progress=progress_callback,
    )

    if result.applied:
        action = "Would apply" if args.dry_run else "Applied"
        print(f"{action} migrations: {', '.join(result.applied)}")
    if result.skipped:
        print(f"Skipped migrations: {', '.join(result.skipped)}")
    if result.errors:
        print("Errors:")
        for name, error in result.errors.items():
            print(f"  {name}: {error}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
