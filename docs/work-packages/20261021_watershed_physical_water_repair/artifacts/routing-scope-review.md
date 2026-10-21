# Routing scope review

**Superseded recommendation:** the operator selected the MC-preserving audit.
[mc-continuity-review.md](mc-continuity-review.md) supersedes the geometric-volume
recommendation and acceptance interpretation below. Retained observations are
historical evidence; geometric disagreement alone is not an MC continuity failure.

Independent scientific/correctness review, 2026-10-21. Reviewed the native
WSHCHR/CHRSTATE implementation, the three-day native solver control at
`/workdir/watershed-physical-water-repair-20261021/solver-budget-control-v3`,
the full-node follow-up at
`/workdir/watershed-physical-water-repair-20261021/solver-full-node-v2`,
and the full-period `routing-accounting.json` receipts. No production source
was changed for this review.

## Disposition

**Do not promote the channel experiment or claim repaired routing yet.**
The controls demonstrate a discrepancy between routed discharge and the current
published storage calculation after the missing-source mechanisms are removed.
Changing only the published outflow or redefining storage from a balance identity
cannot satisfy the physical accounting contract.

The full-node follow-up establishes that replacing endpoint geometry with full
spatial geometric storage is also insufficient. The mismatch remains in MC4
with a fixed grid, fixed positive coefficients and no sinks, while the separate
MC algebraic ledger closes within native arithmetic precision. Consequently,
the next production correction requires an explicit **authoritative storage and
continuity contract decision** under M3. It is more than a reporting or spatial
quadrature edit. The recommended bounded direction retains existing Manning
geometry/rating physics and makes independently stored channel volume and
accepted fluxes conservative. It does not introduce another routing engine.
The original package excludes a general routing rewrite, so changing the
numerical storage/update semantics requires the concrete scope decision below.

## What the control establishes

The probe calls actual WSHCHR. Its only forcing alteration is a prescribed
nonnegative 0.1 m³/s source, with an additional 1 m³/s during the last hour of
day two. The source is applied through either the side/lateral path or the top
boundary. There are no local net exchanges or transmission sinks in this control.
It retains the native spatial grid, coefficient selection and daily state carry.
The first day establishes a steady boundary before the pulse. The third day
allows recession. This separates the remaining mismatch from CHRQIN estimation
and the missing channel-local source defect.

| Native method / placement | Day-two residual against current geometry | Day-three residual | Interpretation |
| --- | ---: | ---: | --- |
| MC4 / side | +1,063.191 m³ | -1,063.238 m³ | Daily storage disagreement largely cancels over the pulse/recession. |
| MC4 / top | -1,858.219 m³ | +1,858.214 m³ | Cancellation cannot validate daily output, storage or transfer timing. |
| MC5 / side | +1,353.869 m³ | -1,281.428 m³ | About +72.423 m³ remains over all three days against endpoint geometry. |
| MC5 / top | -1,845.949 m³ | +2,657.056 m³ | About +811.107 m³ remains against endpoint geometry. |

Residual here is observed solver input minus integrated output minus change in
the current geometric store. The MC control correctly uses trapezoidal temporal
integration, matching its recurrence. The imposed daily source totals and the
solver integrals differ by approximately 300 m³ at the midnight boundary of
the late pulse; that known source-quadrature effect is visible and is not silently
folded into storage closure.

The BUDGET tap is after WSHCHR's final storage/balance assignment. For these
positive-flow cases its reported store is the existing inlet/outlet geometric
estimate; the tap does not expose all interior cross sections. Consequently,
the MC5 cumulative residual is **not yet a measurement of whole-channel water
creation or loss**. Equal endpoint areas do not prove that no water remains
between those endpoints. The follow-up below resolves that evidence gap for
MC4; MC5 still needs its corresponding complete state/variable-coefficient
analysis before assigning the cumulative residual to a particular mechanism.

The longer paired experiment supports the same scope disposition. Combined
positive-local and flat-source corrections reduce rectangular input disagreement
to approximately 0.01 m³ over 44 years, but trapezoidal outflow minus publication
still totals +821.470 m³ daily and +4.326 m³ hourly, with absolute daily-error
sums 1,634.118 and 652.358 m³ respectively. The near-zero hourly signed sum is
not acceptance. These are diagnostic candidates, not promoted channel code.

## Full-node follow-up rules out an estimator-only repair

