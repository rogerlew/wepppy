from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ELEMENT_FILE_RE: Any
ELEMENT_COLUMN_NAMES: List[str]
ELEMENT_FIELD_WIDTHS: List[int]
SCHEMA: Any
EMPTY_TABLE: Any
_LINE_WIDTH: int

def _is_missing_token(token: str) -> bool: ...

def _parse_optional_float(token: str) -> Optional[float]: ...

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _split_fixed_width_line(raw_line: str) -> List[str]: ...

def _normalize_date_tokens(
    raw_year: int,
    raw_month: int,
    raw_day: int,
    *,
    start_year: Optional[int] = ...,
) -> Tuple[int, int, int, int, int]: ...

def _parse_element_file(path: Path, *, start_year: Optional[int] = ...) -> Any: ...

def run_wepp_hillslope_element_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
) -> Path: ...
