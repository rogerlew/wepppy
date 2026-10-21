# Muskingum–Cunge continuity probe QA

Date: 2026-10-21. Reviewer: independent secondary QA agent.
Scope: read-only review of native `tools/mc_continuity_probe.py`, its actual
WSHCHR recurrence instrumentation, the 16 three-day controls, the eight native
cascade controls, and the dry-interior recurrence guard. This review
follows the operator's MC-preserving continuation: geometric channel volume is
not promoted to routing authority. No implementation source was edited here.

## Disposition

The revised probe is suitable for the bounded MC4/MC5 diagnostic investigation.
The local recurrence equation is correct, diagnostic writes preserve the tested
rates and publication values, and the demonstrated parser integrity defects
were corrected during review. The final one-guard correction is acceptable for
its narrow purpose: route retained interior discharge when current boundary and
lateral inputs are dry. It preserves the existing MC equations and volume
authority. No blocking quality finding remains for that change. Full source,
sink and publication closure remains open; the combined day-boundary jump is
not, by itself, evidence of a transported volume defect.

Reviewed v3 parser SHA256:
`7f56ff16d69d7b140f86988fc43bc57fa0800ae03f991b8e7dc51cf2e8d2afd4`.
V3 instrumented WSHCHR SHA256:
`bb8b008eaa49531ed0d93d44b5b761f1060b05dc17bd391788b874e0629acac0`.
The v1 and v3 native stdout files are byte-identical; v3 changes the interpretation
and validation of those observations. All 16 v3 JSON case summaries were
independently regenerated from their raw stdout using the final parser.

## Recurrence and field interpretation

For one segment and interval, let `I0/I1` and `O0/O1` be the actual upstream and
downstream discharge at the two endpoints, `K=tk`, `X=cx`, `dt=dtchr`,
`dx=dxchr`, and `qL=qlavg` in volume/time/length. The native coefficients have
denominator `D = 2*K*(1-X) + dt`. Rearranging the native discharge recurrence gives:

```text
S0* = K * (X*I0 + (1-X)*O0)
S1* = K * (X*I1 + (1-X)*O1)
S1* - S0* = dt * ((I0+I1-O0-O1)/2 + dx*qL)
```

The probe evaluates both endpoint expressions using the same coefficients from
that actual interval. This is the correct local identity for MC4 and MC5, subject
to native floating-point arithmetic. `S*` is a coefficient-weighted diagnostic
state with volume units; this derivation does not assign geometric or independent
physical-water authority to it.

| Diagnostic | Valid interpretation |
| --- | --- |
| `mc_increment_sum_m3` | Sum of interval changes using each interval's own coefficients |
| `within_day_coefficient_revaluation_m3` | Change from evaluating an unchanged shared nodal state with successive coefficient sets |
| `endpoint_identity_residual_m3` | Telescoping bookkeeping check; not independent proof of continuity or record completeness |
| `day_boundary_combined_jump_m3` | Combined change across coefficient selection, nodal interpolation and caller boundary changes; not attributed yet |
| `top_trapezoid_m3`, `outlet_trapezoid_m3` | Endpoint quadrature used by the MC recurrence |
| `lateral_trapezoid_m3` | Lateral integration for `mofapp=1` |
| `lateral_rectangle_m3` | Lateral integration for interval-average mode |
| `outlet_clipping_volume_m3` | Routed-minus-raw outlet integral, including the initial endpoint contribution; `positive_time_clipping_volume_m3` excludes that separately reported contribution |
| `reported_storage_start_m3`, `reported_storage_end_m3` | Publication-state values after native channel-volume clamps/reassignment; not necessarily unadjusted Manning geometry |

The absolute operand scale now uses `dt*Q` and `K*Q` terms instead of the
cancellation-small net flux/increment. That is appropriate for establishing a
roundoff bound. A bound still needs to be stated before any scientific acceptance
claim. The largest observed local identity residual in these controls is
0.00012948812514 m³. Its smallness alone does not validate published daily volume.

