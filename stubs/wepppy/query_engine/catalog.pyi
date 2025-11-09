from __future__ import annotations

from pathlib import Path
from typing import Any

class CatalogEntry:
    path: str
    extension: str
    size_bytes: int
    modified: str
    schema: dict[str, Any] | None

class DatasetCatalog:
    root: Path

    def __init__(self, root: Path, entries: list[CatalogEntry]) -> None: ...
    @classmethod
    def load(cls, catalog_path: Path) -> DatasetCatalog: ...
    def get(self, rel_path: str) -> CatalogEntry | None: ...
    def entries(self) -> list[CatalogEntry]: ...
    def has(self, rel_path: str) -> bool: ...
    def get_column_type(self, rel_path: str, column: str) -> str | None: ...

def load_catalog(base: Path) -> DatasetCatalog: ...
