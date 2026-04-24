# Tracker - Landuse Legacy Flask State Route Removal (Post Gate 3)

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-24 06:14 UTC  
**Current phase**: Complete / Closure (post-closure smoke + UX/state-integrity + load-path + stale-write + custom-map description integrity remediations applied)  
**Last updated**: 2026-04-24 08:08 UTC  
**Next milestone**: None (package closed).  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/artifacts/2026-04-24_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None currently.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `prompts/completed/`, `artifacts/`, `notes/`) (2026-04-24 06:14 UTC).
- [x] Created active ExecPlan for legacy route removal execution (2026-04-24 06:14 UTC).
- [x] Created dedicated security review artifact scaffold (2026-04-24 06:14 UTC).
- [x] Registered package in `PROJECT_TRACKER.md` Backlog with execution-link handoff (2026-04-24 06:18 UTC).
- [x] Validated package docs lint (`wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path PROJECT_TRACKER.md`) (2026-04-24 06:18 UTC).
- [x] Froze removal set including `tasks/modify_landuse_mapping/` and completed caller audit (2026-04-24 06:23-06:24 UTC).
- [x] Removed legacy Flask compatibility state/mutator handlers from `wepppy/weppcloud/routes/nodb_api/landuse_bp.py` (2026-04-24 06:27 UTC).
- [x] Updated route/schema/package docs for rq-engine-only machine/state ownership (2026-04-24 06:31 UTC).
- [x] Updated `tests/weppcloud/routes/test_landuse_bp.py` to cover render/query behavior plus `404` assertions for removed endpoints (2026-04-24 06:29 UTC).
- [x] Rebuilt `wepppy/weppcloud/static/js/controllers-gl.js` to remove stale generated legacy caller drift (2026-04-24 06:30 UTC).
- [x] Completed required validation suite and doc-lint evidence collection (2026-04-24 06:33 UTC).
- [x] Closed dedicated security review findings with no unresolved medium/high issues (2026-04-24 06:33 UTC).
- [x] Moved package prompts from `prompts/active/` to `prompts/completed/` with outcome notes (2026-04-24 06:36 UTC).
- [x] Updated `PROJECT_TRACKER.md` lifecycle entry to Done (2026-04-24 06:36 UTC).
- [x] Applied post-closure smoke remediation for Finder ZIP metadata sidecars on `landuse-user-defined/upload` with regression coverage and full validation rerun (2026-04-24 06:54 UTC).
- [x] Applied post-closure stale system map-override recovery + shared title-shell styling remediation for `/landuse-user-defined` and `/landuse-map`, with full required validation rerun (2026-04-24 07:26 UTC).
- [x] Applied post-closure `Landuse.clean()` preservation guard so `build_landuse` no longer wipes `landuse/user-defined/` or `landuse/landuse_user_defined_mapping.json`, with regression coverage and full required validation rerun (2026-04-24 07:30 UTC).
- [x] Applied post-closure run-page load-path recovery so stale missing system map overrides do not make `/runs/<runid>/<config>/` unloadable (`500`), with regression coverage and full required validation rerun (2026-04-24 07:38 UTC).
- [x] Applied post-closure stale-write race remediation so stale system-map recovery never acquires a new lock on unlocked read paths and `run_0` retries on stale-write recoverable boundary errors (2026-04-24 07:50 UTC).
- [x] Applied post-closure custom-map description integrity remediation so changed map assignments persist/compute management labels (for example key `43` -> `Moderate Severity Fire`) instead of stale base-map descriptions (2026-04-24 08:00 UTC).
- [x] Applied post-closure runid-link title parity remediation so `/landuse-user-defined` and `/landuse-map` render a run-home `runid` link to the left of `wc-control__title`, matching existing editor pages (2026-04-24 08:08 UTC).

## Timeline

