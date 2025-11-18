from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

CalendarLookup = Dict[int, List[Tuple[int, int]]]

def _wait_for_path(path: Path | str, timeout: float = ..., poll: float = ...) -> None: ...

def _parse_float(token: str) -> float: ...

def _julian_to_calendar(year: int, julian: int, *, calendar_lookup: Optional[CalendarLookup] = ...) -> Tuple[int, int]: ...

def _calendar_day_to_julian(
    year: int,
    month: int,
    day_of_month: int,
    *,
    calendar_lookup: Optional[CalendarLookup] = ...,
) -> int: ...

def _compute_sim_day_index(
    year: int,
    julian: int,
    *,
    start_year: int,
    calendar_lookup: Optional[CalendarLookup] = ...,
) -> int: ...

def _ensure_cli_parquet(
    cli_dir: Path,
    *,
    cli_file_hint: Optional[str] = ...,
    log: Optional[object] = ...,
) -> Optional[Path]: ...

def _build_cli_calendar_lookup(
    wepp_output_dir: Path,
    *,
    climate_files: Optional[Sequence[str]] = ...,
    log: Optional[object] = ...,
) -> CalendarLookup: ...
