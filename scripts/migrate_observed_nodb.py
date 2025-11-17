#!/usr/bin/env python3
"""
Migrate legacy observed.nodb files from old module path to new path.

Old path: wepppy.nodb.observed.Observed
New path: wepppy.nodb.mods.observed.observed.Observed

Usage:
    python scripts/migrate_observed_nodb.py /path/to/run/directory
    python scripts/migrate_observed_nodb.py /wc1/runs/md/mdobre-auxiliary-responsiveness
"""

import os
import sys
import json
import shutil
from pathlib import Path


def migrate_observed_nodb(run_dir: str) -> None:
    """
    Migrate observed.nodb file in a run directory from legacy module path.
    
    Args:
        run_dir: Path to the run directory containing observed.nodb
    """
    run_path = Path(run_dir)
    observed_nodb = run_path / "observed.nodb"
    
    if not observed_nodb.exists():
        print(f"❌ No observed.nodb found in {run_dir}")
        return
    
    # Create backup
    backup_path = run_path / "observed.nodb.bak"
    shutil.copy2(observed_nodb, backup_path)
    print(f"✓ Created backup: {backup_path}")
    
    # Read the file
    try:
        with open(observed_nodb, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return
    
    # Check if migration is needed
    py_object = data.get("py/object", "")
    
    if py_object == "wepppy.nodb.mods.observed.observed.Observed":
        print(f"✓ Already migrated: {observed_nodb}")
        return
    
    if py_object == "wepppy.nodb.observed.Observed":
        print(f"🔄 Migrating: {observed_nodb}")
        print(f"   Old path: {py_object}")
        
        # Update the module path
        data["py/object"] = "wepppy.nodb.mods.observed.observed.Observed"
        
        print(f"   New path: {data['py/object']}")
        
        # Write back
        with open(observed_nodb, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Migration complete!")
    else:
        print(f"⚠️  Unknown py/object type: {py_object}")
        print(f"   File: {observed_nodb}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_observed_nodb.py /path/to/run/directory")
        print("\nExample:")
        print("  python scripts/migrate_observed_nodb.py /wc1/runs/md/mdobre-auxiliary-responsiveness")
        sys.exit(1)
    
    run_dir = sys.argv[1]
    
    if not os.path.isdir(run_dir):
        print(f"❌ Directory not found: {run_dir}")
        sys.exit(1)
    
    print(f"🔍 Checking run directory: {run_dir}")
    migrate_observed_nodb(run_dir)


if __name__ == "__main__":
    main()
