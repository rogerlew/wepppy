# Tracker - Landuse Batched Mapping Submit

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 00:27 UTC  
**Current phase**: Discovery  
**Last updated**: 2026-04-24 00:31 UTC  
**Next milestone**: Finalize batch API semantics and begin controller + route implementation.  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Define canonical request payload and server-side validation rules for batch mapping submit.
- [ ] Implement staged-edit UX in `landuse.js` and `reports/landuse.htm`.
- [ ] Implement batch enqueue route in `landuse_routes.py` without mapping `depends_on`.
- [ ] Implement batch mapping worker behavior in `project_rq.py` under one lock window.
- [ ] Update tests (JS, microservice, RQ) for batch semantics and failure cases.
- [ ] Update user/developer documentation for new mapping submit contract.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-24 00:27 UTC).
- [x] Authored active ExecPlan at `prompts/active/landuse_batched_mapping_submit_execplan.md` (2026-04-24 00:27 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-04-24 00:27 UTC).
- [x] Authored execution prompt at `prompts/active/execute_landuse_batched_mapping_submit_prompt.md` (2026-04-24 00:31 UTC).

## Timeline

- **2026-04-24 00:27 UTC** - Package initialized and scoped from landuse mapping UX/queue contention issue.
- **2026-04-24 00:27 UTC** - Active ExecPlan authored for implementation handoff.
- **2026-04-24 00:31 UTC** - Execution prompt authored for direct agent handoff.

## Decisions Log

### 2026-04-24 00:27 UTC: Use explicit staged-submit UX for both single and Multi-OFE mapping
**Context**: Current immediate-submit model posts one mapping request per select change and performs poorly under repeated edits.

**Options considered**:
1. Keep immediate-submit and harden dependency semantics.
2. Keep immediate-submit and debounce requests.
3. Move to staged edits with explicit submit and batch processing.

**Decision**: Option 3.

**Impact**: Lower queue fan-out and lock contention, with one visible submit action per edit session.

### 2026-04-24 00:27 UTC: Remove mapping `depends_on` chaining in enqueue path
**Context**: Deferred jobs can remain stranded when chained predecessor jobs fail.

**Options considered**:
1. Keep chaining and add `allow_failure`/status filters.
2. Remove chaining and enforce one-submit/one-job semantics.

**Decision**: Option 2.

**Impact**: Eliminates the observed deferred-blocked-by-failed-predecessor failure mode for this path.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Ambiguous batch semantics for duplicate/chained mappings | High | Medium | Define deterministic ordering + dedupe semantics before coding | Open |
| UX confusion about staged vs applied state | Medium | Medium | Add dirty-state indicators + clear submit/result messaging | Open |
| Regression in status-stream completion handling | Medium | Medium | Keep completion event contract explicit and add regression tests | Open |
| Backend partial-apply behavior on invalid rows | High | Low | Use explicit all-or-nothing validation contract and tests | Open |

## Verification Checklist

### Code Quality
- [ ] Targeted unit/integration tests pass for changed files.
- [ ] No new broad exception swallowing introduced.
- [ ] Queue contract remains explicit and observable.

### Security
- [x] Security triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required.
- [ ] Input validation for batch payload documented and tested.

### Documentation
- [x] Work-package scaffolded.
- [x] Active ExecPlan authored.
- [ ] Mapping API contract docs updated.
- [ ] Closure notes completed.

### Testing
- [ ] Controller JS tests updated for staged + submit flow.
- [ ] rq-engine route tests updated for batch payload contract and failures.
- [ ] RQ mutation-guard tests updated for batch worker behavior.
- [ ] Manual smoke test verifies single + Multi-OFE staged-submit UX.

### Deployment
- [ ] Validate in local docker-compose.dev stack.
- [ ] Capture rollback path (restore immediate-submit behavior) if regressions appear.

## Progress Notes

### 2026-04-24 00:27 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and authored `package.md` with scoped objectives.
- Authored active ExecPlan for implementation sequencing.
- Added package to project-level backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Lock batch request/response semantics in route and ExecPlan.
2. Implement controller/template staged submit UX.
3. Implement backend batch worker path and remove mapping dependency chaining.

**Test results**:
- N/A (planning/docs only).

### 2026-04-24 00:31 UTC: Execution prompt added
**Agent/Contributor**: Codex

**Work completed**:
- Added handoff-ready execution prompt:
  - `docs/work-packages/20260423_landuse_batched_mapping_submit/prompts/active/execute_landuse_batched_mapping_submit_prompt.md`

**Blockers encountered**:
- None.

**Next steps**:
1. Use the new execute prompt to run the package end-to-end.

**Test results**:
- N/A (docs update only).

## Communication Log

### 2026-04-24 00:27 UTC: Package request
**Participants**: User, Codex  
**Question/Topic**: Create a work package for staged/batched landuse mapping submit UX and queue simplification.  
**Outcome**: Package scaffolded with active ExecPlan and backlog entry.