- **2026-04-24 06:14 UTC** - Package created as immediate post-Gate-3 follow-up.
- **2026-04-24 06:18 UTC** - Package added to global tracker backlog and lint-validated for execution readiness.
- **2026-04-24 06:23 UTC** - Removal set frozen; explicit decision recorded to remove `tasks/modify_landuse_mapping/`.
- **2026-04-24 06:27 UTC** - Legacy Flask compatibility handlers removed from `landuse_bp.py`.
- **2026-04-24 06:29 UTC** - Route test suite rewritten for render/query + removed-endpoint `404` coverage.
- **2026-04-24 06:30 UTC** - Generated controller bundle rebuilt to eliminate stale legacy caller.
- **2026-04-24 06:33 UTC** - Required pytest/Jest/doc-lint validation set passed; security artifact closed.
- **2026-04-24 06:36 UTC** - Prompt artifacts archived under `prompts/completed/`; global tracker entry moved to Done.
- **2026-04-24 06:54 UTC** - Finder ZIP smoke issue remediated by allowing/ignoring macOS metadata sidecars while retaining strict root `.man` payload policy; required validation matrix re-passed.
- **2026-04-24 07:26 UTC** - Remediated stale system custom-map reference failures (`landuse/landuse_user_defined_mapping.json` missing) and switched landuse catalog/map page titles to shared WEPPcloud shell styling; required validation matrix re-passed.
- **2026-04-24 07:30 UTC** - Root cause confirmed and remediated: `Landuse.clean()` no longer removes run-scoped user-defined catalog/map override assets during build; regression + required validation matrix re-passed.
- **2026-04-24 07:38 UTC** - Run-page load-path now recovers stale system map override references in `run_0` context so projects remain loadable/recoverable even when stale state exists.
- **2026-04-24 07:50 UTC** - Closed stale-write race follow-on: stale-system-map cleanup no longer acquires lock/write on unlocked read paths, and `run_0` recovery now also retries recoverable `NoDbStaleWriteError` cases.
- **2026-04-24 08:00 UTC** - Closed custom-map description integrity follow-on: map-save now updates changed-key descriptions from selected management labels and build-time summaries relabel legacy stale custom-map descriptions against base-map drift.
- **2026-04-24 08:08 UTC** - Closed title-row parity follow-on: landuse catalog/map pages now include run-home `runid` link in the shared control meta slot and ship render regression coverage.

## Decisions Log

### 2026-04-24 06:14 UTC: Remove legacy state routes in dedicated package
**Context**: Gate 3 is complete and prior package policy removed calendar delay for deprecation.

**Options considered**:
1. Keep legacy Flask compatibility indefinitely.
2. Remove legacy compatibility routes now under a dedicated controlled package.

**Decision**: Option 2.

**Impact**: Closes dual-route maintenance burden and makes rq-engine the only landuse machine/state API surface.

---

### 2026-04-24 06:18 UTC: Keep new package in Backlog until execution starts
**Context**: Package preparation is complete, but implementation removal work has not begun.

**Options considered**:
1. Mark package In Progress immediately after scaffolding.
2. Keep package in Backlog and move to In Progress on first implementation/test commit.

**Decision**: Option 2.

**Impact**: Preserves lifecycle semantics in `PROJECT_TRACKER.md` and makes start criteria explicit.

---

### 2026-04-24 06:14 UTC: Preserve render routes in WEPPcloud
**Context**: Render-route ownership was explicitly retained through all migration gates.

**Options considered**:
1. Expand removal to render routes.
2. Remove only state/mutator compatibility routes; keep render routes.

**Decision**: Option 2.

**Impact**: Keeps route-boundary contract stable while removing deprecated API surfaces.

---

### 2026-04-24 06:23 UTC: Remove all candidate compatibility routes, including `tasks/modify_landuse_mapping/`
**Context**: Caller audit found no in-repo production dependency on Flask compatibility endpoints.

**Options considered**:
1. Keep `tasks/modify_landuse_mapping/` as a transitional exception.
2. Remove all candidate compatibility routes in one package cut.

**Decision**: Option 2.

**Impact**: rq-engine is now the only machine/state surface for all removed operations.

---

### 2026-04-24 06:54 UTC: Accept Finder metadata sidecars without relaxing payload contract
**Context**: Post-closure smoke testing found valid Finder-created archives rejected with `Archive members must be at the archive root.` due macOS sidecar entries (`__MACOSX/._*`, `.DS_Store`).

**Options considered**:
1. Keep strict rejection and require users to hand-normalize archive internals.
2. Ignore known macOS metadata sidecars but keep root-only `.man` payload enforcement for real files.

