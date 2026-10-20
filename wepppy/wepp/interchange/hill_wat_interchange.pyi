from __future__ import annotations

from logging import Logger
from pathlib import Path
from typing import Any

LOGGER: Logger
CANONICAL_COLUMN_ALIASES: dict[str, tuple[str, ...]]
DAILY_MM_COLUMNS: tuple[str, ...]
PANDAS_TYPE_MAP: dict[str, Any]
SCHEMA: Any
WAT_OPTIONAL_COLUMN_NAMES: list[str]

def run_wepp_hillslope_wat_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = ...,
    max_workers: int | None = ...,
) -> Path: ...

def load_hill_wat_dataframe(
    wepp_output_dir: Path | str,
    wepp_id: int,
    *,
    collapse: str | None = ...,
    _source_fingerprint_cache: dict | None = ...,
) -> Any: ...
