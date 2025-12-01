#!/usr/bin/env python3
"""
Run all migrations on a single working directory.

This script applies all available migrations to a run directory, normalizing
legacy assets and updating schemas. It's idempotent and safe to run multiple times.

Usage:
    python -m wepppy.tools.migrations.run_migrations /path/to/run/directory
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/bi/biogeographic-six
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/bi/biogeographic-six --dry-run
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/bi/biogeographic-six --archive-before

Examples:
    # Check what migrations would run (dry run)
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/rlew-demo --dry-run

    # Run all migrations
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/rlew-demo

    # Run with archive backup first
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/rlew-demo --archive-before

    # Run specific migrations only
    python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/rlew-demo --only run_paths --only observed_nodb
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def create_archive(wd: str, verbose: bool = True) -> Optional[str]:
    """
    Create an archive backup of the working directory.
    
    Args:
        wd: Working directory path
        verbose: If True, print progress messages
        
    Returns:
        Path to created archive, or None if failed
    """
    run_path = Path(wd)
    runid = run_path.name
    
    archives_dir = run_path / "archives"
    archives_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    archive_name = f'{runid}.pre_migration.{timestamp}.zip'
    archive_path = archives_dir / archive_name
    archive_path_tmp = archive_path.with_suffix('.zip.tmp')
    
    if archive_path_tmp.exists():
        archive_path_tmp.unlink()
    
    if verbose:
        print(f"📦 Creating archive: {archive_name}")
    
    try:
        with zipfile.ZipFile(archive_path_tmp, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(wd):
                rel_root = os.path.relpath(root, wd)
                
                # Skip archives directory
                if rel_root.startswith('archives'):
                    dirs[:] = []
                    continue
                
                dirs[:] = [d for d in dirs if not os.path.relpath(os.path.join(root, d), wd).startswith('archives')]
                
                for filename in files:
                    abs_path = os.path.join(root, filename)
                    arcname = os.path.relpath(abs_path, wd)
                    if not arcname.startswith('archives'):
                        zf.write(abs_path, arcname)
        
        archive_path_tmp.rename(archive_path)
        
        if verbose:
            size_mb = archive_path.stat().st_size / (1024 * 1024)
            print(f"✅ Archive created: {archive_path} ({size_mb:.2f} MB)")
        
        return str(archive_path)
    except Exception as e:
        if verbose:
            print(f"❌ Archive creation failed: {e}")
        if archive_path_tmp.exists():
            archive_path_tmp.unlink()
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all migrations on a single working directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available migrations:
  observed_nodb     Migrate observed.nodb module path
  run_paths         Migrate hardcoded paths in .nodb files
  watersheds        Normalize watershed parquet schemas
  wbt_geojson       Normalize WBT GeoJSON ID types
  landuse_parquet   Normalize landuse parquet schema
  soils_parquet     Normalize soils parquet schema
  interchange       Generate WEPP interchange files

Examples:
  # Dry run to see what would change
  python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/demo --dry-run

  # Run all migrations with backup
  python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/demo --archive-before

  # Run specific migrations only
  python -m wepppy.tools.migrations.run_migrations /wc1/runs/rl/demo --only run_paths
"""
    )
    
    parser.add_argument(
        "wd",
        help="Path to the run working directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what migrations would run without making changes"
    )
    parser.add_argument(
        "--archive-before",
        action="store_true",
        help="Create archive backup before running migrations"
    )
    parser.add_argument(
        "--only",
        action="append",
        dest="migrations",
        metavar="MIGRATION",
        help="Run only specific migration(s). Can be specified multiple times."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress information"
    )
    parser.add_argument(
        "--list-migrations",
        action="store_true",
        help="List available migrations and exit"
    )
    
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    
    # Import runner after arg parsing to avoid slow startup for --help
    from wepppy.tools.migrations.runner import run_all_migrations, AVAILABLE_MIGRATIONS
    
    if args.list_migrations:
        print("Available migrations:")
        for name, fn in AVAILABLE_MIGRATIONS:
            doc = fn.__doc__ or ""
            first_line = doc.strip().split('\n')[0] if doc else "No description"
            print(f"  {name:20} {first_line}")
        return 0
    
    wd = os.path.abspath(args.wd)
    
    if not os.path.isdir(wd):
        print(f"❌ Directory not found: {wd}")
        return 1
    
    print(f"🔍 {'[DRY RUN] ' if args.dry_run else ''}Running migrations on: {wd}")
    print()
    
    # Archive before migrations if requested (and not dry run)
    if args.archive_before and not args.dry_run:
        archive_path = create_archive(wd, verbose=True)
        if archive_path:
            print()
        else:
            print("⚠️  Continuing without archive backup")
            print()
    
    def progress_callback(migration_name: str, message: str) -> None:
        if args.verbose or args.dry_run:
            print(f"  {message}")
    
    result = run_all_migrations(
        wd,
        dry_run=args.dry_run,
        migrations=args.migrations,
        on_progress=progress_callback,
    )
    
    print()
    
    # Summary
    if result.applied:
        action = "Would apply" if args.dry_run else "Applied"
        print(f"✅ {action} migrations: {', '.join(result.applied)}")
    
    if result.skipped:
        print(f"⏭️  Skipped migrations: {', '.join(result.skipped)}")
    
    if result.errors:
        print(f"❌ Errors:")
        for name, error in result.errors.items():
            print(f"   {name}: {error}")
    
    if not result.success:
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
