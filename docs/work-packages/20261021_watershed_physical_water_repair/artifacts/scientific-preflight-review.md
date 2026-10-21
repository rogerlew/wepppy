# Scientific preflight review

**Updated routing interpretation:** [mc-continuity-review.md](mc-continuity-review.md)
supersedes geometric-equality acceptance in S2 under the operator's selected
MC-preserving audit. The narrow groundwater, hourly-allocation and source-cell
findings remain applicable.

Reviewed 2026-10-21 by the independent scientific/correctness reviewer against
native baseline `6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb`, the predecessor audit,
the active repair ExecPlan, and the proposed native physical-water contract.
Native paths below are relative to `/workdir/wepp-forest-release-20261009`.
This is a source and contract review; no model source was edited for this review.

## Decision

Groundwater initialization, bounded hourly allocation with explicit failure for
unmet withdrawal, and volume/support-authoritative flat source cells are
scientifically defensible narrow corrections. They may proceed with their
specified native regressions. Flat source-cell conservation does not certify
the consuming channel solver. Channel exchange timing, sink availability, solver
quadrature, and physical storage need additional executable evidence before
the complete routing contract can be ratified. The four local fixes are not
sufficient evidence for a repaired watershed-routing claim.

## High-priority findings

### S1 — Source-cell volume and solver-consumed volume are distinct

`src/chrqin.for:116` drops fractional flat intervals and does not reconcile
volume greater than peak times duration. The proposed policy is defensible:
preserve requested volume V and positive support duration T, use continuous flat
rate V/T, and integrate each interval's overlap with [0,T]. The supplied peak is
then subordinate when all three operands conflict; this changes peak behavior
explicitly rather than extending duration or discarding water.

However, `src/wshchr.for:510` through the Muskingum-Cunge update at line 567
uses trapezoidal upstream rates. Its lateral input uses a trapezoidal average
in point mode and a cell rate in cell-average mode (`:515`). CHRQIN's existing
pointwise exponential normalization instead uses the right-endpoint sum
(`src/chrqin.for:141`). A source-cell test cannot establish native forcing
conservation across this interface. For example, baseline flat q(0:3) =
[1,1,1,0] at 600 seconds has 1,200 m³ in the positive-index sum and 1,500 m³
in the trapezoidal integral. Initial channel storage is also nonzero in this
first-day steady-state initialization and must be observed separately.

Required contract: distinguish physical support, cell-integrated source volume,
point boundary values, and solver state. Index zero carries boundary/state
information, not a separate cell volume. A partial final cell can have a nonzero
mean although its endpoint is after T; that must not be described as extending
physical event support. Verify the conversion using the actual solver equations,
including first day, midnight continuation, and pulses shorter than one step.
Do not normalize downstream routed discharge merely to make a source test pass.

### S2 — Published geometric storage is not the MC recurrence's storage

For fixed K and X, algebraic rearrangement of the native update gives:

    S(n) - S(n-1) = dt/2 * [I(n)+I(n-1)-O(n)-O(n-1)]
                   + dt * lateral_mean * dx
    S(n) = K * [X*I(n) + (1-X)*O(n)]

Here K is `tk`, X is `cx`, and I/O are adjacent spatial-node discharges.
This is a derivation of `src/wshchr.for:510` through `:567`, not an external
claim about all routing implementations. Summing spatial reaches cancels their
internal transfers. In contrast, reported storage is the average of inlet and
outlet Manning areas times total length (`:576` through `:618`). Those stores
are not generally equal. The final published outflow comes from the geometric
balance identity and storage is then reset from that identity (`:654` through
`:657`), rather than being independently integrated from routed discharge.

Daily changes in K, X and the spatial grid add another boundary. The `ipeak=5`
path changes coefficients within the day (`:523` through `:565`), while
`src/chrstate.for:14` interpolates discharge when the spatial grid changes.
Neither operation by itself conserves physical cross-sectional water volume.
Also, `cxmin=-10` permits negative X, so simply publishing MC's algebraic
storage as physical stored water is not a sufficient correction.

