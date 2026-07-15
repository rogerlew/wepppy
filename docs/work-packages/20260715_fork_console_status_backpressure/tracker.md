# Tracker - Fork Console Status Backpressure and Recovery

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-15 17:15 UTC
**Current phase**: Complete; awaiting separate production deployment
**Last updated**: 2026-07-15 17:32 UTC
**Next milestone**: Deploy through the wepp1 operator workflow and observe for 14 days
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260715_fork_console_status_backpressure/artifacts/20260715_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Deploy through a separate wepp1 operator action and start the 14-day observation window.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Replaced raw rsync streaming with bounded stage, heartbeat, summary, and failure telemetry (2026-07-15 17:32 UTC).
- [x] Implemented authoritative polling, dual completion signals, batched/bounded rendering, reload/resume recovery, and idle disconnection (2026-07-15 17:32 UTC).
- [x] Rebuilt assets; updated behavior docs; passed focused backend, complete frontend, lint, template, generated-asset, and docs gates (2026-07-15 17:32 UTC).
- [x] Completed code, QA, and security reviews with no unresolved package findings (2026-07-15 17:32 UTC).
- [x] Created package, tracker, active ExecPlan, ADR, and security-review scaffold (2026-07-15 17:15 UTC).
- [x] Captured production incident evidence and froze scope to requested items 1-7 (2026-07-15 17:15 UTC).

## Timeline

- **2026-07-15 05:23 UTC** - Production fork job started on wepp1.
- **2026-07-15 06:20 UTC** - RQ recorded the job as successfully finished while the hidden browser tab continued draining status output.
- **2026-07-15 17:15 UTC** - Package created and implementation started.
- **2026-07-15 17:32 UTC** - Implementation, documentation, validation, and review completed; production deployment deferred.

## Decisions Log

### 2026-07-15 17:15 UTC: Preserve dual signals with authoritative polling

**Context**: WebSocket completion and polling provide useful redundancy, but the UI must not declare a terminal result from an ephemeral stream alone.

**Options considered**:

1. WebSocket-only completion - rejected because Redis Pub/Sub has no replay.
2. Polling-only completion - rejected because it removes a useful prompt signal and existing redundancy.
3. Dual signal with job-status confirmation - selected.

**Decision**: Keep both signals. A WebSocket terminal trigger requests immediate status reconciliation; only `/jobstatus/<job_id>` terminal state completes or fails the UI.

**Impact**: Stream loss cannot hide completion, and a stale/unrelated stream message cannot authoritatively terminate the tracked job.

### 2026-07-15 17:15 UTC: Use bounded operational telemetry

**Context**: `rsync --progress` produced enough browser work to delay terminal presentation.

**Decision**: Remove per-file/per-progress output, emit stage transitions and a periodic heartbeat, retain bounded process-output tails, and publish final summary/error information only.

**Impact**: Users keep proof of activity without an unbounded browser or worker backlog.

### 2026-07-15 17:32 UTC: Render restored identifiers as text

**Context**: Reload recovery introduces a browser-storage-to-DOM boundary for the destination run ID.

**Decision**: Persist identifiers only, validate the stored record, URL-encode link paths, and construct labels with text nodes and `textContent`.

**Impact**: A modified session-storage record cannot inject markup through fork restoration.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Suppressed output hides useful rsync failures | Medium | Low | Retain bounded stderr/stdout tails and include them in explicit failure errors | Mitigated; covered |
| Shared StatusStream changes regress other controls | Medium | Low | Preserve append/event contracts and add focused StatusStream tests | Mitigated; 629 frontend tests pass |
| Session restoration tracks stale jobs | Low | Medium | Scope storage by run/config, validate payload, and clear on terminal state | Mitigated; covered |
| Hidden tabs still defer timers | Medium | Medium | Reconcile on visibility, focus, and pageshow | Mitigated; covered |

## Hardening Signal Log

