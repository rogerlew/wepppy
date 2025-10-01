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
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wepppy.topo.watershed_collection import WatershedCollection
from wepppy.weppcloud.utils.helpers import get_batch_root_dir

from .base import NoDbBase, TriggerEvents, nodb_setter

from enum import Enum

class RunDirectiveEnum(str, Enum):
    FETCH_DEM = "fetch_dem"
    BUILD_CHANNELS = "build_channels"
    FIND_OUTLET = "find_outlet"
    BUILD_SUBCATCHMENTS = "build_subcatchments"
    ABSTRACT_WATERSHED = "abstract_watershed"
    BUILD_LANDUSE = "build_landuse"
    BUILD_SOILS = "build_soils"
    ACQUIRE_RAP = "acquire_rap"


class BatchRunner(NoDbBase):
    """NoDb controller for batch runner state."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"

    def __init__(self, wd: str, batch_config: str, base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            self._base_config = base_config
            self._geojson_state = None
            self._runid_template_state = None
            self._base_wd = os.path.join(self.wd, "_base")
            self._run_directives = {}
            for rd in RunDirectiveEnum:
                self._run_directives[rd.value] = True

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    @property
    def run_directives(self) -> Dict[str, bool]:
        return self._run_directives

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

__all__ = ["BatchRunner", "RunDirectiveEnum"]
