from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Mapping

class DeleteRuntime:
    get_current_job: Callable[[], Any]
    get_wd: Callable[[str], str]
    publish_status: Callable[[str, str], None]
    clear_nodb_file_cache: Callable[[str], Any]
    clear_locks: Callable[[str], Any]
    rmtree: Callable[[Path], None]
    sleep: Callable[[float], None]
    logger: logging.Logger

    def __init__(
        self,
        get_current_job: Callable[[], Any],
        get_wd: Callable[[str], str],
        publish_status: Callable[[str, str], None],
        clear_nodb_file_cache: Callable[[str], Any],
        clear_locks: Callable[[str], Any],
        rmtree: Callable[[Path], None],
        sleep: Callable[[float], None],
        logger: logging.Logger,
    ) -> None: ...


def delete_run_rq(runid: str, wd: str | None = ..., *, delete_files: bool = ..., runtime: DeleteRuntime) -> None: ...

def gc_runs_rq(
    *,
    root: str = ...,
    limit: int = ...,
    dry_run: bool = ...,
    runtime: DeleteRuntime,
) -> Mapping[str, Any]: ...

def compile_dot_logs_rq(
    *,
    access_log_path: str | None = ...,
    run_locations_path: str | None = ...,
    run_roots: list[str] | None = ...,
    legacy_roots: list[str] | None = ...,
    runtime: DeleteRuntime,
) -> Mapping[str, Any]: ...
