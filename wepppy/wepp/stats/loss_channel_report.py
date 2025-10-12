from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd

from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest
from wepppy.wepp.stats.report_base import ReportBase
from wepppy.wepp.stats.row_data import RowData


class ChannelSummary(ReportBase):
    """Channel-scale summary derived from loss_pw0.chn and watershed channel metadata."""

    _LOSS_DATASET = "wepp/output/interchange/loss_pw0.chn.parquet"
    _CHANNEL_DATASET = "watershed/channels.parquet"

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
        required = [self._LOSS_DATASET, self._CHANNEL_DATASET]
        missing = [path for path in required if not context.catalog.has(path)]
        if missing:
            raise FileNotFoundError(
                f"Missing required dataset(s) for channel summary: {', '.join(missing)}"
            )
        return context

    def _build_dataframe(self, context) -> pd.DataFrame:
        payload = QueryRequest(
            datasets=[
                {"path": self._LOSS_DATASET, "alias": "loss"},
                {"path": self._CHANNEL_DATASET, "alias": "chn"},
            ],
            columns=[
                'loss."Channels and Impoundments" AS loss_channel_id',
                "chn.wepp_id AS channel_wepp_id",
                "chn.chn_enum AS channel_enum",
                "chn.TopazID AS topaz_id",
                "chn.length AS length_m",
                "chn.width AS width_m",
                "chn.order AS channel_order",
                "chn.slope_scalar AS slope",
                "chn.area AS channel_area_m2",
                'loss."Contributing Area" AS contributing_area_ha',
                'loss."Discharge Volume" AS discharge_m3',
                'loss."Subsuface Flow Volume" AS lateral_m3',
                'loss."Upland Charge" AS upland_m3',
                'loss."Sediment Yield" AS sediment_yield_tonne',
                'loss."Soil Loss" AS soil_loss_kg',
                'loss."Solub. React. Pollutant" AS solub_react_kg',
                'loss."Particulate Pollutant" AS particulate_kg',
                'loss."Total Pollutant" AS total_kg',
            ],
            joins=[
                {
                    "left": "loss",
                    "right": "chn",
                    "left_on": ["Channels and Impoundments"],
                    "right_on": ["chn_enum"],
                }
            ],
            order_by=['loss."Channels and Impoundments"'],
        )
        result = run_query(context, payload)
        records = result.records or []
        if not records:
            return pd.DataFrame(columns=self._column_order(include_phosphorus=False))

        frame = pd.DataFrame.from_records(records)
        numeric_fields = [
            "loss_channel_id",
            "channel_wepp_id",
            "channel_enum",
            "topaz_id",
            "length_m",
            "width_m",
            "channel_order",
            "slope",
            "channel_area_m2",
            "contributing_area_ha",
            "discharge_m3",
            "lateral_m3",
            "upland_m3",
            "sediment_yield_tonne",
            "soil_loss_kg",
            "solub_react_kg",
            "particulate_kg",
            "total_kg",
        ]
        for field in numeric_fields:
            if field in frame.columns:
                frame[field] = pd.to_numeric(frame[field], errors="coerce")

        channel_area_ha = (frame["channel_area_m2"] / 10000.0).replace(0, pd.NA)
        contributing_area_ha = frame["contributing_area_ha"].replace(0, pd.NA)

        frame["discharge_depth_mm"] = ((frame["discharge_m3"] * 1000.0) / (contributing_area_ha * 10000.0)).astype(float)
        frame["lateral_depth_mm"] = ((frame["lateral_m3"] * 1000.0) / (contributing_area_ha * 10000.0)).astype(float)
        frame["upland_charge_mm"] = ((frame["upland_m3"] * 1000.0) / (contributing_area_ha * 10000.0)).astype(float)

        frame["channel_area_ha"] = channel_area_ha.astype(float)
        frame["sediment_yield_density"] = (frame["sediment_yield_tonne"] * 1000.0 / channel_area_ha).astype(float)
        frame["soil_loss_density"] = (frame["soil_loss_kg"] / channel_area_ha).astype(float)

        include_phosphorus = frame[["solub_react_kg", "particulate_kg", "total_kg"]].abs().sum().sum() > 0
        if include_phosphorus:
            frame["solub_react_density"] = (frame["solub_react_kg"] / channel_area_ha).astype(float)
            frame["particulate_density"] = (frame["particulate_kg"] / channel_area_ha).astype(float)
            frame["total_density"] = (frame["total_kg"] / channel_area_ha).astype(float)
        else:
            frame.drop(columns=["solub_react_kg", "particulate_kg", "total_kg"], inplace=True)

        frame.drop(columns=["channel_area_m2", "discharge_m3", "lateral_m3", "upland_m3"], inplace=True)

        frame.rename(
            columns={
                "channel_wepp_id": "Wepp Channel ID",
                "channel_enum": "Channel Enum",
                "TopazID": "Topaz ID",
                "topaz_id": "Topaz ID",
                "loss_channel_id": "Channel ID",
                "length_m": "Length (m)",
                "width_m": "Width (m)",
                "channel_order": "Order",
                "slope": "Slope",
                "channel_area_ha": "Channel Area (ha)",
                "contributing_area_ha": "Contributing Area (ha)",
                "discharge_depth_mm": "Discharge Depth (mm/yr)",
                "lateral_depth_mm": "Lateral Flow Depth (mm/yr)",
                "upland_charge_mm": "Upland Charge Depth (mm/yr)",
                "sediment_yield_tonne": "Sediment Yield (tonne/yr)",
                "sediment_yield_density": "Sediment Yield Density (kg/ha/yr)",
                "soil_loss_kg": "Channel Erosion (kg/yr)",
                "soil_loss_density": "Channel Erosion Density (kg/ha/yr)",
            },
            inplace=True,
        )

        if include_phosphorus:
            frame["Soluble Reactive P (kg/yr)"] = frame["solub_react_kg"]
            frame["Soluble Reactive P Density (kg/ha/yr)"] = frame["solub_react_density"]
            frame["Particulate P (kg/yr)"] = frame["particulate_kg"]
            frame["Particulate P Density (kg/ha/yr)"] = frame["particulate_density"]
            frame["Total P (kg/yr)"] = frame["total_kg"]
            frame["Total P Density (kg/ha/yr)"] = frame["total_density"]
            frame.drop(
                columns=[
                    "solub_react_kg",
                    "solub_react_density",
                    "particulate_kg",
                    "particulate_density",
                    "total_kg",
                    "total_density",
                ],
                inplace=True,
            )

        frame["Channel ID"] = frame.get("Channel ID", frame.get("Channel Enum", pd.Series(dtype=float)))
        frame["Channel ID"] = frame["Channel ID"].astype("Int64")
        frame["Wepp Channel ID"] = frame["Wepp Channel ID"].astype("Int64")
        frame["Channel Enum"] = frame["Channel Enum"].astype("Int64")
        frame["Topaz ID"] = frame["Topaz ID"].astype("Int64")

        numeric_cols = frame.select_dtypes(include=["number"]).columns
        frame[numeric_cols] = frame[numeric_cols].fillna(0.0)

        columns = self._column_order(include_phosphorus=include_phosphorus)
        frame = frame[columns]

        return frame

    def _column_order(self, *, include_phosphorus: bool) -> List[str]:
        columns = [
            "Channel ID",
            "Wepp Channel ID",
            "Channel Enum",
            "Topaz ID",
            "Length (m)",
            "Width (m)",
            "Order",
            "Slope",
            "Channel Area (ha)",
            "Contributing Area (ha)",
            "Discharge Depth (mm/yr)",
            "Lateral Flow Depth (mm/yr)",
            "Upland Charge Depth (mm/yr)",
            "Sediment Yield (tonne/yr)",
            "Sediment Yield Density (kg/ha/yr)",
            "Channel Erosion (kg/yr)",
            "Channel Erosion Density (kg/ha/yr)",
        ]
        if include_phosphorus:
            columns.extend(
                [
                    "Soluble Reactive P (kg/yr)",
                    "Soluble Reactive P Density (kg/ha/yr)",
                    "Particulate P (kg/yr)",
                    "Particulate P Density (kg/ha/yr)",
                    "Total P (kg/yr)",
                    "Total P Density (kg/ha/yr)",
                ]
            )
        return columns

    def __iter__(self) -> Iterable[RowData]:
        for record in self._dataframe.to_dict(orient="records"):
            yield RowData(record)
