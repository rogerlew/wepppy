"""SA-01 request validation and effective preparation settings."""
from __future__ import annotations

import math
from typing import Any

__all__ = ["parse_anisotropy_inputs", "effective_anisotropy"]

_FIELDS = {"soil_anisotropy_upper": 100.0, "soil_anisotropy_lower": 10.0}


def _value(name: str, value: Any) -> float | None:
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"{name} requires one number or blank")
        value = value[0]
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{name} requires one number or blank")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} requires one number or blank") from exc
    if not math.isfinite(number) or not 1 <= number <= _FIELDS[name]:
        raise ValueError(f"{name} must be finite and between 1 and {_FIELDS[name]:g}")
    return number


def parse_anisotropy_inputs(wepp: Any, payload: dict[str, Any]) -> dict[str, float | None]:
    """Validate all submitted values before the caller mutates controller state."""
    values = {name: _value(name, payload[name]) for name in _FIELDS if name in payload}
    if any(value is not None for value in values.values()):
        if not (getattr(wepp, "multi_ofe", False) and getattr(wepp, "run_wepp_ui", False)):
            raise ValueError("Soil anisotropy overrides require MOFE and hourly water balance/deep seepage")
    return values


def effective_anisotropy(wepp: Any, hourly: bool | None = None) -> tuple[float | None, float | None]:
    """Stored inactive values are retained but never applied to an ineligible prep."""
    if not getattr(wepp, "multi_ofe", False):
        return None, None
    enabled = getattr(wepp, "run_wepp_ui", False) if hourly is None else hourly
    if not enabled:
        return None, None
    return (
        _value("soil_anisotropy_upper", getattr(wepp, "soil_anisotropy_upper", None)),
        _value("soil_anisotropy_lower", getattr(wepp, "soil_anisotropy_lower", None)),
    )
