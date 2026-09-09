"""Independent publication/Decimal oracles and scalar numerical edge contracts."""

from dataclasses import FrozenInstanceError, asdict
from decimal import Decimal, localcontext
import json
import math
import sys

import numpy as np
import pytest

from wepppy.nodb.mods.postfire_debris_flow.staley2017 import (
    probability, rainfall_threshold,
)

pytestmark = pytest.mark.unit

# Publication Table 4 rows, independent of implementation constants.
ROWS = [
    ("M1", 15, "-3.63", ".41", ".67", ".70"),
    ("M1", 30, "-3.61", ".26", ".39", ".50"),
    ("M1", 60, "-3.21", ".17", ".20", ".220"),
    ("M3", 15, "-3.71", ".32", ".33", ".47"),
    ("M3", 30, "-3.79", ".21", ".19", ".36"),
    ("M3", 60, "-3.46", ".14", ".10", ".18"),
]


@pytest.mark.parametrize("model,duration,b,ct,cf,cs", ROWS)
def test_publication_decimal_forward_and_inverse(model, duration, b, ct, cf, cs):
    with localcontext() as context:
        context.prec = 60
        intercept = Decimal(b)
        q = Decimal(ct)*Decimal(".4") + Decimal(cf)*Decimal(".6") + Decimal(cs)*Decimal(".3")
        x = intercept + Decimal(8)*q
        expected = Decimal(1) / (Decimal(1) + (-x).exp())
        expected_threshold = -intercept / q
    args = dict(T=.4, F=.6, S=.3)
    assert probability(model, duration, **args, rainfall_mm=8) == pytest.approx(float(expected), rel=2e-15)
    result = rainfall_threshold(model, duration, **args, target_probability=.5)
    assert result.status == "available" and result.reason is None
    assert result.rainfall_mm == pytest.approx(float(expected_threshold), rel=2e-15)
    assert result.intensity_mm_per_hour == pytest.approx(float(expected_threshold)*60/duration)
    assert probability(model, duration, **args, rainfall_mm=result.rainfall_mm) == pytest.approx(.5, abs=2e-15)


@pytest.mark.parametrize("model,duration,b,ct,cf,cs", ROWS)
@pytest.mark.parametrize("target", [.01, .1, .5, .75, .99])
def test_inverse_reconstructs_or_identifies_negative_solution(model, duration, b, ct, cf, cs, target):
    args = dict(T=.2, F=.8, S=.1)
    result = rainfall_threshold(model, duration, **args, target_probability=target)
    if target < 1/(1+math.exp(-float(b))):
        assert result.reason == "negative_rainfall"
        assert result.rainfall_mm is None and result.intensity_mm_per_hour is None
    else:
        assert result.status == "available"
        assert probability(model, duration, **args, rainfall_mm=result.rainfall_mm) == pytest.approx(target, rel=3e-15)


@pytest.mark.parametrize("model,duration,b,ct,cf,cs", ROWS)
def test_zero_rainfall_and_exact_constant_response(model, duration, b, ct, cf, cs):
    args = dict(T=0, F=0, S=0)
    baseline = probability(model, duration, **args, rainfall_mm=0)
    assert baseline == pytest.approx(1/(1+math.exp(-float(b))))
    assert baseline > 0
    assert probability(model, duration, **args, rainfall_mm=100) == baseline
    result = rainfall_threshold(model, duration, **args, target_probability=baseline)
    assert result.status == "nonunique" and result.reason == "constant_probability"
    assert result.rainfall_mm is None and result.intensity_mm_per_hour is None
    with pytest.raises(FrozenInstanceError):
        result.rainfall_mm = 0
    mismatch = rainfall_threshold(model, duration, **args, target_probability=math.nextafter(baseline, 1))
    assert mismatch.reason == "constant_probability_mismatch"
    args['S'] = .2
    unique = rainfall_threshold(model, duration, **args, target_probability=baseline)
    assert unique.status == "available" and unique.rainfall_mm == unique.intensity_mm_per_hour == 0


def test_negative_dnbr_decreasing_curve_and_cancellation():
    args = dict(T=0, F=-1, S=0)
    baseline = probability("M1", 15, **args, rainfall_mm=0)
    assert probability("M1", 15, **args, rainfall_mm=10) < baseline
    result = rainfall_threshold("M1", 15, **args, target_probability=.01)
    assert result.status == "available" and result.rainfall_mm > 0
    assert probability("M1", 15, **args, rainfall_mm=result.rainfall_mm) == pytest.approx(.01)
    assert rainfall_threshold("M1", 15, **args, target_probability=.5).reason == "negative_rainfall"
    assert rainfall_threshold("M1", 15, T=0, F=-.7, S=.67, target_probability=baseline).status == "nonunique"


@pytest.mark.parametrize("model,duration,b,ct,cf,cs", ROWS)
def test_adjacent_intercept_targets_preserve_reachability(model, duration, b, ct, cf, cs):
    cases = [dict(T=.4, F=.6, S=.3)]
    if model == "M1":
        cases.append(dict(T=0, F=-1, S=0))
    for args in cases:
        increasing = args['F'] >= 0
        baseline = probability(model, duration, **args, rainfall_mm=0)
        for endpoint in (0, 1):
            target = math.nextafter(baseline, endpoint)
            result = rainfall_threshold(model, duration, **args, target_probability=target)
            reachable = (endpoint == 1) == increasing
            if reachable:
                assert result.status == "available" and result.rainfall_mm > 0
                actual = probability(model, duration, **args, rainfall_mm=result.rainfall_mm)
                # Forward logit formation can round back to B at this scale.
                assert abs(actual - target) <= 4 * math.ulp(target)
            else:
                assert result.status == "unavailable" and result.reason == "negative_rainfall"
                assert result.rainfall_mm is None and result.intensity_mm_per_hour is None


