"""Roads design vocabulary and unchanged parameterization bounds."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from . import _unrutted

__all__ = [
    'DESIGN_ALIASES',
    'ELIGIBLE_ROADS_DESIGNS',
    'ELIGIBLE_POINT_SOURCE_DESIGNS',
    'OUTSLOPE_UNRUTTED_AREA_EPSILON_M2',
    'OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M',
    'OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS',
    'OUTSLOPE_UNRUTTED_BOUNDS',
    'SURFACE_ALIASES',
    'TRAFFIC_ALIASES',
    'CONDITION_TRAFFIC_MAP',
    'SOIL_TEXTURE_ALIASES',
    'ALLOWED_SOIL_TEXTURES',
    'ALLOWED_SURFACES',
    'ALLOWED_TRAFFIC',
    'ATTRIBUTE_FIELD_MAP_KEYS',
    'LEGACY_DESIGN_KEYS',
    'LEGACY_SURFACE_KEYS',
    'LEGACY_TRAFFIC_KEYS',
    'ATTRIBUTE_DISCOVERY_PROFILE_FEATURE_LIMIT_KEY',
    'ATTRIBUTE_DISCOVERY_VALUE_PREVIEW_LIMIT_KEY',
    'ATTRIBUTE_DISCOVERY_VALUE_MAX_CHARS_KEY',
    'DEFAULT_MAPPING_WARNING_EXAMPLE_LIMIT',
]

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

OUTSLOPE_UNRUTTED_AREA_EPSILON_M2 = _unrutted.AREA_EPSILON_M2
OUTSLOPE_UNRUTTED_LANDUSE_MIN_LENGTH_M = 10.0
OUTSLOPE_UNRUTTED_REQUIRED_FIELD_KEYS: Dict[str, Tuple[str, ...]] = {
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
OUTSLOPE_UNRUTTED_BOUNDS: Dict[str, Tuple[float, float]] = {
    "fill_length_m": (0.3, 100.0),
    "fill_slope_pct": (0.1, 150.0),
    "buffer_length_m": (0.3, 300.0),
    "buffer_slope_pct": (0.1, 100.0),
}


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


