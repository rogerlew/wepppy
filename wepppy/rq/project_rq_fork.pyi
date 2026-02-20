from __future__ import annotations

from typing import Any, Callable


def _clean_env_for_system_tools() -> dict[str, str]: ...

def _build_fork_rsync_cmd(run_right: str, *, undisturbify: bool) -> list[str]: ...

def prepare_fork_run(
    runid: str,
    new_runid: str,
    *,
    undisturbify: bool,
    status_channel: str,
    publish_status: Callable[[str, str], None],
    get_wd: Callable[[str], str],
    get_primary_wd: Callable[[str], str],
    wait_for_paths: Callable[..., Any],
    ron_cls: Any,
    disturbed_cls: Any,
    landuse_cls: Any,
    soils_cls: Any,
    initialize_ttl: Callable[[str], None] | None,
    format_ttl_failure: Callable[[Exception], str] | None = ...,
) -> str: ...
