# Tracker - SSURGO Project SQLite Cache

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-19 19:04 UTC
**Current phase**: ADR ratification follow-up
**Last updated**: 2026-06-19 21:38 UTC
**Next milestone**: Validate ADR docs and hand off ratified decision record.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260619_ssurgo_project_sqlite_cache/artifacts/security_review.md`
**Parameterization ADR**: `docs/adrs/ADR-0007-project-local-ssurgo-sqlite-cache.md`

## Task Board

### Ready / Backlog
- [ ] Decide whether package closure can proceed with the unrelated deterministic WEPP route test failure recorded as an external blocker.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Work-package scaffold authored with package, tracker, active ExecPlan, and review disposition template (2026-06-19 19:04 UTC).
- [x] Refactored `wepppy/soils/ssurgo/ssurgo.py` so direct `SurgoSoilCollection(...)` use defaults to in-memory SQLite and explicit file-backed cache paths remain supported.
- [x] Added `clear_ssurgo_cache_on_rebuild` serialization to `wepppy/nodb/core/soils.py`, while deriving absolute cache paths from `Soils.soils_dir` instead of serializing them.
- [x] Passed project-local cache paths from all current `Soils` build paths that construct `SurgoSoilCollection`: `build_statsgo`, `_build_spatial_api` primary SSURGO, `_build_spatial_api` STATSGO fallback, `_build_single`, and `_build_gridded`.
- [x] Updated direct non-`Soils` caller `surgo_tabular_db_builder.py` to pass its explicit builder DB path, and documented `spatializer.py` as intentionally in-memory.
- [x] Parsed and persisted the checkbox option in `wepppy/microservices/rq_engine/soils_routes.py` and exposed it through RQ schema/defaults.
- [x] Honored cache clearing in the worker/build path while deleting only the project-local cache database and exact SQLite sidecar files `<cache_path>-wal` and `<cache_path>-shm`.
- [x] Rendered `Clear SSURGO cache on rebuild` in `soil_pure.htm` using `ui.checkbox_field(...)`.
- [x] Updated soil controller tests; generated frontend assets were not required because controller source did not change.
- [x] Added backend regression tests for in-memory default, explicit file cache, legacy NoDb defaults, normal and batch route parsing, schema/defaults, template rendering, and constructor-site coverage.
- [x] Updated durable cache documentation in `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md`.
- [x] Accepted and fixed dual subagent review findings for symlink path confinement, SpatialAPI cache-use locking, cache reuse coverage, doc links, and markdown whitespace.
- [x] Completed dedicated security review artifact with no unresolved medium/high findings.
- [x] Added file-backed cache Markdown metadata sidecars using `<cache>.meta.md`, with NRCS source provenance and table counts.
- [x] Authored and ratified ADR-0007 for project-local SSURGO SQLite cache non-determinism and provenance expectations.

## Timeline

- **2026-06-19 19:04 UTC** - Package created from user request and initial code inspection.
- **2026-06-19 20:09 UTC** - Implementation completed; targeted tests, npm test/lint, and broad-exception gate passed. Full pytest remains blocked by an unrelated deterministic WEPP route test.
- **2026-06-19 20:24 UTC** - Dual subagent findings dispositioned; accepted findings fixed and rechecked; security review gate passed.
- **2026-06-19 20:54 UTC** - Added cache provenance metadata sidecar behavior after operator validation of new and old projects.
- **2026-06-19 21:38 UTC** - Ratified ADR-0007 because project-local SSURGO caching can affect generated soil parameters when upstream NRCS rows change.

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

### 2026-06-19 20:54 UTC: Cache provenance sidecars are Markdown derivatives
**Context**: Operator validation showed project-local cache behavior works for new and old projects. The follow-up request added a human-readable provenance sidecar when SQLite caches are written.

**Options considered**:
1. Write one generic `meta.md` in `<wd>/soils/`.
2. Write one sidecar per cache as `<cache>.meta.md`.
3. Store provenance only inside SQLite tables.

**Decision**: Option 2.

**Impact**: SSURGO and STATSGO caches can coexist without metadata collisions, and cache clearing can target each sidecar exactly. The sidecar is a human-readable derivative; the SQLite file remains canonical for machine-readable cache data.

---

### 2026-06-19 21:38 UTC: ADR required for source-snapshot non-determinism
**Context**: Operator validation showed the cache works for old and new projects, then the user identified that per-project SSURGO caches can lead to non-deterministic generated soil parameters when NRCS rows change over time.

**Options considered**:
1. Keep the package ADR gate as `not required` because no formulas/defaults changed.
2. Ratify a parameterization ADR because source-snapshot policy can change generated WEPP soil inputs.

**Decision**: Option 2.

**Impact**: `docs/adrs/ADR-0007-project-local-ssurgo-sqlite-cache.md` now records the accepted cache behavior, non-determinism modes, provenance expectations, and rollback options.

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
| In-memory SQLite default breaks multiprocessing worker-view reads | High | Medium | Keep a parent connection alive or materialize a temporary URI only long enough for worker-view construction; test direct default construction and `makeWeppSoils` with stubs | Mitigated |
| Cache clear deletes generated `.sol` files or unrelated artifacts | High | Low | Delete only deterministic cache file and SQLite sidecars; path-resolve under `soils_dir`; add unit test | Mitigated |
| Old `soils.nodb` files fail due to missing new fields | High | Medium | Defaults in `__init__` and `_post_instance_loaded`; legacy-load regression test | Mitigated |
| Build route parses unchecked checkbox ambiguously | Medium | Medium | Use `parse_request_payload(..., boolean_fields={...})`; test checked and absent payloads | Mitigated |
| Batch no-enqueue route misses the persisted cache-clear option | Medium | Medium | Persist the option before the batch return and add route coverage for `run_group == "batch"` | Mitigated |
| Existing tests assume shared `/dev/shm` cache files | Medium | Medium | Audit SSURGO tests and add explicit cache path fixtures where persistence is expected | Open |
| Durable docs retain stale `/dev/shm` cache guidance | Medium | Medium | Update `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` before closure | Mitigated |
| One of the five current `Soils` SSURGO/STATSGO constructor sites is missed | Medium | Medium | Add explicit constructor-site test or inspection evidence for `build_statsgo`, `_build_spatial_api` primary/fallback, `_build_single`, and `_build_gridded` | Mitigated |
| Direct non-`Soils` callers get unintended in-memory behavior | Low | Medium | Update the bundled DB builder to pass its DB path and disposition `spatializer.py` as intentionally in-memory or pass a cache path if persistence is required | Mitigated |
| Security review finds path traversal/cache-clear risk | High | Low | Resolve cache path from `self.soils_dir`, disallow user-supplied absolute paths from route payload, and record dedicated review evidence | Mitigated |
| Full pytest gate blocked by unrelated WEPP disturbed preview route test | Medium | High | Targeted SSURGO/package tests passed; single failing test also fails standalone and contradicts existing disturbed normalization unit contract | Open |

## Hardening Signal Log

- **Baseline health signals**: Current `ssurgo.py` can use shared `/dev/shm/surgo_tabular.db` copied from bundled data.
- **Post-change health signals**: Rebuild logs or tests show `<wd>/soils/ssurgo_tabular_cache.sqlite` or `<wd>/soils/statsgo_tabular_cache.sqlite` creation with adjacent `<cache>.meta.md` provenance sidecars, and direct constructor use leaves no shared cache file writes.
- **Danger signals observed**: None yet.
- **Temporary callus register**: None.
- **Softening experiments**: None.

## Verification Checklist

### Code Quality
- [x] Targeted SSURGO/cache tests pass (`wctl run-pytest tests/soils/<target> --maxfail=1`).
- [x] Targeted NoDb soils tests pass (`wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py --maxfail=1` plus any new file).
- [x] RQ engine soils route tests pass (`wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`).
- [x] Frontend tests pass (`wctl run-npm test`).
- [x] Frontend lint passes (`wctl run-npm lint`).
- [ ] Full pre-handoff sanity run completed (`wctl run-pytest tests --maxfail=1`) or explicit package-owner risk acceptance recorded if external constraints prevent it.

### Security
- [x] Security impact triage recorded as `high` with rationale.
- [x] File/path handling review proves cache path is derived from `Soils.soils_dir`, not from unchecked user input.
- [x] Cache clearing is limited to the project-local database, exact SQLite sidecars `<cache_path>-wal` and `<cache_path>-shm`, and cache metadata sidecar.
- [x] Existing auth/session/queue access controls remain unchanged.
- [x] Dedicated security review artifact is complete.
- [x] No unresolved medium/high security findings remain.

### Documentation
- [x] Package and tracker updated with implementation decisions and outcomes.
- [x] Active ExecPlan progress, surprises, decision log, and retrospective updated during work.
- [x] `wepppy/soils/README.md` and `wepppy/soils/ssurgo/ssurgo.md` updated for project-local/default in-memory cache behavior.
- [x] Parameterization ADR added because cache source-snapshot behavior can affect generated WEPP soil inputs.

### Testing
- [x] Unit coverage for direct in-memory `SurgoSoilCollection` default.
- [x] Unit coverage for explicit project cache persistence and clear behavior.
- [x] Unit coverage for explicit project cache metadata sidecar creation and clearing.
- [x] Explicit coverage or inspection artifact for all five `Soils` constructor sites.
- [x] Explicit coverage or disposition for non-`Soils` direct callers (`surgo_tabular_db_builder.py`, `spatializer.py`).
- [x] Legacy NoDb load coverage for missing new fields.
- [x] Route/controller/template coverage for checkbox option, including batch no-enqueue route behavior.
- [ ] Generated run artifact coverage proves project-local SQLite appears in `<wd>/soils/` after rebuild; current coverage is fixture-only and avoids live NRCS requests.

### Review
- [x] `reviewer` subagent review completed and saved to `artifacts/code_review_findings.md`.
- [x] `qa_reviewer` subagent review completed and saved to `artifacts/qa_review_findings.md`.
- [x] Every finding is dispositioned in the artifact or tracker.
- [x] Accepted medium/high findings are fixed and rechecked.

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

### 2026-06-19 20:09 UTC: Implementation and validation
**Agent/Contributor**: Codex

**Work completed**:
- Refactored SSURGO tabular SQLite handling so direct `SurgoSoilCollection(...)` calls use in-memory SQLite by default, while project builds pass explicit cache files under `<wd>/soils/`.
- Added `Soils.clear_ssurgo_cache_on_rebuild`, derived SSURGO/STATSGO cache paths, exact sidecar deletion, and legacy instance backfill.
- Wired the option through the RQ build-soils route, RQ schema/defaults, `soil_pure.htm`, and controller serialization tests.
- Updated durable soil docs and direct caller disposition.
- Fixed two shared UI validation-gate issues discovered by full-suite attempts: query-engine pure macro context import/default maturity href handling, and pure macro default maturity href resolution for isolated Flask route tests.
- Fixed two unrelated frontend test lint violations so `wctl run-npm lint` can run cleanly.

**Blockers encountered**:
- `wctl run-pytest tests --maxfail=1` still fails at `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]`.
- The same WEPP route test fails standalone and is outside the SSURGO cache change set. Its expectation also conflicts with existing `normalize_disturbed_class_for_management_lookup` unit coverage that says fire-mulch classes inherit burned-base lookup classes.

**Next steps**:
- Complete `reviewer` and `qa_reviewer` subagent reviews and disposition findings.
- Complete the dedicated security review artifact.
- Either obtain owner acceptance for the unrelated full-suite blocker or address it in a separate WEPP disturbed preview package.

**Test results**:
- Passed: `python -m py_compile wepppy/soils/ssurgo/ssurgo.py wepppy/nodb/core/soils.py wepppy/microservices/rq_engine/soils_routes.py wepppy/microservices/rq_engine/schema_defaults_routes.py`
- Passed: `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py tests/nodb/test_soils_gridded_root_creation.py tests/microservices/test_rq_engine_soils_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- Passed: `wctl run-npm test`
- Passed: `wctl run-npm lint`
- Passed: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Passed: `wctl run-pytest tests/query_engine/test_server_routes.py::test_query_endpoint_accepts_trailing_slash --maxfail=1`
- Passed: `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py::test_modify_disturbed_page_emits_csrf_token_for_save --maxfail=1`
- Blocked: `wctl run-pytest tests --maxfail=1` due to the unrelated deterministic WEPP disturbed preview test listed above.

