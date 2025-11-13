from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

CHAN_PEAK_FILENAME: str
CHAN_PEAK_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any

def _init_column_store() -> Dict[str, List[object]]: ...

def _flush_chunk(store: Dict[str, List[object]], writer: Any) -> None: ...

def _write_chan_peak_parquet(
    source: Path,
    target: Path,
    *,
    start_year: Optional[int] = ...,
    chunk_size: int = ...,
) -> None: ...

def run_wepp_watershed_chan_peak_interchange(
    wepp_output_dir: Path | str,
    *,
    start_year: Optional[int] = ...,
) -> Path: ...

def chanout_dss_export(
    wd: Path | str,
    status_channel: Optional[str] = ...,
    *,
    start_date: date | None = ...,
    end_date: date | None = ...,
) -> None: ...
