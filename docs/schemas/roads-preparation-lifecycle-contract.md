# Roads preparation and result lifecycle

Status: operator-approved direction, implementation pending (2026-10-22).
This is the upstream authority for preparation identity and current-result
eligibility across Roads producers, reports, downloads and GL Dashboard.
It does not claim that current runtime code already enforces every requirement.

## Decision and rationale

Roger selected a simple replacement lifecycle during the Roads dashboard design
conversation: Roads is beta; preserving old segment identity or backward
compatibility is not required. Preparation replaces the segment set. Previous
Roads results become unavailable as current results until a fresh Roads run
completes against that set. This rule is permanent, not a temporary beta workaround.

Reject stable-ID reconciliation, split/merge ancestry, cross-preparation matching,
and historical-result admission heuristics. They add complexity without serving
this workflow. Existing artifact hashes remain useful integrity evidence; they
are not a reason to introduce an identity/versioning subsystem for this feature.

## Identity and labels

- Each prepared geometry feature has a unique `segment_id` within the current set.
  It is a join key, not a durable real-world road identity. Sequential IDs are
  permitted; consumers must never join records across preparations.
- Each modeled profile has a unique `segment_run_id` within its execution.
  Several profiles may reference one prepared segment_id. That parent-child
  relationship is valid; duplicate geometry IDs or profile IDs are defects.
- Display the uploaded road name or ID where available, with a local segment label
  when needed. Do not present generated join keys as stable road names. No new
  source-name inference or identity reconciliation service is required.

## Replacement and invalidation

1. Accepted upload or model-affecting parameter changes invalidate Roads results
   and preparation as required by the existing controller state machine.
2. Before preparation overwrites any current segment geometry, revoke current
   Roads result readiness and invalidate result caches and discovery. Preparation
   replaces the whole segment set; it does not merge with prior preparations.
3. Invalidation covers the segment manifest/result association, segment summary,
   Roads-scoped aggregate/report resources, dashboard data and query catalog/cache
   admission. A leftover file or previously completed job must not re-enable them.
4. Until a fresh Roads execution successfully completes against the current set
   and its generated outputs pass readback validation, current Roads results are
   unavailable. Rebuilding a summary from old model outputs is not a fresh run.
5. Failed or interrupted preparation/execution remains unavailable; retry must
   not revive prior results. Prevent preparation/result publication races under
   existing run locking and job orchestration. A late response must not restore
   stale dashboard data after invalidation.
6. Baseline WEPP outputs remain independent. Their validity and visibility do not
   change merely because Roads is prepared again.

Enforce this in the upstream lifecycle and artifact publication, not only by hiding
one dashboard layer. Implementation must prove actual consumer behavior for
surviving old files, cached catalogs and failed attempts; clearing a NoDb summary
alone is insufficient. Use existing locks, status, artifact and cache mechanisms;
this contract does not prescribe new generation tokens or geometry fingerprints.

## Retention and beta compatibility

Invalidation is not permission to silently delete diagnostic evidence. Retained
old outputs may remain inspectable and archivable as explicitly historical files;
they must not be advertised or served as current Roads results. Archive restoration
must preserve a coherent project state and must not combine an old result set with
newly prepared geometry. Follow the artifact-observability standard.

No migration, stable identity repair, or compatibility admission path is required
for pre-contract beta projects. When current-result eligibility cannot be established,
the supported recovery is **Prepare and run Roads again**. Do not guess from matching
segment IDs, relabel old outputs, or reuse old model outputs to certify the new set.
Existing legacy parsing of diagnostic artifacts does not make them current results.

## Consumer behavior and acceptance

Reports, result download links, query-backed views and GL Dashboard use the same
current-result eligibility. UI wording is simple: **Run Roads to generate results**
after successful preparation, or the actual preparation/run error on failure.
No user-facing preparation versions, lineage controls or compatibility switches.

Required acceptance: successful run -> prepare again -> no current Roads results
in any consumer -> fresh successful run -> new results only. Repeat with changed
geometry but reused sequential IDs, failed/interrupted preparation, failed run,
late job completion, page reload, cached query results, multiple profiles per
segment, and archive/restore. Verify baseline remains intact and historical
artifacts remain distinguishable. The user-approved lifecycle must be covered by
the independent contract checkpoint before production implementation.
