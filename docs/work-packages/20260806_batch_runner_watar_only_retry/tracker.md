# Tracker - Batch Runner WATAR-Only Retry Correctness

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-06 19:56 UTC

**Current phase**: Closed

**Last updated**: 2026-08-06 21:18 UTC

**Next milestone**: Separately authorized deployment and production retry

**Security impact**: low

**Dedicated security review**: no

**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Compare the exact incident serialization with the cases already covered
  by `tests/rq/test_batch_rq_retry_selection.py`.
- [ ] Add an incident-shaped WATAR-only regression that records timestamp and
  artifact fingerprints before and after execution.
- [ ] Implement only gaps demonstrated by the characterization tests.
- [ ] Verify caught leaf failures write failed metadata and produce the final
  failure summary without breaking sibling/finalizer execution.
- [ ] Run focused tests and a disposable generated WATAR-only integration run.
- [ ] Update Batch Runner documentation and obtain independent correctness
  review.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Diagnosed production job
  `4fae6b30-709b-49b8-bd4e-f177b03344e7`: dispatcher enqueued 93
  leaves, all 93 returned application failure, and none produced ash results.
  (2026-08-06 19:56 UTC)
- [x] Scoped the corrective package without changing production code or state.
  (2026-08-06 19:56 UTC)
- [x] Audited the current baseline and identified commit `70f74fef6` as the
  existing narrow runtime-station drift correction. (2026-08-06 20:18 UTC)
- [x] Added an active, self-contained ExecPlan and reconciled application
  failure semantics with the failure-tolerant RQ contract.
  (2026-08-06 20:18 UTC)
- [x] Confirmed the exact incident state matches the existing current-format
  runtime-station regression. (2026-08-06 20:31 UTC)
- [x] Added complete leaf-path reuse and caught-failure metadata regressions;
  focused tests pass. (2026-08-06 20:37 UTC)
- [x] Ran real WATAR/AshPost on a disposable completed WEPP leaf and proved
  climate/WEPP inputs and timestamps were unchanged. (2026-08-06 20:50 UTC)
- [x] Cleared local evidence state and moved the disposable batch to trash.
  (2026-08-06 20:51 UTC)
- [x] Passed NoDb and full Python validation, static gates, documentation lint,
  and final correctness review. (2026-08-06 21:18 UTC)
- [x] Closed the package and archived its ExecPlan. (2026-08-06 21:18 UTC)

## Decisions Log

### 2026-08-06 19:56 UTC: WATAR-only means reuse valid prerequisites

**Context**: The operator intentionally selected only `Run WATAR`; the stored
station fields did not represent a real climate change.

**Decision**: A WATAR-only run must recognize valid completed climate and WEPP
work and consume it. It must neither invalidate that work for representation-
only drift nor rerun WEPP implicitly.

**Impact**: The fix belongs at semantic climate-change detection and batch
result reporting, not in a new dependency scheduler.

### 2026-08-06 20:18 UTC: Preserve the existing narrow equivalence

**Context**: Baseline inspection found that commit `70f74fef6` already excludes
the supported runtime-resolved station pair from base-project resynchronization
and includes positive and negative unit tests.

**Decision**: Treat that implementation as the starting contract. Execution
must first reproduce the incident against it and may change production logic
only when a failing characterization demonstrates a remaining gap.

**Impact**: The package is now a bounded completion and end-to-end evidence
effort rather than a speculative rewrite of climate equivalence.

### 2026-08-06 20:18 UTC: RQ transport completion is not leaf success

**Context**: `run_batch_watershed_rq` catches leaf exceptions, persists failed
metadata, and returns `(False, elapsed)` so other leaves and the finalizer run.
The finalizer classifies durable leaf state and publishes
`BATCH_RUN_COMPLETED_WITH_FAILURES`.

**Decision**: Preserve failure-tolerant RQ completion. Acceptance requires
failed durable metadata and a failed final summary; it does not require the RQ
job itself to enter RQ's failed registry.