- **Baseline health signals**: One observed successful 56-minute fork left the hidden console draining stale output well after RQ completion.
- **Post-change health signals**: Worker tests prove bounded publication/tails; browser tests prove terminal confirmation, reload/focus reconciliation, bounded batching, hidden-page deferral, and idle disconnection.
- **Danger signals observed**: Raw per-line rsync output plus whole-log rewriting on every message.
- **Temporary callus register**:
  - Session-scoped job restoration, owner WEPPpy frontend maintainers, introduced 2026-07-15, review after 14-day production observation.
  - Resume reconciliation hooks, owner WEPPpy frontend maintainers, introduced 2026-07-15, review after 14-day production observation.
- **Softening experiments**: None during initial implementation.

## Verification Checklist

### Code Quality

- [x] Targeted Python tests pass: 10 selected fork-worker tests.
- [x] Frontend tests pass: 85 suites and 629 tests.
- [x] Frontend lint passes.
- [ ] Broad pytest sanity passes. Blocked during collection by unrelated WEPPpyo3 interchange `WAT_OPTIONAL_COLUMN_NAMES` worktree failure.
- [ ] Broad-exception changed-file enforcement passes. Package file delta is zero; unrelated interchange files add three broad catches.

### Security

- [x] Security impact triage recorded as high because the worker subprocess boundary changes.
- [x] Dedicated security review is complete.
- [x] No unresolved medium/high package findings remain.
- [x] Subprocess and output-safety checks are explicitly reviewed.

### Documentation

- [x] Authoritative forking documentation updated.
- [x] Controller helper documentation updated.
- [x] Work-package closure notes complete.
- [x] ADR-0021 records operational thresholds and provenance.

### Testing

- [x] Unit coverage for bounded worker telemetry.
- [x] Frontend coverage for authoritative completion and recovery.
- [x] Generated asset parity verified by the stale-generated-controller test and standalone StatusStream harness.
- [x] Backward compatibility verified by the complete frontend suite.

### Deployment

- [x] Tested through the local Docker development tooling.
- [x] Production deployment explicitly deferred to a separate operator action.

## Progress Notes

### 2026-07-15 17:15 UTC: Package kickoff

**Agent/Contributor**: Codex

**Work completed**:

- Triaged the production job and confirmed RQ completion, no active rsync, and no continued Redis publication.
- Confirmed the deployed fork console already uses hybrid StatusStream plus two-second job-status polling.
- Recorded the user decision to implement requested hardening items 1-7 as a work package.

**Blockers encountered**: None.

**Next steps**:

- Implement worker telemetry changes and regression tests.
- Implement frontend lifecycle, storage, visibility, and rendering changes.
- Rebuild assets, update docs, and run gates/reviews.

**Test results**: Not run yet.

### 2026-07-15 17:32 UTC: Package completion

**Agent/Contributor**: Codex

**Work completed**:

- Delivered all seven requested worker and frontend hardening behaviors.
- Added backend, StatusStream, fork-console, template, reload, and storage-safety regression coverage.
- Rebuilt generated assets and updated authoritative UI/controller documentation.
- Completed separate code, QA, and security review passes.

**Blockers encountered**:

- Repository-wide pytest collection is blocked by the unrelated in-progress WEPPpyo3 interchange refactor: `WAT_OPTIONAL_COLUMN_NAMES` is undefined.
- Changed-file broad-exception enforcement reports only unrelated interchange additions; `wepppy/rq/project_rq_fork.py` has delta zero.

**Next steps**:

- Deploy through a separately authorized wepp1 operator action.
- Observe completion latency, heartbeat clarity, and failure diagnostics for 14 days after deployment.

**Test results**: 10 focused worker tests passed; 3 template/generated-StatusStream tests passed; frontend lint passed; all 85 frontend suites and 629 tests passed; documentation lint and `git diff --check` passed.

## Watch List

- **Terminal-event ordering**: WebSocket signals must prompt status confirmation without becoming authoritative themselves.
- **Shared helper compatibility**: StatusStream batching must preserve public events and manual append behavior.
- **Operational observability**: Removing raw output must not remove actionable failure details.

## Communication Log

### 2026-07-15 17:15 UTC: Scope confirmation

**Participants**: WEPPpy requesting maintainer, Codex
**Question/Topic**: Whether to retain dual completion signals and implement frontend/backend hardening items 1-7.
**Outcome**: Keep dual signals, make `/jobstatus/<job_id>` authoritative, and execute the work as a dedicated package.
