"""Roads NoDb controller for Roads point-source routing workflows."""

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
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from pyproj import CRS, Geod, Transformer
from shapely.geometry import GeometryCollection, LineString, MultiLineString, shape
from shapely.ops import transform as shapely_transform
from wepp_runner.wepp_runner import (make_hillslope_run,
    make_watershed_omni_contrasts_run,
    run_hillslope,
    run_watershed,
)

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.geojson_crs_inference import GeoBounds, infer_geojson_crs
from wepppy.nodb.mods.roads.monotonic_segments import convert_geojson_file_to_monotonic_segments

__all__ = ["Roads"]


DESIGN_ALIASES: Dict[str, str] = {
    "inslope_bd": "inslope_bd",
    "inslope_rd": "inslope_rd",
    "outslope_rutted": "outslope_rutted",
    "outrut": "outslope_rutted",
    "outslope_unrutted": "outslope_unrutted",
    "outslope": "outslope_unrutted",
    "outunrut": "outslope_unrutted",
}

ELIGIBLE_ROADS_DESIGNS: frozenset[str] = frozenset(DESIGN_ALIASES.values())
ELIGIBLE_POINT_SOURCE_DESIGNS: frozenset[str] = frozenset(
    {"inslope_bd", "inslope_rd", "outslope_rutted"}
)

OUTSLOPE_UNRUTTED_AREA_EPSILON_M2 = 0.001
OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M = 10.0