**Decision**: Option 2.

**Impact**: Restores expected upload UX for Finder-generated archives while preserving explicit archive safety/error contracts for non-sidecar nested members.

---

### 2026-04-24 07:26 UTC: Auto-clear only stale system custom-map references
**Context**: Operator smoke run failed in `build_landuse_rq` when `Landuse.custom_mapping_relpath` pointed to missing system override file `landuse/landuse_user_defined_mapping.json`.

**Options considered**:
1. Keep current strict failure for all missing custom-map paths (including stale system override).
2. Auto-clear only the stale system-managed override reference and retain strict typed failures for other custom-map paths.

**Decision**: Option 2.

**Impact**: Prevents orphaned system override references from hard-failing build jobs while preserving explicit error contracts for arbitrary missing/invalid custom map paths.

---

### 2026-04-24 07:26 UTC: Use shared WEPPcloud shell title styling for landuse catalog/map pages
**Context**: `/landuse-user-defined` and `/landuse-map` were using one-off heading markup/styles that did not match existing WEPPcloud editor/control pages.

**Options considered**:
1. Keep one-off heading markup and tune CSS locally.
2. Use shared `ui.card_shell` title/header treatment already used by existing WEPPcloud pages.

**Decision**: Option 2.

**Impact**: Aligns page-title look-and-feel with existing WEPPcloud controls and removes page-specific heading style drift.

---

### 2026-04-24 07:30 UTC: Preserve run-scoped user-defined assets during `Landuse.clean()`
**Context**: Operator reported `build_landuse` was cleaning `landuse/user-defined/` and `landuse_user_defined_mapping.json`, causing follow-on map/catalog build failures.

**Options considered**:
1. Keep full root clean behavior and rely on later recovery/auto-clear logic.
2. Update clean behavior to preserve run-scoped user-defined catalog directory and system override JSON while still removing generated transient landuse build artifacts.

**Decision**: Option 2.

**Impact**: Eliminates destructive cleanup drift in normal build flows and keeps run-scoped user-defined catalog/map state intact across rebuilds.

---

### 2026-04-24 07:38 UTC: Add run-page stale-map recovery boundary
**Context**: Operator reported projects became unloadable (`500` in `run_0`) when stale missing system custom-map references persisted.

**Options considered**:
1. Rely only on NoDb-level stale-map auto-clear behavior.
2. Add an explicit render-path recovery wrapper in `run_0` for landuse read calls while preserving strict failures for non-system custom-map paths.

**Decision**: Option 2.

**Impact**: Prevents unrecoverable project load failures; stale system map references are repaired during render reads and page load proceeds.

---

### 2026-04-24 07:50 UTC: Keep stale-system-map recovery read-only on unlocked paths and retry stale-write boundary failures
**Context**: Follow-on smoke trace showed `NoDbStaleWriteError` could still bubble from stale-system-map cleanup writeback during `run_0` render reads.

**Options considered**:
1. Keep lock-persist attempt inside stale cleanup for unlocked read paths.
2. Treat unlocked stale cleanup as in-memory-only recovery and add explicit `NoDbStaleWriteError` retry boundary in `run_0`.

**Decision**: Option 2.

**Impact**: Eliminates stale-write race as a render-time hard-failure mode while preserving explicit non-system-path failures and rq-engine-only mutator ownership.

---

### 2026-04-24 08:00 UTC: Normalize stale custom-map descriptions when assignment changes
**Context**: Operator reported build results still appeared to use base-map semantics because key `43` kept stale description `Mixed Forest` despite custom map assignment to `UnDisturbed/Moderate_Severity_Fire.man`.

**Options considered**:
1. Require manual map JSON edits/re-save for every stale description.
2. Auto-normalize changed-key descriptions in map-save path and relabel legacy stale descriptions at build-time when custom-map management file diverges from base-map entry.

**Decision**: Option 2.

**Impact**: Prevents stale description drift from masking applied custom-map assignments and fixes severity labeling consistency for existing runs.

---

### 2026-04-24 08:08 UTC: Use shared control meta slot for run-home link parity
**Context**: Operator requested run-home `runid` link to appear left of `wc-control__title` on both landuse editor pages, matching existing editor page treatment.