@pytest.mark.parametrize("fire,expected", [(-1, 0.0), (1, 1.0)])
def test_finite_extreme_logits_saturate_stably(fire, expected):
    assert probability("M1", 15, T=0, F=fire, S=0, rainfall_mm=1e6) == expected


def test_no_additional_calibration_caps_or_double_dnbr_scaling():
    assert probability("M1", 15, T=0, F=2, S=4, rainfall_mm=1) == pytest.approx(1/(1+math.exp(-.51)))
    assert probability("M3", 15, T=4, F=1, S=2, rainfall_mm=1) > 0
    assert probability("M1", np.float64(15), T=np.float64(.4), F=.6, S=.3, rainfall_mm=np.int64(8)) > .5


@pytest.mark.parametrize("bad", [True, np.bool_(True), "1", 1j, [], {}, np.array(1.), np.array([1.]), None])
@pytest.mark.parametrize("field", ["T", "F", "S", "rainfall_mm", "duration_minutes"])
def test_reject_non_scalar_types(field, bad):
    args = dict(model="M1", duration_minutes=15, T=.4, F=.6, S=.3, rainfall_mm=1)
    args[field] = bad
    with pytest.raises(TypeError, match=field):
        probability(**args)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 10**400])
@pytest.mark.parametrize("field", ["T", "F", "S", "rainfall_mm", "duration_minutes"])
def test_nonfinite_input_is_caller_error(field, bad):
    args = dict(model="M1", duration_minutes=15, T=.4, F=.6, S=.3, rainfall_mm=1)
    args[field] = bad
    with pytest.raises(ValueError, match=field):
        probability(**args)


@pytest.mark.parametrize("field,value,error", [
    ("model", "M2", ValueError), ("model", "m1", ValueError), ("model", [], TypeError),
    ("duration_minutes", 0, ValueError), ("duration_minutes", 15.1, ValueError),
    ("T", -.1, ValueError), ("T", 1.1, ValueError),
    ("S", -.1, ValueError), ("rainfall_mm", -.1, ValueError),
])
def test_invalid_model_duration_and_ranges(field, value, error):
    args = dict(model="M1", duration_minutes=15, T=.4, F=.6, S=.3, rainfall_mm=1)
    args[field] = value
    with pytest.raises(error, match=field):
        probability(**args)


@pytest.mark.parametrize("field,value", [("T", -1), ("F", -.1), ("F", 1.1), ("S", -1)])
def test_m3_physical_ranges(field, value):
    args = dict(T=.4, F=.6, S=.3)
    args[field] = value
    with pytest.raises(ValueError, match=field):
        rainfall_threshold("M3", 15, **args, target_probability=.5)


@pytest.mark.parametrize("target", [0, 1, -.1, 1.1, math.nan, math.inf])
def test_invalid_target_range(target):
    with pytest.raises(ValueError, match="target_probability"):
        rainfall_threshold("M1", 15, T=0, F=0, S=0, target_probability=target)


@pytest.mark.parametrize("target", [True, "0.5", np.array(.5), None])
def test_invalid_target_type(target):
    with pytest.raises(TypeError, match="target_probability"):
        rainfall_threshold("M1", 15, T=0, F=0, S=0, target_probability=target)


def test_explicit_overflow_and_tiny_nonzero_response():
    largest = sys.float_info.max
    with pytest.raises(OverflowError, match="response"):
        probability("M1", 15, T=0, F=largest, S=largest, rainfall_mm=0)
    with pytest.raises(OverflowError, match="response"):
        rainfall_threshold("M1", 15, T=0, F=largest, S=largest, target_probability=.5)
    for fire in (-largest, largest):
        with pytest.raises(OverflowError, match="logit"):
            probability("M1", 15, T=0, F=fire, S=0, rainfall_mm=10)
    for soil in (1e-320, (3.63/1e308)/.7):
        result = rainfall_threshold("M1", 15, T=0, F=0, S=soil, target_probability=.5)
        assert result.status == "unavailable" and result.reason == "arithmetic_overflow"
        assert result.rainfall_mm is None and result.intensity_mm_per_hour is None
        json.dumps(asdict(result), allow_nan=False)
    result = rainfall_threshold("M1", 15, T=0, F=0, S=1e-200, target_probability=.5)
    assert result.status == "available" and result.rainfall_mm > 1e200
    assert probability("M1", 15, T=0, F=0, S=1e-200, rainfall_mm=result.rainfall_mm) == pytest.approx(.5)


@pytest.mark.parametrize("target,fire", [(math.nextafter(0., 1.), -1), (math.nextafter(1., 0.), 1)])
def test_targets_near_endpoints_are_finite(target, fire):
    result = rainfall_threshold("M1", 15, T=0, F=fire, S=0, target_probability=target)
    assert result.status == "available" and math.isfinite(result.rainfall_mm)
    actual = probability("M1", 15, T=0, F=fire, S=0, rainfall_mm=result.rainfall_mm)
    assert abs(actual-target) <= math.ulp(target)


@pytest.mark.parametrize("fire,endpoint", [(1e308, 1), (-1e308, 0)])
def test_nonzero_inverse_underflow_is_not_zero_rainfall(fire, endpoint):
    args = dict(T=0, F=fire, S=0)
    baseline = probability("M1", 15, **args, rainfall_mm=0)
    result = rainfall_threshold("M1", 15, **args, target_probability=math.nextafter(baseline, endpoint))
    assert result.status == "unavailable" and result.reason == "arithmetic_underflow"
    assert result.rainfall_mm is None and result.intensity_mm_per_hour is None