## Independent parity and trace checks

A separate native control was compiled with the same `/usr/bin/gfortran` flags,
three-day driver, prescribed forcing and grid/reference overrides, but without
internal MC diagnostic writes. All 16 configurations had exactly identical
432-row `Q` trajectories. A second control observed completed-call COMMON values
from the driver; all 48 records of input accounting, published outlet volume,
initial reported state and final reported state matched the instrumented probe
exactly. This is probe noninterference under identical synthetic forcing, not
parity between synthetic forcing and ordinary hillslope source assembly.

All 48 trace-days independently contain every expected segment/time pair,
145 ordered boundary samples, complete initial/final node sets and one publication
record, with finite values. No routed-versus-raw outlet clipping or initial
outlet-boundary difference occurs in these controls. Their zero clipping therefore
does not exercise the clipping mechanism.

Evidence is retained under
`/workdir/watershed-physical-water-repair-20261021/mc-continuity-qa-v1/`:

| Receipt | SHA256 |
| --- | --- |
| `parity-receipt.json` | `47873dabe610029640d00de1d22d5a06a45ea54d531d5ebb2f681aaadd6c0be5` |
| `publication-parity-receipt.json` | `8dcdb4d350244c2e380c5a2b5773b5919a6bdfe7a86ea0344dd9ba70600d85ac` |
| `parser-final-receipt.json` | `a173ebd31804bceb9827520c1a4d73e6d1dad8493c23eb7643609650e3658287` |
| `cascade-field-review.json` | `6707f8f0dae6b36020eead8253a7e5c70e487db5667918701d2830d5df8f35cf` |
| `guard-final-review.json` | `b98dfce7f823ca1d71c8c10ee5dd9e4993498cfac8c99c6f791bceb52156de72` |

The first two receipts retain compiler commands, source/binary hashes and
per-case results. Native source and driver inputs were matched to the v1 manifest
before the independent builds.

## Findings resolved during review

1. **Record completeness and finiteness.** Initial summaries accepted omitted
   or duplicate MCSTEP records, reordered MCBOUND samples and NaN output.
   Missing/duplicate steps still produced a roughly 4.55e-13 m³ endpoint
   identity residual, demonstrating why that identity cannot validate a trace.
   The revised parser rejects all four corruption controls.
2. **Publication uniqueness and chronological transitions.** An extra conflicting
   MCPUB record previously replaced day-two outlet volume with 99,999 m³ without
   error. Complete day blocks supplied as 3/2/1 generated a spurious -2,756.2974 m³
   transition in a fixed control. Duplicate publication now fails explicitly;
   reversed day blocks are canonicalized and reproduce the baseline summary
   exactly. Previous endpoints are grouped by channel for the cascade extension.
3. **Misleading labels and scales.** The combined boundary jump is no longer
   labeled coefficient revaluation alone. Post-publication states are named
   reported storage, and precision scales use absolute operands. Initial outlet
   mismatch and output clipping are separately exposed.

## Final guard and cascade review

The `src/wshchr.for` change extends recurrence eligibility with
`any(qs(1:nseg,it-1).ne.0.)`. Coefficient selection, recurrence equations, grid
handling, state retention and publication formulas are unchanged. An exactly
empty profile still skips the recurrence; no new magnitude threshold discards
small retained states. The explanatory comment states the reason for the guard.

Independent execution of `tests/test_channel_state.py` with `/usr/bin/gfortran`
passes all 21 tests. The eight new controls cover MC4 and MC5 with an all-zero
profile and a unit initial discharge at nodes 1, 4 and 7 of an eight-segment
channel. Each requires 144 finite, nonnegative outlet observations; the zero
control remains exactly zero. The MC4 controls additionally compare exported
volume with the fixed-coefficient initial inventory `K`, using an explicit
binary32 accumulation bound. The MC5 controls establish pulse propagation and
finite behavior, not independent variable-coefficient conservation. The baseline
six failures and two zero-control passes make these tests sensitive to the
corrected branch. No production/test source was edited by this reviewer.

