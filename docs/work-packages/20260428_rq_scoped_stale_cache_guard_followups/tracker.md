# Tracker - RQ Scoped Stale NoDb Cache Guard Follow-Ups

> Living document tracking the rollout of scoped stale-cache guards across adjacent RQ mutation paths.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-28 16:01 UTC  
**Current phase**: Discovery / Scoping Complete  
**Last updated**: 2026-04-28 16:01 UTC  
**Next milestone**: Execute Priority 0 guards and regression coverage  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Guard Priority 0 project-prep call sites listed in `package.md`.
- [ ] Audit and implement or disposition Priority 1 mod call sites.
- [ ] Audit and disposition Priority 2 orchestration/module-family call sites.
- [ ] Add targeted regression coverage for guard scope and ordering.
- [ ] Run targeted pytest, docs lint, and `git diff --check`.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Identified candidate RQ mutation call sites after closing the `build_soils_rq` guard package (2026-04-28 16:01 UTC).
- [x] Created follow-up package scaffold (`package.md`, `tracker.md`, `prompts/active/`) (2026-04-28 16:01 UTC).
- [x] Added package to `PROJECT_TRACKER.md` Backlog for visibility (2026-04-28 16:01 UTC).

## Timeline

- **2026-04-28 15:58 UTC** - `build_soils_rq` stale-cache guard package closed and pushed.
- **2026-04-28 16:01 UTC** - Adjacent `_rq` call-site scan completed; candidates grouped by priority.
- **2026-04-28 16:01 UTC** - Follow-up package and active ExecPlan drafted.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Guarding too broadly disrupts unrelated cached controllers | Medium | Medium | Use scoped `pup_relpath` only and add tests asserting exact scope | Open |
| Guard inserted before archive-root rejection changes failure ordering | Medium | Low | Mirror soils guard test pattern on lock-root paths | Open |
| Priority 2 orchestration paths become too large for one package | Medium | Medium | Require explicit split/defer disposition before implementation proceeds | Open |
| Missing a mutating mod path leaves stale-write recurrence possible | Medium | Medium | Keep candidate matrix current and add audit notes before closure | Open |

## Verification Checklist

### Code Quality
- [ ] `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1`
- [ ] Additional targeted pytest suites for any non-`project_rq.py` module touched.
- [ ] `git diff --check`

### Documentation
- [ ] Package docs updated with implementation/disposition evidence.
- [ ] `PROJECT_TRACKER.md` updated at package start and closure.
- [ ] `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups --path PROJECT_TRACKER.md`

### Testing
- [ ] Regression coverage asserts exact `pup_relpath` values for guarded paths.
- [ ] Regression coverage asserts cache clear happens after root/archive checks where applicable.
- [ ] Existing status/timestamp/enqueue behavior remains covered or explicitly unchanged.

### Deployment
- [ ] No deployment changes required unless implementation discovers operational runbook impact.

## Progress Notes

### 2026-04-28 16:01 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Scanned `wepppy/rq/*` for `*_rq` functions that hydrate NoDb controllers and call mutating methods.
- Recorded Priority 0 direct project-prep mutation paths and Priority 1/2 audit candidates in `package.md`.
- Created package lifecycle docs and active execution prompt/ExecPlan.
- Added a Backlog entry in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement Priority 0 guards in `project_rq.py` with scoped cache clear calls.
2. Add tests mirroring the `build_soils_rq` ordering/scope assertions.
3. Audit Priority 1 mod call sites and decide whether to include them in this package or split.

**Test results**:
- Not run in this step; docs-only package setup.
