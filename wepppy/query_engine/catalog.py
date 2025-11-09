"""In-memory representation of the query-engine catalog JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CatalogEntry:
    """Metadata describing a single dataset entry within the catalog."""

    path: str
    extension: str
    size_bytes: int
    modified: str
    schema: dict[str, object] | None = None


class DatasetCatalog:
    """Lightweight helper for interrogating catalog entries."""

    def __init__(self, root: Path, entries: list[CatalogEntry]) -> None:
        self.root = root
        self._entries = entries
        self._by_path = {entry.path: entry for entry in entries}

    @classmethod
    def load(cls, catalog_path: Path) -> "DatasetCatalog":
        """Load a catalog JSON file from disk.

        Args:
            catalog_path: Path to `_query_engine/catalog.json`.

        Returns:
            Instantiated DatasetCatalog pointing at the same root directory.
        """
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        root = Path(data["root"])
        entries = [CatalogEntry(**item) for item in data.get("files", [])]
        return cls(root, entries)

    def get(self, rel_path: str) -> CatalogEntry | None:
        """Return the catalog entry for a relative path, if present.

        Args:
            rel_path: File path relative to `self.root`.

        Returns:
            The CatalogEntry if the path exists, otherwise None.
        """
        return self._by_path.get(rel_path)

    def entries(self) -> list[CatalogEntry]:
        """Return a copy of the catalog entries.

        Returns:
            A list containing shallow copies of CatalogEntry objects.
        """
        return list(self._entries)

    def has(self, rel_path: str) -> bool:
        """Return True when the given relative path exists in the catalog.

        Args:
            rel_path: File path relative to `self.root`.

        Returns:
            True when the path is catalogued, False otherwise.
        """
        return rel_path in self._by_path

    def get_column_type(self, rel_path: str, column: str) -> str | None:
        """Return the stringified column type for the requested dataset path.

        Args:
            rel_path: Catalogued dataset relative path.
            column: Column name to look up.

        Returns:
            The type string if the column metadata exists, else None.
        """
        entry = self.get(rel_path)
        if entry is None or not entry.schema:
            return None
        fields = entry.schema.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict) and field.get("name") == column:
                    return str(field.get("type"))
        return None


def load_catalog(base: Path) -> DatasetCatalog:
    """Load the `_query_engine/catalog.json` file under a run directory.

    Args:
        base: Base path for the WEPP run.

    Returns:
        DatasetCatalog loaded from disk.

    Raises:
        FileNotFoundError: If the expected catalog file is missing.
    """
    catalog_path = base / "_query_engine" / "catalog.json"
    if not catalog_path.exists():
        raise FileNotFoundError(catalog_path)
    return DatasetCatalog.load(catalog_path)
