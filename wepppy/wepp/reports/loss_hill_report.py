"""Hillslope-scale summaries that blend loss_pw0.hill with landuse/soil metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List

import pandas as pd

from wepppy.query_engine.payload import QueryRequest

from .helpers import ReportQueryContext
from .report_base import ReportBase
from .row_data import RowData

__all__ = ["HillSummaryReport", "HillSummary"]


class HillSummaryReport(ReportBase):
    """Per-hillslope summary derived from loss_pw0.hill + spatial metadata."""

    _LOSS_DATASET = "wepp/output/interchange/loss_pw0.hill.parquet"
    _HILLSLOPE_DATASET = "watershed/hillslopes.parquet"
    _LANDUSE_DATASET = "landuse/landuse.parquet"
    _SOILS_DATASET = "soils/soils.parquet"

    def __init__(
        self,
        wd: str | Path | Any,
        *,
        fraction_under: float | None = None,
        **_unused_kwargs,
    ):
        loss = wd if self._is_loss_like(wd) else None
        if loss is not None:
            self._wd = self._infer_wd_from_loss(loss)
        else:
            self._wd = Path(wd).expanduser()
        if not self._wd.exists():
            raise FileNotFoundError(self._wd)
        
        self._fraction_under = fraction_under

        context = self._prepare_context()
        dataframe = self._build_dataframe(context)

        self._dataframe = dataframe
        self.header = list(dataframe.columns)

    def _prepare_context(self) -> ReportQueryContext:
        """Bootstrap and validate the report query context."""
        context = ReportQueryContext(self._wd, run_interchange=False)
        context.ensure_datasets(self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET)
        return context

    def _build_dataframe(self, context: ReportQueryContext) -> pd.DataFrame:
        """Run the DuckDB query and produce the fully formatted dataframe."""
        catalog = context.catalog
        include_soils = catalog.has(self._SOILS_DATASET)

        datasets = [
            {"path": self._LOSS_DATASET, "alias": "loss"},
            {"path": self._HILLSLOPE_DATASET, "alias": "hills"},
            {"path": self._LANDUSE_DATASET, "alias": "lu"},
        ]
        joins = [
            {"left": "loss", "right": "hills", "left_on": ["wepp_id"], "right_on": ["wepp_id"]},
            {"left": "hills", "right": "lu", "left_on": ["topaz_id"], "right_on": ["topaz_id"], "join_type": "left"},
        ]
        columns: List[str] = [
            'loss.wepp_id AS wepp_id',
            "hills.topaz_id AS topaz_id",
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
                {"left": "hills", "right": "soil", "left_on": ["topaz_id"], "right_on": ["topaz_id"], "join_type": "left"}
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
            order_by=['loss.wepp_id'],
        )
        result = context.query(payload)
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

    @staticmethod
    def _is_loss_like(value: Any) -> bool:
        """Return ``True`` if ``value`` mimics the historic loss wrapper."""
        return hasattr(value, "fn") and hasattr(value, "hill_tbl")

    @staticmethod
    def _infer_wd_from_loss(loss: Any) -> Path:
        """Derive the run directory from a ``loss`` object."""
        fn_path = Path(loss.fn).expanduser()
        try:
            return fn_path.parents[2]
        except IndexError:
            return fn_path.parent

    def _default_columns(self, include_soils: bool) -> List[str]:
        """Return the default column ordering, optionally including soil fields."""
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
        """Yield ``RowData`` wrappers for each formatted hillslope row."""
        for record in self._dataframe.to_dict(orient="records"):
            yield RowData(record)


# Backwards compatibility.
HillSummary = HillSummaryReport
