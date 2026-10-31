# Joint GRNA/QINF ownership experiment specification

Status: draft scientific contract; model_gap / requires_scientific_review.
This specifies the next bounded diagnostic, not an accepted physical model or
permission to promote parameter defaults. O4's recession-only rule is rejected.

## Physical accounting contract

Use water volumes and explicit owners. Distinguish local rainfall/snow/interception
supply, storm infiltration, recession infiltration, incoming/outgoing Hortonian
runoff, hourly return/lateral transfer, liquid/frozen stock and each sink.
A downstream equivalent-plane evaluation cannot return infiltration already
assigned to an upstream soil. Each local withdrawal must be funded at its actual
time, and each local addition must respect available storage and explicit
percolation/return pathways. A negative local infiltration exchange may be valid
only with a documented physical source and available inventory; it is not
implicitly forbidden by this diagnostic.

Preserve the distinct local soil length, hydraulic routing length, cumulative
reporting length and wetted extent. Preserve incoming-event support for sediment
routing even when outlet runoff is zero. The known C3 peak under-scaling and lost
deposition branch remain counterexamples. Equal-width observations alone do not
establish a variable-width or contour contract.

## O6 proposed observation and offline attribution lane

Prerequisite satisfied by O5 for the observed cases: matching-boundary liquid
stock residuals are at most 0.000312 mm. This is accounting evidence, not a
validated new physical law.
Retain any unresolved residual; do not calibrate it away.

Add observations of local and aggregated GRNA storage, conductivity, storm input,
raw runoff and accepted infiltration, plus pre/post QINF recession operands.
Capture the actual before/after upstream stocks and the stold snapshot separately
so a prior-day/current-day mismatch can be tested rather than assumed. Record
chain roots, effective lengths, ROCHEK branches and partial wetted extents.

For each connected chain, report the physical volume difference between successive
storm infiltration proposals and successive recession proposals independently.
Compare each implied local exchange with local supply, incoming accepted surface
water and available stock. No monotonic-loss assumption, clipping, artificial
water borrowing, or adjustment of native state is allowed in this lane.

Evaluate every recorded day in the twelve O5 cases; include the five original
failure events, Charleston year 9/day 93/element 3 and delayed_return year 1/day
191/element 3. Carry zero recession, absorbing runon, delayed return and geometry
counterexamples explicitly. Duplicate road configurations are not independent
hydrologic evidence. Require exact native status and all output-file parity for
observation off/on. Retain raw signed operands and hashes.

The deliverable is an attribution table showing whether inconsistency first
appears in storm infiltration, recession, or their combination, plus any missing
ownership terms. Only then specify one isolated behavioral formula with a
physical rationale and explicit regression expectations. A ledger assembled
from measured state changes is an accounting check, not an independently
validated infiltration law.

## Behavior-lane and adoption gates

Before a behavior lane: document equations, units, source ownership, temporal
boundary, valid geometries and any unresolved model gap. Declare its single
change group and predicted effects before running. No guard relaxation, altered
acceptance thresholds, parameter fitting or wholesale C3 restoration.

Require funded native hourly transfers and complete configured runs for all
regression fixtures. Check generated hydrology and sediment artifacts and event
support, not just completion. Follow with native release/watchlist gates,
Disturbed matrix, Cedar Creek semantic analysis and the frozen 840-case Roads
development panel. The separate meaningful/small-load magnitude gates remain
unchanged. Withheld materials stay reserved until a development candidate passes.
Human approval of UI specification and layout remains required before UI work.
