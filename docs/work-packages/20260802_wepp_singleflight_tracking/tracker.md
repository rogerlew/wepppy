# Tracker - WEPP Workflow Single-Flight Tracking

> Living record for the production incident fix and review evidence.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-08-03 06:41 UTC  
**Current phase**: Closed
**Last updated**: 2026-08-03 06:57 UTC
**Next milestone**: Production observation
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Production failure and duplicate-submission sequence diagnosed (2026-08-03 06:20 UTC).
- [x] Canonical single-flight contract recorded before implementation (2026-08-03 06:41 UTC).
- [x] Package and active ExecPlan scaffolded (2026-08-03 06:41 UTC).
- [x] RQ `JobStatus` enum normalization defect identified and covered (2026-08-03 06:48 UTC).
- [x] Contract decision and two independent contract-review dispositions recorded (2026-08-03 06:55 UTC).
- [x] Descendant-aware tracking and RQ 1.16 normalization implemented (2026-08-03 06:52 UTC).
- [x] Scoped tests, stub gates, documentation lint, and diff checks passed (2026-08-03 06:56 UTC).
- [x] Independent correctness and QA reviews closed with no High/Medium findings (2026-08-03 06:57 UTC).
- [x] Package closed and ExecPlan archived (2026-08-03 06:57 UTC).

## Timeline

- **2026-08-03 06:20 UTC** - Confirmed two same-run orchestrators completed quickly while their hillslope descendants overlapped.
- **2026-08-03 06:41 UTC** - Ratified complete-workflow tracking behavior and opened this package.
- **2026-08-03 06:48 UTC** - Confirmed the old string conversion also failed to normalize pinned RQ 1.16.2 enum statuses.
- **2026-08-03 06:52 UTC** - Dual reviews exposed RQ 1.16.2 byte dependency keys; runtime normalization and production-shaped tests were corrected.
- **2026-08-03 06:55 UTC** - Contract checkpoint completed at exact base revision `9a02c00f2700afdd4150e0e3bf760b6f530ff54f` with correctness and QA review artifacts.
- **2026-08-03 06:57 UTC** - Post-remediation code and QA reviews approved; package closed.

## Decisions Log

### 2026-08-03 06:41 UTC: Inspect the recorded orchestration tree

**Context**: Route admission stores the orchestration root ID, but that root finishes immediately after enqueueing child work.

**Options considered**:
1. Hold a Redis lock for the entire workflow, requiring reliable release on every descendant failure.
2. Replace the stored root with the final deferred job, which can remain deferred forever after an upstream failure.
3. Inspect child links already recorded on the root and distinguish live work from failure-stranded deferred work.

**Decision**: Option 3, because it preserves status/cancellation root identity and has explicit recovery behavior after failure.

**Impact**: Submission admission follows the existing RQ tree without changing dependency wiring.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| A failed dependency's deferred tail blocks all retries | High | Medium | Inspect each deferred job's transitive dependencies and suppress only jobs blocked by terminal failure/cancellation | Mitigated |
| Watershed-only paths escape tracking | High | Low | Parameterize regression coverage across all five canonical job keys | Mitigated |
| Job metadata contains missing/expired children | Medium | Low | Skip `NoSuchJobError` consistently with existing root handling | Mitigated |
| Root receipt expires during an outage/backlog longer than seven days | Medium | Very low | Record as residual; evaluate durable workflow receipts if production queue delay approaches retention | Accepted residual |

## Hardening Signal Log

- **Baseline health signals**: Two `_run_hillslopes_rq` jobs for one run overlapped on different workers.
- **Post-change health signals**: Pending deployment observation.
- **Danger signals observed**: Existing guard stopped at a finished orchestration root.
- **Temporary callus register**: None.
- **Softening experiments**: Not applicable.

## Verification Checklist

### Code Quality

- [x] Focused pytest passes (`118 passed`).
- [x] Full pytest sanity attempted; collection blocked by missing local `SECRET_KEY`.
- [x] RQ graph checked; pre-existing artifact drift documented, with no enqueue/dependency changes in scope.
- [x] `git diff --check` passes.

### Security

- [x] Low security impact recorded; no attack-surface change.
- [x] No unresolved medium/high reviewer findings.

### Documentation

- [x] Canonical contract updated before implementation.
- [x] Package, tracker, RQ README, and review artifacts complete.
- [x] Scoped documentation lint passes.

### Testing

- [x] Active descendant blocks duplicate submission.
- [x] Viable deferred descendant blocks duplicate submission.
- [x] Failed/stranded tree allows recovery.
- [x] Every canonical hillslope/watershed tracking key is covered.

## Progress Notes

### 2026-08-03 06:41 UTC: Contract checkpoint

**Agent/Contributor**: Codex

**Work completed**:
- Diagnosed the lifecycle mismatch between the stored orchestration root and its descendants.
- Recorded the cross-path single-flight contract and failure recovery rule.
- Created the work package and active plan.

**Next steps**:
- Implement the tree inspection helper and regression tests.
- Run the required gates, then initiate two independent reviews.

### 2026-08-03 06:57 UTC: Implementation and closure

**Agent/Contributor**: Codex

**Work completed**:
- Implemented root/descendant inspection, RQ enum normalization, and byte dependency-key normalization.
- Added 15 focused unit cases plus normal/bootstrap route regression execution.
- Resolved all independent code and QA review findings and archived the plan.

**Test results**: `118 passed` scoped; stubtest and stub completeness passed; docs lint and diff check passed. Full local collection was blocked by missing `SECRET_KEY`; canonical container wrappers were blocked by the stopped `weppcloud` service.
