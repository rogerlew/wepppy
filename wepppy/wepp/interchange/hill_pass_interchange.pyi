from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

EVENT_LABELS: set[str]
SEDCLASS_COUNT: int
EVENT_FLOAT_COUNT: int
SUBEVENT_FLOAT_COUNT: int
NOEVENT_FLOAT_COUNT: int
SCHEMA: Any
EMPTY_TABLE: Any

def _event_tokens(lines: List[str], start_idx: int) -> Tuple[List[str], int]: ...

def _subevent_tokens(line: str) -> List[str]: ...

def _noevent_tokens(line: str) -> List[str]: ...

def _init_column_store() -> Dict[str, List[object]]: ...

def _append_row(store: Dict[str, List[object]], row: Dict[str, object]) -> None: ...

def _parse_pass_file(path: Path, *, calendar_lookup: Dict[int, List[Tuple[int, int]]] | None = ...) -> Any: ...

def run_wepp_hillslope_pass_interchange(wepp_output_dir: Path | str, *, expected_hillslopes: int | None = ...) -> Path: ...
PASS_FILE_RE: Any
