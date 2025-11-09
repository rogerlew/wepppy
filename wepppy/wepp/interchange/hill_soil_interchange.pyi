from __future__ import annotations

from pathlib import Path
from re import Pattern
from typing import Any, Dict, List, Tuple

SOIL_FILE_RE: Pattern[str]
RAW_HEADER: List[str]
LEGACY_HEADER: List[str]
RAW_UNITS: List[str]
COMPACT_UNITS: List[str]
LEGACY_UNITS: List[str]
MEASUREMENT_COLUMNS: List[str]
LEGACY_MEASUREMENT_COLUMNS: List[str]
SCHEMA: Any
EMPTY_TABLE: Any

def _extract_layout(lines: List[str]) -> Tuple[List[str], List[str], List[str]]: ...

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _parse_soil_file(path: Path) -> Any: ...

def run_wepp_hillslope_soil_interchange(wepp_output_dir: Path | str) -> Path: ...