**Options considered**:
1. Add custom one-off header wrappers above each card.
2. Use shared `ui.card_shell` `meta` slot and local style ordering (`order: -1`) to position the run link left of the title.

**Decision**: Option 2.

**Impact**: Maintains shared shell consistency and eliminates one-off title-row drift while restoring expected navigation affordance.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Hidden in-repo caller still depends on legacy Flask endpoint | High | Medium | Route/caller grep audit + targeted tests before removal | Closed (caller audit clean; only intentional 404 regression test references remain) |
| Removal accidentally breaks render pages | High | Medium | Keep render routes untouched and validate pure render tests | Closed (`test_landuse_bp.py`, `test_pure_controls_render.py` passed) |
| Endpoint contract docs drift after removal | Medium | Medium | Block closure on doc updates + OpenAPI/discovery checks | Closed (docs updated + doc-lint/openapi tests passed) |
| Fallback behavior reintroduced during cleanup | Medium | Low | Explicit no-fallback rule in ExecPlan + security review checks | Closed (no fallback paths added; security review closed) |
| Finder ZIPs rejected due metadata sidecars despite valid `.man` payloads | Medium | Medium | Ignore known macOS sidecars while retaining root-only `.man` member enforcement; add regressions | Closed (new rq-engine regressions + full required validation rerun passed) |
| Stale system custom-map reference (`landuse/landuse_user_defined_mapping.json`) causes build failures | Medium | Medium | Auto-clear only stale system-managed override relpath when backing file is absent; add unit regression | Closed (`tests/nodb/test_landuse_custom_mapping.py` added and full matrix rerun passed) |
| `Landuse.clean()` removes run-scoped user-defined catalog/override assets during build | High | Medium | Preserve `user-defined/` and `landuse_user_defined_mapping.json` during clean; add regression | Closed (`tests/nodb/test_root_dir_materialization.py` coverage + full matrix rerun passed) |
| Stale system custom-map state causes run-page render `500` (project unloadable) | High | Medium | Add run_0 stale-map recovery wrapper for landuse read calls; keep strict failure for non-system custom-map paths | Closed (`tests/weppcloud/routes/test_run_0_openet_admin_gate.py` coverage + full matrix rerun passed) |
| Stale-system-map cleanup writeback can trigger `NoDbStaleWriteError` during render reads | High | Medium | Avoid lock acquisition/writeback in unlocked stale cleanup; add `run_0` stale-write retry recovery and regressions | Closed (`tests/nodb/test_landuse_custom_mapping.py`, `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` + full required matrix rerun passed) |
| Changed custom-map assignments can retain stale base-map descriptions (example key `43` still `Mixed Forest`) and mask applied management overrides | Medium | Medium | Update map-save to refresh changed-key description labels and relabel legacy stale descriptions during build-time custom-map summary construction | Closed (`tests/nodb/test_landuse_custom_mapping.py`, `tests/microservices/test_rq_engine_landuse_routes.py` + full required matrix rerun passed) |

## Verification Checklist

### Route Removal
- [x] All approved legacy routes are removed from `landuse_bp.py`.
- [x] Render routes remain present and unchanged.
- [x] Removed routes return not-found behavior via Flask routing (no shadow wrappers).
- [x] `landuse-user-defined/upload` accepts Finder ZIP metadata sidecars without accepting nested non-sidecar payload members.
- [x] Missing system-managed landuse override file no longer blocks build; stale override relpath is cleared explicitly.
- [x] `build_landuse` cleanup no longer deletes run-scoped `landuse/user-defined/` catalog files or `landuse/landuse_user_defined_mapping.json`.
- [x] Run-page load (`run_0`) no longer fails unrecoverably when stale system map override references are present.
- [x] Run-page stale-system-map recovery no longer hard-fails with `NoDbStaleWriteError` from cleanup writeback races on unlocked read paths.
- [x] Changed custom-map assignments no longer keep stale base-map descriptions in saved overrides, and legacy stale descriptions are relabeled during build summary generation.
- [x] `/landuse-user-defined` and `/landuse-map` titles use shared WEPPcloud shell styling (`ui.card_shell`) instead of one-off heading markup.
- [x] `/landuse-user-defined` and `/landuse-map` title rows include run-home `runid` links positioned to the left of `wc-control__title` using shared control-meta styling patterns.

