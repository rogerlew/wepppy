# ADR-0101: Physical water allocation and routing

## Status

Partially accepted for local source experiments, 2026-10-21. Independent reviews
approve groundwater, hourly allocation and flat-cell corrections.
Routing solver/storage compatibility remains an explicit model gap; no release
or complete watershed repair is approved by this ADR.

## Context

The [repair package](../work-packages/20261021_watershed_physical_water_repair/package.md)
addresses four native failures demonstrated against 261021: terminal-OFE
initial groundwater area, discarded hourly infiltration, underfilled flat source
hydrographs and absent channel-local rate contributions. Native baseline probes
reproduce all four; existing calendar/source/state tests pass.

## Decision provenance

- Decision venue: operator/Codex workspace conversation, 2026-10-21, America/Los_Angeles.
- Participants present: operator and Codex; independent agent reviews are recorded separately.
- Decision owner: operator authorized executing the source-repair package. Codex proposes the numerical contracts below; no human scientific endorsement is implied.
- Implementer: Codex.
- Evidence: repair package `artifacts/baseline-provenance.json`, `baseline-defect-tests.txt`, and predecessor audit at `e85d582ed`.

## Proposed decisions and exact changes

Groundwater: convert initial depth from mm to m and multiply by the sum of all
OFE areas once at simulation start. Reset prior baseflow/deep-seepage withdrawals
at that boundary. Accumulate daily Dp by each OFE's area; preserve the existing
previous-day withdrawal recurrence and do not reset at ordinary year boundaries.

Hourly allocation: visit at most the configured soil-layer count. Continue
allocation of a nonzero remainder rather than discarding quantities below
0.00001 m. Preserve proportional tilled-layer placement for positive water;
the final layer receives the remaining positive amount before the existing
percolation process handles saturation. Every negative allocation is bounded
by available liquid water, including one-layer and subthreshold cases. An
unfulfilled withdrawal must produce an explicit diagnosed failure or a separately
reviewed generating-flux repair; it must never disappear or create negative water.
Negative inputs use the sum of the original binary32 liquid stores evaluated in
binary64 as available inventory. Keep working stores/remainder in binary64 through
the weighted pass and a bounded top-down pass over remaining liquid; cast once
at completion. Exact inventory exhaustion sets all eligible stores to zero.
Demand exceeding represented inventory fails explicitly. Rounding bounds follow
final-store half-ULPs plus operation-count binary64 error, not a fitted cutoff.

Flat sources: source volume and supplied duration are authoritative. Require a
finite physical duration 0 < T <= 86400 seconds. Use constant
continuous rate V/T and integrate its overlap with each routing interval. This
represents a fractional last interval and substep duration without extending the
continuous event. Compute overlap bounds in binary64 to avoid cancellation on
fine, non-divisor grids; cast each mean once. When V exceeds supplied peak times duration, the supplied peak
cannot also hold; recomputing the flat rate preserves mass and timing. Time-zero
boundary values carry no independent cell volume. This contract specifies source
cells, not yet their conversion into every solver's point-value convention.

Channel-local exchange: positive local net water must appear independently of
side-hillslope surface runoff. A negative transmission term can represent net
soil-water release and is not intrinsically invalid. A loss must draw only
available water and preserve individual source timing. No final assembly policy
is ratified until the solver's temporal quadrature, available stores and upstream
volume contract are measured together.

## MC continuity decision (operator authorized)

2026-10-21: Preserve Muskingum-Cunge dynamics and its numerical storage meaning.
The operator rejected replacing MC storage with cross-sectional physical volume
and authorized an MC-preserving consistency audit. A geometric-volume mismatch
alone is not evidence that the MC recurrence creates or destroys water. The
previous recommendation in `routing-scope-review.md` is superseded by this decision.

Derive the implemented per-step continuity for fixed and variable K/X, measure
coefficient and grid transitions separately, and trace source integration,
outlet clipping, published volume and downstream transfers. Geometric volume is
a diagnostic, not an imposed equality acceptance gate. Do not replace the routing
method, redefine authoritative storage, normalize outlet rates, or introduce an
event-specific switch between storage meanings. Any eventual interface repair
must preserve the recurrence and distinguish numerical storage increments from
an independently measurable geometric inventory. An accumulated balance alone
must not be represented as observed physical storage.

Rationale: the fixed-grid positive-coefficient control closes against MC storage
within native precision while disagreeing with geometric storage. This supports
investigating coupling and accounting before proposing changes to accepted dynamics.

## Alternatives considered

Retaining the terminal OFE area or dropping small infiltration violates mass
accounting. Adding all small remainders to reports would not repair the actual
state. Extending flat duration to preserve peak changes supplied event timing;
retaining peak and duration underdelivers known volume. Arbitrary channel-source
rescaling changes unrelated source timing. Normalizing outlet output or deriving
storage from the balance being tested would conceal the routing discrepancy.

