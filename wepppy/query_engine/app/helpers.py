from __future__ import annotations

from pathlib import Path

from wepppy.weppcloud.utils.helpers import get_wd


def resolve_run_path(runid_param: str) -> Path:
    """
    Resolve a run identifier or path to an absolute existing directory.
    """

    try:
        wd = get_wd(runid_param)
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