def _normalize_design(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = DESIGN_ALIASES.get(value.strip().lower())
    if normalized is None:
        return None
    return str(normalized)


def _is_eligible_design(value: Any) -> bool:
    return _normalize_design(value) in ELIGIBLE_ROADS_DESIGNS


def _is_hillslope_topaz_id(value: Any) -> bool:
    try:
        return abs(int(value)) % 10 in {1, 2, 3}
    except (TypeError, ValueError):
        return False


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

ATTRIBUTE_FIELD_MAP_KEYS: Tuple[str, ...] = (
    "design",
    "surface",
    "traffic",
)

LEGACY_DESIGN_KEYS: Tuple[str, ...] = ("DESIGN", "design")
LEGACY_SURFACE_KEYS: Tuple[str, ...] = ("SURFACE", "surface", "ROAD_SURFACE")
LEGACY_TRAFFIC_KEYS: Tuple[str, ...] = ("TRAFFIC", "traffic", "CONDITION", "condition")

ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY = "attribute_discovery_profile_feature_limit"
ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY = "attribute_discovery_value_preview_limit"
ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY = "attribute_discovery_value_max_chars"

DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT = 10


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
        return {
            "input_crs": "EPSG:4326",
            "sample_step_m": None,
            "tolerance_m": 0.5,
            "soil_texture_default": "loam",
            "surface_default": "gravel",
            "traffic_default": "low",
            "rfg_pct_default": 15.0,
            "road_width_m_default": 4.0,
            "fill_length_default_m": 30.0,
            "fill_slope_default_pct": 10.0,
            "trace_max_steps": 20000,
            "max_upload_mb": 50,
            "attribute_field_map": {
                "design": None,
                "surface": None,
                "traffic": None,
            },
            ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY: 5000,
            ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY: 5,
            ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY: 120,
        }

    @classmethod
    def _empty_attribute_field_map(cls) -> Dict[str, Optional[str]]:
        return {key: None for key in ATTRIBUTE_FIELD_MAP_KEYS}

    @classmethod
    def _normalize_attribute_field_map(
        cls,
        raw_map: Any,
        *,
        known_fields: Optional[Set[str]] = None,
    ) -> Dict[str, Optional[str]]:
        if raw_map in (None, ""):
            return cls._empty_attribute_field_map()
        if not isinstance(raw_map, Mapping):
            raise ValueError("attribute_field_map must be an object.")

        unknown_keys = sorted(str(key) for key in raw_map.keys() if str(key) not in ATTRIBUTE_FIELD_MAP_KEYS)
        if unknown_keys:
            raise ValueError(f"attribute_field_map has unsupported key(s): {', '.join(unknown_keys)}.")

        normalized = cls._empty_attribute_field_map()
        for field_key in ATTRIBUTE_FIELD_MAP_KEYS:
            raw_value = raw_map.get(field_key)
            if raw_value in (None, ""):
                normalized[field_key] = None
                continue
            if not isinstance(raw_value, str):
                raise ValueError(f"attribute_field_map.{field_key} must be a string or null.")
            field_name = raw_value.strip()
            if not field_name:
                normalized[field_key] = None
                continue
            if known_fields is not None and field_name not in known_fields:
                raise ValueError(
                    f"attribute_field_map.{field_key}={field_name!r} is not present in discovered attributes."
                )
            normalized[field_key] = field_name
        return normalized

    @classmethod
    def _normalize_params_with_defaults(cls, params: Mapping[str, Any]) -> Dict[str, Any]:
        merged = dict(cls._default_params())
        merged.update(dict(params))
        try:
            merged["attribute_field_map"] = cls._normalize_attribute_field_map(
                merged.get("attribute_field_map"),
                known_fields=None,
            )
        except ValueError:
            merged["attribute_field_map"] = cls._empty_attribute_field_map()

        for key in (
            ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY,
            ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY,
            ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY,
        ):
            default_value = int(cls._default_params()[key])
            try:
                parsed = int(merged.get(key, default_value))
            except (TypeError, ValueError):
                parsed = default_value
            if parsed <= 0:
                parsed = default_value
            merged[key] = parsed

        return merged

    @staticmethod
    def _dedupe_keys(keys: Iterable[str]) -> Tuple[str, ...]:
        ordered: List[str] = []
        seen: Set[str] = set()
        for key in keys:
            if not isinstance(key, str):
                continue
            normalized = key.strip()
            if not normalized or normalized in seen:
                continue
            ordered.append(normalized)
            seen.add(normalized)
        return tuple(ordered)

    @staticmethod
    def _first_non_empty_property_with_key(
        properties: Mapping[str, Any],
        keys: Iterable[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        for key in keys:
            value = properties.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text, key
        return None, None

    @staticmethod
    def _stringify_attribute_sample(value: Any, *, max_chars: int) -> str:
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, (int, float, bool)) or value is None:
            text = str(value)
        else:
            text = json.dumps(value, sort_keys=True, default=str)
        if len(text) <= max_chars:
            return text
        if max_chars <= 3:
            return text[:max_chars]
        return text[: max_chars - 3] + "..."

    def _discovered_attribute_field_names(self) -> Tuple[str, ...]:
        catalog = getattr(self, "_uploaded_attribute_catalog", None)
        if not isinstance(catalog, Mapping):
            return tuple()
        field_names = catalog.get("field_names")
        if not isinstance(field_names, list):
            return tuple()
        return tuple(
            field_name
            for field_name in field_names
            if isinstance(field_name, str) and field_name.strip()
        )

    def _build_attribute_catalog(
        self,
        *,
        payload: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> Dict[str, Any]:
        features_raw = payload.get("features")
        features = features_raw if isinstance(features_raw, list) else []

        field_names_set: Set[str] = set()
        for feature in features:
            properties = feature.get("properties") if isinstance(feature, Mapping) else None
            if not isinstance(properties, Mapping):
                continue
            for key in properties.keys():
                if isinstance(key, str) and key.strip():
                    field_names_set.add(key)

        field_names = sorted(field_names_set)
        profile_limit = int(params.get(ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY, 5000))
        preview_limit = int(params.get(ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY, 5))
        preview_max_chars = int(params.get(ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY, 120))

        profiled_feature_count = min(len(features), profile_limit)
        field_non_empty_counts: Dict[str, int] = {field_name: 0 for field_name in field_names}
        field_distinct_sets: Dict[str, Set[str]] = {field_name: set() for field_name in field_names}
        field_samples: Dict[str, List[str]] = {field_name: [] for field_name in field_names}

        for feature in features[:profiled_feature_count]:
            properties = feature.get("properties") if isinstance(feature, Mapping) else None
            if not isinstance(properties, Mapping):
                continue
            for key, raw_value in properties.items():
                if key not in field_non_empty_counts:
                    continue
                text = str(raw_value).strip() if raw_value is not None else ""
                if not text:
                    continue
                field_non_empty_counts[key] += 1
                sample_value = self._stringify_attribute_sample(raw_value, max_chars=preview_max_chars)
                field_distinct_sets[key].add(sample_value)
                if sample_value not in field_samples[key] and len(field_samples[key]) < preview_limit:
                    field_samples[key].append(sample_value)

        field_profiles = [
            {
                "name": field_name,
                "non_empty_count": field_non_empty_counts[field_name],
                "distinct_non_empty_count": len(field_distinct_sets[field_name]),
                "sample_values": field_samples[field_name],
            }
            for field_name in field_names
        ]

        return {
            "field_names": field_names,
            "field_profiles": field_profiles,
            "field_count": len(field_names),
            "total_feature_count": len(features),
            "profiled_feature_count": profiled_feature_count,
            "profile_truncated": profiled_feature_count < len(features),
            "discovery_limits": {
                ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY: profile_limit,
                ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY: preview_limit,
                ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY: preview_max_chars,
            },
        }

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
        warning_counts[code] += 1
        if len(warning_examples) >= max(0, int(limit)):
            return
        row: Dict[str, Any] = {"code": code, "message": message}
        if segment_id:
            row["segment_id"] = segment_id
        if field_name:
            row["field_name"] = field_name
        warning_examples.append(row)

    def _auto_discover_attribute_field_map(
        self,
        *,
        field_names: Sequence[str],
        previous_map: Mapping[str, Any],
    ) -> Dict[str, Optional[str]]:
        discovered_fields: Set[str] = {
            field_name for field_name in field_names if isinstance(field_name, str) and field_name.strip()
        }
        normalized_previous = self._normalize_attribute_field_map(previous_map, known_fields=None)
        resolved = self._empty_attribute_field_map()

        for field_key in ATTRIBUTE_FIELD_MAP_KEYS:
            previous_value = normalized_previous.get(field_key)
            if previous_value and previous_value in discovered_fields:
                resolved[field_key] = previous_value

        candidate_defaults = {
            "design": ("DESIGN", "design"),
            "surface": ("SURFACE", "surface"),
            "traffic": ("TRAFFIC", "traffic"),
        }
        for field_key, candidates in candidate_defaults.items():
            if resolved[field_key]:
                continue
            for candidate in candidates:
                if candidate in discovered_fields:
                    resolved[field_key] = candidate
                    break

        return resolved

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
        mapped_design_key = attribute_field_map.get("design")
        mapped_design_is_custom = bool(mapped_design_key) and mapped_design_key not in LEGACY_DESIGN_KEYS
        if mapped_design_key:
            mapped_design_raw, _ = self._first_non_empty_property_with_key(properties, (mapped_design_key,))
            if mapped_design_raw is None:
                if mapped_design_is_custom and warning_counts is not None and warning_examples is not None:
                    self._collect_warning(
                        warning_counts,
                        warning_examples,
                        code="design_mapped_field_missing",
                        message=(
                            f"Mapped design field {mapped_design_key!r} is missing or empty; using fallback keys."
                        ),
                        limit=warning_limit,
                        segment_id=segment_id,
                        field_name=mapped_design_key,
                    )
            else:
                normalized_design = _normalize_design(mapped_design_raw)
                if normalized_design is not None:
                    return normalized_design, mapped_design_key
                if mapped_design_is_custom and warning_counts is not None and warning_examples is not None:
                    self._collect_warning(
                        warning_counts,
                        warning_examples,
                        code="design_mapped_field_not_eligible",
                        message=(
                            f"Mapped design field {mapped_design_key!r} value {mapped_design_raw!r} "
                            "is not an eligible roads design; using fallback keys."
                        ),
                        limit=warning_limit,
                        segment_id=segment_id,
                        field_name=mapped_design_key,
                    )

        for key in LEGACY_DESIGN_KEYS:
            raw_value, _ = self._first_non_empty_property_with_key(properties, (key,))
            if raw_value is None:
                continue
            normalized_design = _normalize_design(raw_value)
            if normalized_design is not None:
                return normalized_design, key
        return None, None

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
        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))

        if "input_crs" in payload:
            value = str(payload["input_crs"]).strip()
            if not value:
                raise ValueError("input_crs must be a non-empty string.")
            try:
                CRS.from_user_input(value)
            except Exception as exc:
                raise ValueError(f"input_crs is invalid: {exc}") from exc
            params["input_crs"] = value

        for key in (
            "sample_step_m",
            "tolerance_m",
            "rfg_pct_default",
            "road_width_m_default",
            "fill_length_default_m",
            "fill_slope_default_pct",
        ):
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
            if key == "fill_slope_default_pct":
                numeric = self._clamp_percent_slope(numeric)
            params[key] = numeric

        if "trace_max_steps" in payload:
            try:
                trace_max_steps = int(payload["trace_max_steps"])
            except (TypeError, ValueError):
                raise ValueError("trace_max_steps must be an integer.")
            if trace_max_steps <= 0:
                raise ValueError("trace_max_steps must be > 0.")
            params["trace_max_steps"] = trace_max_steps

        if "max_upload_mb" in payload:
            try:
                max_upload_mb = int(payload["max_upload_mb"])
            except (TypeError, ValueError):
                raise ValueError("max_upload_mb must be an integer.")
            if max_upload_mb <= 0:
                raise ValueError("max_upload_mb must be > 0.")
            params["max_upload_mb"] = max_upload_mb

        for key in (
            ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY,
            ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY,
            ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY,
        ):
            if key not in payload:
                continue
            try:
                value = int(payload[key])
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be an integer.")
            if value <= 0:
                raise ValueError(f"{key} must be > 0.")
            params[key] = value

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

        if "attribute_field_map" in payload:
            payload_map = payload["attribute_field_map"]
            current_map = self._normalize_attribute_field_map(params.get("attribute_field_map"), known_fields=None)
            if payload_map in (None, ""):
                merged_map = self._empty_attribute_field_map()
            else:
                if not isinstance(payload_map, Mapping):
                    raise ValueError("attribute_field_map must be an object.")
                merged_map = dict(current_map)
                for key in payload_map.keys():
                    key_text = str(key)
                    if key_text not in ATTRIBUTE_FIELD_MAP_KEYS:
                        raise ValueError(f"attribute_field_map has unsupported key: {key_text}.")
                    merged_map[key_text] = payload_map[key]
            known_fields = set(self._discovered_attribute_field_names()) or None
            params["attribute_field_map"] = self._normalize_attribute_field_map(
                merged_map,
                known_fields=known_fields,
            )

        params = self._normalize_params_with_defaults(params)

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
        shutil.copy2(source_path, target_path)

        digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        relpath = str(target_path.relative_to(self.wd))
        now = int(time.time())
        attribute_catalog = self._build_attribute_catalog(payload=payload, params=params)
        previous_map = self._normalize_attribute_field_map(params.get("attribute_field_map"), known_fields=None)
        discovered_map = self._auto_discover_attribute_field_map(
            field_names=attribute_catalog.get("field_names", []),
            previous_map=previous_map,
        )
        params["attribute_field_map"] = discovered_map

        with self.locked():
            self._uploaded_geojson_relpath = relpath
            self._uploaded_geojson_sha256 = digest
            self._uploaded_attribute_catalog = attribute_catalog
            self._roads_params = params
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
                "effective_input_crs": effective_input_crs,
                "input_crs_source": input_crs_source,
                "discovered_attribute_field_count": int(attribute_catalog.get("field_count", 0)),
                "attribute_field_map": discovered_map,
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
            "effective_input_crs": effective_input_crs,
            "input_crs_source": input_crs_source,
            "discovered_attribute_catalog": attribute_catalog,
            "attribute_field_map": discovered_map,
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

    def _load_prepared_segments_geojson(self) -> Dict[str, Any]:
        segment_path = Path(self.roads_monotonic_geojson_path)
        if not segment_path.exists():
            raise FileNotFoundError(
                "Prepared roads segments not found. Run prepare_segments first."
            )

        payload = json.loads(segment_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Prepared roads segment GeoJSON is malformed.")
        if payload.get("type") != "FeatureCollection":
            raise ValueError("Prepared roads segment payload must be a FeatureCollection.")
        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("Prepared roads segment payload is missing features.")
        return dict(payload)

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
        manifest_path = Path(self.roads_segment_pass_manifest_path)
        if not manifest_path.exists():
            return {}
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Roads segment pass manifest is malformed.")
        records: Dict[str, Dict[str, Any]] = {}
        for row in payload:
            if not isinstance(row, Mapping):
                continue
            segment_id = str(row.get("segment_id") or "").strip()
            if not segment_id:
                continue
            records[segment_id] = dict(row)
        return records

    def _build_segment_profile_for_query(
        self,
        *,
        feature: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        input_crs_raw = str(params.get("input_crs") or "EPSG:4326")
        try:
            input_crs = CRS.from_user_input(input_crs_raw)
        except Exception as exc:
            return None, f"Unable to parse Roads input CRS {input_crs_raw!r}: {exc}"

        try:
            raster_paths = self._resolve_prepare_raster_paths()
        except Exception as exc:
            return None, f"Unable to resolve Roads DEM path: {exc}"

        try:
            with rasterio.open(raster_paths["dem_path"]) as dem_dataset:
                if dem_dataset.crs is None:
                    return None, "Roads DEM is missing CRS metadata."
                dem_crs = CRS.from_user_input(dem_dataset.crs)
                input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
                input_to_dem = Transformer.from_crs(input_crs, dem_crs, always_xy=True)
                geod = Geod(ellps="WGS84")
                profile = self._build_segment_profile(
                    feature=feature,
                    input_crs=input_crs,
                    dem_dataset=dem_dataset,
                    input_to_wgs84=input_to_wgs84,
                    input_to_dem=input_to_dem,
                    geod=geod,
                )
        except (RasterioIOError, ValueError) as exc:
            return None, str(exc)

        return profile, None

    @staticmethod
    def _derive_routing_mode_hint(properties: Mapping[str, Any]) -> str:
        routing_eligibility = str(properties.get("_roads_routing_eligibility") or "").strip()
        chn_lowpoint = properties.get("topaz_id_chn_lowpoint")
        hill_lowpoint = properties.get("topaz_id_hill_lowpoint")
        if chn_lowpoint is not None and hill_lowpoint is not None:
            return "channel_associated"
        if routing_eligibility == "non_channel_routable":
            return "non_channel_routed"
        if routing_eligibility:
            return routing_eligibility
        return "unknown"

    def query_map_segments_geojson(self) -> Dict[str, Any]:
        payload = self._load_prepared_segments_geojson()
        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        attribute_field_map = self._normalize_attribute_field_map(
            params.get("attribute_field_map"),
            known_fields=None,
        )

        features_raw = payload.get("features", [])
        features_out: List[Dict[str, Any]] = []
        for feature_index, feature in enumerate(features_raw):
            if not isinstance(feature, Mapping):
                continue
            geometry = feature.get("geometry")
            properties_raw = feature.get("properties")
            properties: Dict[str, Any] = dict(properties_raw) if isinstance(properties_raw, Mapping) else {}
            segment_id = self._segment_key(feature, fallback_index=feature_index)
            properties["segment_id"] = segment_id
            design, _ = self._resolve_design_for_feature(
                properties=properties,
                attribute_field_map=attribute_field_map,
            )
            if isinstance(design, str) and design:
                properties["design"] = design
            properties["routing_mode_hint"] = self._derive_routing_mode_hint(properties)
            properties["non_channel_routable"] = self._is_truthy_property(properties.get("_roads_non_channel_routable"))
            features_out.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties,
                }
            )

        response_payload: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features_out,
        }
        if isinstance(payload.get("name"), str) and payload.get("name"):
            response_payload["name"] = payload["name"]
        self._append_roads_log(
            "query",
            "query_map_segments_geojson",
            {
                "feature_count": len(features_out),
                "roads_monotonic_geojson_relpath": os.path.relpath(self.roads_monotonic_geojson_path, self.wd),
            },
        )
        return response_payload

    def query_segment_detail(self, segment_id: str) -> Dict[str, Any]:
        segment_key = str(segment_id or "").strip()
        if not segment_key:
            raise ValueError("segment_id is required.")

        payload = self._load_prepared_segments_geojson()
        feature = self._find_segment_feature(payload, segment_id=segment_key)
        if feature is None:
            raise KeyError(f"Road segment {segment_key!r} was not found in prepared roads artifacts.")

        properties_raw = feature.get("properties")
        properties: Dict[str, Any] = dict(properties_raw) if isinstance(properties_raw, Mapping) else {}
        properties["segment_id"] = segment_key

        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        attribute_field_map = self._normalize_attribute_field_map(
            params.get("attribute_field_map"),
            known_fields=None,
        )

        warning_counts: Counter[str] = Counter()
        warning_examples: List[Dict[str, Any]] = []
        design, design_source_key = self._resolve_design_for_feature(
            properties=properties,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
            segment_id=segment_key,
        )

        resolved_inputs: Optional[Dict[str, Any]] = None
        if design is not None:
            resolved_inputs = self._resolve_segment_run_inputs(
                properties=properties,
                params=params,
                segment_id=segment_key,
                design=design,
                warning_counts=warning_counts,
                warning_examples=warning_examples,
                warning_limit=DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT,
            )
            resolved_inputs["resolution_sources"]["design"] = (
                "mapped_primary" if design_source_key == attribute_field_map.get("design") else "segment_property"
            )

        execution_records = self._load_segment_execution_manifest()
        execution_record = execution_records.get(segment_key)
        if not isinstance(execution_record, Mapping):
            execution_record = {}

        profile_values: Dict[str, Optional[float]] = {
            "segment_length_m": self._as_float_or_none(execution_record.get("segment_length_m")),
            "slope_pct_raw": self._as_float_or_none(execution_record.get("slope_pct_raw")),
            "slope_pct_clamped": self._as_float_or_none(execution_record.get("slope_pct_clamped")),
            "elevation_high_m": self._as_float_or_none(execution_record.get("elevation_high_m")),
            "elevation_low_m": self._as_float_or_none(execution_record.get("elevation_low_m")),
        }
        profile_error: Optional[str] = None
        if all(value is None for value in profile_values.values()) and design is not None:
            computed_profile, profile_error = self._build_segment_profile_for_query(
                feature=feature,
                params=params,
            )
            if computed_profile is not None:
                profile_values = {
                    "segment_length_m": self._as_float_or_none(computed_profile.get("segment_length_m")),
                    "slope_pct_raw": self._as_float_or_none(computed_profile.get("raw_slope_pct")),
                    "slope_pct_clamped": self._as_float_or_none(computed_profile.get("slope_pct")),
                    "elevation_high_m": self._as_float_or_none(computed_profile.get("elevation_high_m")),
                    "elevation_low_m": self._as_float_or_none(computed_profile.get("elevation_low_m")),
                }

        topaz_id_chn_lowpoint = self._as_int_or_none(
            execution_record.get("topaz_id_chn_lowpoint", properties.get("topaz_id_chn_lowpoint"))
        )
        topaz_id_hill_lowpoint = self._as_int_or_none(
            execution_record.get("topaz_id_hill_lowpoint", properties.get("topaz_id_hill_lowpoint"))
        )
        routing_eligibility = str(
            execution_record.get("routing_eligibility")
            or properties.get("_roads_routing_eligibility")
            or ""
        )
        routing_mode = str(execution_record.get("routing_mode") or self._derive_routing_mode_hint(properties))
        non_channel_routable = self._is_truthy_property(properties.get("_roads_non_channel_routable"))
        if routing_mode == "non_channel_routed":
            non_channel_routable = True

        result: Dict[str, Any] = {
            "segment_id": segment_key,
            "design": str(execution_record.get("design") or (resolved_inputs or {}).get("design") or design or ""),
            "surface": str(execution_record.get("surface") or (resolved_inputs or {}).get("surface") or ""),
            "traffic": str(execution_record.get("traffic") or (resolved_inputs or {}).get("traffic") or ""),
            "soil_texture": str(
                execution_record.get("soil_texture") or (resolved_inputs or {}).get("soil_texture") or ""
            ),
            "rfg_pct": self._as_float_or_none(execution_record.get("rfg_pct", (resolved_inputs or {}).get("rfg_pct"))),
            "road_width_m": self._as_float_or_none(
                execution_record.get("road_width_m", (resolved_inputs or {}).get("road_width_m"))
            ),
            "segment_length_m": profile_values["segment_length_m"],
            "slope_pct_raw": profile_values["slope_pct_raw"],
            "slope_pct_clamped": profile_values["slope_pct_clamped"],
            "elevation_high_m": profile_values["elevation_high_m"],
            "elevation_low_m": profile_values["elevation_low_m"],
            "topaz_id_chn_lowpoint": topaz_id_chn_lowpoint,
            "topaz_id_hill_lowpoint": topaz_id_hill_lowpoint,
            "routing_eligibility": routing_eligibility,
            "routing_mode": routing_mode,
            "channel_associated": routing_mode == "channel_associated",
            "non_channel_routable": bool(non_channel_routable),
            "target_hillslope_wepp_id": self._as_int_or_none(execution_record.get("target_hillslope_wepp_id")),
            "segment_run_id": self._as_int_or_none(execution_record.get("segment_run_id")),
            "execution_status": str(execution_record.get("status") or ""),
            "buffer_length_m": self._as_float_or_none(
                execution_record.get("buffer_length_m", properties.get("buffer_length_m"))
            ),
            "buffer_slope_pct": self._as_float_or_none(
                execution_record.get("buffer_slope_pct", properties.get("buffer_slope_pct"))
            ),
            "fill_length_m": self._as_float_or_none(
                execution_record.get("fill_length_m", (resolved_inputs or {}).get("fill_length_m", properties.get("fill_length_m")))
            ),
            "fill_slope_pct": self._as_float_or_none(
                execution_record.get("fill_slope_pct", (resolved_inputs or {}).get("fill_slope_pct", properties.get("fill_slope_pct")))
            ),
            "trace_path_length_m": self._as_float_or_none(execution_record.get("trace_path_length_m")),
            "trace_mean_slope": self._as_float_or_none(execution_record.get("trace_mean_slope")),
            "trace_drop_m": self._as_float_or_none(execution_record.get("trace_drop_m")),
            "trace_termination_reason": str(execution_record.get("trace_termination_reason") or ""),
            "resolution_sources": dict((resolved_inputs or {}).get("resolution_sources", {})),
            "mapping_warning_counts": dict(sorted(warning_counts.items())),
            "mapping_warning_examples": warning_examples,
            "design_source_key": design_source_key,
            "roads_params_signature": self._params_signature(params),
            "profile_error": profile_error,
            "feature_properties": properties,
        }
        self._append_roads_log(
            "query",
            "query_segment_detail",
            {
                "segment_id": segment_key,
                "routing_mode": result["routing_mode"],
                "execution_status": result["execution_status"] or "not_run",
                "profile_error": profile_error,
            },
        )
        return result

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
            params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
            attribute_field_map = self._normalize_attribute_field_map(
                params.get("attribute_field_map"),
                known_fields=None,
            )
            design_property_keys = self._dedupe_keys(
                (
                    [attribute_field_map.get("design")] if attribute_field_map.get("design") else []
                )
                + list(LEGACY_DESIGN_KEYS)
            )
            warning_limit = DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT
            configured_input_crs = str(params.get("input_crs") or "EPSG:4326")
            try:
                CRS.from_user_input(configured_input_crs)
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
            convert_kwargs = {
                "input_geojson_path": staged_path,
                "dem_path": raster_paths["dem_path"],
                "output_geojson_path": self.roads_monotonic_geojson_path,
                "low_points_output_geojson_path": self.roads_low_points_geojson_path,
                "input_crs": input_crs_value,
                "sample_step_m": params.get("sample_step_m"),
                "tolerance_m": float(params.get("tolerance_m", 0.5)),
                "channel_raster_path": raster_paths["channel_raster_path"],
                "topaz_id_raster_path": raster_paths["topaz_id_raster_path"],
                "design_property_keys": design_property_keys,
            }
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
                        "reason": str(exc),
                    },
                )
                convert_kwargs["input_crs"] = dem_input_crs
                summary = convert_geojson_file_to_monotonic_segments(**convert_kwargs)
                input_crs_value = dem_input_crs
                input_crs_source = "dem_crs_fallback"
            params["input_crs"] = input_crs_value

            segment_payload = json.loads(Path(self.roads_monotonic_geojson_path).read_text(encoding="utf-8"))
            features = segment_payload.get("features", [])
            eligible_segments = 0
            mapped_candidates = 0
            decision_counts: Counter[str] = Counter()
            routing_eligibility_counts: Counter[str] = Counter()
            warning_counts: Counter[str] = Counter()
            warning_examples: List[Dict[str, Any]] = []
            for feature_index, feature in enumerate(features):
                properties = feature.get("properties", {}) if isinstance(feature, Mapping) else {}
                segment_id = self._segment_key(feature, fallback_index=feature_index)
                design_value, _ = self._resolve_design_for_feature(
                    properties=properties,
                    attribute_field_map=attribute_field_map,
                    warning_counts=warning_counts,
                    warning_examples=warning_examples,
                    warning_limit=warning_limit,
                    segment_id=segment_id,
                )
                if design_value is None:
                    continue
                eligible_segments += 1
                decision_key = str(properties.get("_roads_lowpoint_decision") or "unknown")
                decision_counts[decision_key] += 1
                routing_key = str(properties.get("_roads_routing_eligibility") or "unknown")
                routing_eligibility_counts[routing_key] += 1
                if (
                    properties.get("topaz_id_chn_lowpoint") is not None
                    and properties.get("topaz_id_hill_lowpoint") is not None
                ):
                    mapped_candidates += 1

            channel_associated_count = int(routing_eligibility_counts.get("channel_associated", 0))
            non_channel_routable_count = int(routing_eligibility_counts.get("non_channel_routable", 0))
            non_routable_count = int(routing_eligibility_counts.get("non_routable", 0))
            prepare_summary = {
                "input_feature_count": int(summary.input_feature_count),
                "output_feature_count": int(summary.output_feature_count),
                "split_feature_count": int(summary.split_feature_count),
                "low_point_feature_count": int(summary.low_point_feature_count),
                "sample_step_m": float(summary.sample_step_m),
                "tolerance_m": float(summary.tolerance_m),
                "eligible_segment_count": eligible_segments,
                "eligible_with_lowpoint_ids": mapped_candidates,
                "eligible_channel_associated_count": channel_associated_count,
                "eligible_non_channel_routable_count": non_channel_routable_count,
                "eligible_non_routable_count": non_routable_count,
                "eligible_lowpoint_decision_counts": dict(sorted(decision_counts.items())),
                "eligible_routing_eligibility_counts": dict(sorted(routing_eligibility_counts.items())),
                "mapping_warning_count": int(sum(warning_counts.values())),
                "mapping_warning_counts": dict(sorted(warning_counts.items())),
                "mapping_warning_examples": warning_examples,
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
                "configured_input_crs": configured_input_crs,
                "source_crs": source_crs,
                "input_crs_source": input_crs_source,
                "design_property_keys": list(design_property_keys),
                "attribute_field_map": dict(attribute_field_map),
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
                    "eligible_channel_associated_count": channel_associated_count,
                    "eligible_non_channel_routable_count": non_channel_routable_count,
                    "eligible_lowpoint_decision_counts": dict(sorted(decision_counts.items())),
                    "mapping_warning_count": int(sum(warning_counts.values())),
                    "summary_relpath": prepare_summary["summary_relpath"],
                },
            )
            if warning_counts:
                self._append_roads_log(
                    "prepare",
                    "mapping_warnings_detected",
                    {
                        "mapping_warning_count": int(sum(warning_counts.values())),
                        "mapping_warning_codes": sorted(warning_counts.keys()),
                    },
                )

            with self.locked():
                self._roads_params = params
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
        for key in keys:
            value = properties.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None


    @staticmethod
    def _has_non_empty_property(properties: Mapping[str, Any], keys: Iterable[str]) -> bool:
        return Roads._first_non_empty_property(properties, keys) is not None

    @classmethod
    def _missing_outslope_unrutted_required_fields(cls, properties: Mapping[str, Any]) -> List[str]:
        required_fields = {
            "fill_length_m": ("FILL_LENGTH_M", "fill_length_m", "FILL_LEN_M", "fill_len_m"),
            "fill_slope_pct": (
                "FILL_SLOPE_PCT",
                "fill_slope_pct",
                "FILL_SLOPE",
                "fill_slope",
                "FILL_GRADE_PCT",
                "fill_grade_pct",
            ),
            "buffer_length_m": ("BUFFER_LENGTH_M", "buffer_length_m", "BUFFER_LEN_M", "buffer_len_m"),
            "buffer_slope_pct": ("BUFFER_SLOPE_PCT", "buffer_slope_pct", "BUFFER_SLOPE", "buffer_slope"),
        }
        missing: List[str] = []
        for field_name, keys in required_fields.items():
            if not cls._has_non_empty_property(properties, keys):
                missing.append(field_name)
        return missing

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

    @staticmethod
    def _normalize_traffic_value(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        normalized = TRAFFIC_ALIASES.get(text.lower().replace(" ", ""))
        if normalized is not None:
            return normalized
        condition_normalized = CONDITION_TRAFFIC_MAP.get(text.lower())
        if condition_normalized is not None:
            return condition_normalized
        return None

    def _normalize_traffic(self, value: Optional[str], condition: Optional[str], default_value: str) -> str:
        from_value = self._normalize_traffic_value(value)
        if from_value is not None:
            return from_value
        from_condition = self._normalize_traffic_value(condition)
        if from_condition is not None:
            return from_condition
        return default_value

    def _normalize_soil_texture(self, value: Optional[str], default_value: str) -> str:
        if value is None:
            return default_value
        normalized = SOIL_TEXTURE_ALIASES.get(value.strip().lower())
        if normalized is None:
            return default_value
        return normalized

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
        mapped_surface_key = attribute_field_map.get("surface")
        if mapped_surface_key:
            mapped_raw, _ = self._first_non_empty_property_with_key(properties, (mapped_surface_key,))
            if mapped_raw is None:
                if mapped_surface_key not in LEGACY_SURFACE_KEYS:
                    self._collect_warning(
                        warning_counts,
                        warning_examples,
                        code="surface_mapped_primary_missing",
                        message=(
                            f"Mapped surface field {mapped_surface_key!r} is missing/empty; "
                            "using configured surface default value."
                        ),
                        limit=warning_limit,
                        segment_id=segment_id,
                        field_name=mapped_surface_key,
                    )
                return default_value, "mapped_default_value"
            normalized_mapped = SURFACE_ALIASES.get(mapped_raw.strip().lower())
            if normalized_mapped is not None:
                return normalized_mapped, "mapped_primary"
            if mapped_surface_key not in LEGACY_SURFACE_KEYS:
                self._collect_warning(
                    warning_counts,
                    warning_examples,
                    code="surface_mapped_primary_invalid",
                    message=(
                        f"Mapped surface field {mapped_surface_key!r} value {mapped_raw!r} is not recognized; "
                        "using configured surface default value."
                    ),
                    limit=warning_limit,
                    segment_id=segment_id,
                    field_name=mapped_surface_key,
                )
            return default_value, "mapped_default_value"

        for key in LEGACY_SURFACE_KEYS:
            raw_value, _ = self._first_non_empty_property_with_key(properties, (key,))
            if raw_value is None:
                continue
            normalized = SURFACE_ALIASES.get(raw_value.strip().lower())
            if normalized is not None:
                return normalized, "segment_property"
        return default_value, "roads_default"

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
        mapped_traffic_key = attribute_field_map.get("traffic")
        if mapped_traffic_key:
            mapped_raw, _ = self._first_non_empty_property_with_key(properties, (mapped_traffic_key,))
            if mapped_raw is None:
                if mapped_traffic_key not in LEGACY_TRAFFIC_KEYS:
                    self._collect_warning(
                        warning_counts,
                        warning_examples,
                        code="traffic_mapped_primary_missing",
                        message=(
                            f"Mapped traffic field {mapped_traffic_key!r} is missing/empty; "
                            "using configured traffic default value."
                        ),
                        limit=warning_limit,
                        segment_id=segment_id,
                        field_name=mapped_traffic_key,
                    )
                return default_value, "mapped_default_value"
            normalized_mapped = self._normalize_traffic_value(mapped_raw)
            if normalized_mapped is not None:
                return normalized_mapped, "mapped_primary"
            if mapped_traffic_key not in LEGACY_TRAFFIC_KEYS:
                self._collect_warning(
                    warning_counts,
                    warning_examples,
                    code="traffic_mapped_primary_invalid",
                    message=(
                        f"Mapped traffic field {mapped_traffic_key!r} value {mapped_raw!r} is not recognized; "
                        "using configured traffic default value."
                    ),
                    limit=warning_limit,
                    segment_id=segment_id,
                    field_name=mapped_traffic_key,
                )
            return default_value, "mapped_default_value"

        for key in LEGACY_TRAFFIC_KEYS:
            raw_value, _ = self._first_non_empty_property_with_key(properties, (key,))
            if raw_value is None:
                continue
            normalized = self._normalize_traffic_value(raw_value)
            if normalized is not None:
                return normalized, "segment_property_or_condition"
        return default_value, "roads_default"

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
        if design not in ELIGIBLE_ROADS_DESIGNS:
            raise ValueError(f"Unsupported Roads design for segment execution: {design!r}")

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
        default_fill_length_m = float(params.get("fill_length_default_m", 30.0))
        if default_fill_length_m <= 0:
            default_fill_length_m = 30.0
        default_fill_slope_pct = self._as_float_or_none(params.get("fill_slope_default_pct"))
        if default_fill_slope_pct is None:
            default_fill_slope_pct = 10.0
        default_fill_slope_pct = self._clamp_percent_slope(float(default_fill_slope_pct))

        attribute_field_map = self._normalize_attribute_field_map(
            params.get("attribute_field_map"),
            known_fields=None,
        )
        resolved_surface, surface_source = self._resolve_surface_for_feature(
            properties=properties,
            default_value=default_surface,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
        )
        resolved_traffic, traffic_source = self._resolve_traffic_for_feature(
            properties=properties,
            default_value=default_traffic,
            attribute_field_map=attribute_field_map,
            warning_counts=warning_counts,
            warning_examples=warning_examples,
            warning_limit=warning_limit,
            segment_id=segment_id,
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
        fill_length_raw = self._first_non_empty_property(
            properties,
            ("FILL_LENGTH_M", "fill_length_m", "FILL_LEN_M", "fill_len_m"),
        )
        fill_slope_raw = self._first_non_empty_property(
            properties,
            ("FILL_SLOPE_PCT", "fill_slope_pct", "FILL_SLOPE", "fill_slope", "FILL_GRADE_PCT", "fill_grade_pct"),
        )

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

        fill_length_m = self._coerce_float(fill_length_raw)
        fill_length_source = "segment_property"
        if fill_length_m is None or fill_length_m <= 0:
            fill_length_m = default_fill_length_m
            fill_length_source = "roads_default"

        fill_slope_pct = self._coerce_float(fill_slope_raw)
        fill_slope_source = "segment_property"
        if fill_slope_pct is None or fill_slope_pct <= 0:
            fill_slope_pct = default_fill_slope_pct
            fill_slope_source = "roads_default"
        fill_slope_pct = self._clamp_percent_slope(float(fill_slope_pct))

        return {
            "design": design,
            "surface": resolved_surface,
            "traffic": resolved_traffic,
            "soil_texture": resolved_texture,
            "rfg_pct": float(rfg_pct),
            "road_width_m": float(road_width_m),
            "fill_length_m": float(fill_length_m),
            "fill_slope_pct": float(fill_slope_pct),
            "resolution_sources": {
                "surface": surface_source,
                "traffic": traffic_source,
                "soil_texture": "segment_property" if texture_raw else "roads_default",
                "rfg_pct": "segment_property" if rfg_raw else "roads_default",
                "road_width_m": "segment_property" if width_raw else "roads_default",
                "fill_length_m": fill_length_source,
                "fill_slope_pct": fill_slope_source,
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
        hillslope_geojson_path = self._normalize_existing_path(getattr(self.watershed_instance, "subwta_shp", None))
        if hillslope_geojson_path is None:
            raise FileNotFoundError("Roads outslope_unrutted replacement requires watershed subcatchments WGS GeoJSON.")

        payload = json.loads(Path(hillslope_geojson_path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or payload.get("type") != "FeatureCollection":
            raise ValueError("Watershed subcatchments payload is malformed; expected FeatureCollection.")

        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("Watershed subcatchments payload is missing a features array.")

        hillslopes: List[Dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, Mapping):
                continue
            properties = feature.get("properties")
            geometry_payload = feature.get("geometry")
            if not isinstance(properties, Mapping) or not isinstance(geometry_payload, Mapping):
                continue

            topaz_id_hill = self._resolve_topaz_id_from_properties(properties)
            if topaz_id_hill is None or not _is_hillslope_topaz_id(topaz_id_hill):
                continue

            geometry = shape(geometry_payload)
            if geometry.is_empty:
                continue

            hillslopes.append(
                {
                    "topaz_id_hill": int(topaz_id_hill),
                    "geometry_wgs84": geometry,
                }
            )

        if not hillslopes:
            raise ValueError("No hillslope geometries were resolved from watershed subcatchments.")

        return hillslopes

    def _select_outslope_unrutted_hillslope_segments(
        self,
        *,
        pending_segments: Sequence[Dict[str, Any]],
        input_crs: CRS,
        geod: Geod,
        top2wepp: Mapping[int, Any],
    ) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
        inclusion_ratio_threshold = 0.60
        overlap_length_min_m = 10.0
        max_crossings_per_hillslope = 3

        input_to_wgs84 = Transformer.from_crs(input_crs, CRS.from_epsg(4326), always_xy=True)
        hillslope_geometries = self._load_hillslope_geometries_wgs84()

        hillslope_records: Dict[int, Dict[str, Any]] = {}
        candidate_status_by_id: Dict[str, Dict[str, Any]] = {}
        included_pre_cap_by_hillslope: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        for pending in pending_segments:
            source_segment_id = str(pending["segment_id"])
            feature = pending["feature"]
            properties = pending["properties"]
            geometry_payload = feature.get("geometry") if isinstance(feature, Mapping) else None
            if not isinstance(geometry_payload, Mapping):
                continue

            geometry_input = shape(geometry_payload)
            if geometry_input.is_empty:
                continue

            geometry_wgs84 = shapely_transform(input_to_wgs84.transform, geometry_input)
            if geometry_wgs84.is_empty:
                continue

            for hillslope in hillslope_geometries:
                topaz_id_hill = int(hillslope["topaz_id_hill"])
                hillslope_geometry_wgs84 = hillslope["geometry_wgs84"]
                overlap_geometry = geometry_wgs84.intersection(hillslope_geometry_wgs84)
                overlap_length_m = self._geometry_line_length_m_wgs84(overlap_geometry, geod=geod)
                if overlap_length_m <= 0.0:
                    continue

                try:
                    hillslope_width_m = float(self.watershed_instance.hillslope_width(topaz_id_hill))
                except Exception:
                    hillslope_width_m = 0.0
                inclusion_ratio = float(overlap_length_m / hillslope_width_m) if hillslope_width_m > 0 else 0.0

                segment_hillslope_id = self._build_segment_hillslope_id(source_segment_id, topaz_id_hill)
                hillslope_wepp_id = self._as_int_or_none(top2wepp.get(int(topaz_id_hill)))

                record = hillslope_records.setdefault(
                    topaz_id_hill,
                    {
                        "topaz_id_hill": int(topaz_id_hill),
                        "wepp_id_hill": int(hillslope_wepp_id) if hillslope_wepp_id is not None else None,
                        "segment_ids_included": [],
                        "segment_ids_excluded": [],
                        "segment_ids_capped": [],
                        "inclusion_ratio_by_segment": {},
                        "top_ofe_compensation_m": 0.0,
                        "area_error_before_compensation_m2": 0.0,
                        "area_error_after_compensation_m2": 0.0,
                    },
                )
                record["inclusion_ratio_by_segment"][segment_hillslope_id] = float(inclusion_ratio)

                status = "included"
                if overlap_length_m < overlap_length_min_m:
                    status = "excluded_overlap_length_min"
                elif inclusion_ratio < inclusion_ratio_threshold:
                    status = "excluded_inclusion_ratio"

                candidate_payload = {
                    "segment_hillslope_id": segment_hillslope_id,
                    "source_segment_id": source_segment_id,
                    "topaz_id_hill": int(topaz_id_hill),
                    "hillslope_wepp_id": int(hillslope_wepp_id) if hillslope_wepp_id is not None else None,
                    "overlap_length_m": float(overlap_length_m),
                    "hillslope_width_m": float(hillslope_width_m),
                    "inclusion_ratio": float(inclusion_ratio),
                    "overlap_geometry_wgs84": overlap_geometry,
                    "feature": feature,
                    "properties": properties,
                }
                candidate_status_by_id[segment_hillslope_id] = {
                    **candidate_payload,
                    "status": status,
                }

                if status == "included" and hillslope_wepp_id is not None:
                    included_pre_cap_by_hillslope[int(topaz_id_hill)].append(candidate_payload)
                else:
                    record["segment_ids_excluded"].append(segment_hillslope_id)

        selected_by_wepp: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        capped_segment_count = 0

        for topaz_id_hill, candidates in included_pre_cap_by_hillslope.items():
            candidates_sorted = sorted(
                candidates,
                key=lambda row: (-float(row["overlap_length_m"]), str(row["segment_hillslope_id"])),
            )
            record = hillslope_records[topaz_id_hill]

            for index, candidate in enumerate(candidates_sorted):
                segment_hillslope_id = str(candidate["segment_hillslope_id"])
                if index < max_crossings_per_hillslope:
                    record["segment_ids_included"].append(segment_hillslope_id)
                    wepp_id_hill = self._as_int_or_none(candidate.get("hillslope_wepp_id"))
                    if wepp_id_hill is not None:
                        selected_by_wepp[int(wepp_id_hill)].append(candidate)
                else:
                    capped_segment_count += 1
                    record["segment_ids_capped"].append(segment_hillslope_id)
                    record["segment_ids_excluded"].append(segment_hillslope_id)
                    candidate_status_by_id[segment_hillslope_id]["status"] = "excluded_cap_limit"

        included_segment_count = 0
        excluded_segment_count = 0
        for candidate in candidate_status_by_id.values():
            status = str(candidate.get("status") or "")
            if status == "included":
                included_segment_count += 1
            elif status.startswith("excluded_") and status != "excluded_cap_limit":
                excluded_segment_count += 1

        diagnostics = {
            "outslope_unrutted_targeted_hillslope_count": int(
                sum(1 for value in selected_by_wepp.values() if value)
            ),
            "outslope_unrutted_included_segment_count": int(included_segment_count),
            "outslope_unrutted_excluded_segment_count": int(excluded_segment_count),
            "outslope_unrutted_capped_segment_count": int(capped_segment_count),
            "outslope_unrutted_hillslope_records": [
                hillslope_records[topaz_id]
                for topaz_id in sorted(hillslope_records)
            ],
        }

        return selected_by_wepp, diagnostics, candidate_status_by_id

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

    def _derive_buffer_profile_from_trace(self, trace_result: Mapping[str, Any]) -> Dict[str, float]:
        path_length_m = self._as_float_or_none(trace_result.get("path_length_m"))
        if path_length_m is None or path_length_m <= 0:
            raise ValueError("Trace result is missing a positive path_length_m for routed contributor assembly.")

        slope_candidates: List[float] = []
        mean_slope = self._as_float_or_none(trace_result.get("mean_slope"))
        if mean_slope is not None and np.isfinite(mean_slope):
            slope_candidates.append(float(mean_slope))

        drop_m = self._as_float_or_none(trace_result.get("drop_m"))
        if drop_m is not None and np.isfinite(drop_m) and path_length_m > 0:
            slope_candidates.append(float(drop_m) / float(path_length_m))

        segment_slope = trace_result.get("segment_slope")
        if isinstance(segment_slope, list):
            for raw in segment_slope:
                value = self._as_float_or_none(raw)
                if value is None or not np.isfinite(value):
                    continue
                slope_candidates.append(float(value))

        positive_candidates = [value for value in slope_candidates if value > 0.0]
        slope_fraction = max(positive_candidates) if positive_candidates else 0.001
        slope_pct = self._clamp_percent_slope(slope_fraction * 100.0)
        return {
            "buffer_length_m": max(0.3, float(path_length_m)),
            "buffer_slope_pct": float(slope_pct),
            "buffer_slope_fraction": float(slope_pct / 100.0),
        }

    def _derive_buffer_profile_from_feature_or_defaults(
        self,
        *,
        properties: Mapping[str, Any],
        road_profile: Mapping[str, Any],
    ) -> Dict[str, Any]:
        buffer_length_raw = self._first_non_empty_property(
            properties,
            ("BUFFER_LENGTH_M", "buffer_length_m", "BUFFER_LEN_M", "buffer_len_m"),
        )
        buffer_slope_raw = self._first_non_empty_property(
            properties,
            ("BUFFER_SLOPE_PCT", "buffer_slope_pct", "BUFFER_SLOPE", "buffer_slope"),
        )

        buffer_length_source = "segment_property"
        buffer_length_m = self._coerce_float(buffer_length_raw)
        if buffer_length_m is None or buffer_length_m <= 0:
            segment_length_m = self._as_float_or_none(road_profile.get("segment_length_m"))
            if segment_length_m is None or segment_length_m <= 0:
                buffer_length_m = 30.0
            else:
                buffer_length_m = max(0.3, min(float(segment_length_m), 30.0))
            buffer_length_source = "derived_default"

        buffer_slope_source = "segment_property"
        buffer_slope_pct = self._coerce_float(buffer_slope_raw)
        if buffer_slope_pct is None or buffer_slope_pct <= 0:
            road_slope_pct = self._as_float_or_none(road_profile.get("slope_pct"))
            if road_slope_pct is None or road_slope_pct <= 0:
                buffer_slope_pct = 6.0
            else:
                buffer_slope_pct = float(road_slope_pct) * 0.5
            buffer_slope_source = "derived_default"

        buffer_slope_pct = self._clamp_percent_slope(float(buffer_slope_pct))
        return {
            "buffer_length_m": max(0.3, float(buffer_length_m)),
            "buffer_slope_pct": float(buffer_slope_pct),
            "buffer_slope_fraction": float(buffer_slope_pct / 100.0),
            "buffer_length_source": buffer_length_source,
            "buffer_slope_source": buffer_slope_source,
        }

    @staticmethod
    def _derive_fill_profile_from_inputs(*, fill_length_m: float, fill_slope_pct: float) -> Dict[str, float]:
        fill_length = max(0.3, float(fill_length_m))
        slope_pct = max(0.1, min(40.0, float(fill_slope_pct)))
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
        outslope_fraction = 0.04
        longitudinal_fraction = max(0.001, float(road_slope_pct) / 100.0)
        road_slope_fraction = (outslope_fraction**2.0) + (longitudinal_fraction**2.0)
        scale = max(road_slope_fraction / outslope_fraction, 1e-6)

        sim_length_m = max(1.0, min(300.0, float(road_length_m) * scale))
        sim_width_m = max(0.3, min(100.0, float(road_width_m) / scale))

        return {
            "sim_length_m": float(sim_length_m),
            "sim_width_m": float(sim_width_m),
            "road_slope_fraction": float(road_slope_fraction),
            "road_slope_pct": float(road_slope_fraction * 100.0),
            "geometry_scale": float(scale),
        }

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
        road_slope_fraction = float(road_slope_pct) / 100.0
        buffer_slope_fraction = float(buffer_slope_pct) / 100.0
        content = [
            "97.3",
            "2",
            f"180.0 {float(width_m):.3f}",
            f"2 {float(road_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
            f"3 {float(buffer_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 0.05, {buffer_slope_fraction:.6f} 1.00, {buffer_slope_fraction:.6f}",
        ]
        path.write_text("\n".join(content) + "\n", encoding="utf-8")

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
        road_slope_fraction = float(road_slope_pct) / 100.0
        fill_slope_fraction = float(fill_slope_pct) / 100.0
        buffer_slope_fraction = float(buffer_slope_pct) / 100.0
        content = [
            "97.3",
            "3",
            f"180.0 {float(width_m):.3f}",
            f"2 {float(road_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
            f"3 {float(fill_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
            f"3 {float(buffer_length_m):.3f}",
            f"0.00, {fill_slope_fraction:.6f} 0.05, {buffer_slope_fraction:.6f} 1.00, {buffer_slope_fraction:.6f}",
        ]
        path.write_text("\n".join(content) + "\n", encoding="utf-8")

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
        top_landuse_slope_fraction = float(top_landuse_slope_pct) / 100.0
        road_slope_fraction = float(road_slope_pct) / 100.0
        fill_slope_fraction = float(fill_slope_pct) / 100.0
        content = [
            "97.3",
            "3",
            f"180.0 {float(width_m):.3f}",
            f"2 {float(top_landuse_length_m):.3f}",
            f"0.00, {top_landuse_slope_fraction:.6f} 1.00, {top_landuse_slope_fraction:.6f}",
            f"3 {float(road_length_m):.3f}",
            f"0.00, {top_landuse_slope_fraction:.6f} 0.05, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
            f"3 {float(fill_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
        ]
        path.write_text("\n".join(content) + "\n", encoding="utf-8")

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
        top_landuse_slope_fraction = float(top_landuse_slope_pct) / 100.0
        road_slope_fraction = float(road_slope_pct) / 100.0
        fill_slope_fraction = float(fill_slope_pct) / 100.0
        bottom_landuse_slope_fraction = float(bottom_landuse_slope_pct) / 100.0
        content = [
            "97.3",
            "4",
            f"180.0 {float(width_m):.3f}",
            f"2 {float(top_landuse_length_m):.3f}",
            f"0.00, {top_landuse_slope_fraction:.6f} 1.00, {top_landuse_slope_fraction:.6f}",
            f"3 {float(road_length_m):.3f}",
            f"0.00, {top_landuse_slope_fraction:.6f} 0.05, {road_slope_fraction:.6f} 1.00, {road_slope_fraction:.6f}",
            f"3 {float(fill_length_m):.3f}",
            f"0.00, {road_slope_fraction:.6f} 0.05, {fill_slope_fraction:.6f} 1.00, {fill_slope_fraction:.6f}",
            f"3 {float(bottom_landuse_length_m):.3f}",
            f"0.00, {fill_slope_fraction:.6f} 0.05, {bottom_landuse_slope_fraction:.6f} 1.00, {bottom_landuse_slope_fraction:.6f}",
        ]
        path.write_text("\n".join(content) + "\n", encoding="utf-8")

    @staticmethod
    def _extract_ofe_from_nycrop_comment(line: str) -> Optional[int]:
        match = re.search(r"OFE\s*:\s*(\d+)", line)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

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
        if not ofe_order:
            raise ValueError("ofe_order must not be empty")
        if any(index not in {1, 2, 3} for index in ofe_order):
            raise ValueError("ofe_order entries must be one of 1 (road), 2 (fill), or 3 (hill/forest).")

        nofe = len(ofe_order)
        lines = template_path.read_text(encoding="utf-8").splitlines()
        out: List[str] = []
        i = 0
        initial_indices_rewritten = False

        while i < len(lines):
            line = lines[i]

            if "# number of OFEs" in line:
                out.append(self._replace_leading_int(line, nofe))
                i += 1
                continue

            if "# `nofe'" in line:
                out.append(self._replace_leading_int(line, nofe))
                i += 1
                continue

            if "# `Initial Conditions indx'" in line and not initial_indices_rewritten:
                original_index_lines: List[str] = []
                while i < len(lines) and "# `Initial Conditions indx'" in lines[i]:
                    original_index_lines.append(lines[i])
                    i += 1

                if not original_index_lines:
                    continue

                for scenario_idx in ofe_order:
                    template_line = original_index_lines[min(len(original_index_lines) - 1, scenario_idx - 1)]
                    out.append(self._replace_leading_int(template_line, int(scenario_idx)))

                initial_indices_rewritten = True
                continue

            ofe_from_comment = self._extract_ofe_from_nycrop_comment(line)
            if ofe_from_comment is not None and (i + 1) < len(lines) and "# `YEAR indx'" in lines[i + 1]:
                original_pairs: List[Tuple[int, str, str]] = []
                while i < len(lines):
                    nycrop_line = lines[i]
                    parsed_ofe = self._extract_ofe_from_nycrop_comment(nycrop_line)
                    if parsed_ofe is None:
                        break
                    if (i + 1) >= len(lines) or "# `YEAR indx'" not in lines[i + 1]:
                        break
                    year_line = lines[i + 1]
                    original_pairs.append((int(parsed_ofe), nycrop_line, year_line))
                    i += 2

                if not original_pairs:
                    continue

                pair_map = {ofe_idx: (nycrop_line, year_line) for ofe_idx, nycrop_line, year_line in original_pairs}
                fallback_pair = pair_map.get(3) or pair_map.get(1) or original_pairs[-1][1:]

                for new_ofe_pos, scenario_idx in enumerate(ofe_order, start=1):
                    nycrop_line, year_line = pair_map.get(int(scenario_idx), fallback_pair)
                    nycrop_line = re.sub(r"(OFE\s*:\s*)\d+", rf"\g<1>{int(new_ofe_pos)}", nycrop_line)
                    year_line = self._replace_leading_int(year_line, int(scenario_idx))
                    out.append(nycrop_line)
                    out.append(year_line)
                continue

            out.append(line)
            i += 1

        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

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
        if not ofe_order:
            raise ValueError("ofe_order must not be empty")
        if any(index not in {1, 2, 3} for index in ofe_order):
            raise ValueError("ofe_order entries must be one of 1 (road), 2 (fill), or 3 (hill/forest).")

        lines = template_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 10:
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
        out.append(f"{len(ofe_order)} {ksflag}")
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        ofe_pairs: List[Tuple[str, str]] = []
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                continue
            if i + 1 >= len(lines):
                raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
            ofe_pairs.append((lines[i], lines[i + 1]))
            i += 2

        if len(ofe_pairs) < 3:
            raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

        urr_ref = 95.0 if surface == "paved" else 65.0
        ufr_ref = (float(rfg_pct) + 65.0) / 2.0

        for scenario_idx in ofe_order:
            header, horizon = ofe_pairs[int(scenario_idx) - 1]
            if int(scenario_idx) == 1:
                road_tokens = shlex.split(header)
                if len(road_tokens) < 8:
                    raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
                slid, texid = road_tokens[0], road_tokens[1]
                nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
                avke = road_tokens[8] if len(road_tokens) > 8 else None

                ki_value = float(ki)
                kr_value = float(kr)
                if traffic != "high":
                    ki_value /= 4.0
                    kr_value /= 4.0

                header_line = f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
                if avke is not None:
                    header_line += f" {avke}"
            else:
                header_line = header

            horizon_line = self._replace_soil_marker(
                horizon,
                urr_ref=urr_ref,
                ufr_ref=ufr_ref,
                ubr_value=float(rfg_pct),
            )

            out.append(header_line)
            out.append(horizon_line)

        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    
    
    
    @staticmethod
    def _replace_soil_marker(
        horizon_line: str,
        *,
        urr_ref: float,
        ufr_ref: float,
        ubr_value: float,
    ) -> str:
        tokens = horizon_line.split()
        if not tokens:
            return horizon_line
        marker = tokens[-1].lower()
        if marker == "urr":
            tokens[-1] = f"{float(urr_ref):.6g}"
        elif marker == "ufr":
            tokens[-1] = f"{float(ufr_ref):.6g}"
        elif marker == "ubr":
            tokens[-1] = f"{float(ubr_value):.6g}"
        return " ".join(tokens)

    def _build_routed_two_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        lines = template_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 8:
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
        out.append(f"2 {ksflag}")
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        ofe_pairs: List[Tuple[str, str]] = []
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                continue
            if i + 1 >= len(lines):
                raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
            ofe_pairs.append((lines[i], lines[i + 1]))
            i += 2

        if len(ofe_pairs) < 3:
            raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

        road_header, road_horizon = ofe_pairs[0]
        buffer_header, buffer_horizon = ofe_pairs[2]
        road_tokens = shlex.split(road_header)
        if len(road_tokens) < 8:
            raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
        slid, texid = road_tokens[0], road_tokens[1]
        nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
        avke = road_tokens[8] if len(road_tokens) > 8 else None

        ki_value = float(ki)
        kr_value = float(kr)
        if traffic != "high":
            ki_value /= 4.0
            kr_value /= 4.0

        road_header_line = (
            f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
        )
        if avke is not None:
            road_header_line += f" {avke}"

        urr_ref = 95.0 if surface == "paved" else 65.0
        ufr_ref = (float(rfg_pct) + 65.0) / 2.0
        road_horizon_line = self._replace_soil_marker(
            road_horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )
        buffer_horizon_line = self._replace_soil_marker(
            buffer_horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )

        out.append(road_header_line)
        out.append(road_horizon_line)
        out.append(buffer_header)
        out.append(buffer_horizon_line)
        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _build_routed_three_ofe_soil_file(
        self,
        *,
        template_path: Path,
        output_path: Path,
        traffic: str,
        surface: str,
        rfg_pct: float,
    ) -> None:
        lines = template_path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 10:
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
        out.append(f"3 {ksflag}")
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        ofe_pairs: List[Tuple[str, str]] = []
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                continue
            if i + 1 >= len(lines):
                raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
            ofe_pairs.append((lines[i], lines[i + 1]))
            i += 2

        if len(ofe_pairs) < 3:
            raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

        road_header, road_horizon = ofe_pairs[0]
        fill_header, fill_horizon = ofe_pairs[1]
        buffer_header, buffer_horizon = ofe_pairs[2]

        road_tokens = shlex.split(road_header)
        if len(road_tokens) < 8:
            raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
        slid, texid = road_tokens[0], road_tokens[1]
        nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
        avke = road_tokens[8] if len(road_tokens) > 8 else None

        ki_value = float(ki)
        kr_value = float(kr)
        if traffic != "high":
            ki_value /= 4.0
            kr_value /= 4.0

        road_header_line = (
            f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
        )
        if avke is not None:
            road_header_line += f" {avke}"

        urr_ref = 95.0 if surface == "paved" else 65.0
        ufr_ref = (float(rfg_pct) + 65.0) / 2.0
        road_horizon_line = self._replace_soil_marker(
            road_horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )
        fill_horizon_line = self._replace_soil_marker(
            fill_horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )
        buffer_horizon_line = self._replace_soil_marker(
            buffer_horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )

        out.append(road_header_line)
        out.append(road_horizon_line)
        out.append(fill_header)
        out.append(fill_horizon_line)
        out.append(buffer_header)
        out.append(buffer_horizon_line)
        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    @staticmethod
    def _strip_management_scenario_block(
        lines: List[str], *, start_marker: str, end_marker: str
    ) -> List[str]:
        out: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if start_marker in line:
                while i < len(lines) and end_marker not in lines[i]:
                    i += 1
                continue
            out.append(line)
            i += 1
        return out

    def _build_routed_two_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
        lines = template_path.read_text(encoding="utf-8").splitlines()
        lines = self._strip_management_scenario_block(
            lines,
            start_marker="Plant scenario 2 of 3",
            end_marker="Plant scenario 3 of 3",
        )
        lines = self._strip_management_scenario_block(
            lines,
            start_marker="Initial Conditions scenario 2 of 3",
            end_marker="Initial Conditions scenario 3 of 3",
        )
        lines = self._strip_management_scenario_block(
            lines,
            start_marker="Yearly scenario 2 of 3",
            end_marker="Yearly scenario 3 of 3",
        )

        out: List[str] = []
        initial_condition_index_counter = 0
        skip_next_year_index = False
        remap_next_year_index = False

        for line in lines:
            if "Plant scenario 3 of 3" in line:
                line = line.replace("Plant scenario 3 of 3", "Plant scenario 2 of 2")
            elif "Initial Conditions scenario 3 of 3" in line:
                line = line.replace("Initial Conditions scenario 3 of 3", "Initial Conditions scenario 2 of 2")
            elif "Yearly scenario 3 of 3" in line:
                line = line.replace("Yearly scenario 3 of 3", "Yearly scenario 2 of 2")

            if (
                "# number of OFEs" in line
                or "# looper; number of Plant scenarios" in line
                or "# looper; number of Initial Conditions scenarios" in line
                or "# looper; number of Yearly scenarios" in line
                or "# `nofe'" in line
            ):
                line = self._replace_leading_int(line, 2)

            if "# `Initial Conditions indx'" in line:
                initial_condition_index_counter += 1
                if initial_condition_index_counter == 2:
                    continue
                if initial_condition_index_counter == 3:
                    line = self._replace_leading_int(line, 2)

            if "# `itype'" in line:
                match = re.match(r"^\s*(\d+)", line)
                if match and int(match.group(1)) == 3:
                    line = self._replace_leading_int(line, 2)

            if "# `nycrop'" in line and "OFE :" in line:
                if "OFE : 2" in line:
                    skip_next_year_index = True
                    continue
                if "OFE : 3" in line:
                    line = line.replace("OFE : 3", "OFE : 2")
                    remap_next_year_index = True

            if skip_next_year_index:
                skip_next_year_index = False
                continue

            if remap_next_year_index and "# `YEAR indx'" in line:
                line = self._replace_leading_int(line, 2)
                remap_next_year_index = False

            out.append(line)

        output_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _materialize_routed_two_ofe_management_template(self, *, traffic: str) -> Path:
        source_path = self._resolve_legacy_management_template_path(traffic=traffic)
        output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.routed_two_ofe.man"
        self._build_routed_two_ofe_management_file(template_path=source_path, output_path=output_path)
        return output_path

    def _materialize_routed_three_ofe_management_template(self, *, traffic: str) -> Path:
        source_path = self._resolve_legacy_management_template_path(traffic=traffic)
        output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.routed_three_ofe.man"
        if source_path.resolve() != output_path.resolve():
            shutil.copy2(source_path, output_path)
        return output_path

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
        elif design in {"inslope_bd", "outslope_rutted"} and surface == "paved":
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
        strategy: str = "phase1",
    ) -> None:
        from wepppyo3.wepp_interchange import combine_hillslope_pass_files

        combine_hillslope_pass_files(
            base_pass=str(base_pass_path),
            road_passes=[str(path) for path in road_pass_paths],
            out_pass=str(output_pass_path),
            strategy=str(strategy),
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
                            )
                        except Exception as exc:
                            skipped_segments.append({"segment_id": segment_id, "reason": "trace_execution_failed"})
                            segment_execution_records.append(
                                {
                                    "segment_id": segment_id,
                                    "status": "failed",
                                    "routing_mode": routing_mode,
                                    "reason": "trace_execution_failed",
                                    "error": str(exc),
                                }
                            )
                            failed_segment_records.append(
                                {
                                    "segment_id": segment_id,
                                    "reason": "trace_execution_failed",
                                    "error": str(exc),
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
                                    "error": str(exc),
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
                                "error": str(exc),
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
                                "error": str(exc),
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
                                "routing_mode": routing_mode,
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
                                            "error": str(exc),
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
                                            "error": str(exc),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "error": str(exc),
                                        },
                                    )
                                continue

                            if hillslope_length_m <= 0.0 or hillslope_width_m <= 0.0:
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

                                missing_fields = self._missing_outslope_unrutted_required_fields(properties)
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
                                            "error": str(exc),
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
                                            "error": str(exc),
                                        }
                                    )
                                    self._append_roads_log(
                                        "run",
                                        "segment_skipped",
                                        {
                                            "segment_id": source_segment_id,
                                            "segment_hillslope_id": segment_hillslope_id,
                                            "reason": "failed_missing_parameter",
                                            "error": str(exc),
                                        },
                                    )
                                    strip_failure = True
                                    continue

                                profile = dict(profile)
                                profile["segment_length_m"] = max(1.0, float(overlap_length_m))
                                parity_profile = self._apply_outslope_unrutted_geometry_parity(
                                    road_length_m=float(profile["segment_length_m"]),
                                    road_width_m=float(segment_inputs["road_width_m"]),
                                    road_slope_pct=float(profile["slope_pct"]),
                                )

                                fill_profile = self._derive_fill_profile_from_inputs(
                                    fill_length_m=segment_inputs["fill_length_m"],
                                    fill_slope_pct=segment_inputs["fill_slope_pct"],
                                )
                                routed_buffer_profile = self._derive_buffer_profile_from_feature_or_defaults(
                                    properties=properties,
                                    road_profile=profile,
                                )

                                overlap_geometry_wgs84 = candidate.get("overlap_geometry_wgs84")
                                discha_median_m = None
                                if overlap_geometry_wgs84 is not None:
                                    discha_median_m = self._sample_discha_median_from_wgs84_geometry(
                                        overlap_geometry_wgs84,
                                        discha_dataset=discha_dataset,
                                        wgs84_to_discha=wgs84_to_discha,
                                    )
                                if discha_median_m is None:
                                    discha_median_m = hillslope_length_m * 0.5

                                downslope_landuse_length_m = max(0.0, float(discha_median_m) - float(fill_profile["fill_length_m"]))
                                has_downslope_landuse = downslope_landuse_length_m >= OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M
                                if not has_downslope_landuse:
                                    downslope_landuse_length_m = 0.0

                                top_landuse_length_m = (
                                    hillslope_length_m
                                    - float(parity_profile["sim_length_m"])
                                    - float(fill_profile["fill_length_m"])
                                    - float(downslope_landuse_length_m)
                                )

                                if top_landuse_length_m <= 0.0:
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
                                    strip_plans[0]["top_landuse_length_m"] = (
                                        float(strip_plans[0]["top_landuse_length_m"]) + float(compensation_m)
                                    )
                                    strip_plans[0]["top_ofe_compensation_m"] = (
                                        float(strip_plans[0]["top_ofe_compensation_m"]) + float(compensation_m)
                                    )
                                    remainder_width_m = 0.0

                            def _plan_total_length_m(plan_row: Mapping[str, Any]) -> float:
                                return float(
                                    float(plan_row["top_landuse_length_m"])
                                    + float(plan_row["parity_profile"]["sim_length_m"])
                                    + float(plan_row["fill_profile"]["fill_length_m"])
                                    + float(plan_row["bottom_landuse_length_m"])
                                )

                            hillslope_area_m2 = float(hillslope_width_m * hillslope_length_m)
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
                                    adjusted_top_length_m = float(strip_plans[0]["top_landuse_length_m"]) + compensation_m
                                    if adjusted_top_length_m <= 0.0:
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
                                    else:
                                        strip_plans[0]["top_landuse_length_m"] = adjusted_top_length_m
                                        strip_plans[0]["top_ofe_compensation_m"] = (
                                            float(strip_plans[0]["top_ofe_compensation_m"]) + compensation_m
                                        )

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
                                hillslope_record["area_error_before_compensation_m2"] = float(area_error_before_m2)
                                hillslope_record["area_error_after_compensation_m2"] = float(area_error_after_m2)

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

                                ofe_order: Tuple[int, ...] = (3, 1, 2, 3) if has_downslope_landuse else (3, 1, 2)
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

                                if has_downslope_landuse:
                                    self._write_routed_four_ofe_landuse_road_fill_hill_slope_file(
                                        segment_slope_path,
                                        width_m=strip_width_m,
                                        top_landuse_length_m=top_landuse_length_m,
                                        top_landuse_slope_pct=float(plan["top_landuse_slope_pct"]),
                                        road_length_m=parity_profile["sim_length_m"],
                                        road_slope_pct=parity_profile["road_slope_pct"],
                                        fill_length_m=fill_profile["fill_length_m"],
                                        fill_slope_pct=fill_profile["fill_slope_pct"],
                                        bottom_landuse_length_m=bottom_landuse_length_m,
                                        bottom_landuse_slope_pct=float(plan["bottom_landuse_slope_pct"]),
                                    )
                                else:
                                    self._write_routed_three_ofe_landuse_road_fill_slope_file(
                                        segment_slope_path,
                                        width_m=strip_width_m,
                                        top_landuse_length_m=top_landuse_length_m,
                                        top_landuse_slope_pct=float(plan["top_landuse_slope_pct"]),
                                        road_length_m=parity_profile["sim_length_m"],
                                        road_slope_pct=parity_profile["road_slope_pct"],
                                        fill_length_m=fill_profile["fill_length_m"],
                                        fill_slope_pct=fill_profile["fill_slope_pct"],
                                    )

                                self._append_roads_log(
                                    "run",
                                    "segment_inputs_ready",
                                    {
                                        "segment_id": source_segment_id,
                                        "segment_hillslope_id": segment_hillslope_id,
                                        "segment_run_id": segment_run_id,
                                        "routing_mode": "outslope_unrutted_replacement",
                                        "target_hillslope_wepp_id": int(wepp_id_int),
                                        "target_hillslope_topaz_id": int(topaz_id_hill),
                                        "design": "outslope_unrutted",
                                        "surface": segment_inputs["surface"],
                                        "traffic": segment_inputs["traffic"],
                                        "soil_texture": segment_inputs["soil_texture"],
                                        "rfg_pct": segment_inputs["rfg_pct"],
                                        "road_width_m": segment_inputs["road_width_m"],
                                        "fill_length_m": fill_profile["fill_length_m"],
                                        "fill_slope_pct": fill_profile["fill_slope_pct"],
                                        "segment_length_m": profile["segment_length_m"],
                                        "overlap_length_m": overlap_length_m,
                                        "inclusion_ratio": inclusion_ratio,
                                        "top_landuse_length_m": top_landuse_length_m,
                                        "bottom_landuse_length_m": bottom_landuse_length_m,
                                        "strip_width_m": strip_width_m,
                                        "discha_median_m": discha_median_m,
                                        "contributor_ofe_count": len(ofe_order),
                                        **parity_profile,
                                        **routed_buffer_profile,
                                    },
                                )

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
                                            "error": str(exc),
                                            "design": "outslope_unrutted",
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
                                            "error": str(exc),
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
                                            "error": str(exc),
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
                                    "contributor_ofe_count": 4 if has_downslope_landuse else 3,
                                    "top_landuse_length_m": top_landuse_length_m,
                                    "bottom_landuse_length_m": bottom_landuse_length_m,
                                    "discha_median_m": discha_median_m,
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
                                self._write_single_ofe_slope_file(
                                    remainder_slope_path,
                                    width_m=float(remainder_width_m),
                                    length_m=float(hillslope_length_m),
                                    slope_pct=float(strip_plans[0]["top_landuse_slope_pct"]),
                                )

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
                                            "error": str(exc),
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
                                            "error": str(exc),
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
                                            "error": str(exc),
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

            for wepp_id in additive_targeted_without_replacement_ids:
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

            for wepp_id in replacement_targeted_ids:
                replacement_paths = list(replacement_pass_paths_by_wepp.get(wepp_id, []))
                if not replacement_paths:
                    continue
                output_pass_path = Path(self.roads_output_dir) / f"H{wepp_id}.pass.dat"
                output_was_symlink = output_pass_path.is_symlink()
                if output_pass_path.exists() or output_was_symlink:
                    output_pass_path.unlink()

                additive_count = len(segment_pass_paths_by_wepp.get(wepp_id, []))
                if additive_count:
                    self._append_roads_log(
                        "run",
                        "replacement_supersedes_additive",
                        {
                            "wepp_id": int(wepp_id),
                            "additive_pass_count": int(additive_count),
                            "replacement_pass_count": len(replacement_paths),
                        },
                    )

                self._append_roads_log(
                    "run",
                    "replacement_target_hillslope_start",
                    {
                        "wepp_id": int(wepp_id),
                        "replacement_pass_count": len(replacement_paths),
                        "replacement_pass_relpaths": [
                            os.path.relpath(path, self.wd) for path in replacement_paths
                        ],
                        "output_pass_relpath": os.path.relpath(output_pass_path, self.wd),
                        "output_was_symlink": output_was_symlink,
                    },
                )

                if len(replacement_paths) == 1:
                    staged_strategy[str(wepp_id)] = (
                        f"replacement_{self._safe_link_or_copy(replacement_paths[0], str(output_pass_path))}"
                    )
                else:
                    self._combine_target_hillslope_pass(
                        base_pass_path=str(replacement_paths[0]),
                        road_pass_paths=replacement_paths[1:],
                        output_pass_path=str(output_pass_path),
                        strategy="phase4",
                    )
                    staged_strategy[str(wepp_id)] = "replacement_combined"

                self._append_roads_log(
                    "run",
                    "replacement_hillslope_pass_staged",
                    {
                        "wepp_id": int(wepp_id),
                        "replacement_pass_count": len(replacement_paths),
                        "staged_strategy": staged_strategy[str(wepp_id)],
                        "staged_pass_relpath": os.path.relpath(output_pass_path, self.wd),
                    },
                )

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
        params = self._normalize_params_with_defaults(getattr(self, "_roads_params", {}))
        summary_payload = {
            "enabled": bool(getattr(self, "_enabled", False)),
            "uploaded_geojson_relpath": getattr(self, "_uploaded_geojson_relpath", None),
            "uploaded_geojson_sha256": getattr(self, "_uploaded_geojson_sha256", None),
            "roads_params": params,
            "attribute_field_map": dict(params.get("attribute_field_map", self._empty_attribute_field_map())),
            "discovered_attribute_catalog": getattr(self, "_uploaded_attribute_catalog", None),
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
                "has_attribute_catalog": summary_payload["discovered_attribute_catalog"] is not None,
                "has_prepare_summary": summary_payload["last_prepare_summary"] is not None,
                "has_run_summary": summary_payload["last_run_summary"] is not None,
            },
        )
        return summary_payload
