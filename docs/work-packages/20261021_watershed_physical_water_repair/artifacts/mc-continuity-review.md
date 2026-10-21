# MC continuity and interface review

Independent scientific/correctness review, 2026-10-21. Native source references
are relative to `/workdir/wepp-forest-release-20261009`. Reviewed the actual
WSHCHR/CHRSTATE recurrence, the retained fixed/adaptive-grid controls, and
`tools/mc_continuity_probe.py` and `tools/mc_interior_state_probe.py`. No native
implementation changes were made for this review.

## Authority and disposition

The operator selected an **MC-preserving consistency audit**. This review
supersedes the geometric-volume recommendation and acceptance requirements in
[routing-scope-review.md](routing-scope-review.md), and the geometric-equality
interpretation of S2 in [scientific-preflight-review.md](scientific-preflight-review.md).
Their numerical observations remain evidence; disagreement with Manning-derived
geometric volume is not, by itself, a failure of the implemented MC continuity
equation. The current contract is recorded in the active ExecPlan's
“MC-preserving continuation” and ADR-0101.

Preserve MC4/5 recurrence, coefficient selection and supported routing paths.
Audit its discrete continuity, source quadrature, carried state and exported
fluxes independently. Do not impose geometric equality, restrict X to force
positive algebraic storage, freeze coefficients, change the grid remap, or
introduce another routing scheme under an accounting correction. Geometry
remains a constitutive input and useful diagnostic. Algebraic routing storage
must not silently replace a public geometric-storage field.

## Findings and bounded repair priorities

| Finding | Severity and evidence | Smallest supported action |
| --- | --- | --- |
| Live interior state can be discarded by the dry-boundary optimization. | **High, demonstrated in an admissible controlled MC4 state.** `src/wshchr.for:514` and `:521` inspect inlet/outlet forcing but ignore interior `qs`. The skip branch leaves the next profile at its initialized zero. | Include existing nonzero interior state in the decision to execute the unchanged recurrence; validate MC4/5 and retain the genuinely empty fast path. |
| Published/transferred daily volume is independently calculated from geometry, although downstream rates come from actual routed Q. | **High, demonstrated interface disagreement.** `src/wshchr.for:654`, `:713`, `:733`; `src/wshcqi.for:199`; upstream rate transfer at `src/wshchr.for:231`. | Use the same accepted outlet flux integral for the daily outlet volume and its downstream volume transfer, while retaining an explicit, separately interpreted storage ledger. Validate downstream coupling, not just report text. |
| Source-cell volume is not always the volume consumed by MC's temporal quadrature. | **Medium, demonstrated convention difference; defect attribution depends on the documented source contract.** Top flow always uses adjacent-time averages, while lateral flow depends on `mofapp`. | Retain source contributions, endpoint carry and actual consumed integrals. Correct omissions or duplicate transfers demonstrated by that ledger. Do not normalize arbitrary rate arrays or alter their support merely to force daily equality. |
| Variable coefficients, regridding and clipping can be mistaken for unexplained continuity error. | **Medium, audit/interpretation risk.** MC5 changes K/X per cell and step; CHRSTATE interpolates discharge; exported Q is clipped independently of raw state. | Observe and account for the terms derived below. Their existence does not authorize a different routing method. |

The original positive-local and negative-exchange defects remain separate
acceptance work. This review does not certify their repair, impoundment routing,
or a complete network solely from a closed MC cell equation.

## Exact regular-step equation

For one spatial cell and time step, let I and O be the raw upstream/downstream
`qs` values, K=`tk`, X=`cx`, and L the actual `qlavg` in volume/time/length.
Subscripts p and n denote previous/current time. Use the K/X actually selected
for this cell and step. For a regular, executed update the source implements:

```text
D = 2*K*(1-X) + dt
a = (dt-2*K*X)/D
b = (dt+2*K*X)/D
c = (2*K*(1-X)-dt)/D
d = 2*dt*dx*L/D
O_n = a*I_n + b*I_p + c*O_p + d

F = dt/2*(I_n+I_p-O_n-O_p) + dt*dx*L
M = K*(X*(I_n-I_p) + (1-X)*(O_n-O_p))
F = M
```

This follows by rearranging `src/wshchr.for:510` through `:567`. Both MC modes
therefore use **trapezoidal inlet and outlet fluxes**. Summing over spatial
cells cancels their shared raw internal discharge interfaces. Lateral integration
is `dt*dx*L`, with L formed by the actual mode-specific rule.

Native `c3=1-c1-c2` and the other coefficients are evaluated in binary32.
For observed values define `r=F-M`; report this arithmetic residual instead of
assuming mathematical exactness in the executable. Also evaluate the recurrence
independently using the observed a/b/c/d. Bound coefficient-rounding and update
rounding from operation magnitudes and machine precision; do not fit a tolerance
to the largest observed discrepancy. Record actual c1/c2/c3, not just K/X/c0/c4,
when attributing residuals to coefficient versus state arithmetic.

The denominator guard and skipped-update branch are not regular updates.
Record branch tags and state before/after those paths; do not classify their
residuals as floating-point error. The current MC5 coefficient block also needs
its own nonfinite/degenerate-case observations rather than assuming that MC4's
earlier denominator guards cover it.