### Caller and Contract Integrity
- [x] In-repo caller audit confirms no production references to removed endpoints.
- [x] rq-engine endpoints remain canonical in JS/template paths.
- [x] Route docs and schema contracts updated.

### Testing
- [x] `test_landuse_bp.py` updated and passing.
- [x] `test_pure_controls_render.py` passing.
- [x] rq-engine landuse/discovery/openapi suites passing.
- [x] JS controller suites passing.

### Security
- [x] Dedicated security artifact updated through closure.
- [x] No unresolved medium/high findings.

## Progress Notes

### 2026-04-24 06:14 UTC: Package preparation
**Agent/Contributor**: Codex

**Work completed**:
- Created dedicated post-Gate-3 package scaffold for legacy Flask landuse state-route removal.
- Drafted package scope, constraints, and validation command set.
- Added active ExecPlan and security artifact scaffold.

**Blockers encountered**:
- None.

**Next steps**:
- Freeze exact route list and run in-repo caller audit.
- Execute removal in small slices with tests after each slice.

**Test results**:
- Not run (scaffolding/docs only).

### 2026-04-24 06:18 UTC: Readiness validation
**Agent/Contributor**: Codex

**Work completed**:
- Added package listing to `PROJECT_TRACKER.md` Backlog with direct execution prompt link.
- Corrected stale deprecation wording in completed landuse migration summary to align with no-delay policy.
- Ran doc-lint for package + tracker and confirmed clean output.

**Blockers encountered**:
- None.

**Next steps**:
- Execute active package prompt and move tracker state to In Progress at first implementation step.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path PROJECT_TRACKER.md` -> `6 files validated, 0 errors, 0 warnings`.

### 2026-04-24 06:33 UTC: Execution and closure evidence
**Agent/Contributor**: Codex

**Work completed**:
- Removed legacy Flask compatibility state/mutator routes from `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`.
- Updated `tests/weppcloud/routes/test_landuse_bp.py` to assert render/query behavior and removed-endpoint `404` behavior.
- Updated route/schema contracts (`wepppy/weppcloud/routes/nodb_api/README.md`, `docs/schemas/rq-engine-agent-api-contract.md`, `docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`).
- Rebuilt `wepppy/weppcloud/static/js/controllers-gl.js` and verified no production caller references remain to removed Flask endpoints.

**Blockers encountered**:
- One initial route-test failure due fixture drift (`DummyLanduse` missing `_resolve_effective_mapping_reference`) resolved by aligning test stub contract.

**Next steps**:
- Finalize package lifecycle updates (`PROJECT_TRACKER.md`, prompt move to `prompts/completed/`).

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `39 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

### 2026-04-24 06:54 UTC: Post-closure smoke remediation (Finder ZIP sidecars)
**Agent/Contributor**: Codex

**Work completed**:
- Updated `landuse_bp` archive member policy to tolerate known macOS metadata sidecars (`__MACOSX/*`, `.DS_Store`, `._*`) while retaining strict root-member enforcement for real `.man` payload files.
- Updated rq-engine landuse upload staging to install only root-level normalized `.man` files (excluding sidecars).
- Added regression coverage in `tests/microservices/test_rq_engine_landuse_routes.py` for Finder-sidecar acceptance and nested-member rejection.
- Updated route contract docs and package/security artifacts with remediation evidence.

**Blockers encountered**:
- None.

**Next steps**:
- None (package remains closed with remediation applied).

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

### 2026-04-24 07:26 UTC: Post-closure UX/state-integrity remediation (stale map override + title styling)
**Agent/Contributor**: Codex

**Work completed**:
- Updated landuse page templates (`controls/landuse_user_defined.htm`, `controls/landuse_map.htm`) to shared WEPPcloud title/header shell styling via `ui.card_shell`.
- Added stale system custom-map override recovery in `Landuse._resolve_effective_mapping_reference`: when `custom_mapping_relpath` points to missing `landuse/landuse_user_defined_mapping.json`, clear the stale reference and continue with baseline mapping.
- Added NoDb regression test coverage (`tests/nodb/test_landuse_custom_mapping.py`) for stale system override cleanup while preserving strict errors for arbitrary missing custom map paths.
- Updated package/security/project tracker artifacts with remediation evidence.

