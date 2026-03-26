# Tracker – Disturbed Lookup Hardening and Preservation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-25  
**Current phase**: Closed  
**Last updated**: 2026-03-26  
**Next milestone**: None (package complete)

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with `package.md`, `tracker.md`, and active prompts directory (2026-03-25).
- [x] Active ExecPlan authored for end-to-end execution (2026-03-25).
- [x] Disturbed lookup writer hardened with validation, duplicate-key guard, and partial-table rejection semantics.
- [x] Legacy schema upgrade/readability hardening implemented for `disturbed_class`/`texid` rows.
- [x] Extended lookup generation redirected to `disturbed_land_soil_lookup_extended.csv` (non-clobber).
- [x] Editor CSV config migrated to dynamic header-driven columns.
- [x] Route payload validation tightened with explicit 400 responses for malformed payloads.
- [x] Subagent code review + QA review completed and findings artifacts recorded.
- [x] Targeted validation suites and stub checks passed.
- [x] Package reopened for stale-page polling/lockout + double-submit safeguards (2026-03-26).
- [x] Added lookup snapshot API (`csv + sha`) and strict optimistic concurrency precondition enforcement (`if_match_sha256`) for save writes.
- [x] Added editor stale lockout controls (`Load Current Table` / `Refresh Page`) and in-flight save editing lock.
- [x] Added observability logs for blocked/committed disturbed lookup writes.
- [x] Reopen-cycle code review + QA review artifacts completed with spawned `reviewer` + `qa_reviewer` subagents.
- [x] Reopen-cycle full validation sweep passed, including `wctl run-pytest tests --maxfail=1`.

## Timeline

- **2026-03-25** – Package created and implementation started.
- **2026-03-25** – Implementation completed, review findings resolved, validations passed, package closed.
- **2026-03-26** – Package reopened to add stale-page UI safeguards and double-submit prevention requested by user.
- **2026-03-26** – Reopen implementation, review artifacts, and full validation completed; package re-closed.

## Decisions Log

### 2026-03-25: Keep `?pup` compatibility, do not remove legacy scope behavior
**Context**: User requested hardening while explicitly retaining `?pup` behavior.

**Options considered**:
1. Remove `?pup` entirely and force composite runids.
2. Keep `?pup` compatibility and harden disturbed editor scope consistency.

**Decision**: Option 2.

**Impact**: Disturbed lookup hardening remains backward compatible with existing scoped run links.

---

### 2026-03-26: Enforce optimistic concurrency preconditions and add atomic lookup snapshot loading
**Context**: Users can leave stale editor pages open; stale saves and rapid repeated clicks must not overwrite newer lookup data.

**Options considered**:
1. Best-effort stale polling only, while allowing saves without precondition hash.
2. Require precondition hash for writes, add stale polling/lockout UX, and provide explicit reload/refresh recovery actions.

**Decision**: Option 2.

**Impact**: Save writes fail closed on stale or missing preconditions; UI guides users into safe reload flow instead of silently overwriting newer data.

---

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Save-path changes regress disturbed editor behavior | High | Medium | Added focused route/editor regressions including real writer-path error tests | Closed |
| Schema-upgrade changes unexpectedly alter legacy lookup rows | Medium | Medium | Added additive upgrade/read fallback + regression coverage for legacy key rows | Closed |
| Scope fix touches route URL assumptions | Medium | Low | Kept CSV download on existing `download.download_with_subpath` proxy-safe path | Closed |
| Stale editor page overwrites newer disturbed lookup content | High | High | Enforced `if_match_sha256` precondition + stale mismatch `409` contract + stale polling lockout controls | Closed |
| Repeated save clicks submit duplicate in-flight writes | Medium | Medium | Added in-flight save guard and temporary table editing lock during save | Closed |

## Verification Checklist

### Code Quality
- [x] Targeted disturbed route/module tests passing.
- [x] No medium/high review findings left unresolved.

### Documentation
- [x] ExecPlan `Progress`, `Decision Log`, and `Outcomes & Retrospective` updated.
- [x] Tracker timeline/notes updated with completion details.

### Testing
- [x] Regression tests for malformed save rejection and persistence retention.
- [x] Regression test for extended export non-clobber behavior.
- [x] Regression test for scope-safe editor URL behavior.
- [x] Regression tests for missing `if_match_sha256`, stale hash mismatch, and unavailable lookup hash handling.
- [x] Regression test for lookup snapshot endpoint payload contract.
- [x] Full suite sanity pass completed after reopen-cycle safeguards.

## Progress Notes

### 2026-03-25: Package initialization and execution kickoff
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold and active ExecPlan.
- Registered initial goals, scope, and risk posture.

**Blockers encountered**:
- None.

**Next steps**:
- Implement hardening code changes and tests.
- Run subagent code + QA reviews and resolve findings.

**Test results**: Pending

### 2026-03-25: Implementation + review + validation closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented disturbed lookup persistence hardening across NoDb writer/upgrade paths and disturbed route/editor paths.
- Resolved subagent `reviewer` and `qa_reviewer` medium/high findings; recorded artifacts:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`
- Added regression coverage in:
  - `tests/nodb/mods/test_disturbed_lookup_persistence.py`
  - `tests/weppcloud/routes/test_disturbed_bp.py`
- Completed validation and docs lint passes.

**Blockers encountered**:
- None.

**Next steps**:
- None. Package closed.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl doc-lint --path PROJECT_TRACKER.md`
- `wctl doc-lint --path docs/work-packages/20260325_disturbed_lookup_hardening/package.md`
- `wctl doc-lint --path docs/work-packages/20260325_disturbed_lookup_hardening/tracker.md`
- `wctl doc-lint --path docs/work-packages/20260325_disturbed_lookup_hardening/prompts/completed/disturbed_lookup_hardening_execplan.md`

### 2026-03-26: Reopen cycle for stale-page + double-submit UI safeguards
**Agent/Contributor**: Codex

**Work completed**:
- Added route-level lookup snapshot endpoint and strict optimistic-concurrency save precondition enforcement in disturbed route.
- Updated disturbed editor template/JS with stale polling lockout controls, current-data reload action, refresh action, and in-flight save editing lock.
- Added explicit write-path observability logs for missing precondition, stale mismatch, hash-unavailable, post-save hash-unavailable, and committed writes.
- Expanded disturbed route regression coverage for new endpoint/contracts and optimistic-concurrency failure paths.
- Completed subagent reviews and recorded artifacts in:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`

**Blockers encountered**:
- None.

**Next steps**:
- None. Reopen scope completed and package re-closed.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-pytest tests --maxfail=1`

## Watch List

- Disturbed lookup schema upgrade remains additive and preserves user-modified values.
- Disturbed editor save/read scope remains consistent with `?pup` compatibility.
- Stale polling/lockout UX currently relies on route/template-level regressions; browser E2E polling cadence tests remain a follow-up opportunity.

## Communication Log

### 2026-03-25: User request confirmation
**Participants**: User, Codex  
**Question/Topic**: Create and complete a work-package end-to-end with subagent code and QA reviews.  
**Outcome**: Work-package completed end-to-end with code + QA subagent reviews, artifacts, and passing targeted validations.

### 2026-03-26: User reopen request for stale-page and double-submit safeguards
**Participants**: User, Codex  
**Question/Topic**: Reopen package and implement stale-page lockout/recovery UX plus double-submission prevention in disturbed lookup editor.  
**Outcome**: Reopen scope completed with route/UI/test hardening, observability updates, review artifacts, and full validation pass.
