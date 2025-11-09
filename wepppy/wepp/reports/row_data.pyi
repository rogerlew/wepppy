from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Mapping


def parse_name(colname: str) -> str: ...


def parse_units(colname: str) -> str | None: ...


class RowData:
    row: Mapping[str, Any]

    def __init__(self, row: Mapping[str, Any]) -> None: ...

    def __getitem__(self, item: str) -> Any: ...

    def __iter__(self) -> Iterator[tuple[Any, str | None]]: ...
