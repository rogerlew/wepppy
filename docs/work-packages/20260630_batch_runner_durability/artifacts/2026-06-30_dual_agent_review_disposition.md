# Dual Agent Review Disposition - Batch Runner Durability

## Metadata

- **Package**: `docs/work-packages/20260630_batch_runner_durability/`
- **Date**: 2026-06-30
- **Reviewers**:
  - Correctness/RQ reviewer: subagent `019f1a3e-ebd7-7531-aa78-04466f6dac32`
  - Security/data-integrity reviewer: subagent `019f1a3f-0ee2-7db3-90c0-0967c94f7e93`
- **Scope reviewed**: current local implementation after scaffold commit `82d7b8805`.

## Findings and Dispositions

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| DR-01 | High | Optional RAP/OpenET directives can be enabled while their optional NoDb controllers are absent, causing successful leaves to remain retry-eligible forever. | Fixed. `BatchRunner` now excludes optional RAP/OpenET completion tasks when the corresponding `rap_ts.nodb` or `openet_ts.nodb` file is absent. Added regression coverage. |
| DR-02 | High | `delete_batch_rq` cleared NoDb caches/locks before checking for active jobs. | Fixed. The worker-side active-job guard now runs before cache, lock, instance cleanup, and filesystem deletion. Added regression coverage. |
| DR-03 | Medium | Explicit full-rerun mode could fail before reset because retry selection classified old/corrupt leaf state before checking `if_exists_rmtree`. | Fixed. Full-rerun selection now bypasses pre-reset runstate classification and enqueues all leaves. Added regression coverage. |
| DR-04 | Medium | Retry classifier hand-joined leaf run IDs into paths without validating path separators or traversal markers. | Fixed. Template validation rejects unsafe generated run IDs, and classifier marks unsafe legacy leaf IDs as `invalid` without probing outside the batch run tree. Added regression coverage. |
| DR-05 | Medium | Diagnostic task-status collection could alter watershed worker success/failure outcome if `redisprep.dump` or Redis status lookup failed. | Fixed. Task-status collection is best-effort, records `metadata_warnings`, and does not change watershed worker return status. Added regression coverage. |
| DR-06 | Medium | Finalizer emitted unconditional completion without a failed/incomplete leaf summary. | Fixed. Finalizer now publishes a run summary status line and `BATCH_RUN_COMPLETED_WITH_FAILURES` when final classification still has failed, incomplete, missing, invalid, or retry-eligible leaves. Existing `BATCH_RUN_COMPLETED` is preserved for compatibility. Added regression coverage. |
| DR-07 | Medium | `run-batch` route lacked the batch-name validation already used by `delete-batch`. | Fixed during local review. `run-batch` now validates names before resolving the batch path. Added regression coverage. |

## Residual Items

- Existing broad exception boundary catches in touched files still cause changed-file broad-exception enforcement to fail relative to `origin/master`. No new broad catches were introduced by the durability package.
- Concurrent pytest execution can collide on distributed NoDb locks for BatchRunner fixtures; affected endpoint tests pass when run sequentially.
- Production rollout remains pending active-job preflight and operator approval.

## Validation After Disposition

- `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1` - 18 passed after the watershed-interchange retry follow-up.
- `wctl run-pytest tests/microservices/test_rq_engine_batch_routes.py --maxfail=1` - 10 passed.
- `wctl run-pytest tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1` - 9 passed.
