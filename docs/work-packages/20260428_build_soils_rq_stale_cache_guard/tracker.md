# Tracker - `build_soils_rq` Stale NoDb Cache Guard

> Living document tracking progress, decisions, risks, and validation for adding a scoped stale-cache guard to the soils build RQ path.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-28 15:30 UTC  
**Current phase**: Closed  
**Last updated**: 2026-04-28 15:58 UTC  
**Next milestone**: None; package closed  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- None.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active/`) (2026-04-28 15:30 UTC).
- [x] Authored active ExecPlan for implementation and validation flow (2026-04-28 15:30 UTC).
- [x] Added package to `PROJECT_TRACKER.md` Backlog for visibility and handoff continuity (2026-04-28 15:30 UTC).
- [x] Ran scoped docs lint for package + tracker entry (`4 files validated, 0 errors, 0 warnings`) (2026-04-28 15:32 UTC).
- [x] Authored execution prompt at `prompts/active/execute_build_soils_rq_stale_cache_guard_prompt.md` (2026-04-28 15:33 UTC).
- [x] Implemented scoped `clear_nodb_file_cache(runid, pup_relpath="soils.nodb")` guard in `build_soils_rq` (2026-04-28 15:53 UTC).
- [x] Added regression coverage for guard ordering, scoped cache key, status/timestamp preservation, and archive-root rejection (2026-04-28 15:53 UTC).
- [x] Ran targeted RQ mutation guard pytest (`26 passed`) (2026-04-28 15:54 UTC).
- [x] Ran soils rq-engine route non-regression pytest (`3 passed`) (2026-04-28 15:55 UTC).
- [x] Ran package docs lint (`5 files validated, 0 errors, 0 warnings`) (2026-04-28 15:58 UTC).
- [x] Closed package lifecycle docs and archived ExecPlan under `prompts/completed/` (2026-04-28 15:58 UTC).

## Timeline

- **2026-04-28 15:30 UTC** - Package created from wepp1 incident analysis for `build_soils_rq` stale-cache failure signature.
- **2026-04-28 15:30 UTC** - Initial scope, risks, and success criteria recorded.
- **2026-04-28 15:30 UTC** - Active ExecPlan drafted and linked.
- **2026-04-28 15:32 UTC** - Scoped docs lint passed for package docs and `PROJECT_TRACKER.md`.
- **2026-04-28 15:33 UTC** - Execution prompt added and linked from package kickoff section.
- **2026-04-28 15:53 UTC** - Scoped cache guard and regression test implemented.
- **2026-04-28 15:54 UTC** - `tests/rq/test_project_rq_mutation_guards.py` passed with `26 passed`.
- **2026-04-28 15:55 UTC** - `tests/microservices/test_rq_engine_soils_routes.py` passed with `3 passed`.
- **2026-04-28 15:58 UTC** - Package docs lint passed and lifecycle docs closed.

## Decisions Log

### 2026-04-28 15:30 UTC: Apply a scoped guard in `build_soils_rq` instead of broader cache-system changes
**Context**: The confirmed failure occurred in the soils RQ build path with stale Redis cache signature state for `soils.nodb`.

**Options considered**:
1. Immediate broad cache architecture changes in `wepppy/nodb/base.py`.
2. Scoped `build_soils_rq` guard clearing `soils.nodb` cache before hydration/build.

**Decision**: Option 2.

**Impact**: Fast, low-blast-radius mitigation aligned with current mutation-guard patterns in `project_rq.py`.

---

### 2026-04-28 15:30 UTC: Keep scope narrow to one RQ path plus regression coverage
**Context**: Incident evidence points to one reproducible failing path and there is existing pressure to avoid speculative abstractions.

**Options considered**:
1. Expand to guard multiple RQ mutation jobs in the same change.
2. Fix the confirmed path first; defer broader rollout unless additional evidence appears.

**Decision**: Option 2.

**Impact**: Preserves change-scope discipline and keeps validation focused.

### 2026-04-28 15:53 UTC: Clear cache inside the existing soils lock callback
**Context**: `build_soils_rq` already wraps soils mutation with `_run_with_directory_root_lock(...)`, which rejects archive-backed roots before invoking the callback.

**Options considered**:
1. Clear `soils.nodb` cache before entering the directory-root lock.
2. Clear `soils.nodb` cache inside the locked callback immediately before `Soils.getInstance(wd).build()`.

**Decision**: Option 2.

**Impact**: The guard runs immediately before mutable soils hydration/build while preserving archive-root rejection ordering and the existing status/timestamp flow.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Guard added in wrong location/order and does not prevent stale hydration | High | Medium | Added explicit ordering assertions in targeted tests and reviewed callback flow | Mitigated |
| Guard unintentionally alters archive-root or job-status behavior | Medium | Low | Regression test asserts archive-root rejection before cache clear/hydration plus status/timestamp order on success path | Mitigated |
| Scoped fix masks broader systemic issue across other jobs | Medium | Medium | Track incident recurrence and open follow-up package only with evidence | Monitoring |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**: Known production failure signature in `build_soils_rq` with stale NoDb cache signature mismatch.
- **Post-change health signals**: Expected elimination of stale-cache failure signature on `build_soils_rq` path.
- **Danger signals observed**: None yet beyond the initiating failure.
- **Temporary callus register**: none.
- **Softening experiments**: none planned in this package.

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` (`26 passed`, 2026-04-28 15:54 UTC)
- [x] `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` (`3 passed`, 2026-04-28 15:55 UTC)
- [x] `git diff --check` (passed, 2026-04-28 15:58 UTC)

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security review artifact not required.
- [x] Residual risks documented at closure.

