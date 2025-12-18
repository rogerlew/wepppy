"""Utilities shared across Starlette entrypoints."""

from __future__ import annotations

from pathlib import Path

from wepppy.weppcloud.utils.helpers import get_wd


def resolve_run_path(runid_param: str) -> Path:
    """Resolve a run identifier or path to an absolute existing directory.

    Handles URL path formats like ``runid/config`` by stripping the config
    suffix since run data lives at the run root, not in config subdirectories.

    Args:
        runid_param: Run slug, ``runid/config`` path, or filesystem path.

    Returns:
        Absolute Path to the detected run directory.

    Raises:
        FileNotFoundError: If the path cannot be resolved.
    """

    # Try full path first
    try:
        wd = get_wd(runid_param)
    except Exception:
        wd = None

    if wd:
        run_path = Path(wd).expanduser()
        if run_path.exists():
            return run_path.resolve()

    # Handle runid/config format: extract just the runid (first segment)
    # URL paths like "rlew-gummed-message/disturbed9002_wbt" should resolve
    # to the run directory for "rlew-gummed-message"
    if "/" in runid_param and not runid_param.startswith("/"):
        base_runid = runid_param.split("/")[0]
        try:
            wd = get_wd(base_runid)
        except Exception:
            wd = None

        if wd:
            run_path = Path(wd).expanduser()
            if run_path.exists():
                return run_path.resolve()

    param_path = Path(runid_param)
    if param_path.is_absolute():
        if param_path.exists():
            return param_path.expanduser().resolve()

    candidate = Path("/" + runid_param)
    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(runid_param)
