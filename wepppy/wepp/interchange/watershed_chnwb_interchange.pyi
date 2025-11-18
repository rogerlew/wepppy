from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CHANWB_FILENAME: str
CHANWB_PARQUET: str
SCHEMA: Any
MEASUREMENT_COLUMNS: Any

def _init_column_store() -> Dict[str, List[object]]: ...

def _flush_chunk(store: Dict[str, List[object]], writer: Any) -> None: ...

def _write_chanwb_parquet(
    source: Path,
    target: Path,
    *,
    start_year: Optional[int] = ...,
    calendar_lookup: Dict[int, List[Tuple[int, int]]] | None = ...,
    chunk_size: int = ...,
) -> None: ...

def run_wepp_watershed_chnwb_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
) -> Path: ...
