# Return support feasibility contract

2026-10-08. Roger authorized the feasibility test proposed in
[the alternatives assessment](return-alternatives.md). One fixed rule; no tuning,
release, vendoring or deployment. Baseline remains wepp_260803 at 10 cm.

## Physical and source rules

Retain MIXPEAK's hourly Pr+Ps, native peak floor/cap, erosion effective duration,
water-balance scheduling and all physical hillslope calculations unchanged from
the hourly candidate. Retain the isolated midnight-state repair as the immediate
parent. Do not bring in the old channel-patch bundle or daily-mean estimator.

For an active return component, let Vs be the caller-allocated return volume,
and let the positive hourly weights define its normalized hourly maximum:

```text
Ps_source = Vs * max(weights) / sum(weights) / 3600
Teq = 3600 * sum(weights) / max(weights)
Ts = max(existing storm support, Teq)
return rate = Vs / Ts
```

Use a rectangular return source on [0,Ts], on the existing computational event
clock. Add the exact interval-overlap mean at each existing routing step. On
initial setup q0 receives the first source rate; subsequent days preserve existing
aggregate q0. No new source storage/carry, runtime flag or user parameter.

The rainfall reconstruction, its original support and volume-only caller scaling
remain untouched. Ts is local to return assembly; never write it into legacy
storm duration, tcs or erosion effective duration. Read storm support directly
for the return component even when rainfall is zero. Do not use an uninitialized
rainfall-local duration on that path.

The reconstructed return rate is a ceiling-constrained approximation; it need
not attain the hourly maximum. This explicitly changes source timing/shape, not
the physical peak estimator. Reject invalid/nonfinite/negative operands or support
beyond the existing day instead of clipping water or silently changing support.
No rain-fraction or return-dominance threshold. No-return/out-of-scope paths remain
the parent's paths.

## In-band version 3

Use `WEPP_PASS_COMPONENTS 3`, `SRC3`, and `SOURCES3` to distinguish this source
assembly contract from literal-hourly v1 and daily-mean v2. Keep the v1 payload
layout unchanged: Vr, Qr, Vs and 24 hourly weights, at existing supplemental
precision. The weights remain hourly source evidence and determine Teq; their
clock positions do not determine channel forcing in v3. This avoids additional
fields or a transport redesign during feasibility.

Legacy files remain readable for reader compatibility tests. V1, v2 and unknown
component headers are rejected by this candidate; do not reinterpret them as v3.
New simulations always generate matching-build passes. Existing date/index,
finite-value and count checks remain. Isolate the matching native interchange
reader; installed extensions and production files remain unchanged. Ordinary
Parquet schema stays unchanged. PASS-combination workflows remain outside the
already-incomplete compatibility envelope; no promotion is implied.

## Bounded execution

First demonstrate hourly peak/state preservation on both original H106 triggers
and Ksat/no-return controls. Native source tests must cover pure return, mixed
flow, the 43.484 mm rainfall control with 0.01 mm late return, vanishing rainfall
and return, partial endpoints, first-day and subsequent-day boundaries, invalid
support, and volume/peak ceiling under existing caller scaling.

If those checks pass, run complete Cedar and representative independent cases
with fresh matching-build passes and native conversion. Compare baseline, hourly
state-repair parent and v3: full/annual/daily/event water, source and outlet
sediment, peaks, timing, dry weather, new pulses and the existing integral-ledger
discrepancy. Inspect earlier portions of each event, not just disappearance of
the old 01:10 peak. No exact closure or newly chosen fit-score threshold.

Stop if the fixed rule merely moves the pulse, materially worsens ordinary
behavior, changes hillslope physics, or needs additional mechanisms. Preserve
failed evidence. No phase shifts, duration multipliers, recalibration, soil-water
repair or alternative candidate to rescue this one during the authorized test.
