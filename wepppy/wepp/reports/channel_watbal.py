"""Channel-scale water-balance reporting backed by interchange parquet assets."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .helpers import extract_units_from_schema
from .report_base import ReportBase
from .row_data import RowData, parse_units


__all__ = ["ChannelWatbalReport", "ChannelWatbal"]


class ChannelWatbalReport(ReportBase):
    """Average annual channel water balance derived from interchange assets."""

    _DATASET_REL_PATH = Path("wepp/output/interchange/chnwb.parquet")
    _MEASURE_MAP = OrderedDict(
        [
            ("Precipitation (mm)", "precip_mm"),
            ("Streamflow (mm)", "streamflow_mm"),
            ("Transpiration + Evaporation (mm)", "transp_evap_mm"),
            ("Percolation (mm)", "percolation_mm"),
            ("Total Soil Water Storage (mm)", "soil_water_mm"),
            ("Baseflow (mm)", "baseflow_mm"),
        ]
    )
    _SOURCE_COLUMNS = {
        "precip_mm": "P (mm)",
        "streamflow_mm": "Q (mm)",
        "percolation_mm": "Dp (mm)",
        "soil_water_mm": "Total Soil Water (mm)",
        "baseflow_mm": "Base (mm)",
    }
    _TRANSPIRATION_COLUMNS = ["Ep (mm)", "Es (mm)", "Er (mm)"]

    def __init__(self, wd: str | Path):
        """Load the channel water-balance parquet and compute summary tables."""
        self.wd = Path(wd).expanduser()
        if not self.wd.exists():
            raise FileNotFoundError(self.wd)

        dataset_path = self.wd / self._DATASET_REL_PATH
        if not dataset_path.exists():
            raise FileNotFoundError(dataset_path)

        required_columns = (
            ["wepp_id", "water_year", "Area (m^2)"]
            + list(self._SOURCE_COLUMNS.values())
            + self._TRANSPIRATION_COLUMNS
        )

        table = pq.read_table(dataset_path, columns=required_columns)
        self._schema = table.schema
        dataframe = table.to_pandas()

        if dataframe.empty:
            self._avg_dataframe = pd.DataFrame(columns=["TopazID", *self._MEASURE_MAP.values()])
            self._watershed_yearly = pd.DataFrame(columns=["Year", *self._MEASURE_MAP.values()])
            self.areas = {}
            self.wsarea = 0.0
            self.years = []
            self.units_d = {label: "mm" for label in self._MEASURE_MAP}
            return

        dataframe = dataframe.copy()
        dataframe["transp_evap_mm"] = (
            dataframe["Ep (mm)"].astype(float).fillna(0.0)
            + dataframe["Es (mm)"].astype(float).fillna(0.0)
            + dataframe["Er (mm)"].astype(float).fillna(0.0)
        )

        aggregations = {
            "P (mm)": "sum",
            "Q (mm)": "sum",
            "transp_evap_mm": "sum",
            "Dp (mm)": "sum",
            "Total Soil Water (mm)": "sum",
            "Base (mm)": "sum",
            "Area (m^2)": "max",
        }

        aggregated = (
            dataframe.groupby(["wepp_id", "water_year"], as_index=False)
            .agg(aggregations)
            .rename(
                columns={
                    "P (mm)": "precip_mm",
                    "Q (mm)": "streamflow_mm",
                    "Dp (mm)": "percolation_mm",
                    "Total Soil Water (mm)": "soil_water_mm",
                    "Base (mm)": "baseflow_mm",
                }
            )
        )

        aggregated["wepp_id"] = aggregated["wepp_id"].astype(int)
        aggregated["water_year"] = aggregated["water_year"].astype(int)
        aggregated["Area (m^2)"] = aggregated["Area (m^2)"].astype(float).fillna(0.0)

        self.areas = (
            aggregated.groupby("wepp_id")["Area (m^2)"]
            .max()
            .to_dict()
        )
        self.wsarea = float(sum(self.areas.values()))
        self.years = sorted(aggregated["water_year"].unique().astype(int).tolist())

        self._avg_dataframe = (
            aggregated.groupby("wepp_id", as_index=False)[list(self._MEASURE_MAP.values())]
            .mean()
            .rename(columns={"wepp_id": "TopazID"})
            .sort_values("TopazID")
        )

        weighted = aggregated.copy()
        for column in self._MEASURE_MAP.values():
            weighted[column] = weighted[column] * weighted["Area (m^2)"]

        watershed = weighted.groupby("water_year")[list(self._MEASURE_MAP.values())].sum()
        if self.wsarea > 0.0:
            watershed = watershed / self.wsarea
        else:
            watershed.loc[:, :] = 0.0

        self._watershed_yearly = (
            watershed.reset_index()
            .rename(columns={"water_year": "Year"})
            .sort_values("Year")
        )

        column_mapping: dict[str, str | list[str]] = {}
        for label, column in self._MEASURE_MAP.items():
            if column == "transp_evap_mm":
                column_mapping[label] = self._TRANSPIRATION_COLUMNS
            else:
                column_mapping[label] = self._SOURCE_COLUMNS.get(column, column)
        self.units_d = extract_units_from_schema(self._schema, column_mapping, default_unit="mm")

    @property
    def header(self) -> list[str]:
        """Return the ordered set of watershed-level measure labels."""
        return list(self._MEASURE_MAP.keys())

    @property
    def avg_annual_header(self) -> list[str]:
        """Include the Topaz identifier ahead of the per-channel measures."""
        return ["TopazID"] + list(self.header)

    @property
    def avg_annual_units(self) -> list[str | None]:
        """Return the display units aligned with :pyattr:`avg_annual_header`."""
        return [None] + [parse_units(label) for label in self.header]

    @property
    def yearly_header(self) -> list[str]:
        """Include the calendar year ahead of the watershed measures."""
        return ["Year"] + list(self.header)

    @property
    def yearly_units(self) -> list[str | None]:
        """Return the display units aligned with :pyattr:`yearly_header`."""
        return [None] + [parse_units(label) for label in self.header]

    def avg_annual_iter(self) -> Iterator[RowData]:
        """Yield per-channel average annual metrics as ``RowData`` objects."""
        for _, row in self._avg_dataframe.iterrows():
            record = OrderedDict()
            record["TopazID"] = int(row["TopazID"])
            for label, column in self._MEASURE_MAP.items():
                record[label] = float(row.get(column, 0.0))
            yield RowData(record)

    def yearly_iter(self) -> Iterator[RowData]:
        """Yield watershed-wide yearly metrics (weighted by channel area)."""
        for _, row in self._watershed_yearly.iterrows():
            record = OrderedDict()
            record["Year"] = int(row["Year"])
            for label, column in self._MEASURE_MAP.items():
                record[label] = float(row.get(column, 0.0))
            yield RowData(record)


# Backwards compatibility for callers still importing ChannelWatbal.
ChannelWatbal = ChannelWatbalReport
