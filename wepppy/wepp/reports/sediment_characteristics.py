from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import List, Union

import pandas as pd

from wepppy.query_engine.payload import QueryRequest

from .helpers import ReportQueryContext
from .sediment_class_info_report import SedimentClassInfoReport
from .sediment_channel_distribution_report import (
    ChannelClassFractionReport,
    ChannelParticleDistributionReport,
    ChannelSedimentDistribution,
)
from .sediment_hillslope_distribution_report import (
    HillslopeClassFractionReport,
    HillslopeParticleDistributionReport,
    HillslopeSedimentDistribution,
)


class SedimentCharacteristics:
    """Aggregated sediment characteristics for channel outlet and hillslopes."""

    _CLASS_DATASET = "wepp/output/interchange/loss_pw0.class_data.parquet"
    _OUTLET_DATASET = "wepp/output/interchange/loss_pw0.out.parquet"
    _HILL_DATASET = "wepp/output/interchange/loss_pw0.hill.parquet"
    _HILL_ALL_YEARS_DATASET = "wepp/output/interchange/loss_pw0.all_years.hill.parquet"
    _PASS_DATASET = "wepp/output/interchange/H.pass.parquet"

    def __init__(self, wd: Union[str, Path, object]):
        self._wd = self._coerce_run_directory(wd)

        context = self._prepare_context()
        class_table = self._load_class_dataframe(context)
        years = self._load_year_count(context)

        self.class_info_report = SedimentClassInfoReport(class_table)

        channel_total = self._load_outlet_discharge(context)
        channel_class_rows = self._build_channel_class_rows(class_table, channel_total)
        channel_particle_rows = self._build_particle_rows(class_table, channel_total, class_table["fraction"].to_numpy())
        self.channel = ChannelSedimentDistribution(
            total_discharge_tonne=channel_total,
            class_fraction_report=ChannelClassFractionReport(channel_class_rows),
            particle_distribution_report=ChannelParticleDistributionReport(channel_particle_rows),
        )

        hill_class_masses = self._load_hillslope_class_masses(context)
        hill_total_tonne = self._compute_hill_total_delivery(hill_class_masses, years)
        hill_frac = self._normalize_hill_class_fractions(hill_class_masses)
        hill_class_rows = self._build_hill_class_rows(hill_frac, hill_total_tonne)
        hill_particle_rows = self._build_particle_rows(class_table, hill_total_tonne, hill_frac)
        self.hillslope = HillslopeSedimentDistribution(
            total_delivery_tonne=hill_total_tonne,
            class_fraction_report=HillslopeClassFractionReport(hill_class_rows),
            particle_distribution_report=HillslopeParticleDistributionReport(hill_particle_rows),
        )

        self.specific_surface_index = self._lookup_outlet_value(context, "Index of specific surface")
        self.enrichment_ratio_of_spec_surface = self._lookup_outlet_value(context, "Enrichment ratio of specific surface")

    @staticmethod
    def _coerce_run_directory(source: Union[str, Path, object]) -> Path:
        if isinstance(source, (str, Path)):
            path = Path(source).expanduser()
            if not path.exists():
                raise FileNotFoundError(path)
            return path
        if hasattr(source, "wd"):
            return Path(source.wd).expanduser()
        if hasattr(source, "fn"):
            return Path(source.fn).resolve().parents[2].expanduser()
        raise TypeError("SedimentCharacteristics expects a run directory path or a loss report instance")

    def _prepare_context(self):
        context = ReportQueryContext(self._wd, run_interchange=False)
        context.ensure_datasets(
            self._CLASS_DATASET,
            self._OUTLET_DATASET,
            self._HILL_DATASET,
            self._HILL_ALL_YEARS_DATASET,
            self._PASS_DATASET,
        )
        return context

    def _load_class_dataframe(self, context) -> pd.DataFrame:
        payload = QueryRequest(
            datasets=[{"path": self._CLASS_DATASET, "alias": "class"}],
            columns=[
                "class.Class AS class",
                'class.Diameter AS diameter_mm',
                'class."Specific Gravity" AS specific_gravity',
                'class."Pct Sand" AS pct_sand',
                'class."Pct Silt" AS pct_silt',
                'class."Pct Clay" AS pct_clay',
                'class."Pct OM" AS pct_om',
                'class."Fraction In Flow Exiting" AS fraction',
            ],
            order_by=["class.Class"],
        )
        result = context.query(payload)
        records = result.records or []
        if not records:
            raise ValueError("loss_pw0.class_data.parquet returned no records")
        return pd.DataFrame.from_records(records)

    def _load_year_count(self, context) -> int:
        payload = QueryRequest(
            datasets=[{"path": self._HILL_ALL_YEARS_DATASET, "alias": "ay"}],
            columns=["COUNT(DISTINCT ay.year) AS year_count"],
        )
        result = context.query(payload)
        years = int(result.records[0]["year_count"]) if result.records else 0
        return max(years, 1)

    def _load_outlet_discharge(self, context) -> float:
        payload = QueryRequest(
            datasets=[{"path": self._OUTLET_DATASET, "alias": "out"}],
            columns=["out.key", "out.value"],
            filters=[{"column": "out.key", "operator": "=", "value": "Avg. Ann. sediment discharge from outlet"}],
        )
        result = context.query(payload)
        if not result.records:
            return 0.0
        return float(result.records[0]["value"] or 0.0)

    def _lookup_outlet_value(self, context, key: str) -> float:
        payload = QueryRequest(
            datasets=[{"path": self._OUTLET_DATASET, "alias": "out"}],
            columns=["out.value"],
            filters=[{"column": "out.key", "operator": "=", "value": key}],
        )
        result = context.query(payload)
        return float(result.records[0]["value"] or 0.0) if result.records else 0.0

    def _build_channel_class_rows(self, class_table: pd.DataFrame, total_tonne: float) -> List[OrderedDict[str, float]]:
        rows: List[OrderedDict[str, float]] = []
        for _, row in class_table.iterrows():
            fraction = float(row["fraction"] or 0.0)
            discharge = fraction * total_tonne
            rows.append(
                OrderedDict(
                    {
                        "Class": int(row["class"]),
                        "Fraction (ratio)": fraction,
                        "Sediment Discharge (tonne/yr)": discharge,
                    }
                )
            )
        return rows

    def _build_particle_rows(self, class_table: pd.DataFrame, total_tonne: float, fractions: List[float]) -> List[OrderedDict[str, float]]:
        fraction_series = pd.Series(fractions)
        particle_map = OrderedDict(
            {
                "Clay": (class_table["pct_clay"] / 100.0 * fraction_series).sum(),
                "Silt": (class_table["pct_silt"] / 100.0 * fraction_series).sum(),
                "Sand": (class_table["pct_sand"] / 100.0 * fraction_series).sum(),
                "Organic Matter": (class_table["pct_om"] / 100.0 * fraction_series).sum(),
            }
        )
        rows: List[OrderedDict[str, float]] = []
        for label, fraction in particle_map.items():
            discharge = fraction * total_tonne
            rows.append(
                OrderedDict(
                    {
                        "Particle Type": label,
                        "Fraction (ratio)": float(fraction),
                        "Sediment Discharge (tonne/yr)": discharge,
                    }
                )
            )
        return rows

    def _load_hillslope_class_masses(self, context) -> List[float]:
        payload = QueryRequest(
            datasets=[{"path": self._PASS_DATASET, "alias": "pass"}],
            columns=[
                "SUM(pass.runvol * pass.sedcon_1) AS mass_c1",
                "SUM(pass.runvol * pass.sedcon_2) AS mass_c2",
                "SUM(pass.runvol * pass.sedcon_3) AS mass_c3",
                "SUM(pass.runvol * pass.sedcon_4) AS mass_c4",
                "SUM(pass.runvol * pass.sedcon_5) AS mass_c5",
            ],
        )
        result = context.query(payload)
        if not result.records:
            return [0.0] * 5
        row = result.records[0]
        return [float(row[key] or 0.0) for key in ["mass_c1", "mass_c2", "mass_c3", "mass_c4", "mass_c5"]]

    def _compute_hill_total_delivery(self, class_masses: List[float], year_count: int) -> float:
        total_kg = sum(class_masses)
        if total_kg <= 0.0:
            return 0.0
        return total_kg / max(year_count, 1) / 1000.0

    def _normalize_hill_class_fractions(self, class_masses: List[float]) -> List[float]:
        total = sum(class_masses)
        if total <= 0.0:
            return [0.0] * len(class_masses)
        return [mass / total for mass in class_masses]

    def _build_hill_class_rows(self, fractions: List[float], total_tonne: float) -> List[OrderedDict[str, float]]:
        rows: List[OrderedDict[str, float]] = []
        for idx, fraction in enumerate(fractions, start=1):
            delivery = fraction * total_tonne
            rows.append(
                OrderedDict(
                    {
                        "Class": idx,
                        "Fraction (ratio)": float(fraction),
                        "Sediment Delivery (tonne/yr)": delivery,
                    }
                )
            )
        return rows


__all__ = ["SedimentCharacteristics"]
