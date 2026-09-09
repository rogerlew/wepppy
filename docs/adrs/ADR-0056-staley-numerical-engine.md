# ADR-0056: Staley scalar numerical engine

Status: Accepted

Date: 2026-09-09

## Context

The offline module had no probability or inverse engine. Published equations
and coefficients alone do not define caller errors, overflow, or zero/negative
response behavior. Prepared predictors must remain separate from future raster,
climate and UI integration.

## Decision

Adopt N01–N04 in the [scalar engine contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/staley2017_engine.md).
Use the six verified Table 4 rows, `q=Ct*T+Cf*F+Cs*S`, `x=B+R*q`, and a stable
sigmoid. R is duration-specific accumulation in mm; inverse intensity divides
accumulation by duration in hours. Model, duration, predictors and target are
explicit; there are no model or probability-target defaults.

Accept finite real scalars, nonnegative rainfall, physical fractions in [0,1],
nonnegative M3 ruggedness and soil predictors, and negative finite M1 dNBR.
No additional upper calibration bounds or rescaling are introduced. Invalid
types/ranges fail explicitly. Intermediate forward/response overflow raises;
inverse arithmetic overflow is a structured unavailable result.

Inverse means equality, including decreasing-response solutions. Exact zero q
returns nonunique if the target equals the representable intercept probability,
otherwise unavailable. For nonzero q the same exact target yields zero rainfall;
other targets use stable logit inversion. Negative solutions are unavailable.
No tolerance, clipping, denominator repair, or infinite outputs are introduced.

## Decision Provenance

Decision Venue: repository execution conversation, 2026-09-09 UTC
(2026-09-08 America/Los_Angeles).

Participants Present: repository owner and Codex.

Decision Owner: repository owner, explicit “yes” to adopting recommended
N01–N04 in the drafted numerical contract.

Implementer: Codex.

## Change Summary

Add the first pure M1/M3 engine and documented binary64 edge semantics.
Existing soil/dNBR helpers, run state, calibration coefficients and production
workflow defaults remain unchanged. The engine does not normalize dNBR or K.

## Rationale and Alternatives Considered

Scalar inputs meet the current one-watershed need without speculative array
broadcasting. Preserving the equation at zero rainfall and negative dNBR avoids
silently altering the empirical model. Equality semantics distinguish inverse
algebra from minimum rainfall to exceed a target. Exact representable intercept
comparison avoids spurious tiny thresholds caused by a logit round-trip.

Rejected alternatives: default 50%/75% targets belong to future UI decisions;
zero clipping hides unavailable results; tolerance-based q handling invents
a numerical cutoff; blanket negative-dNBR rejection discards valid observations.

## Evidence

- [Publication equations and coefficient audit](../work-packages/20260908_staley_watershed_engine/artifacts/coefficient_check.md).
- [Decision register](../work-packages/20260908_staley_watershed_engine/artifacts/decision_register.md).
- [Validation evidence](../work-packages/20260908_staley_watershed_engine/artifacts/validation.md).

## Consequences, Risk and Rollback Notes

Negative-response inverse results are mathematical extensions beyond the
publication's positive-contribution discussion. Rounded 0/1 forward results
and very small response coefficients limit numerical reconstruction. Synthetic
examples demonstrate arithmetic, not scientific calibration or deployed safety.
There is no NoDb, UI, RQ, network or raster loader in the engine. Reverting this
additive module removes the new API without migrating run state. Future
production integration requires its own accepted contracts and real workflow
evidence.


## Review refinement: adjacent intercept targets

Independent review reproduced false positive/zero thresholds for targets one
representable value below an increasing curve's baseline. Enforce exact
side-of-baseline reachability before logit inversion. Near baseline, evaluate
the equivalent centered log-odds difference with log1p (dispatch at half the
baseline to keep arguments well-conditioned); elsewhere retain ordinary stable
logit subtraction. This numerical branch preserves the accepted representable
intercept policy and introduces no zero tolerance or scientific threshold.
Forward reconstruction at adjacent targets remains limited by rounding in
B+R*q. The reviewer regression covers all durations/models and decreasing M1.

The same review identified nonzero inverse solutions rounding to binary64 zero
for extreme finite q. Return `arithmetic_underflow` with absent numeric values;
only an exact baseline target can yield available zero rainfall. This explicit
unavailability refines the accepted prohibition on zero placeholders.
