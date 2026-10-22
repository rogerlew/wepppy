# MC source and publication interface design review

Independent read-only scientific/correctness review, 2026-10-21. Native paths
refer to `/workdir/wepp-forest-release-20261009`. This design follows
[mc-continuity-review.md](mc-continuity-review.md) and the operator's decision
to preserve MC4/5. No native source was edited and no new routing or storage
authority is proposed.

## Findings and recommended boundary

**A volume correction is possible without changing the MC recurrence, but one
unconditional daily normalization cannot preserve all existing source contracts.**
The implementation must distinguish physical source intervals, point-rate
reconstruction, inherited boundary rates and already routed channel exports.
Scalar normalization can preserve a selected discrete template's relative
ordinates and peak index. It cannot generally preserve its supplied peak,
physical interval volumes and exact event support simultaneously.

The smallest complete accounting correction is to retain authoritative source
amounts/support, measure their actual consumed quadrature and boundary carry,
publish the accepted outlet integral consistently, and expose MC and geometric
diagnostics separately. Implement demonstrated source omissions independently.
Apply source normalization only to an isolated reconstruction with an explicit
target and feasible boundary conditions; do not normalize the aggregate channel
array, an upstream routed hydrograph, or a geometric-balance residual.

| Priority | Finding | Repair disposition |
| --- | --- | --- |
| High | Actual outlet rates and daily `chvol/tmpvol` disagree, so downstream has two different inflow amounts. | Integrate accepted outlet Q with MC's quadrature and use that same amount for publication and downstream transfer. Preserve the recurrence and independently observed storage definitions. |
| High | Fixed inherited q0 makes exact nonnegative daily-volume normalization impossible for some valid sequences. | Retain and identify source-interface carry; never subtract it from another source, invent negative rates, or silently reset q0. |
| Medium | Flat/return arrays are interval means but are consumed as points on several paths. | Preserve physical cells separately from the solver representation. Document and measure projection error and timing resolution; passing source-cell sums alone is insufficient. |
| Medium | Coarse point sampling can have zero positive-index samples for a positive-volume exponential event. | Do not silently drop it. Exercise the actual branch and adopt an explicit bounded projection/resolution contract; choosing a new support or resetting boundaries is not just a normalization denominator fix. |

## Actual source representations and consumers

The current flat branch integrates the continuous source V/T over each interval
(`src/chrqin.for:127`), retaining a fractional final cell and a separate time-zero
boundary value. MIXRETURN also constructs interval means
(`src/mixpass.for:170`). These cells are the accepted physical source contract;
their positive-index rectangle sum is V. A nonzero final cell does not mean
that the continuous event extends to the cell's right edge.

The exponential point branch samples an approximate shape, then normalizes its
positive-index rectangle sum to `rainvol` (`src/chrqin.for:145` through `:165`).
That is precedent for volume-authoritative amplitude correction **of a
reconstructed source**, not for normalizing an already routed outlet. The
exponential interval branch separately integrates its shape and needs independent
support/partial-cell checks; do not assume its denominators or end truncation
are certified by the flat-source tests.

| Source at MC boundary | Actual consumer quadrature | Consequence |
| --- | --- | --- |
| Side source, `mofapp=2` | Rectangle of interval means | Canonical flat/return cells already integrate to V; no blanket normalization is needed. |
| Side source, `mofapp=1` | Trapezoid of adjacent rates | A cell mean and a point rate are distinct representations, even when their daily totals happen to agree. |
| Top hillslope source, either mode | Trapezoid of adjacent rates | `mofapp=2` does not make the MC top boundary consume interval means. |
| Upstream routed channel | Trapezoid of its accepted `q1` points | Transfer the same array and integral; never reconstruct or normalize it again. |
| Uniform daily lateral/base/local term | Mode-dependent lateral rule, with previous q0 retained | Ordinary changes between days create a measurable endpoint carry term in point mode. |

The consumer's method and placement determine weights; `mofapp` alone is not
enough. Do not accidentally change KW3, whose top/output quadrature differs,
while repairing MC. Keep rain, return flow, lateral flow, groundwater, signed
local exchange and upstream channel contributions distinguishable until their
own accounting has passed.

## What a scalar source normalization can establish

Let s be an isolated, nonnegative reconstruction template, and Q(s) the linear
quadrature actually used by its consuming boundary. If all its ordinates are
adjustable, V>0 and Q(s)>0, then:

