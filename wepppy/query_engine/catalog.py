"""In-memory representation of the query-engine catalog JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Canonical logical dataset ids and their legacy WD-level sidecar aliases.
_DATASET_PATH_ALIASES: dict[str, str] = {
    "landuse/landuse.parquet": "landuse.parquet",
    "soils/soils.parquet": "soils.parquet",
    "watershed/hillslopes.parquet": "watershed.hillslopes.parquet",
    "watershed/channels.parquet": "watershed.channels.parquet",
    "watershed/flowpaths.parquet": "watershed.flowpaths.parquet",
    "climate/wepp_cli.parquet": "climate.wepp_cli.parquet",
}
_DATASET_PATH_ALIAS_LOOKUP: dict[str, str] = {
    **_DATASET_PATH_ALIASES,
    **{legacy: logical for logical, legacy in _DATASET_PATH_ALIASES.items()},
}


def _normalize_catalog_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def resolve_dataset_path_alias(rel_path: str, *, available_paths: set[str]) -> str | None:
    """Resolve a dataset path to a catalog key, honoring legacy aliases.

    Args:
        rel_path: Requested dataset path.
        available_paths: Catalog keys currently available.

    Returns:
        Matching catalog key, or None when no exact/alias match exists.
    """
    normalized = _normalize_catalog_path(rel_path)
    if normalized in available_paths:
        return normalized

    alias = _DATASET_PATH_ALIAS_LOOKUP.get(normalized)
    if alias is not None and alias in available_paths:
        return alias

    return None


@dataclass(slots=True)
class CatalogEntry:
    """Metadata describing a single dataset entry within the catalog."""

    path: str
    extension: str
    size_bytes: int
    modified: str
    # Optional on-disk pointer when the catalog path is a logical id (e.g.,
    # `landuse/landuse.parquet`) but the file lives elsewhere (e.g., WD sidecar
    # `landuse.parquet`). Relative paths are resolved against `DatasetCatalog.root`.
    fs_path: str | None = None
    schema: dict[str, object] | None = None


class DatasetCatalog:
    """Lightweight helper for interrogating catalog entries."""

    def __init__(self, root: Path, entries: list[CatalogEntry]) -> None:
        self.root = root
        self._entries = entries
        self._by_path = {entry.path: entry for entry in entries}
        self._available_paths = set(self._by_path)

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
        resolved_path = resolve_dataset_path_alias(rel_path, available_paths=self._available_paths)
        if resolved_path is None:
            return None
        return self._by_path.get(resolved_path)

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
            True when the path is cataloged, False otherwise.
        """
        return resolve_dataset_path_alias(rel_path, available_paths=self._available_paths) is not None

    def get_column_type(self, rel_path: str, column: str) -> str | None:
        """Return the stringified column type for the requested dataset path.

        Args:
            rel_path: Cataloged dataset relative path.
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
