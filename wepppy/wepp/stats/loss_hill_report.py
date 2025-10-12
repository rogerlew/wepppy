from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd

from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest
from wepppy.wepp.stats.report_base import ReportBase
from wepppy.wepp.stats.row_data import RowData


class HillSummary(ReportBase):
    """Per-hillslope summary derived from loss_pw0.hill + spatial metadata."""

    _LOSS_DATASET = "wepp/output/interchange/loss_pw0.hill.parquet"
    _HILLSLOPE_DATASET = "watershed/hillslopes.parquet"
    _LANDUSE_DATASET = "landuse/landuse.parquet"
    _SOILS_DATASET = "soils/soils.parquet"

    def __init__(self, wd: str | Path):
        self._wd = Path(wd).expanduser()
        if not self._wd.exists():
            raise FileNotFoundError(self._wd)

        context = self._prepare_context()
        dataframe = self._build_dataframe(context)

        self._dataframe = dataframe
        self.header = list(dataframe.columns)

    def _prepare_context(self):
        activate_query_engine(self._wd, run_interchange=False)
        context = resolve_run_context(str(self._wd), auto_activate=False)
        required = [self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET]
        missing = [path for path in required if not context.catalog.has(path)]
        if missing:
            raise FileNotFoundError(
                f"Missing required dataset(s) for hill summary: {', '.join(missing)}"
            )
        return context

    def _build_dataframe(self, context) -> pd.DataFrame:
        catalog = context.catalog
        include_soils = catalog.has(self._SOILS_DATASET)

        datasets = [
            {"path": self._LOSS_DATASET, "alias": "loss"},
            {"path": self._HILLSLOPE_DATASET, "alias": "hills"},
            {"path": self._LANDUSE_DATASET, "alias": "lu"},
        ]
        joins = [
            {"left": "loss", "right": "hills", "left_on": ["Hillslopes"], "right_on": ["wepp_id"]},
            {"left": "hills", "right": "lu", "left_on": ["TopazID"], "right_on": ["TopazID"], "join_type": "left"},
        ]
        columns: List[str] = [
            'loss."Hillslopes" AS wepp_id',
            "hills.TopazID AS topaz_id",
            "hills.length AS length_m",
            "hills.width AS width_m",
            "hills.slope_scalar AS slope",
            'loss."Hillslope Area" AS area_ha',
            'loss."Runoff Volume" AS runoff_m3',
            'loss."Subrunoff Volume" AS lateral_m3',
            'loss."Baseflow Volume" AS baseflow_m3',
            'loss."Soil Loss" AS soil_loss_kg',
            'loss."Sediment Deposition" AS sediment_dep_kg',
            'loss."Sediment Yield" AS sediment_yield_kg',
            'loss."Solub. React. Pollutant" AS solub_react_kg',
            'loss."Particulate Pollutant" AS particulate_kg',
            'loss."Total Pollutant" AS total_kg',
            "CAST(lu.key AS INTEGER) AS landuse_key",
            "lu.desc AS landuse_desc",
        ]

        if include_soils:
            datasets.append({"path": self._SOILS_DATASET, "alias": "soil"})
            joins.append(
                {"left": "hills", "right": "soil", "left_on": ["TopazID"], "right_on": ["TopazID"], "join_type": "left"}
            )
            columns.extend(
                [
                    "soil.mukey AS soil_key",
                    "soil.desc AS soil_desc",
                ]
            )
        else:
            columns.extend(
                [
                    "NULL AS soil_key",
                    "NULL AS soil_desc",
                ]
            )

        payload = QueryRequest(
            datasets=datasets,
            columns=columns,
            joins=joins,
            order_by=['loss."Hillslopes"'],
        )
        result = run_query(context, payload)
        records = result.records or []
        if not records:
            return pd.DataFrame(columns=self._default_columns(include_soils))

        frame = pd.DataFrame.from_records(records)

        numeric_fields = [
            "wepp_id",
            "topaz_id",
            "length_m",
            "width_m",
            "slope",
            "area_ha",
            "runoff_m3",
            "lateral_m3",
            "baseflow_m3",
            "soil_loss_kg",
            "sediment_dep_kg",
            "sediment_yield_kg",
            "solub_react_kg",
            "particulate_kg",
            "total_kg",
        ]
        for field in numeric_fields:
            if field in frame.columns:
                frame[field] = pd.to_numeric(frame[field], errors="coerce")

        frame["landuse_key"] = pd.to_numeric(frame.get("landuse_key"), errors="coerce").astype("Int64")
        frame["landuse_desc"] = frame.get("landuse_desc", pd.Series(dtype=str)).fillna("")
        frame["soil_key"] = frame.get("soil_key", pd.Series(dtype=object)).fillna("")
        frame["soil_desc"] = frame.get("soil_desc", pd.Series(dtype=str)).fillna("")

        area_ha = frame["area_ha"].replace(0, pd.NA)
        area_m2 = area_ha * 10000.0

        frame["runoff_depth_mm"] = ((frame["runoff_m3"] * 1000.0) / area_m2).astype(float)
        frame["lateral_depth_mm"] = ((frame["lateral_m3"] * 1000.0) / area_m2).astype(float)
        frame["baseflow_depth_mm"] = ((frame["baseflow_m3"] * 1000.0) / area_m2).astype(float)

        frame["soil_loss_density"] = (frame["soil_loss_kg"] / area_ha).astype(float)
        frame["sediment_dep_density"] = (frame["sediment_dep_kg"] / area_ha).astype(float)
        frame["sediment_yield_density"] = (frame["sediment_yield_kg"] / area_ha).astype(float)

        if frame["solub_react_kg"].abs().sum(skipna=True) > 0:
            frame["solub_react_density"] = (frame["solub_react_kg"] / area_ha).astype(float)
        else:
            frame.drop(columns=["solub_react_kg"], inplace=True)
            frame.drop(columns=["particulate_kg"], inplace=True)
            frame.drop(columns=["total_kg"], inplace=True)

        frame.drop(columns=["runoff_m3", "lateral_m3", "baseflow_m3"], inplace=True)

        columns_order = self._default_columns(include_soils)
        if "solub_react_density" in frame.columns:
            columns_order.extend(
                [
                    "Soluble Reactive P (kg/yr)",
                    "Soluble Reactive P Density (kg/ha/yr)",
                    "Particulate P (kg/yr)",
                    "Particulate P Density (kg/ha/yr)",
                    "Total P (kg/yr)",
                    "Total P Density (kg/ha/yr)",
                ]
            )
            frame["Soluble Reactive P (kg/yr)"] = frame.pop("solub_react_kg")
            frame["Soluble Reactive P Density (kg/ha/yr)"] = frame.pop("solub_react_density")
            frame["Particulate P (kg/yr)"] = frame.pop("particulate_kg")
            frame["Particulate P Density (kg/ha/yr)"] = frame["Particulate P (kg/yr)"] / area_ha
            frame["Total P (kg/yr)"] = frame.pop("total_kg")
            frame["Total P Density (kg/ha/yr)"] = frame["Total P (kg/yr)"] / area_ha

        frame.rename(
            columns={
                "wepp_id": "Wepp ID",
                "topaz_id": "Topaz ID",
                "landuse_key": "Landuse Key",
                "landuse_desc": "Landuse Description",
                "soil_key": "Soil Key",
                "soil_desc": "Soil Description",
                "length_m": "Length (m)",
                "width_m": "Width (m)",
                "slope": "Slope",
                "area_ha": "Landuse Area (ha)",
                "runoff_depth_mm": "Runoff Depth (mm/yr)",
                "lateral_depth_mm": "Lateral Flow Depth (mm/yr)",
                "baseflow_depth_mm": "Baseflow Depth (mm/yr)",
                "soil_loss_kg": "Soil Loss (kg/yr)",
                "soil_loss_density": "Soil Loss Density (kg/ha/yr)",
                "sediment_dep_kg": "Sediment Deposition (kg/yr)",
                "sediment_dep_density": "Sediment Deposition Density (kg/ha/yr)",
                "sediment_yield_kg": "Sediment Yield (kg/yr)",
                "sediment_yield_density": "Sediment Yield Density (kg/ha/yr)",
            },
            inplace=True,
        )

        if "Landuse Key" in frame.columns:
            frame["Landuse Key"] = frame["Landuse Key"].apply(
                lambda x: "" if pd.isna(x) else int(x)
            )
        if "Soil Key" in frame.columns:
            frame["Soil Key"] = frame["Soil Key"].fillna("")

        numeric_cols = frame.select_dtypes(include=["number"]).columns
        frame[numeric_cols] = frame[numeric_cols].fillna(0.0)

        frame = frame.fillna("")
        frame = frame[columns_order]
        return frame

    def _default_columns(self, include_soils: bool) -> List[str]:
        base_columns = [
            "Wepp ID",
            "Topaz ID",
            "Landuse Key",
            "Landuse Description",
        ]
        if include_soils:
            base_columns.extend(["Soil Key", "Soil Description"])
        else:
            base_columns.extend(["Soil Key", "Soil Description"])

        base_columns.extend(
            [
                "Length (m)",
                "Width (m)",
                "Slope",
                "Landuse Area (ha)",
                "Runoff Depth (mm/yr)",
                "Lateral Flow Depth (mm/yr)",
                "Baseflow Depth (mm/yr)",
                "Soil Loss (kg/yr)",
                "Soil Loss Density (kg/ha/yr)",
                "Sediment Deposition (kg/yr)",
                "Sediment Deposition Density (kg/ha/yr)",
                "Sediment Yield (kg/yr)",
                "Sediment Yield Density (kg/ha/yr)",
            ]
        )
        return base_columns

    def __iter__(self) -> Iterable[RowData]:
        for record in self._dataframe.to_dict(orient="records"):
            yield RowData(record)
