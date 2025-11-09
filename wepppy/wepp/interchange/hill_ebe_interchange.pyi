from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

EBE_FILE_RE: Any
UNIT_SKIP_TOKENS: set[str]
RAW_HEADER_STANDARD: List[str]
RAW_UNITS_STANDARD: List[str]
RAW_HEADER_REVEG: List[str]
RAW_UNITS_REVEG: List[str]
RAW_LAYOUTS: Dict[str, Tuple[List[str], List[str]]]
MEASUREMENT_COLUMNS_STANDARD: List[str]
MEASUREMENT_COLUMNS_REVEG: List[str]
MEASUREMENT_COLUMNS_BY_LAYOUT: Dict[str, List[str]]
COLUMN_ALIASES: Dict[str, str]
SCHEMA: Any
EMPTY_TABLE: Any
BASE_FIELD_NAMES: Tuple[str, ...]
MEASUREMENT_FIELD_NAMES: List[str]

def _normalize_column_names(headers: List[str], units: List[str]) -> Tuple[List[str], str]: ...

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _extract_tokens(lines: List[str]) -> Tuple[List[str], List[str], List[str]]: ...

def _parse_ebe_file(path: Path, *, start_year: Optional[int] = ...) -> Any: ...

def run_wepp_hillslope_ebe_interchange(wepp_output_dir: Path | str, *, start_year: Optional[int] = ...) -> Path: ...
