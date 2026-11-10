from __future__ import annotations

import functools
import inspect
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar, Any

from rq import get_current_job

from wepppy.weppcloud.utils.helpers import get_wd

P = ParamSpec("P")
R = TypeVar("R")

LOGGER = logging.getLogger(__name__)


def _extract_runid(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str | None:
    candidate = kwargs.get("runid")
    if candidate is None and args:
        candidate = args[0]
    if isinstance(candidate, str):
        return candidate
    return None


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
    except Exception as exc:  # broad-except: best-effort logging must preserve original failure
        # Best-effort: never mask the original exception path while attempting to
        # write `exceptions.log`.
        LOGGER.debug(
            "Failed to append exceptions.log (runid=%s func=%s): %s",
            runid,
            func_name,
            exc,
            exc_info=True,
        )


def with_exception_logging(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that appends exceptions to ``exceptions.log`` under the run folder."""

    signature = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        runid = None
        try:
            runid = signature.bind(*args, **kwargs).arguments.get("runid")
            if runid is not None:
                from wepppy.declarative.policy import require_task
                require_task(get_wd(runid), func.__name__)
            return func(*args, **kwargs)
        except Exception:  # broad-except: RQ telemetry boundary re-raises original task failure
            job = get_current_job()
            job_id = getattr(job, "id", None) if job is not None else None
            LOGGER.exception(
                "RQ task failed: %s (runid=%s job_id=%s)",
                func.__qualname__,
                runid,
                job_id,
            )
            if runid is not None:
                _append_exception_log(runid, func.__name__)
            raise

    return wrapper