## Variable coefficients: storage coordinate versus increment

Define the algebraic endpoint coordinate using the coefficients at step n:

```text
H(theta_n, q) = K_n*(X_n*I + (1-X_n)*O)
H_n = H(theta_n, q_n)
C_n = H(theta_n, q_p) - H(theta_p, q_p)

M_n = H_n - H_p - C_n
F_n = H_n - H_p - C_n + r_n
```

C is the revaluation of the same preceding discharge state under a changed
coefficient pair. It is a coordinate-change term, not a new hydrologic source
or a fitted residual. MC4 has C=0 within an ordinary day. MC5 requires a separate
C for every cell and time step (`src/wshchr.for:523`); the final K/X scalar cannot
represent all those cells.

For a simple positive-coefficient example, previous K=2, X=0.2, I=1, O=0.5
gives H=1.2. With current K=3, X=0.1, dt=1, I=2 and no lateral source, the native
formula gives O=0.71875 and H=2.540625. C=0.45, so both the integrated net flux
and `delta(H)-C` equal 0.890625. Omitting C would falsely report a 0.45 volume
error even though the recurrence is satisfied exactly.

Negative X is allowed by the current method. Its algebraic H can be negative
for positive nodal discharges; that fact alone does not mean a geometric water
inventory is negative. Do not clip H, alter X, or claim H is measured physical
volume. A diagnostic cumulative sum of independently observed M increments is
also valid, but it is not a new prognostic store and must not be constructed by
setting storage equal to an unverified boundary-balance remainder.

## Daily state carry and changing grids

CHRSTATE carries nodal discharge, with linear interpolation when the number of
segments changes (`src/chrstate.for:14` through `:25`). The caller independently
sets the new upstream boundary. Observe the previous final profile, new initial
profile, old/new grids and actual coefficient sets.

Let H_old be the preceding day's final summed algebraic coordinate. Let H_start
evaluate the new initial profile using each cell's first actual coefficient
pair. Define the independently observable transition:

```text
J_day = H_start - H_old

V_top_MC + V_lateral_MC - V_out_raw
  = H_end - H_old - J_day - sum(C_within_day) + sum(r)
```

The within-day C sum starts at step two; the first step uses H_start as its
previous coordinate. Initial simulation state is an explicit initial condition,
not an assumed zero. For MC5, “first coefficient” means the actual coefficient
for that cell's first executed step.

J includes grid interpolation, boundary replacement and the coefficient change
at that transition. Retain the stages so same-grid coefficient and boundary
effects can be examined separately. Across different grid dimensions there is
no unique split into pure remap and pure coefficient effects without specifying
a reference mapping; do not manufacture that split. Observing J neither asserts
geometric conservation nor authorizes changing CHRSTATE. If a candidate changes
the mapped state, that is a routing-method choice requiring its own evidence
and contract decision.

## Raw state, accepted export and clipping

WSHCHR clips `q1(n)<eps` to zero at `src/wshchr.for:573` but leaves the raw
`qs(nseg,n)` unchanged. CHRSTATE saves the raw profile. Consequently, the next
initial exported outlet `q1(0)` can also differ from restored raw outlet state.
Define:

```text
deltaQ_n = Q_export_n - Q_raw_n
B_step = dt/2*(deltaQ_p + deltaQ_n)

V_top_MC + V_lateral_MC - V_out_export
  = delta(H) - coefficient_revaluation + r - B_step
```

The daily version additionally contains `-J_day`. The full-day B must include
`dt/2*(q1(0)-qs(nseg,0))`, as well as subsequent points and the half-weighted final
point. Measure this separately from a skipped-state transition. Changing the
clipping rule or overwriting raw state with clipped exports changes the method;
it is not implied by observing the correction.

The current portable MC probe reports subsequent clipping volume and the
initial outlet difference separately. Combine them with the correct dt/2 weight
for the complete exported-flux identity. Retain negative and positive-tiny
clipping contributions separately when diagnosing signed exchanges.

## Source quadrature and temporal carry

For MC4/5, top/inlet arrays are always integrated with temporal trapezoids.
Lateral point mode uses `(qlat(p)+qlat(n))/2`; cell-average mode uses `qlat(n)`
(`src/wshchr.for:515`). For any uniformly sampled array:

```text
V_rectangle = dt*sum(q[1:N])
V_trapezoid = V_rectangle + dt/2*(q[0]-q[N])
```

This is an exact quadrature identity, not proof that every upstream source is
represented correctly. If the source's documented daily amount is the rectangle
integral, the half-step endpoint term is a source-interface carry coordinate.
It is not soil water, groundwater or geometric channel storage. A nonzero q0 on
the first simulation day needs an explicit initial-boundary contribution. Carry
terms telescope only where endpoint state and integration weights match across
days; changed time steps need their own observed transition.

Do not add this correction again to an upstream channel hydrograph whose accepted
volume is already its trapezoidal integral. That same rate array and its integral
must transfer exactly once to the downstream channel. Retain per-source
provenance to distinguish hillslope surface flow, lateral flow, baseflow,
deferred groundwater, local exchange and upstream routed channels.