```text
alpha = V / Q(s)
q = alpha*s
Q(q) = V
```

This preserves the set of nonzero sample indices, relative ordinates, peak
index and all normalized timing moments of that **same discrete template**.
It changes amplitude, including the peak. It does not restore a missing sample,
resolve a substep pulse or make an interval mean into an exact point observation.
Use binary64 accumulation and finite/positive checks, with a precision-derived
final error bound after casting. A positive amount with zero quadrature is an
unrepresented source, not a license to divide by a tiny floor.

This is a defensible small source-interface correction where the reconstruction
contract already subordinates peak amplitude to known volume and all adjusted
points belong to that source. Preserve a separate copy of the canonical flat
or return cells: scaling those cells would invalidate their V/T overlap contract.
Normalize the solver template, not the physical source record.

The existing exponential normalization can use the correct consumer weights
where those conditions hold. Many events already have zero starting/ending
points, in which case rectangle and trapezoid sums agree and a denominator
change should have no effect. Retain those controls. A correction that changes
them materially needs another explanation.

### Fixed boundary values make normalization affine

On ordinary days WSHCHR retains yesterday's final `qinich/qlich` as q0 and
constructs today's points starting at index one (`src/wshchr.for:125`, `:197`).
If the inherited contribution q0 is fixed and s contains the adjustable new
points, the full-day trapezoid is:

```text
Q_total = dt/2*q0 + alpha*Q_free(s)
alpha = (V_target - dt/2*q0) / Q_free(s)
```

A nonnegative solution requires `V_target >= dt*q0/2` and a nonzero free
quadrature when the numerator is positive. For dt=600 s, q0=0.1 m³/s and a dry
day with V_target=0, the fixed endpoint alone supplies 30 m³. No nonnegative
choice of later points can make the daily integral zero. Aggregated q0 also
does not identify how much belongs to each constituent source; attributing it
requires retained component provenance, not a guessed split.

Normalizing only today's free points to V and then adding the inherited endpoint
double counts that endpoint contribution relative to an exact daily-V claim.
Subtracting it from an unrelated current-day source silently changes that
source's amount/timing. Resetting q0 changes the established boundary condition.
These are not routine denominator corrections.

## Conservative source cells and explicit quadrature carry

For a cell-conservative source array whose positive-index rectangle sum is V,
the existing trapezoidal consumption satisfies:

```text
B_start = dt/2*q0
B_end = dt/2*qN
V_consumed = V + B_start - B_end
```

This identity supplies a complete accounting contract without changing MC or
pretending that daily equality holds. B is a numerical source-interface
coordinate, not new soil water, groundwater or measured channel storage. Its
initial value must be documented; first-day q0 is not automatically zero.
With matching endpoint values and timestep across days, these terms telescope.
Changed timesteps or boundary replacement require their own observed transition.
Do not label arbitrary missing-source volume as B: calculate it independently
from the source endpoints and compare the remainder with a numerical error bound.

This is the recommended general baseline while preserving the current boundary
carry. It preserves the source-cell volume/support contract and reports the
consumer's actual numerical timing. It does not establish exact within-day
physical forcing at arbitrary temporal resolution. If exact per-day consumed
volume is required instead, a new boundary/source projection rule must resolve
the feasibility conditions above; changing only a scalar denominator cannot.

## Coarse-grid limits: volume is not timing

Two exact arithmetic examples isolate the limits:

1. A 60 m³ flat event lasting 60 s on a 600 s grid has canonical mean q1=0.1
   m³/s and later means zero. With a dry inherited q0, MC's point trapezoid
   already integrates to 60 m³. Interpreted as a linear point hydrograph, its
   support spans 0–1,200 s and its centroid is 600 s; the physical flat event's
   centroid is 30 s. No scalar normalization fixes that timing discrepancy.
   On the first day, the flat branch additionally sets q0=1 m³/s; the same
   trapezoid is 360 m³. Scaling by 1/6 fixes that integral while changing the
   amplitude and leaving the selected template's timing unchanged.
2. To force every desired interval mean m exactly while keeping a continuous
   trapezoidal boundary, the points must satisfy `q_n=2*m_n-q_(n-1)`.
   For means `[0.1, 0, 0]` and q0=0, this produces `[0, 0.2, -0.2, 0.2]`.
   Exact interval volumes, nonnegative points and that initial endpoint cannot
   all hold. Clipping the negative point breaks the imposed interval volumes.

