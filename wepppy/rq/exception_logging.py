from __future__ import annotations

import functools
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar, Any

from wepppy.weppcloud.utils.helpers import get_wd

P = ParamSpec("P")
R = TypeVar("R")


def _append_exception_log(runid: str, func_name: str) -> None:
    """Best-effort append of traceback details to ``<wd>/exceptions.log``."""
    try:
        wd = Path(get_wd(runid))
        target = wd / "exceptions.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().isoformat() + "Z"
        formatted = traceback.format_exc()
        with target.open("a", encoding="utf-8") as stream:
            stream.write(f"[{timestamp}] {func_name} failed\n{formatted}\n")
    except Exception:
        # Never block the original exception path
        return


def with_exception_logging(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that appends exceptions to ``exceptions.log`` under the run folder."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except Exception:
            runid: Any | None = kwargs.get("runid")
            if runid is None and args:
                runid = args[0]
            if isinstance(runid, str):
                _append_exception_log(runid, func.__name__)
            raise

    return wrapper