A cell-mean-to-node conversion is not automatically a harmless rescaling.
Enforcing `q_n=2*mean_n-q_p` with a fixed initial point can oscillate or become
negative for otherwise nonnegative interval means. A new interpolation,
source-support, initial-state or carry policy is an explicit method/interface
choice. The flat-source cell-volume correction alone does not settle it.

## Publication and downstream contract

For the accepted MC outlet array, use the actual native timestep and full
precision to calculate:

```text
V_export = dt*(sum(q1[1:N]) + 0.5*(q1[0]-q1[N]))
```

Compare this independently with the channel daily outlet, EBE outlet path,
`runvol`, `tmpvol`, and that channel's contribution to downstream `rvotop`.
Current WSHCHR calculates `chvol=volint+sinit-sfnl` from a separate geometric
estimate, then modifies the reported storage to satisfy that identity
(`src/wshchr.for:654`). This is the demonstrated conflict; an algebraically
zero printed balance cannot establish agreement with routed discharge.

The bounded repair target is agreement among **accepted rates, published volume
and downstream transfer** while keeping the MC update intact. Merely changing
the output file leaves `tmpvol` and downstream coupling wrong. Correcting those
transfers can change downstream soil/channel water balance and subsequent
routing, even when each local fixed-forcing recurrence is unchanged. Require
both local recurrence parity and a full cascade comparison; do not promise
byte-identical whole-network Q.

Storage publication needs a documented interpretation, not a forced zero
residual. Retain geometric storage as a labeled diagnostic or preserve its
existing field with clearly documented limitations; expose algebraic coordinates,
revaluation and carry in separate observations. Do not silently repurpose the
old column or set its value from the desired balance.

Include a boundary-only outlet case: q1(0)>0 with all later q1=0 has positive
trapezoidal export. The current peak scan excludes index zero (`:623`), and
`qchpk<=0` forces chvol=0 (`:656`). Peak/duration metadata and the one-row
low-flow hydrograph fallback therefore need explicit coverage alongside the
daily integral. Rounded public hydrograph rows omit q0 and cannot serve as the
sole numerical oracle.

## Demonstrated interior-state defect

The actual-source paired control at
`/workdir/watershed-physical-water-repair-20261021/mc-interior-v1/receipt.json`
uses MC4 with fixed eight-cell coefficients, dry boundaries and one interior
node at 1 m³/s. K=1262.1805419921875 s and X=0.23073482513427734; all recurrence
weights are positive. This is an admissible seeded nodal state, not evidence
that a particular natural run reached it.

The baseline executes zero cell updates, exports zero, and erases an initial
algebraic coordinate of 1262.18054 m³. The isolated guard change adding
`any(qs(1:nseg,it-1).ne.0.)` to the execution condition runs 1,152 updates and
exports 1262.179855 m³, with negligible final state and a 0.000687 m³ residual.
That small remainder still requires the normal arithmetic/clipping accounting;
it is not a fitted acceptance tolerance.

The candidate preserves the recurrence and prevents an optimization from
bypassing live state. It is a supported narrow repair. Test MC5, negative/tiny
existing states under the established method, a truly empty profile, and normal
forcing parity. Exact nonzero detection avoids introducing a new cutoff that
would delete small stored state. Measure any runtime effect from additional
recession steps. Do not claim natural-run frequency from this seeded control.

## Evidence interpretation and remaining acceptance

The retained full-node MC4 controls at
`/workdir/watershed-physical-water-repair-20261021/solver-full-node-v2/receipt.json`
show day-two algebraic residuals around 0.001–0.016 m³, including the fixed,
positive-coefficient controls. Their simultaneous geometric residuals of
hundreds of cubic meters demonstrate that the two inventory definitions differ;
they do not prove an MC continuity defect. The older MC5 endpoint-geometry
residual likewise cannot establish MC loss without its coefficient terms.

Require the portable observer to retain complete cell/time records or explicit
skip/guard records, full initial/final profiles, K/X and recurrence coefficients,
raw/exported outlet rates, actual source integrals, publication and cascade
transfers. Reject missing, reordered or nonfinite observations. Preserve paired
observer-off/on output parity so instrumentation cannot manufacture agreement.

Priority controls are fixed and varying K/X; fixed and changing grids; both
source modes and side/top placement; first-day and midnight carry; short pulses
and recession; boundary-only and live-interior states; positive/negative local
exchange; and tributary/cascade transfers. The deferred-groundwater term is
included in `src/wshcqi.for:206` but lacks the corresponding ordinary daily
WSHCHR source addition; retain a threshold-crossing cascade control before
certifying baseflow. Impoundment inputs need separate coverage.

The review supports the demonstrated interior-state guard correction and a
consistent accepted-flux publication/transfer repair. Source omissions proven
by a component ledger are also bounded interface fixes. Altering recurrence,
clipping, coefficient restrictions, source interpolation, grid remap or storage
authority remains a distinct method decision. No such change is recommended
as a prerequisite to the authorized MC audit.
