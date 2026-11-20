"""The editable ESDAC missing-subsoil profile and its request fields."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
import re

SOURCE_FIELDS = {
    "clay": "CLAY",
    "sand": "SAND",
    "silt": "SILT",
    "bulk_density": "BD",
    "organic_carbon": "OC",
    "gravel": "GRAVEL",
}
DEFAULT_SUBSOIL = {
    "clay": 25.0,
    "sand": 40.0,
    "silt": 35.0,
    "bulk_density": 1.4,
    "organic_carbon": 0.5,
    "gravel": 5.0,
}
FALLBACK_DIAGNOSTIC = "source.stu.subsoil_defaults_applied"
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def validate_subsoil_profile(values: Mapping[str, object]) -> dict[str, float]:
    """Return a complete, finite profile suitable for ESDAC soil building."""
    if not isinstance(values, Mapping) or values.keys() != SOURCE_FIELDS.keys():
        raise ValueError("Supply all six ESDAC subsoil defaults together.")
    profile: dict[str, float] = {}
    for field, raw in values.items():
        if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
            raise ValueError(f"ESDAC subsoil {field} must be a finite number.")
        if isinstance(raw, str) and _DECIMAL.fullmatch(raw.strip()) is None:
            raise ValueError(f"ESDAC subsoil {field} must be a finite number.")
        try:
            value = float(raw)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"ESDAC subsoil {field} must be a finite number.") from exc
        if not isfinite(value):
            raise ValueError(f"ESDAC subsoil {field} must be a finite number.")
        if field == "bulk_density":
            if value <= 0.0:
                raise ValueError("ESDAC subsoil bulk density must be positive.")
        elif not 0.0 <= value <= 100.0:
            raise ValueError(f"ESDAC subsoil {field} must be between 0 and 100 percent.")
        profile[field] = value
    texture = sum(profile[field] for field in ("clay", "sand", "silt"))
    if abs(texture - 100.0) > 1.0:
        raise ValueError("ESDAC subsoil clay, sand and silt must add up to 100 percent.")
    return profile