Thus “preserve timing” must name the object: physical source support, the
existing sampled template, interval-integrated timing, or an approximation with
a measured resolution error. A source template can preserve sample indices
while its implied interpolation extends beyond physical support. Neither a
point normalization nor the MC-preserving requirement removes this limitation.

A bounded projection from physical source cells is an implementation design
that can be documented and tested under the authorized interface repair.
Its resolution error must be explicit. Automatically refining the solver grid,
changing the recurrence's input averaging, altering midnight state carry, or
switching methods by event would change the routing/boundary contract and needs
a separate method decision. Do not use such changes as hidden fallback paths.

## Outlet publication without redefining storage

Use the accepted, post-clipping MC outlet points and their actual timestep:

```text
V_export = dt*(sum(q1[1:N]) + (q1[0]-q1[N])/2)
```

`chvol`, `runvol`, `tmpvol`, EBE outlet amounts and downstream channel volume
intake must describe this same accepted transfer, within documented rounding.
Continue passing the same q1 array to downstream routing. This is an interface
consistency correction; it neither rescales Q nor selects a different storage
authority. It can change downstream hydrology because the earlier daily intake
was inconsistent, so isolated recurrence parity does not guarantee whole-network
output parity.

Retain the independently computed geometric diagnostic G=`aavg*length` at
`src/wshchr.for:618`. Do not follow exact-rate chvol with the existing assignment
`sfnl=sinit+volint-chvol` (`:657`): that would replace G by a residual-derived
store. Likewise, do not force the printed balance to zero. Preserve schema
positions with a clearly documented diagnostic interpretation, and expose the
MC ledger through separate observations rather than silently substituting H
into the old storage field.

Check the q0-only export case, positive-tiny clipping, initial state, sediment/
solute consumers of `runvol/tmpvol`, and peak/duration metadata. A peak scan
excluding q0 must not erase a positive accepted trapezoidal volume. Publication
repair must include the actual downstream WSHCQI transfer path, not just a
formatted daily report.

## Complete accounting contract and acceptance limits

For one channel/day define these independently observed quantities:

| Symbol | Meaning |
| --- | --- |
| P | Scheduled net source amount from physical inputs and accepted signed exchanges; retain gross additions and withdrawals separately. |
| I | Actual top plus lateral volume consumed by the native MC quadrature. |
| E | Accepted outlet integral after the existing clipping rule. |
| M | Sum of per-cell MC increments `K*(X*delta(I_node)+(1-X)*delta(O_node))`. |
| H, C, J | Algebraic endpoint coordinate, within-day coefficient revaluation and daily grid/boundary transition, as derived in the continuity review. |
| B_out | Trapezoidal integral of exported minus raw outlet Q, including time zero. |
| G | Independently evaluated geometric storage diagnostic. |
| R_MC | Observed regular-step coefficient/update arithmetic residual, with skipped/guarded paths separately identified. |

The audit must reconcile, without deriving a store from the desired result:

```text
I - E = M + R_MC - B_out
M = delta(H) - sum(C) - J

R_geometric_report = P - E - delta(G)
                   = (P-I) + (M-delta(G)) + R_MC - B_out

published_outlet - E = 0
downstream_received_volume - upstream_E = 0
```

P-I is reconciled by observed component conversion/carry and actual omissions;
it is not automatically zero or automatically excused. M-delta(G) reports the
difference between numerical and geometric conventions. Under the operator's
MC contract it is not an invented source, physical sink, or geometric-equality
failure gate. A nonzero legacy geometric balance after truthful outlet
publication must be explained by this decomposition, not hidden or relabeled
as a closed physical inventory.

The minimum acceptance matrix exercises rain/return separately and mixed,
flat/exponential sources, side/top placement, both modes, first/subsequent days,
zero and nonzero q0/qN, substep and fractional/full-day duration, positive and
signed local exchange, both MC methods, and an actual two-channel cascade.
Retain independent physical-cell sums, consumed fluxes, timing/peak changes,
recurrence terms, publication and downstream intake. Report unresolved
coarse-grid timing and availability limits explicitly. These checks support
bounded interface repairs; they do not certify all channel hydrology or change
the operator's selected MC/storage contract.
