from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class CatalogEntry:
    path: str
    extension: str
    size_bytes: int
    modified: str
    schema: Optional[Dict[str, object]] = None


class DatasetCatalog:
    def __init__(self, root: Path, entries: List[CatalogEntry]) -> None:
        self.root = root
        self._entries = entries
        self._by_path = {entry.path: entry for entry in entries}

    @classmethod
    def load(cls, catalog_path: Path) -> "DatasetCatalog":
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        root = Path(data["root"])
        entries = [CatalogEntry(**item) for item in data.get("files", [])]
        return cls(root, entries)

    def get(self, rel_path: str) -> CatalogEntry | None:
        return self._by_path.get(rel_path)

    def entries(self) -> List[CatalogEntry]:
        return list(self._entries)

    def has(self, rel_path: str) -> bool:
        return rel_path in self._by_path


def load_catalog(base: Path) -> DatasetCatalog:
    catalog_path = base / "_query_engine" / "catalog.json"
    if not catalog_path.exists():
        raise FileNotFoundError(catalog_path)
    return DatasetCatalog.load(catalog_path)
