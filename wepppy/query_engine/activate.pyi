from __future__ import annotations

from pathlib import Path
from collections.abc import Callable, Iterable

def activate_query_engine(
    wd: str | Path,
    *,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
    mutation_checkpoint: Callable[[], None] | None = ...,
) -> dict[str, object]: ...

def update_catalog_entry(wd: str | Path, asset_path: str) -> dict[str, object] | None: ...

# Internal collaborators are declared because catalog_refresh shares these primitives.
from typing import Any
SUPPORTED_EXTENSIONS: tuple[str, ...]
def _build_catalog(base: Path) -> list[dict[str, Any]]: ...
def _build_catalog_subset(base: Path, directory: Path) -> list[dict[str, Any]]: ...
def _build_entry(base: Path, path: Path, *, base_len: int | None = ..., catalog_path: str | None = ...) -> dict[str, Any] | None: ...
def _is_allowed_target(base: Path, target: Path) -> bool: ...

import logging
LOGGER: logging.Logger
GEO_SCHEMA_EXTENSIONS: tuple[str, ...]
PASS_FAMILY_HBP: str
PASS_FAMILY_LEGACY_ASCII: str
READONLY_SENTINEL: str

def _normalize_relative_parts(path: Path) -> tuple[str, ...]: ...

def _read_parquet_schema(path: Path) -> dict[str, Any] | None: ...