## Consequences, risks and rollback

Fresh paired hillslope/PASS/watershed outputs are required. Existing files remain
historical results; schemas, event thresholds, calendar, capacities and default
binary selection are unchanged. Negative-demand fail-fast may expose a previously
hidden upstream inconsistency and therefore requires full-period regression.
Muskingum-Cunge storage and point/cell quadrature may need a separately bounded
algorithm correction; narrow fixes cannot establish full closure. Keep 261021 as
the immutable comparator and revert individual source lanes on failed invariants.

## MC interior-state execution correction

The dry-boundary control reproduces six failures (MC4/5, three interior pulse
positions) and two passing dry controls. WSHCHR's skip guard checks inlet/outlet
and lateral forcing but omits retained interior discharge. Permit the existing
recurrence whenever any previous interior node is nonzero. This preserves all
MC equations, coefficient selection, storage definitions and the all-zero fast
path. Independent scientific review supports this control-flow correction.
A seeded admissible state proves the defect; natural-run frequency is not claimed.

## MC interface experiment after checkpoint 22133f0c9

Independent `mc-interface-repair-design-review.md` supports testing MC accepted
outlet integration as the single published/downstream transfer amount, retaining
the independently computed geometric storage diagnostic and exposing its residual.
Do not replace that diagnostic with `prior storage + input - export`. Include q0
in the daily peak assessment so a q0-only trapezoidal export is not erased by a
zero positive-index peak. KW3 is unchanged in this MC-specific experiment.
This is an isolated candidate, not yet promoted or release-ready.

For conservative source cells, actual trapezoidal consumption is V plus
`dt*q0/2 - dt*qN/2`. Observe these numerical boundary terms independently;
they are not new physical water stores. Fixed positive q0 and a zero-volume dry
day cannot yield a nonnegative exact-zero trapezoid without changing the boundary
contract. Do not apply blanket daily normalization or reset midnight boundaries.
Keep source omission, numerical carry, MC coefficient/grid terms, clipping and
geometric diagnostic differences separate in the acceptance ledger.

## Reviewed interface promotion and remaining loss contract

The corrected v2 source/publication changes are approved by independent science
and QA for a narrow source checkpoint, conditional on native regression gates.
Admitted deferred groundwater enters qin once; the redundant initial outlet term
is removed. Positive local net water with no side surface source uses the existing
uniform representation only without positive side-impoundment transfers. These
shared source corrections also apply to KW3; MC-specific publication leaves KW3
publication unchanged. See native `physical-water-routing-contract.md` for the
compatibility/regeneration contract.

Signed-loss availability remains unresolved independently of negative MC
coefficients. WSHDRV computes transmission after WATBAL has credited soil.
Preserve requested, executed, skipped and clipped amounts separately; do not
reduce the requested loss afterward or assign the mismatch to a geometric store.
A full repair needs a reviewed source/sink acceptance and soil-commit contract,
while retaining MC recurrence and numerical-storage authority. No such new
contract or completed watershed-closure claim is implied by this checkpoint.

## MC4 retained-state reference and exact fixed points

The v2 full native gate timed out at 900 seconds, year16/day81 of100.
With live interior but a boundary-derived reference at or below the existing
`eps`, MC4 selects zero K. On dry forcing the recurrence alternates the sign
of retained interior discharge; even-step days repeat the same profile.
Preserve the last valid per-channel MC4 reference only when retained interior
is nonzero and the newly selected reference is degenerate. Reset reference
history on a new simulation, retain it over ordinary days/years, and preserve
ordinary reference selection, MC5 and KW3. No-history cases remain unchanged.
A readonly CHRSTATE query establishes eligibility before selecting the grid.

Rationale: carrying the prior reference preserves the last valid coefficient
coordinate during recession. The controlled 100 m³ late pulse exports about
99.9999 m³; selecting a new positive-interior reference instead changes that
coordinate and exports about 100.3233 m³. This is a bounded reference correction,
not a new storage definition or an assertion of general physical closure.

At 60-second timesteps, finite-precision subnormal states can reach an exact
fixed point. For MC4 only, when all future inlet/lateral forcing is bitwise
unchanged and the entire consecutive raw spatial profiles and clipped outlets
are bitwise identical, copy that exact state to the remaining timesteps.
Retain all represented values, including subnormals and signed zero; do not
introduce a cutoff. Numeric equality alone was rejected after a signed-zero
counterexample. MC5 coefficients vary by cell/time and are excluded.

Independent actual-source controls compare all raw state arrays and publication
with the shortcut disabled (26 pairs); separate lifecycle controls check reset,
readonly state access and channel isolation (26 checks). Exhaustive continuity
probes explicitly disable the shortcut and retain strict record completeness.
Native execution gates remain required before this candidate is accepted.
Rollback these two corrections together if propagation or bitwise parity fails.
