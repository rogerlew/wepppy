from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WAT_FILE_RE: Any
RAW_HEADER_SUBSTITUTIONS: Tuple[Tuple[str, str], ...]
WAT_COLUMN_NAMES: List[str]
HEADER_ALIASES: Dict[str, str]
SCHEMA: Any
EMPTY_TABLE: Any
CANONICAL_COLUMN_ALIASES: Dict[str, Tuple[str, ...]]
PANDAS_TYPE_MAP: Dict[str, Any]
DAILY_MM_COLUMNS: Tuple[str, ...]

def _empty_wat_dataframe() -> Any: ...

def _resolve_column_aliases(path: Path) -> Dict[str, str]: ...

def _coerce_wat_dtypes(frame: Any) -> Any: ...

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _extract_header(lines: List[str]) -> Tuple[List[str], int]: ...

def _parse_wat_file(path: Path) -> Any: ...

def run_wepp_hillslope_wat_interchange(wepp_output_dir: Path | str) -> Path: ...

def load_hill_wat_dataframe(
    wepp_output_dir: Path | str,
    wepp_id: int,
    *,
    collapse: Optional[str] = ...,
) -> Any: ...
