"""Roads input normalization, attribute mapping, and validation.

Facade adapters retain caller seams; these functions do not persist controller state."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import numpy as np
from pyproj import CRS
from ._constants import (
    ELIGIBLE_ROADS_DESIGNS,
    OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS,
    OUTSLOPE_UNRUTTED_BOUNDS,
    _normalize_design,
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


def _default_params() -> Dict[str, Any]:
    return {
        "input_crs": "EPSG:4326",
        "sample_step_m": None,
        "tolerance_m": 0.5,
        "soil_texture_default": "loam",
        "surface_default": "gravel",
        "traffic_default": "low",
        "rfg_pct_default": 20.0,
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


def _empty_attribute_field_map(cls) -> Dict[str, Optional[str]]:
    return {key: None for key in ATTRIBUTE_FIELD_MAP_KEYS}


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


def _validated_params_payload(cls, payload, current_params, *, known_fields=None):
    params = cls._normalize_params_with_defaults(current_params)

    if "input_crs" in payload:
        value = str(payload["input_crs"]).strip()
        if not value:
            raise ValueError("input_crs must be a non-empty string.")
        try:
            CRS.from_user_input(value)
        except Exception as exc:  # broad-except: preserve CRS parser error translation at the input boundary.
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
        if key == "tolerance_m" and numeric < 0:
            raise ValueError("tolerance_m must be >= 0.")
        if key == "sample_step_m" and numeric <= 0:
            raise ValueError("sample_step_m must be > 0.")
        if key == "rfg_pct_default" and not (0.0 <= numeric <= 100.0):
            raise ValueError("rfg_pct_default must be between 0 and 100.")
        if key == "road_width_m_default" and not (0.3 <= numeric <= 100.0):
            raise ValueError("road_width_m_default must be between 0.3 and 100.")
        if key == "fill_length_default_m" and not (0.3 <= numeric <= 100.0):
            raise ValueError("fill_length_default_m must be between 0.3 and 100.")
        if key == "fill_slope_default_pct":
            if not (0.1 <= numeric <= 150.0):
                raise ValueError("fill_slope_default_pct must be between 0.1 and 150.")
            numeric = cls._clamp_fill_slope_pct(numeric)
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
        current_map = cls._normalize_attribute_field_map(params.get("attribute_field_map"), known_fields=None)
        if payload_map in (None, ""):
            merged_map = cls._empty_attribute_field_map()
        else:
            if not isinstance(payload_map, Mapping):
                raise ValueError("attribute_field_map must be an object.")
            merged_map = dict(current_map)
            for key in payload_map.keys():
                key_text = str(key)
                if key_text not in ATTRIBUTE_FIELD_MAP_KEYS:
                    raise ValueError(f"attribute_field_map has unsupported key: {key_text}.")
                merged_map[key_text] = payload_map[key]
        params["attribute_field_map"] = cls._normalize_attribute_field_map(
            merged_map,
            known_fields=known_fields,
        )

    params = cls._normalize_params_with_defaults(params)
    return params


def _first_non_empty_property(properties: Mapping[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = properties.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _missing_outslope_unrutted_required_fields(cls, properties: Mapping[str, Any]) -> List[str]:
    missing: List[str] = []
    for field_name, keys in OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS.items():
        if not cls._has_non_empty_property(properties, keys):
            missing.append(field_name)
    return missing


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_outslope_unrutted_required_profiles(
    self,
    *,
    properties: Mapping[str, Any],
) -> Tuple[Optional[Dict[str, float]], Optional[Dict[str, float]], List[str]]:
    missing_or_invalid_fields: List[str] = self._missing_outslope_unrutted_required_fields(properties)
    parsed_values: Dict[str, float] = {}

    for field_name, keys in OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS.items():
        raw_value = self._first_non_empty_property(properties, keys)
        if raw_value is None:
            continue
        parsed = self._coerce_float(raw_value)
        if parsed is None or not np.isfinite(parsed):
            missing_or_invalid_fields.append(field_name)
            continue
        parsed_values[field_name] = float(parsed)

    for field_name, (min_value, max_value) in OUTSLOPE_UNRUTTED_BOUNDS.items():
        value = parsed_values.get(field_name)
        if value is None:
            continue
        if not (float(min_value) <= float(value) <= float(max_value)):
            missing_or_invalid_fields.append(field_name)

    if missing_or_invalid_fields:
        return None, None, sorted(set(missing_or_invalid_fields))

    fill_profile = {
        "fill_length_m": float(parsed_values["fill_length_m"]),
        "fill_slope_pct": float(parsed_values["fill_slope_pct"]),
        "fill_slope_fraction": float(parsed_values["fill_slope_pct"] / 100.0),
    }
    buffer_profile = {
        "buffer_length_m": float(parsed_values["buffer_length_m"]),
        "buffer_slope_pct": float(parsed_values["buffer_slope_pct"]),
        "buffer_slope_fraction": float(parsed_values["buffer_slope_pct"] / 100.0),
        "buffer_length_source": "segment_property",
        "buffer_slope_source": "segment_property",
    }
    return fill_profile, buffer_profile, []


def _normalize_surface(self, value: Optional[str], default_value: str) -> str:
    if value is None:
        return default_value
    normalized = SURFACE_ALIASES.get(value.strip().lower())
    if normalized is None:
        return default_value
    return normalized


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
    default_rfg = float(params.get("rfg_pct_default", 20.0))
    if not np.isfinite(default_rfg):
        default_rfg = 20.0
    default_rfg = max(0.0, min(100.0, float(default_rfg)))
    default_width = float(params.get("road_width_m_default", 4.0))
    if not np.isfinite(default_width) or not (0.3 <= float(default_width) <= 100.0):
        default_width = 4.0
    default_fill_length_m = float(params.get("fill_length_default_m", 30.0))
    if not np.isfinite(default_fill_length_m) or not (0.3 <= float(default_fill_length_m) <= 100.0):
        default_fill_length_m = 30.0
    default_fill_slope_pct = self._as_float_or_none(params.get("fill_slope_default_pct"))
    if default_fill_slope_pct is None:
        default_fill_slope_pct = 10.0
    default_fill_slope_pct = self._clamp_fill_slope_pct(float(default_fill_slope_pct))

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
    texture_source = (
        "segment_property" if texture_raw and texture_raw.strip().lower() in SOIL_TEXTURE_ALIASES
        else "roads_default"
    )

    rfg_pct = self._coerce_float(rfg_raw)
    rfg_source = "segment_property"
    if rfg_pct is None or not np.isfinite(rfg_pct):
        rfg_pct = default_rfg
        rfg_source = "roads_default"
    rfg_pct = max(0.0, min(100.0, float(rfg_pct)))

    road_width_m = self._coerce_float(width_raw)
    width_source = "segment_property"
    if road_width_m is None or not np.isfinite(road_width_m):
        road_width_m = default_width
        width_source = "roads_default"
    if not (0.3 <= float(road_width_m) <= 100.0):
        road_width_m = default_width
        width_source = "roads_default"

    fill_length_m = self._coerce_float(fill_length_raw)
    fill_length_source = "segment_property"
    if fill_length_m is None or not np.isfinite(fill_length_m) or fill_length_m <= 0:
        fill_length_m = default_fill_length_m
        fill_length_source = "roads_default"

    fill_slope_pct = self._coerce_float(fill_slope_raw)
    fill_slope_source = "segment_property"
    if fill_slope_pct is None or not np.isfinite(fill_slope_pct) or fill_slope_pct <= 0:
        fill_slope_pct = default_fill_slope_pct
        fill_slope_source = "roads_default"
    fill_slope_pct = self._clamp_fill_slope_pct(float(fill_slope_pct))

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
            "soil_texture": texture_source,
            "rfg_pct": rfg_source,
            "road_width_m": width_source,
            "fill_length_m": fill_length_source,
            "fill_slope_pct": fill_slope_source,
        },
    }
