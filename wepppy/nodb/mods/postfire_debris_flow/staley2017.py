"""Scalar Staley (2017) M1/M3 equations for explicitly prepared predictors.

See docs/staley2017_engine.md and ADR-0056 for units and numerical policy.
Inverse results solve an equality, not minimum rainfall to exceed a target.
"""

from dataclasses import dataclass
import math
from numbers import Real
from typing import Literal

__all__ = ["ThresholdResult", "probability", "rainfall_threshold"]

# Independently transcribed from Table 4; tuple order is B, Ct, Cf, Cs.
_COEFFICIENTS = {
    ("M1", 15): (-3.63, 0.41, 0.67, 0.70),
    ("M1", 30): (-3.61, 0.26, 0.39, 0.50),
    ("M1", 60): (-3.21, 0.17, 0.20, 0.220),
    ("M3", 15): (-3.71, 0.32, 0.33, 0.47),
    ("M3", 30): (-3.79, 0.21, 0.19, 0.36),
    ("M3", 60): (-3.46, 0.14, 0.10, 0.18),
}


@dataclass(frozen=True)
class ThresholdResult:
    """Finite rainfall and intensity, or an explicit unavailable/nonunique reason."""

    status: Literal["available", "unavailable", "nonunique"]
    reason: Literal[
        "constant_probability", "constant_probability_mismatch",
        "negative_rainfall", "arithmetic_overflow", "arithmetic_underflow",
    ] | None
    rainfall_mm: float | None
    intensity_mm_per_hour: float | None


def _scalar(name: str, value: Real) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real scalar")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite in binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite in binary64")
    return result


def _response(model: str, duration_minutes: Real, T: Real, F: Real, S: Real):
    if not isinstance(model, str):
        raise TypeError("model must be M1 or M3")
    if model not in ("M1", "M3"):
        raise ValueError("model must be M1 or M3")
    duration = _scalar("duration_minutes", duration_minutes)
    if duration not in (15, 30, 60):
        raise ValueError("duration_minutes must be 15, 30 or 60")
    terrain, fire, soil = _scalar("T", T), _scalar("F", F), _scalar("S", S)
    if terrain < 0 or (model == "M1" and terrain > 1):
        raise ValueError("T must be in [0,1] for M1 or nonnegative for M3")
    if model == "M3" and not 0 <= fire <= 1:
        raise ValueError("F must be in [0,1] for M3")
    if soil < 0:
        raise ValueError("S must be nonnegative")
    intercept, ct, cf, cs = _COEFFICIENTS[model, int(duration)]
    response = ct * terrain + cf * fire + cs * soil
    if not math.isfinite(response):
        raise OverflowError("rainfall response coefficient overflow")
    return intercept, response, duration


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        return 1 / (1 + math.exp(-logit))
    exponential = math.exp(logit)
    return exponential / (1 + exponential)


def probability(
    model: str, duration_minutes: Real, *, T: Real, F: Real, S: Real,
    rainfall_mm: Real,
) -> float:
    """Evaluate occurrence probability for duration-specific accumulation in mm.

    Invalid inputs raise TypeError/ValueError; intermediate overflow raises
    OverflowError. Prepared M1 F is normalized dNBR, with no further scaling.
    """
    rainfall = _scalar("rainfall_mm", rainfall_mm)
    if rainfall < 0:
        raise ValueError("rainfall_mm must be nonnegative")
    intercept, response, _ = _response(model, duration_minutes, T, F, S)
    logit = intercept + rainfall * response
    if not math.isfinite(logit):
        raise OverflowError("rainfall logit overflow")
    return _sigmoid(logit)


def rainfall_threshold(
    model: str, duration_minutes: Real, *, T: Real, F: Real, S: Real,
    target_probability: Real,
) -> ThresholdResult:
    """Solve p(R)=target for nonnegative R; intensity is in mm/hour.

    Decreasing-response solutions are algebraic, not validated triggering
    thresholds. Nonunique/unavailable results contain no numeric placeholders.
    """
    target = _scalar("target_probability", target_probability)
    if not 0 < target < 1:
        raise ValueError("target_probability must be strictly between 0 and 1")
    intercept, response, duration = _response(model, duration_minutes, T, F, S)
    baseline = _sigmoid(intercept)
    at_intercept = target == baseline
    if response == 0:
        if at_intercept:
            return ThresholdResult("nonunique", "constant_probability", None, None)
        return ThresholdResult("unavailable", "constant_probability_mismatch", None, None)
    if at_intercept:
        return ThresholdResult("available", None, 0.0, 0.0)
    difference = target - baseline
    if (response > 0 and difference < 0) or (response < 0 and difference > 0):
        return ThresholdResult("unavailable", "negative_rainfall", None, None)
    if abs(difference) <= baseline / 2:
        # Center on the accepted representable intercept probability. This
        # log1p form retains adjacent-target differences lost by logit(p)-B.
        numerator = math.log1p(difference / baseline) - math.log1p(-difference / (1 - baseline))
    else:
        numerator = math.log(target) - math.log1p(-target) - intercept
    rainfall = numerator / response
    if not math.isfinite(rainfall):
        return ThresholdResult("unavailable", "arithmetic_overflow", None, None)
    if rainfall < 0:
        return ThresholdResult("unavailable", "negative_rainfall", None, None)
    if rainfall == 0:
        return ThresholdResult("unavailable", "arithmetic_underflow", None, None)
    intensity = rainfall / (duration / 60)
    if not math.isfinite(intensity):
        return ThresholdResult("unavailable", "arithmetic_overflow", None, None)
    return ThresholdResult("available", None, rainfall, intensity)