The follow-up records every spatial node at the beginning and end of each day,
plus MC4 K/X, and independently inverts rectangular Manning geometry with
width 3 m, slope 0.001 and roughness 0.05. It integrates A(Q) across the whole
5,000 m channel using spatial trapezoids. Native adaptive-grid controls are
paired with an explicitly frozen eight-reach grid and reference discharge
0.5 m³/s, using the existing restart-harness mechanism.

| Grid / source placement | Day-two full-geometric residual | Day-two MC algebraic residual |
| --- | ---: | ---: |
| Native adaptive / side | -558.483 m³ | -0.01598 m³ |
| Native adaptive / top | -822.123 m³ | +0.00110 m³ |
| Fixed eight reaches / side | -968.386 m³ | -0.01528 m³ |
| Fixed eight reaches / top | -659.633 m³ | +0.00091 m³ |

The fixed controls have K=1262.18054 s and X=0.230734825 throughout.
Their recurrence coefficients are c1≈0.0069011, c2≈0.4651861 and c3≈0.5279128,
all positive. Nonnegative forcing and state therefore exclude negative outlet
clipping as the explanation for these fixed controls. The grid does not change,
and the prior final node states equal the next initial states. This excludes
regridding and coefficient transitions as their cause. Full geometric inventory
still disagrees by hundreds of cubic meters while the independent algebraic
ledger closes near binary32 accumulation precision.

This is sufficient evidence for the scope decision: a full-node geometric
reporting correction alone cannot meet physical closure. Additional temporal
observations remain acceptance work for the eventual repair, particularly
MC5, negative exchanges and adaptive remapping; they are not a prerequisite
to rejecting the estimator-only alternative.

## Kinematic-wave quadrature correction

The v3 receipt applies trapezoidal top/output integration to every method.
That is appropriate for MC4/5, but KW3's native equation at
`src/wshchr.for:442` uses current-step top inflow and outflow. In point-source
mode its lateral term is still the adjacent-time average (`:400`).

Reintegrating retained KW output with that actual convention gives top-path
geometric residuals of approximately -762.610 m³ on day two and +137.452 m³
on day three. The side-path steady first day already changes estimated storage
by about 393.930 m³ despite steady boundary discharge. Thus correcting quadrature
does not establish closure, but the all-trapezoidal KW figures must not be cited
as the scheme's native continuity budget. Independent calculations are retained
in `/workdir/watershed-physical-water-repair-20261021/reviewer-routing-scope/kw-quadrature.json`.

## Why a discrete-storage substitution is insufficient

For fixed MC coefficients K=`tk` and X=`cx`, rearranging the implemented update
at `src/wshchr.for:510` through `:567` yields the exact discrete relation:

    S_alg(n) - S_alg(n-1)
      = dt/2 * [I(n)+I(n-1)-O(n)-O(n-1)] + dt*dx*lateral_mean
    S_alg(n) = K * [X*I(n) + (1-X)*O(n)]

This is useful as an independent numerical diagnostic. It is not interchangeable
with a geometric water inventory without additional assumptions:

1. `cxmin=-10` (`src/wshchr.for:110`) permits negative X. Positive I and O do not
   then guarantee nonnegative algebraic storage. For example, X=-1, I=1 and
   O=0.1 gives S_alg=-0.8K. Clamping that store would create an unexplained flux.
2. Geometry is obtained from the nonlinear Manning relation. Even a fixed
   derivative `dA/dQ` supplies a local linear storage approximation, not generally
   the finite geometric area change across an arbitrary pulse.
3. MC4 recomputes coefficients and grid at daily boundaries. MC5 changes K/X
   within the step/space loop (`:523` onward). The recurrence uses the current
   coefficient to weight the discharge increment. A state function evaluated
   with changing coefficients also contains parameter-change terms. Adding an
   algebraic endpoint formula without these terms does not establish continuity.
4. CHRSTATE interpolates discharge during regridding (`src/chrstate.for:14`),
   rather than remapping geometric cell volumes. Bounded discharge interpolation
   alone is not a water-volume conservation statement.
5. Negative/tiny outlet clipping (`src/wshchr.for:450`, `:573`) modifies reported
   boundary flux independently of the internal `qs` update. Clipping must be
   measured explicitly before any discrete conservation claim.

For KW3, the corresponding per-step relation uses
`dx/c(n) * [O(n)-O(n-1)]` as its storage increment and rectangular top/output
fluxes. A varying c makes this different from simply evaluating `dx*O/c` at
successive endpoints. Geometry and remapping still require an independent check.

