# Tracker - AgFields Watershed Parent Job

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-15 23:07 UTC
**Current phase**: Closed
**Last updated**: 2026-07-16 04:25 UTC
**Next milestone**: None
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260715_agfields_watershed_parent_job/artifacts/2026-07-15_security_review.md`

## Task Board

### Ready / Backlog

None.

### In Progress

None.

### Blocked

None.

### Done

- [x] Read the canonical ExecPlan, work-package, RQ API/operator, test, and
      subsystem instructions (2026-07-15 23:07 UTC).
- [x] Completed read-only code archaeology of the existing route and canonical
      `jobs:*` parent metadata pattern (2026-07-15 23:07 UTC).
- [x] Recorded the conversation-derived behavior and compatibility contract
      before implementation (2026-07-15 23:07 UTC).
- [x] Implemented the parent, three serial children, failure-tolerant finalizer,
      state/UI tracking, recursive lifecycle, and cancellation hardening
      (2026-07-15 23:40 UTC).
- [x] Passed focused Python (84 tests), frontend (635 tests), lint, stub, graph,
      endpoint/checklist, broad-exception, and docs gates before final review
      remediation (2026-07-15 23:40 UTC).
- [x] Completed both independent reviews with no unresolved findings
      (2026-07-15 23:55 UTC).
- [x] Passed final broad verification: 4,914 Python tests, 635 frontend tests,
      lint, stub, graph, contract, broad-exception, diff, and documentation gates
      (2026-07-16 00:03 UTC).
- [x] Restarted the local forest services and submitted the authenticated Run
      All parent for `sacral-self-discipline` (2026-07-16 00:01 UTC).
- [x] Completed terminal forest acceptance: parent 5/5, all scheme children and
      finalizer finished, and all fixed output resources verified
      (2026-07-16 04:23 UTC).
- [x] Closed the security gate, archived the ExecPlan, and closed the package
      (2026-07-16 04:25 UTC).

## Timeline

- **2026-07-15 23:07 UTC** - Package opened and execution began.
- **2026-07-15 23:40 UTC** - Dual review findings remediated; final re-reviews
  dispatched.
- **2026-07-15 23:55 UTC** - Both independent final reviews passed with no
  unresolved findings.
- **2026-07-16 00:01 UTC** - Local forest accepted one suite parent, three
  named scheme children, and one finalizer.
- **2026-07-16 04:23 UTC** - The parent reached 5/5 terminal success after all
  children and the finalizer; all 27 required output resources existed.
- **2026-07-16 04:25 UTC** - Package closed and ExecPlan archived.

## Decisions Log

### 2026-07-15 23:07 UTC: Use one dispatch parent only for Run All

**Context**: The existing endpoint returns the first of three independent jobs,
so the dashboard cannot represent the submission as one canonical task tree.

**Options considered**:

1. Keep route-level independent jobs - rejected because it preserves the defect.
2. Add a parent for every request - rejected because it adds unnecessary
   topology to unchanged single-scheme runs.
3. Add one Run All dispatch parent with registered scheme children - selected.

**Decision**: Run All returns a dedicated suite parent and keeps the existing
scheme IDs as children. Single schemes remain direct jobs.

**Impact**: The `all` response's top-level `job_id` intentionally changes from
the Concept 1 child to the suite parent; `job_ids` remains compatible.

### 2026-07-15 23:07 UTC: Preserve serial allow-failure execution

**Context**: The three watershed integrations are memory intensive, and the
comparison suite should still attempt later schemes after an earlier failure.

**Decision**: Keep stable Concept 1 -> Concept 2 -> hybrid dependencies with
`allow_failure=True`; do not parallelize.

**Impact**: Scientific outputs and resource pressure remain unchanged while job
ownership becomes composable.

### 2026-07-15 23:20 UTC: Use the batch finalizer pattern

**Context**: Roger Lew required the Run Batch finalizer behavior: the terminal
job must wait for all scheme jobs and must still run after child failure.

**Decision**: Add a fourth registered finalizer child depending on all three
scheme IDs via `Dependency(..., allow_failure=True)`.

**Impact**: Final suite hydration/telemetry has one deterministic terminal point;
failure of a routing child does not strand the finalizer in deferred state.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Parent reports terminal while a descendant still runs | High | Medium | Regression-test tree aggregation with failed + active children | Closed |
| Cancel stops at already-finished dispatch parent | High | High | Traverse descendants after benign terminal-parent cancel errors | Closed |
| Reload tracks a child instead of the suite parent | Medium | Medium | Add suite state key and frontend hydration test | Closed |
| Child IDs/state race before first enqueue | Medium | Low | Preallocate IDs; parent persists all IDs before enqueueing first child | Closed |
| Failed child strands finalization | High | Medium | Finalizer depends on every scheme ID with `allow_failure=True` | Closed |
| Failed predecessor before dependent registration | High | Medium | Apply Batch Runner ready-deferred release after every dependent enqueue | Closed |
| Cancellation races incomplete dispatch | High | Medium | Register full tree atomically; share dispatch lock and cancel marker | Closed |
| Cross-run cancellation | High | Medium | Enforce `authorize_run_access` from job metadata; regression-test user/service/MCP denial | Closed |

## Verification Checklist

### Code Quality

- [x] Full Python tests pass.
- [x] Frontend tests and lint pass.
- [x] Stub surface passes.
- [x] RQ dependency graph is current.
- [x] No unresolved security findings.

### Security

- [x] Auth/run access remains unchanged.
- [x] Queue and cancellation surfaces reviewed.
- [x] No unresolved medium/high findings.

### Documentation

- [x] AgFields README and UI contract updated.
- [x] RQ catalog and API contract updated.
- [x] Work-package closure and completed ExecPlan archived.

### Testing

- [x] Route and worker unit tests pass.
- [x] Job-tree aggregation and cancellation regressions pass.
- [x] Authenticated manual forest smoke passes.
- [x] Fixed output roots verified.

## Progress Notes

### 2026-07-15 23:07 UTC: Scaffold and discovery

**Agent/Contributor**: Codex with read-only archaeology subagent

**Work completed**:

- Confirmed the current route-level three-job chain.
- Confirmed the canonical `job.meta["jobs:..."]` recursive tree convention.
- Scoped additive suite state and required lifecycle/cancellation hardening.

**Next steps**:

- Implement parent worker and tests.
- Run gates and live acceptance.

**Test results**: Not yet run.

### 2026-07-16 04:25 UTC: Closure

**Agent/Contributor**: Codex with independent code and QA/security reviewers

**Work completed**:

- Verified the live parent at 5/5 terminal success with ordered groups 0-3.
- Verified all child and finalizer jobs finished without exceptions.
- Verified 3,543 parent/PASS rows and all nine required resources for each
  fixed scheme output tree.
- Closed all review/security findings and archived the completed ExecPlan.

**Test results**: Full Python suite 4,914 passed/58 skipped; frontend 635 tests;
all focused, lint, stub, graph, contract, broad-exception, diff, and docs gates
passed.

## Watch List

- Parent aggregation when an earlier allow-failure child fails and a later child
  remains active.
- Worker stack memory while the live three-scheme chain runs.

## Communication Log

### 2026-07-15 23:07 UTC: Operator request

**Participants**: Roger Lew and Codex
**Question/Topic**: Replace three independent Run All submissions with one
canonical parent and child jobs; execute with dual review and forest acceptance.
**Outcome**: Option 3 above selected; Codex authorized to dispatch reviewers and
restart the local stack.
