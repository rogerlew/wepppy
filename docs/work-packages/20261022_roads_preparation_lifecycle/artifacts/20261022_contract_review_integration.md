# Independent integration and security contract review

Date: 2026-10-22. Reviewer: integration_contract_review. Starting runtime revision:
`c3ac573e3`. Runtime implementation was untouched during this review.

## Disposition

Approve the concrete contract checkpoint. No unresolved high or medium contract
finding remains. This is approval to implement the specified lifecycle, not a
runtime, security closure, or deployment claim.

The approved design is bounded: a current-output receipt written last, a single
run-local filesystem lock, visible retained history and shared consumer admission.
It does not introduce durable segment identity, preparation versions, migration,
cross-preparation matching or a compatibility admission subsystem.

Reviewed authorities and fingerprints:

| Document | SHA-256 |
| --- | --- |
| roads-preparation-lifecycle-contract.md | `8d1ff31251de6b8223bf0e7f549cbaefb330a65e698c64017ec780e682494e67` |
| artifacts/20261022_contract_decision.md | `76b88ee8f3140fd3b9fc8e7b36f3e660452c91a49ed7c5cc9e3a8dfff5e0e7c0` |
| output-scope-contract.md | `e21662e174c2038831500a85967e6c5f0f198d726305a6a607da0a642bcfb575` |
| roads-water-accounting-contract.md | `29d849a2461c91e5df6ebfbe6a735681b6d245b8cc8f18fcc62758d099f791d1` |

Also reviewed the package, active ExecPlan, segment-summary/GL contract references,
existing producer/controller, report/cache readers, query planning/execution,
browse/download services, GL request handling and canonical archive/restore.

Final amendment reread confirms exact receipt fields and an independently checked
mandatory resource set, including the executed single-storm/continuous mode.
An empty or shortened receipt cannot certify itself. Producer-owned internal
readback may reuse its exclusive guard without granting public access before
publication. Rejected preflight or retention that fails before invalidation
preserves an untouched prior coherent set; every failure after accepted
invalidation remains non-current. These clarifications preserve approval and
introduce no unresolved high or medium finding.

## Findings resolved in the concrete contract

| ID | Severity | Concrete risk | Contract disposition |
| --- | --- | --- | --- |
| INT-01 | High | RQ's runtime lock does not cover direct upload/parameter/controller mutations; TTL-based ownership alone cannot stop a late writer. | All writers share the persistent flock guard through mutation and publication; no independent direct-controller bypass. |
| INT-02 | High | Cached catalogs/plans and physical path aliases bypass discovery-only checks. Lazy Arrow/DuckDB reads and deferred FileResponse streaming outlive a handler-only guard. | Classify logical and resolved source paths; hold shared admission through actual materialization or response streaming; current logical IDs cannot resolve into history. |
| INT-03 | High | Restore can unlink a held lock inode or expose a receipt extracted before later restoration fails. | Preserve the root lock inode, coordinate the whole restore, validate success and revoke extracted readiness on failure before unlocking. |
| INT-04 | Medium | Moving only output loses matching prepared context or leaves overwritten inputs/failed diagnostics unretained. Copying private files into permissive ancestry can broaden access. | Retain output receipt, prepared context, manifest, actual segments/accounting ledger, prior run inputs and partial failures; preserve directory restrictions as well as file modes. |
| INT-05 | Medium | Roads report caches outside wepp/roads can remain queryable/downloadable after output invalidation. | Explicitly inventory, retain and classify wepp/reports/cache/hillslope_watbal_summary_roads.parquet, its metadata sidecar and attempts tree; preserve baseline siblings. |
| INT-06 | Medium | Undefined absent/legacy/error behavior can become a silent baseline fallback, blank successful report or hidden diagnostic state. | Missing/malformed/incomplete receipt means unavailable; stable 409 codes/no-store; prepared geometry and logs remain available, history is ordinary diagnostic data, failed partial output is retained before writer release. |

The initial ledger path spelling was corrected to
`wepp/roads/segments/roads.accounting.json`. Segment detail's existing
segment_id-keyed dictionary cannot prove unique model-profile identity; the
contract now requires original manifest rows and permits synthetic remainders.

## Valid-state and error assessment

- No Roads state: baseline reports and whole-project browse continue normally.
  Direct current Roads result requests are unavailable without creating readiness.
- Prepared but unrun: geometry/attributes remain available; stale execution
  fields and current results do not. The normal action is to run Roads.
