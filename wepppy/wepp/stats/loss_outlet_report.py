from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest


@dataclass(slots=True)
class OutletRow:
    label: str
    value: Optional[float]
    units: Optional[str]
    per_area_value: Optional[float]
    per_area_units: Optional[str]


class OutletSummary:
    """Summarise outlet delivery metrics using loss_pw0.out interchange assets."""

    _DATASET_PATH = "wepp/output/interchange/loss_pw0.out.parquet"

    def __init__(self, wd: str | Path):
        self._wd = Path(wd).expanduser()
        if not self._wd.exists():
            raise FileNotFoundError(self._wd)

        context = self._prepare_context()
        self._rows = self._build_rows(context)

    def _prepare_context(self):
        activate_query_engine(self._wd, run_interchange=False)
        context = resolve_run_context(str(self._wd), auto_activate=False)
        if not context.catalog.has(self._DATASET_PATH):
            raise FileNotFoundError(
                f"Required dataset '{self._DATASET_PATH}' not found in the query engine catalog for {self._wd}"
            )
        return context

    def _load_table(self, context) -> pd.DataFrame:
        payload = QueryRequest(
            datasets=[{"path": self._DATASET_PATH, "alias": "out"}],
            columns=[
                "out.key AS key",
                "out.value AS value",
                "out.units AS units",
            ],
        )
        result = run_query(context, payload)
        frame = pd.DataFrame(result.records or [], columns=["key", "value", "units"])
        if frame.empty:
            raise ValueError(f"{self._DATASET_PATH} did not return any rows")
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame["units"] = frame["units"].fillna("")
        return frame.set_index("key")

    def _build_rows(self, context) -> List[OutletRow]:
        table = self._load_table(context)

        def value_for(key: str) -> Optional[float]:
            return float(table.value.get(key)) if key in table.index else None

        def units_for(key: str) -> Optional[str]:
            units = table.units.get(key) if key in table.index else None
            return units or None

        area_ha = value_for("Total contributing area to outlet")
        if area_ha in (None, 0):
            raise ValueError("Total contributing area to outlet not available or zero")
        area_m2 = area_ha * 10000.0

        rows: List[OutletRow] = [
            OutletRow(
                label="Total contributing area to outlet",
                value=area_ha,
                units=units_for("Total contributing area to outlet"),
                per_area_value=None,
                per_area_units=None,
            )
        ]

        def add_volume_row(label: str, key: str) -> None:
            value = value_for(key)
            if value is None:
                return
            units = units_for(key)
            per_area = (value * 1000.0 / area_m2) if area_m2 else None
            rows.append(
                OutletRow(
                    label=label,
                    value=value,
                    units=units,
                    per_area_value=per_area,
                    per_area_units="mm/yr",
                )
            )

        add_volume_row(
            label="Precipitation",
            key="Avg. Ann. Precipitation volume in contributing area",
        )

        irrigation_value = value_for("Avg. Ann. irrigation volume in contributing area")
        if irrigation_value not in (None, 0.0):
            add_volume_row(
                label="Irrigation",
                key="Avg. Ann. irrigation volume in contributing area",
            )

        add_volume_row(
            label="Stream discharge",
            key="Avg. Ann. water discharge from outlet",
        )

        def add_mass_row(label: str, key: str, *, units_override: Optional[str] = None) -> None:
            value = value_for(key)
            if value is None:
                return
            units = units_override or units_for(key)
            per_area = value / area_ha if area_ha else None
            per_area_units = None
            if units and units.endswith("/yr"):
                base_unit = units.split("/yr")[0].strip()
                per_area_units = f"{base_unit}/ha/yr"
            rows.append(
                OutletRow(
                    label=label,
                    value=value,
                    units=units,
                    per_area_value=per_area,
                    per_area_units=per_area_units,
                )
            )

        add_mass_row("Total hillslope soil loss", "Avg. Ann. total hillslope soil loss")
        add_mass_row("Total channel soil loss", "Avg. Ann. total channel soil loss")
        add_mass_row("Sediment discharge", "Avg. Ann. sediment discharge from outlet")

        ratio = value_for("Sediment Delivery Ratio for Watershed")
        if ratio is not None:
            rows.append(
                OutletRow(
                    label="Sediment delivery ratio for watershed",
                    value=ratio,
                    units=None,
                    per_area_value=None,
                    per_area_units=None,
                )
            )

        add_mass_row(
            "Phosphorus discharge",
            "Avg. Ann. Phosphorus discharge from outlet",
        )

        # Append extraneous per-area values if provided in the table.
        per_area_keys = [
            (
                "Sediment delivery per unit area",
                "Avg. Ann. Sed. delivery per unit area of watershed",
            ),
            (
                "Phosphorus delivery per unit area",
                "Avg. Ann. P. delivery per unit area of watershed",
            ),
        ]
        for label, key in per_area_keys:
            if key in table.index:
                rows.append(
                    OutletRow(
                        label=label,
                        value=value_for(key),
                        units=units_for(key),
                        per_area_value=None,
                        per_area_units=None,
                    )
                )

        return rows

    def rows(self, include_extraneous: bool = False) -> List[OutletRow]:
        if include_extraneous:
            return list(self._rows)

        primary_labels = {
            "Total contributing area to outlet",
            "Precipitation",
            "Stream discharge",
            "Total hillslope soil loss",
            "Total channel soil loss",
            "Sediment discharge",
            "Sediment delivery ratio for watershed",
            "Phosphorus discharge",
        }
        return [row for row in self._rows if row.label in primary_labels]