### 2026-06-19 20:24 UTC: Review disposition and security closure
**Agent/Contributor**: Codex + `reviewer` and `qa_reviewer` subagents

**Work completed**:
- Accepted and fixed the code-review symlink escape finding by realpath-checking the effective `soils` directory under `self.wd` and each candidate under the effective `soils` directory.
- Accepted and fixed the QA SpatialAPI concurrency finding by keeping cache preparation, collection construction, WEPP soil building, output writes, and invalid-soil logging inside the same `self.locked()` block.
- Accepted and fixed the QA cache-reuse coverage finding with a deterministic non-empty file-backed cache reuse test.
- Fixed stale broken links in touched soil docs and normalized tracker whitespace.
- Wrote `artifacts/code_review_findings.md`, `artifacts/qa_review_findings.md`, and a passing `artifacts/security_review.md`.

**Blockers encountered**:
- Full-suite pytest remains blocked by the unrelated deterministic WEPP disturbed preview route test recorded above.

**Next steps**:
- Stage, commit, and push the package implementation.

**Test results**:
- Passed: `python -m py_compile wepppy/nodb/core/soils.py tests/nodb/test_soils_ssurgo_cache.py`
- Passed: `wctl run-pytest tests/soils/test_ssurgo_cache.py tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`
- Passed: `git diff --check origin/master`
- Passed: `wctl doc-lint --path wepppy/soils/README.md`
- Passed: `wctl doc-lint --path wepppy/soils/ssurgo/ssurgo.md`

## Watch List

- Ensure `SurgoCollectionWorkerViewFactory` can read from the selected cache when the default is in-memory.
- Ensure STATSGO fallback uses `<wd>/soils/statsgo_tabular_cache.sqlite`.
- Ensure project-local cache files are not added to Git and remain run artifacts only.
- Ensure generated `controllers-gl.js` stays synchronized if frontend source changes require a build step.

## Communication Log

### 2026-06-19 19:04 UTC: Roger Lew scoping request
**Participants**: Roger Lew, Codex
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
