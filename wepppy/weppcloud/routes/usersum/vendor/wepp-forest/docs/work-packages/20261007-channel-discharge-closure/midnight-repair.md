# Hourly-estimator midnight diagnostic and repair

2026-10-08. Roger authorized a full defect diagnostic and implementation if
feasible, with a hold if the diagnostic shows the repair cannot be defended.
This supersedes the preceding assessment-only stop. It does not authorize a
daily-mean estimator, release, vendoring or deployment.

## Freeze before execution

Retain the hourly physical estimator, native rainfall calculation, total source
volume and hourly bins. Baseline remains wepp_260803 at 10 cm; use the archived
hourly component candidate as the integration parent, never the daily-v2 source.
Daily-v2 files and all prior evidence remain untouched.

Diagnostic hypotheses:

- H1: interval-mean return rates consumed as point values shift source forcing
  across step/day boundaries; this is distinct from actual channel storage.
- H2: WSHCHR discards the previous internal routing profile and linearly rebuilds
  it from inlet/outlet endpoints each day, changing the continuation state.
- H3: changing the number of channel segments complicates a local H2 repair;
  an unproved interpolation or broad storage reconstruction is not automatically
  admitted as the solution.

First use actual WSHCHR, CHRQIN, MIXRETURN and MANN in a diagnostic driver. Compare
an uninterrupted two-day sequence with the same sequence split at midnight.
Use frozen coefficients/grid as a causal control, and native grid selection as
a separate feasibility check. Compare internal state, sampled outlet volume,
peak and timing. A diagnostic carry lane may retain the exact same-grid state;
it must stop on a different grid rather than silently invent a remapping rule.

Target: the same forcing and discretization should not acquire a new trajectory
solely because a day boundary discards state. Roundoff bounds in native arithmetic
are measurement checks, not global hydrologic acceptance tolerances. The
uninterrupted native calculation is a restart reference, not exact physical truth.

If a local repair is defensible, add a failing test, isolate the behavioral
patch, and validate fresh same-build source passes and watershed outputs against
the baseline and archived hourly candidate. Include both original triggers,
ordinary/day-boundary controls, full Cedar, representative independent watershed
and regression checks before recommending acceptance. No patch pile, source
timing smoothing or unapproved support extension to manufacture a pass.

If preserving state entails unresolved spatial/state or source-time semantics,
stop at the diagnostic evidence and identify the precise decision. No comprehensive
conservation or universal numerical-convergence campaign is required.

Status: [diagnosis, implementation and validation complete](midnight-repair-results.md).
Retain the isolated state-restart correctness patch for review; hold the full
hourly candidate because the target late pulses remain. Native grid-change
feasibility was subsequently tested using bounded nodal interpolation before
implementation; no unproved global routing or storage replacement was introduced.
