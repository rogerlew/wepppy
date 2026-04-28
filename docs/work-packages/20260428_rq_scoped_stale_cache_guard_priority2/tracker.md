# Tracker - RQ Scoped Stale NoDb Cache Guard Priority 2

> Living document for Priority 2 scoped NoDb mutation cache-guard follow-ups.

## Quick Status

**Timezone**: UTC  
**Prepared**: 2026-04-28 17:07 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-28 17:28 UTC  
**Next milestone**: Closed; monitor new RQ mutate paths for standard conformance  
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

- [x] Created Priority 2 work-package scaffold and active ExecPlan (2026-04-28 17:07 UTC).
- [x] Linked package to the canonical scoped NoDb mutation cache-guard standard (2026-04-28 17:07 UTC).
- [x] Added package to `PROJECT_TRACKER.md` Backlog for visibility (2026-04-28 17:07 UTC).
- [x] Audited all Priority 2 candidate paths and confirmed implementation viability (2026-04-28 17:12 UTC).
- [x] Implemented scoped guards in `wepp_rq.py`, `swat_rq.py`, `omni_rq.py`, `path_ce_rq.py`, `roads_rq.py`, `geneva_rq.py`, and `project_rq_fork.py` (2026-04-28 17:18 UTC).
- [x] Added targeted regression assertions for scope and guard-before-hydration ordering in all touched module suites (2026-04-28 17:19 UTC).
- [x] Ran focused pytest suites, docs lint, and `git diff --check` with passing results (2026-04-28 17:28 UTC).
- [x] Updated lifecycle docs and moved ExecPlan to `prompts/completed/` (2026-04-28 17:28 UTC).

## Timeline

- **2026-04-28 16:42 UTC** - Previous scoped stale-cache guard follow-up package closed with Priority 2 module families split/deferred.
- **2026-04-28 17:07 UTC** - Priority 2 package prepared with candidate matrix, execution prompt, active ExecPlan, and tracker entry.
- **2026-04-28 17:12 UTC** - Candidate audit completed across all seven modules; no split/defer required.
- **2026-04-28 17:18 UTC** - Scoped guard implementation completed for all listed Priority 2 candidates.
- **2026-04-28 17:19 UTC** - Targeted regression coverage completed for all touched modules.
- **2026-04-28 17:28 UTC** - Validation gates and package lifecycle closure completed.

## Decisions Log

### 2026-04-28 17:07 UTC: Prepare one Priority 2 umbrella package with split authority

**Context**: The previous package deferred WEPP, SWAT, Omni, PATH CE, Roads,
Geneva, and fork-undisturbify paths because each combines NoDb mutation with
module-specific orchestration behavior.

**Decision**: Scope one umbrella Priority 2 package that requires per-module
audit and allows explicit split/defer disposition for any module whose fixture
or behavior surface is too large for a safe single-pass implementation.

**Impact**: Keeps the backlog visible while preserving narrow, evidence-backed
guard adoption.

### 2026-04-28 17:12 UTC: Implement all listed candidates in this package

**Context**: Module-level audit found each candidate had a clear mutable
hydration boundary and existing tests that could absorb scoped guard assertions.

**Decision**: Implement all listed Priority 2 candidates now; no split/defer
package required.

**Impact**: Completes Priority 2 conformance in one pass with focused evidence.

### 2026-04-28 17:14 UTC: Fork guard scope must key off `new_runid`

**Context**: `prepare_fork_run(..., undisturbify=True)` mutates copied NoDb
state in `new_wd`; guarding with source `runid` would clear the wrong cache key.

**Decision**: Add an injected `clear_nodb_cache_fn` collaborator and call it
with `new_runid` for `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, and
`soils.nodb` before each mutable hydration.

**Impact**: Preserves existing fork flow while enforcing correct scoped keys.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| One execution pass touches too many unrelated orchestration paths | Medium | Medium | Module-by-module implementation with focused tests | Mitigated |
| Guard placement changes lock or status behavior | Medium | Medium | Added ordering assertions and preserved existing status/lock tests | Mitigated |
| Omni/PATH CE multi-scope behavior gets over-cleared | Medium | Medium | Scoped to `path_ce.nodb` and `omni.nodb` only | Mitigated |
| Fork path clears source-run cache instead of new-run cache | High | Low | Explicit `new_runid` cache-keyed calls and fork regression test | Mitigated |

## Verification Checklist

### Code Quality

- [x] Focused pytest command for every touched RQ module.
- [x] `git diff --check`.
- [x] `wctl check-rq-graph` if queue wiring changes (`N/A`; no queue wiring changes).

### Documentation

- [x] Package docs updated with implementation/disposition evidence.
- [x] Active ExecPlan living sections updated during execution.
- [x] `PROJECT_TRACKER.md` updated at package closure.
- [x] `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2 --path PROJECT_TRACKER.md`.

### Testing

- [x] Tests assert exact `pup_relpath` scope values for implemented guards.
- [x] Tests assert cache clear happens after precondition rejection paths where applicable.
- [x] Tests assert cache clear happens before mutable controller hydration.
- [x] Tests preserve status, timestamp, enqueue, lock, clone, deletion, and
      autocommit behavior relevant to touched modules.

## Progress Notes

### 2026-04-28 17:07 UTC: Package preparation

**Agent/Contributor**: Codex

**Work completed**:
- Prepared the Priority 2 work package from the deferred candidate list in the
  previous scoped stale-cache guard package.
- Captured candidate modules, likely guard scopes, validation focus, constraints,
  and success criteria.
- Created an active ExecPlan and execution prompt for a future end-to-end run.
- Added the package to `PROJECT_TRACKER.md` Backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Start execution by moving this package to `PROJECT_TRACKER.md` In Progress.
2. Audit candidate modules against the canonical standard.
3. Implement only confirmed, testable guards or record split/defer disposition.

**Validation results**:
- Pending docs lint and diff checks for package preparation.

### 2026-04-28 17:28 UTC: Execution and closure

**Agent/Contributor**: Codex

**Work completed**:
- Added scoped cache guards to all listed Priority 2 mutate paths:
  - `wepppy/rq/wepp_rq.py`
  - `wepppy/rq/swat_rq.py`
  - `wepppy/rq/omni_rq.py`
  - `wepppy/rq/path_ce_rq.py`
  - `wepppy/rq/roads_rq.py`
  - `wepppy/rq/geneva_rq.py`
  - `wepppy/rq/project_rq_fork.py`
- Added targeted regression assertions for scope and ordering in:
  - `tests/rq/test_bootstrap_enable_rq.py`
  - `tests/rq/test_bootstrap_autocommit_rq.py`
  - `tests/rq/test_omni_rq.py`
  - `tests/rq/test_path_ce_rq.py`
  - `tests/rq/test_roads_rq.py`
  - `tests/rq/test_geneva_rq.py`
  - `tests/rq/test_project_rq_fork.py`
- Implemented fork-specific `new_runid`-scoped cache clears through
  `clear_nodb_cache_fn` injection in `prepare_fork_run(...)`.
- Updated lifecycle docs and moved ExecPlan to `prompts/completed/`.

**Blockers encountered**:
- None.

**Validation results**:
- `wctl run-pytest tests/rq/test_bootstrap_enable_rq.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1` -> `21 passed, 6 warnings`.
- `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> `15 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_path_ce_rq.py --maxfail=1` -> `3 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` -> `4 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> `5 passed, 2 warnings`.
- `wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1` -> `13 passed, 2 warnings`.
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2 --path PROJECT_TRACKER.md` -> passed.
- `git diff --check` -> passed.