The existing geometric estimator has separately repairable weaknesses: MC uses
only the channel endpoints (`src/wshchr.for:576` through `:618`), while KW gives
every spatial node equal weight and can reuse the previous Manning depth when
a node is dry (`:452` through `:471`). Correcting these may remove part of the
observed discrepancy. The full-node control demonstrates that these corrections
alone cannot establish the required physical continuity.

## Concrete next scope and alternatives

### The operator's concrete choice

**Recommended: make cross-sectional physical inventory authoritative.**
Authorize a bounded conservative-continuity repair in the existing
WSHCHR/CHRSTATE channel pipeline, retaining current Manning geometry/rating
relations, source support, network connectivity, PASS/calendar contracts and
the three validated narrow corrections. This permits the minimum method-specific
state/recurrence changes demonstrated necessary to conserve physical volume.
It does not authorize replacing the whole model, changing defaults, adding a
routing engine, or publishing a release without the existing acceptance gates.

**Alternative: adopt MC algebraic routing storage as the authoritative model
inventory.** This requires an explicitly documented routing-storage contract,
nonnegative-state restrictions or a justified positivity treatment, and
conservative coefficient/grid transitions. It cannot be described as closure
against measured cross-sectional physical inventory. It therefore narrows the
original physical-accounting objective and needs explicit operator acceptance.
Choosing this alternative does not remove the need for source quadrature,
sink-availability and cascade-transfer corrections.

### Alternatives that do not satisfy the decision

| Alternative | What it would establish | Cost or reason to reject |
| --- | --- | --- |
| Integrate actual Q only for published daily outflow | Agreement between the published flux and the rate array. | Leaves physical storage and downstream soil/volume coupling inconsistent. Necessary output behavior after a real repair, insufficient alone. |
| Set final storage to prior storage + input - integrated Q | A balance identity. | Does not independently measure or update hydraulic inventory; may hide negative/phantom stores and violates the audit contract. Reject. |
| Promote fixed-coefficient MC algebraic storage | A numerical balance for a restricted fixed-coefficient case. | Requires a new storage interpretation; negative X, coefficient changes, clipping and remapping remain unresolved. Do not call it geometric water volume. |
| Repair the existing methods around an authoritative physical volume state | Conservative actual fluxes, nonnegative inventory and meaningful storage, if implemented and verified. | Changes numerical state/update semantics; requires a ratified continuity/storage contract and method-by-method peak/timing validation. Recommended bounded direction given the failed full-geometry control. |
| Add or replace the model with a different routing engine | Potentially a different hydraulic approximation. | Not justified by current evidence; introduces unnecessary scope before owned routines and their continuity discretization are resolved. |

The recommended repair scope is **conservative channel continuity
using the existing channel geometry and Manning relation**, limited initially
to ordinary channels exercised by the retained matrix. Specify cell/reach water
volume as an independent nonnegative state, calculate physical inputs and sinks
as interval volumes, pass each upstream outlet volume exactly once to the next
reach, and remap volume conservatively when the grid changes. Sinks must be
limited by water actually available at the defined time, with unmet requested
exchange explicitly reconciled with the soil calculation. Published outflow
must then be the same accepted flux used by state evolution and downstream
transfer. Preserve source support and the groundwater threshold contract.

A derivation and prototype must determine whether MC4/5 can retain their method
meaning under that state equation. Replacing them with an implicit conservative
kinematic scheme, limiting X, freezing coefficients, changing timestep selection,
or restricting currently supported methods are distinct choices with different
peak, timing and numerical-diffusion consequences. None should be hidden as a
bookkeeping edit. The operator's reviewable decision should name the chosen
method/state contract, supported paths, expected output changes and rollback,
with comparison evidence, before promotion. A new library or service is not
needed to evaluate these owned numerical routines.

## Acceptance and remaining limits

Require per-step and cumulative independent continuity, nonnegative physical
stores, source-cell and actual-solver agreement, no unobserved clipping, and
identical transferred fluxes across tributaries/cascades. Exercise methods 3/4/5
and all supported geometries, side/top placement, dry-down/re-wetting, midnight
and regridding, coarse/fine timesteps, signed local exchange, and groundwater
threshold crossing. Check convergence and peak/timing changes in addition to
volume; matching one cumulative total is insufficient. Preserve the three
already-reviewed narrow fixes and their separate evidence.

This review confirms the unresolved routing boundary and recommends the concrete
bounded scope above. It does not certify a replacement storage formula, approve a new
routing algorithm, or establish calibration/impoundment/tile/general hydraulic
validity from the current controlled examples.
