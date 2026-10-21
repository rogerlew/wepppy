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
