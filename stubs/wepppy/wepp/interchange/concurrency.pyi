from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Sequence

INTERCHANGE_TMP_DIR: Path

def _select_context() -> Any: ...

def _is_writable(path: Path) -> bool: ...

def _resolve_tmp_path(target_path: Path, tmp_dir: Optional[Path]) -> Path: ...

def _commit_tmp(tmp_path: Path, target_path: Path) -> None: ...

def _default_empty_table(schema: Any) -> Any: ...

def _write_impl(
    file_list: List[Path],
    parser: Callable[[Path], Any],
    schema: Any,
    target: Path,
    *,
    tmp_dir: Optional[Path],
    max_workers: Optional[int],
    empty_table: Any,
) -> Path: ...

def write_parquet_with_pool(
    files: Iterable[Path],
    parser: Callable[[Path], Any],
    schema: Any,
    target_path: Path,
    *,
    tmp_dir: Optional[Path] = ...,
    max_workers: Optional[int] = ...,
    empty_table: Optional[Any] = ...,
) -> Path: ...
