"""Lightweight helpers for formatting WEPP report column metadata."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Mapping


def parse_name(colname: str) -> str:
    """Return the column label stripped of any trailing unit suffix."""
    units = parse_units(colname)
    if units is None:
        return colname

    return colname.replace(f"({units})", "").strip()


def parse_units(colname: str) -> str | None:
    """Extract the measurement units from a column label if present."""
    try:
        colsplit = colname.strip().split()
        if len(colsplit) < 2:
            return None

        if "(" in colsplit[-1]:
            return colsplit[-1].replace("(", "").replace(")", "")

        return None
    except IndexError:
        return None


class RowData:
    """Iterator wrapper that yields value/unit tuples for report rows."""

    def __init__(self, row: Mapping[str, Any]):
        """Store the mapping that backs the row."""
        self.row: Mapping[str, Any] = row

    def __getitem__(self, item: str) -> Any:
        """Return the value whose column name begins with the requested prefix."""
        for colname in self.row:
            if colname.startswith(item):
                return self.row[colname]

        raise KeyError(item)

    def __iter__(self) -> Iterator[tuple[Any, str | None]]:
        """Yield ``(value, units)`` pairs in the original column order."""
        for colname in self.row:
            value = self.row[colname]
            units = parse_units(colname)
            yield value, units
