# ADR-0062: Local Staley rainfall and result composition

## Status

Accepted for local implementation. The operator explicitly approved R02 in the
execution conversation by replying “YES” to returning unavailable results when
a CLI design rank exceeds positive-sample support. Final local validation and independent reviews passed.

## Context

The accepted M1 predictor/scalar interfaces take rainfall accumulation, while
Climate artifacts contain peak intensity. CLI exports also round design values,
use the full recurrence request for rank assignment, and clamp sparse samples.
The new local composition must preserve scientific identity and missing states.

## Decision

Convert peak intensity in mm/hour to accumulation in mm by multiplying by
`duration_minutes / 60`, exactly once; durations are 15/30/60 minutes. Preserve
full precision. Zero is valid event rainfall under the accepted scalar intercept
contract, while zero frequency placeholders yield unavailable design scenarios.
Keep fixed postfire predictors across every climate event. Do not aggregate
probabilities across durations or assign annual debris-flow probabilities.

Require explicit frequency source, requested intervals from 1/2/5/10 years,
durations and inverse targets. CLI uses the Climate-owned `weibull_series` PDS
method and its complete supported recurrence context before selecting subsets.
CLI CSV is rounded parity evidence; NOAA metric PDS intensity is a separate
source. Invalid positive infinite duration samples make CLI design unavailable;
removing those samples would silently shift the Climate ranking. Negative/NaN
samples follow Climate's exclusion from positive ranks. No new sample cutoff.

R02 returns `unavailable` / `insufficient_positive_samples` when the zero-based
requested rank is at least the positive duration sample count. Preserve the
requested rank and sample count; intensity, accumulation and probability are
null. Supported ranks and other durations remain available. An empty positive
series retains `no_positive_samples`. This changes only the local adapter;
Climate continues exporting its established clamped CSV values, which remain
valid parity evidence. No last-observation substitution or extrapolation occurs.

## Decision provenance

- Decision Venue: Codex execution conversation, 2026-09-09, America/Los_Angeles.
- Participants Present: repository user/operator and Codex.
- Decision Owner(s): repository operator; execution authorized with “execute
  docs/work-packages/20260909_staley_rainfall_results/”. R02 was explicitly approved by the operator’s subsequent “YES” response.
  No participant name or broader scientific endorsement is inferred.
- Implementer(s): Codex.
- Change Summary: additive local event/design/inverse outputs from existing
  snapshots; no changes to Climate, numerical coefficients, NoDb, RQ or UI.

## Rationale and alternatives

Clamping a requested unsupported rank can look like a supported design estimate.
The owner selected unavailable rows to expose that limitation while preserving
other results; flagged clamping was considered and rejected for this adapter.

Use the existing scalar engine and Climate estimator to preserve accepted
behavior. Rounded CSV input would unnecessarily lose intensity precision.
Recomputing ranks for a subset would change the shared helper's assignment
context. Silent NOAA fallback would obscure source identity. Automatic source
rebuilding and browser defaults are separately scoped. Materializing the real
30,936 duration rows takes about 2.3 seconds and supports repeated bounded queries.

## Evidence

- [Contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md)
- [Package](../work-packages/20260909_staley_rainfall_results/package.md)
- [Source inventory](../work-packages/20260909_staley_rainfall_results/artifacts/source_inventory.json)
- [Decision register](../work-packages/20260909_staley_rainfall_results/artifacts/decision_register.md)

## Risk and rollback

Pinned hashes establish local identity, not upstream freshness or scientific
validity. Conditional event scenarios with current predictors do not model
postfire recovery. Retain area warnings. Validate rank-boundary and clamped-CSV parity behavior
before completion. Rollback removes the additive local
helpers and newly generated bundles; existing project sources remain untouched.
