# Staley 2017 numerical engine contract

Status: accepted, 2026-09-09 UTC. The owner explicitly approved N01–N04
and this contract in the execution conversation.
[ADR-0056](../../../../../docs/adrs/ADR-0056-staley-numerical-engine.md) records provenance.

## Scope and interfaces

An in-memory scalar Python library consumes prepared watershed predictors.
It performs no raster processing, I/O, model selection, or missing-data fallback.
Signatures:

```python
probability(model, duration_minutes, *, T, F, S, rainfall_mm) -> float
rainfall_threshold(model, duration_minutes, *, T, F, S, target_probability) -> ThresholdResult
```

Model is exactly `M1` or `M3`; duration is 15, 30 or 60 minutes. Numeric inputs
are Python `numbers.Real` scalars convertible to finite binary64 values. Reject booleans,
strings, complex numbers, containers and arrays; no broadcasting is supported.
Caller type errors raise `TypeError`; invalid ranges, model/duration values,
or nonfinite numeric inputs raise `ValueError`, identifying the argument.

M1 T and M3 F are fractions in [0,1]. M3 T and both S values are nonnegative,
with no invented upper calibration bound. M1 F may be any finite value,
including negative normalized dNBR. M1 F is already scaled: do not divide by
1000 again. M1 S is supplied in the calibrated K convention; M3 S is supplied
as thickness in cm divided by 254. These checks do not establish calibration
validity. Rainfall is nonnegative accumulation in mm for the chosen duration.

## Forward calculation

Use the six coefficient rows in the specification, independently checked in
the [publication audit](../../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/coefficient_check.md).
Set `q = Ct*T + Cf*F + Cs*S`, `x = B + rainfall_mm*q` and evaluate sigmoid(x)
with a sign-stable exponential branch. Finite extreme logits may round to 0
or 1. Nonfinite intermediate arithmetic raises `OverflowError` explicitly;
it is not converted into a saturated probability. No response clamping or
override at zero rainfall is applied: the equation returns sigmoid(B) there.
This is mathematical model behavior, not a claim of rainless debris flows.

## Inverse equality and numerical policies

The caller supplies a finite target strictly between 0 and 1. There is no
engine default target. A threshold means a nonnegative rainfall solution to
`p(R) = target`, not minimum rainfall to reach or exceed that target.

Immutable `ThresholdResult` contains `status`, `reason`, `rainfall_mm`
and `intensity_mm_per_hour`. Status is `available`, `unavailable`, or
`nonunique`. Available results have reason `None` and finite nonnegative
numeric values. Other results have both numeric values `None`.

For exact `q == 0`, compare the target exactly with the forward implementation's
sigmoid(B). A match returns `nonunique` / `constant_probability`; otherwise
return `unavailable` / `constant_probability_mismatch`. This binary64 equality
rule avoids an invented tolerance and avoids using a logit round-trip to
recognize the representable intercept probability.

For nonzero q, a target exactly equal to sigmoid(B) returns zero rainfall.
First reject targets below the representable intercept for positive q, or
above it for negative q, as `negative_rainfall`. This exact comparison prevents
cancellation in logit subtraction from manufacturing a reachable threshold.
For reachable targets, divide the stable log-odds difference by q. Normally
use `log(target) - log1p(-target) - B`. When `abs(target-baseline) <= baseline/2`,
use `log1p(delta/baseline) - log1p(-delta/(1-baseline))`, where baseline is
sigmoid(B) and delta is target minus baseline. This numerical evaluation branch
centers on the accepted representable intercept and keeps both log1p arguments
away from -1; it does not classify a nonzero response as zero. A negative solution
returns `unavailable` / `negative_rainfall`. A finite nonnegative solution is
available, with intensity obtained by dividing rainfall by duration in hours.
A nonzero mathematical rainfall solution that rounds to zero returns
`unavailable` / `arithmetic_underflow`; zero is reserved for exact baseline
targets. A nonfinite inverse or intensity returns `unavailable` / `arithmetic_overflow`.
Overflow while constructing q remains `OverflowError`, as in the forward API.
No tolerance-based zero tests or negative-result clipping are used.

Negative q is possible with M1 dNBR. The inverse may then have a nonnegative
equality solution on a decreasing curve. That extension is algebraic, outside
the publication's positive-contribution discussion, and is not a scientifically
validated rainfall-trigger threshold. Tiny q can lead to unrepresentable
solutions; unavailable values must never be replaced by zero or infinity.

## Validation requirements

Independent numerical tests must cover six coefficient rows, negative/zero q,
zero rainfall, finite extremes, overflow, invalid types/ranges and inverse
reconstruction. Synthetic generated examples are numerical evidence only.

At targets adjacent to the intercept probability, adding the solved rainfall
term to B in the forward function may round back to B. Reconstruction is subject
to binary64 rounding; an available equality is not a promise of bitwise target
reconstruction. Exact side-of-baseline reachability is preserved.