Required evidence: retain all spatial node states, coefficients, clipping
amounts, and both beginning/end geometry. Derive and test each solver's actual
discrete balance, then compare it independently with physical storage and
published output. A fixed-coefficient algebraic control isolates bookkeeping;
it cannot validate variable-coefficient or regridded physical storage. A
remaining discrepancy blocks full acceptance. An arithmetic correction within
the existing model can proceed under the repair plan; replacement of routing
physics or a new storage assumption needs an explicit, reviewed scope decision.

### S3 — Negative hourly demand needs availability checks at every magnitude

`src/watbal_hourly.for:511` caps a negative layer allocation only when the
original hourly demand is below -0.00001 m. Smaller negative demand can make
soil storage negative. The single-layer branch (`:494`) has no availability cap.
Removing the continuation cutoff alone therefore does not meet the signed-input
contract. `st` is available soil water (`src/cwater.inc:40`); frozen water is
tracked separately and cannot be silently withdrawn as liquid.

The smallest defensible correction preserves the existing positive allocation
weights, continues through at most `nsl` layers, and accounts for the entire
remainder. Apply negative availability limits for every magnitude and layer
count. Preserve subsequent percolation, upward saturation handling and surface
return flow, which already exports excess water (`src/watbal_hourly.for:567`,
`:866`, `:895`). Do not clamp positive allocation to capacity and discard excess.

If demand exceeds available liquid storage after all layers, fail with explicit
date/OFE/hour, demand, available water and remainder. This is defensible failure
for an inconsistent input state, not a claim that the generating hydrology was
repaired. Silently dropping demand, creating negative storage, or revising an
already routed runoff flux would obscure the inconsistency. Any occurrence in
the full replay matrix remains an unresolved upstream allocation defect and
blocks the affected case. Do not introduce a fitted residual tolerance.

### S4 — Channel local exchange requires an independent source/sink contract

`src/wshchr.for:151` forms local net lateral volume, but `:172` assigns that
water by multiplying side-hill surface volumes. With no side surface volume,
positive local water disappears from the rate arrays; with side flow, the local
water inherits an unrelated source's temporal support. The negative branch at
`:157` can impose a uniform negative lateral rate even when instantaneous water
is unavailable. The solver later clips outflow (`:450`, `:573`), so negative
forcing plus clipping is not a conservative sink implementation.

Use separately accounted hill surface, lateral, groundwater, channel rainfall
excess, and channel soil exchange terms. `rtrans` is a net diagnostic formed
after the channel water balance (`src/wshdrv.for:1012`); it is not necessarily a
nonnegative physical infiltration flux. `chnvol` originates in rainfall excess
before recession infiltration (`src/wshirs.for:266` through `:280`), while later
water-balance surface return may increase runoff. Thus negative `rtrans` can
reflect real channel soil release. Preserve and observe that source.

For a positive daily-only local source, a separately identified daily-uniform
forcing is a possible minimal approximation, but its support choice must be
explicit and reviewed. If rainfall-excess timing is already available, preserve
that support. For sinks, first measure when and where water is available. A
uniform sink cannot draw on a future pulse or a dry reach. Deferring unmet demand,
proportional removal from arriving water, or changing the soil/routing coupling
are different physical assumptions; do not conceal one inside a clamp. Retain
requested and applied sink volumes and treat unreconciled demand as failure.

## Groundwater contract accepted with initialization conditions

At the first OFE of the first simulated day, initialize depth/1000 times the
sum of all local OFE areas and reset prior withdrawals and recharge accumulation.
Do not use terminal area or a constant-width shortcut. The existing recurrence
at `src/contin.for:1107` is:

    G_pre(d) = G_pre(d-1) + recharge(d) - baseflow(d-1) - seepage(d-1)
    baseflow(d) = bfcoeff * G_pre(d)
    seepage(d) = dscoeff * G_pre(d)
    G_post(d) = G_pre(d) - baseflow(d) - seepage(d)

For the first day, substitute initialized groundwater for prior G_pre and zero
prior withdrawals. The observed post-withdrawal store is the end-of-day physical
store when today's emitted fluxes are counted. Do not count today's outputs
against a pre-withdrawal endpoint without this convention. Preserve daily Dp
recharge as a sum of local-area volumes; it is internal to a combined soil plus
groundwater domain. Do not reinitialize at an ordinary year boundary.