The cascade driver calls actual WSHCQI and WSHCHR for the downstream channel;
channel identity is added only to diagnostic labels. Independently checking the
final eight cases establishes exact equality for all 3,480 upstream-outlet versus
downstream-inlet rate samples and all 24 published daily-volume transfers.
The daily-volume versus rate-integral difference already exists upstream and is
carried through the two respective interfaces. This is not evidence of loss at
the transfer edge and is not claimed resolved by the guard.

All 16 final continuity and eight final cascade summaries were independently
regenerated with the current strict parser. Their rates, nodal states, boundaries
and publications exactly match the corresponding pre-guard controls. The final
parser also retains native `c1/c2/c3` observations, reports recurrence rounding,
and includes the initial endpoint in the total clipping integral. Its explicit
expected-channel set rejects removal of an entire downstream channel; that
corruption control passed independently. The continuity manifest predates the
last parser-only change; `guard-final-review.json` pins the current parser and
proves it reproduces all retained summaries against the same native source.

| Final reviewed file | SHA256 |
| --- | --- |
| `src/wshchr.for` | `1b3a5d7dc2c6aa9837230667d4e3ba9c203e05b1992c197c3a9ccafb6f1e9bad` |
| `tests/test_channel_state.py` | `ef17534bbb34e63ec9f1613ed2843e5ce6218d52220959512c30a711725bdb52` |
| `tools/mc_continuity_probe.py` | `9639bb5c8725eea51d4f6cd8cc876f326d906c534d8ec84dbf485cbd3ce5f0c5` |
| `tools/mc_cascade_probe.py` | `bd8770f14fc66a4ad224284c63ff29368c14bf7c35bc88ac12f063cdfc1d2f6a` |

Producer gate receipts, inspected without repeating the broad runs, report
369 passes, four expected failures and two existing tarfile deprecation warnings;
the hillslope watchlist passes all 12 cases. Both binary smoke commands pass
their three-year hillslope control. The retained
29 paired replays include the actual 400-year run. Their `output/` files are
byte-identical except three daily-side channel-water-balance rows, with largest
printed change 1e-6 mm. Routing trace changes also include seven channel-days
expanding from one compressed daily row to 144 samples. The keyed comparison
`mc-guard-cascade-aligned-differences.json` avoids positional misalignment and
reports a maximum shared-rate change of 2.34e-8 m³/s across nine changed cascade
channel-days. These are documented behavior changes from retaining small tails,
not a claim of global byte parity.

## Remaining limits and non-blocking quality debt

The `fixed_grid=8` lane also fixes the reference discharge at 0.5 m³/s through
`midgrid` phase 1. Describe it as a fixed grid/reference control; adaptive-versus-
fixed differences are not isolated grid effects. MC5 still updates coefficients
at each segment/time step despite that reference override.

The normal continuity controls maintain positive baseflow; the separate eight
interior-state controls now exercise dry-boundary routing and the all-zero skip.
Neither set demonstrates general outlet-clipping behavior. The strict parser
correctly prevents a missing recurrence row from being silently interpreted as
zero. General traces with legitimate skips need explicit skip observations or a
separately bounded probe, not relaxed completeness checks.

The current parser intentionally assumes 144 intervals, three days and synthetic
channel/day encoding. Callers now supply their intended channel set explicitly.
Before reusing it for general traces, parameterize those dimensions and validate
timestep/segment-length consistency. For these controls, expected dimensions
and identities were independently checked.

Small maintenance improvements: assert the expected count of driver string
replacements, retain include-profile hashes and compiler identity with the tool's
own receipts, and distinguish fixed-reference overrides in receipt metadata.
These do not invalidate the retained controls or block the narrow guard. Broader
coefficient/grid/boundary attribution and full source/sink/publication closure
remain separate investigations and require their own evidence before additional
production changes.
