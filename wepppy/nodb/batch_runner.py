"""NoDb scaffolding for the Batch Runner feature."""

from __future__ import annotations

from datetime import datetime, timezone
from glob import glob
import hashlib
import json
import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import re
from copy import deepcopy
import shutil
from typing import Any, Dict, Iterable, List, Optional, Tuple, Mapping, ClassVar

from wepppy.topo.watershed_collection import WatershedCollection, WatershedFeature
from wepppy.weppcloud.utils.helpers import get_batch_root_dir, get_wd

from .base import NoDbBase, TriggerEvents, nodb_setter, clear_nodb_file_cache, clear_locks
from .redis_prep import RedisPrep, TaskEnum


class BatchRunner(NoDbBase):
    """NoDb controller for batch runner state."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"

    DEFAULT_TASKS: ClassVar[Tuple[TaskEnum, ...]] = (
        TaskEnum.fetch_dem,
        TaskEnum.build_channels,
        TaskEnum.find_outlet,
        TaskEnum.build_subcatchments,
        TaskEnum.abstract_watershed,
        TaskEnum.build_landuse,
        TaskEnum.build_soils,
        TaskEnum.fetch_rap_ts,
        TaskEnum.build_climate,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_omni_contrasts,
    )

    def __init__(self, wd: str, batch_config: str, base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            self._base_config = base_config
            self._geojson_state = None
            self._runid_template_state = None
            self._base_wd = os.path.join(self.wd, "_base")
            self._run_directives = deepcopy(BatchRunner.DEFAULT_TASKS)

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    @property
    def run_directives(self) -> Dict[str, bool]:
        return self._run_directives

    def is_task_enabled(self, task: TaskEnum) -> bool:
        return bool(self._run_directives.get(task.value, True))

    def update_run_directives(self, directives: Mapping[str, Any]) -> Dict[str, bool]:
        normalized: Dict[str, bool] = {}
        if isinstance(directives, Mapping):
            for raw_key, value in directives.items():
                key = self._normalize_directive_key(raw_key)
                if key is None:
                    continue
                normalized[key] = bool(value)

        with self.locked():
            self._ensure_run_directives_initialized()
            for key in self.DEFAULT_DIRECTIVE_KEYS:
                if key in normalized:
                    self._run_directives[key] = normalized[key]

        return deepcopy(self._run_directives)

    @classmethod
    def _post_instance_loaded(cls, instance):
        instance._migrate_run_directives()
        return instance

    def run_batch_project(
        self,
        watershed_feature: WatershedFeature,
    ) -> Tuple[str, ...]:
        runid = f'batch;;{self.batch_name};;{watershed_feature.runid}'
        runid_wd = get_wd(runid)

        base_wd = self.base_wd
        if os.path.exists(runid_wd):
            shutil.rmtree(runid_wd)
        shutil.copytree(base_wd, runid_wd)

        for nodb_fn in glob(_join(runid_wd, '*.nodb')):
            with open(nodb_fn, 'r') as fp:
                state = json.load(fp)
            state.setdefault('py/state', {})['wd'] = runid_wd
            with open(nodb_fn, 'w') as fp:
                json.dump(state, fp)
                fp.flush()
                os.fsync(fp.fileno())

        clear_nodb_file_cache(runid)
        try:
            locks_cleared = clear_locks(runid)
        except RuntimeError:
            locks_cleared = None

        prep = RedisPrep.getInstance(runid_wd)

        from wepppy.nodb.ron import Ron
        from wepppy.nodb.watershed import Watershed
        from wepppy.nodb.landuse import Landuse
        from wepppy.nodb.soils import Soils
        from wepppy.nodb.climate import Climate
        from wepppy.nodb.wepp import Wepp
        from wepppy.nodb.mods.rap.rap_ts import RAP_TS

        ron = Ron.getInstance(runid_wd)
        watershed = Watershed.getInstance(runid_wd)
        landuse = Landuse.getInstance(runid_wd)
        soils = Soils.getInstance(runid_wd)
        climate = Climate.getInstance(runid_wd)
        wepp = Wepp.getInstance(runid_wd)

        if self.is_task_enabled(TaskEnum.fetch_dem) and prep[str(TaskEnum.fetch_dem)] is None:
            pad = 0.02
            bbox = watershed_feature.get_padded_bbox(pad=pad)
            map_center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            ron.set_map(bbox, center=map_center, zoom=11)
            ron.fetch_dem()
            prep.timestamp(TaskEnum.fetch_dem)

        if self.is_task_enabled(TaskEnum.build_channels) and prep[str(TaskEnum.build_channels)] is None:
            watershed.build_channels()

        if self.is_task_enabled(TaskEnum.find_outlet) and prep[str(TaskEnum.find_outlet)] is None:
            watershed.find_outlet(watershed_feature)

        if self.is_task_enabled(TaskEnum.build_subcatchments) and prep[str(TaskEnum.build_subcatchments)] is None:
            watershed.build_subcatchments()
            prep.timestamp(TaskEnum.build_subcatchments)

        if self.is_task_enabled(TaskEnum.abstract_watershed) and prep[str(TaskEnum.abstract_watershed)] is None:
            watershed.abstract_watershed()

        if self.is_task_enabled(TaskEnum.build_landuse) and prep[str(TaskEnum.build_landuse)] is None:
            landuse.build()

        if self.is_task_enabled(TaskEnum.build_soils) and prep[str(TaskEnum.build_soils)] is None:
            soils.build()

        if self.is_task_enabled(TaskEnum.build_climate) and prep[str(TaskEnum.build_climate)] is None:
            climate.build()

        rap_ts = RAP_TS.tryGetInstance(runid_wd)
        if rap_ts and self.is_task_enabled(TaskEnum.fetch_rap_ts) and prep[str(TaskEnum.fetch_rap_ts)] is None:
            rap_ts.acquire_rasters(
                start_year=climate.observed_start_year,
                end_year=climate.observed_end_year,
            )
            rap_ts.analyze()

        run_hillslopes = self.is_task_enabled(TaskEnum.run_wepp_hillslopes) and prep[str(TaskEnum.run_wepp_hillslopes)] is None
        run_watershed = self.is_task_enabled(TaskEnum.run_wepp_watershed) and prep[str(TaskEnum.run_wepp_watershed)] is None

        if run_hillslopes:
            wepp.clean()

        if run_hillslopes or run_watershed:
            wepp._check_and_set_baseflow_map()
            wepp._check_and_set_phosphorus_map()

        if run_hillslopes:
            wepp.prep_hillslopes()
            wepp.run_hillslopes()

        if run_watershed:
            wepp.prep_watershed()
            wepp.run_watershed()

        return tuple(locks_cleared) if locks_cleared else ()

    @property
    def batch_name(self) -> str:
        return os.path.basename(self.wd)

    @classmethod
    def getInstanceFromRunID(cls, runid, allow_nonexistent=False, ignore_lock=False):
        raise NotImplementedError("BatchRunner does not support getInstanceFromRunID")

    @classmethod
    def getInstanceFromBatchName(cls, batch_name: str) -> BatchRunner:
        batch_root_dir = get_batch_root_dir()
        batch_wd = _join(batch_root_dir, batch_name)
        if not _exists(batch_wd):
            raise FileNotFoundError(f"Batch '{batch_name}' does not exist. wd: {batch_wd}")
        return cls.getInstance(batch_wd)

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------
    @property
    def base_wd(self) -> str:
        return os.path.join(self.wd, "_base")
    
    @property
    def base_config(self) -> Optional[str]:
        return self._base_config

    @base_config.setter
    def base_config(self, value: Optional[str]) -> None:
        self._base_config = value

    @property
    def batch_runs_dir(self) -> str:
        return os.path.join(self.wd, "runs")

    @property
    def resources_dir(self) -> str:
        return os.path.join(self.wd, "resources")

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------
    def _init_base_project(self) -> None:
        from wepppy.nodb.ron import Ron

        if os.path.exists(self._base_wd):
            shutil.rmtree(self._base_wd)
        os.makedirs(self._base_wd)
        batch_name = self.batch_name
        if not batch_name:
            raise ValueError("Batch name cannot be empty")

        Ron(self._base_wd, self._base_config, run_group='batch', group_name=self.batch_name)


    # ------------------------------------------------------------------
    # Watershed GeoJSON
    # ------------------------------------------------------------------
    def register_geojson(self, watershed_collection: WatershedCollection) -> Dict[str, Any]:
        """Register a GeoJSON file as the watershed definition for this batch.

        Fail fast, this is model code.

        Args:
            filepath: Path to the GeoJSON file to register.
        Returns:
            A dictionary with information about the registered GeoJSON.
        """
        from wepppy.topo.watershed_collection.watershed_collection import WatershedCollection

        analysis_results = watershed_collection.analysis_results   # lazy runs analysis

        if analysis_results["feature_count"] == 0:
            os.remove(watershed_collection.geojson_filepath)
            raise ValueError("GeoJSON contains no features.")
        
        # Update state
        with self.locked():
            self._geojson_state = analysis_results
            if self._runid_template_state:
                stale_state = deepcopy(self._runid_template_state)
                stale_state["status"] = "stale"
                summary = stale_state.get("summary") or {}
                summary["is_valid"] = False
                stale_state["summary"] = summary
                self._runid_template_state = stale_state

    def get_watershed_collection(self) -> WatershedCollection:
        """Get the registered watershed collection, if any."""
        if not self._geojson_state:
            raise ValueError("No GeoJSON registered.")    
        return WatershedCollection.load_from_analysis_results(self._geojson_state)

    @property
    def geojson_state(self) -> Optional[Dict[str, Any]]:
        if not self._geojson_state:
            return None
        return deepcopy(self._geojson_state)
    
    @property
    def runid_template_state(self) -> Optional[Dict[str, Any]]:
        return self._runid_template_state

    @runid_template_state.setter
    @nodb_setter
    def runid_template_state(self, value: Optional[Dict[str, Any]]) -> None:
        self._runid_template_state = value

__all__ = ["BatchRunner"]
