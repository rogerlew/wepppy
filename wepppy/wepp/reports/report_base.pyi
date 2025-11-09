from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, TextIO

import pandas as pd

from .row_data import RowData


class ReportBase:
    header: list[str]

    def __iter__(self) -> Iterator[RowData]: ...

    @property
    def hdr(self) -> Iterator[str]: ...

    @property
    def units(self) -> Iterator[str | None]: ...

    @property
    def hdr_units_zip(self) -> Iterator[tuple[str, str | None]]: ...

    def write(
        self,
        fp: TextIO,
        write_header: bool = ...,
        run_descriptors: Sequence[tuple[str, str]] | None = ...,
    ) -> None: ...

    def to_dataframe(
        self,
        fp: str | Path | TextIO | None = ...,
        *,
        write_header: bool = ...,
        run_descriptors: Sequence[tuple[str, str]] | None = ...,
        **to_parquet_kwargs: Any,
    ) -> pd.DataFrame: ...
