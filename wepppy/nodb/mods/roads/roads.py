"""Roads NoDb controller for Roads point-source routing workflows."""

from __future__ import annotations

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER

from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary

import hashlib
import json
import os
import re
import shlex
import shutil
import time
import tempfile
import uuid
from copy import deepcopy
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from pyproj import CRS, Geod, Transformer
from shapely.geometry import GeometryCollection, LineString, MultiLineString, shape
from shapely.ops import transform as shapely_transform, unary_union
from wepp_runner.wepp_runner import (make_hillslope_run,
    make_watershed_omni_contrasts_run,
    run_hillslope,
    run_watershed,
)

from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.geojson_crs_inference import GeoBounds, infer_geojson_crs
from wepppy.nodb.mods.roads.monotonic_segments import convert_geojson_file_to_monotonic_segments
from wepppy.nodb.mods.roads import parameterization as roads_parameterization
from wepppy.nodb.mods.roads import _parameterization_comparisons, _unrutted

from . import _inputs

from . import _prepare

from . import _soil_inputs

from . import _management_inputs

from . import _slope_inputs

from . import _spatial

from . import _queries

from . import _parameterization_support

from . import _pass_routing

from . import _reporting

from . import _native_runner

__all__ = ["Roads"]


from ._constants import (
    DESIGN_ALIASES,
    ELIGIBLE_ROADS_DESIGNS,
    ELIGIBLE_POINT_SOURCE_DESIGNS,
    OUTSLOPE_UNRUTTED_AREA_EPSILON_M2,
    OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M,
    OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS,
    OUTSLOPE_UNRUTTED_BOUNDS,
    _normalize_design,
    _is_eligible_design,
    _is_hillslope_topaz_id,
    SURFACE_ALIASES,
    TRAFFIC_ALIASES,
    CONDITION_TRAFFIC_MAP,
    SOIL_TEXTURE_ALIASES,
    ALLOWED_SOIL_TEXTURES,
    ALLOWED_SURFACES,
    ALLOWED_TRAFFIC,
    ATTRIBUTE_FIELD_MAP_KEYS,
    LEGACY_DESIGN_KEYS,
    LEGACY_SURFACE_KEYS,
    LEGACY_TRAFFIC_KEYS,
    ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY,
    ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY,
    ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY,
    DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
)


