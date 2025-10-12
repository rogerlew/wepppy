from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd
import pyarrow.parquet as pq

from .helpers import ReportCacheManager
from .report_base import ReportBase
from .row_data import RowData, parse_units

__all__ = ["HillslopeWatbalReport", "HillslopeWatbal"]


class HillslopeWatbalReport(ReportBase):
    """Average annual hillslope water balance derived from interchange assets."""

    _SOURCE_REL_PATH = Path("wepp/output/interchange/H.wat.parquet")
    _CACHE_KEY = "hillslope_watbal_summary"
    _CACHE_VERSION = "1"
    _MEASURE_MAP = OrderedDict(
        [
            ("Precipitation (mm)", "precip_mm"),
            ("Percolation (mm)", "percolation_mm"),
            ("Surface Runoff (mm)", "surface_runoff_mm"),
            ("Lateral Flow (mm)", "lateral_flow_mm"),
            ("Transpiration + Evaporation (mm)", "transp_evap_mm"),
        ]
    )

    def __init__(self, wd: str | Path):
        self.wd = Path(wd).expanduser()
        if not self.wd.exists():
            raise FileNotFoundError(self.wd)

        cache = ReportCacheManager(self.wd)
        dataframe = cache.read_parquet(self._CACHE_KEY, version=self._CACHE_VERSION)

        if dataframe is None or not self._validate_cache_columns(dataframe):
            dataframe = self._build_summary()
            cache.write_parquet(self._CACHE_KEY, dataframe, version=self._CACHE_VERSION, index=False)

        if dataframe.empty:
            self._initialise_empty()
            return

        self._per_hill_year = dataframe
        self.years = sorted(dataframe["WaterYear"].unique().astype(int).tolist())
        self.areas = (
            dataframe.groupby("TopazID")["Area_m2"]
            .max()
            .to_dict()
        )
        self.wsarea = float(sum(self.areas.values()))
        self.header = list(self._MEASURE_MAP.keys())
        self.units_d = {label: "mm" for label in self.header}

        self._per_hill_avg = (
            dataframe.groupby("TopazID")[list(self._MEASURE_MAP.keys())]
            .mean()
            .reset_index()
        )

        weighted = dataframe.copy()
        for label in self._MEASURE_MAP:
            weighted[label] = weighted[label] * weighted["Area_m2"]

        watershed = (
            weighted.groupby("WaterYear")[list(self._MEASURE_MAP.keys())]
            .sum()
        )
        if self.wsarea > 0.0:
            watershed = watershed / self.wsarea
        else:
            watershed.loc[:, :] = 0.0

        self._watershed_yearly = (
            watershed.reset_index()
            .sort_values("WaterYear")
        )

    def _validate_cache_columns(self, dataframe: pd.DataFrame) -> bool:
        expected = {"TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()}
        return expected.issubset(set(dataframe.columns))

    def _initialise_empty(self) -> None:
        self._per_hill_year = pd.DataFrame(columns=["TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()])
        self._per_hill_avg = self._per_hill_year.iloc[0:0]
        self._watershed_yearly = pd.DataFrame(columns=["WaterYear", *self._MEASURE_MAP.keys()])
        self.header = list(self._MEASURE_MAP.keys())
        self.units_d = {label: "mm" for label in self.header}
        self.areas = {}
        self.wsarea = 0.0
        self.years = []

    def _build_summary(self) -> pd.DataFrame:
        source_path = self.wd / self._SOURCE_REL_PATH
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        from wepppy.nodb.core import Watershed

        table = pq.read_table(
            source_path,
            columns=[
                "wepp_id",
                "ofe_id",
                "water_year",
                "P",
                "Dp",
                "QOFE",
                "latqcc",
                "Ep",
                "Es",
                "Er",
                "Area",
            ],
        )
        frame = table.to_pandas()
        if frame.empty:
            return pd.DataFrame(columns=["TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()])

        watershed = Watershed.getInstance(str(self.wd))
        translator = watershed.translator_factory()

        frame["TopazID"] = frame["wepp_id"].astype(int).apply(lambda wepp_id: translator.top(wepp=wepp_id))
        frame["P"] = frame["P"].astype(float).fillna(0.0)
        frame["Dp"] = frame["Dp"].astype(float).fillna(0.0)
        frame["QOFE"] = frame["QOFE"].astype(float).fillna(0.0)
        frame["latqcc"] = frame["latqcc"].astype(float).fillna(0.0)
        frame["Ep"] = frame["Ep"].astype(float).fillna(0.0)
        frame["Es"] = frame["Es"].astype(float).fillna(0.0)
        frame["Er"] = frame["Er"].astype(float).fillna(0.0)
        frame["Area"] = frame["Area"].astype(float).fillna(0.0)
        frame["water_year"] = frame["water_year"].astype(int)

        area_lookup = (
            frame.groupby(["wepp_id", "ofe_id"])["Area"]
            .first()
            .groupby("wepp_id")
            .sum()
        )

        topaz_area: dict[int, float] = {}
        for wepp_id, area in area_lookup.items():
            topaz_id = translator.top(wepp=wepp_id)
            topaz_area[topaz_id] = topaz_area.get(topaz_id, 0.0) + float(area)

        grouped = frame.groupby(["TopazID", "water_year"], as_index=False).agg(
            {
                "P": "sum",
                "Dp": "sum",
                "QOFE": "sum",
                "latqcc": "sum",
                "Ep": "sum",
                "Es": "sum",
                "Er": "sum",
            }
        )

        grouped["Area_m2"] = grouped["TopazID"].map(topaz_area).fillna(0.0)
        grouped = grouped.rename(columns={"water_year": "WaterYear"})
        grouped["Precipitation (mm)"] = grouped["P"]
        grouped["Percolation (mm)"] = grouped["Dp"]
        grouped["Surface Runoff (mm)"] = grouped["QOFE"]
        grouped["Lateral Flow (mm)"] = grouped["latqcc"]
        grouped["Transpiration + Evaporation (mm)"] = grouped["Ep"] + grouped["Es"] + grouped["Er"]

        summary = grouped[["TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()]].copy()
        summary.sort_values(["TopazID", "WaterYear"], inplace=True)
        return summary

    @property
    def header(self) -> list[str]:
        return getattr(self, "_header", list(self._MEASURE_MAP.keys()))

    @header.setter
    def header(self, value: Iterable[str]) -> None:
        self._header = list(value)

    @property
    def avg_annual_header(self) -> list[str]:
        return ["TopazID"] + list(self.header)

    @property
    def avg_annual_units(self) -> list[str | None]:
        return [None] + [parse_units(label) for label in self.header]

    @property
    def yearly_header(self) -> list[str]:
        return ["Year"] + list(self.header)
    @property
    def yearly_units(self) -> list[str | None]:
        return [None] + [parse_units(label) for label in self.header]

    def avg_annual_iter(self):
        if self._per_hill_year.empty:
            return iter(())

        num_years = len(self.years)
        divisor = max(num_years - 1, 1)

        for topaz_id, group in self._per_hill_year.groupby("TopazID"):
            record = OrderedDict({"TopazID": int(topaz_id)})
            for label in self.header:
                total = float(group[label].sum())
                record[label] = total / divisor
            yield RowData(record)

    def yearly_iter(self):
        if self._watershed_yearly.empty:
            return iter(())

        for _, row in self._watershed_yearly.iterrows():
            record = OrderedDict()
            record["Year"] = int(row["WaterYear"])
            for label in self.header:
                record[label] = float(row.get(label, 0.0))
            yield RowData(record)


# Backwards compatibility.
HillslopeWatbal = HillslopeWatbalReport
