"""NoDb scaffolding for the Batch Runner feature."""

from __future__ import annotations

from datetime import datetime, timezone
from glob import glob
import hashlib
import json
import os
import logging
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import re
from copy import deepcopy
import shutil
from typing import Any, Dict, Iterable, List, Optional, Tuple, Mapping, ClassVar

from wepppy.topo.watershed_collection import WatershedCollection, WatershedFeature
from wepppy.weppcloud.utils.helpers import get_batch_root_dir, get_wd

from wepppy.nodb.core import *
from wepppy.nodb.mods.rap.rap_ts import RAP_TS


from .base import NoDbBase, TriggerEvents, nodb_setter, clear_nodb_file_cache, clear_locks
from .redis_prep import RedisPrep, TaskEnum


__all__ = [
    'BatchRunner',
]


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value: {value!r}")


class BatchRunner(NoDbBase):
    """NoDb controller for batch runner state."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"

    RESOURCE_WATERSHED: ClassVar[str] = "watershed_geojson"

    DEFAULT_TASKS: ClassVar[Tuple[TaskEnum, ...]] = (
        TaskEnum.if_exists_rmtree,
        TaskEnum.fetch_dem,
        TaskEnum.build_channels,
        TaskEnum.find_outlet,
        TaskEnum.build_subcatchments,
        TaskEnum.abstract_watershed,
        TaskEnum.build_landuse,
        TaskEnum.build_soils,
        TaskEnum.build_climate,
        TaskEnum.fetch_rap_ts,
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
            self._run_directives = {task: True for task in self.DEFAULT_TASKS}
            self._run_directives[TaskEnum.if_exists_rmtree] = False

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

    def __getstate__(self):
        """
        serialize _run_directives keys to strings to make deserialization easier
        """

        state = super().__getstate__()
        directives = state.get('_run_directives')

        if directives:
            storable_directives = {
                (k.value if isinstance(k, TaskEnum) else str(k)): v
                for k, v in directives.items()
            }
            state['_run_directives'] = storable_directives
            
        return state

    @classmethod
    def _post_instance_loaded(cls, instance):
        """
        deserialize _run_directives keys from strings to TaskEnum
        """
        instance = super()._post_instance_loaded(instance)
        if instance._run_directives:
            instance._run_directives = {
                TaskEnum(k): v for k, v in instance._run_directives.items()
            }
        return instance

    # ------------------------------------------------------------------
    # run directives
    # ------------------------------------------------------------------
    @property
    def run_directives(self) -> Dict[TaskEnum, bool]:
        return self._run_directives

    def is_task_enabled(self, task: TaskEnum) -> bool:
        return bool(self._run_directives.get(task, True))

    def update_run_directives(self, directives: Mapping[str, Any]) -> Dict[str, bool]:
        
        if not isinstance(directives, Mapping):
            self.logger.warning(f"Invalid directives type: {type(directives)}")
            
        with self.locked():
            for raw_key, value in directives.items():
                try:
                    task = TaskEnum(raw_key)
                except ValueError:
                    self.logger.warning(f"Unrecognized task directive key: {raw_key}: {value}")
                    continue

                try:
                    coerced_value = _coerce_bool(value)
                except ValueError:
                    self.logger.warning(f"Invalid task directive value: {raw_key}: {value}")
                    continue

                if task in self._run_directives:
                    self._run_directives[task] = coerced_value
                    self.logger.info(f"Updated task directive: {task} = {coerced_value}")

        return deepcopy(self._run_directives)

    # ------------------------------------------------------------------
    # project runner
    # ------------------------------------------------------------------
    def _get_run_logger(self, _runid):
        log_path = os.path.join(self.logs_dir, f"batch_runner_{_runid}.log")
        logger = logging.getLogger(f"batch.{self.batch_name}.{_runid}")
        logger.setLevel(logging.DEBUG)
        if logger.hasHandlers():
            logger.handlers.clear()
        handler = logging.FileHandler(log_path, mode='a')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info(f"Logger initialized for runid: {_runid}")
        return logger

    def run_batch_project(
        self,
        watershed_feature: WatershedFeature,
        job_id: Optional[str] = None,
    ) -> Tuple[str, ...]:
        runid = f'batch;;{self.batch_name};;{watershed_feature.runid}'
        runid_wd = get_wd(runid)

        # setup file logger for this run
        logger = self._get_run_logger(watershed_feature.runid)
        logger.info(f"Starting batch run for runid: {runid}")
        if job_id:
            logger.info(f"RQ jobid: {job_id}")

        base_wd = self.base_wd
        logger.info(f'base_wd: {base_wd}')
        init_required = False
        if os.path.exists(runid_wd) and self.is_task_enabled(TaskEnum.fetch_dem):
            logger.info(f'removing existing runid_wd: {runid_wd}')
            shutil.rmtree(runid_wd)
            init_required = True

        if not os.path.exists(runid_wd):
            init_required = True
        
        logger.info(f'init_required: {init_required}')
        prep = None
        locks_cleared = None
        if init_required:
            logger.info(f'copying base project to runid_wd: {runid_wd}')
            shutil.copytree(base_wd, runid_wd)

            logger
            for nodb_fn in glob(_join(runid_wd, '*.nodb')):
                with open(nodb_fn, 'r') as fp:
                    state = json.load(fp)
                state.setdefault('py/state', {})['wd'] = runid_wd
                with open(nodb_fn, 'w') as fp:
                    json.dump(state, fp)
                    fp.flush()
                    os.fsync(fp.fileno())
            clear_nodb_file_cache(runid)
            logger.info('cleared NoDb file cache')
            try:
                locks_cleared = clear_locks(runid)
                logger.info(f'cleared NoDb locks: {locks_cleared}')
            except RuntimeError:
                pass

            try:
                watershed_feature.save_geojson(_join(runid_wd, 'dem','target_watershed.geojson'))
                if _exists(_join(runid_wd, 'dem','target_watershed.geojson')):
                    logger.info('saved watershed GeoJSON to dem/target_watershed.geojson')
                    ron = Ron.getInstance(runid_wd)
                    with ron.locked():
                        ron._boundary = f'/weppcloud/runs/batch;;{self.batch_name};;{watershed_feature.runid}/browse/dem/target_watershed.geojson'
                        ron._boundary_color = 'blue'
                        ron._boundary_name = 'target_watershed'

            except Exception as e:
                logger.error(f"Failed to save GeoJSON: {e}")

        logger.info('getting RedisPrep instance')
        prep = RedisPrep.getInstance(runid_wd)
        logger.info(prep.timestamps_report())

        if init_required:
            logger.info(f'init_required: {init_required} removing all RedisPrep timestamps')
            prep.remove_all_timestamp()
            logger.info(prep.timestamps_report())

        logger.info('getting NoDb instances')
        ron = Ron.getInstance(runid_wd)
        watershed = Watershed.getInstance(runid_wd)
        landuse = Landuse.getInstance(runid_wd)
        soils = Soils.getInstance(runid_wd)
        climate = Climate.getInstance(runid_wd)
        wepp = Wepp.getInstance(runid_wd)
        
        if self.is_task_enabled(TaskEnum.fetch_dem) and prep[str(TaskEnum.fetch_dem)] is None:
            logger.info('fetching DEM')
            pad = 0.02
            bbox = watershed_feature.get_padded_bbox(pad=pad)
            map_center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            ron.set_map(bbox, center=map_center, zoom=11)
            ron.fetch_dem()

        if self.is_task_enabled(TaskEnum.build_channels) and prep[str(TaskEnum.build_channels)] is None:
            logger.info(f'building channels')
            watershed.build_channels()

        if self.is_task_enabled(TaskEnum.find_outlet) and prep[str(TaskEnum.find_outlet)] is None:
            logger.info(f'finding outlet')
            watershed.find_outlet(watershed_feature)

        if self.is_task_enabled(TaskEnum.build_subcatchments) and prep[str(TaskEnum.build_subcatchments)] is None:
            logger.info(f'building subcatchments')
            watershed.build_subcatchments()

        if self.is_task_enabled(TaskEnum.abstract_watershed) and prep[str(TaskEnum.abstract_watershed)] is None:
            logger.info(f'abstracting watershed')
            watershed.abstract_watershed()

        if self.is_task_enabled(TaskEnum.build_landuse) and prep[str(TaskEnum.build_landuse)] is None:
            logger.info(f'building landuse')
            landuse.build()

        if self.is_task_enabled(TaskEnum.build_soils) and prep[str(TaskEnum.build_soils)] is None:
            logger.info(f'building soils')
            soils.build()

        if self.is_task_enabled(TaskEnum.build_climate) and prep[str(TaskEnum.build_climate)] is None:
            logger.info(f'building climate')
            climate.build()

        rap_ts = RAP_TS.tryGetInstance(runid_wd)
        logger.info(f'rap_ts: {rap_ts}')
        if rap_ts and self.is_task_enabled(TaskEnum.fetch_rap_ts) \
            and prep[str(TaskEnum.fetch_rap_ts)] is None:
            logger.info(f'fetching RAP TS')
            rap_ts.acquire_rasters(
                start_year=climate.observed_start_year,
                end_year=climate.observed_end_year,
            )
            logger.info(f'analyzing RAP TS')
            rap_ts.analyze()

        run_hillslopes = self.is_task_enabled(TaskEnum.run_wepp_hillslopes) \
            and prep[str(TaskEnum.run_wepp_hillslopes)] is None
        run_watershed = self.is_task_enabled(TaskEnum.run_wepp_watershed) \
            and prep[str(TaskEnum.run_wepp_watershed)] is None

        logger.info(f'run_hillslopes: {run_hillslopes}')
        logger.info(f'run_watershed: {run_watershed}')

        if run_hillslopes:
            logger.info('calling wepp.clean()')
            wepp.clean()

        if run_hillslopes or run_watershed:
            logger.info('calling wepp._check_and_set_baseflow_map()')
            wepp._check_and_set_baseflow_map()
            logger.info('calling wepp._check_and_set_phosphorus_map()')
            wepp._check_and_set_phosphorus_map()

        if run_hillslopes:
            logger.info('calling wepp.prep_hillslopes()')
            wepp.prep_hillslopes()
            logger.info('calling wepp.run_hillslopes()')
            wepp.run_hillslopes()

        if run_watershed:
            logger.info('calling wepp.prep_watershed()')
            wepp.prep_watershed()
            logger.info('calling wepp.run_watershed()')
            wepp.run_watershed()  # also triggers post wepp processing

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
    
    @property
    def logs_dir(self) -> str:
        return os.path.join(self.wd, "logs")

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------
    def _init_base_project(self) -> None:
        from wepppy.nodb.core import Ron

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
    def register_geojson(self, watershed_collection: WatershedCollection, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

        if metadata:
            enriched_results = deepcopy(analysis_results)
            enriched_results.update(metadata)
        else:
            enriched_results = analysis_results
        
        # Update state
        with self.locked():
            self._geojson_state = enriched_results
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
            raise ValueError("Upload a GeoJSON resource before validating.")
        
        return WatershedCollection.load_from_analysis_results(
            self._geojson_state, self._runid_template_state)

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

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def generate_runstate_report(self) -> Dict[str, Any]:
        watershed_collection = self.get_watershed_collection()

        report = {}
        for wf in watershed_collection:
            _runid = wf.runid
            run_states = {str(task): None for task in BatchRunner.DEFAULT_TASKS}
            run_wd = _join(self.wd, "runs", _runid)
            if _exists(run_wd):
                prep = RedisPrep.getInstance(run_wd)
                for task in BatchRunner.DEFAULT_TASKS:
                    run_states[str(task)] = prep[task]
                
            report[_runid] = {
                "runid": _runid,
                "run_state": run_states,
            }
        return report

    def state_dict(self) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            "batch_name": self.batch_name,
            "base_config": self.base_config,
            "resources": {},
            "metadata": {},
            "runid_template": None,
            "run_directives": [],
        }

        if self._geojson_state:
            snapshot["resources"][self.RESOURCE_WATERSHED] = deepcopy(self._geojson_state)

        if self._runid_template_state:
            snapshot["metadata"]["template_validation"] = deepcopy(self._runid_template_state)
            snapshot["runid_template"] = self._runid_template_state.get("template")

        for task in self.DEFAULT_TASKS:
            snapshot["run_directives"].append({
                "slug": task.value,
                "label": task.label(),
                "enabled": bool(self._run_directives.get(task, True)),
            })

        return snapshot

    def generate_runstate_cli_report(self) -> Dict[str, Any]:
        from wcwidth import wcswidth
        watershed_collection = self.get_watershed_collection()

        s = []
        for wf in watershed_collection:
            _runid = wf.runid
            run_states = {task.value: None for task in BatchRunner.DEFAULT_TASKS}
            run_wd = _join(self.wd, "runs", _runid)
            if _exists(run_wd):
                prep = RedisPrep.getInstance(run_wd)
                for task in BatchRunner.DEFAULT_TASKS:
                    run_states[task.value] = prep[task]
                
            _checked_states = ''.join(
                TaskEnum(k).emoji() if v is not None else ' ' for k, v in run_states.items())
            s.append(f'{_runid:10} {_checked_states}')

        # arrange in columns
        n_cols = 6

        # 2. Use wcswidth instead of len to get the true visual width
        col_width = max(wcswidth(line) for line in s) + 4 

        rows = [s[i:i+n_cols] for i in range(0, len(s), n_cols)]
        formatted_rows = []
        for row in rows:
            # 3. Use a helper function for padding since f-string padding is based on len()
            formatted_row = ''.join(f"{item}{' ' * (col_width - wcswidth(item))}" for item in row)
            formatted_rows.append(formatted_row)
        cli_report = '\n'.join(formatted_rows)

        # clear screen and print
        cli_report = '\033c' + cli_report

        print(cli_report)
