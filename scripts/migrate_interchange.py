#!/usr/bin/env python3
"""
Migrate WEPP runs to generate Parquet interchange files.

This script converts legacy WEPP text output files to Parquet format,
enabling faster queries and modern analytics workflows. It's idempotent
and safe to run multiple times.

Usage:
    python scripts/migrate_interchange.py /path/to/run/directory
    python scripts/migrate_interchange.py /wc1/runs/bi/biogeographic-six
    python scripts/migrate_interchange.py /wc1/runs/bi/biogeographic-six --force
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional


def migrate_run_interchange(run_dir: str, force: bool = False) -> None:
    """
    Generate WEPP interchange Parquet files for a run directory.
    
    Args:
        run_dir: Path to the run directory
        force: If True, regenerate even if interchange already exists
    """
    run_path = Path(run_dir)
    
    if not run_path.exists():
        print(f"❌ Directory not found: {run_dir}")
        return
    
    # Check for required .nodb files
    wepp_nodb = run_path / "wepp.nodb"
    climate_nodb = run_path / "climate.nodb"
    
    if not wepp_nodb.exists() or not climate_nodb.exists():
        print(f"❌ Not a valid run directory (missing wepp.nodb or climate.nodb): {run_dir}")
        return
    
    # Locate WEPP output directory
    wepp_output_dir = run_path / "wepp" / "output"
    
    if not wepp_output_dir.exists():
        print(f"❌ WEPP output directory not found: {wepp_output_dir}")
        return
    
    # Check for existing interchange
    interchange_dir = wepp_output_dir / "interchange"
    version_file = interchange_dir / "interchange_version.json"
    
    if interchange_dir.exists() and version_file.exists() and not force:
        print(f"✓ Interchange already exists: {interchange_dir}")
        print(f"  (Use --force to regenerate)")
        return
    
    print(f"🔍 Migrating run: {run_dir}")
    print(f"   Output dir: {wepp_output_dir}")
    
    # Import wepppy modules (lazy import to validate environment first)
    try:
        from wepppy.nodb.core import Climate, Wepp
        from wepppy.wepp.interchange import (
            run_wepp_hillslope_interchange,
            run_wepp_watershed_interchange,
            run_totalwatsed3,
            generate_interchange_documentation,
        )
    except ImportError as e:
        print(f"❌ Failed to import wepppy modules: {e}")
        print(f"   Make sure you're in the correct Python environment")
        return
    
    # Load NoDb instances to get configuration
    try:
        climate = Climate.getInstance(str(run_path))
        wepp = Wepp.getInstance(str(run_path))
        start_year: Optional[int] = climate.calendar_start_year
        baseflow_opts = wepp.baseflow_opts
    except Exception as e:
        print(f"❌ Failed to load run configuration: {e}")
        return
    
    # Check for required watershed outputs
    required_watershed_outputs = [
        "pass_pw0.txt",
        "chan.out",
        "chanwb.out",
        "chnwb.txt",
        "ebe_pw0.txt",
        "soil_pw0.txt",
        "loss_pw0.txt",
    ]
    
    missing = []
    for filename in required_watershed_outputs:
        candidate = wepp_output_dir / filename
        gz_candidate = Path(f"{candidate}.gz")
        if not candidate.exists() and not gz_candidate.exists():
            missing.append(filename)
    
    has_watershed_outputs = len(missing) == 0
    
    if missing:
        print(f"⚠️  Missing watershed outputs: {', '.join(missing)}")
        print(f"   Will only generate hillslope interchange")
    
    # Backup existing interchange if forcing regeneration
    if force and interchange_dir.exists():
        backup_dir = interchange_dir.with_suffix('.bak')
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(str(interchange_dir), str(backup_dir))
        print(f"📦 Backed up existing interchange to: {backup_dir}")
    
    # Run hillslope interchange (always)
    try:
        print(f"🔄 Generating hillslope interchange...")
        result_dir = run_wepp_hillslope_interchange(wepp_output_dir, start_year=start_year)
        print(f"✅ Hillslope interchange complete: {result_dir}")
        
        # List generated files
        parquet_files = sorted(result_dir.glob("H.*.parquet"))
        for pf in parquet_files:
            size_mb = pf.stat().st_size / (1024 * 1024)
            print(f"   📊 {pf.name} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"❌ Hillslope interchange failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run watershed interchange (if we have outputs)
    if has_watershed_outputs:
        try:
            print(f"🔄 Generating watershed interchange...")
            run_wepp_watershed_interchange(wepp_output_dir, start_year=start_year)
            print(f"✅ Watershed interchange complete")
            
            # List watershed files
            watershed_files = sorted(interchange_dir.glob("W.*.parquet"))
            for wf in watershed_files:
                size_mb = wf.stat().st_size / (1024 * 1024)
                print(f"   📊 {wf.name} ({size_mb:.2f} MB)")
        except Exception as e:
            print(f"❌ Watershed interchange failed: {e}")
            import traceback
            traceback.print_exc()
            # Continue - hillslope interchange is still useful
    
    # Generate totalwatsed3 (combined daily balance)
    try:
        print(f"🔄 Generating totalwatsed3...")
        run_totalwatsed3(interchange_dir, baseflow_opts=baseflow_opts)
        
        totalwatsed_file = interchange_dir / "totalwatsed3.parquet"
        if totalwatsed_file.exists():
            size_mb = totalwatsed_file.stat().st_size / (1024 * 1024)
            print(f"✅ totalwatsed3.parquet generated ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"⚠️  totalwatsed3 generation failed: {e}")
        # Non-fatal - continue
    
    # Generate documentation
    try:
        print(f"🔄 Generating documentation...")
        generate_interchange_documentation(interchange_dir)
        readme_path = interchange_dir / "README.md"
        if readme_path.exists():
            print(f"✅ README.md generated")
    except Exception as e:
        print(f"⚠️  Documentation generation failed: {e}")
        # Non-fatal
    
    print()
    print(f"✅ Migration complete!")
    print(f"   Interchange directory: {interchange_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate WEPP runs to generate Parquet interchange files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate a run (skip if interchange already exists)
  python scripts/migrate_interchange.py /wc1/runs/bi/biogeographic-six
  
  # Force regeneration even if interchange exists
  python scripts/migrate_interchange.py /wc1/runs/bi/biogeographic-six --force
  
  # Process multiple runs
  for run in /wc1/runs/bi/*; do
    python scripts/migrate_interchange.py "$run"
  done
"""
    )
    
    parser.add_argument("run_dir", help="Path to the run directory")
    parser.add_argument("--force", action="store_true", 
                       help="Force regeneration even if interchange already exists")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.run_dir):
        print(f"❌ Directory not found: {args.run_dir}")
        sys.exit(1)
    
    migrate_run_interchange(args.run_dir, force=args.force)


if __name__ == "__main__":
    main()
