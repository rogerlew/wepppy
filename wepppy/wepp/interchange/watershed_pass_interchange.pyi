from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Tuple

PASS_FILENAME: str
EVENTS_PARQUET: str
METADATA_PARQUET: str
EVENT_CHUNK_SIZE: int

def _parse_float(token: str) -> float: ...

def _julian_to_calendar(year: int, julian: int) -> Tuple[int, int]: ...

def _parse_metadata(header_lines: List[str]) -> Tuple[Dict[str, object], Any, int, List[int], int]: ...

def _build_event_columns(npart: int) -> Tuple[List[str], List[str], List[str]]: ...

def _build_event_schema(npart: int, meta: Dict[str, object], nhill: int) -> Any: ...

def _init_event_store(column_names: Iterable[str]) -> Dict[str, List[object]]: ...

def _flush_event_store(store: Dict[str, List[object]], writer: Any) -> None: ...

def _write_events_parquet(
    line_iter: Iterator[str],
    hillslope_ids: List[int],
    nhill: int,
    npart: int,
    global_meta: Dict[str, object],
    target: Path,
    *,
    chunk_size: int = ...,
) -> None: ...

def _parse_pass_file(stream: Any) -> Tuple[Dict[str, object], Any, int, List[int], int, Iterator[str]]: ...

def run_wepp_watershed_pass_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]: ...
