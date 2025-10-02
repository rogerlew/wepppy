"""NoDb scaffolding for the Batch Runner feature."""

from __future__ import annotations

from datetime import datetime, timezone
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

from wepppy.topo.watershed_collection import WatershedCollection
from wepppy.weppcloud.utils.helpers import get_batch_root_dir

from .base import NoDbBase, TriggerEvents, nodb_setter
from .redis_prep import TaskEnum

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
    DEFAULT_DIRECTIVE_KEYS: ClassVar[Tuple[str, ...]] = tuple(task.value for task in DEFAULT_TASKS)
    LEGACY_DIRECTIVE_SLUGS: ClassVar[Dict[str, str]] = {
        'acquire_rap': TaskEnum.fetch_rap_ts.value,
        'run_wepp': TaskEnum.run_wepp_watershed.value,
    }
    LABEL_OVERRIDES: ClassVar[Dict[str, str]] = {
        TaskEnum.fetch_rap_ts.value: 'Build RAP TS',
    }

    def __init__(self, wd: str, batch_config: str, base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            self._base_config = base_config
            self._geojson_state = None
            self._runid_template_state = None
            self._base_wd = os.path.join(self.wd, "_base")
            self._run_directives = {}
            self._ensure_run_directives_initialized(default=True)

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    @property
    def run_directives(self) -> Dict[str, bool]:
        self._ensure_run_directives_initialized()
        return deepcopy(self._run_directives)

    def is_task_enabled(self, task: TaskEnum) -> bool:
        self._ensure_run_directives_initialized()
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
    def _normalize_directive_key(cls, key: Any) -> Optional[str]:
        if key is None:
            return None
        slug = str(key)
        if slug in cls.LEGACY_DIRECTIVE_SLUGS:
            return cls.LEGACY_DIRECTIVE_SLUGS[slug]
        if slug in cls.DEFAULT_DIRECTIVE_KEYS:
            return slug
        return None

    def _ensure_run_directives_initialized(self, default: bool = True) -> None:
        if not isinstance(getattr(self, '_run_directives', None), dict):
            self._run_directives = {}

        for key in self.DEFAULT_DIRECTIVE_KEYS:
            self._run_directives.setdefault(key, bool(default))

    def _migrate_run_directives(self) -> None:
        directives = getattr(self, '_run_directives', None)
        if not isinstance(directives, dict):
            directives = {}

        migrated: Dict[str, bool] = {}
        for key, value in directives.items():
            normalized_key = self._normalize_directive_key(key)
            if normalized_key is None:
                continue
            migrated[normalized_key] = bool(value)

        self._run_directives = migrated
        self._ensure_run_directives_initialized()

    @classmethod
    def _post_instance_loaded(cls, instance):
        instance._migrate_run_directives()
        return instance

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
