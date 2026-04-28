# Tracker - RQ Scoped Stale NoDb Cache Guard Follow-Ups

> Living document tracking the rollout of scoped stale-cache guards across adjacent RQ mutation paths.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-28 16:01 UTC  
**Current phase**: Complete
**Last updated**: 2026-04-28 16:42 UTC
**Next milestone**: Closed; split Priority 2 module-family follow-ups when capacity is available
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Split Priority 2 module families into dedicated packages when scheduled.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Identified candidate RQ mutation call sites after closing the `build_soils_rq` guard package (2026-04-28 16:01 UTC).
- [x] Created follow-up package scaffold (`package.md`, `tracker.md`, `prompts/active/`) (2026-04-28 16:01 UTC).
- [x] Added package to `PROJECT_TRACKER.md` Backlog for visibility (2026-04-28 16:01 UTC).
- [x] Codified canonical contract in `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` and referenced it from package docs (2026-04-28 16:22 UTC).
- [x] Applied reviewer audit corrections to package candidate matrix (scope fixes, false-positive removals, missed-site additions) (2026-04-28 16:22 UTC).
- [x] Synced `PROJECT_TRACKER.md` candidate scope with the audited matrix and tightened standard wording for multi-scope clear semantics (2026-04-28 16:32 UTC).
- [x] Implemented Priority 0 and simple Priority 1 guards in `wepppy/rq/project_rq.py` (2026-04-28 16:42 UTC).
- [x] Added targeted regression coverage for guard scopes, ordering, archive rejection, and representative status/timestamp/enqueue preservation (2026-04-28 16:42 UTC).
- [x] Recorded split/defer disposition for Priority 2 module families in `package.md` (2026-04-28 16:42 UTC).
- [x] Ran required targeted pytest, docs lint, and `git diff --check` validation (2026-04-28 16:42 UTC).

## Timeline

- **2026-04-28 15:58 UTC** - `build_soils_rq` stale-cache guard package closed and pushed.
- **2026-04-28 16:01 UTC** - Adjacent `_rq` call-site scan completed; candidates grouped by priority.
- **2026-04-28 16:01 UTC** - Follow-up package and active ExecPlan drafted.
- **2026-04-28 16:22 UTC** - Canonical standard added and package matrix corrected from independent reviewer audit.
- **2026-04-28 16:32 UTC** - Backlog scope and standard wording tightened for execution clarity (`rhem` removed, multi-controller clear semantics explicit).
- **2026-04-28 16:42 UTC** - Priority 0 and simple Priority 1 `project_rq.py` guards implemented, tests expanded, Priority 2 families split/deferred, and validation passed.

## Decisions Log

### 2026-04-28 16:01 UTC: Prioritize direct top-level mutation paths first
**Context**: The completed soils fix proved the value of a scoped guard immediately before mutable hydration. The broad `_rq` scan found many possible getInstance call sites, including read-only and orchestration paths.

**Options considered**:
1. Guard every RQ `getInstance(...)` call.
2. Guard only confirmed hydrate-then-mutate paths and require audit/disposition for ambiguous module families.

**Decision**: Option 2.

**Impact**: Keeps behavior changes scoped and testable while preventing accidental cache churn on read-only paths.

### 2026-04-28 16:01 UTC: Preserve archive-root and lock-gate ordering
**Context**: The `build_soils_rq` fix placed the guard inside the existing directory-root lock callback, after archive-root checks and immediately before controller hydration.

**Decision**: Use the same ordering for root-scoped mutation paths: root/archive checks first, then scoped cache clear, then mutable controller hydration/build.

**Impact**: Existing archive-root rejection behavior remains observable and tests can assert cache clearing is not reached on rejected archive-backed roots.

### 2026-04-28 16:22 UTC: Classify this package as contract conformance, not hardening
**Context**: User direction requested formalizing scoped stale-cache guards as canonical write-path behavior under explicit conditions.

**Decision**: Adopt `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` as the governing contract for this package and align candidate selection to that standard.

**Impact**: The rollout is evaluated as standards conformance (required/defer/not-applicable classification), not as callus-style hardening.

