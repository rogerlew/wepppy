"""Hillslope-level water balance summaries sourced from H.wat interchange files."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Iterator, Mapping

import pandas as pd
import pyarrow.parquet as pq

from .helpers import ReportCacheManager
from .output_scope import normalize_output_scope, scoped_dataset_path
from .report_base import ReportBase
from .row_data import RowData, parse_units

__all__ = ["HillslopeWatbalReport", "HillslopeWatbal"]

LOGGER = logging.getLogger(__name__)


class HillslopeWatbalReport(ReportBase):
    """Average annual hillslope water balance derived from interchange assets."""

    _SOURCE_REL_PATH = Path("wepp/output/interchange/H.wat.parquet")
    _ROADS_SEGMENT_MANIFEST_REL_PATH = Path("wepp/roads/segments/roads.segment.pass.manifest.json")
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

    def __init__(self, wd: str | Path, *, output_scope: str | None = None):
        self.wd = Path(wd).expanduser()
        if not self.wd.exists():
            raise FileNotFoundError(self.wd)
        self._output_scope = normalize_output_scope(output_scope)

        source_path = self._resolve_source_path()
        cache = ReportCacheManager(self.wd)
        cache_key = self._resolve_cache_key()
        cache_path = cache.root / f"{cache_key}.parquet"
        dataframe = cache.read_parquet(cache_key, version=self._CACHE_VERSION)
        if dataframe is not None and self._source_is_newer_than_cache(source_path, cache_path):
            dataframe = None
        if dataframe is None:
            legacy_cache = (
                self.wd / "wepp" / "output" / "interchange" / f"{self._CACHE_KEY}.parquet"
            )
            if (
                self._output_scope == "baseline"
                and legacy_cache.exists()
                and not self._source_is_newer_than_cache(source_path, legacy_cache)
            ):
                dataframe = pd.read_parquet(legacy_cache)

        if dataframe is None or not self._validate_cache_columns(dataframe):
            dataframe = self._build_summary()
            cache.write_parquet(cache_key, dataframe, version=self._CACHE_VERSION, index=False)

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
        """Return ``True`` when the cached dataframe matches the expected schema."""
        expected = {"TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()}
        return expected.issubset(set(dataframe.columns))

    @staticmethod
    def _source_is_newer_than_cache(source_path: Path, cache_path: Path) -> bool:
        """Return ``True`` when the source parquet is newer than the cached summary."""
        if not source_path.exists() or not cache_path.exists():
            return False
        return source_path.stat().st_mtime_ns > cache_path.stat().st_mtime_ns

    def _initialise_empty(self) -> None:
        """Initialize placeholder dataframes when no source data exists."""
        self._per_hill_year = pd.DataFrame(columns=["TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()])
        self._per_hill_avg = self._per_hill_year.iloc[0:0]
        self._watershed_yearly = pd.DataFrame(columns=["WaterYear", *self._MEASURE_MAP.keys()])
        self.header = list(self._MEASURE_MAP.keys())
        self.units_d = {label: "mm" for label in self.header}
        self.areas = {}
        self.wsarea = 0.0
        self.years = []

    def _build_summary(self) -> pd.DataFrame:
        """Query the H.wat parquet and aggregate to both hill/year and watershed scales."""
        source_path = self._resolve_source_path()
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
        roads_segment_targets = self._load_roads_segment_target_map()
        wepp_ids = frame["wepp_id"].astype(int)
        fallback_ids: set[int] = set()
        manifest_mapped_ids: set[int] = set()
        topaz_lookup: dict[int, int] = {}

        for wepp_id in sorted(wepp_ids.unique().tolist()):
            try:
                topaz_lookup[wepp_id] = int(translator.top(wepp=int(wepp_id)))
                continue
            except KeyError as exc:
                if self._output_scope != "roads":
                    raise exc

            target_wepp_id = roads_segment_targets.get(int(wepp_id))
            if target_wepp_id is not None:
                try:
                    topaz_lookup[wepp_id] = int(translator.top(wepp=int(target_wepp_id)))
                    manifest_mapped_ids.add(int(wepp_id))
                    continue
                except KeyError:
                    pass

            # Explicit roads fallback: preserve report availability when
            # segment IDs are not part of the baseline translator map.
            topaz_lookup[wepp_id] = int(wepp_id)
            fallback_ids.add(int(wepp_id))
            continue

        if manifest_mapped_ids:
            LOGGER.info(
                "Mapped Roads segment run IDs to target hillslopes in hillslope watbal report",
                extra={
                    "run_dir": str(self.wd),
                    "mapped_count": len(manifest_mapped_ids),
                    "mapped_ids_sample": sorted(manifest_mapped_ids)[:10],
                },
            )
        if fallback_ids:
            LOGGER.warning(
                "Falling back to raw WEPP IDs for roads hillslope watbal translation",
                extra={
                    "run_dir": str(self.wd),
                    "fallback_count": len(fallback_ids),
                    "fallback_ids_sample": sorted(fallback_ids)[:10],
                },
            )

        frame["wepp_id"] = wepp_ids
        frame["TopazID"] = frame["wepp_id"].map(topaz_lookup).astype(int)
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
            topaz_id = int(topaz_lookup[int(wepp_id)])
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

    def _load_roads_segment_target_map(self) -> dict[int, int]:
        """Return Roads segment run ID -> target hillslope WEPP ID map when available."""
        if self._output_scope != "roads":
            return {}

        manifest_path = self.wd / self._ROADS_SEGMENT_MANIFEST_REL_PATH
        if not manifest_path.exists():
            return {}

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            LOGGER.warning(
                "Unable to parse Roads segment manifest for hillslope watbal mapping",
                extra={"manifest_path": str(manifest_path)},
            )
            return {}

        if not isinstance(payload, list):
            return {}

        mapping: dict[int, int] = {}
        for row in payload:
            if not isinstance(row, Mapping):
                continue
            segment_run_id = row.get("segment_run_id")
            target_hillslope_wepp_id = row.get("target_hillslope_wepp_id")
            try:
                segment_id = int(segment_run_id)  # type: ignore[arg-type]
                target_id = int(target_hillslope_wepp_id)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            mapping[segment_id] = target_id
        return mapping

    def _resolve_source_path(self) -> Path:
        rel_path = scoped_dataset_path(self._SOURCE_REL_PATH, self._output_scope)
        return self.wd / rel_path

    def _resolve_cache_key(self) -> str:
        if self._output_scope == "baseline":
            return self._CACHE_KEY
        return f"{self._CACHE_KEY}_{self._output_scope}"

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

    def avg_annual_iter(self) -> Iterator[RowData]:
        """Yield Topaz-level average metrics across the simulation period."""
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

    def yearly_iter(self) -> Iterator[RowData]:
        """Yield watershed-wide yearly totals."""
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
