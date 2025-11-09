"""Watershed-scale water balance reporting sourced from totalwatsed3 parquet."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .report_base import ReportBase
from .row_data import RowData

__all__ = ["TotalWatbalReport", "TotalWatbal"]


class TotalWatbalReport(ReportBase):
    """Water balance summary derived from the totalwatsed3 interchange dataset."""

    _DATASET_REL_PATH = Path("wepp/output/interchange/totalwatsed3.parquet")
    _MEASURE_COLUMNS = OrderedDict(
        [
            ("Precipitation (mm)", "Precipitation"),
            ("Rain + Melt (mm)", "Rain+Melt"),
            ("Lateral Flow (mm)", "Lateral Flow"),
            ("ET (mm)", "ET"),
            ("Percolation (mm)", "Percolation"),
            ("Sed Del (kg)", "tdet"),
        ]
    )
    _RATIO_COLUMNS = {"Rain + Melt (mm)", "Lateral Flow (mm)", "ET (mm)", "Percolation (mm)"}

    def __init__(
        self,
        wd: str | Path,
        exclude_yr_indxs: Iterable[int] | None = None,
        *,
        dataframe: pd.DataFrame | None = None,
    ):
        base = Path(wd).expanduser()
        if not base.exists():
            raise FileNotFoundError(base)

        dataset_path = base / self._DATASET_REL_PATH
        if dataframe is None:
            if not dataset_path.exists():
                raise FileNotFoundError(dataset_path)
            columns = ["water_year", *self._MEASURE_COLUMNS.values()]
            table = pq.read_table(dataset_path, columns=columns)
            dataframe = table.to_pandas()

        self.exclude_yr_indxs = sorted({int(idx) for idx in (exclude_yr_indxs or [])})
        self._frame = dataframe.copy()

        if self._frame.empty:
            self._initialise_empty()
            return

        self._frame["water_year"] = self._frame["water_year"].astype(int)
        for column in self._MEASURE_COLUMNS.values():
            if column not in self._frame:
                self._frame[column] = 0.0
            self._frame[column] = self._frame[column].astype(float).fillna(0.0)

        self.years = sorted(self._frame["water_year"].unique().tolist())
        excluded_years = {
            self.years[idx] for idx in self.exclude_yr_indxs if 0 <= idx < len(self.years)
        }

        grouped = self._frame.groupby("water_year", sort=True)
        measures_template = {label: [] for label in self._MEASURE_COLUMNS}

        data_rows: list[OrderedDict[str, float]] = []
        for year in self.years:
            if year in excluded_years:
                continue
            subset = grouped.get_group(year)
            record = OrderedDict()
            record["WaterYear"] = int(year)
            for label, column in self._MEASURE_COLUMNS.items():
                value = float(subset[column].sum())
                record[label] = value
                measures_template[label].append(value)
            data_rows.append(record)

        self.header = ["Water Year", *self._MEASURE_COLUMNS.keys()]
        self.data = data_rows

        if not data_rows:
            self._initialise_empty()
            return

        self._means = self._build_summary_row("Mean", measures_template, np.mean)
        self._stdevs = self._build_summary_row("StdDev", measures_template, np.std)
        self._pratios = self._build_ratio_row(measures_template)

    def _initialise_empty(self) -> None:
        """Populate placeholder rows when the dataset is empty."""
        self.header = ["Water Year", *self._MEASURE_COLUMNS.keys()]
        self.data = []
        base = OrderedDict({"Water Year": "Mean"})
        for label in self._MEASURE_COLUMNS:
            base[label] = 0.0
        self._means = base.copy()
        self._means["Water Year"] = "Mean"
        self._stdevs = base.copy()
        self._stdevs["Water Year"] = "StdDev"

        ratio = OrderedDict({"Water Year": "{X}/P", "Precipitation (mm)": ""})
        for label in list(self._MEASURE_COLUMNS.keys())[1:]:
            ratio[label if label not in self._RATIO_COLUMNS else label.replace("(mm)", "(%)")] = ""  # type: ignore[index]
        self._pratios = ratio
        self.years = []

    def _build_summary_row(
        self,
        label: str,
        measures: dict[str, list[float]],
        reducer: Callable[[Iterable[float]], float],
    ) -> OrderedDict[str, float | str]:
        """Apply ``reducer`` to each measure list to create an aggregate row."""
        row = OrderedDict({"Water Year": label})
        for measure_label, values in measures.items():
            row[measure_label] = float(reducer(values)) if values else 0.0
        return row

    def _build_ratio_row(self, measures: dict[str, list[float]]) -> OrderedDict[str, float | str]:
        """Compute precipitation-normalized ratios for select measures."""
        ratios = OrderedDict({"Water Year": "{X}/P"})
        precip_values = measures.get("Precipitation (mm)", [])
        precip_sum = float(sum(precip_values)) if precip_values else 0.0
        ratios["Precipitation (mm)"] = ""

        for label in list(self._MEASURE_COLUMNS.keys())[1:]:
            values = measures.get(label, [])
            total = float(sum(values)) if values else 0.0
            if label in self._RATIO_COLUMNS and precip_sum > 0.0:
                ratios[label.replace("(mm)", "(%)")] = (total / precip_sum) * 100.0
            elif label in self._RATIO_COLUMNS:
                ratios[label.replace("(mm)", "(%)")] = 0.0
            else:
                ratios[label] = ""

        return ratios

    def __iter__(self) -> Iterator[RowData]:
        """Yield per-year ``RowData`` rows."""
        for row in self.data:
            yield RowData(row)

    @property
    def means(self) -> RowData:
        """Return the mean row as a ``RowData`` wrapper."""
        return RowData(self._means)

    @property
    def stdevs(self) -> RowData:
        """Return the standard-deviation row as a ``RowData`` wrapper."""
        return RowData(self._stdevs)

    @property
    def pratios(self) -> RowData:
        """Return the precipitation ratio row as a ``RowData`` wrapper."""
        return RowData(self._pratios)


# Backwards compatibility.
TotalWatbal = TotalWatbalReport
