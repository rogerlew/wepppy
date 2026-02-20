from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_ARCHIVE_DISK_HEADROOM_RATIO: float
_ARCHIVE_MIN_HEADROOM_BYTES: int
_ARCHIVE_PER_FILE_OVERHEAD_BYTES: int
_ARCHIVE_EXCLUDE_PREFIXES: tuple[str, ...]

class ArchiveRuntime:
    get_current_job: Callable[[], Any]
    get_wd: Callable[[str], str]
    get_prep_from_runid: Callable[[str], Any]
    lock_statuses: Callable[[str], Mapping[str, Any]]
    clear_nodb_file_cache: Callable[[str], Sequence[Any]]
    publish_status: Callable[[str, str], None]
    disk_usage: Callable[[str | os.PathLike[str]], Any]
    zip_file_cls: type[zipfile.ZipFile]

    def __init__(
        self,
        get_current_job: Callable[[], Any],
        get_wd: Callable[[str], str],
        get_prep_from_runid: Callable[[str], Any],
        lock_statuses: Callable[[str], Mapping[str, Any]],
        clear_nodb_file_cache: Callable[[str], Sequence[Any]],
        publish_status: Callable[[str, str], None],
        disk_usage: Callable[[str | os.PathLike[str]], Any],
        zip_file_cls: type[zipfile.ZipFile],
    ) -> None: ...


def _normalize_relpath(relpath: str) -> str: ...

def _is_archive_excluded_relpath(relpath: str) -> bool: ...

def _estimate_archive_required_bytes(payload_bytes: int, file_count: int) -> int: ...

def _assert_sufficient_disk_space(
    base_path: Path,
    *,
    required_bytes: int,
    purpose: str,
    reclaimable_bytes: int = ...,
    disk_usage: Callable[[str | os.PathLike[str]], Any] = ...,
) -> None: ...

def _calculate_run_payload_bytes(wd: Path) -> tuple[int, int]: ...

def _collect_restore_members(
    zf: zipfile.ZipFile,
    wd: Path,
) -> tuple[list[tuple[zipfile.ZipInfo, Path, Path]], int, int]: ...

def archive_rq(runid: str, comment: str | None, *, runtime: ArchiveRuntime) -> None: ...

def restore_archive_rq(runid: str, archive_name: str, *, runtime: ArchiveRuntime) -> None: ...
