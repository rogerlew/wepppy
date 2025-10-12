from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from wepppy.query_engine.payload import QueryRequest

from .helpers import ReportCacheManager, ReportQueryContext
from .report_base import ReportBase
from .row_data import RowData

__all__ = ["AverageAnnualsByLanduseReport", "AverageAnnualsByLanduse"]


class AverageAnnualsByLanduseReport(ReportBase):
    """Summarise average annual hydrologic metrics per landuse using query-engine assets."""

    _CACHE_KEY = "average_annuals_by_landuse"
    _CACHE_VERSION = "1"
    _LOSS_DATASET = "wepp/output/interchange/loss_pw0.hill.parquet"
    _HILLSLOPE_DATASET = "watershed/hillslopes.parquet"
    _LANDUSE_DATASET = "landuse/landuse.parquet"

    _DISPLAY_COLUMNS = [
        "Landuse ID",
        "Management Description",
        "Landuse Area (ha)",
        "Avg Runoff Depth (mm/yr)",
        "Avg Lateral Flow Depth (mm/yr)",
        "Avg Baseflow Depth (mm/yr)",
        "Avg Soil Loss (kg/yr)",
        "Avg Sediment Yield (kg/yr)",
        "Avg Sediment Deposition (kg/yr)",
    ]

    def __init__(self, wd: str | Path):
        self.wd = Path(wd).expanduser()
        if not self.wd.exists():
            raise FileNotFoundError(self.wd)

        cache = ReportCacheManager(self.wd)
        dataframe = cache.read_parquet(self._CACHE_KEY, version=self._CACHE_VERSION)

        if dataframe is None or list(dataframe.columns) != self._DISPLAY_COLUMNS:
            dataframe = self._build_dataframe()
            cache.write_parquet(self._CACHE_KEY, dataframe, version=self._CACHE_VERSION, index=False)

        self._dataframe = dataframe
        self.header = dataframe.columns.tolist()

    def _build_dataframe(self) -> pd.DataFrame:
        context = ReportQueryContext(self.wd, run_interchange=False)

        context.ensure_datasets(self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET)

        payload = QueryRequest(
            datasets=[
                {"path": self._LOSS_DATASET, "alias": "loss"},
                {"path": self._HILLSLOPE_DATASET, "alias": "hills"},
                {"path": self._LANDUSE_DATASET, "alias": "lu"},
            ],
            columns=[
                "lu.key AS landuse_id",
                "COALESCE(lu.desc, '') AS management_description",
            ],
            joins=[
                {
                    "left": "loss",
                    "right": "hills",
                    "left_on": ["Hillslopes"],
                    "right_on": ["wepp_id"],
                },
                {
                    "left": "hills",
                    "right": "lu",
                    "left_on": ["TopazID"],
                    "right_on": ["TopazID"],
                },
            ],
            aggregations=[
                {"sql": 'SUM(loss."Runoff Volume")', "alias": "sum_runoff_m3"},
                {"sql": 'SUM(loss."Subrunoff Volume")', "alias": "sum_subrunoff_m3"},
                {"sql": 'SUM(loss."Baseflow Volume")', "alias": "sum_baseflow_m3"},
                {"sql": 'SUM(loss."Soil Loss")', "alias": "sum_soil_loss"},
                {"sql": 'SUM(loss."Sediment Yield")', "alias": "sum_sediment_yield"},
                {"sql": 'SUM(loss."Sediment Deposition")', "alias": "sum_sediment_deposition"},
                {"sql": 'SUM(hills.area)', "alias": "sum_area_m2"},
            ],
            group_by=["lu.key", "lu.desc"],
            order_by=["lu.key"],
        )

        result = context.query(payload)
        records = result.records
        if not records:
            return self._empty_dataframe()

        df = pd.DataFrame.from_records(records)
        if df.empty:
            return self._empty_dataframe()

        df["landuse_id"] = df["landuse_id"].astype("Int64")
        df["management_description"] = df["management_description"].fillna("")

        area_m2 = df["sum_area_m2"].astype(float).fillna(0.0)
        area_ha = area_m2 / 10000.0

        def _depth_mm(volume_series: pd.Series) -> pd.Series:
            volume = volume_series.astype(float).fillna(0.0)
            denom = area_m2.replace(0.0, pd.NA)
            return ((volume * 1000.0) / denom).astype(float).fillna(0.0)

        output = pd.DataFrame(
            {
                "Landuse ID": df["landuse_id"],
                "Management Description": df["management_description"],
                "Landuse Area (ha)": area_ha.round(6),
                "Avg Runoff Depth (mm/yr)": _depth_mm(df["sum_runoff_m3"]),
                "Avg Lateral Flow Depth (mm/yr)": _depth_mm(df["sum_subrunoff_m3"]),
                "Avg Baseflow Depth (mm/yr)": _depth_mm(df["sum_baseflow_m3"]),
                "Avg Soil Loss (kg/yr)": df["sum_soil_loss"].astype(float).fillna(0.0),
                "Avg Sediment Yield (kg/yr)": df["sum_sediment_yield"].astype(float).fillna(0.0),
                "Avg Sediment Deposition (kg/yr)": df["sum_sediment_deposition"].astype(float).fillna(0.0),
            }
        )

        output.sort_values("Landuse Area (ha)", ascending=False, inplace=True)
        output.reset_index(drop=True, inplace=True)
        return output

    def _empty_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({column: [] for column in self._DISPLAY_COLUMNS}, columns=self._DISPLAY_COLUMNS)

    def __iter__(self) -> Iterable[RowData]:
        for record in self._dataframe.to_dict(orient="records"):
            yield RowData(record)


# Backwards compatibility.
AverageAnnualsByLanduse = AverageAnnualsByLanduseReport
