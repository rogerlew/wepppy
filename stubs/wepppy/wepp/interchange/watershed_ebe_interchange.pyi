from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

EBE_FILENAME: str
EBE_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any
MEASUREMENT_COLUMNS: List[str]

def _init_column_store() -> Dict[str, List[object]]: ...

def _flush_chunk(store: Dict[str, List[object]], writer: Any) -> None: ...

def _write_ebe_parquet(
    source: Path,
    target: Path,
    *,
    start_year: Optional[int] = ...,
    chunk_size: int = ...,
    legacy_element_id: Optional[int] = ...,
) -> None: ...

def _collect_hillslope_wepp_ids(base: Path) -> Set[int]: ...

def _infer_outlet_element_id(base: Path) -> Optional[int]: ...

def run_wepp_watershed_ebe_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
) -> Path: ...
