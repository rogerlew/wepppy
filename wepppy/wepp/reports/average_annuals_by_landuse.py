"""Average annual landuse summaries backed by query-engine parquet joins."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path
from typing import Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.query_engine.payload import QueryRequest
from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import _apply_identifier_aliases, _find_parent_run_root, _resolve_dataset_path

from .helpers import ReportCacheManager, ReportQueryContext
from ._cache_freshness import _CacheBuild, _cache_verdict, _observe_file, _read_cache
from .report_base import ReportBase
from .row_data import RowData

__all__ = ["AverageAnnualsByLanduseReport", "AverageAnnualsByLanduse"]

_LOG = logging.getLogger(__name__)


def _normalize_report_context(context: ReportQueryContext, selected_paths: tuple[str, ...]) -> None:
    """Rebase a saved catalog in memory for both report SQL and observations."""
    run_context = context.context
    current_root = run_context.base_dir.resolve()
    old_root = context.catalog.root.resolve()
    if old_root == current_root:
        return
    entries = []
    for entry in context.catalog.entries():
        if entry.path not in selected_paths:
            entries.append(replace(entry))
            continue
        selected = entry.fs_path
        if selected and Path(selected).is_absolute():
            try:
                _resolve_dataset_path(current_root, selected, entry.path)
            except ValueError:
                # An explicit current allowed-root selection wins. Only a
                # validated old-root/old-parent relationship may be translated.
                original = _resolve_dataset_path(old_root, selected, entry.path)
                if original.is_relative_to(old_root):
                    target = current_root / original.relative_to(old_root)
                else:
                    old_parent = _find_parent_run_root(old_root)
                    new_parent = _find_parent_run_root(current_root)
                    if old_parent is None or new_parent is None:
                        raise ValueError("Relocated report parent input requires an allowed parent run")
                    target = new_parent / original.relative_to(old_parent)
                selected = str(_resolve_dataset_path(current_root, str(target), entry.path))
        entries.append(replace(entry, fs_path=selected))
    context._context = replace(run_context, catalog=DatasetCatalog(current_root, entries))


class AverageAnnualsByLanduseReport(ReportBase):
    """Summarize average annual hydrologic metrics per landuse using query-engine assets."""

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

        dataframe = self._load_or_build()

        self._dataframe = dataframe
        self.header = dataframe.columns.tolist()

    def _observe_inputs(self, *, history_dependencies: dict | None = None, before_files: dict | None = None):
        paths = (self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET)
        catalog_path = self.wd / "_query_engine/catalog.json"
        absent_catalog = False
        try:
            catalog_path.stat()
        except FileNotFoundError:
            absent_catalog = True
        history_without_catalog = absent_catalog and (history_dependencies is not None or
                                                    any(not (self.wd / path).exists() for path in paths))
        context = ReportQueryContext(self.wd, run_interchange=False, auto_activate=not history_without_catalog)
        if history_without_catalog:
            context._context = RunContext(str(self.wd), self.wd, None, DatasetCatalog(self.wd, []))
        _normalize_report_context(context, paths)
        # Repair an incomplete catalog only for actually present local sources,
        # retaining historical reads when a required source has been archived.
        present = [path for path in paths if not context.catalog.has(path) and (self.wd / path).is_file()]
        if present and not history_without_catalog:
            context.ensure_datasets(*present)
            _normalize_report_context(context, paths)
        dependencies = {}
        for logical in paths:
            entry = context.catalog.get(logical)
            selected_path = entry.fs_path if entry and entry.fs_path else logical
            if history_without_catalog and history_dependencies is not None:
                # Historical evidence selects what can still be checked; it is
                # never query authority or proof of a current catalog selection.
                selected_path = str((self.wd / history_dependencies[logical]["path"]).absolute())
            selected = _resolve_dataset_path(context.catalog.root, selected_path, logical)
            previous = None if before_files is None else before_files.get(logical)
            selected_identity = os.path.relpath(selected.resolve(), self.wd.resolve())
            # Reuse only this build's observation made before catalog acquisition,
            # never an accepted cache digest. The post-query check remains fresh.
            observation = (previous if previous is not None and previous["path"] == selected_identity
                           else _observe_file(self.wd, selected))
            dependencies[logical] = observation
            dependencies[f"{logical}:aliases"] = (
                None if entry is None else
                _apply_identifier_aliases("selected_reader", logical, context.catalog)
            )
        return context, dependencies

    def _load_or_build(self) -> pd.DataFrame:
        cache_path = ReportCacheManager(self.wd).root / f"{self._CACHE_KEY}.parquet"
        loaded = _read_cache(cache_path, self._CACHE_KEY)
        dataframe = None if loaded is None else loaded[0].to_pandas()
        proof = None if loaded is None else loaded[1]
        if dataframe is not None and list(dataframe.columns) != self._DISPLAY_COLUMNS:
            dataframe = None
        history = None if proof is None else proof["dependencies"]
        if history is not None:
            paths = (self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET)
            if set(history) != {*paths, *(f"{path}:aliases" for path in paths)}:
                raise ValueError("Invalid report cache dependency set")
            _cache_verdict(history, history)  # Validate before any historical path use.
        context, before = self._observe_inputs(history_dependencies=history if dataframe is not None else None)
        missing = [key for key, value in before.items()
                   if isinstance(value, dict) and value["sha256"] is None]
        if dataframe is not None:
            verdict = ("historical_unverified" if missing else None) if proof is None else _cache_verdict(
                proof["dependencies"], before)
            if verdict is not None:
                self.cache_status = verdict
                if verdict == "historical_unverified":
                    if proof is None:
                        # Unverified history has no prior digest to validate the
                        # surviving files against. Parse actual available tables.
                        for logical in (self._LOSS_DATASET, self._HILLSLOPE_DATASET, self._LANDUSE_DATASET):
                            if before[logical]["sha256"] is not None:
                                pq.read_table(self.wd / before[logical]["path"])
                    _LOG.warning("Using historical landuse report cache; incomplete catalog or missing sources %s: %s", self.wd, missing)
                return dataframe
        if not missing and any(value is None for value in before.values()):
            # Historical paths/unknown aliases cannot authorize a new query.
            # Acquire its normal catalog, retaining this attempt's earlier file
            # observations only when the selected physical paths still agree.
            context, before = self._observe_inputs(before_files=before)
            missing = [key for key, value in before.items()
                       if value is None or (isinstance(value, dict) and value["sha256"] is None)]
        if missing:
            raise FileNotFoundError(f"Missing report inputs: {', '.join(missing)}")
        with _CacheBuild(cache_path, self._CACHE_KEY) as attempt:
            attempt.observations = {"before": before, "selected_paths": {
                logical: str((self.wd / value["path"]).resolve())
                for logical, value in before.items() if isinstance(value, dict)
            }}
            dataframe = self._build_dataframe(context=context)
            table = pa.Table.from_pandas(dataframe, preserve_index=False)
            with attempt.open_payload("query.parquet") as outgoing:
                pq.write_table(table, outgoing)
            _, after = self._observe_inputs()
            attempt.observations["after"] = after
            if before != after:
                raise RuntimeError("Report dependencies changed during landuse query")
            attempt.publish(table, before)
        self.cache_status = "built"
        return dataframe

    def _build_dataframe(self, *, context: ReportQueryContext | None = None) -> pd.DataFrame:
        """Query DuckDB for the joined loss, hillslope, and landuse metrics."""
        if context is None:
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
                    "left_on": ["wepp_id"],
                    "right_on": ["wepp_id"],
                },
                {
                    "left": "hills",
                    "right": "lu",
                    "left_on": ["topaz_id"],
                    "right_on": ["topaz_id"],
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
        """Return an empty dataframe shaped like the display schema."""
        return pd.DataFrame({column: [] for column in self._DISPLAY_COLUMNS}, columns=self._DISPLAY_COLUMNS)

    def __iter__(self) -> Iterator[RowData]:
        """Yield ``RowData`` objects for each summarized landuse row."""
        for record in self._dataframe.to_dict(orient="records"):
            yield RowData(record)


# Backwards compatibility.
AverageAnnualsByLanduse = AverageAnnualsByLanduseReport
