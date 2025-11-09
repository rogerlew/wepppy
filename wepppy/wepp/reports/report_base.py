"""Shared helpers for producing consistently formatted WEPP report tables."""

from __future__ import annotations

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, TextIO

import pandas as pd

from .row_data import parse_name, parse_units


class ReportBase:
    """Base implementation that powers the tabular WEPP report adapters."""

    header: list[str] = []

    def __iter__(self) -> Iterator["RowData"]:
        """Subclasses must yield ``RowData`` instances in display order."""
        raise NotImplementedError

    @property
    def hdr(self) -> Iterator[str]:
        """Yield header names without inline unit suffixes."""
        for colname in self.header:
            yield parse_name(colname)

    @property
    def units(self) -> Iterator[str | None]:
        """Yield the parsed unit label for each column in ``header``."""
        for colname in self.header:
            yield parse_units(colname)

    @property
    def hdr_units_zip(self) -> Iterator[tuple[str, str | None]]:
        """Yield ``(name, units)`` tuples for convenience when rendering."""
        for colname in self.header:
            yield parse_name(colname), parse_units(colname)

    def write(
        self,
        fp: TextIO,
        write_header: bool = True,
        run_descriptors: Sequence[tuple[str, str]] | None = None,
    ) -> None:
        """Stream the report rows to ``fp`` using CSV formatting.

        Args:
            fp: Open text stream (for example ``Path.open("w")``) that accepts CSV data.
            write_header: When ``True`` the header row (including descriptor columns)
                is emitted before any data rows.
            run_descriptors: Optional ``[(name, value), ...]`` pairs to prepend to every row.

        """
        writer = csv.writer(fp)

        if write_header:
            header_row: list[str] = []
            for cname, units in zip(self.hdr, self.units):
                label = cname
                if units is not None:
                    unit = units.split(",")[0]
                    label = f"{label} ({unit})"
                header_row.append(label)

            if run_descriptors is not None:
                header_row = [cname for cname, _ in run_descriptors] + header_row

            writer.writerow(header_row)

        for row in self:
            data = [value for value, _ in row]
            if run_descriptors is not None:
                data = [desc for _, desc in run_descriptors] + data
            writer.writerow(data)

    def to_dataframe(
        self,
        fp: str | Path | TextIO | None = None,
        *,
        write_header: bool = True,
        run_descriptors: Sequence[tuple[str, str]] | None = None,
        **to_parquet_kwargs: Any,
    ) -> pd.DataFrame:
        """Return the report contents as a ``pandas`` DataFrame.

        Args:
            fp: Optional path or open buffer supplied to ``DataFrame.to_parquet``.
            write_header: When ``True`` descriptor columns are prepended to the DataFrame.
            run_descriptors: Optional ``[(name, value), ...]`` pairs added to each row.
            **to_parquet_kwargs: Additional keyword arguments forwarded to ``to_parquet``.

        Returns:
            ``pd.DataFrame`` containing the rendered report rows.
        """
        columns = list(self.header)
        records: list[dict[str, Any]] = []
        for row in self:
            values = [value for value, _ in row]
            if write_header and run_descriptors:
                descriptor_values = [v for _, v in run_descriptors]
                values = descriptor_values + values
            records.append(dict(zip(columns, values)))

        dataframe = pd.DataFrame(records, columns=columns)
        if fp is not None:
            dataframe.to_parquet(fp, **to_parquet_kwargs)
        return dataframe
