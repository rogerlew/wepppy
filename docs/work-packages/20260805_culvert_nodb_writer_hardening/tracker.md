# Tracker - Culvert NoDb Writer Hardening

> Living record for the culvert batch shared-writer incident and conformance fix.

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-06 00:24 UTC

**Current phase**: Closed

**Last updated**: 2026-08-06 01:15 UTC

**Next milestone**: Complete the 30-day production observation window

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-08-05_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Diagnosed the production stale-write race and excluded archive/fork
  overlap (2026-08-06 00:24 UTC).
- [x] Ratified implementation as conformance to the committed NoDb contract
  (2026-08-06 00:24 UTC).
- [x] Scaffolded the work package and active ExecPlan
  (2026-08-06 00:24 UTC).
- [x] Added route, stale-refresh, child-isolation, and finalizer regressions
  (2026-08-06 00:36 UTC).
- [x] Implemented parent/finalizer shared-state ownership
  (2026-08-06 00:36 UTC).
- [x] Passed focused, full-suite, documentation, exception, and diff gates
  (2026-08-06 00:50 UTC).
- [x] Dispositioned independent correctness, QA, and security reviews with no
  unresolved findings (2026-08-06 01:10 UTC).
- [x] Closed the package and archived the ExecPlan
  (2026-08-06 01:15 UTC).

## Timeline

- **2026-08-05 16:30:22 UTC** - rq-engine enqueued the parent and wrote the
  same shared runner receipt the worker was loading.
- **2026-08-05 16:33:49 UTC** - the parent stale dump was rejected before child
  enqueue.
- **2026-08-06 00:24 UTC** - opened this conformance hardening package.
- **2026-08-06 00:36 UTC** - completed implementation and focused regression
  validation.
- **2026-08-06 00:50 UTC** - full suite completed with 5,842 passed and 61
  skipped.
- **2026-08-06 01:10 UTC** - independent re-review passed correctness, QA,
  security, RQ graph, and documentation gates with no remaining findings.
- **2026-08-06 01:15 UTC** - closed the package and archived the ExecPlan.

## Decisions Log

### 2026-08-06 00:24 UTC: Preserve strict stale detection and remove writers

**Context**: The generation guard exposed an actual ownership conflict; it was
not the source of state loss.

**Options considered**:

1. Disable generation checks or treat stale writes as success.
2. Retry every existing writer against refreshed state.
3. Remove avoidable writers, then use bounded refresh only at the remaining
   parent-owned initial transaction.

**Decision**: Option 3. The route returns the RQ receipt without persisting it,
children write run-local metadata only, and the finalizer merges shared
results. The stale guard remains untouched.

**Impact**: Shared mutation becomes deterministic without serializing child
work or accepting lost updates.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Parent receipt is no longer visible from NoDb immediately after HTTP response | Medium | Low | Response and RQ metadata remain immediate; worker writes the durable NoDb receipt | Mitigated |
| Child result is absent when finalizer runs | High | Low | Preserve RQ dependencies and reconstruct only from completed run metadata | Mitigated |
| Retry/manual child job lacks a current shared receipt | Medium | Low | Treat RQ metadata as live job source; retain parent-owned planned receipts | Accepted residual |
| Stale retry overwrites newer state | High | Low | Rehydrate a fresh runner and mutate only the intended idempotent fields under lock | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: one parent failed before child enqueue; 22
  child shared-write warnings occurred across two earlier successful batches.
- **Post-change health signals**: deterministic regressions pass; production
  deployment observation remains pending.
- **Danger signals observed**: two independent writers for the parent receipt
  and parallel children writing shared `_runs` metadata.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable.

## Verification Checklist

### Code Quality

- [x] Focused pytest passes (`43 passed`).
- [x] Full `wctl run-pytest tests --maxfail=1` passes (`5,842 passed`, `61
  skipped`).
- [x] Changed-file broad-exception and quality observability checks recorded.
  Broad-exception debt decreased by four; the observe-only report did not
  produce changed-file deltas and its generated tracked reports were restored.
- [x] `git diff --check` passes.

### Security

- [x] Route authorization/CSRF and response contracts remain unchanged.
- [x] NoDb stale-write and filesystem boundaries remain intact.
- [x] Dedicated review closes with no unresolved medium/high finding.

### Documentation

- [x] Contract discrepancy and rationale recorded before implementation.
- [x] Culvert integration docs describe writer ownership.
- [x] Package and touched docs pass canonical lint (8 files, 0 errors, 0
  warnings).

### Testing

- [x] Submit route does not write shared NoDb state.
- [x] Parent refreshes after an initial stale write and retries boundedly.
- [x] Children write run-local metadata without shared runner mutation.
- [x] Finalizer rebuilds the shared summary from run-local metadata.

## Progress Notes

### 2026-08-06 00:24 UTC: Package opened

**Agent/Contributor**: Codex

**Work completed**:

- Captured the exact incident signature and prior child-write warnings.
- Mapped the defect to the committed NoDb single-writer contract.
- Defined regression and closeout gates.

**Next steps**:

- Add focused regressions before implementation.
- Apply the smallest conformance changes and run required gates.

### 2026-08-06 00:52 UTC: Implementation and validation complete

**Agent/Contributor**: Codex

**Work completed**:

- Removed the route and child shared NoDb writers.
- Added fresh-runner retry to the parent's initial transaction while leaving
  generation checks unchanged.
- Verified finalizer reconstruction and explicit missing-parent child failure.
- Passed 43 scoped tests, the 5,904-test repository collection, docs lint,
  changed-file exception enforcement, and diff checks.

**Test results**: `5,842 passed`, `61 skipped`, 1 collection skip, no failures.

**Next steps**:

- Disposition independent correctness, QA, and security review findings.
- Close the package and begin the post-deploy observation window.

### 2026-08-06 01:15 UTC: Review disposition and package closure

**Agent/Contributor**: Codex; independent reviewer
`batch_runtime_station_review`

**Work completed**:

- Fixed the review finding that a successful retry could retain a prior
  finalizer-owned error, then added a refinalization regression.
- Refreshed generated RQ graph artifacts and closed coverage/documentation
  findings.
- Re-ran focused and full validation after remediation.
- Closed correctness, QA, and security review with no unresolved findings.

**Residual risk**: Concurrency regressions simulate generation changes rather
than launch multiple processes; production observation remains required for 30
days.

**Next steps**: Monitor the health and danger signals in this tracker during
the post-deploy observation window.