### 2026-04-28 16:42 UTC: Implement `project_rq.py` Priority 1 paths, split Priority 2
**Context**: Priority 1 candidates in `wepppy/rq/project_rq.py` had clear mutable controller boundaries and could be covered in the existing mutation-guard suite. Priority 2 candidates span orchestration modules with queue pipelines, clone/deletion semantics, single-flight locks, or new-runid fork behavior.

**Decision**: Implement all Priority 0 and simple Priority 1 `project_rq.py` guards in this package; split/defer non-`project_rq.py` Priority 2 families to dedicated follow-ups.

**Impact**: This package closes the direct stale-cache risk shapes without broadening scope into untested orchestration behavior.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Guarding too broadly disrupts unrelated cached controllers | Medium | Medium | Use scoped `pup_relpath` only and add tests asserting exact scope | Mitigated |
| Guard inserted before archive-root rejection changes failure ordering | Medium | Low | Mirror soils guard test pattern on lock-root paths | Mitigated |
| Priority 2 orchestration paths become too large for one package | Medium | Medium | Require explicit split/defer disposition before implementation proceeds | Split/deferred |
| Missing a mutating mod path leaves stale-write recurrence possible | Medium | Medium | Keep candidate matrix current and add audit notes before closure | Residual follow-up |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` (`44 passed, 15 warnings`)
- [x] Additional targeted pytest suites for any non-`project_rq.py` module touched (`N/A`; no non-`project_rq.py` implementation files touched)
- [x] `git diff --check`

### Documentation
- [x] Package docs updated with implementation/disposition evidence.
- [x] `PROJECT_TRACKER.md` updated at package start and closure.
- [x] `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md`

### Testing
- [x] Regression coverage asserts exact `pup_relpath` values for guarded paths.
- [x] Regression coverage asserts cache clear happens after root/archive checks where applicable.
- [x] Existing status/timestamp/enqueue behavior remains covered or explicitly unchanged.

### Deployment
- [x] No deployment changes required.

## Progress Notes

### 2026-04-28 16:01 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Scanned `wepppy/rq/*` for `*_rq` functions that hydrate NoDb controllers and call mutating methods.
- Recorded Priority 0 direct project-prep mutation paths and Priority 1/2 audit candidates in `package.md`.
- Created package lifecycle docs and active execution prompt/ExecPlan.
- Added a Backlog entry in `PROJECT_TRACKER.md`.
- Codified canonical scoped-guard contract in `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.
- Updated `package.md` to reference the standard and corrected candidate rows per reviewer audit.
- Synchronized `PROJECT_TRACKER.md` scope to the audited matrix and clarified per-file multi-controller clear semantics in the standard.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement Priority 0 guards in `project_rq.py` with scoped cache clear calls.
2. Add tests mirroring the `build_soils_rq` ordering/scope assertions.
3. Audit Priority 1 mod call sites and decide whether to include them in this package or split.

**Test results**:
- Not run in this step; docs-only package setup.

### 2026-04-28 16:42 UTC: Implementation and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added scoped guards to Priority 0 project-prep paths in `wepppy/rq/project_rq.py`: SBS mod map initialization, DEM fetch, watershed metadata/channel/outlet/subcatchment/abstraction, landuse build, climate build, and CLI upload.
- Added scoped guards to simple Priority 1 `project_rq.py` paths: rangeland cover, treatments, ash, debris flow, RAP TS, OpenET TS, POLARIS, and RUSLE.
- Kept root-locked guards inside existing lock callbacks so archive/root rejection remains before cache clearing.
- Added regression coverage for exact scopes, guard ordering, archive rejection, and representative status/timestamp/enqueue behavior.
- Recorded Priority 2 split/defer disposition in `package.md`.

**Blockers encountered**:
- None. Priority 2 was intentionally split/deferred because module-specific orchestration tests are required.

**Next steps**:
1. Create follow-up packages for Priority 2 module families when scheduled.
2. Keep using `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` for future hydrate-then-mutate RQ paths.

**Test results**:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` -> `44 passed, 15 warnings`.
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md` -> passed.
- `git diff --check` -> passed.
