# ADR-0143: Candidate nominal 1 m culvert pruning boundary

Status: Superseded candidate by ADR-0144  
Date: 2026-11-16

## Context

Santee's nominal 1 m DEM reports 1.0000000000089009 m, selecting two
pruning passes and producing 14,339 subcatchments and 5,765 channels.

## Decision

Evaluate a 1.5 m inclusive upper boundary for three passes on forest.
Acceptance remains pending a fresh RQ replay of Point_ID 1040. Both counts
must be within half to twice the retained 726 subcatchments and 298 channels,
with valid connected drainage/outlet and no silent unpruned-stream fallback.

## Decision Provenance

Decision Venue: Operator/Codex conversation, recorded 2026-11-16 00:46 UTC.  
Participants Present: Operator and Codex.  
Decision Owner(s): Operator.  
Implementer(s): Codex.

## Change Summary

Effective resolution remains cell size times sqrt(flow_accum_threshold / 100).
Three passes change from effective resolution <= 1.0 m to <= 1.5 m;
two passes cover > 1.5 through 4 m; one pass covers > 4 m. Missing or
nonpositive thresholds still use 100. Explicit payload overrides remain intact.

## Rationale

Represent the nominal resolution class explicitly instead of treating metadata
precision as a scientific distinction. This is a heuristic pending calibration.

## Alternatives Considered

- Epsilon only: repairs rounding but preserves an unsupported 1.01 m cliff.
- Floor: also reclassifies genuine 1.9 m and 4.9 m data.

## Consequences

There is no retained intermediate 1.5-2.5 m production calibration site.
The existing 2 m test is regression evidence only. Santee acceptance cannot
establish general calibration for every resolution or watershed.

## Evidence

See the [execution plan](../work-packages/20261115_culvert_stream_order_resolution_boundary/prompts/active/implementation_execplan.md)
for retained batches, acceptance gates, and replay procedure.

## Risk and Rollback Notes

Three passes may still produce excessive counts or lose drainage semantics.
Reject acceptance and revert to the strict mapping if replay gates fail.
Do not promote to production pending forest evidence and final decision.

## Implementation Notes

Preserve the helper signature, formula, 4 m boundary, and queue wiring.
Require uncached SDA soil builds before restart and immediately before replay.

## Disposition

The three-pass candidate repaired classification but failed the Santee count
criterion. The operator subsequently selected per-run coarse-to-fine pruning
in ADR-0144, preserving supplied culvert connections while preferring simpler
networks. The earlier experiment remains evidence, not the final default policy.
