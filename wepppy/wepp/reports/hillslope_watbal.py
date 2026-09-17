"""Hillslope-level water balance summaries sourced from H.wat interchange files."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Iterator, Mapping

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange._rust_interchange import (
    require_wepppyo3_interchange, WeppInterchangeUnavailableError,
)

from .helpers import ReportCacheManager
from ._cache_freshness import _CacheBuild, _cache_verdict, _observe_file, _read_cache
from .output_scope import normalize_output_scope, scoped_dataset_path
from .report_base import ReportBase
from .row_data import RowData, parse_units

__all__ = ["HillslopeWatbalReport", "HillslopeWatbal"]

LOGGER = logging.getLogger(__name__)


class _MappingUnavailable(FileNotFoundError):
    """Required translator resources are physically absent."""


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

        dataframe = self._load_or_build()

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

    def _historical(self, dataframe: pd.DataFrame, reason: str) -> pd.DataFrame:
        self.cache_status = "historical_unverified"
        LOGGER.warning("Using historical report cache; %s: %s (%s)",
                       reason, self.wd, self._resolve_cache_key())
        return dataframe

    def _load_or_build(self) -> pd.DataFrame:
        source = self._resolve_source_path()
        key = self._resolve_cache_key()
        cache_path = ReportCacheManager(self.wd).root / f"{key}.parquet"
        loaded = _read_cache(cache_path, key)
        if loaded is None and self._output_scope == "baseline":
            cache_path = self.wd / "wepp/output/interchange" / f"{self._CACHE_KEY}.parquet"
            loaded = _read_cache(cache_path, key, require_version=False)
        dataframe = None if loaded is None else loaded[0].to_pandas()
        proof = None if loaded is None else loaded[1]
        if dataframe is not None and not self._validate_cache_columns(dataframe):
            dataframe = None
        before = _observe_file(self.wd, source)
        if dataframe is not None and proof is not None:
            ids = proof.get("source_ids")
            if (not isinstance(ids, list) or any(type(value) is not int for value in ids)
                    or len(set(ids)) != len(ids) or (not ids and not dataframe.empty)):
                raise ValueError("Invalid report cache source IDs")
            mapping = proof["dependencies"].get("mapping")
            if (not isinstance(mapping, list) or len(mapping) != len(ids) or
                    any(not isinstance(pair, list) or len(pair) != 2 or
                        any(type(value) is not int for value in pair) for pair in mapping) or
                    sorted(pair[0] for pair in mapping) != sorted(ids)):
                raise ValueError("Invalid report cache translator mapping")
            if set(proof["dependencies"]) != {"source", "mapping"}:
                raise ValueError("Invalid report cache dependency set")
            source_verdict = _cache_verdict({"source": proof["dependencies"]["source"]}, {"source": before})
            verdict = None
            if source_verdict is not None:
                dependencies = self._dependencies(ids, before, allow_missing=True)
                verdict = _cache_verdict(proof["dependencies"], dependencies)
            if verdict is not None:
                self.cache_status = verdict
                if verdict == "historical_unverified":
                    missing = []
                    if before["sha256"] is None:
                        missing.append(str(source))
                    if dependencies["mapping"] is None:
                        missing.append("Watershed translator prerequisites")
                    return self._historical(dataframe, f"missing {', '.join(missing)}")
                return dataframe
            # A known mismatch cannot fall through to the older legacy location.
            dataframe = None
        if dataframe is not None and before["sha256"] is None:
            return self._historical(dataframe, f"missing source {source}")
        try:
            result = self._build_summary(initial_source=before)
        except _MappingUnavailable as exc:
            if dataframe is None:
                raise
            return self._historical(dataframe, str(exc))
        except WeppInterchangeUnavailableError:
            if dataframe is None or self._source_is_newer_than_cache(source, cache_path):
                raise
            return self._historical(dataframe, "native summary API unavailable")
        self.cache_status = "built"
        return result

    def _dependencies(self, ids: list[int], source: dict, *, allow_missing: bool = False) -> dict:
        try:
            mapping = self._resolve_mapping(ids)
        except _MappingUnavailable:
            if not allow_missing:
                raise
            mapping = None
        return {"source": source, "mapping": None if mapping is None else
                [[int(key), int(value)] for key, value in sorted(mapping.items())]}

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

    def _build_summary(self, *, initial_source: dict | None = None) -> pd.DataFrame:
        """Build native rows and bind observations before atomic publication."""
        source_path = self._resolve_source_path()
        before_source = initial_source if initial_source is not None else _observe_file(self.wd, source_path)
        if before_source["sha256"] is None:
            raise FileNotFoundError(source_path)
        native = require_wepppyo3_interchange(
            "hillslope water balance", "hillslope_watbal_wepp_ids", "hillslope_watbal_to_parquet"
        )
        cache_path = ReportCacheManager(self.wd).root / f"{self._resolve_cache_key()}.parquet"
        with _CacheBuild(cache_path, self._resolve_cache_key(), native_source=source_path) as attempt:
            attempt.observations = {"source_before": before_source}
            ids = native.hillslope_watbal_wepp_ids(str(source_path))
            before = self._dependencies(ids, before_source)
            attempt.observations = {"before": before, "selected_source": str(source_path.resolve())}
            mapping = dict(before["mapping"])
            table = self._write_native_summary(native, source_path, mapping, attempt)
            after = self._dependencies(ids, _observe_file(self.wd, source_path))
            attempt.observations["after"] = after
            if before != after:
                raise RuntimeError("Report dependencies changed during native build")
            dataframe = table.to_pandas()
            attempt.publish(table, before, source_ids=ids)
            return dataframe

    def _resolve_mapping(self, wepp_ids: list[int]) -> dict[int, int]:
        if not wepp_ids:
            return {}
        from wepppy.nodb.core import Watershed

        try:
            watershed = Watershed.getInstance(str(self.wd))
        except FileNotFoundError as exc:
            raise _MappingUnavailable("Watershed controller is absent") from exc
        try:
            translator = watershed.translator_factory()
        except RuntimeError as exc:
            if str(exc) != "No sub_ids/chn_ids available for translator (no summaries or parquet files)":
                raise
            # The native translator's missing-resource error is RuntimeError.
            # Prove physical absence; never hide schema/access/unknown-ID errors.
            if (getattr(watershed, "_subs_summary", None) is None or
                    getattr(watershed, "_chns_summary", None) is None):
                missing = []
                for relative in ("watershed/hillslopes.parquet", "watershed/channels.parquet"):
                    try:
                        # Inspect every surviving prerequisite before absence is
                        # classified; a missing peer must not hide denied reads.
                        with (self.wd / relative).open("rb") as incoming:
                            pq.read_schema(incoming)
                    except FileNotFoundError:
                        missing.append(relative)
                if missing:
                    raise _MappingUnavailable(f"Translator source absent: {', '.join(missing)}") from exc
            raise
        roads_segment_targets = self._load_roads_segment_target_map()
        fallback_ids: set[int] = set()
        manifest_mapped_ids: set[int] = set()
        topaz_lookup: dict[int, int] = {}

        for wepp_id in wepp_ids:
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

        return topaz_lookup

    def _write_native_summary(self, native, source_path: Path, mapping: dict[int, int],
                              attempt: _CacheBuild) -> pa.Table:
        """Keep full H.wat aggregation native; annotate only the compact result."""
        names = ["TopazID", "WaterYear", "Area_m2", *self._MEASURE_MAP.keys()]
        if mapping:
            template = pd.DataFrame({
                name: pd.Series(dtype="int64" if i < 2 else "float64")
                for i, name in enumerate(names)
            })
        else:
            template = pd.DataFrame(columns=names)
        metadata = pa.Schema.from_pandas(template, preserve_index=False).metadata[b"pandas"].decode()
        with attempt.open_payload("native.parquet"):
            pass
        candidate = attempt.root / "native.parquet"
        native.hillslope_watbal_to_parquet(
            str(source_path), str(candidate), mapping, pandas_metadata=metadata
        )
        return pq.read_table(candidate)

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
