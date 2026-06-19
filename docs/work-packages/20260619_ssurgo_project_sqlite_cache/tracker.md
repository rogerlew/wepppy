# Tracker - SSURGO Project SQLite Cache

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-19 19:04 UTC  
**Current phase**: Scoping  
**Last updated**: 2026-06-19 19:24 UTC  
**Next milestone**: Implement project-local cache path and NoDb serialization.  
**Security impact**: high  
**Dedicated security review**: yes  
**Security artifact**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`

## Task Board

### Ready / Backlog
- [ ] Refactor `wepppy/soils/ssurgo/ssurgo.py` so direct `SurgoSoilCollection(...)` use defaults to in-memory SQLite and explicit file-backed cache paths remain supported.
- [ ] Add `clear_ssurgo_cache_on_rebuild` serialization to `wepppy/nodb/core/soils.py`, while deriving absolute cache paths from `Soils.soils_dir` instead of serializing them.
- [ ] Pass project-local cache paths from all current `Soils` build paths that construct `SurgoSoilCollection`: `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded`.
- [ ] Update direct non-`Soils` caller `surgo_tabular_db_builder.py` to pass its explicit builder DB path, and document `spatializer.py` as intentionally in-memory unless implementation finds it needs persistence.
- [ ] Parse and persist the checkbox option in `wepppy/microservices/rq_engine/soils_routes.py`.
- [ ] Honor cache clearing in the worker/build path while deleting only the project-local cache database and exact SQLite sidecar files `<cache_path>-wal` and `<cache_path>-shm`.
- [ ] Render `Clear SSURGO cache on rebuild` in `soil_pure.htm` using `ui.checkbox_field(...)`.
- [ ] Update soil controller tests and rebuild generated JS assets if required.
- [ ] Add backend regression tests for in-memory default, explicit file cache, legacy NoDb defaults, normal and batch route parsing, and project cache artifact creation.
- [ ] Run targeted validation and pre-handoff sanity checks.
- [ ] Run dual subagent review and disposition all findings.
- [ ] Complete mandatory dedicated security review artifact.
- [ ] Update durable cache documentation in `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md`.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Work-package scaffold authored with package, tracker, active ExecPlan, and review disposition template (2026-06-19 19:04 UTC).

## Timeline

- **2026-06-19 19:04 UTC** - Package created from user request and initial code inspection.

## Decisions Log

### 2026-06-19 19:04 UTC: Project builds own the persistent cache path
**Context**: The user requested each project to create a SQLite database in `<wd>/soils/` on `build_soils`, while `ssurgo.py` should use an in-memory database by default.

**Options considered**:
1. Keep the existing module-level default and add only a clear button.
2. Make `ssurgo.py` default to in-memory and require `Soils` to pass a project cache path.
3. Add a new global cache versioning layer.

**Decision**: Option 2.

**Impact**: Direct utility callers avoid stale persistent cache by default. WEPPcloud project builds still get rebuild-local cache reuse through `Soils`.

---

### 2026-06-19 19:04 UTC: Cache clear is run-scoped and additive
**Context**: The checkbox must clear stale SSURGO cache data without deleting generated soil outputs or unrelated project artifacts.

**Options considered**:
1. Delete the entire `soils` directory.
2. Delete only a named project-local SSURGO cache file and SQLite sidecars.
3. Keep the old shared cache and add a timestamp marker.

**Decision**: Option 2.

**Impact**: The implementation must name the cache file deterministically and constrain deletion to that file plus SQLite sidecars derived exactly as `<cache_path>-wal` and `<cache_path>-shm`.

---

### 2026-06-19 19:04 UTC: Dual subagent review is a closure gate
**Context**: The user explicitly requested dual subagent review with dispositioning.

**Options considered**:
1. Ask one reviewer to cover all concerns.
2. Require `reviewer` plus `qa_reviewer`, with finding disposition recorded in artifacts.
3. Defer review until after production deployment.

**Decision**: Option 2.

**Impact**: The package cannot close until both review artifacts exist and all findings are accepted/fixed, rejected with rationale, or deferred with owner and follow-up.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| In-memory SQLite default breaks multiprocessing worker-view reads | High | Medium | Keep a parent connection alive or materialize a temporary URI only long enough for worker-view construction; test direct default construction and `makeWeppSoils` with stubs | Open |
| Cache clear deletes generated `.sol` files or unrelated artifacts | High | Low | Delete only deterministic cache file and SQLite sidecars; path-resolve under `soils_dir`; add unit test | Open |
| Old `soils.nodb` files fail due to missing new fields | High | Medium | Defaults in `__init__` and `_post_instance_loaded`; legacy-load regression test | Open |
| Build route parses unchecked checkbox ambiguously | Medium | Medium | Use `parse_request_payload(..., boolean_fields={...})`; test checked and absent payloads | Open |
| Batch no-enqueue route misses the persisted cache-clear option | Medium | Medium | Persist the option before the batch return and add route coverage for `run_group == "batch"` | Open |
| Existing tests assume shared `/dev/shm` cache files | Medium | Medium | Audit SSURGO tests and add explicit cache path fixtures where persistence is expected | Open |
| Durable docs retain stale `/dev/shm` cache guidance | Medium | Medium | Update `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` before closure | Open |
| One of the five current `Soils` SSURGO/STATSGO constructor sites is missed | Medium | Medium | Add explicit constructor-site test or inspection evidence for `build_statsgo`, `_build_spatial_api` primary/fallback, `_build_single`, and `_build_gridded` | Open |
| Direct non-`Soils` callers get unintended in-memory behavior | Low | Medium | Update the bundled DB builder to pass its DB path and disposition `spatializer.py` as intentionally in-memory or pass a cache path if persistence is required | Open |
| Security review finds path traversal/cache-clear risk | High | Low | Resolve cache path from `self.soils_dir`, disallow user-supplied absolute paths from route payload, and record dedicated review evidence | Open |

## Hardening Signal Log

- **Baseline health signals**: Current `ssurgo.py` can use shared `/dev/shm/surgo_tabular.db` copied from bundled data.
- **Post-change health signals**: Rebuild logs or tests show `<wd>/soils/ssurgo_tabular_cache.sqlite` or `<wd>/soils/statsgo_tabular_cache.sqlite` creation, and direct constructor use leaves no shared cache file writes.
- **Danger signals observed**: None yet.
- **Temporary callus register**: None.
- **Softening experiments**: None.

## Verification Checklist

### Code Quality
- [ ] Targeted SSURGO/cache tests pass (`wctl run-pytest tests/soils/<target> --maxfail=1`).
- [ ] Targeted NoDb soils tests pass (`wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py --maxfail=1` plus any new file).
- [ ] RQ engine soils route tests pass (`wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`).
- [ ] Frontend tests pass (`wctl run-npm test`).
- [ ] Frontend lint passes (`wctl run-npm lint`).
- [ ] Full pre-handoff sanity run completed (`wctl run-pytest tests --maxfail=1`) or explicit package-owner risk acceptance recorded if external constraints prevent it.

### Security
- [ ] Security impact triage recorded as `high` with rationale.
- [ ] File/path handling review proves cache path is derived from `Soils.soils_dir`, not from unchecked user input.
- [ ] Cache clearing is limited to the project-local database and exact SQLite sidecars `<cache_path>-wal` and `<cache_path>-shm`.
- [ ] Existing auth/session/queue access controls remain unchanged.
- [ ] Dedicated security review artifact is complete.
- [ ] No unresolved medium/high security findings remain.

### Documentation
- [ ] Package and tracker updated with implementation decisions and outcomes.
- [ ] Active ExecPlan progress, surprises, decision log, and retrospective updated during work.
- [ ] `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` updated for project-local/default in-memory cache behavior.
- [ ] Parameterization ADR remains not required because no model formulas/default hydrology parameters change.

### Testing
- [ ] Unit coverage for direct in-memory `SurgoSoilCollection` default.
- [ ] Unit coverage for explicit project cache persistence and clear behavior.
- [ ] Explicit coverage or inspection artifact for all five `Soils` constructor sites.
- [ ] Explicit coverage or disposition for non-`Soils` direct callers (`surgo_tabular_db_builder.py`, `spatializer.py`).
- [ ] Legacy NoDb load coverage for missing new fields.
- [ ] Route/controller/template coverage for checkbox option, including batch no-enqueue route behavior.
- [ ] Generated run artifact coverage proves project-local SQLite appears in `<wd>/soils/` after rebuild.

### Review
- [ ] `reviewer` subagent review completed and saved to `artifacts/code_review_findings.md`.
- [ ] `qa_reviewer` subagent review completed and saved to `artifacts/qa_review_findings.md`.
- [ ] Every finding is dispositioned in the artifact or tracker.
- [ ] Accepted medium/high findings are fixed and rechecked.

## Progress Notes

### 2026-06-19 19:04 UTC: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed current SSURGO cache, Soils build, RQ build-soils route, pure template, controller, and existing test entry points.
- Created package scope, risk model, tracker, active ExecPlan, and review disposition template.
- Added root tracker entry in backlog.

**Blockers encountered**:
- None.

**Next steps**:
- Implement milestone 1 from the active ExecPlan: cache path abstraction and in-memory default in `ssurgo.py`.

**Test results**: Not run; documentation authoring only.

### 2026-06-19 19:16 UTC: Scoping review disposition
**Agent/Contributor**: Codex + `reviewer` subagent

**Work completed**:
- Accepted and patched scoping review findings about mandatory high-impact security artifact language, derived cache paths, exact SQLite sidecar names, batch route coverage, and durable documentation updates.
- Recorded authoring review disposition in `artifacts/package_authoring_review_findings.md`.

**Blockers encountered**:
- `qa_reviewer` scoping review was still running at the time of this patch.

**Next steps**:
- Incorporate any remaining QA scoping findings, rerun doc lint, and hand off implementation.

**Test results**: Package doc-lint rerun passed.

### 2026-06-19 19:24 UTC: QA scoping review disposition
**Agent/Contributor**: Codex + `qa_reviewer` subagent

**Work completed**:
- Accepted and patched QA scoping findings about full-suite validation wording, explicit constructor-site coverage, pre-deciding cache filenames/STATSGO strategy, and direct non-`Soils` caller audit scope.
- Added an initial mandatory security review artifact with gate status pending implementation.

**Blockers encountered**:
- None.

**Next steps**:
- Rerun doc lint and hand off implementation.

**Test results**: Package doc-lint rerun passed.

## Watch List

- Ensure `SurgoCollectionWorkerViewFactory` can read from the selected cache when the default is in-memory.
- Ensure STATSGO fallback uses `<wd>/soils/statsgo_tabular_cache.sqlite`.
- Ensure project-local cache files are not added to Git and remain run artifacts only.
- Ensure generated `controllers-gl.js` stays synchronized if frontend source changes require a build step.

## Communication Log

### 2026-06-19 19:04 UTC: User scoping request
**Participants**: User, Codex  
**Question/Topic**: Author a work-package to implement project-local SSURGO SQLite cache behavior, UI control, NoDb serialization, and dual subagent review with dispositioning.  
**Outcome**: Package authored and ready for implementation.

## Handoff Summary Template

**From**: Codex  
**To**: Any available implementation agent  
**Date**: 2026-06-19 19:04 UTC

**What's complete**:
- Work-package scope and tracker are authored.
- Active ExecPlan is available at `prompts/active/ssurgo_project_sqlite_cache_execplan.md`.
- Review disposition template is available at `artifacts/subagent_review_disposition_template.md`.

**What's next**:
1. Implement the `ssurgo.py` cache-path changes and tests.
2. Wire `Soils` serialization, route parsing, UI checkbox, and controller tests.
3. Run validation, dual subagent reviews, disposition findings, and close the package.

**Context needed**:
- The persistent cache file must live under `<wd>/soils/`.
- The default `ssurgo.py` constructor behavior must be in-memory.
- The checkbox must clear only the run-scoped SSURGO cache on rebuild.

**Open questions**:
- None for implementation scoping. Project cache filenames are fixed as `ssurgo_tabular_cache.sqlite` and `statsgo_tabular_cache.sqlite`.

**Files modified this session**:
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/package.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/prompts/active/ssurgo_project_sqlite_cache_execplan.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/subagent_review_disposition_template.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/package_authoring_review_findings.md`
- `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`
- `PROJECT_TRACKER.md`

**Tests to run**:

    wctl doc-lint --path docs/work-packages/20260619_ssurgo_project_sqlite_cache/package.md
    wctl doc-lint --path docs/work-packages/20260619_ssurgo_project_sqlite_cache/tracker.md
