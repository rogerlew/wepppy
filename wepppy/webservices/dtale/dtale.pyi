from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from flask import Flask, Response

from wepppy.microservices.parquet_filters import CompiledParquetFilter


logger: logging.Logger
HOST: str
PORT: int
SITE_PREFIX: Optional[str]
APP_ROOT: Optional[str]
IS_PROXY: bool
DTALE_BASE_URL: str
DTALE_INTERNAL_TOKEN: str
MAX_FILE_MB: float
MAX_ROWS: int
ALLOW_CELL_EDITS: bool
DTALE_THEME: str
DATASETS: Dict[str, "DatasetMeta"]
LAZY_PARQUET_DATASETS: Dict[str, "LazyParquetDtaleInstance"]
REGISTERED_GEOJSON: Dict[str, str]
MAP_DEFAULTS: Dict[str, Dict[str, object]]
MAP_CHOICES: Dict[str, List[Tuple[str, str, Optional[str]]]]
_IDENTIFIER_STRING_ALIASES: Tuple[Tuple[str, str], ...]
app: Flask
__all__: List[str]

__all__ = ["app"]


DtaleData = Any


@dataclass
class DatasetMeta:
    path: Path
    fingerprint: str
    name: str
    last_loaded: float


def _clean_prefix(value: Optional[str]) -> Optional[str]: ...


def _fingerprint(path: Path) -> str: ...


def _is_parquet_path(path: Path) -> bool: ...


def _quote_identifier(name: str) -> str: ...


def _make_dataset_id(runid: str, config: str, rel_path: str) -> str: ...


def _resolve_target(runid: str, rel_path: str, *, config: Optional[str] = ...) -> Tuple[Path, Path]: ...


def _normalize_rel(rel_path: str) -> str: ...


def _load_geojson(path: Path) -> Optional[dict]: ...


def _infer_featureidkey(properties: Iterable[str], preferred: Optional[Iterable[str]] = ...) -> Optional[str]: ...


def _register_geojson_asset(
    runid: str,
    slug: str,
    path: Path | str | None,
    *,
    data_id: Optional[str] = ...,
    label: Optional[str] = ...,
    preferred_keys: Optional[Iterable[str]] = ...,
    make_default: bool = ...,
    loc_candidates: Optional[Iterable[str]] = ...,
    property_aliases: Optional[Iterable[Tuple[str, str]]] = ...,
) -> Tuple[Optional[str], Optional[str]]: ...


def _ensure_geojson_assets(runid: str, wd: Path, data_id: Optional[str]) -> None: ...


def _postprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame: ...


def _read_feather(path: Path) -> pd.DataFrame: ...


def _read_csv(path: Path, *, sep: str = ..., compression: Optional[str] = ...) -> pd.DataFrame: ...


def _read_pickle(path: Path) -> pd.DataFrame: ...


READERS: Dict[str, Callable[[Path], pd.DataFrame]]


def _load_dataframe(path: Path) -> pd.DataFrame: ...


class LazyParquetDtaleInstance:
    def __init__(self, path: Path, *, compiled_filter: Optional[CompiledParquetFilter] = ...) -> None: ...
    @property
    def base_columns(self) -> List[str]: ...
    @property
    def alias_to_source(self) -> Dict[str, str]: ...
    def rows(self, **kwargs: Any) -> int: ...
    @property
    def base_df(self) -> pd.DataFrame: ...
    @property
    def is_large(self) -> bool: ...
    @property
    def data(self) -> pd.DataFrame: ...
    def load_data(
        self,
        row_range: Optional[List[int] | Tuple[int, int]] = ...,
        columns: Optional[Iterable[str]] = ...,
        sort: Optional[List[Any]] = ...,
        **kwargs: Any,
    ) -> pd.DataFrame: ...


def _initialize_lazy_parquet_dataset(
    data_id: str,
    display_name: str,
    path: Path,
    *,
    compiled_filter: Optional[CompiledParquetFilter] = ...,
) -> DtaleData: ...


def _initialize_dtale_dataset(data_id: str, display_name: str, df: pd.DataFrame) -> DtaleData: ...


def health() -> Response: ...


def _verify_token() -> None: ...


def _build_instance_response(data_id: str, instance: DtaleData, meta: DatasetMeta) -> Response: ...


def load_into_dtale() -> Response: ...
