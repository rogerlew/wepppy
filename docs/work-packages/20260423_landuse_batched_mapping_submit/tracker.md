# Tracker - Landuse Batched Mapping Submit

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 00:27 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-24 01:31 UTC  
**Next milestone**: Archived (ExecPlan moved to `prompts/completed/`).  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-24 00:27 UTC).
- [x] Authored active ExecPlan at `prompts/active/landuse_batched_mapping_submit_execplan.md` (2026-04-24 00:27 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog (2026-04-24 00:27 UTC).
- [x] Authored execution prompt at `prompts/active/execute_landuse_batched_mapping_submit_prompt.md` (2026-04-24 00:31 UTC).
- [x] Defined canonical mapping batch contract + limits + compatibility semantics in ExecPlan and implementation (2026-04-24 00:45 UTC).
- [x] Implemented staged mapping-submit UX in `landuse.htm` and `landuse.js` (2026-04-24 00:48 UTC).
- [x] Implemented rq-engine batch enqueue path without `depends_on` chaining (2026-04-24 00:49 UTC).
- [x] Implemented RQ batch worker under one lock window with deterministic apply semantics and one completion trigger (2026-04-24 00:51 UTC).
- [x] Updated targeted JS/microservice/RQ tests for staged/batch semantics (2026-04-24 00:52 UTC).
- [x] Updated RQ dependency graph artifacts after queue wiring change (`job-dependencies-catalog.md`, `job-dependency-graph.static.json`) (2026-04-24 00:58 UTC).
- [x] Attempted live job-tree validation via `wepppy.rq.job_info`; no queued default jobs were available in dev stack (`default_queue_jobs=0`) (2026-04-24 00:59 UTC).
- [x] Manual UX smoke validated staged-submit flow end-to-end (`greenlight`; `job_id=3082d0f1-acd4-41e0-b897-abda94b31c1f`) (2026-04-24 01:12 UTC).
- [x] Ran required validations and docs lint (2026-04-24 00:54 UTC).
- [x] Archived ExecPlan to `prompts/completed/landuse_batched_mapping_submit_execplan.md` (2026-04-24 00:54 UTC).
- [x] Dispatched code + QA reviews and dispositioned findings (route `None` validation, lock-gate stale skip, readonly/inflight UX guardrails, stub parity) with refreshed validation evidence (2026-04-24 01:31 UTC).

## Timeline

- **2026-04-24 00:27 UTC** - Package initialized and scoped from landuse mapping UX/queue contention issue.
- **2026-04-24 00:27 UTC** - Active ExecPlan authored for implementation handoff.
- **2026-04-24 00:31 UTC** - Execution prompt authored for direct agent handoff.
- **2026-04-24 00:45 UTC** - Canonical batch contract, duplicate/chained semantics, and compatibility decisions finalized.
- **2026-04-24 00:52 UTC** - Code + tests completed across template/controller/rq-engine/RQ worker paths.
- **2026-04-24 00:54 UTC** - Required validations passed; package and tracker closure updates completed.
- **2026-04-24 00:58 UTC** - `wctl check-rq-graph` enforced; dependency graph artifacts regenerated and validated clean.
- **2026-04-24 00:59 UTC** - Live job-tree validation attempted in container; no runnable queue sample existed (`default_queue_jobs=0`).
- **2026-04-24 01:12 UTC** - Manual UX staged-submit validation reported as greenlight with job `3082d0f1-acd4-41e0-b897-abda94b31c1f`.
- **2026-04-24 01:31 UTC** - Code/QA review findings dispositioned; lock-gate stale completion bug fixed and targeted suites re-run clean.

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

### 2026-04-24 00:45 UTC: Canonical batch payload shape and limits
**Context**: Mapping submit now supports one or many staged edits with one request.

**Options considered**:
1. Keep only legacy top-level `{dom,newdom}`.
2. Add list-based canonical payload and keep legacy as compatibility input.

**Decision**: Option 2.

**Impact**: Canonical payload is `{"mappings":[{"dom":"...","newdom":"..."}, ...]}` with max 500 edits; response includes `job_id` + `mapping_count`; legacy top-level `dom/newdom` is still accepted.

### 2026-04-24 00:45 UTC: Duplicate/chained edit semantics
**Context**: Batch payloads can contain repeated source domains and cross-domain chains.

**Options considered**:
1. Reject duplicates/chains.
2. Last-write-wins per source `dom`, then execute deterministically.

**Decision**: Option 2.

**Impact**: Duplicate source-dom entries collapse to last-write-wins; normalized edits execute in first-seen `dom` order, producing deterministic chained remap outcomes.

### 2026-04-24 00:45 UTC: All-or-nothing apply semantics
**Context**: Batch errors should not leave partially applied mapping state.

**Options considered**:
1. Partial apply with per-row errors.
2. All-or-nothing validation and mutation semantics.

**Decision**: Option 2.

**Impact**: Route validates payload before enqueue; worker validates all source doms before mutation; unknown doms abort before any mutation; in-memory mapping snapshots are restored if downstream build fails.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Ambiguous batch semantics for duplicate/chained mappings | High | Medium | Deterministic ordering + dedupe semantics implemented and tested | Closed |
| UX confusion about staged vs applied state | Medium | Medium | Added staged count/status text + explicit submit button state in report | Mitigated |
| Regression in status-stream completion handling | Medium | Medium | Completion trigger contract preserved and controller tests updated | Mitigated |
| Backend partial-apply behavior on invalid rows | High | Low | Pre-mutation validation + rollback snapshot strategy + regression tests | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted unit/integration tests pass for changed files.
- [x] No new broad exception swallowing introduced.
- [x] Queue contract remains explicit and observable.

### Security
- [x] Security triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required.
- [x] Input validation for batch payload documented and tested.

### Documentation
- [x] Work-package scaffolded.
- [x] Active ExecPlan authored.
- [x] Mapping API contract docs updated.
- [x] Closure notes completed.

### Testing
- [x] Controller JS tests updated for staged + submit flow.
- [x] rq-engine route tests updated for batch payload contract and failures.
- [x] RQ mutation-guard tests updated for batch worker behavior.
- [x] Manual smoke test verifies single + Multi-OFE staged-submit UX.

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

### 2026-04-24 00:54 UTC: Implementation + validation closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented staged-submit mapping UX in:
  - `wepppy/weppcloud/templates/reports/landuse.htm`
  - `wepppy/weppcloud/controllers_js/landuse.js`
- Implemented canonical batch route contract in:
  - `wepppy/microservices/rq_engine/landuse_routes.py`
- Implemented deterministic batch worker semantics in:
  - `wepppy/rq/project_rq.py`
- Updated tests:
  - `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/rq/test_project_rq_mutation_guards.py`

**Blockers encountered**:
- None.

**Next steps**:
1. Optional: manual browser smoke for staged-submit UX in a live run.
2. Optional: follow-up package for staged coverage override batching.

**Test results**:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` (`17 passed`)
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` (`20 passed`)
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` (`18 passed`)
- `wctl doc-lint --path docs/work-packages/20260423_landuse_batched_mapping_submit` (`4 files validated, 0 errors`)
- `wctl check-rq-graph` (`RQ dependency graph artifacts are up to date`)
- `wctl exec weppcloud python - <<'PY' ... Queue(...).job_ids ... PY` (`default_queue_jobs=0`; no live tree sample to inspect)
- Manual UX validation (user-reported): `greenlight`, `job_id=3082d0f1-acd4-41e0-b897-abda94b31c1f`

### 2026-04-24 01:12 UTC: Manual UX greenlight
**Agent/Contributor**: User

**Work completed**:
- Manual end-to-end UX validation of staged mapping submit completed successfully.
- Captured proof reference: `job_id=3082d0f1-acd4-41e0-b897-abda94b31c1f`.

**Blockers encountered**:
- None reported.

**Next steps**:
1. None required for this package.

**Test results**:
- Manual UX smoke: greenlight.

### 2026-04-24 01:31 UTC: Post-review hardening + disposition
**Agent/Contributor**: Codex

**Work completed**:
- Dispatched code review + QA review and dispositioned findings in implementation/tests/docs.
- Added route regression coverage for explicit `null` mapping keys.
- Added RQ mutation-guard coverage for lock-gate stale skip, rollback-on-build-failure, and legacy three-arg worker invocation.
- Added controller regression coverage for readonly staged-submit disable behavior and inflight staging race prevention.
- Fixed lock-gate stale path so it no longer publishes completion trigger when skipped.
- Updated `wepppy/rq/project_rq.pyi` for runtime signature/constants parity.
- Regenerated RQ dependency graph artifacts after final queue-path changes.

**Blockers encountered**:
- One regression found during disposition: lock-gate stale jobs were still emitting completion trigger; fixed before final validation.

**Next steps**:
1. None required for this package.

**Test results**:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` (`19 passed`)
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` (`23 passed`)
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` (`20 passed`)
- `wctl doc-lint --path docs/work-packages/20260423_landuse_batched_mapping_submit` (`4 files validated, 0 errors`)
- `wctl check-rq-graph` (`RQ dependency graph artifacts are up to date`)

## Communication Log

### 2026-04-24 00:27 UTC: Package request
**Participants**: User, Codex  
**Question/Topic**: Create a work package for staged/batched landuse mapping submit UX and queue simplification.  
**Outcome**: Package scaffolded with active ExecPlan and backlog entry.

### 2026-04-24 01:12 UTC: Manual UX confirmation
**Participants**: User, Codex  
**Question/Topic**: Manual staged-submit validation result.  
**Outcome**: User confirmed greenlight with job `3082d0f1-acd4-41e0-b897-abda94b31c1f`.

### 2026-04-24 01:31 UTC: Review dispatch + disposition request
**Participants**: User, Codex  
**Question/Topic**: Dispatch code and QA reviews, then disposition findings.  
**Outcome**: Findings were triaged, fixed in code/tests/docs, and re-validated.