**Impact**: No queue topology change is planned, and `wctl check-rq-graph` is
conditional on an actual enqueue/dependency edit.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Real climate changes are incorrectly treated as equivalent. | High | Medium | Characterize material versus non-material fields and retain a negative invalidation test. | Open |
| WATAR consumes missing or stale WEPP artifacts. | High | Low | Keep explicit timestamp and artifact prerequisite checks. | Open |
| Fix adds unnecessary orchestration complexity. | Medium | Low | Limit edits to comparison, validation, result semantics, tests, and docs. | Open |
| RQ continues to label caught leaf failures as successful. | Medium | Medium | Assert aggregate status against a false leaf result. | Open |

## Verification Checklist

- [x] `wctl run-pytest tests/nodb/test_batch_runner_watar.py --maxfail=1`
- [x] `wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1`
- [x] Applicable broader Python suite passes.
- [x] `wctl check-rq-graph` not required; no RQ wiring changed.
- [x] `wctl doc-lint --path docs/work-packages/20260806_batch_runner_watar_only_retry/package.md`
- [x] `wctl doc-lint --path docs/work-packages/20260806_batch_runner_watar_only_retry/tracker.md`
- [x] Disposable generated WATAR-only leaf reuses existing climate/WEPP and
  produces Ash/AshPost outputs.
- [x] Final correctness review has no unresolved findings; disposition is in
  `artifacts/2026-08-06_correctness_review.md`.

## Progress Notes

### 2026-08-06 19:56 UTC: Incident-driven scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the observed false invalidation and misleading finished status.
- Converted the operator requirement into bounded acceptance criteria.
- Kept production execution and deployment explicitly outside this scaffold.

**Next steps**:

1. Add a failing regression that reproduces the stored-value mismatch.
2. Implement semantic equivalence without weakening real climate invalidation.
3. Prove WATAR-only reuse on a disposable generated leaf.

**Test results**: Documentation-only scaffold; validation pending.

### 2026-08-06 20:18 UTC: Execution-readiness review

**Agent/Contributor**: Codex

**Work completed**:

- Reconciled the package with the already-shipped runtime-station drift fix.
- Defined the exact supported semantic-equivalence pair and fail-closed cases.
- Clarified durable application failure versus RQ transport completion.
- Added the active ExecPlan with exact files, commands, evidence, and recovery.

**Next steps**:

1. Execute Milestone 1 in the active ExecPlan.
2. Record exact incident-state evidence before any production-code edit.
3. Continue autonomously through generated-leaf proof and review.

**Test results**: Markdown lint is required after this revision.

### 2026-08-06 20:52 UTC: Implementation and generated evidence

**Agent/Contributor**: Codex

**Work completed**:

- Verified the incident signature read-only on `wepp1` and reconciled it with
  the earlier durability evidence.
- Added regression coverage for a WATAR-only `run_batch_project` execution that
  fingerprints persisted climate and WEPP artifacts.
- Added regression coverage for caught WATAR prerequisite failure metadata.
- Ran real Ash/AshPost against a disposable copy of a completed three-hillslope
  WEPP leaf and captured immutable-input and timestamp evidence.
- Updated Batch Runner operator documentation.

**Next steps**:

1. Run NoDb and full Python validation plus code-quality gates.
2. Complete correctness review and disposition any findings.
3. Close and archive the package plan.

**Test results**:

- Focused WATAR/Batch Runner modules: 42 passed, 8 warnings in 17.78 seconds.
- Generated evidence: 3 WATAR hillslope parquets and 5 AshPost parquets;
  climate/WEPP hashes and prerequisite timestamps unchanged.

### 2026-08-06 21:18 UTC: Validation and closure

**Agent/Contributor**: Codex

**Work completed**:

- Passed focused, NoDb, and full repository tests.
- Passed broad-exception, Python compilation, documentation, and diff gates.
- Completed a fresh diff-level correctness review with no findings.
- Closed the package; production deployment and rerun remain separate.

**Test results**:

- Focused modules: 42 passed, 8 warnings in 19.56 seconds.
- NoDb: 1,560 passed, 26 skipped, 28 warnings in 163.81 seconds.
- Full Python: 5,897 passed, 61 skipped, 1,048 warnings in 677.54 seconds.
- Broad exceptions: pass, net delta +0.
- Code-quality observability: report generated, observe-only.
- Documentation lint and `git diff --check`: pass.
