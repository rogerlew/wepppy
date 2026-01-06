"""NoDb scaffolding for culvert batch runs."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from glob import glob
import json
import os
from os.path import exists as _exists
from os.path import join as _join
import shutil
from typing import Any, Dict, List, Optional, Tuple

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core import Ron, Watershed
from wepppy.weppcloud.utils.helpers import get_wd


__all__ = ["CulvertsRunner"]


class CulvertsRunner(NoDbBase):
    """NoDb controller for culvert batch state."""

    __name__ = "CulvertsRunner"
    filename = "culverts_runner.nodb"

    DEFAULT_RETENTION_DAYS = 7
    DEFAULT_DEM_REL_PATH = "topo/hydro-enforced-dem.tif"
    DEFAULT_WATERSHEDS_REL_PATH = "culverts/watersheds.geojson"
    DEFAULT_FLOVEC_REL_PATH = "topo/flovec.tif"
    DEFAULT_NETFUL_REL_PATH = "topo/netful.tif"
    DEFAULT_BASE_DIRNAME = "_base"
    POINT_ID_FIELD = "Point_ID"

    def __init__(self, wd: str, cfg_fn: str = "culvert.cfg") -> None:
        super().__init__(wd, cfg_fn)
        with self.locked():
            self._culvert_batch_uuid: Optional[str] = None
            self._payload_metadata: Optional[Dict[str, Any]] = None
            self._model_parameters: Optional[Dict[str, Any]] = None
            self._runs: Dict[str, Dict[str, Any]] = {}
            self._created_at: str = datetime.now(timezone.utc).isoformat()
            self._completed_at: Optional[str] = None
            self._retention_days: Optional[int] = None
            self._run_config: str = cfg_fn

        os.makedirs(self.runs_dir, exist_ok=True)

    @property
    def runs_dir(self) -> str:
        return _join(self.wd, "runs")

    @property
    def base_wd(self) -> str:
        return _join(self.wd, self.DEFAULT_BASE_DIRNAME)

    @property
    def base_runid(self) -> Optional[str]:
        override = self._get_model_param_str(
            getattr(self, "_model_parameters", None), "base_project_runid"
        )
        if override is not None:
            return override
        return self.config_get_str("culvert_runner", "base_runid")

    @property
    def culvert_batch_uuid(self) -> Optional[str]:
        return getattr(self, "_culvert_batch_uuid", None)

    @property
    def payload_metadata(self) -> Optional[Dict[str, Any]]:
        if self._payload_metadata is None:
            return None
        return deepcopy(self._payload_metadata)

    @property
    def model_parameters(self) -> Optional[Dict[str, Any]]:
        if self._model_parameters is None:
            return None
        return deepcopy(self._model_parameters)

    @property
    def runs(self) -> Dict[str, Dict[str, Any]]:
        return deepcopy(self._runs)

    @property
    def completed_at(self) -> Optional[str]:
        return getattr(self, "_completed_at", None)

    @property
    def retention_days(self) -> Optional[int]:
        return getattr(self, "_retention_days", None)

    @property
    def run_config(self) -> str:
        return getattr(self, "_run_config", "culvert.cfg")

    def create_runs(
        self,
        culvert_batch_uuid: str,
        batch_root: str,
        payload_metadata: Dict[str, Any],
        model_parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ...]:
        if not culvert_batch_uuid:
            raise ValueError("culvert_batch_uuid is required")
        if not isinstance(payload_metadata, dict):
            raise TypeError("payload_metadata must be a dict")
        if model_parameters is not None and not isinstance(model_parameters, dict):
            raise TypeError("model_parameters must be a dict")

        abs_batch_root = os.path.abspath(batch_root)
        if abs_batch_root != os.path.abspath(self.wd):
            raise ValueError("batch_root must match CulvertsRunner working directory")

        dem_src = self._resolve_payload_path(
            payload_metadata, "dem", self.DEFAULT_DEM_REL_PATH, abs_batch_root
        )
        watersheds_src = self._resolve_payload_path(
            payload_metadata,
            "watersheds",
            self.DEFAULT_WATERSHEDS_REL_PATH,
            abs_batch_root,
        )
        flovec_src = _join(abs_batch_root, self.DEFAULT_FLOVEC_REL_PATH)
        netful_src = _join(abs_batch_root, self.DEFAULT_NETFUL_REL_PATH)

        for path_label, path in (
            ("DEM", dem_src),
            ("watersheds", watersheds_src),
            ("flovec", flovec_src),
            ("netful", netful_src),
        ):
            if not _exists(path):
                raise FileNotFoundError(f"{path_label} file does not exist: {path}")

        run_ids = self._load_run_ids(watersheds_src)

        run_config = self._resolve_run_config(model_parameters)

        with self.locked():
            self._culvert_batch_uuid = culvert_batch_uuid
            self._payload_metadata = deepcopy(payload_metadata)
            self._model_parameters = deepcopy(model_parameters) if model_parameters else None
            self._runs = {}
            self._run_config = run_config

        self._ensure_base_project()
        os.makedirs(self.runs_dir, exist_ok=True)

        created: List[str] = []
        for run_id in run_ids:
            run_wd = _join(self.runs_dir, run_id)
            if _exists(_join(run_wd, "ron.nodb")):
                raise FileExistsError(f"Run already exists: {run_wd}")
            os.makedirs(run_wd, exist_ok=True)

            ron = Ron(run_wd, run_config, run_group="culvert", group_name=culvert_batch_uuid)
            ron.symlink_dem(dem_src)

            watershed = Watershed.getInstance(run_wd)
            watershed.symlink_channels_map(flovec_src, netful_src)

            created_at = datetime.now(timezone.utc).isoformat()
            run_record = {
                "runid": run_id,
                "point_id": run_id,
                "wd": run_wd,
                "created_at": created_at,
            }
            with self.locked():
                self._runs[run_id] = run_record

            created.append(run_id)

        return tuple(created)

    def run(
        self,
        culvert_batch_uuid: str,
        batch_root: str,
        payload_metadata: Dict[str, Any],
        model_parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ...]:
        run_ids = self.create_runs(
            culvert_batch_uuid,
            batch_root,
            payload_metadata,
            model_parameters=model_parameters,
        )
        with self.locked():
            self._completed_at = datetime.now(timezone.utc).isoformat()
            self._retention_days = self.DEFAULT_RETENTION_DAYS
        return run_ids

    def _ensure_base_project(self) -> Optional[str]:
        base_runid = self.base_runid
        if not base_runid:
            return None

        dest = self.base_wd
        if _exists(dest):
            return dest

        src = get_wd(base_runid, prefer_active=False)
        if not _exists(src):
            raise FileNotFoundError(f"Base runid path does not exist: {src}")

        shutil.copytree(src, dest, symlinks=True)

        for nodb_fn in glob(_join(dest, "*.nodb")):
            with open(nodb_fn, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if "py/state" in state:
                state["py/state"]["wd"] = dest
            else:
                state["wd"] = dest
            with open(nodb_fn, "w", encoding="utf-8") as handle:
                json.dump(state, handle)
                handle.flush()
                os.fsync(handle.fileno())

        return dest

    def _resolve_payload_path(
        self,
        payload_metadata: Dict[str, Any],
        section: str,
        default_relpath: str,
        batch_root: str,
    ) -> str:
        section_data = payload_metadata.get(section) or {}
        relpath = section_data.get("path") if isinstance(section_data, dict) else None
        relpath = relpath or default_relpath
        if os.path.isabs(relpath):
            return relpath
        return _join(batch_root, relpath)

    def _resolve_run_config(
        self, model_parameters: Optional[Dict[str, Any]]
    ) -> str:
        config = self._config or "culvert.cfg"
        nlcd_db = self._get_model_param_str(model_parameters, "nlcd_db")
        if nlcd_db is None:
            return config
        separator = "&" if "?" in config else "?"
        return f"{config}{separator}landuse:nlcd_db={nlcd_db}"

    def _get_model_param_str(
        self, model_parameters: Optional[Dict[str, Any]], key: str
    ) -> Optional[str]:
        if not model_parameters:
            return None
        value = model_parameters.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError(f"model_parameters.{key} must be a string")
        if value == "":
            raise ValueError(f"model_parameters.{key} must be non-empty")
        return value

    def _load_run_ids(self, watersheds_src: str) -> List[str]:
        with open(watersheds_src, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("Watersheds GeoJSON contains no features")

        run_ids: List[str] = []
        seen: set[str] = set()
        for idx, feature in enumerate(features):
            props = (feature or {}).get("properties") or {}
            if self.POINT_ID_FIELD not in props:
                raise ValueError(
                    f"Feature {idx} missing {self.POINT_ID_FIELD} property in watersheds GeoJSON"
                )
            point_id = props.get(self.POINT_ID_FIELD)
            if point_id is None or point_id == "":
                raise ValueError(f"Feature {idx} has empty {self.POINT_ID_FIELD} value")
            run_id = str(point_id)
            if run_id in seen:
                raise ValueError(f"Duplicate Point_ID detected: {run_id}")
            seen.add(run_id)
            run_ids.append(run_id)

        return run_ids
