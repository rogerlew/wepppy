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
import numpy as np
import rasterio

from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.all_your_base.geo.vrt import calculate_src_window
from wepppy.nodb.base import NoDbBase, clear_nodb_file_cache, clear_locks, nodb_setter
from wepppy.nodb.core import Map, Ron, Watershed
from wepppy.topo.watershed_collection import WatershedFeature
from wepppy.topo.watershed_collection.watershed_collection import _extract_geojson_crs
from wepppy.weppcloud.utils.helpers import get_wd


__all__ = ["CulvertsRunner"]


def _sum_masked_raster(stream_path: str, mask_path: str) -> float:
    with rasterio.open(stream_path) as src_stream:
        stream_arr = src_stream.read(1)
        # Identify the nodata value for the stream network
        stream_nodata = src_stream.nodata

    with rasterio.open(mask_path) as src_mask:
        mask_arr = src_mask.read(1)
        # Identify the nodata value for the mask
        mask_nodata = src_mask.nodata

    # Create a boolean mask: True where mask is 1 (or not NoData)
    # Adjust 'mask_arr == 1' if your mask uses a different value
    boolean_mask = (mask_arr != mask_nodata) & (mask_arr > 0)

    # Filter out stream NoData values and apply the watershed mask
    valid_pixels = stream_arr[(stream_arr != stream_nodata) & boolean_mask]

    return float(np.sum(valid_pixels))


def _symlink_matches(dest: str, src: str) -> bool:
    if not os.path.islink(dest):
        return False
    return os.path.realpath(dest) == os.path.abspath(src)


