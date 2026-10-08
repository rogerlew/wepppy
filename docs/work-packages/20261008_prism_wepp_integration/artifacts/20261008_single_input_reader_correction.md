# Single-input variant reader correction

Starting committed revision: 0e331f5e2 (an unrelated user paper commit above
PRISM reader floor e25299022), with the reviewed PRISM implementation in the
working tree. Ratified contract ancestor: d3b5958c5. Preserve the user commit.

The full suite found a real conformance gap after4,964 passes: the existing
single-input project variant transforms the new ordinary CONUS graph into an
unregistered structure. Strict validation correctly rejects it, so no invalid
variant can be persisted. The live watershed's ordinary methods are unaffected.

The user's authorization covers CONUS PRISM integration while preserving existing
workflows. The original amendment omitted this already-supported variant; it
must inherit the new climate without changing any landuse/soil/module/binary
restriction. Clarify the same intended envelope in the current Project Config
contract, append only the exact new variant and retain every old structure.
No new permission, source method, execution topology or parameterization is added.

Exact candidate:
`545e2197c8a67a88da9c796246a2b0572427c8228bcb0e5d3ccd883f11b320a6`;
retained in `single-input-candidate-structure.json`. Its differences from the old
single-input structure must be only the PRISM climate ID, station/spatial relations
and method defaults. Treat this as a compatibility defect correction, not
permission to change single-input behavior elsewhere.

Required evidence: independent amendment reviews, standalone reader-catalog
ancestor, unchanged historical catalog records, ordinary and single-input Builder
creation with both watershed representations, committed-reader reopening of both
new structures, and resumption of the full suite from the failing module. The
already passed long-running modules need not be repeated for this bounded catalog
correction. The aggregate rollback floor must advance to include the variant.

Review dispositions and commit revision are recorded in the tracker.