- Completed current run: the full producer validates outputs, persists completed
  state, then atomically writes the receipt last. Required resources follow the
  existing continuous versus single-storm contracts.
- Accepted preparation/input replacement: prior output and receipt move to
  visible history before inputs change. Reused sequential IDs do not admit old
  results. Invalid requests that are not accepted must not acquire accidental
  permission to overwrite the current prepared set.
- Interrupted/failed work: current admission remains revoked. Useful partial
  output is retained in history; retention failure remains explicit and cannot
  delete diagnostics or publish readiness.
- Rejection before accepted invalidation: an untouched coherent prior set may
  stay current. This does not authorize restoring old readiness after any
  partial mutation.
- Legacy output/archive without receipt: diagnostic evidence remains historical;
  prepare/run is the recovery. No read or postprocessing action certifies it.
- Concurrent readers/writers: nonblocking conflicts are explicit. Current-result
  unavailability is HTTP 409/roads_results_unavailable; mutation contention is
  HTTP 409/roads_operation_busy, after ordinary authorization. Query transports
  preserve their existing envelope shape.
- Restored valid current archive: success validates the whole restored set under
  the writer guard. A failed restore cannot leave an extracted receipt admitted.

## Concrete implementation hooks

1. Roads methods and status/detail: direct set/upload/prepare/run entry points,
   `_clear_stale_run_state_locked`, `_prepare_roads_output_workspace`,
   `_prepare_roads_runs_workspace`, `_load_execution_records`, results context
   and final publication. Existing destructive workspace resets must follow
   successful retention. Ensure nested internal producer calls do not deadlock
   by acquiring a second independent lock descriptor against their own writer.
2. Report/cache reads: `wepp/reports/output_scope.py`, scoped report constructors,
   HillslopeWatbal's cache path and return-period products. Guard report routes
   before their existing broad missing-report catches; a lifecycle rejection
   must not turn into an apparently successful empty report.
3. Query engine: `core._dataset_source_sql` and `executor.execute`, including
   already-built QuerySource objects through `fetch_arrow_table`. Filter stale
   discovery and handle both standard server and MCP error envelopes. A parent
   source's resolved owner must govern its admission; keep baseline parent assets
   independent. Refreshing catalog JSON alone is insufficient.
4. Browse/download: directory inventories, schema and Parquet previews, raw and
   filtered binary/CSV downloads, deferred FileResponse streaming and aria2c
   inventory. Preserve authenticated historical reads and release shared guards
   on completion, exception and client disconnect. Also classify the external
   Roads cache family, including stale catalog aliases into it.
5. GL/dashboard clients: result admission at bootstrap and actual queries;
   cancellation/state barriers for the invalidating client. Clear cached Roads
   views and drop older in-flight replies. The bounded cross-session guarantee
   is next-read/reload correctness, not retracting an already delivered response.
6. Archive: canonical archive/restore uses the same guard; the empty coordination
   file is the explicitly named exclusion, while history and useful failures
   remain ordinary project records. Restore must preserve the guard inode.

## Minimum executable acceptance evidence

Use real files and actual readers for the full success -> prepare -> unavailable
-> fresh-success transition. Include changed geometry with reused IDs, multiple
profiles per geometry, valid empty diagnostics, single storm, legacy files and
absent Roads state. Retain unchanged baseline hashes.

Construct stale in-memory catalogs and plans, logical-to-history aliases, external
Roads report caches, surviving old files and read-only report-cache paths. Exercise
all direct current readers and confirm the contracted 409/no-store behavior,
without changing history or baseline access. Use actual streamed responses and
lazy query consumption for the shared-lock tests, including disconnect cleanup.

Use separate processes for writer/read contention, direct mutation versus queued
run, and late completion. Exercise retention failure before and after moving
current output, publication failure, retry, and private-directory permissions.
Test actual archive/restore member bytes/modes, preserved lock inode, interrupted
restoration after receipt extraction, legacy archive and successful coherent
restore. Verify history and failed artifacts through live browse/download using
the existing runtime identities and ordinary authorization.

Only the real full Roads producer may satisfy final publication acceptance;
fabricated receipts can test parser rejection but cannot prove this workflow.

## Residual limits

Filesystem flock behavior across the deployed shared mounts and participating
service identities remains an implementation validation obligation. This review
does not certify it from the local precedent. It also does not certify native
hydrology, cross-session live notification, adversarial writers outside the guarded
lifecycle, or production rollout. No new identity/lineage subsystem is warranted
by these remaining tests.