`igwstrv`, `ibfv` and `idsv` are scalar COMMON state (`src/cchrt1.inc:14`), so
explicit start initialization is necessary for sequential hillslopes as well as
new processes. Coefficients that demand more than available storage are a
separate unsupported-input concern; do not silently retune coefficients here.

## Additional coverage risks discovered

1. **Transferred groundwater at the ephemeral/perennial boundary:**
   `src/wshcqi.for:145` adds deferred upstream groundwater to `bflwpere`, and
   `:206` includes it in incoming volume. In WSHCHR the only positive use is the
   first-day initial outflow (`src/wshchr.for:261`); it is absent from the daily
   qin/qlat assembly and later reset (`:707`). This is a source-confirmed missing
   assembly path, requiring a bounded threshold-crossing cascade regression
   before groundwater-routing certification. A direct baseflow-only hillslope
   control does not exercise it.
2. **Impoundment transfers:** WSHCQI counts `nitop`, `nileft` and `nirght` volumes
   (`:167`, `:199`), whereas WSHCHR's explicit source calls use hillslopes and
   channels. Impoundment timing remains a coverage gap; no certification from
   the ordinary hillslope matrix should extend to that path.
3. **Kinematic-wave storage:** `src/wshchr.for:452` computes Manning depth only
   for nonzero nodes but adds area for every node. A zero node can reuse the
   previous `y`; observe a dry downstream node after a wet one. Its spatial
   area average also gives endpoints full equal weight. Do not infer physical
   storage accuracy from a passing MC case.

## Portable native harness recommendations

| Boundary | Production execution and independent oracle | Essential controls |
| --- | --- | --- |
| Groundwater | Compile the verbatim CONTIN block, then paired complete decks; oracle uses known areas, initial storage and manually specified recharge. | Single/60-40/20-30-50, unequal widths, zero/nonzero initial storage, nonzero seepage, day two, year boundary, sequential hillslopes and disabled mode. |
| Hourly allocation | Compile the exact allocation block and retain before/after layer stores and remainder; complete WATBAL replay verifies later exports. | Positive and negative below/at/above cutoff, one/multiple layers, zero tillage depth, tillage reaching/beyond profile, dry/frozen/saturated states, partially dry layers, profile exhaustion, unequal OFEs. |
| Flat source | Existing CHRQIN native harness, parameterized for point/cell modes, nt0, timestep and prior q(0); compare interval overlap analytically. | 1,200 aligned; 900 fractional; 1,000 incompatible peak; substep duration; zero/tiny volume; exponential and mixed return controls; volume, peak/support and midnight boundaries. |
| Channel assembly | Actual WSHCHR with a read-only tap immediately after assembly; separately expose each physical source and sink. | No side hill; zero-flow side hill; top/side equality of source volume; signed local exchange; zero/positive storage; lateral/baseflow only; threshold-crossing cascade; absent-source indexes. |
| Solver/storage | Existing midnight driver extended with read-only full spatial state and coefficient taps; independently evaluate native discrete equations and geometry. | Methods 3/4/5, both approximation modes, fixed and changing grid, steady/impulse/late pulse, dry-down, signed sinks, channel geometry variants, tributaries and cascades. |

The portable tests drafted in `tests/test_physical_water.py` reproduce the four
specific audited failures with real production blocks/routines. At review time,
they are appropriately narrow M1 controls: their positive-only soil cases and
right-endpoint channel-source sums do not yet cover the contracts above.
Read-only probe off/on parity and full executable paired replay remain required.

## Scope and residual risk

This review approves the narrow contracts above, not full model accuracy or
field calibration. Large daily/hourly partition differences remain an explicit
scientific limit. Preserve ASCII PASS v3, WAT schemas, event thresholds, calendar
fixes, dated release artifacts and defaults. Review the concrete routing remedy
and retained evidence before deciding whether the remaining model boundary can
be corrected within scope; do not stop the already authorized narrow repairs
merely because that later boundary is unresolved.