**Blockers encountered**:
- None.

**Next steps**:
- None (package remains closed with post-closure remediations applied).

**Test results**:
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `7 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_user_defined_catalog_inline.test.js` -> `2 passed`.

### 2026-04-24 07:30 UTC: Post-closure root-cause remediation (`Landuse.clean()` destructive wipe)
**Agent/Contributor**: Codex

**Work completed**:
- Updated `wepppy/nodb/core/landuse.py` clean path to preserve run-scoped user-defined assets (`user-defined/` and `landuse_user_defined_mapping.json`) when clearing generated landuse build artifacts.
- Added regression in `tests/nodb/test_root_dir_materialization.py` to assert preserved catalog + override files survive `Landuse.clean()`.
- Re-ran required package validation matrix after the root-cause fix.

**Blockers encountered**:
- None.

**Next steps**:
- None (package remains closed with post-closure remediations applied).

**Test results**:
- `wctl run-pytest tests/nodb/test_root_dir_materialization.py --maxfail=1` -> `7 passed`.
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `7 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.

### 2026-04-24 07:38 UTC: Post-closure run-page recoverability remediation (`run_0` stale-map boundary)
**Agent/Contributor**: Codex

**Work completed**:
- Added `run_0` render-path stale-system-map recovery wrapper for `landuse.landuseoptions` and `build_landuse_report_context` reads.
- Hardened stale-system-map comparison in `Landuse` to tolerate legacy relpath formatting variants.
- Added route-level regression tests in `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`.

**Blockers encountered**:
- None.

**Next steps**:
- None (package remains closed with post-closure recoverability remediations applied).

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` -> `27 passed`.
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `8 passed`.
- `wctl run-pytest tests/nodb/test_root_dir_materialization.py --maxfail=1` -> `7 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

### 2026-04-24 07:50 UTC: Post-closure stale-write race remediation (`NoDbStaleWriteError` during stale-map cleanup)
**Agent/Contributor**: Codex

**Work completed**:
- Updated `Landuse._clear_stale_system_custom_mapping_reference()` so unlocked render/read callers perform in-memory stale-system-map cleanup without acquiring a new lock/writeback path.
- Updated `run_0` `_call_landuse_with_stale_mapping_recovery()` to also recover/retry on `NoDbStaleWriteError` when the stale system map reference boundary applies.
- Added NoDb regression (`tests/nodb/test_landuse_custom_mapping.py`) proving unlocked stale cleanup does not acquire `locked()`.
- Added route regressions (`tests/weppcloud/routes/test_run_0_openet_admin_gate.py`) for stale-write retry on system path and explicit re-raise for non-system paths.
- Re-ran required package validation matrix and confirmed smoke report closure (`it loaded`).

**Blockers encountered**:
- None.

**Next steps**:
- None (package remains closed with stale-write follow-on closed).

**Test results**:
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `9 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` -> `29 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

### 2026-04-24 08:00 UTC: Post-closure custom-map description integrity remediation (key `43` stale label)
**Agent/Contributor**: Codex

**Work completed**:
- Updated `Landuse.build_managements()` to relabel legacy stale custom-map descriptions when a custom mapping management file diverges from base-map entry but still carries base-map description text.
- Updated rq-engine `landuse-map/save` to persist updated description labels for changed keys (file-name normalized for mapping-source selections, preserving catalog descriptions for user-defined entries).
- Added NoDb regression in `tests/nodb/test_landuse_custom_mapping.py` for stale custom-map description relabeling.
- Added rq-engine map-save regression in `tests/microservices/test_rq_engine_landuse_routes.py` asserting changed-key description normalization in override payload.

**Blockers encountered**:
- One manual run-level reproduction attempt (`wctl run-python` + `landuse.build_managements()` on `drilled-plight`) exited `137` in this environment after pre-build state inspection; closure evidence relies on deterministic regression coverage and required matrix reruns.

**Next steps**:
- None (package remains closed with custom-map description integrity follow-on closed).

