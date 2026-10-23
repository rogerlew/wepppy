# Roads preparation and result lifecycle

Status: implemented and locally environment-validated (2026-10-23 UTC).
This is the upstream authority for preparation identity and current-result
eligibility across Roads producers, reports, downloads and GL Dashboard.
Implementation and retained evidence: [Roads lifecycle package](../work-packages/20261022_roads_preparation_lifecycle/package.md), runtime commit `e4d28c9ad`. Production deployment is separate.

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

## Implementation admission and retention contract

The implementation work package uses a plain current-output receipt, not durable
segment identities or preparation versions. `wepp/roads/output/roads.current.json`
has policy `roads_current_v1` and lists the required validated Roads report resource
paths relative to the project root. Only the full Roads execution publishes it,
atomically and last, after completed state persistence and generated-output
validation. Postprocessing alone never publishes it. Missing, malformed, aliased
or incomplete receipt/resources mean unavailable, including old beta projects.
Empty valid diagnostics and single-storm runs retain their existing report-resource
requirements; a segment summary is not required for a single-storm run.

A project-root `roads.lifecycle.lock` coordinates all Roads input mutations,
preparation, execution/publication and current-result reads using the existing
filesystem flock pattern. Writers use an exclusive lock; current readers hold a
shared lock through actual data consumption/materialization or response streaming.
Conflicts are nonblocking and explicit. The lock lives outside all moved trees;
archive/restore participates in it, excludes the empty coordination file from ZIP
members and preserves its inode during restore. Project paths and lock/output/history
aliases are rejected before mutation. A disconnected or failed reader releases its
lock. No process-wide runtime identity or permission changes are authorized.

Before mutation, revoke current admission by moving prior output (including its
receipt as historical evidence) into a fresh visible
`wepp/roads/history/<unique-directory>/` snapshot. Retain corresponding prepared
geometry, prepare summary and execution manifest with it, so historical IDs have
historical context. A fresh run preserves the active prepared geometry; preparation
replaces it. Unique history directory names prevent overwrite and are not segment
identity/version controls. If retention fails before the current tree moves, abort without replacing inputs;
otherwise interrupted invalidation remains non-current and retains whatever history
was already moved. Retries must not destroy it. Keep source-relative
layout in history and permit normal authorized browsing/download/archive of history.

Direct current-prefix browse, schema, preview, CSV and binary downloads, aria2c
inventory, current Roads report links and scope-based report/dashboard reads, and
query execution all honor the same admission. Query checks classify both logical
catalog IDs and resolved physical sources, including cached plans and parent-source
paths: a current logical ID must not silently resolve into historical data. Historic
paths explicitly requested as history remain ordinary authorized diagnostic reads.
Current-prefix directories may explain unavailability, but must not advertise stale
or in-progress files as current results. Parent directory inventories must not offer
an invalid current output subtree as ready data.

Current-result HTTP reads unavailable due to lifecycle state use status 409 and
code `roads_results_unavailable`, with a useful preparation/run action. A conflicting
mutation uses 409 and `roads_operation_busy`. Preserve authentication/authorization
before these responses. Current-result HTTP responses use Cache-Control: no-store;
no authorization bypass, baseline fallback or silent HTTP 200 empty success.
Query transports retain their existing envelope shape with the new stable error code.
Ordinary absent Roads state must not break baseline routes or whole-project browsing.

The request that initiated invalidation clears its Roads result view and ignores
older in-flight results using existing request cancellation/state mechanisms.
Server responses already delivered before another session mutates the project
cannot be retracted; subsequent reads/reloads must reflect invalidation. Do not add
a polling service or a live cross-session notification guarantee for this package.

Publication verifies required generated resources are readable and complete under
the existing scope/accounting contracts. Segment/profile IDs are validated within
the current set; synthetic replacement remainders are explicitly allowed without
road geometry. Validation must include the actual producer and direct consumers,
not fabricated readiness receipts alone. Historical retention/admission is a deliberate
amendment to existing current-only output path rules; baseline paths stay unchanged.

### Diagnostic and restore details

Prepared road geometry remains available without current results. Segment detail
must withhold stale execution fields while preserving prepared geometry/attributes.
Do not use a segment_id-keyed dictionary to validate multiple model profiles;
validate original manifest rows by unique segment_run_id.

Retain `wepp/roads/segments/roads.accounting.json` when present, prepared geometry/summary,
manifest, prior run inputs and partial failed outputs with historical attempts.
During active writes, current output consumption is temporarily unavailable under
the exclusive lock; the ordinary Roads lifecycle log remains inspectable. On run
failure preserve partial outputs in visible history before releasing the writer,
so useful failed output is inspectable without a current-result bypass switch.
History preserves directory access restrictions as well as file modes; moving a
private tree must not broaden its effective access through more permissive ancestry.
Failure to move history must not publish readiness or delete original diagnostics;
report the retention error with its path and leave current admission revoked.

Restore must not admit a receipt extracted before the rest of the project. Hold
the writer guard for the entire restore, validate the complete restored current set
on success, and revoke any extracted current receipt before releasing the guard on
failure. A legacy archive with no receipt restores as non-current; it does not
receive a fabricated one. Preserve the coordination file through root cleanup.

Roads-specific report caches outside the output tree are also current-result
artifacts: `wepp/reports/cache/hillslope_watbal_summary_roads.parquet`, its
`.meta.json` sidecar and `hillslope_watbal_summary_roads.attempts/` tree. Invalidation
retains these under history with their source-relative paths; query/browse/download
classification includes them. Preserve baseline cache siblings. New Roads report
caches must explicitly participate in this inventory rather than relying on output-
prefix discovery alone.

Receipt fields are exactly policy `roads_current_v1`, boolean `is_single_storm`,
and nonempty unique string list `required_relpaths`. Paths are project-relative,
non-traversing and non-aliased. Admission validates the mandatory set independently
of the supplied list: both modes require H.pass.parquet, ebe_pw0.parquet and README.md
under Roads interchange; continuous mode additionally requires H.wat.parquet,
loss_pw0.out/hill/chn.parquet, totalwatsed3.parquet and roads_segment_loss_summary.parquet.
The mode comes from executed model configuration at publication, not the request.
Existing accounting and channel-water resource requirements apply when produced;
include their paths in the receipt. Empty/shortened lists cannot self-certify.
Producer readback may use its already-held exclusive operation guard rather than
reacquiring public shared admission before publication. That trusted in-process
producer context does not grant external readers access to unpublished results.

Preflight rejection or retention failure before invalidation is accepted aborts
without changing the prior coherent result set; that untouched set may remain
current. Once invalidation succeeds, any preparation/run failure stays non-current.
This distinction prevents a rejected request from being treated as a completed
replacement, and does not permit restoring old readiness after partial mutation.
