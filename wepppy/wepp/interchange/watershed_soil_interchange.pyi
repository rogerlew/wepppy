from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

SOIL_FILENAME: str
SOIL_PARQUET: str
CHUNK_SIZE: int
RAW_HEADER: List[str]
LEGACY_HEADER: List[str]
MEASUREMENT_COLUMNS: List[str]
LEGACY_MEASUREMENT_COLUMNS: List[str]
SCHEMA: Any

def _init_column_store() -> Dict[str, List[object]]: ...

def _flush_chunk(store: Dict[str, List[object]], writer: Any) -> None: ...

def _write_soil_parquet(
    source: Path,
    target: Path,
    *,
    chunk_size: int = ...,
    calendar_lookup: Dict[int, List[Tuple[int, int]]] | None = ...,
) -> None: ...

def run_wepp_watershed_soil_interchange(wepp_output_dir: Path | str) -> Path: ...
