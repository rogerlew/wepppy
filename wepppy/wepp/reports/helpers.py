from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import pyarrow as pa

from wepppy.query_engine import (
    activate_query_engine,
    resolve_run_context,
    run_query,
    update_catalog_entry,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportQueryContext:
    """Lightweight helper that wraps the query engine bootstrap for reports.

    This ensures we only pay the activation cost once per report and provides
    convenience helpers for catalog checks and query execution.
    """

    run_directory: Path
    run_interchange: bool = False
    auto_activate: bool = True
    _context: Any | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.run_directory = Path(self.run_directory).expanduser()
        if not self.run_directory.exists():
            raise FileNotFoundError(self.run_directory)
        if self.auto_activate:
            self.activate()

    def activate(self):
        if self._context is None:
            activate_query_engine(self.run_directory, run_interchange=self.run_interchange)
            self._context = resolve_run_context(str(self.run_directory), auto_activate=False)
        return self._context

    @property
    def context(self):
        return self.activate()

    @property
    def catalog(self):
        return self.context.catalog

    def ensure_datasets(self, *dataset_paths: str) -> None:
        missing = [path for path in dataset_paths if not self.catalog.has(path)]
        if missing:
            refreshed = False
            for path in missing:
                dataset = Path(self.run_directory, path)
                if dataset.exists():
                    try:
                        update_catalog_entry(self.run_directory, path)
                        refreshed = True
                    except Exception:  # pragma: no cover - best effort catalog repair
                        LOGGER.warning(
                            "Failed to refresh catalog entry for %s under %s",
                            path,
                            self.run_directory,
                            exc_info=True,
                        )
            if refreshed:
                self._context = None
                missing = [path for path in dataset_paths if not self.catalog.has(path)]
        if missing:
            formatted = ", ".join(sorted(missing))
            raise FileNotFoundError(f"Missing dataset(s) for report {formatted}")

    def query(self, payload):
        return run_query(self.context, payload)


class ReportCacheManager:
    """Centralises cache path management and versioned parquet IO for reports."""

    def __init__(self, run_directory: Path | str, *, namespace: str | None = None):
        base = Path(run_directory).expanduser()
        if not base.exists():
            raise FileNotFoundError(base)
        cache_root = base / "wepp" / "reports" / "cache"
        if namespace:
            namespace = namespace.strip("/ ")
            if namespace:
                cache_root /= namespace
        self._root = cache_root

    @property
    def root(self) -> Path:
        return self._root

    def _path_for(self, key: str) -> tuple[Path, Path]:
        safe_key = key.replace("/", "_")
        data_path = self._root / f"{safe_key}.parquet"
        meta_path = self._root / f"{safe_key}.meta.json"
        return data_path, meta_path

    def read_parquet(self, key: str, *, version: str | None = None, **kwargs) -> pd.DataFrame | None:
        data_path, meta_path = self._path_for(key)
        if not data_path.exists():
            return None
        if version is not None:
            metadata = self._read_metadata(meta_path)
            if metadata.get("version") != version:
                return None
        return pd.read_parquet(data_path, **kwargs)

    def write_parquet(
        self,
        key: str,
        dataframe: pd.DataFrame,
        *,
        version: str | None = None,
        **kwargs,
    ) -> Path:
        data_path, meta_path = self._path_for(key)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_parquet(data_path, **kwargs)
        if version is not None:
            meta = {"version": version}
            meta_path.write_text(json.dumps(meta, indent=2))
        return data_path

    def invalidate(self, key: str) -> None:
        data_path, meta_path = self._path_for(key)
        for path in (data_path, meta_path):
            if path.exists():
                path.unlink()

    @staticmethod
    def _read_metadata(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}


def extract_units_from_schema(
    schema: pa.Schema,
    column_mapping: Mapping[str, str | Sequence[str]],
    *,
    metadata_key: bytes = b"units",
    default_unit: str | None = None,
) -> dict[str, str]:
    """Extract display label → units mapping using parquet field metadata."""
    units: dict[str, str] = {}
    for label, columns in column_mapping.items():
        if isinstance(columns, str):
            columns = (columns,)
        unit_value: str | None = None
        for column in columns:
            try:
                field = schema.field(column)
            except KeyError:
                continue
            metadata = field.metadata or {}
            raw = metadata.get(metadata_key)
            if raw:
                unit_value = raw.decode("utf-8")
                break
        units[label] = unit_value or (default_unit or "")
    return units
