# ADR-0146: Simplified unrutted partial-crossing strips

Status: RUPC-01 accepted and locally validated; RUPC-02 accepted, implemented and locally validated
Date: 2026-11-17

## Context

Whole-hillslope 60% eligibility and longitudinal downhill splitting exclude partial
contour-following roads. Existing Roads machinery already supports independently
executed affected strips, an unaffected remainder and replacement PASS aggregation.

## Decision

Use the accepted [strip contract](../schemas/roads-unrutted-strip-contract.md).
Total hillslope area is invariant. Road area is preserved where feasible; proportional
strip width reduction reports road-area deficits rather than hiding them. Model road
flow transversely with physical road width as OFE length and fixed 4% cross slope.
Retain existing minimum overlap and crossing cap; disclose their excluded road area.
No flowpath walking or switchback connectivity reconstruction in this version.

## Decision provenance

Venue: Codex conversation, 2026-11-17 (UTC date).
Participants: Roger Lew and Codex. Decision owner: Roger Lew. Implementer: Codex.
Roger approved proceeding with the package and mutation/forking of the synced
forest `misty-eyed-divorcee`; scoped tests were explicitly requested. Roger explicitly approved the concrete formula proposal: “i approve. proceed with
implementation”. This ratifies the geometry contract and its checkpoint/implementation
sequence.
Marta was not present in the recorded decision conversation.

## Change summary

Replace ratio >= 0.60 with minimum-length eligibility alone, preserving the cap.
Replace legacy longitudinal-slope parity length/width with road length = physical
width, cross slope = 4%, strip width = overlap times min(1, hill width / summed
overlap). Preserve full profile length with landuse remainder and area accounting.

## Alternatives considered

Full flowpath-derived drainage partitions and switchback routing were deferred by
the operator as unnecessary complexity for this abstraction. Lowering 60% alone
leaves longitudinal segmentation dependence. Extending road OFE lengths to preserve
area after width compression distorts the transverse physical road dimension; the
proposed first version instead reports the lost road area explicitly.

## Consequences

Area closure does not prove physical contributing-area allocation. Winding roads
can be compressed and excluded crossings are not represented. Existing required
fill/buffer attributes still apply. No new defaults or dependencies are introduced.

## Evidence

[Incident observations](../work-packages/20261117_roads_unrutted_partial_crossings/artifacts/20261117_incident_evidence.md)
identify the prior 38-segment exclusion and the later 9-segment missing-input failure.
Native 141/42 slice validation and 191 scoped tests pass; full copied upload
retains eight explicit infeasible-upstream failures. See work-package evidence.

## Risk and rollback

Failing area closure, non-positive inputs, baseline double counting or stale result
publication blocks release. Retain original inputs/results and validate disposable
forest runs. Revert using commit-preserving integration; reprepare under the active
policy before execution. No production deployment follows automatically.

## RUPC-02 amendment — 2026-11-17

Roger Lew asked whether the eight rejected crossings should be modeled at the
hillslope top, then directed: “let's add to the current work-package / branch.
update the work-package and proceed with the contract ammendments”. Venue and
participants remain the Codex conversation with Roger and Codex. This authorizes
the top-placement contract amendment; implementation and native validation remain
pending and are not covered by the original 191-test receipt.

Adopt the RUPC-02 section of the strip contract. Omit upstream landuse when the
ordinary placement is non-positive; preserve road/fill dimensions and hillslope
area using downhill landuse, including positive lengths below 10 m. Exact fit uses
a road/fill profile. Reject road plus fill longer than the representative hill.
Place remainder absorption downhill for these strips. Record the original position
and adjustment, and disclose zero modeled runoff from land above the road.

Reject silent distance clamping with a fabricated upstream OFE and silent fill
shortening. Relative terrain-position mapping needs a separate scientific choice
and is outside this amendment. The top placement is an explicit abstraction,
not evidence of physical ridge location or resolved switchback connectivity.
Preserve geometry preparation compatibility; invalidate current execution results
by the new placement policy marker and require rerun. Revert through normal
commit-preserving history and rerun under the selected policy; never relabel old
outputs. Scoped native profile/PASS/watershed evidence is required before claiming
conformance or that any of the eight crossings is repaired.

### RUPC-02 implementation evidence

199 scoped tests pass and both independent implementation reviews pass. Native
exact-fit road/fill and 1 m downstream profiles each produce 5,844 daily PASS rows.
Use decimal input-dimension subtraction for the exact-fit boundary to avoid
binary cancellation creating a positive section that serializes to zero; this
adds no physical length tolerance and does not drop meaningful short landuse.

With the original synthetic 30 m fills, three of the eight old failures now execute;
five explicitly exceed hillslope length. A separate synthetic 5 m-fill full-upload
experiment completes 24 contributors/remainders and the watershed/report chain.
These inputs are validation fixtures, not measured site dimensions. See
`20261117_top_placement_native_evidence.json` in the active package. No deployment.