**Test results**:
- `wctl run-pytest tests/nodb/test_landuse_custom_mapping.py --maxfail=1` -> `10 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> `41 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `44 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `54 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `10 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` -> `29 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> `20 passed`.
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> `10 files validated, 0 errors, 0 warnings`.

### 2026-04-24 08:08 UTC: Post-closure title-row runid link parity
**Agent/Contributor**: Codex

**Work completed**:
- Added run-home `runid` link markup in shared control `meta` slot on both `controls/landuse_user_defined.htm` and `controls/landuse_map.htm`.
- Styled both pages to position `wc-control__meta` before `wc-control__title` using the same established editor-page pattern.
- Added regression coverage in `tests/weppcloud/routes/test_pure_controls_render.py` to assert both templates render the runid link and expected run-home href.

**Blockers encountered**:
- Initial parallel pytest run exited `137`; reran sequentially for stable evidence.

**Next steps**:
- None (post-closure UX parity item complete).

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> `20 passed`.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` -> `46 passed`.

## Communication Log

### 2026-04-24 06:14 UTC: User request
**Participants**: User, Codex  
**Question/Topic**: Sanity check completed Gate 3 package and prepare the next work-package.  
**Outcome**: Gate 3 sanity-checked; new legacy route removal package scaffolded for execution.

### 2026-04-24 06:20 UTC: User execution prompt
**Participants**: User, Codex  
**Question/Topic**: Execute the active landuse legacy Flask state-route removal package end-to-end.  
**Outcome**: Package executed with required validations and security closure evidence; completion artifacts prepared.

### 2026-04-24 06:49 UTC: User smoke-test defect report
**Participants**: User, Codex  
**Question/Topic**: Finder-generated landuse user-defined catalog ZIP rejected with `Archive members must be at the archive root.`  
**Outcome**: Post-closure remediation shipped; Finder metadata sidecars are ignored while root-only `.man` payload policy remains enforced.

### 2026-04-24 07:18 UTC: User smoke-test defect/style report
**Participants**: User, Codex  
**Question/Topic**: Landuse user-defined/catalog pages had one-off title styling and operator run failed with stale custom-map reference (`landuse/landuse_user_defined_mapping.json` missing).  
**Outcome**: Shared page-shell title styling applied for both pages; stale system custom-map reference is auto-cleared with regression coverage so build no longer hard-fails on orphaned system override path.

### 2026-04-24 07:28 UTC: User root-cause report
**Participants**: User, Codex  
**Question/Topic**: `build_landuse` clean path is removing user-defined catalog directory and custom map file.  
**Outcome**: `Landuse.clean()` now preserves run-scoped `user-defined/` and `landuse_user_defined_mapping.json`; destructive wipe regression covered and full required validation matrix re-passed.

### 2026-04-24 07:34 UTC: User recoverability report
**Participants**: User, Codex  
**Question/Topic**: Missing `landuse/landuse_user_defined_mapping.json` still made projects unloadable (`run_0` render `500`) and unrecoverable.  
**Outcome**: Added `run_0` stale-system-map recovery boundary with regressions so page loads remain recoverable while preserving strict failures for non-system custom-map paths.

### 2026-04-24 07:45 UTC: User follow-on stale-write report
**Participants**: User, Codex  
**Question/Topic**: Run-page still reported `500` with `NoDbStaleWriteError` during stale-system-map cleanup writeback.  
**Outcome**: Switched unlocked stale-system-map cleanup to in-memory-only recovery + added `run_0` stale-write retry boundary and regressions; user smoke then confirmed `it loaded`.

### 2026-04-24 07:58 UTC: User custom-map label integrity report
**Participants**: User, Codex  
**Question/Topic**: Build landuse appeared to ignore user-defined map because key `43` still showed as `Mixed Forest` instead of `Moderate Severity Fire`.  
**Outcome**: Added map-save changed-key description normalization + build-time legacy stale description relabeling; regressions and required validation matrix passed.

### 2026-04-24 08:06 UTC: User title-row run-link parity request
**Participants**: User, Codex  
**Question/Topic**: Add run-home `runid` link to the left of `wc-control__title` on both landuse editor pages to match existing README/editor page treatment.  
**Outcome**: Added shared control-meta run link markup/style to `/landuse-user-defined` and `/landuse-map`, added render regression coverage, and updated package/security/tracker artifacts.
