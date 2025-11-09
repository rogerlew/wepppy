"""Return-period style flood frequency reporting for outlet-scale events."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .report_base import ReportBase
from .row_data import RowData, parse_units

__all__ = ["FrqFloodReport", "FrqFlood"]


class FrqFloodReport(ReportBase):
    """Flood frequency analysis based on interchange event data."""

    _EBE_DATASET = Path("wepp/output/interchange/ebe_pw0.parquet")
    _TOTALWATSED_DATASET = Path("wepp/output/interchange/totalwatsed3.parquet")
    _COLUMN_MAP = OrderedDict(
        [
            ("Precipitation Depth (mm)", "precip"),
            ("Runoff Volume (m^3)", "runoff_volume"),
            ("Peak Runoff (m^3/s)", "peak_runoff"),
            ("Sediment Yield (kg)", "sediment_yield"),
            ("Soluble Reactive P (kg)", "soluble_pollutant"),
            ("Particulate P (kg)", "particulate_pollutant"),
            ("Total P (kg)", "total_pollutant"),
        ]
    )

    def __init__(self, wd: str | Path, recurrence: Sequence[int] = (2, 5, 10, 20, 25)) -> None:
        self.wd = Path(wd).expanduser()
        if not self.wd.exists():
            raise FileNotFoundError(self.wd)

        self.recurrence = sorted(int(value) for value in recurrence)
        events = self._load_event_dataframe()

        if events.empty:
            self._initialise_empty()
            return

        self.num_events = len(events)

        phosphorus_columns = ["Soluble Reactive P (kg)", "Particulate P (kg)", "Total P (kg)"]
        self.has_phosphorus = bool(events[phosphorus_columns].abs().sum().sum())

        display_columns = [
            "Precipitation Depth (mm)",
            "Runoff Volume (m^3)",
            "Peak Runoff (m^3/s)",
            "Sediment Yield (kg)",
        ]
        if self.has_phosphorus:
            display_columns.extend(phosphorus_columns)

        self.wsarea = self._load_watershed_area()
        display_columns.insert(2, "Runoff (mm)")
        self.header = ["Recurrence", *display_columns]
        self.units_d = {
            "Precipitation Depth": "mm",
            "Runoff Volume": "m^3",
            "Runoff": "mm",
            "Peak Runoff": "m^3/s",
            "Sediment Yield": "kg",
            "Soluble Reactive P": "kg",
            "Particulate P": "kg",
            "Total P": "kg",
        }

        self.years = events["simulation_year"].nunique()
        numeric_columns = [column for column in display_columns if column != "Runoff (mm)"]
        annual_max = (
            events.groupby("simulation_year")[numeric_columns]
            .max()
            .reset_index(drop=True)
        )

        self._rows = self._build_frequency_rows(annual_max, display_columns)

    def _initialise_empty(self) -> None:
        """Reset derived attributes when no event data is available."""
        self.header = ["Recurrence", "Precipitation Depth (mm)", "Runoff Volume (m^3)", "Runoff (mm)"]
        self.units_d = {
            "Precipitation Depth": "mm",
            "Runoff Volume": "m^3",
            "Runoff": "mm",
            "Peak Runoff": "m^3/s",
            "Sediment Yield": "kg",
            "Soluble Reactive P": "kg",
            "Particulate P": "kg",
            "Total P": "kg",
        }
        self._rows: list[OrderedDict[str, float | str]] = []
        self.has_phosphorus = False
        self.years = 0
        self.wsarea = 0.0
        self.num_events = 0

    def _load_event_dataframe(self) -> pd.DataFrame:
        """Read the per-event interchange parquet into a tidy dataframe."""
        dataset_path = self.wd / self._EBE_DATASET
        if not dataset_path.exists():
            raise FileNotFoundError(dataset_path)

        columns = ["simulation_year", *self._COLUMN_MAP.values()]
        table = pq.read_table(dataset_path, columns=columns)
        frame = table.to_pandas()
        if frame.empty:
            return pd.DataFrame()

        frame["simulation_year"] = frame["simulation_year"].astype(int)
        for column in self._COLUMN_MAP.values():
            frame[column] = frame[column].astype(float).fillna(0.0)

        rename_map = {raw: friendly for friendly, raw in self._COLUMN_MAP.items()}
        frame = frame.rename(columns=rename_map)
        return frame

    def _load_watershed_area(self) -> float:
        """Return the contributing watershed area in hectares if available."""
        dataset_path = self.wd / self._TOTALWATSED_DATASET
        if not dataset_path.exists():
            return 0.0
        try:
            table = pq.read_table(dataset_path, columns=["Area"])
            series = table.column(0).to_numpy(zero_copy_only=False)
            mask = ~np.isnan(series)
            if not mask.any():
                return 0.0
            area_m2 = float(series[mask].max())
            return area_m2 / 10000.0
        except Exception:  # pragma: no cover - fall back if parquet cannot be read
            return 0.0

    def _build_frequency_rows(
        self,
        annual_max: pd.DataFrame,
        display_columns: Sequence[str],
    ) -> list[OrderedDict[str, float | str]]:
        """Compute Weibull-based frequency rows for the configured recurrence intervals."""
        rows: list[OrderedDict[str, float | str]] = []

        if annual_max.empty:
            return rows

        numeric_columns = [col for col in display_columns if col != "Runoff (mm)"]
        data = annual_max[numeric_columns]

        means = {column: float(np.mean(data[column].to_numpy(dtype=float))) for column in numeric_columns}
        stds = {column: float(np.std(data[column].to_numpy(dtype=float), ddof=0)) for column in numeric_columns}

        for T in self.recurrence:
            if T >= self.years:
                continue
            kfactor = -1.0 * (0.45005 + 0.7797 * np.log(np.log(T / (T - 1.0))))
            values: dict[str, float | str] = {"Recurrence": T}
            for column in numeric_columns:
                values[column] = means[column] + stds[column] * kfactor
            values["Runoff (mm)"] = self._runoff_depth(values.get("Runoff Volume (m^3)"))
            ordered = OrderedDict((name, values.get(name, 0.0)) for name in ["Recurrence", *display_columns])
            rows.append(ordered)

        mean_values: dict[str, float | str] = {"Recurrence": "Mean"}
        for column in numeric_columns:
            mean_values[column] = means[column]
        mean_values["Runoff (mm)"] = self._runoff_depth(mean_values.get("Runoff Volume (m^3)"))
        rows.append(OrderedDict((name, mean_values.get(name, 0.0)) for name in ["Recurrence", *display_columns]))

        std_values: dict[str, float | str] = {"Recurrence": "StdDev"}
        for column in numeric_columns:
            std_values[column] = stds[column]
        std_values["Runoff (mm)"] = self._runoff_depth(std_values.get("Runoff Volume (m^3)"))
        rows.append(OrderedDict((name, std_values.get(name, 0.0)) for name in ["Recurrence", *display_columns]))

        return rows

    def _runoff_depth(self, runoff_volume_m3: float | None) -> float:
        """Convert a runoff volume to depth (mm) using watershed area."""
        if not runoff_volume_m3 or self.wsarea <= 0:
            return 0.0
        return float(runoff_volume_m3) / (self.wsarea * 10000.0) * 1000.0

    def __iter__(self) -> Iterator[RowData]:
        """Yield each recurrence interval row as ``RowData``."""
        for row in self._rows:
            yield RowData(row)


# Backwards compatibility.
FrqFlood = FrqFloodReport