class Roads(NoDbBase):
    """Persist run-scoped Roads state and orchestrate Roads prep/run stages."""

    __name__ = "Roads"
    filename = "roads.nodb"
    TRANSIENT_FIELDS = ("_parameterization_runtime_templates", "_parameterization_runtime_readbacks")

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
            self._uploaded_attribute_catalog = None
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
        else:
            instance._roads_params = instance._normalize_params_with_defaults(instance._roads_params)
        if not hasattr(instance, "_uploaded_attribute_catalog"):
            instance._uploaded_attribute_catalog = None
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
        return _inputs._default_params()

    @classmethod
    def _empty_attribute_field_map(cls) -> Dict[str, Optional[str]]:
        return _inputs._empty_attribute_field_map(cls)

    @classmethod
    def _normalize_attribute_field_map(
        cls,
        raw_map: Any,
        *,
        known_fields: Optional[Set[str]] = None,
    ) -> Dict[str, Optional[str]]:
        return _inputs._normalize_attribute_field_map(cls, raw_map, known_fields=known_fields)

    @classmethod
    def _normalize_params_with_defaults(cls, params: Mapping[str, Any]) -> Dict[str, Any]:
        return _inputs._normalize_params_with_defaults(cls, params)

    @staticmethod
    def _dedupe_keys(keys: Iterable[str]) -> Tuple[str, ...]:
        return _inputs._dedupe_keys(keys)

    @staticmethod
    def _first_non_empty_property_with_key(
        properties: Mapping[str, Any],
        keys: Iterable[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        return _inputs._first_non_empty_property_with_key(properties, keys)

    @staticmethod
    def _stringify_attribute_sample(value: Any, *, max_chars: int) -> str:
        return _inputs._stringify_attribute_sample(value, max_chars=max_chars)

    def _discovered_attribute_field_names(self) -> Tuple[str, ...]:
        return _inputs._discovered_attribute_field_names(self)

    def _build_attribute_catalog(
        self,
        *,
        payload: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return _inputs._build_attribute_catalog(self, payload=payload, params=params)

    @staticmethod
    def _collect_warning(
        warning_counts: Counter[str],
        warning_examples: List[Dict[str, Any]],
        *,
        code: str,
        message: str,
        limit: int,
        segment_id: Optional[str] = None,
        field_name: Optional[str] = None,
    ) -> None:
        return _inputs._collect_warning(
            warning_counts,
            warning_examples,
            code=code,
            message=message,
            limit=limit,
            segment_id=segment_id,
            field_name=field_name,
        )

    def _auto_discover_attribute_field_map(
        self,
        *,
        field_names: Sequence[str],
        previous_map: Mapping[str, Any],
    ) -> Dict[str, Optional[str]]:
        return _inputs._auto_discover_attribute_field_map(
            self,
            field_names=field_names,
            previous_map=previous_map,
        )

    def _resolve_design_for_feature(
        self,
        *,
        properties: Mapping[str, Any],
        attribute_field_map: Mapping[str, Optional[str]],
        warning_counts: Optional[Counter[str]] = None,
        warning_examples: Optional[List[Dict[str, Any]]] = None,
        warning_limit: int = DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
        segment_id: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        return _inputs._resolve_design_for_feature(
            self,
            properties=properties,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )

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

    @staticmethod
    def _is_projection_resolution_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "non-finite dem coordinates" in message or "non-finite dem length" in message

    @staticmethod
    def _read_dataset_metadata(path: str, *, label: str) -> Tuple[str, GeoBounds]:
        with rasterio.open(path) as dataset:
            dataset_crs = dataset.crs
            dataset_bounds = dataset.bounds
        if dataset_crs is None:
            raise ValueError(f"{label} must have a CRS.")
        try:
            CRS.from_user_input(dataset_crs)
        except Exception as exc:
            raise ValueError(f"{label} CRS is invalid: {exc}") from exc
        return (
            str(dataset_crs),
            (
                float(dataset_bounds.left),
                float(dataset_bounds.bottom),
                float(dataset_bounds.right),
                float(dataset_bounds.top),
            ),
        )

    @classmethod
    def _read_dataset_crs(cls, path: str, *, label: str) -> str:
        dataset_crs, _ = cls._read_dataset_metadata(path, label=label)
        return dataset_crs

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

        current_params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        prepared_signature = str(prepare_summary.get("roads_params_signature") or "")
        current_signature = self._params_signature(current_params)
        if not prepared_signature or prepared_signature != current_signature:
            raise ValueError("Roads parameters changed after prepare_segments. Run prepare_segments again.")

        state = self._saved_parameterization_state()
        if state is None:
            raise ValueError("Roads parameterization is unbound. Run prepare_segments before a new Roads run.")
        signature = roads_parameterization.configuration_hash(roads_parameterization.validate_state(state))
        if prepare_summary.get("parameterization_hash") != signature:
            raise ValueError("Roads parameterization changed after prepare_segments. Run prepare_segments again.")

        if status == "idle":
            raise ValueError("Roads segments are stale or missing. Run prepare_segments before run_roads_wepp.")

        if prepare_summary.get("unrutted_geometry_policy") != _unrutted.POLICY:
            field_map = current_params.get("attribute_field_map", {})
            for feature in self._load_prepared_segments_geojson()["features"]:
                design, _ = self._resolve_design_for_feature(
                    properties=feature.get("properties", {}), attribute_field_map=field_map,
                )
                if design == "outslope_unrutted":
                    raise ValueError("Unrutted geometry policy changed. Prepare and run Roads again.")

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

    def _resolve_trace_raster_paths(self) -> Dict[str, str]:
        base_paths = self._resolve_prepare_raster_paths()
        watershed = self.watershed_instance
        flovec_path = self._normalize_existing_path(getattr(watershed, "flovec", None))

        if flovec_path is None:
            wbt_wd = Path(getattr(watershed, "wbt_wd", Path(self.wd) / "dem" / "wbt"))
            flovec_candidates = (wbt_wd / "flovec.tif", wbt_wd / "flovec.vrt")
            for candidate in flovec_candidates:
                normalized = self._normalize_existing_path(str(candidate))
                if normalized is not None:
                    flovec_path = normalized
                    break

        if flovec_path is None:
            raise FileNotFoundError(
                "Roads run tracing requires an existing flow-vector raster (`watershed.flovec` or dem/wbt/flovec.tif)."
            )

        return {
            **base_paths,
            "flovec_path": flovec_path,
        }

    @staticmethod
    def _as_int_or_none(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_float_or_none(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_truthy_property(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"1", "true", "yes", "y"}
        return False

    def _clear_stale_run_state_locked(self) -> None:
        self._last_prepare_summary = None
        self._last_run_summary = None
        self._status = "idle"
        self._errors = []

    def _record_error_and_raise(self, exc: Exception) -> None:
        message = safe_text(str(exc), source_profile=current_profile(WORKER))
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

    @roads_lifecycle.mutation
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
        if not requested_enabled:
            roads_lifecycle.retain(self.wd, replace_segments=True)
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

    @classmethod
    def _validated_params_payload(cls, payload, current_params, *, known_fields=None):
        return _inputs._validated_params_payload(
            cls,
            payload,
            current_params,
            known_fields=known_fields,
        )

    @classmethod
    def validate_initial_params(cls, payload):
        """Validate a first-use request before creating any Roads state or files."""
        if not isinstance(payload, Mapping):
            raise ValueError("Roads params payload must be a JSON object.")
        params = cls._validated_params_payload(payload, cls._default_params())
        if "parameterization" in payload:
            roads_parameterization.apply_payload(
                roads_parameterization.UNBOUND, payload["parameterization"],
                template_root=Path(__file__).resolve().parent / "legacy_templates",
            )
        return params

    @roads_lifecycle.mutation
    def set_params(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("Roads params payload must be a JSON object.")

        self._append_roads_log(
            "config",
            "set_params_requested",
            {"keys": sorted(str(key) for key in payload.keys())},
        )
        with self.locked():
            self.recover_mutation_state()
            params = self._validated_params_payload(
                payload, self._roads_params,
                known_fields=set(self._discovered_attribute_field_names()) or None,
            )

            state = self._saved_parameterization_state()
            if "parameterization" in payload:
                state = roads_parameterization.apply_payload(
                    roads_parameterization.UNBOUND if state is None else state,
                    payload["parameterization"], template_root=Path(self.roads_legacy_templates_dir)
                )
            elif state is not None:
                state = roads_parameterization.validate_state(state)
            retained = roads_lifecycle.retain(self.wd, replace_segments=True)
            if "parameterization" in payload:
                # Retain the previous durable authority, including invalid repair input.
                history = Path(self.roads_wepp_dir) / "history"
                if history.resolve() != Path(self.wd).resolve() / "wepp/roads/history":
                    raise ValueError("Roads parameterization history path must not be aliased.")
                history.mkdir(parents=True, exist_ok=True)
                snapshot = retained or Path(tempfile.mkdtemp(prefix="parameterization-", dir=history))
                shutil.copy2(self._nodb, snapshot / "roads.nodb")
                self._parameterization = state
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

    @roads_lifecycle.mutation
    def set_uploaded_geojson(
        self,
        src_path: str,
        *,
        publication_commit: Callable[[], None] | None = None,
    ) -> Dict[str, Any]:
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

        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        max_upload_mb = int(params.get("max_upload_mb", 50))
        max_upload_bytes = max_upload_mb * 1024 * 1024
        if source_path.stat().st_size > max_upload_bytes:
            raise ValueError(f"Roads upload exceeds max_upload_mb limit ({max_upload_mb} MB).")

        payload = json.loads(source_path.read_text(encoding="utf-8"))
        self._validate_uploaded_geojson(payload)

        configured_input_crs = str(params.get("input_crs") or "EPSG:4326")
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

        project_crs: Optional[str] = None
        project_bounds: Optional[GeoBounds] = None
        try:
            raster_paths = self._resolve_prepare_raster_paths()
            project_crs, project_bounds = self._read_dataset_metadata(
                raster_paths["dem_path"],
                label="Roads prepare DEM",
            )
        except (FileNotFoundError, ValueError, RasterioIOError):
            project_crs = None
            project_bounds = None

        crs_inference = infer_geojson_crs(
            payload,
            explicit_crs=source_crs,
            project_crs=project_crs,
            configured_crs=configured_input_crs,
            project_bounds=project_bounds,
        )
        params["input_crs"] = crs_inference.crs
        effective_input_crs = crs_inference.crs
        input_crs_source = crs_inference.source

        self._ensure_roads_dirs()
        target_path = Path(self.roads_upload_dir) / "roads.uploaded.geojson"
        backup_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.backup")
        staged_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        had_target = target_path.exists()
        if had_target:
            shutil.copy2(target_path, backup_path)
        shutil.copy2(source_path, staged_path)
        retained_snapshot = None

        digest = hashlib.sha256(staged_path.read_bytes()).hexdigest()
        relpath = str(target_path.relative_to(self.wd))
        now = int(time.time())
        attribute_catalog = self._build_attribute_catalog(payload=payload, params=params)
        previous_map = self._normalize_attribute_field_map(params.get("attribute_field_map"), known_fields=None)
        discovered_map = self._auto_discover_attribute_field_map(
            field_names=attribute_catalog.get("field_names", []),
            previous_map=previous_map,
        )
        params["attribute_field_map"] = discovered_map
        publication_committed = False
        try:
            retained_snapshot = roads_lifecycle.retain(self.wd, replace_segments=True)
            with self.locked():
                prior_state = {
                    name: deepcopy(getattr(self, name, None))
                    for name in (
                        "_uploaded_geojson_relpath",
                        "_uploaded_geojson_sha256",
                        "_uploaded_attribute_catalog",
                        "_roads_params",
                        "_timestamps",
                        "_last_prepare_summary",
                        "_last_run_summary",
                        "_status",
                        "_errors",
                    )
                }
                try:
                    os.replace(staged_path, target_path)
                    self._uploaded_geojson_relpath = relpath
                    self._uploaded_geojson_sha256 = digest
                    self._uploaded_attribute_catalog = attribute_catalog
                    self._roads_params = params
                    self._timestamps["upload_geojson"] = now
                    self._clear_stale_run_state_locked()
                    status = str(self._status)
                    if publication_commit is not None:
                        publication_commit()
                    publication_committed = True
                except BaseException:  # broad-except: transaction rollback includes cancellation
                    if had_target:
                        os.replace(backup_path, target_path)
                    else:
                        target_path.unlink(missing_ok=True)
                    roads_lifecycle.restore_retained(self.wd, retained_snapshot)
                    for name, value in prior_state.items():
                        setattr(self, name, value)
                    raise
            try:
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
                        "effective_input_crs": effective_input_crs,
                        "input_crs_source": input_crs_source,
                        "discovered_attribute_field_count": int(attribute_catalog.get("field_count", 0)),
                        "attribute_field_map": discovered_map,
                        "status": status,
                    },
                )
            except OSError:
                self.logger.warning("Accepted Roads upload completion log is deferred", exc_info=True)
        except BaseException:  # broad-except: transaction rollback includes cancellation
            if publication_committed:
                raise
            staged_path.unlink(missing_ok=True)
            raise
        finally:
            staged_path.unlink(missing_ok=True)
            backup_path.unlink(missing_ok=True)

        return {
            "uploaded_geojson_relpath": relpath,
            "uploaded_geojson_sha256": digest,
            "feature_count": len(payload.get("features", [])),
            "uploaded_at": now,
            "configured_input_crs": configured_input_crs,
            "source_crs": source_crs,
            "effective_input_crs": effective_input_crs,
            "input_crs_source": input_crs_source,
            "discovered_attribute_catalog": attribute_catalog,
            "attribute_field_map": discovered_map,
        }

    def _load_segment_features(self) -> List[Dict[str, Any]]:
        return _queries._load_segment_features(self)

    def _load_prepared_segments_geojson(self) -> Dict[str, Any]:
        return _queries._load_prepared_segments_geojson(self)

    @staticmethod
    def _find_segment_feature(
        payload: Mapping[str, Any],
        *,
        segment_id: str,
    ) -> Optional[Dict[str, Any]]:
        features = payload.get("features")
        if not isinstance(features, list):
            return None
        for feature_index, feature in enumerate(features):
            if not isinstance(feature, Mapping):
                continue
            candidate = Roads._segment_key(feature, fallback_index=feature_index)
            if str(candidate) == segment_id:
                return dict(feature)
        return None

    def _load_segment_execution_manifest(self) -> Dict[str, Dict[str, Any]]:
        return _queries._load_segment_execution_manifest(self)

    def _build_segment_profile_for_query(
        self,
        *,
        feature: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return _queries._build_segment_profile_for_query(self, feature=feature, params=params)

    @staticmethod
    def _derive_routing_mode_hint(properties: Mapping[str, Any]) -> str:
        return _queries._derive_routing_mode_hint(properties)

    @roads_lifecycle.inspection
    def query_map_segments_geojson(self) -> Dict[str, Any]:
        return _queries.query_map_segments_geojson(self)

    @roads_lifecycle.inspection
    def query_segment_detail(self, segment_id: str) -> Dict[str, Any]:
        return _queries.query_segment_detail(self, segment_id)

    @roads_lifecycle.mutation
    def prepare_segments(self) -> Dict[str, Any]:
        try:
            if not self.enabled:
                raise ValueError("Roads must be enabled before preparing segments.")

            staged_path = self.roads_staged_geojson_path
            if not staged_path:
                raise ValueError("No roads GeoJSON has been uploaded.")

            self._ensure_roads_dirs()
            self._append_roads_log(
                "prepare",
                "start_prepare_segments",
                {"uploaded_geojson_relpath": self._path_for_summary(staged_path)},
            )
            params, attribute_field_map, design_property_keys, warning_limit = _prepare.configuration(self)
            configured_input_crs = str(params.get("input_crs") or "EPSG:4326")
            try:
                CRS.from_user_input(configured_input_crs)
            except Exception as exc:
                # broad-except: preserve the CRS input error translation boundary.
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
            staged_payload = json.loads(Path(staged_path).read_text(encoding="utf-8"))
            source_crs = self._extract_geojson_crs(staged_payload)
            dem_input_crs: Optional[str] = None
            dem_bounds: Optional[GeoBounds] = None
            try:
                dem_input_crs, dem_bounds = self._read_dataset_metadata(
                    raster_paths["dem_path"],
                    label="Roads prepare DEM",
                )
            except RasterioIOError:
                dem_input_crs = None
                dem_bounds = None
            crs_inference = infer_geojson_crs(
                staged_payload,
                explicit_crs=source_crs,
                project_crs=dem_input_crs,
                configured_crs=configured_input_crs,
                project_bounds=dem_bounds,
            )
            input_crs_value = crs_inference.crs
            input_crs_source = crs_inference.source
            with self.locked():
                self.recover_mutation_state()
                if self._normalize_params_with_defaults(self._roads_params) != params:
                    raise ValueError("Roads settings changed while preparing; retry Prepare.")
                state = self._saved_parameterization_state()
                self._parameterization = (
                    roads_parameterization.new_state(Path(self.roads_legacy_templates_dir))
                    if state is None else roads_parameterization.validate_state(state)
                )
                roads_lifecycle.retain(self.wd, replace_segments=True)
            self._reset_roads_log("prepare")
            self._ensure_roads_dirs()
            convert_kwargs = _prepare.conversion_arguments(
                self, staged_path=staged_path, params=params, raster_paths=raster_paths,
                design_property_keys=design_property_keys, input_crs_value=input_crs_value,
            )
            try:
                summary = convert_geojson_file_to_monotonic_segments(**convert_kwargs)
            except ValueError as exc:
                if source_crs is not None or not self._is_projection_resolution_error(exc):
                    raise
                if dem_input_crs is None or dem_input_crs == input_crs_value:
                    raise
                self._append_roads_log(
                    "prepare",
                    "retry_with_dem_crs_input_crs",
                    {
                        "configured_input_crs": configured_input_crs,
                        "dem_input_crs": dem_input_crs,
                        "reason": safe_text(str(exc), source_profile=current_profile(WORKER)),
                    },
                )
                convert_kwargs["input_crs"] = dem_input_crs
                summary = convert_geojson_file_to_monotonic_segments(**convert_kwargs)
                input_crs_value = dem_input_crs
                input_crs_source = "dem_crs_fallback"
            params["input_crs"] = input_crs_value

            prepare_summary = _prepare.build_summary(
                self, summary=summary, params=params, attribute_field_map=attribute_field_map,
                design_property_keys=design_property_keys, warning_limit=warning_limit,
                raster_paths=raster_paths, input_crs_value=input_crs_value,
                configured_input_crs=configured_input_crs, source_crs=source_crs,
                input_crs_source=input_crs_source,
            )
            Path(self.roads_summary_path).write_text(
                json.dumps(prepare_summary, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            _prepare.log_summary(self, prepare_summary)

            with self.locked():
                self._roads_params = params
                self._last_prepare_summary = prepare_summary
                self._last_run_summary = None
                self._status = "prepared"
                self._errors = []
                self._timestamps["prepare_segments"] = int(time.time())

            return dict(prepare_summary)
        except Exception as exc:
            # broad-except: record failed preparation only after lifecycle invalidation.
            if not roads_lifecycle.invalidated(self.wd):
                raise
            self._record_error_and_raise(exc)


    @staticmethod
    def _safe_link_or_copy(src: str, dst: str) -> str:
        return _pass_routing._safe_link_or_copy(src, dst)

    @staticmethod
    def _segment_key(feature: Mapping[str, Any], *, fallback_index: Optional[int] = None) -> str:
        properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
        segment_id = properties.get("segment_id")
        if isinstance(segment_id, str):
            normalized = segment_id.strip()
            if normalized:
                return normalized
        if isinstance(fallback_index, int) and fallback_index >= 0:
            return f"roads-seg-missing-{fallback_index + 1:06d}"
        return "roads-seg-unknown"

    @staticmethod
    def _first_non_empty_property(properties: Mapping[str, Any], keys: Iterable[str]) -> Optional[str]:
        return _inputs._first_non_empty_property(properties, keys)


    @staticmethod
    def _has_non_empty_property(properties: Mapping[str, Any], keys: Iterable[str]) -> bool:
        return Roads._first_non_empty_property(properties, keys) is not None

    @classmethod
    def _missing_outslope_unrutted_required_fields(cls, properties: Mapping[str, Any]) -> List[str]:
        return _inputs._missing_outslope_unrutted_required_fields(cls, properties)

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        return _inputs._coerce_float(value)

    def _resolve_outslope_unrutted_required_profiles(
        self,
        *,
        properties: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, float]], List[str]]:
        return _inputs._resolve_outslope_unrutted_required_profiles(self, properties=properties)

    def _normalize_surface(self, value: Optional[str], default_value: str) -> str:
        return _inputs._normalize_surface(self, value, default_value)

    @staticmethod
    def _normalize_traffic_value(value: Optional[str]) -> Optional[str]:
        return _inputs._normalize_traffic_value(value)

    def _normalize_traffic(self, value: Optional[str], condition: Optional[str], default_value: str) -> str:
        return _inputs._normalize_traffic(self, value, condition, default_value)

    def _normalize_soil_texture(self, value: Optional[str], default_value: str) -> str:
        return _inputs._normalize_soil_texture(self, value, default_value)

    def _resolve_surface_for_feature(
        self,
        *,
        properties: Mapping[str, Any],
        default_value: str,
        attribute_field_map: Mapping[str, Optional[str]],
        warning_counts: Counter[str],
        warning_examples: List[Dict[str, Any]],
        warning_limit: int,
        segment_id: str,
    ) -> Tuple[str, str]:
        return _inputs._resolve_surface_for_feature(
            self,
            properties=properties,
            default_value=default_value,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )

    def _resolve_traffic_for_feature(
        self,
        *,
        properties: Mapping[str, Any],
        default_value: str,
        attribute_field_map: Mapping[str, Optional[str]],
        warning_counts: Counter[str],
        warning_examples: List[Dict[str, Any]],
        warning_limit: int,
        segment_id: str,
    ) -> Tuple[str, str]:
        return _inputs._resolve_traffic_for_feature(
            self,
            properties=properties,
            default_value=default_value,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )

    def _resolve_segment_run_inputs(
        self,
        *,
        properties: Mapping[str, Any],
        params: Mapping[str, Any],
        segment_id: str,
        design: str,
        warning_counts: Counter[str],
        warning_examples: List[Dict[str, Any]],
        warning_limit: int,
    ) -> Dict[str, Any]:
        return _inputs._resolve_segment_run_inputs(
            self,
            properties=properties,
            params=params,
            segment_id=segment_id,
            design=design,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
        )

    @staticmethod
    def _extract_segment_coordinates(feature: Mapping[str, Any]) -> List[List[float]]:
        return _spatial._extract_segment_coordinates(feature)

    @staticmethod
    def _line_length_m(coords: List[List[float]], transformer: Transformer, geod: Geod) -> float:
        return _spatial._line_length_m(coords, transformer, geod)


    @staticmethod
    def _iter_linestring_geometries(geometry_obj: Any) -> Iterable[LineString]:
        if geometry_obj is None:
            return
        if isinstance(geometry_obj, LineString):
            if not geometry_obj.is_empty:
                yield geometry_obj
            return
        if isinstance(geometry_obj, MultiLineString):
            for line in geometry_obj.geoms:
                if isinstance(line, LineString) and not line.is_empty:
                    yield line
            return
        if isinstance(geometry_obj, GeometryCollection):
            for part in geometry_obj.geoms:
                yield from Roads._iter_linestring_geometries(part)

    @staticmethod
    def _geometry_line_length_m_wgs84(geometry_obj: Any, *, geod: Geod) -> float:
        total = 0.0
        for line in Roads._iter_linestring_geometries(geometry_obj):
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            lons = [float(point[0]) for point in coords]
            lats = [float(point[1]) for point in coords]
            total += float(geod.line_length(lons, lats))
        return float(max(total, 0.0))

    @staticmethod
    def _resolve_topaz_id_from_properties(properties: Mapping[str, Any]) -> Optional[int]:
        for key in ("TopazID", "TOPAZID", "topaz_id", "topazId", "TOPAZ_ID"):
            try:
                raw_value = properties.get(key)
            except Exception:
                raw_value = None
            topaz_id = Roads._as_int_or_none(raw_value)
            if topaz_id is not None:
                return int(topaz_id)
        return None

    @staticmethod
    def _build_segment_hillslope_id(segment_id: str, topaz_id_hill: int) -> str:
        return f"{segment_id}::h{int(topaz_id_hill)}"

    def _load_hillslope_geometries_wgs84(self) -> List[Dict[str, Any]]:
        return _spatial._load_hillslope_geometries_wgs84(self)

    def _select_outslope_unrutted_hillslope_segments(
        self,
        *,
        pending_segments: Sequence[Dict[str, Any]],
        input_crs: CRS,
        geod: Geod,
        top2wepp: Mapping[int, Any],
    ) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
        return _spatial._select_outslope_unrutted_hillslope_segments(
            self,
            pending_segments=pending_segments,
            input_crs=input_crs,
            geod=geod,
            top2wepp=top2wepp,
        )

    @staticmethod
    def _sample_dem_elevation(
        dataset: rasterio.io.DatasetReader,
        transformer: Transformer,
        x: float,
        y: float,
    ) -> float:
        return _spatial._sample_dem_elevation(dataset, transformer, x, y)

    @staticmethod
    def _clamp_percent_slope(value: float) -> float:
        return _slope_inputs._clamp_percent_slope(value)

    @staticmethod
    def _clamp_fill_slope_pct(value: float) -> float:
        return _slope_inputs._clamp_fill_slope_pct(value)

    @staticmethod
    def _clamp_buffer_slope_pct(value: float) -> float:
        return _slope_inputs._clamp_buffer_slope_pct(value)

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
        return _spatial._build_segment_profile(
            self,
            feature=feature,
            input_crs=input_crs,
            dem_dataset=dem_dataset,
            input_to_wgs84=input_to_wgs84,
            input_to_dem=input_to_dem,
            geod=geod,
        )

    def _derive_buffer_profile_from_trace(self, trace_result: Mapping[str, Any]) -> Dict[str, float]:
        return _slope_inputs._derive_buffer_profile_from_trace(self, trace_result)

    def _derive_buffer_profile_from_feature_or_defaults(
        self,
        *,
        properties: Mapping[str, Any],
        road_profile: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return _slope_inputs._derive_buffer_profile_from_feature_or_defaults(
            self,
            properties=properties,
            road_profile=road_profile,
        )

    @staticmethod
    def _derive_fill_profile_from_inputs(*, fill_length_m: float, fill_slope_pct: float) -> Dict[str, float]:
        fill_length = max(0.3, min(100.0, float(fill_length_m)))
        slope_pct = Roads._clamp_fill_slope_pct(float(fill_slope_pct))
        return {
            "fill_length_m": float(fill_length),
            "fill_slope_pct": float(slope_pct),
            "fill_slope_fraction": float(slope_pct / 100.0),
        }


    @staticmethod
    def _apply_outslope_unrutted_geometry_parity(
        *,
        road_length_m: float,
        road_width_m: float,
        road_slope_pct: float,
    ) -> Dict[str, float]:
        return _slope_inputs._apply_outslope_unrutted_geometry_parity(
            road_length_m=road_length_m,
            road_width_m=road_width_m,
            road_slope_pct=road_slope_pct,
        )

    @staticmethod
    def _write_routed_two_ofe_slope_file(
        path: Path,
        *,
        width_m: float,
        road_length_m: float,
        road_slope_pct: float,
        buffer_length_m: float,
        buffer_slope_pct: float,
    ) -> None:
        return _slope_inputs._write_routed_two_ofe_slope_file(
            path,
            width_m=width_m,
            road_length_m=road_length_m,
            road_slope_pct=road_slope_pct,
            buffer_length_m=buffer_length_m,
            buffer_slope_pct=buffer_slope_pct,
        )

    @staticmethod
    def _write_routed_three_ofe_slope_file(
        path: Path,
        *,
        width_m: float,
        road_length_m: float,
        road_slope_pct: float,
        fill_length_m: float,
        fill_slope_pct: float,
        buffer_length_m: float,
        buffer_slope_pct: float,
    ) -> None:
        return _slope_inputs._write_routed_three_ofe_slope_file(
            path,
            width_m=width_m,
            road_length_m=road_length_m,
            road_slope_pct=road_slope_pct,
            fill_length_m=fill_length_m,
            fill_slope_pct=fill_slope_pct,
            buffer_length_m=buffer_length_m,
            buffer_slope_pct=buffer_slope_pct,
        )

    @staticmethod
    def _write_routed_three_ofe_landuse_road_fill_slope_file(
        path: Path,
        *,
        width_m: float,
        top_landuse_length_m: float,
        top_landuse_slope_pct: float,
        road_length_m: float,
        road_slope_pct: float,
        fill_length_m: float,
        fill_slope_pct: float,
    ) -> None:
        return _slope_inputs._write_routed_three_ofe_landuse_road_fill_slope_file(
            path,
            width_m=width_m,
            top_landuse_length_m=top_landuse_length_m,
            top_landuse_slope_pct=top_landuse_slope_pct,
            road_length_m=road_length_m,
            road_slope_pct=road_slope_pct,
            fill_length_m=fill_length_m,
            fill_slope_pct=fill_slope_pct,
        )

    @staticmethod
    def _write_routed_four_ofe_landuse_road_fill_hill_slope_file(
        path: Path,
        *,
        width_m: float,
        top_landuse_length_m: float,
        top_landuse_slope_pct: float,
        road_length_m: float,
        road_slope_pct: float,
        fill_length_m: float,
        fill_slope_pct: float,
        bottom_landuse_length_m: float,
        bottom_landuse_slope_pct: float,
    ) -> None:
        return _slope_inputs._write_routed_four_ofe_landuse_road_fill_hill_slope_file(
            path,
            width_m=width_m,
            top_landuse_length_m=top_landuse_length_m,
            top_landuse_slope_pct=top_landuse_slope_pct,
            road_length_m=road_length_m,
            road_slope_pct=road_slope_pct,
            fill_length_m=fill_length_m,
            fill_slope_pct=fill_slope_pct,
            bottom_landuse_length_m=bottom_landuse_length_m,
            bottom_landuse_slope_pct=bottom_landuse_slope_pct,
        )

    @staticmethod
    def _extract_ofe_from_nycrop_comment(line: str) -> Optional[int]:
        return _management_inputs._extract_ofe_from_nycrop_comment(line)

    @staticmethod
    def _sample_discha_median_from_wgs84_geometry(
        geometry_wgs84: Any,
        *,
        discha_dataset: rasterio.io.DatasetReader,
        wgs84_to_discha: Transformer,
    ) -> Optional[float]:
        values: List[float] = []
        nodata_value = discha_dataset.nodata
        for line in Roads._iter_linestring_geometries(geometry_wgs84):
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            for x, y in coords:
                dx, dy = wgs84_to_discha.transform(float(x), float(y))
                sample = next(discha_dataset.sample([(dx, dy)]))
                value = float(sample[0])
                if not np.isfinite(value):
                    continue
                if nodata_value is not None and abs(value - float(nodata_value)) < 1e-12:
                    continue
                if value <= 0.0:
                    continue
                values.append(value)
        if not values:
            return None
        return float(np.median(np.asarray(values, dtype=np.float64)))

    def _build_routed_mofe_management_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        ofe_order: Sequence[int],
    ) -> None:
        return _management_inputs._build_routed_mofe_management_file(
            self,
            template_path=template_path,
            output_path=output_path,
            ofe_order=ofe_order,
        )

    def _build_routed_mofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
        ofe_order: Sequence[int],
    ) -> None:
        return _soil_inputs._build_routed_mofe_soil_file(
            self,
            template_path=template_path,
            output_path=output_path,
            traffic=traffic,
            surface=surface,
            rfg_pct=rfg_pct,
            ofe_order=ofe_order,
        )

    
    
    
    @staticmethod
    def _replace_soil_marker(
        horizon_line: str,
        *,
        urr_ref: float,
        ufr_ref: float,
        ubr_value: float,
    ) -> str:
        return _soil_inputs._replace_soil_marker(
            horizon_line,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=ubr_value,
        )

    def _build_routed_two_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        return _soil_inputs._build_routed_two_ofe_soil_file(
            self,
            template_path=template_path,
            output_path=output_path,
            traffic=traffic,
            surface=surface,
            rfg_pct=rfg_pct,
        )

    def _build_routed_three_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        return _soil_inputs._build_routed_three_ofe_soil_file(
            self,
            template_path=template_path,
            output_path=output_path,
            traffic=traffic,
            surface=surface,
            rfg_pct=rfg_pct,
        )

    @staticmethod
    def _strip_management_scenario_block(
        lines: List[str], *, start_marker: str, end_marker: str
    ) -> List[str]:
        return _management_inputs._strip_management_scenario_block(
            lines,
            start_marker=start_marker,
            end_marker=end_marker,
        )

    def _build_routed_two_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
        return _management_inputs._build_routed_two_ofe_management_file(
            self,
            template_path=template_path,
            output_path=output_path,
        )

    def _materialize_routed_two_ofe_management_template(self, *, traffic: str) -> Path:
        return _management_inputs._materialize_routed_two_ofe_management_template(self, traffic=traffic)

    def _materialize_routed_three_ofe_management_template(self, *, traffic: str) -> Path:
        return _management_inputs._materialize_routed_three_ofe_management_template(
            self,
            traffic=traffic,
        )

    def _resolve_trace_receiving_hillslope_topaz(
        self,
        *,
        trace_result: Mapping[str, Any],
        topaz_values: np.ndarray,
    ) -> Optional[int]:
        rows = trace_result.get("rows")
        cols = trace_result.get("cols")
        if not isinstance(rows, list) or not isinstance(cols, list):
            return None
        if len(rows) != len(cols) or len(rows) < 2:
            return None

        channel_row = self._as_int_or_none(trace_result.get("channel_row"))
        channel_col = self._as_int_or_none(trace_result.get("channel_col"))
        channel_index = len(rows) - 1
        if channel_row is not None and channel_col is not None:
            for idx in range(len(rows) - 1, -1, -1):
                row_i = self._as_int_or_none(rows[idx])
                col_i = self._as_int_or_none(cols[idx])
                if row_i == channel_row and col_i == channel_col:
                    channel_index = idx
                    break
        if channel_index <= 0:
            return None

        row_i = self._as_int_or_none(rows[channel_index - 1])
        col_i = self._as_int_or_none(cols[channel_index - 1])
        if row_i is None or col_i is None:
            return None
        if row_i < 0 or col_i < 0 or row_i >= topaz_values.shape[0] or col_i >= topaz_values.shape[1]:
            return None

        topaz_value = float(topaz_values[row_i, col_i])
        if not np.isfinite(topaz_value):
            return None
        topaz_id = int(round(topaz_value))
        if not _is_hillslope_topaz_id(topaz_id):
            return None
        return topaz_id

    @staticmethod
    def _write_single_ofe_slope_file(path: Path, *, width_m: float, length_m: float, slope_pct: float) -> None:
        return _slope_inputs._write_single_ofe_slope_file(
            path,
            width_m=width_m,
            length_m=length_m,
            slope_pct=slope_pct,
        )

    def _saved_parameterization_state(self):
        # A persisted null is malformed, distinct from an absent legacy key.
        return _parameterization_support._saved_parameterization_state(self)

    def _parameterization_template_path(self, directory: str, name: str) -> Path:
        return _parameterization_support._parameterization_template_path(self, directory, name)

    def _apply_parameterization_to_soil(self, path, template_path, traffic, ofe_order):
        return _parameterization_support._apply_parameterization_to_soil(
            self,
            path,
            template_path,
            traffic,
            ofe_order,
        )

    def _record_parameterization_inputs(self, soil_path, slope_path, management_path):
        return _parameterization_support._record_parameterization_inputs(
            self,
            soil_path,
            slope_path,
            management_path,
        )

    def _attach_parameterization_records(self, records):
        return _parameterization_support._attach_parameterization_records(self, records)

    @staticmethod
    def _parameterization_group(state, design, surface, traffic, texture, routing,
                                segment_ids, index, source_kind):
        return _queries._parameterization_group(
            state,
            design,
            surface,
            traffic,
            texture,
            routing,
            segment_ids,
            index,
            source_kind,
        )

    @classmethod
    def initial_parameterization_preview(cls):
        """Return a default preview for enabled first use without creating Roads."""
        return _queries.initial_parameterization_preview(cls)

    def _parameterization_groups(self, state, params):
        """Resolve displayed groups through the same feature/default selector as Run."""
        return _queries._parameterization_groups(self, state, params)

    def _last_parameterization_readback(self, diagnostics):
        return _queries._last_parameterization_readback(self, diagnostics)

    def query_parameterization(self):
        """Inspect saved authority without enrolling or repairing legacy state."""
        return _queries.query_parameterization(self)

    def _resolve_legacy_soil_template_path(self, *, design: str, surface: str, soil_texture: str) -> Path:
        return _parameterization_support._resolve_legacy_soil_template_path(
            self,
            design=design,
            surface=surface,
            soil_texture=soil_texture,
        )

    def _resolve_legacy_management_template_path(self, *, traffic: str) -> Path:
        return _parameterization_support._resolve_legacy_management_template_path(self, traffic=traffic)

    @staticmethod
    def _replace_leading_int(line: str, replacement: int) -> str:
        return _management_inputs._replace_leading_int(line, replacement)

    def _build_single_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
        return _management_inputs._build_single_ofe_management_file(
            self,
            template_path=template_path,
            output_path=output_path,
        )

    def _build_single_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        return _soil_inputs._build_single_ofe_soil_file(
            self,
            template_path=template_path,
            output_path=output_path,
            traffic=traffic,
            surface=surface,
            rfg_pct=rfg_pct,
        )

    def _materialize_single_ofe_management_template(self, *, traffic: str) -> Path:
        return _management_inputs._materialize_single_ofe_management_template(self, traffic=traffic)

    @staticmethod
    def _read_pass_header_climate_line(pass_path: Path) -> str:
        return _pass_routing._read_pass_header_climate_line(pass_path)

    @staticmethod
    def _rewrite_pass_header_climate_line(pass_path: Path, climate_line: str) -> None:
        return _pass_routing._rewrite_pass_header_climate_line(pass_path, climate_line)

    @staticmethod
    def _resolve_pass_header_climate_path(pass_path: Path, climate_token: str) -> Optional[Path]:
        return _pass_routing._resolve_pass_header_climate_path(pass_path, climate_token)

    def _normalize_road_pass_header_climate_tokens(
        self,
        *,
        base_pass_path: Path,
        road_pass_paths: Iterable[Path],
    ) -> None:
        return _pass_routing._normalize_road_pass_header_climate_tokens(
            self,
            base_pass_path=base_pass_path,
            road_pass_paths=road_pass_paths,
        )

    def _combine_target_hillslope_pass(
        self,
        *,
        base_pass_path: str,
        road_pass_paths: Iterable[str],
        output_pass_path: str,
        strategy: str = "phase1",
    ) -> None:
        return _pass_routing._combine_target_hillslope_pass(
            self,
            base_pass_path=base_pass_path,
            road_pass_paths=road_pass_paths,
            output_pass_path=output_pass_path,
            strategy=strategy,
        )

    def _prepare_roads_runs_workspace(self) -> None:
        return _pass_routing._prepare_roads_runs_workspace(self)

    def _prepare_roads_output_workspace(self) -> None:
        return _pass_routing._prepare_roads_output_workspace(self)

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
        return _native_runner._run_segment_hillslope(
            self,
            segment_run_id=segment_run_id,
            climate_wepp_id=climate_wepp_id,
            sim_years=sim_years,
            wepp_bin=wepp_bin,
            single_ofe_management_path=single_ofe_management_path,
            single_ofe_soil_path=single_ofe_soil_path,
            single_ofe_slope_path=single_ofe_slope_path,
            make_hillslope_run=make_hillslope_run,
            run_hillslope=run_hillslope,
        )

    def _build_roads_segment_loss_summary_parquet(self, *, interchange_dir: Path) -> str:
        return _reporting._build_roads_segment_loss_summary_parquet(
            self,
            interchange_dir=interchange_dir,
        )

    def _required_roads_report_resource_relpaths(
        self,
        *,
        is_single_storm: bool,
        include_chnwb: bool,
        include_segment_loss_summary: bool,
    ) -> List[str]:
        return _reporting._required_roads_report_resource_relpaths(
            self,
            is_single_storm=is_single_storm,
            include_chnwb=include_chnwb,
            include_segment_loss_summary=include_segment_loss_summary,
        )

    def _regenerate_roads_report_resources(self) -> Dict[str, Any]:
        return _reporting._regenerate_roads_report_resources(self)

    def _prepare_modeled_area_accounting(self, canonical_ids, records):
        return _reporting._prepare_modeled_area_accounting(self, canonical_ids, records)

    @roads_lifecycle.mutation
    def run_roads_wepp(self) -> Dict[str, Any]:
        failed_run_summary: Optional[Dict[str, Any]] = None
        run_summary_base: Optional[Dict[str, Any]] = None
        current_stage = "startup"
        placement_marker = {}
        try:
            if not self.enabled:
                raise ValueError("Roads must be enabled before run_roads_wepp.")

            self._require_prepare_state_current()
            current_stage = "load_prepared_segments"
            features = self._load_segment_features()
            field_map = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))["attribute_field_map"]
            if any(self._resolve_design_for_feature(properties=f.get("properties", {}),
                    attribute_field_map=field_map)[0] == "outslope_unrutted" for f in features):
                placement_marker = {"unrutted_placement_policy": _unrutted.PLACEMENT_POLICY}
            translator = self.watershed_instance.translator_factory()
            top2wepp = dict(getattr(translator, "top2wepp", {}))
            self._append_roads_log(
                "run",
                "translator_loaded",
                {"top2wepp_count": len(top2wepp)},
            )

            roads_lifecycle.retain(self.wd)
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

            self._parameterization_runtime_templates = roads_parameterization.materialize_baseline(
                self._parameterization, Path(self.roads_runs_dir)
            )
            self._parameterization_runtime_readbacks = {}

            params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
            attribute_field_map = self._normalize_attribute_field_map(
                params.get("attribute_field_map"),
                known_fields=None,
            )
            warning_limit = DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT
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
            mapping_warning_counts: Counter[str] = Counter()
            mapping_warning_examples: List[Dict[str, Any]] = []
            design_execution_counts: Counter[str] = Counter()
            fill_default_usage_counts: Counter[str] = Counter()
            replacement_pass_paths_by_wepp: Dict[int, List[str]] = defaultdict(list)
            outslope_unrutted_pending_segments: List[Dict[str, Any]] = []
            outslope_unrutted_candidate_status: Dict[str, Dict[str, Any]] = {}
            outslope_unrutted_diagnostics: Dict[str, Any] = {
                "outslope_unrutted_targeted_hillslope_count": 0,
                "outslope_unrutted_included_segment_count": 0,
                "outslope_unrutted_excluded_segment_count": 0,
                "outslope_unrutted_capped_segment_count": 0,
                "outslope_unrutted_hillslope_records": [],
            }

            current_stage = "segment_runs"
            with rasterio.open(dem_path) as dem_dataset:
                if dem_dataset.crs is None:
                    raise ValueError(f"Roads DEM is missing CRS metadata: {dem_path}")
                input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
                input_to_dem = Transformer.from_crs(input_crs, dem_dataset.crs, always_xy=True)
                routed_management_cache_by_traffic: Dict[str, Path] = {}
                routed_three_ofe_management_cache_by_traffic: Dict[str, Path] = {}
                routing_mode_counts: Counter[str] = Counter()
                trace_invocation_count = 0
                trace_reaches_channel_count = 0
                trace_termination_reason_counts: Counter[str] = Counter()
                trace_context: Optional[Dict[str, Any]] = None
                trace_fn = None

                for feature_index, feature in enumerate(features):
                    properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
                    segment_id = self._segment_key(feature, fallback_index=feature_index)
                    design, design_source = self._resolve_design_for_feature(
                        properties=properties,
                        attribute_field_map=attribute_field_map,
                        warning_counts=mapping_warning_counts,
                        warning_examples=mapping_warning_examples,
                        warning_limit=warning_limit,
                        segment_id=segment_id,
                    )

                    if design is None:
                        skipped_segments.append({"segment_id": segment_id, "reason": "design_not_eligible"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "design_not_eligible"},
                        )
                        continue

                    eligible_segment_count += 1
                    if design == "outslope_unrutted":
                        outslope_unrutted_pending_segments.append(
                            {
                                "segment_id": segment_id,
                                "feature": feature,
                                "properties": properties,
                                "design_source": design_source,
                            }
                        )
                        continue

                    routing_eligibility = str(properties.get("_roads_routing_eligibility") or "unknown")
                    channel_hill_topaz = self._as_int_or_none(properties.get("topaz_id_hill_lowpoint"))
                    channel_chn_topaz = self._as_int_or_none(properties.get("topaz_id_chn_lowpoint"))
                    non_channel_routable = self._is_truthy_property(
                        properties.get("_roads_non_channel_routable")
                    ) or routing_eligibility == "non_channel_routable"

                    routing_mode = "channel_associated" if (
                        channel_hill_topaz is not None and channel_chn_topaz is not None
                    ) else "non_channel_routed"
                    if routing_mode == "non_channel_routed" and not non_channel_routable:
                        skipped_segments.append({"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"})
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {"segment_id": segment_id, "reason": "missing_topaz_lowpoint_ids"},
                        )
                        continue

                    trace_result: Optional[Dict[str, Any]] = None
                    trace_summary: Dict[str, Any] = {}
                    hill_topaz_int: Optional[int] = None
                    chn_topaz_int: Optional[int] = None
                    if routing_mode == "channel_associated":
                        hill_topaz_int = channel_hill_topaz
                        chn_topaz_int = channel_chn_topaz
                        if hill_topaz_int is None or chn_topaz_int is None:
                            skipped_segments.append(
                                {"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"}
                            )
                            self._append_roads_log(
                                "run",
                                "segment_skipped",
                                {"segment_id": segment_id, "reason": "invalid_topaz_lowpoint_ids"},
                            )
                            continue
                    else:
                        seed_row = self._as_int_or_none(properties.get("_roads_lowpoint_row"))
                        seed_col = self._as_int_or_none(properties.get("_roads_lowpoint_col"))
                        if seed_row is None or seed_col is None:
                            skipped_segments.append({"segment_id": segment_id, "reason": "trace_seed_cell_missing"})
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "skipped",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_seed_cell_missing",
                                }
                            )
                            self._append_roads_log(
                                "run",
                                "segment_skipped",
                                {
                                    "segment_id": segment_id,
                                    "routing_mode": routing_mode,
                                    "reason": "trace_seed_cell_missing",
                                },
                            )
                            continue

                        if trace_context is None:
                            trace_paths = self._resolve_trace_raster_paths()
                            with rasterio.open(trace_paths["topaz_id_raster_path"]) as topaz_dataset:
                                topaz_arr = topaz_dataset.read(1, masked=True)
                                topaz_values = np.asarray(topaz_arr.filled(np.nan), dtype=float)
                                if np.ma.isMaskedArray(topaz_arr):
                                    topaz_values[np.ma.getmaskarray(topaz_arr)] = np.nan
                                nodata = topaz_dataset.nodata
                                if nodata is not None and np.isfinite(nodata):
                                    topaz_values[np.isclose(topaz_values, nodata, rtol=0.0, atol=1e-8)] = np.nan
                            from wepppyo3.roads_flowpath import trace_downslope_flowpath

                            trace_context = {"paths": trace_paths, "topaz_values": topaz_values}
                            trace_fn = trace_downslope_flowpath
                            self._append_roads_log(
                                "run",
                                "trace_context_initialized",
                                {
                                    "trace_relief_path": self._path_for_summary(trace_paths["dem_path"]),
                                    "trace_flovec_path": self._path_for_summary(trace_paths["flovec_path"]),
                                    "trace_subwta_path": self._path_for_summary(trace_paths["topaz_id_raster_path"]),
                                    "trace_channel_path": self._path_for_summary(trace_paths["channel_raster_path"]),
                                },
                            )

                        assert trace_context is not None and trace_fn is not None
                        trace_max_steps = int(params.get("trace_max_steps", 20000))
                        trace_invocation_count += 1
                        try:
                            trace_result = trace_fn(
                                trace_context["paths"]["topaz_id_raster_path"],
                                trace_context["paths"]["flovec_path"],
                                trace_context["paths"]["dem_path"],
                                seed_row,
                                seed_col,
                                channel_path=trace_context["paths"]["channel_raster_path"],
                                max_steps=trace_max_steps,
                                wbt=True,
                            )
                        except Exception as exc:
                            skipped_segments.append({"segment_id": segment_id, "reason": "trace_execution_failed"})
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "failed",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_execution_failed",
                                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                }
                            )
                            failed_segment_records.append(
                                {
                                    "segment_id": segment_id,
                                    "reason": "trace_execution_failed",
                                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                }
                            )
                            self._append_roads_log(
                                "run",
                                "segment_trace_failed",
                                {
                                    "segment_id": segment_id,
                                    "routing_mode": routing_mode,
                                    "seed_row": seed_row,
                                    "seed_col": seed_col,
                                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                },
                            )
                            continue

                        termination_reason = str(trace_result.get("termination_reason") or "unknown")
                        trace_termination_reason_counts[termination_reason] += 1
                        reaches_channel = bool(trace_result.get("reaches_channel"))
                        if reaches_channel:
                            trace_reaches_channel_count += 1
                        trace_summary = {
                            "trace_seed_row": seed_row,
                            "trace_seed_col": seed_col,
                            "trace_reaches_channel": reaches_channel,
                            "trace_termination_reason": termination_reason,
                            "trace_path_length_m": self._as_float_or_none(trace_result.get("path_length_m")),
                            "trace_mean_slope": self._as_float_or_none(trace_result.get("mean_slope")),
                            "trace_drop_m": self._as_float_or_none(trace_result.get("drop_m")),
                            "trace_profile_point_count": (
                                len(trace_result.get("rows"))
                                if isinstance(trace_result.get("rows"), list)
                                else 0
                            ),
                            "trace_segment_slope_count": (
                                len(trace_result.get("segment_slope"))
                                if isinstance(trace_result.get("segment_slope"), list)
                                else 0
                            ),
                        }
                        if not reaches_channel:
                            skipped_segments.append({"segment_id": segment_id, "reason": "trace_did_not_reach_channel"})
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "skipped",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_did_not_reach_channel",
                                    **trace_summary,
                                }
                            )
                            self._append_roads_log(
                                "run",
                                "segment_skipped",
                                {
                                    "segment_id": segment_id,
                                    "routing_mode": routing_mode,
                                    "reason": "trace_did_not_reach_channel",
                                    "trace_termination_reason": termination_reason,
                                },
                            )
                            continue

                        chn_topaz_int = self._as_int_or_none(trace_result.get("channel_topaz_id"))
                        if chn_topaz_int is None:
                            skipped_segments.append({"segment_id": segment_id, "reason": "trace_channel_topaz_missing"})
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "skipped",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_channel_topaz_missing",
                                    **trace_summary,
                                }
                            )
                            self._append_roads_log(
                                "run",
                                "segment_skipped",
                                {
                                    "segment_id": segment_id,
                                    "routing_mode": routing_mode,
                                    "reason": "trace_channel_topaz_missing",
                                },
                            )
                            continue

                        hill_topaz_int = self._resolve_trace_receiving_hillslope_topaz(
                            trace_result=trace_result,
                            topaz_values=trace_context["topaz_values"],
                        )
                        if hill_topaz_int is None:
                            skipped_segments.append(
                                {"segment_id": segment_id, "reason": "trace_receiving_hillslope_missing"}
                            )
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "skipped",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_receiving_hillslope_missing",
                                    **trace_summary,
                                }
                            )
                            self._append_roads_log(
                                "run",
                                "segment_skipped",
                                {
                                    "segment_id": segment_id,
                                    "routing_mode": routing_mode,
                                    "reason": "trace_receiving_hillslope_missing",
                                    "channel_topaz_id": chn_topaz_int,
                                },
                            )
                            continue

                    wepp_id = top2wepp.get(int(hill_topaz_int))
                    if wepp_id is None:
                        skipped_segments.append(
                            {"segment_id": segment_id, "reason": "translator_missing_hillslope_map"}
                        )
                        segment_execution_records.append(
                            {
                                "segment_id": segment_id,
                                "status": "skipped",
                                "routing_mode": routing_mode,
                                "reason": "translator_missing_hillslope_map",
                                "topaz_id_hill_lowpoint": int(hill_topaz_int),
                                **trace_summary,
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {
                                "segment_id": segment_id,
                                "routing_mode": routing_mode,
                                "reason": "translator_missing_hillslope_map",
                                "topaz_id_hill_lowpoint": int(hill_topaz_int),
                            },
                        )
                        continue

                    mapped_segment_count += 1
                    routing_mode_counts[routing_mode] += 1
                    wepp_id_int = int(wepp_id)

                    segment_inputs = self._resolve_segment_run_inputs(
                        properties=properties,
                        params=params,
                        segment_id=segment_id,
                        design=design,
                        warning_counts=mapping_warning_counts,
                        warning_examples=mapping_warning_examples,
                        warning_limit=warning_limit,
                    )
                    segment_inputs["resolution_sources"]["design"] = (
                        "mapped_primary" if design_source == attribute_field_map.get("design") else "segment_property"
                    )

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
                                "routing_mode": routing_mode,
                                "reason": "segment_profile_unavailable",
                                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                **trace_summary,
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_skipped",
                            {
                                "segment_id": segment_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "routing_mode": routing_mode,
                                "reason": "segment_profile_unavailable",
                                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
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
                    segment_soil_suffix = "single_ofe"
                    management_path: Path
                    segment_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.single_ofe.sol"
                    segment_slope_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.slp"
                    routed_buffer_profile: Dict[str, Any] = {}
                    fill_profile: Dict[str, float] = {}
                    is_outslope_rutted = segment_inputs["design"] == "outslope_rutted"

                    if is_outslope_rutted:
                        if segment_inputs["resolution_sources"].get("fill_length_m") == "roads_default":
                            fill_default_usage_counts["fill_length_m"] += 1
                        if segment_inputs["resolution_sources"].get("fill_slope_pct") == "roads_default":
                            fill_default_usage_counts["fill_slope_pct"] += 1

                        fill_profile = self._derive_fill_profile_from_inputs(
                            fill_length_m=segment_inputs["fill_length_m"],
                            fill_slope_pct=segment_inputs["fill_slope_pct"],
                        )
                        segment_soil_suffix = "routed_three_ofe"
                        segment_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.routed_three_ofe.sol"
                        management_path = routed_three_ofe_management_cache_by_traffic.get(segment_inputs["traffic"])
                        if management_path is None:
                            management_path = self._materialize_routed_three_ofe_management_template(
                                traffic=segment_inputs["traffic"]
                            )
                            routed_three_ofe_management_cache_by_traffic[segment_inputs["traffic"]] = management_path
                        self._build_routed_three_ofe_soil_file(
                            template_path=soil_template_path,
                            output_path=segment_soil_path,
                            traffic=segment_inputs["traffic"],
                            surface=segment_inputs["surface"],
                            rfg_pct=segment_inputs["rfg_pct"],
                        )

                        if routing_mode == "channel_associated":
                            routed_buffer_profile = self._derive_buffer_profile_from_feature_or_defaults(
                                properties=properties,
                                road_profile=profile,
                            )
                        else:
                            assert trace_result is not None
                            routed_buffer_profile = self._derive_buffer_profile_from_trace(trace_result)

                        self._write_routed_three_ofe_slope_file(
                            segment_slope_path,
                            width_m=segment_inputs["road_width_m"],
                            road_length_m=profile["segment_length_m"],
                            road_slope_pct=profile["slope_pct"],
                            fill_length_m=fill_profile["fill_length_m"],
                            fill_slope_pct=fill_profile["fill_slope_pct"],
                            buffer_length_m=routed_buffer_profile["buffer_length_m"],
                            buffer_slope_pct=routed_buffer_profile["buffer_slope_pct"],
                        )
                    elif routing_mode == "channel_associated":
                        management_path = management_cache_by_traffic.get(segment_inputs["traffic"])
                        if management_path is None:
                            management_path = self._materialize_single_ofe_management_template(
                                traffic=segment_inputs["traffic"]
                            )
                            management_cache_by_traffic[segment_inputs["traffic"]] = management_path
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
                    else:
                        assert trace_result is not None
                        segment_soil_suffix = "routed_two_ofe"
                        segment_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.routed_two_ofe.sol"
                        management_path = routed_management_cache_by_traffic.get(segment_inputs["traffic"])
                        if management_path is None:
                            management_path = self._materialize_routed_two_ofe_management_template(
                                traffic=segment_inputs["traffic"]
                            )
                            routed_management_cache_by_traffic[segment_inputs["traffic"]] = management_path
                        self._build_routed_two_ofe_soil_file(
                            template_path=soil_template_path,
                            output_path=segment_soil_path,
                            traffic=segment_inputs["traffic"],
                            surface=segment_inputs["surface"],
                            rfg_pct=segment_inputs["rfg_pct"],
                        )
                        routed_buffer_profile = self._derive_buffer_profile_from_trace(trace_result)
                        self._write_routed_two_ofe_slope_file(
                            segment_slope_path,
                            width_m=segment_inputs["road_width_m"],
                            road_length_m=profile["segment_length_m"],
                            road_slope_pct=profile["slope_pct"],
                            buffer_length_m=routed_buffer_profile["buffer_length_m"],
                            buffer_slope_pct=routed_buffer_profile["buffer_slope_pct"],
                        )

                    self._append_roads_log(
                        "run",
                        "segment_inputs_ready",
                        {
                            "segment_id": segment_id,
                            "segment_run_id": segment_run_id,
                            "routing_mode": routing_mode,
                            "routing_eligibility": routing_eligibility,
                            "target_hillslope_wepp_id": wepp_id_int,
                            "topaz_id_chn_lowpoint": int(chn_topaz_int),
                            "topaz_id_hill_lowpoint": int(hill_topaz_int),
                            "design": segment_inputs["design"],
                            "surface": segment_inputs["surface"],
                            "traffic": segment_inputs["traffic"],
                            "soil_texture": segment_inputs["soil_texture"],
                            "rfg_pct": segment_inputs["rfg_pct"],
                            "soil_file_variant": segment_soil_suffix,
                            "road_width_m": segment_inputs["road_width_m"],
                            "fill_length_m": fill_profile.get("fill_length_m", segment_inputs.get("fill_length_m")),
                            "fill_slope_pct": fill_profile.get("fill_slope_pct", segment_inputs.get("fill_slope_pct")),
                            "segment_length_m": profile["segment_length_m"],
                            **fill_profile,
                            "slope_pct_raw": profile["raw_slope_pct"],
                            "slope_pct_clamped": profile["slope_pct"],
                            "high_point": profile["high_point"],
                            "low_point": profile["low_point"],
                            **trace_summary,
                            **routed_buffer_profile,
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
                                "routing_mode": routing_mode,
                                "reason": "segment_run_failed",
                                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                **trace_summary,
                            }
                        )
                        failed_segment_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "routing_mode": routing_mode,
                                "reason": "segment_run_failed",
                                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                            }
                        )
                        self._append_roads_log(
                            "run",
                            "segment_run_failed",
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "routing_mode": routing_mode,
                                "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
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
                                "routing_mode": routing_mode,
                                "reason": "segment_pass_missing",
                                **trace_summary,
                            }
                        )
                        failed_segment_records.append(
                            {
                                "segment_id": segment_id,
                                "segment_run_id": segment_run_id,
                                "target_hillslope_wepp_id": wepp_id_int,
                                "routing_mode": routing_mode,
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
                                "routing_mode": routing_mode,
                                "reason": "segment_pass_missing",
                            },
                        )
                        continue

                    successful_segment_count += 1
                    design_execution_counts[segment_inputs["design"]] += 1
                    segment_pass_paths_by_wepp[wepp_id_int].append(str(segment_pass_path))
                    execution_record = {
                        "segment_id": segment_id,
                        "segment_run_id": segment_run_id,
                        "target_hillslope_wepp_id": wepp_id_int,
                        "status": "completed",
                        "routing_mode": routing_mode,
                        "routing_eligibility": routing_eligibility,
                        "topaz_id_chn_lowpoint": int(chn_topaz_int),
                        "topaz_id_hill_lowpoint": int(hill_topaz_int),
                        "design": segment_inputs["design"],
                        "surface": segment_inputs["surface"],
                        "traffic": segment_inputs["traffic"],
                        "soil_texture": segment_inputs["soil_texture"],
                        "rfg_pct": segment_inputs["rfg_pct"],
                        "road_width_m": segment_inputs["road_width_m"],
                        "fill_length_m": fill_profile.get("fill_length_m", segment_inputs.get("fill_length_m")),
                        "fill_slope_pct": fill_profile.get("fill_slope_pct", segment_inputs.get("fill_slope_pct")),
                        "segment_length_m": profile["segment_length_m"],
                        "slope_pct_raw": profile["raw_slope_pct"],
                        "slope_pct_clamped": profile["slope_pct"],
                        "elevation_high_m": profile["elevation_high_m"],
                        "elevation_low_m": profile["elevation_low_m"],
                        "segment_pass_relpath": os.path.relpath(segment_pass_path, self.wd),
                        **fill_profile,
                        **trace_summary,
                        **routed_buffer_profile,
                    }
                    segment_execution_records.append(execution_record)
                    self._append_roads_log("run", "segment_run_completed", execution_record)

                if outslope_unrutted_pending_segments:
                    selected_outslope_by_wepp, outslope_unrutted_diagnostics, outslope_unrutted_candidate_status = (
                        self._select_outslope_unrutted_hillslope_segments(
                            pending_segments=outslope_unrutted_pending_segments,
                            input_crs=input_crs,
                            geod=geod,
                            top2wepp=top2wepp,
                        )
                    )

                    hillslope_records_by_topaz = {
                        int(record["topaz_id_hill"]): record
                        for record in outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", [])
                        if isinstance(record, Mapping)
                    }

                    def _move_outslope_candidate_to_status(candidate: Mapping[str, Any], status: str) -> None:
                        segment_hillslope_id = str(candidate["segment_hillslope_id"])
                        topaz_id_hill = int(candidate["topaz_id_hill"])
                        candidate_row = outslope_unrutted_candidate_status.get(segment_hillslope_id)
                        if candidate_row is not None:
                            candidate_row["status"] = status
                        record = hillslope_records_by_topaz.get(topaz_id_hill)
                        if record is None:
                            return
                        included_ids = record.get("segment_ids_included") or []
                        excluded_ids = record.get("segment_ids_excluded") or []
                        try:
                            while segment_hillslope_id in included_ids:
                                included_ids.remove(segment_hillslope_id)
                        except Exception:
                            pass
                        if segment_hillslope_id not in excluded_ids:
                            excluded_ids.append(segment_hillslope_id)

                    selected_outslope_candidate_count = int(sum(1 for rows in selected_outslope_by_wepp.values() if rows))
                    discha_path = self._normalize_existing_path(getattr(self.watershed_instance, "discha", None))
                    if discha_path is None:
                        if selected_outslope_candidate_count > 0:
                            raise FileNotFoundError(
                                "Roads outslope_unrutted replacement requires watershed distance-to-channel raster (watershed.discha)."
                            )
                        discha_path = str(dem_path)

                    routed_mofe_management_cache_by_traffic_and_order: Dict[Tuple[str, Tuple[int, ...]], Path] = {}

                    with rasterio.open(discha_path) as discha_dataset:
                        if discha_dataset.crs is None:
                            raise ValueError(
                                "Roads outslope_unrutted replacement requires watershed.discha to declare a CRS."
                            )
                        wgs84_to_discha = Transformer.from_crs(
                            CRS.from_epsg(4326),
                            CRS.from_user_input(discha_dataset.crs),
                            always_xy=True,
                        )

                        for wepp_id_int in sorted(selected_outslope_by_wepp):
                            candidates = sorted(
                                selected_outslope_by_wepp[wepp_id_int],
                                key=lambda row: str(row["segment_hillslope_id"]),
                            )
                            if not candidates:
                                continue

                            topaz_id_hill = int(candidates[0]["topaz_id_hill"])
                            hillslope_record = hillslope_records_by_topaz.get(topaz_id_hill)

                            try:
                                hillslope_length_m = float(self.watershed_instance.hillslope_length(topaz_id_hill))
                                hillslope_width_m = float(self.watershed_instance.hillslope_width(topaz_id_hill))
                            except Exception as exc:
                                hillslope_length_m = 0.0
                                hillslope_width_m = 0.0
                                for candidate in candidates:
                                    segment_hillslope_id = str(candidate["segment_hillslope_id"])
                                    source_segment_id = str(candidate["source_segment_id"])
                                    overlap_length_m = float(candidate["overlap_length_m"])
                                    inclusion_ratio = float(candidate["inclusion_ratio"])
                                    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["hillslope_geometry"],
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["hillslope_geometry"],
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        },
                                    )
                                continue

                            if not np.isfinite(hillslope_length_m) or not np.isfinite(hillslope_width_m) or hillslope_length_m <= 0.0 or hillslope_width_m <= 0.0:
                                for candidate in candidates:
                                    segment_hillslope_id = str(candidate["segment_hillslope_id"])
                                    source_segment_id = str(candidate["source_segment_id"])
                                    overlap_length_m = float(candidate["overlap_length_m"])
                                    inclusion_ratio = float(candidate["inclusion_ratio"])
                                    _move_outslope_candidate_to_status(candidate, "failed_non_positive_top_ofe")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_non_positive_top_ofe",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_non_positive_top_ofe",
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_non_positive_top_ofe",
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_non_positive_top_ofe",
                                            "hillslope_length_m": hillslope_length_m,
                                            "hillslope_width_m": hillslope_width_m,
                                        },
                                    )
                                continue

                            strip_plans: List[Dict[str, Any]] = []
                            strip_failure = False

                            for candidate in candidates:
                                segment_hillslope_id = str(candidate["segment_hillslope_id"])
                                source_segment_id = str(candidate["source_segment_id"])
                                feature = candidate["feature"]
                                properties = candidate["properties"]
                                overlap_length_m = float(candidate["overlap_length_m"])
                                inclusion_ratio = float(candidate["inclusion_ratio"])

                                mapped_segment_count += 1

                                segment_inputs = self._resolve_segment_run_inputs(
                                    properties=properties,
                                    params=params,
                                    segment_id=segment_hillslope_id,
                                    design="outslope_unrutted",
                                    warning_counts=mapping_warning_counts,
                                    warning_examples=mapping_warning_examples,
                                    warning_limit=warning_limit,
                                )
                                segment_inputs["resolution_sources"]["design"] = "segment_property"

                                fill_profile, routed_buffer_profile, missing_fields = (
                                    self._resolve_outslope_unrutted_required_profiles(
                                        properties=properties,
                                    )
                                )
                                if missing_fields:
                                    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": missing_fields,
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": missing_fields,
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": missing_fields,
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": missing_fields,
                                        },
                                    )
                                    strip_failure = True
                                    continue

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
                                    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["segment_profile"],
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["segment_profile"],
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        },
                                    )
                                    strip_failure = True
                                    continue

                                profile = dict(profile)
                                profile["segment_length_m"] = max(1.0, float(overlap_length_m))
                                parity_profile = _unrutted.road_geometry(
                                    overlap_length_m, float(segment_inputs["road_width_m"]),
                                )

                                if fill_profile is None or routed_buffer_profile is None:
                                    _move_outslope_candidate_to_status(candidate, "failed_missing_parameter")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["fill_or_buffer_profile"],
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["fill_or_buffer_profile"],
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["fill_or_buffer_profile"],
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "missing_fields": ["fill_or_buffer_profile"],
                                        },
                                    )
                                    strip_failure = True
                                    continue

                                overlap_geometry_wgs84 = candidate.get("overlap_geometry_wgs84")
                                discha_median_m = None
                                if overlap_geometry_wgs84 is not None:
                                    discha_median_m = self._sample_discha_median_from_wgs84_geometry(
                                        overlap_geometry_wgs84,
                                        discha_dataset=discha_dataset,
                                        wgs84_to_discha=wgs84_to_discha,
                                    )
                                placement_source = "distance_to_channel_median"
                                if discha_median_m is None:
                                    discha_median_m = hillslope_length_m * 0.5
                                    placement_source = "mid_hillslope_fallback"

                                placement = _unrutted.placement(
                                    hillslope_length_m, float(parity_profile["sim_length_m"]),
                                    float(fill_profile["fill_length_m"]), float(discha_median_m),
                                    OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M,
                                )
                                top_landuse_length_m = placement["top_landuse_length_m"]
                                downslope_landuse_length_m = placement["bottom_landuse_length_m"]
                                has_downslope_landuse = downslope_landuse_length_m > 0
                                if not placement.pop("fits"):
                                    _move_outslope_candidate_to_status(candidate, "failed_road_fill_exceeds_hillslope")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_road_fill_exceeds_hillslope",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_road_fill_exceeds_hillslope",
                                            "design": "outslope_unrutted",
                                            **placement,
                                            "placement_source": placement_source,
                                            "discha_median_m": float(discha_median_m),
                                            "road_width_m": float(parity_profile["sim_length_m"]),
                                            "fill_length_m": float(fill_profile["fill_length_m"]),
                                            "error": "Road plus fill exceeds hillslope length; verify supplied dimensions and representative hillslope geometry.",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_road_fill_exceeds_hillslope",
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_road_fill_exceeds_hillslope",
                                        },
                                    )
                                    strip_failure = True
                                    continue

                                strip_plans.append(
                                    {
                                        "candidate": candidate,
                                        "source_segment_id": source_segment_id,
                                        "segment_hillslope_id": segment_hillslope_id,
                                        "topaz_id_hill": int(topaz_id_hill),
                                        "target_hillslope_wepp_id": int(wepp_id_int),
                                        "segment_inputs": segment_inputs,
                                        "profile": profile,
                                        "parity_profile": parity_profile,
                                        "fill_profile": fill_profile,
                                        "routed_buffer_profile": routed_buffer_profile,
                                        "overlap_length_m": overlap_length_m,
                                        "inclusion_ratio": inclusion_ratio,
                                        "discha_median_m": float(discha_median_m),
                                        "placement_source": placement_source,
                                        **placement,
                                        "bottom_ofe_compensation_m": 0.0,
                                        "top_landuse_length_m": float(top_landuse_length_m),
                                        "bottom_landuse_length_m": float(downslope_landuse_length_m),
                                        "has_downslope_landuse": bool(has_downslope_landuse),
                                        "top_landuse_slope_pct": float(routed_buffer_profile["buffer_slope_pct"]),
                                        "bottom_landuse_slope_pct": float(routed_buffer_profile["buffer_slope_pct"]),
                                        "strip_width_m": float(parity_profile["sim_width_m"]),
                                        "top_ofe_compensation_m": 0.0,
                                    }
                                )

                            if strip_failure or not strip_plans:
                                continue

                            strip_plans = sorted(
                                strip_plans,
                                key=lambda plan: (
                                    -float(plan["discha_median_m"]),
                                    str(plan["segment_hillslope_id"]),
                                ),
                            )

                            width_sum_before_scaling = float(sum(float(plan["strip_width_m"]) for plan in strip_plans))
                            if width_sum_before_scaling <= 0.0:
                                for plan in strip_plans:
                                    candidate = plan["candidate"]
                                    source_segment_id = str(plan["source_segment_id"])
                                    segment_hillslope_id = str(plan["segment_hillslope_id"])
                                    overlap_length_m = float(plan["overlap_length_m"])
                                    inclusion_ratio = float(plan["inclusion_ratio"])
                                    _move_outslope_candidate_to_status(candidate, "failed_non_positive_top_ofe")
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_non_positive_top_ofe",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_non_positive_top_ofe",
                                            "design": "outslope_unrutted",
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "failed_non_positive_top_ofe",
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_non_positive_top_ofe",
                                        },
                                    )
                                continue

                            if width_sum_before_scaling > hillslope_width_m:
                                width_scale = hillslope_width_m / width_sum_before_scaling
                                for plan in strip_plans:
                                    plan["strip_width_m"] = float(plan["strip_width_m"]) * float(width_scale)

                            strip_width_sum = float(sum(float(plan["strip_width_m"]) for plan in strip_plans))
                            remainder_width_m = max(0.0, float(hillslope_width_m) - strip_width_sum)

                            if 0.0 < remainder_width_m < 0.3 and strip_plans:
                                area_to_compensate_m2 = float(remainder_width_m * hillslope_length_m)
                                comp_width = float(strip_plans[0]["strip_width_m"])
                                if comp_width > 0.0:
                                    compensation_m = area_to_compensate_m2 / comp_width
                                    if not _unrutted.compensate(strip_plans[0], compensation_m):
                                        raise ValueError("Unrutted remainder compensation produces invalid landuse length.")
                                    remainder_width_m = 0.0

                            def _plan_total_length_m(plan_row: Mapping[str, Any]) -> float:
                                return float(
                                    float(plan_row["top_landuse_length_m"])
                                    + float(plan_row["parity_profile"]["sim_length_m"])
                                    + float(plan_row["fill_profile"]["fill_length_m"])
                                    + float(plan_row["bottom_landuse_length_m"])
                                )

                            hillslope_area_m2 = float(hillslope_width_m * hillslope_length_m)
                            if not np.isfinite(hillslope_area_m2):
                                raise ValueError("Unrutted hillslope area must be finite.")
                            represented_area_before_m2 = float(
                                sum(
                                    float(plan["strip_width_m"]) * _plan_total_length_m(plan)
                                    for plan in strip_plans
                                )
                                + float(remainder_width_m * hillslope_length_m)
                            )
                            area_error_before_m2 = float(hillslope_area_m2 - represented_area_before_m2)

                            if abs(area_error_before_m2) > OUTSLOPE_UNRUTTED_AREA_EPSILON_M2 and strip_plans:
                                comp_width = float(strip_plans[0]["strip_width_m"])
                                if comp_width <= 0.0:
                                    comp_width = 0.0
                                if comp_width > 0.0:
                                    compensation_m = float(area_error_before_m2 / comp_width)
                                    if not _unrutted.compensate(strip_plans[0], compensation_m):
                                        for plan in strip_plans:
                                            candidate = plan["candidate"]
                                            source_segment_id = str(plan["source_segment_id"])
                                            segment_hillslope_id = str(plan["segment_hillslope_id"])
                                            overlap_length_m = float(plan["overlap_length_m"])
                                            inclusion_ratio = float(plan["inclusion_ratio"])
                                            _move_outslope_candidate_to_status(candidate, "failed_non_positive_top_ofe")
                                            skipped_segments.append(
                                                {
                                                    "segment_id": source_segment_id,
                                                    "segment_hillslope_id": segment_hillslope_id,
                                                    "reason": "failed_non_positive_top_ofe",
                                                }
                                            )
                                            segment_execution_records.append(
                                                {
                                                    "segment_id": source_segment_id,
                                                    "segment_hillslope_id": segment_hillslope_id,
                                                    "target_hillslope_wepp_id": int(wepp_id_int),
                                                    "target_hillslope_topaz_id": int(topaz_id_hill),
                                                    "status": "failed",
                                                    "routing_mode": "outslope_unrutted_replacement",
                                                    "reason": "failed_non_positive_top_ofe",
                                                    "design": "outslope_unrutted",
                                                    "overlap_length_m": overlap_length_m,
                                                    "inclusion_ratio": inclusion_ratio,
                                                }
                                            )
                                            failed_segment_records.append(
                                                {
                                                    "segment_id": source_segment_id,
                                                    "segment_hillslope_id": segment_hillslope_id,
                                                    "target_hillslope_wepp_id": int(wepp_id_int),
                                                    "routing_mode": "outslope_unrutted_replacement",
                                                    "reason": "failed_non_positive_top_ofe",
                                                }
                                            )
                                            self._append_roads_log(
                                                "run",
                                                "segment_skipped",
                                                {
                                                    "segment_id": source_segment_id,
                                                    "segment_hillslope_id": segment_hillslope_id,
                                                    "reason": "failed_non_positive_top_ofe",
                                                },
                                            )
                                        strip_plans = []

                            if not strip_plans:
                                continue

                            represented_area_after_m2 = float(
                                sum(
                                    float(plan["strip_width_m"]) * _plan_total_length_m(plan)
                                    for plan in strip_plans
                                )
                                + float(remainder_width_m * hillslope_length_m)
                            )
                            area_error_after_m2 = float(hillslope_area_m2 - represented_area_after_m2)

                            if hillslope_record is not None:
                                hillslope_record["top_ofe_compensation_m"] = float(
                                    sum(float(plan["top_ofe_compensation_m"]) for plan in strip_plans)
                                )
                                hillslope_record["bottom_ofe_compensation_m"] = sum(
                                    plan["bottom_ofe_compensation_m"] for plan in strip_plans
                                )
                                hillslope_record["area_error_before_compensation_m2"] = float(area_error_before_m2)
                                hillslope_record["area_error_after_compensation_m2"] = float(area_error_after_m2)

                            emitted_area = 0.0
                            for index, plan in enumerate(strip_plans):
                                lengths, slopes, plan["ofe_order"] = _unrutted.profile_parts(plan)
                                plan["slope_path"] = Path(self.roads_runs_dir) / f"unrutted-h{topaz_id_hill}-{index}.slp"
                                emitted_area += _unrutted.write_slope(plan["slope_path"], plan["strip_width_m"], lengths, slopes)
                                target = plan["parity_profile"]["road_target_area_m2"]
                                modeled = plan["strip_width_m"] * plan["parity_profile"]["sim_length_m"]
                                plan["accounting"] = {
                                    "geometry_policy": _unrutted.POLICY, "connectivity_limitation": _unrutted.LIMITATION,
                                    "source_segment_ids": plan["candidate"]["source_segment_ids"],
                                    "placement_source": plan["placement_source"],
                                    **{key: plan[key] for key in (
                                        "placement_policy", "placement_adjustment", "placement_adjustment_reason",
                                        "original_top_landuse_length_m", "hillslope_length_m",
                                        "upslope_runon_assumed_zero", "top_ofe_compensation_m", "bottom_ofe_compensation_m",
                                        "top_landuse_length_m", "bottom_landuse_length_m", "discha_median_m",
                                    )},
                                    "road_target_area_m2": target, "road_modeled_area_m2": modeled,
                                    "road_area_deficit_m2": max(0.0, target - modeled),
                                    "strip_width_factor": min(1.0, hillslope_width_m / width_sum_before_scaling),
                                    "area_accounting_status": "complete", "area_accounting_reason": None,
                                    "road_area_deficit_reason": "hillslope_width_limit" if modeled < target else None,
                                }
                            remainder_prepared_path = Path(self.roads_runs_dir) / f"unrutted-h{topaz_id_hill}-remainder.slp"
                            if remainder_width_m >= 0.3:
                                emitted_area += _unrutted.write_slope(remainder_prepared_path, remainder_width_m,
                                    [hillslope_length_m], [strip_plans[0]["top_landuse_slope_pct"] / 100])
                            if not np.isfinite(emitted_area) or abs(emitted_area - hillslope_area_m2) > OUTSLOPE_UNRUTTED_AREA_EPSILON_M2:
                                raise ValueError(f"Unrutted emitted hillslope {topaz_id_hill} area does not close.")
                            hillslope_record.update({
                                "reference_area_m2": hillslope_area_m2,
                                "affected_area_m2": represented_area_after_m2 - remainder_width_m * hillslope_length_m,
                                "remainder_area_m2": remainder_width_m * hillslope_length_m,
                                "area_residual_m2": area_error_after_m2,
                                "emitted_area_residual_m2": hillslope_area_m2 - emitted_area,
                                "road_target_area_m2": sum(plan["accounting"]["road_target_area_m2"] for plan in strip_plans),
                                "road_modeled_area_m2": sum(plan["accounting"]["road_modeled_area_m2"] for plan in strip_plans),
                                "road_area_deficit_m2": sum(plan["accounting"]["road_area_deficit_m2"] for plan in strip_plans),
                                "strip_width_factor": min(1.0, hillslope_width_m / width_sum_before_scaling),
                                "area_accounting_status": "complete", "area_accounting_reason": None,
                            })

                            for plan in strip_plans:
                                source_segment_id = str(plan["source_segment_id"])
                                segment_hillslope_id = str(plan["segment_hillslope_id"])
                                overlap_length_m = float(plan["overlap_length_m"])
                                inclusion_ratio = float(plan["inclusion_ratio"])
                                segment_inputs = plan["segment_inputs"]
                                profile = plan["profile"]
                                parity_profile = plan["parity_profile"]
                                fill_profile = plan["fill_profile"]
                                routed_buffer_profile = plan["routed_buffer_profile"]
                                top_landuse_length_m = float(plan["top_landuse_length_m"])
                                bottom_landuse_length_m = float(plan["bottom_landuse_length_m"])
                                has_downslope_landuse = bool(plan["has_downslope_landuse"])
                                discha_median_m = float(plan["discha_median_m"])
                                strip_width_m = float(plan["strip_width_m"])

                                segment_sequence += 1
                                segment_run_id = 900000 + segment_sequence

                                soil_template_path = self._resolve_legacy_soil_template_path(
                                    design="outslope_rutted",
                                    surface=segment_inputs["surface"],
                                    soil_texture=segment_inputs["soil_texture"],
                                )

                                ofe_order = plan["ofe_order"]
                                management_cache_key = (str(segment_inputs["traffic"]), tuple(ofe_order))
                                management_path = routed_mofe_management_cache_by_traffic_and_order.get(management_cache_key)
                                if management_path is None:
                                    management_template_path = self._resolve_legacy_management_template_path(
                                        traffic=segment_inputs["traffic"]
                                    )
                                    management_path = (
                                        Path(self.roads_runs_dir)
                                        / (
                                            f"{management_template_path.stem}.routed_mofe_"
                                            + "_".join(str(value) for value in ofe_order)
                                            + ".man"
                                        )
                                    )
                                    self._build_routed_mofe_management_file(
                                        template_path=management_template_path,
                                        output_path=management_path,
                                        ofe_order=ofe_order,
                                    )
                                    routed_mofe_management_cache_by_traffic_and_order[management_cache_key] = management_path

                                segment_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.routed_mofe.sol"
                                segment_slope_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.slp"

                                self._build_routed_mofe_soil_file(
                                    template_path=soil_template_path,
                                    output_path=segment_soil_path,
                                    traffic=segment_inputs["traffic"],
                                    surface=segment_inputs["surface"],
                                    rfg_pct=segment_inputs["rfg_pct"],
                                    ofe_order=ofe_order,
                                )

                                shutil.copyfile(plan["slope_path"], segment_slope_path)
                                _unrutted.slope_area(segment_slope_path)

                                try:
                                    sim_years = int(self.wepp_instance.climate_instance.input_years)
                                    self._run_segment_hillslope(
                                        segment_run_id=segment_run_id,
                                        climate_wepp_id=int(wepp_id_int),
                                        sim_years=sim_years,
                                        wepp_bin=getattr(self.wepp_instance, "wepp_bin", None),
                                        single_ofe_management_path=management_path,
                                        single_ofe_soil_path=segment_soil_path,
                                        single_ofe_slope_path=segment_slope_path,
                                    )
                                except Exception as exc:
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "segment_run_failed",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_run_failed",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                            "design": "outslope_unrutted",
                                            **plan["accounting"],
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_run_failed",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_run_failed",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        },
                                    )
                                    continue

                                segment_pass_path = Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat"
                                if not segment_pass_path.exists():
                                    skipped_segments.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "segment_pass_missing",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_pass_missing",
                                            "design": "outslope_unrutted",
                                            **plan["accounting"],
                                            "overlap_length_m": overlap_length_m,
                                            "inclusion_ratio": inclusion_ratio,
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_pass_missing",
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_run_failed",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_pass_missing",
                                        },
                                    )
                                    continue

                                successful_segment_count += 1
                                routing_mode_counts["outslope_unrutted_replacement"] += 1
                                design_execution_counts["outslope_unrutted"] += 1
                                replacement_pass_paths_by_wepp[int(wepp_id_int)].append(str(segment_pass_path))

                                execution_record = {
                                    "segment_id": source_segment_id,
                                    "segment_hillslope_id": segment_hillslope_id,
                                    "segment_run_id": segment_run_id,
                                    "target_hillslope_wepp_id": int(wepp_id_int),
                                    "target_hillslope_topaz_id": int(topaz_id_hill),
                                    "status": "completed",
                                    "routing_mode": "outslope_unrutted_replacement",
                                    "routing_eligibility": "outslope_unrutted_replacement",
                                    "design": "outslope_unrutted",
                                    "surface": segment_inputs["surface"],
                                    "traffic": segment_inputs["traffic"],
                                    "soil_texture": segment_inputs["soil_texture"],
                                    "rfg_pct": segment_inputs["rfg_pct"],
                                    "road_width_m": segment_inputs["road_width_m"],
                                    "strip_width_m": strip_width_m,
                                    "fill_length_m": fill_profile["fill_length_m"],
                                    "fill_slope_pct": fill_profile["fill_slope_pct"],
                                    "segment_length_m": profile["segment_length_m"],
                                    "slope_pct_raw": profile["raw_slope_pct"],
                                    "slope_pct_clamped": profile["slope_pct"],
                                    "elevation_high_m": profile["elevation_high_m"],
                                    "elevation_low_m": profile["elevation_low_m"],
                                    "overlap_length_m": overlap_length_m,
                                    "inclusion_ratio": inclusion_ratio,
                                    "segment_pass_relpath": os.path.relpath(segment_pass_path, self.wd),
                                    "contributor_ofe_count": len(ofe_order),
                                    "top_landuse_length_m": top_landuse_length_m,
                                    "bottom_landuse_length_m": bottom_landuse_length_m,
                                    "discha_median_m": discha_median_m,
                                    **plan["accounting"],
                                    **parity_profile,
                                    **fill_profile,
                                    **routed_buffer_profile,
                                }
                                segment_execution_records.append(execution_record)
                                self._append_roads_log("run", "segment_run_completed", execution_record)

                            if remainder_width_m >= 0.3:
                                remainder_segment_id = f"h{int(topaz_id_hill)}::remainder"
                                segment_sequence += 1
                                segment_run_id = 900000 + segment_sequence

                                remainder_segment_inputs = strip_plans[0]["segment_inputs"]
                                remainder_soil_template_path = self._resolve_legacy_soil_template_path(
                                    design="outslope_rutted",
                                    surface=remainder_segment_inputs["surface"],
                                    soil_texture=remainder_segment_inputs["soil_texture"],
                                )

                                remainder_order: Tuple[int, ...] = (3,)
                                management_cache_key = (str(remainder_segment_inputs["traffic"]), remainder_order)
                                management_path = routed_mofe_management_cache_by_traffic_and_order.get(management_cache_key)
                                if management_path is None:
                                    management_template_path = self._resolve_legacy_management_template_path(
                                        traffic=remainder_segment_inputs["traffic"]
                                    )
                                    management_path = (
                                        Path(self.roads_runs_dir)
                                        / (
                                            f"{management_template_path.stem}.routed_mofe_"
                                            + "_".join(str(value) for value in remainder_order)
                                            + ".man"
                                        )
                                    )
                                    self._build_routed_mofe_management_file(
                                        template_path=management_template_path,
                                        output_path=management_path,
                                        ofe_order=remainder_order,
                                    )
                                    routed_mofe_management_cache_by_traffic_and_order[management_cache_key] = management_path

                                remainder_soil_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.routed_mofe.sol"
                                remainder_slope_path = Path(self.roads_runs_dir) / f"p{segment_run_id}.slp"
                                self._build_routed_mofe_soil_file(
                                    template_path=remainder_soil_template_path,
                                    output_path=remainder_soil_path,
                                    traffic=remainder_segment_inputs["traffic"],
                                    surface=remainder_segment_inputs["surface"],
                                    rfg_pct=remainder_segment_inputs["rfg_pct"],
                                    ofe_order=remainder_order,
                                )
                                shutil.copyfile(remainder_prepared_path, remainder_slope_path)
                                _unrutted.slope_area(remainder_slope_path)

                                try:
                                    sim_years = int(self.wepp_instance.climate_instance.input_years)
                                    self._run_segment_hillslope(
                                        segment_run_id=segment_run_id,
                                        climate_wepp_id=int(wepp_id_int),
                                        sim_years=sim_years,
                                        wepp_bin=getattr(self.wepp_instance, "wepp_bin", None),
                                        single_ofe_management_path=management_path,
                                        single_ofe_soil_path=remainder_soil_path,
                                        single_ofe_slope_path=remainder_slope_path,
                                    )
                                except Exception as exc:
                                    skipped_segments.append(
                                        {
                                            "segment_id": remainder_segment_id,
                                            "reason": "segment_run_failed",
                                        }
                                    )
                                    segment_execution_records.append(
                                        {
                                            "segment_id": remainder_segment_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "failed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_run_failed",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                            "design": "outslope_unrutted_remainder",
                                        }
                                    )
                                    failed_segment_records.append(
                                        {
                                            "segment_id": remainder_segment_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "reason": "segment_run_failed",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_run_failed",
                                        {
                                            "segment_id": remainder_segment_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                                        },
                                    )
                                else:
                                    remainder_pass_path = Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat"
                                    if not remainder_pass_path.exists():
                                        skipped_segments.append(
                                            {
                                                "segment_id": remainder_segment_id,
                                                "reason": "segment_pass_missing",
                                            }
                                        )
                                        segment_execution_records.append(
                                            {
                                                "segment_id": remainder_segment_id,
                                                "segment_run_id": segment_run_id,
                                                "target_hillslope_wepp_id": int(wepp_id_int),
                                                "target_hillslope_topaz_id": int(topaz_id_hill),
                                                "status": "failed",
                                                "routing_mode": "outslope_unrutted_replacement",
                                                "reason": "segment_pass_missing",
                                                "design": "outslope_unrutted_remainder",
                                            }
                                        )
                                        failed_segment_records.append(
                                            {
                                                "segment_id": remainder_segment_id,
                                                "segment_run_id": segment_run_id,
                                                "target_hillslope_wepp_id": int(wepp_id_int),
                                                "routing_mode": "outslope_unrutted_replacement",
                                                "reason": "segment_pass_missing",
                                            }
                                        )
                                        self._append_roads_log(
                                            "run",
                                            "segment_run_failed",
                                            {
                                                "segment_id": remainder_segment_id,
                                                "segment_run_id": segment_run_id,
                                                "target_hillslope_wepp_id": int(wepp_id_int),
                                                "routing_mode": "outslope_unrutted_replacement",
                                                "reason": "segment_pass_missing",
                                            },
                                        )
                                    else:
                                        successful_segment_count += 1
                                        routing_mode_counts["outslope_unrutted_replacement_remainder"] += 1
                                        replacement_pass_paths_by_wepp[int(wepp_id_int)].append(str(remainder_pass_path))
                                        execution_record = {
                                            "segment_id": remainder_segment_id,
                                            "segment_run_id": segment_run_id,
                                            "target_hillslope_wepp_id": int(wepp_id_int),
                                            "target_hillslope_topaz_id": int(topaz_id_hill),
                                            "status": "completed",
                                            "routing_mode": "outslope_unrutted_replacement",
                                            "routing_eligibility": "outslope_unrutted_replacement",
                                            "design": "outslope_unrutted_remainder",
                                            "segment_pass_relpath": os.path.relpath(remainder_pass_path, self.wd),
                                            "strip_width_m": float(remainder_width_m),
                                            "segment_length_m": float(hillslope_length_m),
                                            "contributor_ofe_count": 1,
                                        }
                                        segment_execution_records.append(execution_record)
                                        self._append_roads_log("run", "segment_run_completed", execution_record)

                    included_count = 0
                    excluded_count = 0
                    capped_count = 0
                    for candidate_row in outslope_unrutted_candidate_status.values():
                        status_value = str(candidate_row.get("status") or "")
                        if status_value == "included":
                            included_count += 1
                        elif status_value == "excluded_cap_limit":
                            capped_count += 1
                        elif status_value.startswith("excluded_"):
                            excluded_count += 1

                    outslope_unrutted_diagnostics["outslope_unrutted_included_segment_count"] = int(included_count)
                    outslope_unrutted_diagnostics["outslope_unrutted_excluded_segment_count"] = int(excluded_count)
                    outslope_unrutted_diagnostics["outslope_unrutted_capped_segment_count"] = int(capped_count)
                    outslope_unrutted_diagnostics["outslope_unrutted_targeted_hillslope_count"] = int(
                        sum(
                            1
                            for record in outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", [])
                            if isinstance(record, Mapping) and bool(record.get("segment_ids_included"))
                        )
                    )

            for hill in outslope_unrutted_diagnostics.get("outslope_unrutted_hillslope_records", []):
                if hill.get("area_accounting_status") != "complete":
                    hill["top_ofe_compensation_m"] = None
                    hill["bottom_ofe_compensation_m"] = None
            for record in segment_execution_records:
                if record.get("design") != "outslope_unrutted":
                    continue
                candidate = outslope_unrutted_candidate_status.get(record.get("segment_hillslope_id"), {})
                record.setdefault("source_segment_ids", candidate.get("source_segment_ids", [record["segment_id"]]))
                for key in ("placement_source", "placement_adjustment", "placement_adjustment_reason",
                            "original_top_landuse_length_m", "hillslope_length_m", "discha_median_m",
                            "top_landuse_length_m", "bottom_landuse_length_m", "upslope_runon_assumed_zero"):
                    record.setdefault(key, None)
                record.setdefault("placement_policy", _unrutted.PLACEMENT_POLICY)
                record.setdefault("geometry_policy", _unrutted.POLICY)
                record.setdefault("connectivity_limitation", _unrutted.LIMITATION)
                if record.get("status") != "completed":
                    record.update(area_accounting_status="unavailable",
                                  area_accounting_reason=record.get("reason", "execution_failed"))
                    for key in ("road_target_area_m2", "road_modeled_area_m2", "road_area_deficit_m2", "strip_width_factor", "top_ofe_compensation_m", "bottom_ofe_compensation_m"):
                        record.setdefault(key, None)
            self._attach_parameterization_records(segment_execution_records)
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
            mapping_warning_count = int(sum(mapping_warning_counts.values()))
            mapping_warning_counts_dict = dict(sorted(mapping_warning_counts.items()))
            if mapping_warning_count:
                self._append_roads_log(
                    "run",
                    "mapping_warnings_detected",
                    {
                        "mapping_warning_count": mapping_warning_count,
                        "mapping_warning_codes": sorted(mapping_warning_counts.keys()),
                    },
                )

            if failed_segment_records:
                additive_targeted_ids = sorted(
                    int(wepp_id)
                    for wepp_id, paths in segment_pass_paths_by_wepp.items()
                    if paths
                )
                replacement_targeted_ids = sorted(
                    int(wepp_id)
                    for wepp_id, paths in replacement_pass_paths_by_wepp.items()
                    if paths
                )
                targeted_ids = sorted(set(additive_targeted_ids) | set(replacement_targeted_ids))
                failed_run_summary = {
                    "eligible_segment_count": eligible_segment_count,
                    "mapped_segment_count": mapped_segment_count,
                    "executed_segment_count": successful_segment_count,
                    "executed_channel_associated_segment_count": int(routing_mode_counts.get("channel_associated", 0)),
                    "executed_non_channel_routed_segment_count": int(routing_mode_counts.get("non_channel_routed", 0)),
                    "segment_routing_mode_counts": dict(sorted(routing_mode_counts.items())),
                    "executed_outslope_rutted_segment_count": int(design_execution_counts.get("outslope_rutted", 0)),
                    "executed_outslope_unrutted_segment_count": int(
                        design_execution_counts.get("outslope_unrutted", 0)
                    ),
                    "segment_design_counts": dict(sorted(design_execution_counts.items())),
                    "fill_default_usage_counts": dict(sorted(fill_default_usage_counts.items())),
                    "trace_invocation_count": int(trace_invocation_count),
                    "trace_reached_channel_count": int(trace_reaches_channel_count),
                    "trace_termination_reason_counts": dict(sorted(trace_termination_reason_counts.items())),
                    "targeted_hillslope_count": len(targeted_ids),
                    "targeted_hillslope_wepp_ids": targeted_ids,
                    "additive_targeted_hillslope_wepp_ids": additive_targeted_ids,
                    "replacement_targeted_hillslope_wepp_ids": replacement_targeted_ids,
                    "skipped_segments": skipped_segments,
                    "skipped_segment_reason_counts": dict(sorted(skipped_reason_counts.items())),
                    "segment_execution_records": segment_execution_records,
                "parameterization_hash": roads_parameterization.configuration_hash(self._parameterization),
                    "pass_staging_strategy": {},
                    "segment_pass_count": successful_segment_count,
                    "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                    "roads_runs_relpath": os.path.relpath(self.roads_runs_dir, self.wd),
                    "roads_output_relpath": os.path.relpath(self.roads_output_dir, self.wd),
                    "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
                    "mapping_warning_count": mapping_warning_count,
                    "mapping_warning_counts": mapping_warning_counts_dict,
                    "mapping_warning_examples": mapping_warning_examples,
                    "attribute_field_map": dict(attribute_field_map),
                    **outslope_unrutted_diagnostics,
                    **placement_marker,
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
                        "segment_pass_manifest_relpath": os.path.relpath(
                            self.roads_segment_pass_manifest_path, self.wd
                        ),
                        "mapping_warning_count": mapping_warning_count,
                    },
                )
                raise RuntimeError(failed_run_summary["error"])

            baseline_output_dir = Path(self.wepp_instance.output_dir)
            if not baseline_output_dir.exists():
                raise FileNotFoundError(f"Missing baseline WEPP output directory: {baseline_output_dir}")

            staged_strategy: Dict[str, str] = {}
            additive_targeted_ids = sorted(
                int(wepp_id)
                for wepp_id, paths in segment_pass_paths_by_wepp.items()
                if paths
            )
            replacement_targeted_ids = sorted(
                int(wepp_id)
                for wepp_id, paths in replacement_pass_paths_by_wepp.items()
                if paths
            )
            replacement_targeted_id_set = set(replacement_targeted_ids)
            additive_targeted_without_replacement_ids = sorted(
                wepp_id for wepp_id in additive_targeted_ids if wepp_id not in replacement_targeted_id_set
            )
            targeted_ids = sorted(set(additive_targeted_ids) | set(replacement_targeted_ids))
            all_hillslope_wepp_ids = sorted(int(value) for value in translator.iter_wepp_sub_ids())

            current_stage = "pass_combination"
            accounting_ledger = self._prepare_modeled_area_accounting(
                all_hillslope_wepp_ids, segment_execution_records
            )
            staged_strategy = {str(t["id"]): t["mode"] for t in accounting_ledger["targets"]}

            run_summary_base = {
                "eligible_segment_count": eligible_segment_count,
                "mapped_segment_count": mapped_segment_count,
                "executed_segment_count": successful_segment_count,
                "executed_channel_associated_segment_count": int(routing_mode_counts.get("channel_associated", 0)),
                "executed_non_channel_routed_segment_count": int(routing_mode_counts.get("non_channel_routed", 0)),
                "segment_routing_mode_counts": dict(sorted(routing_mode_counts.items())),
                "executed_outslope_rutted_segment_count": int(design_execution_counts.get("outslope_rutted", 0)),
                "executed_outslope_unrutted_segment_count": int(design_execution_counts.get("outslope_unrutted", 0)),
                "segment_design_counts": dict(sorted(design_execution_counts.items())),
                "fill_default_usage_counts": dict(sorted(fill_default_usage_counts.items())),
                "trace_invocation_count": int(trace_invocation_count),
                "trace_reached_channel_count": int(trace_reaches_channel_count),
                "trace_termination_reason_counts": dict(sorted(trace_termination_reason_counts.items())),
                "targeted_hillslope_count": len(targeted_ids),
                "targeted_hillslope_wepp_ids": targeted_ids,
                "additive_targeted_hillslope_wepp_ids": additive_targeted_ids,
                "replacement_targeted_hillslope_wepp_ids": replacement_targeted_ids,
                "skipped_segments": skipped_segments,
                "skipped_segment_reason_counts": dict(sorted(skipped_reason_counts.items())),
                "segment_execution_records": segment_execution_records,
                "parameterization_hash": roads_parameterization.configuration_hash(self._parameterization),
                "pass_staging_strategy": staged_strategy,
                "segment_pass_count": successful_segment_count,
                "segment_pass_manifest_relpath": os.path.relpath(self.roads_segment_pass_manifest_path, self.wd),
                "roads_runs_relpath": os.path.relpath(self.roads_runs_dir, self.wd),
                "roads_output_relpath": os.path.relpath(self.roads_output_dir, self.wd),
                "roads_log_relpath": os.path.relpath(self.roads_log_path, self.wd),
                "mapping_warning_count": mapping_warning_count,
                "mapping_warning_counts": mapping_warning_counts_dict,
                "mapping_warning_examples": mapping_warning_examples,
                "attribute_field_map": dict(attribute_field_map),
                **outslope_unrutted_diagnostics,
                **placement_marker,
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
                make_watershed_omni_contrasts_run(
                    years,
                    wepp_id_paths,
                    self.roads_runs_dir,
                    pass_family=self.wepp_instance.pass_family,
                    wepp_bin=self.wepp_instance.wepp_bin,
                )
                run_watershed(self.roads_runs_dir, wepp_bin=self.wepp_instance.wepp_bin)
                from wepppy.wepp.interchange.roads_accounting import mark_routed

                mark_routed(Path(self.wd))
            except Exception as exc:
                failed_run_summary = {
                    **run_summary_base,
                    "status": "failed",
                    "failed_stage": "watershed_rerun",
                    "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                    "failed_at": int(time.time()),
                }
                self._append_roads_log(
                    "run",
                    "watershed_rerun_failed",
                    {
                        "watershed_run_relpath": run_summary_base["watershed_run_relpath"],
                        "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
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

            run_summary["parameterization_comparison"] = _parameterization_comparisons.write_comparison_snapshot(
                self.wd, parameterization=self._parameterization,
                configuration_hash=roads_parameterization.configuration_hash(self._parameterization),
                completed_at=run_summary["completed_at"],
                wepp_bin=getattr(self.wepp_instance, "wepp_bin", None),
            )
            comparison_relpath = "wepp/roads/output/roads.parameterization.comparison.json"
            if comparison_relpath not in roads_report_resources["required_relpaths"]:
                roads_report_resources["required_relpaths"].append(comparison_relpath)
            with self.locked():
                self._last_run_summary = run_summary
                self._status = "completed"
                self._errors = []
                self._timestamps["run_roads"] = int(time.time())

            roads_lifecycle.publish(
                self.wd, roads_report_resources,
                single_storm=roads_report_resources["is_single_storm"],
            )
            return dict(run_summary)
        except Exception as exc:
            if not roads_lifecycle.invalidated(self.wd):
                raise
            if failed_run_summary is None:
                failed_run_summary = dict(run_summary_base or {})
                failed_run_summary.update(
                    {
                        "status": "failed",
                        "failed_stage": current_stage,
                        "error": safe_text(str(exc), source_profile=current_profile(WORKER)),
                        "failed_at": int(time.time()),
                    }
                )
            with self.locked():
                failed_run_summary.update(placement_marker)
                self._last_run_summary = failed_run_summary
            self._record_error_and_raise(exc)

        finally:
            self.__dict__.pop("_parameterization_runtime_templates", None)
            self.__dict__.pop("_parameterization_runtime_readbacks", None)

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

    def query_inputs(self) -> Dict[str, Any]:
        """Read saved form inputs without requiring access to model results."""
        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        return {
            "roads_params": params,
            "parameterization": self.query_parameterization(),
            "attribute_field_map": dict(params["attribute_field_map"]),
            "discovered_attribute_catalog": getattr(self, "_uploaded_attribute_catalog", None),
            "uploaded_geojson_relpath": getattr(self, "_uploaded_geojson_relpath", None),
        }

    @roads_lifecycle.inspection
    def query_summary(self) -> Dict[str, Any]:
        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        last_run_summary = getattr(self, '_last_run_summary', None)
        if last_run_summary and last_run_summary.get('status') == 'completed' and not roads_lifecycle.available(self.wd):
            last_run_summary = None
        summary_payload = {
            "enabled": bool(getattr(self, "_enabled", False)),
            "uploaded_geojson_relpath": getattr(self, "_uploaded_geojson_relpath", None),
            "uploaded_geojson_sha256": getattr(self, "_uploaded_geojson_sha256", None),
            "roads_params": params,
            "parameterization": self.query_parameterization(),
            "attribute_field_map": dict(params.get("attribute_field_map", self._empty_attribute_field_map())),
            "discovered_attribute_catalog": getattr(self, "_uploaded_attribute_catalog", None),
            "last_prepare_summary": getattr(self, "_last_prepare_summary", None),
            "last_run_summary": last_run_summary,
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
                "has_attribute_catalog": summary_payload["discovered_attribute_catalog"] is not None,
                "has_prepare_summary": summary_payload["last_prepare_summary"] is not None,
                "has_run_summary": summary_payload["last_run_summary"] is not None,
            },
        )
        return summary_payload