class CulvertsRunner(NoDbBase):
    """NoDb controller for culvert batch state."""

    __name__ = "CulvertsRunner"
    filename = "culverts_runner.nodb"

    DEFAULT_RETENTION_DAYS = 7
    DEFAULT_DEM_REL_PATH = "topo/breached_filled_DEM_UTM.tif"
    DEFAULT_WATERSHEDS_REL_PATH = "culverts/watersheds.geojson"
    DEFAULT_CULVERT_POINTS_REL_PATH = "culverts/culvert_points.geojson"
    DEFAULT_FLOVEC_REL_PATH = "topo/flovec.tif"
    DEFAULT_FULL_STREAM_REL_PATH = "topo/streams.tif"
    DEFAULT_STREAMS_CHNJNT_REL_PATH = "topo/chnjnt.streams.tif"
    DEFAULT_NETFUL_REL_PATH = "topo/netful.tif"
    DEFAULT_CHNJNT_REL_PATH = "topo/chnjnt.tif"
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
            self._summary: Optional[Dict[str, Any]] = None
            self._rq_job_ids: Dict[str, str] = {}
            self._run_config: str = cfg_fn
            order_reduction = self.config_get_int(
                "culvert_runner", "order_reduction_passes", 1
            )
            if order_reduction is None:
                order_reduction = 1
            if order_reduction < 0:
                raise ValueError("order_reduction_passes must be >= 0")
            self._order_reduction_passes = order_reduction
            order_reduction_mode = self.config_get_str(
                "culvert_runner", "order_reduction_mode", "fixed"
            )
            if order_reduction_mode is None:
                order_reduction_mode = "fixed"
            order_reduction_mode = order_reduction_mode.lower()
            if order_reduction_mode not in {"fixed", "map"}:
                raise ValueError("order_reduction_mode must be 'fixed' or 'map'")
            self._order_reduction_mode = order_reduction_mode
            crop_pad_px = self.config_get_int("culvert_runner", "crop_pad_px", 5)
            if crop_pad_px is None:
                crop_pad_px = 5
            if crop_pad_px < 0:
                raise ValueError("crop_pad_px must be >= 0")
            self._crop_pad_px = crop_pad_px
            buffer_m = self.config_get_float(
                "culvert_runner", "contains_point_buffer_m", None
            )
            if buffer_m is not None:
                buffer_m = float(buffer_m)
                if buffer_m < 0:
                    raise ValueError("contains_point_buffer_m must be >= 0")
                if buffer_m == 0:
                    buffer_m = None
            buffer_px = self.config_get_int(
                "culvert_runner", "contains_point_buffer_px", 0
            )
            if buffer_px is None:
                buffer_px = 0
            if buffer_px < 0:
                raise ValueError("contains_point_buffer_px must be >= 0")
            self._contains_point_buffer_m = buffer_m
            self._contains_point_buffer_px = buffer_px
            min_area = self.config_get_float(
                "culvert_runner", "minimum_watershed_area_m2", None
            )
            if min_area is not None:
                min_area = float(min_area)
                if min_area < 0:
                    raise ValueError("minimum_watershed_area_m2 must be >= 0")
                if min_area == 0:
                    min_area = None
            self._minimum_watershed_area_m2 = min_area

        os.makedirs(self.runs_dir, exist_ok=True)

    @classmethod
    def _post_instance_loaded(cls, instance):
        instance = super()._post_instance_loaded(instance)
        if not hasattr(instance, "_rq_job_ids") or instance._rq_job_ids is None:
            instance._rq_job_ids = {}
        return instance

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
    def rq_job_ids(self) -> Dict[str, str]:
        return deepcopy(self._rq_job_ids) if self._rq_job_ids else {}

    @property
    def completed_at(self) -> Optional[str]:
        return getattr(self, "_completed_at", None)

    @property
    def retention_days(self) -> Optional[int]:
        return getattr(self, "_retention_days", None)

    @property
    def summary(self) -> Optional[Dict[str, Any]]:
        summary = getattr(self, "_summary", None)
        if summary is None:
            return None
        return deepcopy(summary)

    @property
    def run_config(self) -> str:
        return getattr(self, "_run_config", "culvert.cfg")

    @property
    def order_reduction_passes(self) -> int:
        return int(getattr(self, "_order_reduction_passes", 1))

    @property
    def order_reduction_mode(self) -> str:
        return str(getattr(self, "_order_reduction_mode", "fixed"))

    @order_reduction_passes.setter
    @nodb_setter
    def order_reduction_passes(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("order_reduction_passes must be an int")
        if value < 0:
            raise ValueError("order_reduction_passes must be >= 0")
        self._order_reduction_passes = value

    @property
    def crop_pad_px(self) -> int:
        return int(getattr(self, "_crop_pad_px", 5))

    @property
    def contains_point_buffer_px(self) -> int:
        return int(getattr(self, "_contains_point_buffer_px", 0))

    @property
    def contains_point_buffer_m(self) -> Optional[float]:
        value = getattr(self, "_contains_point_buffer_m", None)
        if value is None:
            return None
        return float(value)

    @property
    def minimum_watershed_area_m2(self) -> Optional[float]:
        value = getattr(self, "_minimum_watershed_area_m2", None)
        if value is None:
            return None
        return float(value)

    def set_rq_job_id(self, key: str, job_id: Optional[str]) -> None:
        if not key:
            return
        with self.locked():
            if not self._rq_job_ids:
                self._rq_job_ids = {}
            if job_id:
                self._rq_job_ids[key] = job_id
            else:
                self._rq_job_ids.pop(key, None)

    def _select_stream_sources_for_run(
        self,
        *,
        run_id: str,
        payload_metadata: Dict[str, Any],
        abs_batch_root: str,
        dem_src: str,
        flovec_src: str,
        netful_src: str,
        chnjnt_src: str,
        watershed: Watershed,
    ) -> tuple[str, str]:
        watersheds_src = self._resolve_payload_path(
            payload_metadata,
            "watersheds",
            self.DEFAULT_WATERSHEDS_REL_PATH,
            abs_batch_root,
        )
        features = self.load_watershed_features(watersheds_src)
        watershed_feature = features.get(run_id)
        if watershed_feature is None:
            raise ValueError(f"Watershed feature not found for Point_ID {run_id}")

        target_path = watershed.target_watershed_path
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if not _exists(target_path):
            # Use full DEM for stream check mask - this matches batch netful dimensions
            # The mask will be regenerated with VRT dimensions later by find_outlet
            watershed_feature.build_raster_mask(
                template_filepath=dem_src, dst_filepath=target_path
            )

        if _sum_masked_raster(netful_src, target_path) == 0:
            streams_src = self._resolve_payload_path(
                payload_metadata,
                "streams",
                self.DEFAULT_FULL_STREAM_REL_PATH,
                abs_batch_root,
            )
            if not _exists(streams_src):
                raise FileNotFoundError(
                    f"Streams file does not exist: {streams_src}"
                )
            streams_chnjnt = _join(
                abs_batch_root, self.DEFAULT_STREAMS_CHNJNT_REL_PATH
            )
            if not _exists(streams_chnjnt):
                raise FileNotFoundError(
                    f"Stream junction file does not exist: {streams_chnjnt}"
                )
            return streams_src, streams_chnjnt

        return netful_src, chnjnt_src

    def _compute_dem_crop_window(
        self,
        dem_src: str,
        watershed_feature: WatershedFeature,
    ) -> Tuple[int, int, int, int]:
        rdi_src = RasterDatasetInterpolator(dem_src)
        bbox = watershed_feature.get_padded_bbox(
            pad=0.0,
            output_crs=rdi_src.proj4,
        )
        return calculate_src_window(
            dem_src,
            bbox=bbox,
            bbox_crs=rdi_src.proj4,
            pad_px=self.crop_pad_px,
        )

    def create_run_if_missing(
        self,
        run_id: str,
        payload_metadata: Dict[str, Any],
        model_parameters: Optional[Dict[str, Any]] = None,
        watershed_feature: Optional[WatershedFeature] = None,
        as_cropped_vrt: bool = True,
    ) -> None:
        if not run_id:
            raise ValueError("run_id is required")
        if not isinstance(payload_metadata, dict):
            raise TypeError("payload_metadata must be a dict")
        if model_parameters is not None and not isinstance(model_parameters, dict):
            raise TypeError("model_parameters must be a dict")

        culvert_batch_uuid = self.culvert_batch_uuid
        if not culvert_batch_uuid:
            raise ValueError("culvert_batch_uuid is required")

        use_vrt = as_cropped_vrt and watershed_feature is not None
        if as_cropped_vrt and watershed_feature is None:
            self.logger.info(
                "create_run_if_missing requested VRT crop without watershed feature; using symlinks"
            )

        abs_batch_root = os.path.abspath(self.wd)

        dem_src = self._resolve_payload_path(
            payload_metadata, "dem", self.DEFAULT_DEM_REL_PATH, abs_batch_root
        )
        flovec_src = _join(abs_batch_root, self.DEFAULT_FLOVEC_REL_PATH)
        netful_src = _join(abs_batch_root, self.DEFAULT_NETFUL_REL_PATH)
        chnjnt_src = _join(abs_batch_root, self.DEFAULT_CHNJNT_REL_PATH)

        for path_label, path in (
            ("DEM", dem_src),
            ("flovec", flovec_src),
            ("netful", netful_src),
            ("chnjnt", chnjnt_src),
        ):
            if not _exists(path):
                raise FileNotFoundError(f"{path_label} file does not exist: {path}")

        self._ensure_base_project()
        os.makedirs(self.runs_dir, exist_ok=True)

        run_wd = _join(self.runs_dir, run_id)
        nodb_path = _join(run_wd, "ron.nodb")
        if _exists(nodb_path):
            ron = Ron.getInstance(run_wd)
            watershed = Watershed.getInstance(run_wd)
            self._set_run_map(ron, watershed_feature)
            netful_src, chnjnt_src = self._select_stream_sources_for_run(
                run_id=run_id,
                payload_metadata=payload_metadata,
                abs_batch_root=abs_batch_root,
                dem_src=dem_src,
                flovec_src=flovec_src,
                netful_src=netful_src,
                chnjnt_src=chnjnt_src,
                watershed=watershed,
            )

            required_paths = (
                ron.dem_fn,
                _join(watershed.wbt_wd, "flovec.tif"),
                _join(watershed.wbt_wd, "netful.tif"),
                _join(watershed.wbt_wd, "relief.tif"),
                _join(watershed.wbt_wd, "chnjnt.tif"),
            )
            netful_link = _join(watershed.wbt_wd, "netful.tif")
            chnjnt_link = _join(watershed.wbt_wd, "chnjnt.tif")
            if (
                all(os.path.lexists(path) for path in required_paths)
                and _symlink_matches(netful_link, netful_src)
                and _symlink_matches(chnjnt_link, chnjnt_src)
            ):
                return

            crop_window = None
            if use_vrt:
                assert watershed_feature is not None
                crop_window = self._compute_dem_crop_window(dem_src, watershed_feature)
            ron.symlink_dem(
                dem_src,
                as_cropped_vrt=use_vrt,
                crop_window=crop_window,
            )
            self._set_run_map(ron, watershed_feature)
            for filename in ("relief.tif", "chnjnt.tif"):
                cleanup_path = _join(watershed.wbt_wd, filename)
                if os.path.lexists(cleanup_path):
                    if os.path.islink(cleanup_path):
                        os.unlink(cleanup_path)
                        continue
                    if os.path.isdir(cleanup_path):
                        raise IsADirectoryError(
                            f"Expected file or symlink, found directory: {cleanup_path}"
                        )
                    os.unlink(cleanup_path)
            watershed.symlink_channels_map(
                flovec_src,
                netful_src,
                relief_src=dem_src,
                chnjnt_src=chnjnt_src,
                as_cropped_vrt=use_vrt,
            )

            created_at = datetime.now(timezone.utc).isoformat()
            with self.locked():
                run_record = self._runs.get(run_id, {})
                if "created_at" not in run_record:
                    run_record["created_at"] = created_at
                run_record.update(
                    {
                        "runid": run_id,
                        "point_id": run_id,
                        "wd": run_wd,
                    }
                )
                self._runs[run_id] = run_record
            return
        if _exists(run_wd):
            if not os.path.isdir(run_wd):
                raise FileExistsError(f"Run path exists and is not a directory: {run_wd}")
            shutil.rmtree(run_wd)

        run_group = "culvert"
        group_name = culvert_batch_uuid

        shutil.copytree(self.base_wd, run_wd, symlinks=True)

        for nodb_fn in glob(_join(run_wd, "*.nodb")):
            with open(nodb_fn, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            if "py/state" in state and isinstance(state["py/state"], dict):
                state["py/state"]["wd"] = run_wd
                state["py/state"]["_run_group"] = run_group
                state["py/state"]["_group_name"] = group_name
            state["wd"] = run_wd
            state["_run_group"] = run_group
            state["_group_name"] = group_name
            with open(nodb_fn, "w", encoding="utf-8") as handle:
                json.dump(state, handle)
                handle.flush()
                os.fsync(handle.fileno())

        runid = f"{run_group};;{group_name};;{run_id}"
        clear_nodb_file_cache(runid)
        try:
            clear_locks(runid)
        except RuntimeError:
            pass

        ron = Ron.getInstance(run_wd)
        crop_window = None
        if use_vrt:
            assert watershed_feature is not None
            crop_window = self._compute_dem_crop_window(dem_src, watershed_feature)
        ron.symlink_dem(
            dem_src,
            as_cropped_vrt=use_vrt,
            crop_window=crop_window,
        )
        self._set_run_map(ron, watershed_feature)

        watershed = Watershed.getInstance(run_wd)
        netful_src, chnjnt_src = self._select_stream_sources_for_run(
            run_id=run_id,
            payload_metadata=payload_metadata,
            abs_batch_root=abs_batch_root,
            dem_src=dem_src,
            flovec_src=flovec_src,
            netful_src=netful_src,
            chnjnt_src=chnjnt_src,
            watershed=watershed,
        )
        for filename in ("relief.tif", "chnjnt.tif"):
            cleanup_path = _join(watershed.wbt_wd, filename)
            if os.path.lexists(cleanup_path):
                if os.path.islink(cleanup_path):
                    os.unlink(cleanup_path)
                    continue
                if os.path.isdir(cleanup_path):
                    raise IsADirectoryError(
                        f"Expected file or symlink, found directory: {cleanup_path}"
                    )
                os.unlink(cleanup_path)
        watershed.symlink_channels_map(
            flovec_src,
            netful_src,
            relief_src=dem_src,
            chnjnt_src=chnjnt_src,
            as_cropped_vrt=use_vrt,
        )

        created_at = datetime.now(timezone.utc).isoformat()
        # Note: We skip locking here because in batch processing, each worker
        # handles a unique run_id and the orchestrator tracks runs via job
        # metadata. Locking would cause contention when multiple workers
        # process runs in parallel.
        run_record = self._runs.get(run_id, {})
        run_record.update(
            {
                "runid": run_id,
                "point_id": run_id,
                "wd": run_wd,
                "created_at": created_at,
            }
        )
        self._runs[run_id] = run_record

    def _set_run_map(
        self,
        ron: Ron,
        watershed_feature: Optional[WatershedFeature],
    ) -> None:
        if watershed_feature is None:
            return
        try:
            bbox = watershed_feature.get_padded_bbox(
                pad=0.0,
                output_crs="EPSG:4326",
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self.logger.warning(
                "culvert_run %s: failed to derive map extent from watershed feature - %s",
                watershed_feature.runid if watershed_feature else "?",
                exc,
            )
            return
        center = [(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0]
        zoom = Map.zoom_for_extent(bbox)
        ron.set_map(bbox, center=center, zoom=zoom)

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
        features = self.load_watershed_features(watersheds_src)
        ordered = sorted(
            features.values(),
            key=lambda feature: feature.area_m2,
            reverse=True,
        )
        return [feature.runid for feature in ordered]

    def load_watershed_features(
        self, watersheds_geojson_path: str
    ) -> Dict[str, WatershedFeature]:
        with open(watersheds_geojson_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("Watersheds GeoJSON contains no features")

        run_features: Dict[str, WatershedFeature] = {}
        crs_name = _extract_geojson_crs(payload)
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
            self._validate_run_id(run_id, idx)
            if run_id in run_features:
                raise ValueError(f"Duplicate Point_ID detected: {run_id}")
            run_features[run_id] = WatershedFeature(
                feature, runid=run_id, index=idx, crs=crs_name
            )

        return run_features

    def load_culvert_points(
        self, culvert_points_geojson_path: str
    ) -> Tuple[Dict[str, Tuple[float, float]], Optional[str]]:
        with open(culvert_points_geojson_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("Culvert points GeoJSON contains no features")

        crs_name = _extract_geojson_crs(payload)
        point_features: Dict[str, Tuple[float, float]] = {}
        for idx, feature in enumerate(features):
            props = (feature or {}).get("properties") or {}
            if self.POINT_ID_FIELD not in props:
                raise ValueError(
                    f"Feature {idx} missing {self.POINT_ID_FIELD} property in culvert points GeoJSON"
                )
            point_id = props.get(self.POINT_ID_FIELD)
            if point_id is None or point_id == "":
                raise ValueError(f"Feature {idx} has empty {self.POINT_ID_FIELD} value")
            run_id = str(point_id)
            self._validate_run_id(run_id, idx)
            if run_id in point_features:
                raise ValueError(f"Duplicate Point_ID detected: {run_id}")

            geometry = (feature or {}).get("geometry") or {}
            geom_type = geometry.get("type")
            if geom_type != "Point":
                raise ValueError(
                    f"Feature {idx} geometry type must be Point (found {geom_type})"
                )
            coords = geometry.get("coordinates")
            if not isinstance(coords, (list, tuple)) or len(coords) < 2:
                raise ValueError(
                    f"Feature {idx} missing point coordinates in culvert points GeoJSON"
                )
            try:
                x = float(coords[0])
                y = float(coords[1])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Feature {idx} has invalid point coordinates in culvert points GeoJSON"
                )
            point_features[run_id] = (x, y)

        return point_features, crs_name

    def _validate_run_id(self, run_id: str, idx: int) -> None:
        if run_id in {".", ".."}:
            raise ValueError(f"Invalid Point_ID for feature {idx}: {run_id}")
        separators = {"/", "\\", os.sep}
        if os.path.altsep:
            separators.add(os.path.altsep)
        if any(sep for sep in separators if sep and sep in run_id):
            raise ValueError(f"Invalid Point_ID for feature {idx}: {run_id}")
