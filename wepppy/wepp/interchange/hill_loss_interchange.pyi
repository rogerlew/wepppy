from __future__ import annotations

from pathlib import Path
from re import Pattern
from typing import Any, Dict, List, Optional

LOSS_FILE_RE: Pattern[str]
MEASUREMENT_COLUMNS: List[str]
COLUMN_ALIASES: Dict[str, str]
SCHEMA: Any
EMPTY_TABLE: Any

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _locate_class_table(lines: List[str]) -> Optional[int]: ...

def _parse_loss_file(path: Path) -> Any: ...

def run_wepp_hillslope_loss_interchange(wepp_output_dir: Path | str, *, expected_hillslopes: int | None = None) -> Path: ...
