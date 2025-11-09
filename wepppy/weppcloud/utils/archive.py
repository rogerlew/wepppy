"""Server-side helpers for archiving run directories."""

from __future__ import annotations

import os
import shutil
import subprocess

# This module differs from the archive blueprint, which handles user-facing downloads.
# Here we focus on the background archiving and restoration flows that move run folders
# between `/wc/runs` and the cold-storage `/wc/archive` hierarchy.


def archive_run(runid: str, archive_dir: str = "/wc/archive", wd: str | None = None) -> None:
    """Compress a run directory into the partitioned archive tree.

    Args:
        runid: Run identifier to archive.
        archive_dir: Root directory that stores archived runs.
        wd: Optional absolute path to the run directory. When omitted the helper
            resolves it via `helpers.get_wd`.

    Raises:
        Exception: If the archive could not be created or the source directory
            cannot be removed after a successful archive.
    """
    if wd is None:
        from wepppy.weppcloud.utils.helpers import get_wd
        wd = get_wd(runid)

    # Get the first two characters for the subdirectory (handle short runids)
    prefix = runid[:2] if len(runid) >= 2 else runid.ljust(2, '_')
    
    # Create the subdirectory path (e.g., archive_dir/th)
    subdir = os.path.join(archive_dir, prefix)
    os.makedirs(subdir, exist_ok=True)  # Create if it doesn’t exist
    
    # Full path for the .tar.gz file (e.g., archive_dir/th/thunderHub.tar.gz)
    arc_fn = os.path.join(subdir, runid + '.tar.gz')

    if os.path.exists(arc_fn):
        os.remove(arc_fn)
    
    # Use tar -czf directly and capture output
    result = subprocess.run(f'tar -cf - -C "{wd}" . | pigz -p 8 > "{arc_fn}"', 
                           shell=True, 
                           check=False,  # Changed to false to handle error ourselves
                           capture_output=True,
                           text=True)

    if os.path.exists(arc_fn):
        try:
            shutil.rmtree(wd)
        except PermissionError:
            raise Exception(f'PermissionError: Failed to remove {wd} during archiving')

    else:
        stdout = result.stdout
        stderr = result.stderr
        raise Exception(f'Archive {arc_fn} does not exist. Failed to archive {runid}\n'
                       f'Command output: stdout={stdout}, stderr={stderr}')
    
    
def has_archive(runid: str, archive_dir: str = "/wc/archive") -> bool:
    """Return True if the archive tree already contains the run's tarball."""
    # Get the first two characters for the subdirectory (handle short runids)
    prefix = runid[:2] if len(runid) >= 2 else runid.ljust(2, '_')
    
    # Full path for the .tar.gz file (e.g., archive_dir/th/thunderHub.tar.gz)
    arc_fn = os.path.join(archive_dir, prefix, runid + '.tar.gz')
    
    return os.path.exists(arc_fn)


def restore_archive(arc_fn: str, wc_runs: str = '/wc/runs/') -> None:
    """Inflate an archived run back into the active runs tree.

    Args:
        arc_fn: Absolute path to the `.tar.gz` archive that should be restored.
        wc_runs: Root directory that stores live runs.

    Raises:
        Exception: If the archive cannot be found or decompressed.
    """
    # Get the runid from the archive filename
    runid = os.path.split(arc_fn)[1].split('.')[0]
    
    # Get the first two characters for the subdirectory (handle short runids)
    prefix = runid[:2] if len(runid) >= 2 else runid.ljust(2, '_')
    
    # Create the subdirectory path (e.g., wc_runs/th)
    subdir = os.path.join(wc_runs, prefix)
    os.makedirs(subdir, exist_ok=True)  # Create if it doesn’t exist
    
    # Full path for the .tar.gz file (e.g., wc_runs/th/thunderHub.tar.gz)
    arc_fn = os.path.join(subdir, runid + '.tar.gz')

    if os.path.exists(arc_fn):
        os.remove(arc_fn)
    
    # Use tar -czf directly and capture output
    result = subprocess.run(f'pigz -dc "{arc_fn}" | tar -xf - -C "{subdir}"', 
                           shell=True, 
                           check=False,  # Changed to false to handle error ourselves
                           capture_output=True,
                           text=True)

    if os.path.exists(arc_fn):
        try:
            os.remove(arc_fn)
        except PermissionError:
            raise Exception(f'PermissionError: Failed to remove {arc_fn} during restoration')

    else:
        stdout = result.stdout
        stderr = result.stderr
        raise Exception(f'Archive {arc_fn} does not exist. Failed to restore {runid}\n'
                       f'Command output: stdout={stdout}, stderr={stderr}')
