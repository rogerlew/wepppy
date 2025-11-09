from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import pyarrow as pa


class ReportQueryContext:
    run_directory: Path
    run_interchange: bool
    auto_activate: bool

    def __init__(self, run_directory: Path, run_interchange: bool = ..., auto_activate: bool = ...) -> None: ...

    def activate(self) -> Any: ...

    @property
    def context(self) -> Any: ...

    @property
    def catalog(self) -> Any: ...

    def ensure_datasets(self, *dataset_paths: str) -> None: ...

    def query(self, payload: Any) -> Any: ...


class ReportCacheManager:
    def __init__(self, run_directory: Path | str, *, namespace: str | None = ...) -> None: ...

    @property
    def root(self) -> Path: ...

    def read_parquet(self, key: str, *, version: str | None = ..., **kwargs: Any) -> pd.DataFrame | None: ...

    def write_parquet(
        self,
        key: str,
        dataframe: pd.DataFrame,
        *,
        version: str | None = ...,
        **kwargs: Any,
    ) -> Path: ...

    def invalidate(self, key: str) -> None: ...


def extract_units_from_schema(
    schema: pa.Schema,
    column_mapping: Mapping[str, str | Sequence[str]],
    *,
    metadata_key: bytes = ...,
    default_unit: str | None = ...,
) -> dict[str, str]: ...
