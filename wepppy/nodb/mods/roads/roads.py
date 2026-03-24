"""Roads NoDb controller for the phase-1 inslope workflow."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import rasterio
from pyproj import CRS, Geod, Transformer
from wepp_runner.wepp_runner import (
    make_hillslope_run,
    make_watershed_omni_contrasts_run,
    run_hillslope,
    run_watershed,
)

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.roads.monotonic_segments import convert_geojson_file_to_monotonic_segments

__all__ = ["Roads"]


def _is_eligible_design(value: Any) -> bool:
    return isinstance(value, str) and value.lower() in {"inslope_bd", "inslope_rd"}


SURFACE_ALIASES: Dict[str, str] = {
    "gravel": "gravel",
    "graveled": "gravel",
    "dirt": "gravel",
    "native": "gravel",
    "unpaved": "gravel",
    "paved": "paved",
    "asphalt": "paved",
    "concrete": "paved",
}

TRAFFIC_ALIASES: Dict[str, str] = {
    "high": "high",
    "low": "low",
    "none": "none",
    "no": "none",
    "notraffic": "none",
}

CONDITION_TRAFFIC_MAP: Dict[str, str] = {
    "impassable": "none",
    "year round": "high",
    "new2011": "low",
}

SOIL_TEXTURE_ALIASES: Dict[str, str] = {
    "clay": "clay",
    "clay loam": "clay",
    "loam": "loam",
    "sandy loam": "sand",
    "sand": "sand",
    "silt": "silt",
    "silt loam": "silt",
}

ALLOWED_SOIL_TEXTURES: frozenset[str] = frozenset(SOIL_TEXTURE_ALIASES.values())
ALLOWED_SURFACES: frozenset[str] = frozenset(SURFACE_ALIASES.values())
ALLOWED_TRAFFIC: frozenset[str] = frozenset({"high", "low", "none"})


class Roads(NoDbBase):
    """Persist run-scoped Roads state and orchestrate Roads prep/run stages."""

    __name__ = "Roads"
    filename = "roads.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)
        self._ensure_roads_dirs()

        with self.locked():
            self._enabled = False
            self._uploaded_geojson_relpath = None
            self._uploaded_geojson_sha256 = None
            self._roads_params = self._default_params()
            self._last_prepare_summary = None
            self._last_run_summary = None
            self._status = "idle"
            self._errors = []
            self._timestamps = {}
        self._append_roads_log(
            "lifecycle",
            "controller_initialized",
            {
                "config": cfg_fn,
                "run_group": run_group,
                "group_name": group_name,
                "status": "idle",
            },
        )

    @classmethod
    def _post_instance_loaded(cls, instance: "Roads") -> "Roads":
        instance = super()._post_instance_loaded(instance)
        instance._ensure_roads_dirs()

        if not hasattr(instance, "_enabled"):
            instance._enabled = False
        if not hasattr(instance, "_uploaded_geojson_relpath"):
            instance._uploaded_geojson_relpath = None
        if not hasattr(instance, "_uploaded_geojson_sha256"):
            instance._uploaded_geojson_sha256 = None
        if not hasattr(instance, "_roads_params") or not isinstance(instance._roads_params, dict):
            instance._roads_params = instance._default_params()
        if not hasattr(instance, "_last_prepare_summary"):
            instance._last_prepare_summary = None
        if not hasattr(instance, "_last_run_summary"):
            instance._last_run_summary = None
        if not hasattr(instance, "_status"):
            instance._status = "idle"
        if not hasattr(instance, "_errors") or not isinstance(instance._errors, list):
            instance._errors = []
        if not hasattr(instance, "_timestamps") or not isinstance(instance._timestamps, dict):
            instance._timestamps = {}
        instance._append_roads_log(
            "lifecycle",
            "controller_loaded",
            {
                "status": str(getattr(instance, "_status", "idle")),
                "enabled": bool(getattr(instance, "_enabled", False)),
            },
        )
        return instance

    @staticmethod
    def _default_params() -> Dict[str, Any]:
        return {
            "input_crs": "EPSG:4326",
            "sample_step_m": None,
            "tolerance_m": 0.5,
            "soil_texture_default": "loam",
            "surface_default": "gravel",
            "traffic_default": "low",
            "rfg_pct_default": 15.0,
            "road_width_m_default": 4.0,
            "max_upload_mb": 50,
        }

    @property
    def enabled(self) -> bool:
        return bool(getattr(self, "_enabled", False))

    @property
    def roads_upload_dir(self) -> str:
        return os.path.join(self.wd, "roads")

    @property
    def roads_staged_geojson_path(self) -> Optional[str]:
        relpath = getattr(self, "_uploaded_geojson_relpath", None)
        if not relpath:
            return None
        return os.path.join(self.wd, relpath)

    @property
    def roads_wepp_dir(self) -> str:
        return os.path.join(self.wd, "wepp", "roads")

    @property
    def roads_segments_dir(self) -> str:
        return os.path.join(self.roads_wepp_dir, "segments")

    @property
    def roads_runs_dir(self) -> str:
        return os.path.join(self.roads_wepp_dir, "runs")

    @property
    def roads_output_dir(self) -> str:
        return os.path.join(self.roads_wepp_dir, "output")

    @property
    def roads_summary_path(self) -> str:
        return os.path.join(self.roads_segments_dir, "roads.inslope.summary.json")

    @property
    def roads_monotonic_geojson_path(self) -> str:
        return os.path.join(self.roads_segments_dir, "roads.inslope.monotonic.geojson")

    @property
    def roads_low_points_geojson_path(self) -> str:
        return os.path.join(self.roads_segments_dir, "roads.inslope.low_points.geojson")

    @property
    def roads_segment_pass_manifest_path(self) -> str:
        return os.path.join(self.roads_segments_dir, "roads.segment.pass.manifest.json")

    @property
    def roads_log_path(self) -> str:
        return os.path.join(self.roads_wepp_dir, "roads.log")

    @property
    def roads_legacy_templates_dir(self) -> str:
        return str(Path(__file__).resolve().parent / "legacy_templates")

    @property
    def roads_legacy_soils_dir(self) -> str:
        return os.path.join(self.roads_legacy_templates_dir, "soils")

    @property
    def roads_legacy_managements_dir(self) -> str:
        return os.path.join(self.roads_legacy_templates_dir, "managements")

    def _ensure_roads_dirs(self) -> None:
        for path in (
            self.roads_upload_dir,
            self.roads_wepp_dir,
            self.roads_segments_dir,
            self.roads_runs_dir,
            self.roads_output_dir,
        ):
            os.makedirs(path, exist_ok=True)
        self._ensure_roads_log_initialized()

    def _ensure_roads_log_initialized(self) -> None:
        log_path = Path(self.roads_log_path)
        if log_path.exists():
            return
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log_path.write_text(
            f"{timestamp} [lifecycle] roads_log_initialized\n",
            encoding="utf-8",
        )

    def _reset_roads_log(self, stage: str) -> None:
        self._append_roads_log(stage, "stage_started")

    def _append_roads_log(self, stage: str, event: str, details: Optional[Mapping[str, Any]] = None) -> None:
        self._ensure_roads_log_initialized()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        line = f"{timestamp} [{stage}] {event}"
        if details:
            serialized = json.dumps(dict(details), sort_keys=True, default=str)
            line += f" {serialized}"
        with open(self.roads_log_path, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")

    @staticmethod
    def _normalize_existing_path(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        candidate = Path(path)
        return str(candidate) if candidate.exists() else None

    def _path_for_summary(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        candidate = Path(path)
        try:
            return str(candidate.relative_to(Path(self.wd)))
        except ValueError:
            return str(candidate)

    @staticmethod
    def _params_signature(params: Mapping[str, Any]) -> str:
        payload = json.dumps(dict(params), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_geojson_crs(payload: Mapping[str, Any]) -> Optional[str]:
        crs_block = payload.get("crs")
        if crs_block in (None, ""):
            return None
        if not isinstance(crs_block, Mapping):
            raise ValueError("Roads GeoJSON `crs` must be an object when provided.")

        properties = crs_block.get("properties")
        if not isinstance(properties, Mapping):
            raise ValueError("Roads GeoJSON `crs.properties.name` is required when `crs` is provided.")
        name = properties.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Roads GeoJSON `crs.properties.name` must be a non-empty string.")
        return name.strip()

    def _require_prepare_state_current(self) -> None:
        status = str(getattr(self, "_status", "idle"))
        if status == "running":
            raise ValueError("Roads run is already in progress.")

        prepare_summary = getattr(self, "_last_prepare_summary", None)
        if not isinstance(prepare_summary, Mapping):
            raise ValueError("Roads segments are stale or missing. Run prepare_segments before run_roads_wepp.")

        prepared_sha = prepare_summary.get("uploaded_geojson_sha256")
        current_sha = getattr(self, "_uploaded_geojson_sha256", None)
        if not prepared_sha or prepared_sha != current_sha:
            raise ValueError("Roads upload changed after prepare_segments. Run prepare_segments again.")

        current_params = dict(getattr(self, "_roads_params", self._default_params()))
        prepared_signature = str(prepare_summary.get("roads_params_signature") or "")
        current_signature = self._params_signature(current_params)
        if not prepared_signature or prepared_signature != current_signature:
            raise ValueError("Roads parameters changed after prepare_segments. Run prepare_segments again.")

        if status == "idle":
            raise ValueError("Roads segments are stale or missing. Run prepare_segments before run_roads_wepp.")

    def _resolve_prepare_raster_paths(self) -> Dict[str, str]:
        watershed = self.watershed_instance
        relief_path = self._normalize_existing_path(getattr(watershed, "relief", None))
        dem_fallback_path = self._normalize_existing_path(getattr(self.ron_instance, "dem_fn", None))
        dem_path = relief_path or dem_fallback_path
        if dem_path is None:
            raise FileNotFoundError(
                "Roads prepare requires an existing DEM (`watershed.relief` or `ron.dem_fn`)."
            )

        channel_raster_path = self._normalize_existing_path(getattr(watershed, "netful", None))
        topaz_id_raster_path = self._normalize_existing_path(getattr(watershed, "subwta", None))
        if channel_raster_path is None:
            raise FileNotFoundError(
                "Roads prepare requires an existing channel raster (`watershed.netful`)."
            )
        if topaz_id_raster_path is None:
            raise FileNotFoundError(
                "Roads prepare requires an existing Topaz-id raster (`watershed.subwta`)."
            )

        return {
            "dem_path": dem_path,
            "channel_raster_path": channel_raster_path,
            "topaz_id_raster_path": topaz_id_raster_path,
        }

    def _clear_stale_run_state_locked(self) -> None:
        self._last_prepare_summary = None
        self._last_run_summary = None
        self._status = "idle"
        self._errors = []

    def _record_error_and_raise(self, exc: Exception) -> None:
        message = str(exc)
        try:
            self._append_roads_log(
                "error",
                "exception",
                {"error_type": type(exc).__name__, "message": message},
            )
        except OSError:
            # Boundary catch: logging must not mask the canonical exception contract.
            pass
        with self.locked():
            self._status = "failed"
            self._errors.append(message)
            self._timestamps["failed"] = int(time.time())
        raise exc

    def set_enabled(self, enabled: bool) -> None:
        requested_enabled = bool(enabled)
        if requested_enabled and not bool(getattr(self.watershed_instance, "delineation_backend_is_wbt", False)):
            raise ValueError("Roads requires WBT delineation backend.")
        self._append_roads_log(
            "config",
            "set_enabled_requested",
            {
                "requested_enabled": requested_enabled,
                "previous_enabled": bool(getattr(self, "_enabled", False)),
            },
        )
        with self.locked():
            self._enabled = requested_enabled
            self._timestamps["enabled"] = int(time.time())
            if not self._enabled:
                self._clear_stale_run_state_locked()
            status = str(self._status)
            timestamps_enabled = int(self._timestamps["enabled"])
        self._append_roads_log(
            "config",
            "set_enabled_applied",
            {
                "enabled": requested_enabled,
                "status": status,
                "timestamp": timestamps_enabled,
            },
        )

    def set_params(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("Roads params payload must be a JSON object.")

        self._append_roads_log(
            "config",
            "set_params_requested",
            {"keys": sorted(str(key) for key in payload.keys())},
        )
        params = dict(self._default_params())
        params.update(dict(getattr(self, "_roads_params", {})))

        if "input_crs" in payload:
            value = str(payload["input_crs"]).strip()
            if not value:
                raise ValueError("input_crs must be a non-empty string.")
            try:
                CRS.from_user_input(value)
            except Exception as exc:
                raise ValueError(f"input_crs is invalid: {exc}") from exc
            params["input_crs"] = value

        for key in ("sample_step_m", "tolerance_m", "rfg_pct_default", "road_width_m_default"):
            if key not in payload:
                continue
            value = payload[key]
            if value in (None, "") and key == "sample_step_m":
                params[key] = None
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be numeric.")
            if key != "tolerance_m" and numeric <= 0:
                raise ValueError(f"{key} must be > 0.")
            if key == "tolerance_m" and numeric < 0:
                raise ValueError("tolerance_m must be >= 0.")
            params[key] = numeric

        if "max_upload_mb" in payload:
            try:
                max_upload_mb = int(payload["max_upload_mb"])
            except (TypeError, ValueError):
                raise ValueError("max_upload_mb must be an integer.")
            if max_upload_mb <= 0:
                raise ValueError("max_upload_mb must be > 0.")
            params["max_upload_mb"] = max_upload_mb

        for key in ("soil_texture_default", "surface_default", "traffic_default"):
            if key in payload:
                raw_value = str(payload[key]).strip()
                if not raw_value:
                    raise ValueError(f"{key} must be a non-empty string.")
                value = raw_value.lower()
                if key == "soil_texture_default":
                    normalized_texture = SOIL_TEXTURE_ALIASES.get(value)
                    if normalized_texture not in ALLOWED_SOIL_TEXTURES:
                        raise ValueError(
                            f"soil_texture_default must resolve to one of {sorted(ALLOWED_SOIL_TEXTURES)}."
                        )
                    params[key] = normalized_texture
                elif key == "surface_default":
                    normalized_surface = SURFACE_ALIASES.get(value)
                    if normalized_surface not in ALLOWED_SURFACES:
                        raise ValueError(
                            f"surface_default must resolve to one of {sorted(ALLOWED_SURFACES)}."
                        )
                    params[key] = normalized_surface
                else:
                    traffic_key = value.replace(" ", "")
                    normalized_traffic = TRAFFIC_ALIASES.get(traffic_key)
                    if normalized_traffic not in ALLOWED_TRAFFIC:
                        raise ValueError(f"traffic_default must be one of {sorted(ALLOWED_TRAFFIC)}.")
                    params[key] = normalized_traffic

        with self.locked():
            self._roads_params = params
            self._timestamps["set_params"] = int(time.time())
            self._clear_stale_run_state_locked()
            status = str(self._status)
            timestamp = int(self._timestamps["set_params"])

        self._append_roads_log(
            "config",
            "set_params_applied",
            {
                "status": status,
                "timestamp": timestamp,
                "roads_params": params,
            },
        )

        return dict(params)

    def _validate_uploaded_geojson(self, payload: Mapping[str, Any]) -> None:
        if payload.get("type") != "FeatureCollection":
            raise ValueError("Roads GeoJSON must be a FeatureCollection.")

        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("Roads GeoJSON must contain at least one feature.")

        for feature in features:
            geometry = feature.get("geometry") if isinstance(feature, Mapping) else None
            geometry_type = geometry.get("type") if isinstance(geometry, Mapping) else None
            if geometry_type not in {"LineString", "MultiLineString"}:
                raise ValueError("Roads GeoJSON supports only LineString or MultiLineString geometries.")

    def set_uploaded_geojson(self, src_path: str) -> Dict[str, Any]:
        source_path = Path(src_path)
        if not source_path.is_absolute():
            source_path = Path(self.wd) / source_path
        source_path = source_path.resolve()
        self._append_roads_log(
            "upload",
            "upload_requested",
            {"source_path": str(source_path)},
        )

        if not source_path.exists():
            raise FileNotFoundError(f"Roads input file not found: {source_path}")
        if source_path.suffix.lower() != ".geojson":
            raise ValueError("Roads upload must be a .geojson file.")

        max_upload_mb = int(dict(getattr(self, "_roads_params", {})).get("max_upload_mb", 50))
        max_upload_bytes = max_upload_mb * 1024 * 1024
        if source_path.stat().st_size > max_upload_bytes:
            raise ValueError(f"Roads upload exceeds max_upload_mb limit ({max_upload_mb} MB).")

        payload = json.loads(source_path.read_text(encoding="utf-8"))
        self._validate_uploaded_geojson(payload)

        configured_input_crs = str(dict(getattr(self, "_roads_params", {})).get("input_crs") or "EPSG:4326")
        try:
            CRS.from_user_input(configured_input_crs)
        except Exception as exc:
            raise ValueError(f"Configured input_crs is invalid; update Roads params before upload: {exc}") from exc

        source_crs = self._extract_geojson_crs(payload)
        if source_crs is not None:
            try:
                CRS.from_user_input(source_crs)
            except Exception as exc:
                raise ValueError(f"Roads GeoJSON CRS is invalid ({source_crs!r}): {exc}") from exc

        self._ensure_roads_dirs()
        target_path = Path(self.roads_upload_dir) / "roads.uploaded.geojson"
        shutil.copy2(source_path, target_path)

        digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        relpath = str(target_path.relative_to(self.wd))
        now = int(time.time())

        with self.locked():
            self._uploaded_geojson_relpath = relpath
            self._uploaded_geojson_sha256 = digest
            self._timestamps["upload_geojson"] = now
            self._clear_stale_run_state_locked()
            status = str(self._status)

        self._append_roads_log(
            "upload",
            "upload_completed",
            {
                "uploaded_geojson_relpath": relpath,
                "uploaded_geojson_sha256": digest,
                "feature_count": len(payload.get("features", [])),
                "uploaded_at": now,
                "configured_input_crs": configured_input_crs,
                "source_crs": source_crs,
                "status": status,
            },
        )

        return {
            "uploaded_geojson_relpath": relpath,
            "uploaded_geojson_sha256": digest,
            "feature_count": len(payload.get("features", [])),
            "uploaded_at": now,
            "configured_input_crs": configured_input_crs,
            "source_crs": source_crs,
        }

    def _load_segment_features(self) -> List[Dict[str, Any]]:
        segment_path = Path(self.roads_monotonic_geojson_path)
        if not segment_path.exists():
            raise FileNotFoundError(
                "Prepared roads segments not found. Run prepare_segments before run_roads_wepp."
            )

        payload = json.loads(segment_path.read_text(encoding="utf-8"))
        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("Prepared roads segment GeoJSON is malformed.")
        self._append_roads_log(
            "run",
            "loaded_prepared_segments",
            {
                "segment_feature_count": len(features),
                "roads_monotonic_geojson_relpath": os.path.relpath(segment_path, self.wd),
            },
        )
        return features

    def prepare_segments(self) -> Dict[str, Any]:
        try:
            if not self.enabled:
                raise ValueError("Roads must be enabled before preparing segments.")

            staged_path = self.roads_staged_geojson_path
            if not staged_path:
                raise ValueError("No roads GeoJSON has been uploaded.")

            self._ensure_roads_dirs()
            self._reset_roads_log("prepare")
            self._append_roads_log(
                "prepare",
                "start_prepare_segments",
                {"uploaded_geojson_relpath": self._path_for_summary(staged_path)},
            )
            params = dict(getattr(self, "_roads_params", self._default_params()))
            input_crs_value = str(params.get("input_crs") or "EPSG:4326")
            try:
                CRS.from_user_input(input_crs_value)
            except Exception as exc:
                raise ValueError(f"Roads input_crs is invalid: {exc}") from exc
            raster_paths = self._resolve_prepare_raster_paths()
            self._append_roads_log(
                "prepare",
                "resolved_prepare_rasters",
                {
                    "dem_path": self._path_for_summary(raster_paths["dem_path"]),
                    "channel_raster_path": self._path_for_summary(raster_paths["channel_raster_path"]),
                    "topaz_id_raster_path": self._path_for_summary(raster_paths["topaz_id_raster_path"]),
                },
            )

            summary = convert_geojson_file_to_monotonic_segments(
                input_geojson_path=staged_path,
                dem_path=raster_paths["dem_path"],
                output_geojson_path=self.roads_monotonic_geojson_path,
                low_points_output_geojson_path=self.roads_low_points_geojson_path,
                input_crs=input_crs_value,
                sample_step_m=params.get("sample_step_m"),
                tolerance_m=float(params.get("tolerance_m", 0.5)),
                channel_raster_path=raster_paths["channel_raster_path"],
                topaz_id_raster_path=raster_paths["topaz_id_raster_path"],
            )

            segment_payload = json.loads(Path(self.roads_monotonic_geojson_path).read_text(encoding="utf-8"))
            features = segment_payload.get("features", [])
            eligible_segments = 0
            mapped_candidates = 0
            decision_counts: Counter[str] = Counter()
            for feature in features:
                properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
                design_value = self._first_non_empty_property(properties, ("DESIGN", "design"))
                if not _is_eligible_design(design_value):
                    continue
                eligible_segments += 1
                decision_key = str(properties.get("_roads_lowpoint_decision") or "unknown")
                decision_counts[decision_key] += 1
                if properties.get("topaz_id_chn_lowpoint") is not None and properties.get("topaz_id_hill_lowpoint") is not None:
                    mapped_candidates += 1

            prepare_summary = {
                "input_feature_count": int(summary.input_feature_count),
                "output_feature_count": int(summary.output_feature_count),
                "split_feature_count": int(summary.split_feature_count),
                "low_point_feature_count": int(summary.low_point_feature_count),
                "sample_step_m": float(summary.sample_step_m),
                "tolerance_m": float(summary.tolerance_m),
                "eligible_segment_count": eligible_segments,
                "eligible_with_lowpoint_ids": mapped_candidates,
                "eligible_lowpoint_decision_counts": dict(sorted(decision_counts.items())),
                "prepare_raster_paths": {
                    "dem_path": self._path_for_summary(raster_paths["dem_path"]),
                    "channel_raster_path": self._path_for_summary(raster_paths["channel_raster_path"]),
                    "topaz_id_raster_path": self._path_for_summary(raster_paths["topaz_id_raster_path"]),
                },
                "roads_monotonic_geojson_relpath": os.path.relpath(self.roads_monotonic_geojson_path, self.wd),
                "roads_low_points_geojson_relpath": os.path.relpath(self.roads_low_points_geojson_path, self.wd),
                "summary_relpath": os.path.relpath(self.roads_summary_path, self.wd),
                "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
                "input_crs": input_crs_value,
                "roads_params_signature": self._params_signature(params),
                "uploaded_geojson_sha256": getattr(self, "_uploaded_geojson_sha256", None),
                "prepared_at": int(time.time()),
            }
            Path(self.roads_summary_path).write_text(
                json.dumps(prepare_summary, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            self._append_roads_log(
                "prepare",
                "prepare_summary_written",
                {
                    "eligible_segment_count": eligible_segments,
                    "eligible_with_lowpoint_ids": mapped_candidates,
                    "eligible_lowpoint_decision_counts": dict(sorted(decision_counts.items())),
                    "summary_relpath": prepare_summary["summary_relpath"],
                },
            )

            with self.locked():
                self._last_prepare_summary = prepare_summary
                self._last_run_summary = None
                self._status = "prepared"
                self._errors = []
                self._timestamps["prepare_segments"] = int(time.time())

            return dict(prepare_summary)
        except Exception as exc:
            self._record_error_and_raise(exc)

    @staticmethod
    def _safe_link_or_copy(src: str, dst: str) -> str:
        src_path = Path(src)
        dst_path = Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if dst_path.exists() or dst_path.is_symlink():
            dst_path.unlink()

        try:
            os.symlink(src_path, dst_path)
            return "symlink"
        except OSError:
            shutil.copy2(src_path, dst_path)
            return "copy"

    @staticmethod
    def _segment_key(feature: Mapping[str, Any]) -> str:
        properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
        segment_id = properties.get("segment_id")
        if isinstance(segment_id, str) and segment_id:
            return segment_id
        return "roads-seg-unknown"

    @staticmethod
    def _first_non_empty_property(properties: Mapping[str, Any], keys: Iterable[str]) -> Optional[str]:
        for key in keys:
            value = properties.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_surface(self, value: Optional[str], default_value: str) -> str:
        if value is None:
            return default_value
        normalized = SURFACE_ALIASES.get(value.strip().lower())
        if normalized is None:
            return default_value
        return normalized

    def _normalize_traffic(self, value: Optional[str], condition: Optional[str], default_value: str) -> str:
        if value is not None:
            normalized = TRAFFIC_ALIASES.get(value.strip().lower().replace(" ", ""))
            if normalized is not None:
                return normalized
        if condition is not None:
            condition_key = condition.strip().lower()
            if condition_key in CONDITION_TRAFFIC_MAP:
                return CONDITION_TRAFFIC_MAP[condition_key]
        return default_value

    def _normalize_soil_texture(self, value: Optional[str], default_value: str) -> str:
        if value is None:
            return default_value
        normalized = SOIL_TEXTURE_ALIASES.get(value.strip().lower())
        if normalized is None:
            return default_value
        return normalized

    def _resolve_segment_run_inputs(
        self,
        *,
        properties: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> Dict[str, Any]:
        design_raw = self._first_non_empty_property(properties, ("DESIGN", "design"))
        design = (design_raw or "").strip().lower()
        if design not in {"inslope_bd", "inslope_rd"}:
            raise ValueError(f"Unsupported Roads design for segment execution: {design_raw!r}")

        default_surface = self._normalize_surface(
            str(params.get("surface_default", "gravel")),
            "gravel",
        )
        default_traffic = self._normalize_traffic(
            str(params.get("traffic_default", "low")),
            None,
            "low",
        )
        default_texture = self._normalize_soil_texture(
            str(params.get("soil_texture_default", "loam")),
            "loam",
        )
        default_rfg = float(params.get("rfg_pct_default", 15.0))
        default_width = float(params.get("road_width_m_default", 4.0))

        surface_raw = self._first_non_empty_property(
            properties,
            ("SURFACE", "surface", "ROAD_SURFACE"),
        )
        condition_raw = self._first_non_empty_property(
            properties,
            ("CONDITION", "condition"),
        )
        traffic_raw = self._first_non_empty_property(
            properties,
            ("TRAFFIC", "traffic"),
        )
        texture_raw = self._first_non_empty_property(
            properties,
            ("SOIL_TEXTURE", "soil_texture", "SOIL", "soil"),
        )
        rfg_raw = self._first_non_empty_property(
            properties,
            ("RFG_PCT", "rfg_pct", "RFG", "rfg"),
        )
        width_raw = self._first_non_empty_property(
            properties,
            ("WIDTH_M", "width_m", "ROAD_WIDTH_M", "road_width_m"),
        )

        resolved_surface = self._normalize_surface(surface_raw, default_surface)
        resolved_traffic = self._normalize_traffic(traffic_raw, condition_raw, default_traffic)
        resolved_texture = self._normalize_soil_texture(texture_raw, default_texture)

        rfg_pct = self._coerce_float(rfg_raw)
        if rfg_pct is None:
            rfg_pct = default_rfg
        rfg_pct = max(0.0, min(100.0, float(rfg_pct)))

        road_width_m = self._coerce_float(width_raw)
        if road_width_m is None:
            road_width_m = default_width
        if road_width_m <= 0:
            road_width_m = default_width

        return {
            "design": design,
            "surface": resolved_surface,
            "traffic": resolved_traffic,
            "soil_texture": resolved_texture,
            "rfg_pct": float(rfg_pct),
            "road_width_m": float(road_width_m),
            "resolution_sources": {
                "surface": "segment_property" if surface_raw else "roads_default",
                "traffic": "segment_property_or_condition" if (traffic_raw or condition_raw) else "roads_default",
                "soil_texture": "segment_property" if texture_raw else "roads_default",
                "rfg_pct": "segment_property" if rfg_raw else "roads_default",
                "road_width_m": "segment_property" if width_raw else "roads_default",
            },
        }

    @staticmethod
    def _extract_segment_coordinates(feature: Mapping[str, Any]) -> List[List[float]]:
        geometry = feature.get("geometry") if isinstance(feature, Mapping) else None
        if not isinstance(geometry, Mapping):
            raise ValueError("Road segment feature is missing geometry.")

        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if geometry_type == "LineString":
            if not isinstance(coordinates, list) or len(coordinates) < 2:
                raise ValueError("Road segment LineString must include at least two coordinates.")
            return coordinates

        if geometry_type == "MultiLineString":
            if not isinstance(coordinates, list) or not coordinates:
                raise ValueError("Road segment MultiLineString must include at least one linestring.")
            candidates = [line for line in coordinates if isinstance(line, list) and len(line) >= 2]
            if not candidates:
                raise ValueError("Road segment MultiLineString has no valid linestring members.")
            candidates.sort(key=len, reverse=True)
            return candidates[0]

        raise ValueError(f"Unsupported segment geometry type for Roads WEPP run assembly: {geometry_type!r}")

    @staticmethod
    def _line_length_m(coords: List[List[float]], transformer: Transformer, geod: Geod) -> float:
        lons: List[float] = []
        lats: List[float] = []
        for point in coords:
            x = float(point[0])
            y = float(point[1])
            lon, lat = transformer.transform(x, y)
            lons.append(lon)
            lats.append(lat)
        return float(geod.line_length(lons, lats))

    @staticmethod
    def _sample_dem_elevation(
        dataset: rasterio.io.DatasetReader,
        transformer: Transformer,
        x: float,
        y: float,
    ) -> float:
        dx, dy = transformer.transform(float(x), float(y))
        sample = next(dataset.sample([(dx, dy)]))
        value = float(sample[0])
        if dataset.nodata is not None and abs(value - float(dataset.nodata)) < 1e-12:
            raise ValueError("Segment endpoint sampled nodata elevation from DEM.")
        return value

    @staticmethod
    def _clamp_percent_slope(value: float) -> float:
        return max(0.1, min(40.0, float(value)))

    def _build_segment_profile(
        self,
        *,
        feature: Mapping[str, Any],
        input_crs: CRS,
        dem_dataset: rasterio.io.DatasetReader,
        input_to_wgs84: Transformer,
        input_to_dem: Transformer,
        geod: Geod,
    ) -> Dict[str, Any]:
        coords = self._extract_segment_coordinates(feature)
        segment_length_m = self._line_length_m(coords, input_to_wgs84, geod)
        if segment_length_m <= 0:
            raise ValueError("Segment geometry length is zero; cannot build Roads slope profile.")

        start = coords[0]
        end = coords[-1]
        start_elevation = self._sample_dem_elevation(dem_dataset, input_to_dem, start[0], start[1])
        end_elevation = self._sample_dem_elevation(dem_dataset, input_to_dem, end[0], end[1])

        if start_elevation >= end_elevation:
            high_point = start
            low_point = end
            elevation_high = start_elevation
            elevation_low = end_elevation
        else:
            high_point = end
            low_point = start
            elevation_high = end_elevation
            elevation_low = start_elevation

        raw_slope_pct = ((elevation_high - elevation_low) / segment_length_m) * 100.0
        clamped_slope_pct = self._clamp_percent_slope(raw_slope_pct)

        return {
            "segment_length_m": float(segment_length_m),
            "elevation_high_m": float(elevation_high),
            "elevation_low_m": float(elevation_low),
            "raw_slope_pct": float(raw_slope_pct),
            "slope_pct": float(clamped_slope_pct),
            "high_point": [float(high_point[0]), float(high_point[1])],
            "low_point": [float(low_point[0]), float(low_point[1])],
        }

    @staticmethod
    def _write_single_ofe_slope_file(path: Path, *, width_m: float, length_m: float, slope_pct: float) -> None:
        slope_fraction = float(slope_pct) / 100.0
        content = [
            "97.3",
            "1",
            f"180.0 {float(width_m):.3f}",
            f"2 {float(length_m):.3f}",
            f"0.00, {slope_fraction:.6f} 1.00, {slope_fraction:.6f}",
        ]
        path.write_text("\n".join(content) + "\n", encoding="utf-8")

    def _resolve_legacy_soil_template_path(self, *, design: str, surface: str, soil_texture: str) -> Path:
        if design == "inslope_rd":
            tau_value = "10"
        elif design == "inslope_bd" and surface == "paved":
            tau_value = "1"
        else:
            tau_value = "2"

        surface_prefix = "p" if surface == "paved" else "g"
        template_name = f"3{surface_prefix}{soil_texture}{tau_value}.sol"
        template_path = Path(self.roads_legacy_soils_dir) / template_name
        if not template_path.exists():
            raise FileNotFoundError(
                f"Roads soil template is missing: {template_path} "
                f"(design={design}, surface={surface}, soil_texture={soil_texture})."
            )
        return template_path

    def _resolve_legacy_management_template_path(self, *, traffic: str) -> Path:
        template_name = "3inslopen.man" if traffic == "none" else "3inslope.man"
        template_path = Path(self.roads_legacy_managements_dir) / template_name
        if not template_path.exists():
            raise FileNotFoundError(
                f"Roads management template is missing: {template_path} (traffic={traffic})."
            )
        return template_path

    @staticmethod
    def _replace_leading_int(line: str, replacement: int) -> str:
        return re.sub(r"^\s*\d+", str(int(replacement)), line, count=1)

    def _build_single_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
        lines = template_path.read_text(encoding="utf-8").splitlines()
        out: List[str] = []
        i = 0
        replaced_top_nofe = False

        while i < len(lines):
            line = lines[i]
            if "# number of OFEs" in line and not replaced_top_nofe:
                out.append(self._replace_leading_int(line, 1))
                replaced_top_nofe = True
                i += 1
                break
            out.append(line)
            i += 1

        while i < len(lines):
            line = lines[i]
            if "# looper; number of Plant scenarios" in line:
                out.append(self._replace_leading_int(line, 1))
                i += 1
                break
            out.append(line)
            i += 1

        while i < len(lines):
            if "#       Plant scenario 2" in lines[i]:
                break
            out.append(lines[i])
            i += 1

        while i < len(lines) and "#####################" not in lines[i]:
            i += 1

        while i < len(lines):
            line = lines[i]
            if "# looper; number of Initial Conditions scenarios" in line:
                out.append(self._replace_leading_int(line, 1))
                i += 1
                break
            out.append(line)
            i += 1

        while i < len(lines):
            if "#\tInitial Conditions scenario 2" in lines[i]:
                break
            out.append(lines[i])
            i += 1

        while i < len(lines) and "###########################" not in lines[i]:
            i += 1

        while i < len(lines):
            line = lines[i]
            out.append(line)
            i += 1
            if "# looper; number of Yearly scenarios" in line:
                out[-1] = self._replace_leading_int(line, 1)
                break

        while i < len(lines):
            if "#\tYearly scenario 2" in lines[i]:
                break
            out.append(lines[i])
            i += 1

        while i < len(lines) and "######################" not in lines[i]:
            i += 1

        while i < len(lines):
            line = lines[i]
            out.append(line)
            i += 1
            if "# `nofe'" in line:
                out[-1] = self._replace_leading_int(line, 1)
                break

        initial_condition_index_count = 0
        while i < len(lines):
            line = lines[i]
            if "# `Initial Conditions indx'" in line:
                initial_condition_index_count += 1
                if initial_condition_index_count == 1:
                    out.append(line)
                i += 1
                continue
            out.append(line)
            i += 1
            if "# `nyears'" in line:
                break

        skip_next_year_index = False
        while i < len(lines):
            line = lines[i]
            if "# `nycrop'" in line and "OFE :" in line:
                if "OFE : 1" in line:
                    out.append(line)
                    skip_next_year_index = False
                else:
                    skip_next_year_index = True
                i += 1
                continue

            if skip_next_year_index:
                skip_next_year_index = False
                i += 1
                continue

            out.append(line)
            i += 1

        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _build_single_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        lines = template_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 6:
            raise ValueError(f"Roads soil template is malformed: {template_path}")

        out: List[str] = []
        i = 0
        out.append(lines[i])
        i += 1

        while i < len(lines) and lines[i].startswith("#"):
            out.append(lines[i])
            i += 1

        if i >= len(lines):
            raise ValueError(f"Roads soil template is malformed (missing soil comment): {template_path}")
        out.append(lines[i])
        i += 1

        while i < len(lines) and not lines[i].strip():
            out.append(lines[i])
            i += 1

        if i >= len(lines):
            raise ValueError(f"Roads soil template is malformed (missing ntemp line): {template_path}")
        ntemp_tokens = lines[i].split()
        ksflag = ntemp_tokens[1] if len(ntemp_tokens) > 1 else "0"
        out.append(f"1 {ksflag}")
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        if i + 1 >= len(lines):
            raise ValueError(f"Roads soil template is malformed (missing first OFE lines): {template_path}")

        first_ofe_header = lines[i]
        first_ofe_horizon = lines[i + 1]

        header_tokens = shlex.split(first_ofe_header)
        if len(header_tokens) < 8:
            raise ValueError(f"Roads soil template has malformed first OFE header: {template_path}")

        slid, texid = header_tokens[0], header_tokens[1]
        nsl, salb, sat, ki, kr, shcrit = header_tokens[2:8]
        avke = header_tokens[8] if len(header_tokens) > 8 else None

        ki_value = float(ki)
        kr_value = float(kr)
        if traffic != "high":
            ki_value /= 4.0
            kr_value /= 4.0

        header_line = (
            f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
        )
        if avke is not None:
            header_line += f" {avke}"
        out.append(header_line)

        horizon_tokens = first_ofe_horizon.split()
        if len(horizon_tokens) < 6:
            raise ValueError(f"Roads soil template has malformed first OFE horizon: {template_path}")

        urr_ref = 95.0 if surface == "paved" else 65.0
        marker = horizon_tokens[-1].lower()
        if marker == "urr":
            horizon_tokens[-1] = f"{urr_ref:.6g}"
        elif marker == "ufr":
            horizon_tokens[-1] = f"{((float(rfg_pct) + 65.0) / 2.0):.6g}"
        elif marker == "ubr":
            horizon_tokens[-1] = f"{float(rfg_pct):.6g}"
        out.append(" ".join(horizon_tokens))

        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _materialize_single_ofe_management_template(self, *, traffic: str) -> Path:
        source_path = self._resolve_legacy_management_template_path(traffic=traffic)
        output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.single_ofe.man"
        self._build_single_ofe_management_file(template_path=source_path, output_path=output_path)
        return output_path

    def _combine_target_hillslope_pass(
        self,
        *,
        base_pass_path: str,
        road_pass_paths: Iterable[str],
        output_pass_path: str,
    ) -> None:
        from wepppyo3.wepp_interchange import combine_hillslope_pass_files

        combine_hillslope_pass_files(
            base_pass=str(base_pass_path),
            road_passes=[str(path) for path in road_pass_paths],
            out_pass=str(output_pass_path),
            strategy="phase1",
        )

    def _prepare_roads_runs_workspace(self) -> None:
        baseline_runs_dir = Path(self.wepp_instance.runs_dir)
        if not baseline_runs_dir.exists():
            raise FileNotFoundError(f"Missing baseline WEPP runs directory: {baseline_runs_dir}")

        runs_dir = Path(self.roads_runs_dir)
        if runs_dir.exists():
            shutil.rmtree(runs_dir)
        runs_dir.mkdir(parents=True, exist_ok=True)

        for entry in baseline_runs_dir.iterdir():
            if entry.name in {"pw0.run", "pw0.err"}:
                continue
            dst = runs_dir / entry.name
            if entry.is_dir():
                shutil.copytree(entry, dst)
            else:
                self._safe_link_or_copy(str(entry), str(dst))

    def _prepare_roads_output_workspace(self) -> None:
        output_dir = Path(self.roads_output_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    def _run_segment_hillslope(
        self,
        *,
        segment_run_id: int,
        climate_wepp_id: int,
        sim_years: int,
        wepp_bin: Optional[str],
        single_ofe_management_path: Path,
        single_ofe_soil_path: Path,
        single_ofe_slope_path: Path,
    ) -> None:
        baseline_runs_dir = Path(self.wepp_instance.runs_dir)
        climate_source = baseline_runs_dir / f"p{int(climate_wepp_id)}.cli"
        if not climate_source.exists():
            raise FileNotFoundError(
                f"Roads segment run requires baseline climate file: {climate_source}"
            )

        runs_dir = Path(self.roads_runs_dir)
        segment_cli_path = runs_dir / f"p{segment_run_id}.cli"
        segment_man_path = runs_dir / f"p{segment_run_id}.man"
        segment_sol_path = runs_dir / f"p{segment_run_id}.sol"
        segment_slp_path = runs_dir / f"p{segment_run_id}.slp"

        self._safe_link_or_copy(str(climate_source), str(segment_cli_path))

        if single_ofe_management_path.resolve() != segment_man_path.resolve():
            shutil.copy2(single_ofe_management_path, segment_man_path)
        if single_ofe_soil_path.resolve() != segment_sol_path.resolve():
            shutil.copy2(single_ofe_soil_path, segment_sol_path)
        if single_ofe_slope_path.resolve() != segment_slp_path.resolve():
            shutil.copy2(single_ofe_slope_path, segment_slp_path)

        make_hillslope_run(segment_run_id, sim_years, str(runs_dir), reveg=False)
        run_hillslope(segment_run_id, str(runs_dir), wepp_bin=wepp_bin)

    def _build_roads_segment_loss_summary_parquet(self, *, interchange_dir: Path) -> str:
        """Build a segment-level Roads loss summary parquet from manifest + hillslope loss outputs."""
        import duckdb
        import pandas as pd

        manifest_path = Path(self.roads_segment_pass_manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing Roads segment manifest: {manifest_path}")

        loss_hill_path = interchange_dir / "loss_pw0.hill.parquet"
        if not loss_hill_path.exists():
            raise FileNotFoundError(f"Missing roads hillslope loss parquet: {loss_hill_path}")

        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid Roads segment manifest JSON: {manifest_path}") from exc

        if not isinstance(payload, list):
            raise ValueError(f"Roads segment manifest must be a JSON list: {manifest_path}")

        def _as_int(value: Any) -> Optional[int]:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _as_float(value: Any) -> Optional[float]:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        records: List[Dict[str, Any]] = []
        for row in payload:
            if not isinstance(row, Mapping):
                continue

            status = str(row.get("status") or "completed").strip().lower()
            if status != "completed":
                continue

            segment_run_id = _as_int(row.get("segment_run_id"))
            if segment_run_id is None:
                continue

            records.append(
                {
                    "segment_id": str(row.get("segment_id") or segment_run_id),
                    "segment_run_id": segment_run_id,
                    "target_hillslope_wepp_id": _as_int(row.get("target_hillslope_wepp_id")),
                    "topaz_id_hill_lowpoint": _as_int(row.get("topaz_id_hill_lowpoint")),
                    "topaz_id_chn_lowpoint": _as_int(row.get("topaz_id_chn_lowpoint")),
                    "design": str(row.get("design") or ""),
                    "surface": str(row.get("surface") or ""),
                    "traffic": str(row.get("traffic") or ""),
                    "soil_texture": str(row.get("soil_texture") or ""),
                    "rfg_pct": _as_float(row.get("rfg_pct")),
                    "road_width_m": _as_float(row.get("road_width_m")),
                    "segment_length_m": _as_float(row.get("segment_length_m")),
                    "slope_pct_clamped": _as_float(row.get("slope_pct_clamped")),
                }
            )

        manifest_frame = pd.DataFrame.from_records(
            records,
            columns=[
                "segment_id",
                "segment_run_id",
                "target_hillslope_wepp_id",
                "topaz_id_hill_lowpoint",
                "topaz_id_chn_lowpoint",
                "design",
                "surface",
                "traffic",
                "soil_texture",
                "rfg_pct",
                "road_width_m",
                "segment_length_m",
                "slope_pct_clamped",
            ],
        )
        if manifest_frame.empty:
            manifest_frame = pd.DataFrame(
                {
                    "segment_id": pd.Series(dtype="string"),
                    "segment_run_id": pd.Series(dtype="int64"),
                    "target_hillslope_wepp_id": pd.Series(dtype="Int64"),
                    "topaz_id_hill_lowpoint": pd.Series(dtype="Int64"),
                    "topaz_id_chn_lowpoint": pd.Series(dtype="Int64"),
                    "design": pd.Series(dtype="string"),
                    "surface": pd.Series(dtype="string"),
                    "traffic": pd.Series(dtype="string"),
                    "soil_texture": pd.Series(dtype="string"),
                    "rfg_pct": pd.Series(dtype="float64"),
                    "road_width_m": pd.Series(dtype="float64"),
                    "segment_length_m": pd.Series(dtype="float64"),
                    "slope_pct_clamped": pd.Series(dtype="float64"),
                }
            )

        summary_path = interchange_dir / "roads_segment_loss_summary.parquet"
        summary_path_sql = str(summary_path).replace("'", "''")

        with duckdb.connect(database=":memory:") as con:
            con.register("segment_manifest", manifest_frame)
            con.execute(
                f"""
                COPY (
                    SELECT
                        manifest.segment_id::VARCHAR AS segment_id,
                        manifest.segment_run_id::BIGINT AS segment_run_id,
                        manifest.target_hillslope_wepp_id::BIGINT AS target_hillslope_wepp_id,
                        manifest.topaz_id_hill_lowpoint::BIGINT AS topaz_id_hill_lowpoint,
                        manifest.topaz_id_chn_lowpoint::BIGINT AS topaz_id_chn_lowpoint,
                        manifest.design::VARCHAR AS design,
                        manifest.surface::VARCHAR AS surface,
                        manifest.traffic::VARCHAR AS traffic,
                        manifest.soil_texture::VARCHAR AS soil_texture,
                        manifest.rfg_pct::DOUBLE AS rfg_pct,
                        manifest.road_width_m::DOUBLE AS road_width_m,
                        manifest.segment_length_m::DOUBLE AS segment_length_m,
                        manifest.slope_pct_clamped::DOUBLE AS slope_pct_clamped,
                        CASE
                            WHEN target_hill.wepp_id IS NOT NULL THEN 'target_hillslope_wepp_id'
                            WHEN segment_hill.wepp_id IS NOT NULL THEN 'segment_run_id'
                            ELSE NULL
                        END AS loss_match_key,
                        COALESCE(
                            CAST(target_hill."Runoff Volume" AS DOUBLE),
                            CAST(segment_hill."Runoff Volume" AS DOUBLE),
                            0.0
                        ) AS runoff_volume_m3,
                        COALESCE(
                            CAST(target_hill."Subrunoff Volume" AS DOUBLE),
                            CAST(segment_hill."Subrunoff Volume" AS DOUBLE),
                            0.0
                        ) AS subrunoff_volume_m3,
                        COALESCE(
                            CAST(target_hill."Baseflow Volume" AS DOUBLE),
                            CAST(segment_hill."Baseflow Volume" AS DOUBLE),
                            0.0
                        ) AS baseflow_volume_m3,
                        COALESCE(
                            CAST(target_hill."Soil Loss" AS DOUBLE),
                            CAST(segment_hill."Soil Loss" AS DOUBLE),
                            0.0
                        ) AS soil_loss_kg,
                        COALESCE(
                            CAST(target_hill."Sediment Deposition" AS DOUBLE),
                            CAST(segment_hill."Sediment Deposition" AS DOUBLE),
                            0.0
                        ) AS sediment_deposition_kg,
                        COALESCE(
                            CAST(target_hill."Sediment Yield" AS DOUBLE),
                            CAST(segment_hill."Sediment Yield" AS DOUBLE),
                            0.0
                        ) AS sediment_yield_kg,
                        COALESCE(
                            CAST(target_hill."Hillslope Area" AS DOUBLE),
                            CAST(segment_hill."Hillslope Area" AS DOUBLE),
                            0.0
                        ) AS hillslope_area_ha,
                        CASE
                            WHEN COALESCE(
                                    CAST(target_hill."Hillslope Area" AS DOUBLE),
                                    CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                    0.0
                                ) > 0.0
                                THEN (
                                        COALESCE(
                                            CAST(target_hill."Runoff Volume" AS DOUBLE),
                                            CAST(segment_hill."Runoff Volume" AS DOUBLE),
                                            0.0
                                        ) * 1000.0
                                    ) / (
                                        COALESCE(
                                            CAST(target_hill."Hillslope Area" AS DOUBLE),
                                            CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                            0.0
                                        ) * 10000.0
                                    )
                            ELSE NULL
                        END AS runoff_depth_mm,
                        CASE
                            WHEN COALESCE(
                                    CAST(target_hill."Hillslope Area" AS DOUBLE),
                                    CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                    0.0
                                ) > 0.0
                                THEN COALESCE(
                                        CAST(target_hill."Soil Loss" AS DOUBLE),
                                        CAST(segment_hill."Soil Loss" AS DOUBLE),
                                        0.0
                                    ) / (
                                        COALESCE(
                                            CAST(target_hill."Hillslope Area" AS DOUBLE),
                                            CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                            0.0
                                        ) * 10000.0
                                    )
                            ELSE NULL
                        END AS soil_loss_density_kg_m2,
                        CASE
                            WHEN COALESCE(
                                    CAST(target_hill."Hillslope Area" AS DOUBLE),
                                    CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                    0.0
                                ) > 0.0
                                THEN COALESCE(
                                        CAST(target_hill."Sediment Yield" AS DOUBLE),
                                        CAST(segment_hill."Sediment Yield" AS DOUBLE),
                                        0.0
                                    ) / (
                                        COALESCE(
                                            CAST(target_hill."Hillslope Area" AS DOUBLE),
                                            CAST(segment_hill."Hillslope Area" AS DOUBLE),
                                            0.0
                                        ) * 10000.0
                                    )
                            ELSE NULL
                        END AS sediment_yield_density_kg_m2,
                        CASE
                            WHEN ABS(
                                COALESCE(
                                    CAST(target_hill."Soil Loss" AS DOUBLE),
                                    CAST(segment_hill."Soil Loss" AS DOUBLE),
                                    0.0
                                )
                            ) > 0.0
                                THEN COALESCE(
                                        CAST(target_hill."Sediment Yield" AS DOUBLE),
                                        CAST(segment_hill."Sediment Yield" AS DOUBLE),
                                        0.0
                                    ) / COALESCE(
                                        CAST(target_hill."Soil Loss" AS DOUBLE),
                                        CAST(segment_hill."Soil Loss" AS DOUBLE),
                                        0.0
                                    )
                            ELSE NULL
                        END AS sediment_delivery_ratio,
                        COALESCE(
                            CAST(target_hill."Soil Loss" AS DOUBLE),
                            CAST(segment_hill."Soil Loss" AS DOUBLE),
                            0.0
                        ) AS road_prism_erosion_kg,
                        COALESCE(
                            CAST(target_hill."Sediment Yield" AS DOUBLE),
                            CAST(segment_hill."Sediment Yield" AS DOUBLE),
                            0.0
                        ) AS sediment_leaving_buffer_kg,
                        CASE
                            WHEN target_hill.wepp_id IS NULL AND segment_hill.wepp_id IS NULL THEN TRUE
                            ELSE FALSE
                        END AS loss_row_missing
                    FROM segment_manifest AS manifest
                    LEFT JOIN read_parquet(?) AS target_hill
                        ON CAST(target_hill.wepp_id AS BIGINT) = CAST(manifest.target_hillslope_wepp_id AS BIGINT)
                    LEFT JOIN read_parquet(?) AS segment_hill
                        ON CAST(segment_hill.wepp_id AS BIGINT) = CAST(manifest.segment_run_id AS BIGINT)
                    ORDER BY sediment_yield_kg DESC, segment_run_id ASC
                ) TO '{summary_path_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)
                """,
                [str(loss_hill_path), str(loss_hill_path)],
            )

        return os.path.relpath(summary_path, self.wd)

    def _required_roads_report_resource_relpaths(
        self,
        *,
        is_single_storm: bool,
        include_chnwb: bool,
        include_segment_loss_summary: bool,
    ) -> List[str]:
        base = os.path.join("wepp", "roads", "output", "interchange")
        required = [
            os.path.join(base, "H.pass.parquet"),
            os.path.join(base, "ebe_pw0.parquet"),
            os.path.join(base, "README.md"),
        ]
        if not is_single_storm:
            required.extend(
                [
                    os.path.join(base, "H.wat.parquet"),
                    os.path.join(base, "loss_pw0.out.parquet"),
                    os.path.join(base, "loss_pw0.hill.parquet"),
                    os.path.join(base, "loss_pw0.chn.parquet"),
                    os.path.join(base, "totalwatsed3.parquet"),
                ]
            )
            if include_segment_loss_summary:
                required.append(os.path.join(base, "roads_segment_loss_summary.parquet"))
            if include_chnwb:
                required.append(os.path.join(base, "chnwb.parquet"))
        return required

    def _regenerate_roads_report_resources(self) -> Dict[str, Any]:
        from wepppy.nodb.wepp_nodb_post_utils import activate_query_engine_for_run
        from wepppy.wepp.interchange import (
            generate_interchange_documentation,
            run_totalwatsed3,
            run_wepp_hillslope_interchange,
            run_wepp_watershed_interchange,
        )

        climate = self.wepp_instance.climate_instance
        is_single_storm = bool(getattr(climate, "is_single_storm", False))
        start_year_raw = getattr(climate, "calendar_start_year", None)
        start_year = int(start_year_raw) if start_year_raw not in (None, "") else None
        output_dir = Path(self.roads_output_dir)
        interchange_dir = output_dir / "interchange"
        hillslope_soil_available = any(output_dir.glob("H*.soil.dat"))
        watershed_soil_available = (output_dir / "soil_pw0.txt").exists()
        chan_out_available = (output_dir / "chan.out").exists() or (output_dir / "chan.out.gz").exists()
        chnwb_available = (output_dir / "chnwb.txt").exists() or (output_dir / "chnwb.txt.gz").exists()
        run_hillslope_soil_interchange = not is_single_storm and hillslope_soil_available
        run_watershed_soil_interchange = not is_single_storm and watershed_soil_available
        run_chan_out_interchange = not is_single_storm and chan_out_available
        run_chnwb_interchange = not is_single_storm and chnwb_available

        self._append_roads_log(
            "run",
            "roads_report_resources_regen_started",
            {
                "roads_output_relpath": os.path.relpath(output_dir, self.wd),
                "is_single_storm": is_single_storm,
                "start_year": start_year,
                "run_hillslope_soil_interchange": run_hillslope_soil_interchange,
                "run_watershed_soil_interchange": run_watershed_soil_interchange,
                "run_chan_out_interchange": run_chan_out_interchange,
                "run_chnwb_interchange": run_chnwb_interchange,
            },
        )

        run_wepp_hillslope_interchange(
            output_dir,
            start_year=start_year,
            run_loss_interchange=not is_single_storm,
            run_soil_interchange=run_hillslope_soil_interchange,
            run_wat_interchange=not is_single_storm,
            delete_after_interchange=False,
        )
        self._append_roads_log(
            "run",
            "roads_hillslope_interchange_completed",
            {"interchange_relpath": os.path.relpath(interchange_dir, self.wd)},
        )

        if not is_single_storm:
            baseflow_opts = getattr(self.wepp_instance, "baseflow_opts", None)
            if baseflow_opts is None:
                from wepppy.nodb.core.wepp import BaseflowOpts

                baseflow_opts = BaseflowOpts()
            run_totalwatsed3(interchange_dir, baseflow_opts=baseflow_opts)
            self._append_roads_log(
                "run",
                "roads_totalwatsed3_completed",
                {"totalwatsed3_relpath": os.path.relpath(interchange_dir / "totalwatsed3.parquet", self.wd)},
            )

        run_wepp_watershed_interchange(
            output_dir,
            start_year=start_year,
            run_chan_out_interchange=run_chan_out_interchange,
            run_soil_interchange=run_watershed_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
            delete_after_interchange=False,
        )
        self._append_roads_log(
            "run",
            "roads_watershed_interchange_completed",
            {"interchange_relpath": os.path.relpath(interchange_dir, self.wd)},
        )

        roads_segment_loss_summary_relpath = None
        if not is_single_storm:
            roads_segment_loss_summary_relpath = self._build_roads_segment_loss_summary_parquet(
                interchange_dir=interchange_dir
            )
            self._append_roads_log(
                "run",
                "roads_segment_loss_summary_parquet_completed",
                {"roads_segment_loss_summary_relpath": roads_segment_loss_summary_relpath},
            )

        generate_interchange_documentation(interchange_dir)
        self._append_roads_log(
            "run",
            "roads_interchange_readme_completed",
            {"readme_relpath": os.path.relpath(interchange_dir / "README.md", self.wd)},
        )

        activate_query_engine_for_run(self.wepp_instance)
        self._append_roads_log("run", "roads_query_engine_catalog_refreshed")

        required_relpaths = self._required_roads_report_resource_relpaths(
            is_single_storm=is_single_storm,
            include_chnwb=run_chnwb_interchange,
            include_segment_loss_summary=not is_single_storm,
        )
        missing_relpaths = [relpath for relpath in required_relpaths if not Path(self.wd, relpath).exists()]
        if missing_relpaths:
            self._append_roads_log(
                "run",
                "roads_report_resources_missing",
                {"missing_relpaths": missing_relpaths},
            )
            missing = ", ".join(missing_relpaths)
            raise FileNotFoundError(
                f"Roads report resource regeneration incomplete; missing required resources: {missing}"
            )

        resources = {
            "status": "ready",
            "output_scope": "roads",
            "roads_output_relpath": os.path.relpath(output_dir, self.wd),
            "interchange_relpath": os.path.relpath(interchange_dir, self.wd),
            "required_relpaths": required_relpaths,
            "missing_relpaths": [],
            "roads_segment_loss_summary_relpath": roads_segment_loss_summary_relpath,
            "generated_at": int(time.time()),
        }
        self._append_roads_log(
            "run",
            "roads_report_resources_regen_completed",
            {
                "required_resource_count": len(required_relpaths),
                "interchange_relpath": resources["interchange_relpath"],
            },
        )
        return resources

    def run_roads_wepp(self) -> Dict[str, Any]:
        failed_run_summary: Optional[Dict[str, Any]] = None
        run_summary_base: Optional[Dict[str, Any]] = None
        current_stage = "startup"
        try:
            if not self.enabled:
                raise ValueError("Roads must be enabled before run_roads_wepp.")

            self._require_prepare_state_current()
            current_stage = "load_prepared_segments"
            features = self._load_segment_features()
            translator = self.watershed_instance.translator_factory()
            top2wepp = dict(getattr(translator, "top2wepp", {}))
            self._append_roads_log(
                "run",
                "translator_loaded",
                {"top2wepp_count": len(top2wepp)},
            )

            with self.locked():
                self._status = "running"
                self._errors = []
                self._last_run_summary = None
                self._timestamps["run_started"] = int(time.time())

            self._ensure_roads_dirs()
            self._reset_roads_log("run")
            self._append_roads_log(
                "run",
                "start_run_roads_wepp",
                {"prepared_feature_count": len(features)},
            )
            current_stage = "prepare_workspace"
            self._prepare_roads_output_workspace()
            self._append_roads_log(
                "run",
                "roads_output_workspace_prepared",
                {"roads_output_relpath": os.path.relpath(self.roads_output_dir, self.wd)},
            )
            self._prepare_roads_runs_workspace()
            self._append_roads_log(
                "run",
                "roads_runs_workspace_prepared",
                {"roads_runs_relpath": os.path.relpath(self.roads_runs_dir, self.wd)},
            )

            params = dict(getattr(self, "_roads_params", self._default_params()))
            input_crs = CRS.from_user_input(str(params.get("input_crs") or "EPSG:4326"))
            geod = Geod(ellps="WGS84")
            dem_path = self._resolve_prepare_raster_paths()["dem_path"]

            segment_pass_paths_by_wepp: Dict[int, List[str]] = defaultdict(list)
            segment_execution_records: List[Dict[str, Any]] = []
            skipped_segments: List[Dict[str, Any]] = []
            eligible_segment_count = 0
            mapped_segment_count = 0
            successful_segment_count = 0
            segment_sequence = 0
            management_cache_by_traffic: Dict[str, Path] = {}
            failed_segment_records: List[Dict[str, Any]] = []

            current_stage = "segment_runs"
            with rasterio.open(dem_path) as dem_dataset:
                if dem_dataset.crs is None:
                    raise ValueError(f"Roads DEM is missing CRS metadata: {dem_path}")
                input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
                input_to_dem = Transformer.from_crs(input_crs, dem_dataset.crs, always_xy=True)

                for feature in features:
                    properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
                    design = self._first_non_empty_property(properties, ("DESIGN", "design"))
                    segment_id = self._segment_key(feature)

                    if not _is_eligible_design(design):
                        skipped_segments.append({"segment_id": segment_id, "reason": "design_not_eligible"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "design_not_eligible"},
                        )
                        continue

                    eligible_segment_count += 1
                    hill_topaz = properties.get("topaz_id_hill_lowpoint")
                    chn_topaz = properties.get("topaz_id_chn_lowpoint")
                    if hill_topaz is None or chn_topaz is None:
                        skipped_segments.append({"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"},
                        )
                        continue

                    try:
                        hill_topaz_int = int(hill_topaz)
                        chn_topaz_int = int(chn_topaz)
                    except (TypeError, ValueError):
                        skipped_segments.append({"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"},
                        )
                        continue

                    wepp_id = top2wepp.get(hill_topaz_int)
                    if wepp_id is None:
                        skipped_segments.append({"segment_id": segment_id, "reason": "translator_missing_hillslope_map"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "translator_missing_hillslope_map"},
                        )
                        continue

                    mapped_segment_count += 1
                    wepp_id_int = int(wepp_id)

                    segment_inputs = self._resolve_segment_run_inputs(properties=properties, params=params)

                    try:
                        profile = self._build_segment_profile(
                            feature=feature,
                            input_crs=input_crs,
                            dem_dataset=dem_dataset,
                            input_to_wgs84=input_to_wgs84,
                            input_to_dem=input_to_dem,
                            geod=geod,
                        )
                    except ValueError as exc:
                        skipped_segments.append({"segment_id": segment_id, "reason": "segment_profile_unavailable"})
                        segment_execution_records.append(
                            {
                                "segment_id": segment_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "status": "skipped",
                                "reason": "segment_profile_unavailable",
                                "error": str(exc),
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {
                                "segment_id": segment_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "reason": "segment_profile_unavailable",
                                "error": str(exc),
                            },
                        )
                        continue

                    segment_sequence += 1
                    segment_run_id = 900000 + segment_sequence
                    soil_template_path = self._resolve_legacy_soil_template_path(
                        design=segment_inputs["design"],
                        surface=segment_inputs["surface"],
                        soil_texture=segment_inputs["soil_texture"],
                    )

                    management_path = management_cache_by_traffic.get(segment_inputs["traffic"])
                    if management_path is None:
                        management_path = self._materialize_single_ofe_management_template(
                            traffic=segment_inputs["traffic"]
                        )
                        management_cache_by_traffic[segment_inputs["traffic"]] = management_path

                    segment_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.single_ofe.sol"
                    segment_slope_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.slp"

                    self._build_single_ofe_soil_file(
                        template_path=soil_template_path,
                        output_path=segment_soil_path,
                        traffic=segment_inputs["traffic"],
                        surface=segment_inputs["surface"],
                        rfg_pct=segment_inputs["rfg_pct"],
                    )
                    self._write_single_ofe_slope_file(
                        segment_slope_path,
                        width_m=segment_inputs["road_width_m"],
                        length_m=profile["segment_length_m"],
                        slope_pct=profile["slope_pct"],
                    )

                    self._append_roads_log(
                        "run",
                        "segment_inputs_ready",
                        {
                            "segment_id": segment_id,
                            "segment_run_id": segment_run_id,
                            "target_hillslope_wepp_id": wepp_id_int,
                            "design": segment_inputs["design"],
                            "surface": segment_inputs["surface"],
                            "traffic": segment_inputs["traffic"],
                            "soil_texture": segment_inputs["soil_texture"],
                            "rfg_pct": segment_inputs["rfg_pct"],
                            "road_width_m": segment_inputs["road_width_m"],
                            "segment_length_m": profile["segment_length_m"],
                            "slope_pct_raw": profile["raw_slope_pct"],
                            "slope_pct_clamped": profile["slope_pct"],
                            "high_point": profile["high_point"],
                            "low_point": profile["low_point"],
                        },
                    )

                    try:
                        sim_years = int(self.wepp_instance.climate_instance.input_years)
                        self._run_segment_hillslope(
                            segment_run_id=segment_run_id,
                            climate_wepp_id=wepp_id_int,
                            sim_years=sim_years,
                            wepp_bin=getattr(self.wepp_instance, "wepp_bin", None),
                            single_ofe_management_path=management_path,
                            single_ofe_soil_path=segment_soil_path,
                            single_ofe_slope_path=segment_slope_path,
                        )
                    except Exception as exc:
                        skipped_segments.append({"segment_id": segment_id, "reason": "segment_run_failed"})
                        segment_execution_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "status": "failed",
                                "reason": "segment_run_failed",
                                "error": str(exc),
                            }
                        )
                        failed_segment_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "reason": "segment_run_failed",
                                "error": str(exc),
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_run_failed",
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "error": str(exc),
                            },
                        )
                        continue

                    segment_pass_path = Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat"
                    if not segment_pass_path.exists():
                        skipped_segments.append({"segment_id": segment_id, "reason": "segment_pass_missing"})
                        segment_execution_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "status": "failed",
                                "reason": "segment_pass_missing",
                            }
                        )
                        failed_segment_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "reason": "segment_pass_missing",
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_run_failed",
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "reason": "segment_pass_missing",
                            },
                        )
                        continue

                    successful_segment_count += 1
                    segment_pass_paths_by_wepp[wepp_id_int].append(str(segment_pass_path))
                    execution_record = {
                        "segment_id": segment_id,
                        "segment_run_id": segment_run_id,
                        "target_hillslope_wepp_id": wepp_id_int,
                        "status": "completed",
                        "topaz_id_chn_lowpoint": chn_topaz_int,
                        "topaz_id_hill_lowpoint": hill_topaz_int,
                        "design": segment_inputs["design"],
                        "surface": segment_inputs["surface"],
                        "traffic": segment_inputs["traffic"],
                        "soil_texture": segment_inputs["soil_texture"],
                        "rfg_pct": segment_inputs["rfg_pct"],
                        "road_width_m": segment_inputs["road_width_m"],
                        "segment_length_m": profile["segment_length_m"],
                        "slope_pct_raw": profile["raw_slope_pct"],
                        "slope_pct_clamped": profile["slope_pct"],
                        "elevation_high_m": profile["elevation_high_m"],
                        "elevation_low_m": profile["elevation_low_m"],
                        "segment_pass_relpath": os.path.relpath(segment_pass_path, self.wd),
                    }
                    segment_execution_records.append(execution_record)
                    self._append_roads_log("run", "segment_run_completed", execution_record)

            Path(self.roads_segment_pass_manifest_path).write_text(
                json.dumps(segment_execution_records, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            self._append_roads_log(
                "run",
                "segment_manifest_written",
                {
                    "segment_execution_count": len(segment_execution_records),
                    "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                },
            )

            skipped_reason_counts = Counter(
                str(row.get("reason") or "unknown") for row in skipped_segments
            )

            if failed_segment_records:
                failed_run_summary = {
                    "eligible_segment_count": eligible_segment_count,
                    "mapped_segment_count": mapped_segment_count,
                    "executed_segment_count": successful_segment_count,
                    "targeted_hillslope_count": 0,
                    "targeted_hillslope_wepp_ids": [],
                    "skipped_segments": skipped_segments,
                    "skipped_segment_reason_counts": dict(sorted(skipped_reason_counts.items())),
                    "segment_execution_records": segment_execution_records,
                    "pass_staging_strategy": {},
                    "segment_pass_count": successful_segment_count,
                    "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                    "roads_runs_relpath": os.path.relpath(self.roads_runs_dir, self.wd),
                    "roads_output_relpath": os.path.relpath(self.roads_output_dir, self.wd),
                    "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
                    "status": "failed",
                    "failed_stage": "segment_runs",
                    "failed_segment_count": len(failed_segment_records),
                    "failed_segments": failed_segment_records,
                    "error": (
                        "Roads segment execution failed for "
                        f"{len(failed_segment_records)} segment(s); see roads.segment.pass.manifest.json and roads.log."
                    ),
                    "failed_at": int(time.time()),
                }
                self._append_roads_log(
                    "run",
                    "segment_stage_failed",
                    {
                        "failed_segment_count": len(failed_segment_records),
                        "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                    },
                )
                raise RuntimeError(failed_run_summary["error"])

            baseline_output_dir = Path(self.wepp_instance.output_dir)
            if not baseline_output_dir.exists():
                raise FileNotFoundError(f"Missing baseline WEPP output directory: {baseline_output_dir}")

            staged_strategy: Dict[str, str] = {}
            targeted_ids = sorted(segment_pass_paths_by_wepp)
            all_hillslope_wepp_ids = sorted(int(value) for value in translator.iter_wepp_sub_ids())

            current_stage = "pass_combination"
            for wepp_id in all_hillslope_wepp_ids:
                base_pass_path = baseline_output_dir / f"H{wepp_id}.pass.dat"
                if not base_pass_path.exists():
                    raise FileNotFoundError(f"Missing baseline hillslope pass file: {base_pass_path}")

                output_pass_path = Path(self.roads_output_dir) / f"H{wepp_id}.pass.dat"
                staged_strategy[str(wepp_id)] = self._safe_link_or_copy(str(base_pass_path), str(output_pass_path))
                self._append_roads_log(
                    "run",
                    "baseline_hillslope_staged",
                    {
                        "wepp_id": wepp_id,
                        "base_pass_relpath": os.path.relpath(base_pass_path, self.wd),
                        "staged_pass_relpath": os.path.relpath(output_pass_path, self.wd),
                        "strategy": staged_strategy[str(wepp_id)],
                    },
                )

            for wepp_id in targeted_ids:
                base_pass_path = baseline_output_dir / f"H{wepp_id}.pass.dat"
                output_pass_path = Path(self.roads_output_dir) / f"H{wepp_id}.pass.dat"
                output_was_symlink = output_pass_path.is_symlink()
                if output_pass_path.exists() or output_was_symlink:
                    output_pass_path.unlink()
                self._append_roads_log(
                    "run",
                    "combine_target_hillslope_start",
                    {
                        "wepp_id": wepp_id,
                        "base_pass_relpath": os.path.relpath(base_pass_path, self.wd),
                        "road_pass_count": len(segment_pass_paths_by_wepp.get(wepp_id, [])),
                        "output_pass_relpath": os.path.relpath(output_pass_path, self.wd),
                        "output_was_symlink": output_was_symlink,
                    },
                )
                self._combine_target_hillslope_pass(
                    base_pass_path=str(base_pass_path),
                    road_pass_paths=segment_pass_paths_by_wepp.get(wepp_id, []),
                    output_pass_path=str(output_pass_path),
                )
                staged_strategy[str(wepp_id)] = "combined"
                self._append_roads_log(
                    "run",
                    "combined_hillslope_pass",
                    {
                        "wepp_id": wepp_id,
                        "base_pass_relpath": os.path.relpath(base_pass_path, self.wd),
                        "road_pass_count": len(segment_pass_paths_by_wepp.get(wepp_id, [])),
                        "combined_pass_relpath": os.path.relpath(output_pass_path, self.wd),
                    },
                )

            run_summary_base = {
                "eligible_segment_count": eligible_segment_count,
                "mapped_segment_count": mapped_segment_count,
                "executed_segment_count": successful_segment_count,
                "targeted_hillslope_count": len(targeted_ids),
                "targeted_hillslope_wepp_ids": targeted_ids,
                "skipped_segments": skipped_segments,
                "skipped_segment_reason_counts": dict(sorted(skipped_reason_counts.items())),
                "segment_execution_records": segment_execution_records,
                "pass_staging_strategy": staged_strategy,
                "segment_pass_count": successful_segment_count,
                "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                "roads_runs_relpath": os.path.relpath(self.roads_runs_dir, self.wd),
                "roads_output_relpath": os.path.relpath(self.roads_output_dir, self.wd),
                "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
                "watershed_run_relpath": os.path.relpath(
                    os.path.join(self.roads_runs_dir, "pw0.run"),
                    self.wd,
                ),
            }
            current_stage = "watershed_rerun"

            try:
                wepp_id_paths = [os.path.join("..", "output", f"H{wepp_id}") for wepp_id in all_hillslope_wepp_ids]
                years = int(self.wepp_instance.climate_instance.input_years)
                self._append_roads_log(
                    "run",
                    "watershed_rerun_start",
                    {
                        "years": years,
                        "hillslope_path_count": len(wepp_id_paths),
                        "watershed_run_relpath": run_summary_base["watershed_run_relpath"],
                    },
                )
                make_watershed_omni_contrasts_run(years, wepp_id_paths, self.roads_runs_dir)
                run_watershed(self.roads_runs_dir)
            except Exception as exc:
                failed_run_summary = {
                    **run_summary_base,
                    "status": "failed",
                    "failed_stage": "watershed_rerun",
                    "error": str(exc),
                    "failed_at": int(time.time()),
                }
                self._append_roads_log(
                    "run",
                    "watershed_rerun_failed",
                    {
                        "watershed_run_relpath": run_summary_base["watershed_run_relpath"],
                        "error": str(exc),
                    },
                )
                raise

            self._append_roads_log(
                "run",
                "watershed_rerun_completed",
                {"watershed_run_relpath": run_summary_base["watershed_run_relpath"]},
            )
            current_stage = "report_resource_regen"
            roads_report_resources = self._regenerate_roads_report_resources()

            run_summary = {
                **run_summary_base,
                "roads_report_resources": roads_report_resources,
                "status": "completed",
                "completed_at": int(time.time()),
            }

            with self.locked():
                self._last_run_summary = run_summary
                self._status = "completed"
                self._errors = []
                self._timestamps["run_roads"] = int(time.time())

            return dict(run_summary)
        except Exception as exc:
            if failed_run_summary is None:
                failed_run_summary = dict(run_summary_base or {})
                failed_run_summary.update(
                    {
                        "status": "failed",
                        "failed_stage": current_stage,
                        "error": str(exc),
                        "failed_at": int(time.time()),
                    }
                )
            with self.locked():
                self._last_run_summary = failed_run_summary
            self._record_error_and_raise(exc)

    def query_status(self) -> Dict[str, Any]:
        status_payload = {
            "enabled": bool(getattr(self, "_enabled", False)),
            "status": str(getattr(self, "_status", "idle")),
            "errors": list(getattr(self, "_errors", [])),
            "timestamps": dict(getattr(self, "_timestamps", {})),
        }
        self._append_roads_log(
            "query",
            "query_status",
            {
                "enabled": status_payload["enabled"],
                "status": status_payload["status"],
                "error_count": len(status_payload["errors"]),
            },
        )
        return status_payload

    def query_summary(self) -> Dict[str, Any]:
        summary_payload = {
            "enabled": bool(getattr(self, "_enabled", False)),
            "uploaded_geojson_relpath": getattr(self, "_uploaded_geojson_relpath", None),
            "uploaded_geojson_sha256": getattr(self, "_uploaded_geojson_sha256", None),
            "roads_params": dict(getattr(self, "_roads_params", self._default_params())),
            "last_prepare_summary": getattr(self, "_last_prepare_summary", None),
            "last_run_summary": getattr(self, "_last_run_summary", None),
            "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
            "status": str(getattr(self, "_status", "idle")),
            "errors": list(getattr(self, "_errors", [])),
            "timestamps": dict(getattr(self, "_timestamps", {})),
        }
        self._append_roads_log(
            "query",
            "query_summary",
            {
                "enabled": summary_payload["enabled"],
                "status": summary_payload["status"],
                "has_prepare_summary": summary_payload["last_prepare_summary"] is not None,
                "has_run_summary": summary_payload["last_run_summary"] is not None,
            },
        )
        return summary_payload
