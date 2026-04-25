# Tracker - NoDb Atomicity, RQ Graph Baseline, and Observability Follow-Ups

> Living document tracking progress, decisions, risks, and verification for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-25 23:06 UTC  
**Current phase**: Ready for execution  
**Last updated**: 2026-04-25 23:09 UTC  
**Next milestone**: Milestone 1 design + implementation proposal for scoped cross-controller atomicity.  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Implement scoped cross-controller failure-atomicity strategy for grouped rq-engine mutation flows.
- [ ] Milestone 2: Resolve `wctl check-rq-graph` drift baseline and document root cause/disposition.
- [ ] Milestone 3: Harden + validate post-enqueue WEPP job-hint persistence fault paths (lock-contention and non-`RuntimeError` behavior).
- [ ] Milestone 4: Add lock/dump-efficiency observability guard for scoped rq-engine mutation paths.
- [ ] Milestone 5: Complete test maintainability cleanup for scoped rq-engine suites (shared helpers + less brittle assertions).
- [ ] Milestone 6: Execute package-wide validation and close docs/plan/tracker artifacts.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, prompt directories, active ExecPlan placeholder) (2026-04-25 23:06 UTC).
- [x] Authored active ExecPlan and synced package into `PROJECT_TRACKER.md` Backlog (2026-04-25 23:09 UTC).
- [x] Ran docs lint for package docs + `PROJECT_TRACKER.md` (2026-04-25 23:09 UTC).

## Timeline

- **2026-04-25 23:06 UTC** - Package created as follow-up to `20260425_nodb_lock_dump_efficiency_refactor` to implement atomicity, queue-graph baseline cleanup, failure-path hardening, observability guards, and test maintainability cleanup.
- **2026-04-25 23:09 UTC** - Package planning artifacts completed (active ExecPlan + tracker + project tracker backlog entry) and docs lint passed (`0 errors`, `0 warnings`).

## Decisions Log

### 2026-04-25 23:06 UTC: Create a new follow-up package instead of reopening the closed package
**Context**: Prior package is already closed with complete closure evidence; new work was identified as follow-up scope.

**Options considered**:
1. Reopen/extend `20260425_nodb_lock_dump_efficiency_refactor`.
2. Create a new package with explicit dependency on the closed package.

**Decision**: Option 2.

**Impact**: Preserves clean closure history for the completed package and keeps new implementation/review evidence isolated and auditable.

---

### 2026-04-25 23:06 UTC: Execute follow-up items in risk-first order
**Context**: Requested follow-ups include transaction semantics, boundary hardening, baseline hygiene, guardrails, and maintainability work.

**Options considered**:
1. Start with low-risk maintainability cleanup.
2. Start with atomicity and boundary correctness first, then observability and maintainability.

**Decision**: Option 2.

**Impact**: Reduces correctness/regression risk early and lets guardrails/cleanup reflect the final behavior contract.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Atomicity implementation introduces response-contract drift | High | Medium | Keep contract-first design notes + targeted route regressions before/after change | Open |
| Queue-graph drift fix accidentally hides real queue wiring issues | Medium | Medium | Investigate root cause before artifact regeneration; validate with `wctl check-rq-graph` and focused wiring inspection | Open |
| Broad exception handling weakens debugging by swallowing unexpected errors | Medium | Medium | Define explicit exception boundary contract and preserve logging/assertions for fail-open behavior | Open |
| Observability guard becomes brittle/noisy | Low | Medium | Keep guard narrow to scoped paths; validate utility in package regression runs | Open |
| Test helper extraction causes accidental behavior loss in route tests | Low | Medium | Refactor in small steps with targeted suite runs at each step | Open |

## Hardening Signal Log (Required for incident/remediation packages)

- **Applicability**: Preventive hardening + post-close callus-softening follow-up.
- **Baseline health signals**:
  - prior package left low residual risks for cross-controller atomicity and hint-persist boundary behavior.
  - `wctl check-rq-graph` currently reports drift.
- **Post-change health signals**: to be captured during implementation.
- **Danger signals observed**: none yet.
- **Temporary callus register**: none yet.
- **Softening experiments**: to be captured if exception-boundary behavior changes.

## Verification Checklist

### Code Quality
- [ ] Targeted rq-engine and NoDb suites pass for each milestone.
- [ ] `wctl check-rq-graph` is green after queue-graph baseline fix.
- [ ] No broad regressions in touched modules.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required.
- [ ] Residual security-sensitive changes documented at closure.

### Documentation
- [ ] Package docs remain current during execution.
- [ ] `PROJECT_TRACKER.md` status remains synchronized.
- [ ] ExecPlan moved from `prompts/active/` to `prompts/completed/` at closure.

### Testing
- [ ] Atomicity/failure-path regressions added and passing.
- [ ] Observability guard validation added and passing.
- [ ] Maintainability cleanup keeps route/helper behavior assertions intact.

### Deployment
- [ ] No deployment change required (or explicitly documented if needed).

## Progress Notes

### 2026-04-25 23:06 UTC: Package creation and planning initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created follow-up package scaffold and wrote initial `package.md` scope for requested items `1, 2, 3, 4, 6`.
- Initialized tracker with ordered milestones and initial risk register.
- Prepared to author active ExecPlan and update root `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Author active ExecPlan with milestone-level implementation/validation plan.
- Add package entry to `PROJECT_TRACKER.md` Backlog.
- Run doc lint on newly created package docs.

**Test results**: N/A (docs-only setup).

### 2026-04-25 23:09 UTC: Package preparation complete
**Agent/Contributor**: Codex

**Work completed**:
- Authored active ExecPlan with milestone order for requested items `1,2,3,4,6`.
- Added package entry under `PROJECT_TRACKER.md` Backlog with dependencies and next steps.
- Linted docs:
  - `package.md`
  - `tracker.md`
  - active ExecPlan
  - `PROJECT_TRACKER.md`

**Blockers encountered**:
- None.

**Next steps**:
- Begin Milestone 1 execution (cross-controller atomicity strategy and implementation).

**Test results**:
- `wctl doc-lint ...` -> `4 files validated, 0 errors, 0 warnings`.

## Communication Log

### 2026-04-25 23:06 UTC: Follow-up package request
**Participants**: User, Codex  
**Question/Topic**: Prepare package for follow-ups 1, 2, 3, 4, 6 from prior closure recommendations.  
**Outcome**: New follow-up package created with explicit scope and milestone plan initialized.