### Documentation
- [x] Initial package docs lint pass completed.
- [x] Package docs updated with closure evidence.
- [x] Active ExecPlan archived to `prompts/completed/` at closure.
- [x] `PROJECT_TRACKER.md` status updated at closure.
- [x] `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md` (`5 files validated, 0 errors, 0 warnings`, 2026-04-28 15:58 UTC)

### Testing
- [x] Regression coverage added for guard invocation path.
- [x] Existing archive-root rejection behavior remains passing.

### Deployment
- [x] No deployment changes required.

## Progress Notes

### 2026-04-28 15:30 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and authored initial scope/success criteria.
- Drafted active ExecPlan for implementation sequence and validation gates.
- Added package visibility entry in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement the scoped guard in `wepppy/rq/project_rq.py`.
2. Add targeted tests in `tests/rq/test_project_rq_mutation_guards.py`.
3. Run scoped pytest + docs lint + diff-check gates.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md` -> `4 files validated, 0 errors, 0 warnings`.

### 2026-04-28 15:33 UTC: Execution prompt authored
**Agent/Contributor**: Codex

**Work completed**:
- Added copy/paste execution prompt:
  - `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/prompts/active/execute_build_soils_rq_stale_cache_guard_prompt.md`
- Linked kickoff artifacts in `package.md` (`Kickoff Prompt` section).

**Blockers encountered**:
- None.

**Next steps**:
1. Run the execution prompt to implement the guard and tests.
2. Update tracker/package docs with validation evidence.
3. Close and archive plan artifacts when done.

**Test results**: Not run in this step (docs-only update).

### 2026-04-28 15:58 UTC: Implementation, validation, and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added the scoped `soils.nodb` cache clear inside the existing `build_soils_rq` soils directory-root lock callback.
- Added regression coverage proving cache clear happens before soils hydration/build and remains scoped to `soils.nodb`.
- Strengthened archive-root coverage so archive-backed soils roots reject before cache clear or soils hydration.
- Updated package lifecycle docs and moved the package from `Backlog` to `Done` in `PROJECT_TRACKER.md`.
- Prepared the active ExecPlan for archival under `prompts/completed/`.

**Blockers encountered**:
- None.

**Next steps**:
- None for this package.

**Test results**:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` -> `26 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md` -> `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` -> passed.
