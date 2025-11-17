#!/usr/bin/env python3
"""
Migrate run directory paths in .nodb files and parquet files from old server paths to new paths.

This handles migrations like:
- /geodata/wc1/ -> /wc1/ (wepp.cloud -> test-production/docker)
- Any other path remapping needed

Usage:
    python scripts/migrate_run_paths.py /path/to/run/directory [--old-prefix /geodata/wc1 --new-prefix /wc1]
    python scripts/migrate_run_paths.py /wc1/runs/md/mdobre-auxiliary-responsiveness
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def migrate_paths_recursive(obj: Any, old_prefix: str, new_prefix: str) -> Any:
    """
    Recursively walk through a data structure and replace path prefixes.
    
    Args:
        obj: The object to process (dict, list, str, or other)
        old_prefix: The old path prefix to replace
        new_prefix: The new path prefix
        
    Returns:
        The object with paths migrated
    """
    if isinstance(obj, dict):
        return {k: migrate_paths_recursive(v, old_prefix, new_prefix) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [migrate_paths_recursive(item, old_prefix, new_prefix) for item in obj]
    elif isinstance(obj, str):
        if obj.startswith(old_prefix):
            return new_prefix + obj[len(old_prefix):]
        return obj
    else:
        return obj


def migrate_nodb_file(nodb_path: Path, old_prefix: str, new_prefix: str, dry_run: bool = False) -> tuple[bool, int]:
    """
    Migrate paths in a single .nodb file.
    
    Args:
        nodb_path: Path to the .nodb file
        old_prefix: The old path prefix to replace
        new_prefix: The new path prefix
        dry_run: If True, don't write changes
        
    Returns:
        (changed, count) tuple where changed is True if file was modified and count is number of replacements
    """
    try:
        with open(nodb_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse JSON in {nodb_path.name}: {e}")
        return False, 0
    except Exception as e:
        print(f"  ❌ Failed to read {nodb_path.name}: {e}")
        return False, 0
    
    # Convert to string to count occurrences
    original_str = json.dumps(data)
    count = original_str.count(old_prefix)
    
    if count == 0:
        return False, 0
    
    # Create backup before modifying
    if not dry_run:
        backup_path = nodb_path.with_suffix('.nodb.bak')
        shutil.copy2(nodb_path, backup_path)
    
    # Migrate paths
    migrated_data = migrate_paths_recursive(data, old_prefix, new_prefix)
    
    if not dry_run:
        with open(nodb_path, 'w') as f:
            json.dump(migrated_data, f, indent=2)
    
    return True, count


def clear_redis_cache(run_dir: str, dry_run: bool = False) -> int:
    """
    Clear Redis cache for a specific run directory.
    
    Args:
        run_dir: Path to the run directory
        dry_run: If True, show what would be cleared without clearing
        
    Returns:
        Number of keys that would be cleared (or were cleared)
    """
    # Extract the run identifier from the path
    # e.g., /wc1/runs/md/mdobre-auxiliary-responsiveness -> mdobre-auxiliary-responsiveness
    run_id = Path(run_dir).name
    
    total_cleared = 0
    
    # Clear cache in DB 13 (NoDb JSON caching)
    try:
        result = subprocess.run(
            ["redis-cli", "-n", "13", "--scan", "--pattern", f"*{run_id}*"],
            capture_output=True,
            text=True,
            check=True
        )
        cache_keys = [k for k in result.stdout.strip().split('\n') if k]
        
        if cache_keys:
            if dry_run:
                print(f"  Would clear {len(cache_keys)} cache key(s) from Redis DB 13")
                total_cleared += len(cache_keys)
            else:
                for key in cache_keys:
                    subprocess.run(["redis-cli", "-n", "13", "DEL", key], 
                                 capture_output=True, check=True)
                print(f"  🗑️  Cleared {len(cache_keys)} cache key(s) from Redis DB 13")
                total_cleared += len(cache_keys)
    except subprocess.CalledProcessError:
        print(f"  ⚠️  Failed to clear Redis DB 13 cache (redis-cli may not be available)")
    except Exception as e:
        print(f"  ⚠️  Error clearing Redis DB 13: {e}")
    
    # Clear locks in DB 0 (distributed locks)
    try:
        result = subprocess.run(
            ["redis-cli", "-n", "0", "--scan", "--pattern", f"*{run_id}*"],
            capture_output=True,
            text=True,
            check=True
        )
        lock_keys = [k for k in result.stdout.strip().split('\n') if k]
        
        if lock_keys:
            if dry_run:
                print(f"  Would clear {len(lock_keys)} lock key(s) from Redis DB 0")
                total_cleared += len(lock_keys)
            else:
                for key in lock_keys:
                    subprocess.run(["redis-cli", "-n", "0", "DEL", key], 
                                 capture_output=True, check=True)
                print(f"  🗑️  Cleared {len(lock_keys)} lock key(s) from Redis DB 0")
                total_cleared += len(lock_keys)
    except subprocess.CalledProcessError:
        print(f"  ⚠️  Failed to clear Redis DB 0 locks (redis-cli may not be available)")
    except Exception as e:
        print(f"  ⚠️  Error clearing Redis DB 0: {e}")
    
    return total_cleared


def migrate_run_directory(run_dir: str, old_prefix: str = "/geodata/wc1", new_prefix: str = "/wc1", dry_run: bool = False, clear_cache: bool = True):
    """
    Migrate all .nodb files in a run directory and clear Redis cache.
    
    Args:
        run_dir: Path to the run directory
        old_prefix: The old path prefix to replace
        new_prefix: The new path prefix
        dry_run: If True, show what would be changed without modifying files
        clear_cache: If True, clear Redis cache after migration
    """
    run_path = Path(run_dir)
    
    if not run_path.exists():
        print(f"❌ Directory not found: {run_dir}")
        return
    
    # Find all .nodb files
    nodb_files = sorted(run_path.glob("*.nodb"))
    
    if not nodb_files:
        print(f"❌ No .nodb files found in {run_dir}")
        return
    
    print(f"🔍 {'[DRY RUN] ' if dry_run else ''}Migrating paths in {run_dir}")
    print(f"   Old prefix: {old_prefix}")
    print(f"   New prefix: {new_prefix}")
    print()
    
    total_changed = 0
    total_replacements = 0
    
    for nodb_file in nodb_files:
        changed, count = migrate_nodb_file(nodb_file, old_prefix, new_prefix, dry_run)
        
        if changed:
            total_changed += 1
            total_replacements += count
            status = "🔄" if dry_run else "✅"
            print(f"  {status} {nodb_file.name}: {count} path(s) migrated")
            if not dry_run:
                print(f"     Backup: {nodb_file.name}.bak")
        else:
            print(f"  ⏭️  {nodb_file.name}: no changes needed")
    
    print()
    if dry_run:
        print(f"📊 Would migrate {total_changed}/{len(nodb_files)} files ({total_replacements} total replacements)")
        print(f"💡 Run without --dry-run to apply changes")
    else:
        print(f"✅ Migrated {total_changed}/{len(nodb_files)} files ({total_replacements} total replacements)")
    
    # Clear Redis cache if requested
    if clear_cache:
        print()
        print("🗑️  Clearing Redis cache...")
        keys_cleared = clear_redis_cache(run_dir, dry_run)
        if keys_cleared > 0:
            if dry_run:
                print(f"   Would clear {keys_cleared} total Redis key(s)")
            else:
                print(f"   ✅ Cleared {keys_cleared} total Redis key(s)")
        else:
            print(f"   ⏭️  No Redis keys found for this run")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate paths in .nodb files from old server to new server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from /geodata/wc1 to /wc1 (default)
  python scripts/migrate_run_paths.py /wc1/runs/md/mdobre-auxiliary-responsiveness
  
  # Dry run first to see what would change
  python scripts/migrate_run_paths.py /wc1/runs/md/mdobre-auxiliary-responsiveness --dry-run
  
  # Custom path mapping
  python scripts/migrate_run_paths.py /path/to/run --old-prefix /old/path --new-prefix /new/path
"""
    )
    
    parser.add_argument("run_dir", help="Path to the run directory containing .nodb files")
    parser.add_argument("--old-prefix", default="/geodata/wc1", help="Old path prefix to replace (default: /geodata/wc1)")
    parser.add_argument("--new-prefix", default="/wc1", help="New path prefix (default: /wc1)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--no-clear-cache", action="store_true", help="Skip clearing Redis cache after migration")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.run_dir):
        print(f"❌ Directory not found: {args.run_dir}")
        sys.exit(1)
    
    migrate_run_directory(args.run_dir, args.old_prefix, args.new_prefix, args.dry_run, clear_cache=not args.no_clear_cache)


if __name__ == "__main__":
    main()
