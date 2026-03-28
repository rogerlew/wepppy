# Tracker - Features Export Service Quality Refactor (Phased E2E)

> Living document tracking progress, decisions, risks, and verification for phased features export service quality work.

## Quick Status

**Started**: 2026-03-27  
**Current phase**: Complete (all phases closed)  
**Last updated**: 2026-03-28  
**Completed ExecPlan**: `prompts/completed/features_export_service_quality_refactor_execplan.md`  
**Next milestone**: Package closure and handoff

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan, placeholder folders) (2026-03-27).
- [x] Added package entry to `PROJECT_TRACKER.md` backlog with phase-level scope and validation intent (2026-03-27).
- [x] Ran doc lint on new package docs and tracker updates (2026-03-27).
- [x] Phase 1 complete: removed hidden identity-key fallback and enforced explicit `materialization_error` on required-source failures in legacy source merge path (2026-03-28).
- [x] Phase 2 complete: extracted collaborator modules from `service.py` (`column_selection.py`, `cache_rehydration.py`) with stable service API wrappers (2026-03-28).
- [x] Phase 3 complete: enforced strict required-source behavior on carrier discovery path and synchronized specification/test coverage (2026-03-28).
- [x] Phase 4 complete: full validation suite, run-path evidence refresh, and review artifact closure (2026-03-28).

## Timeline

- **2026-03-27** - Package created and scoped from service QA review findings.
- **2026-03-27** - Active ExecPlan authored with four execution phases and mandatory validation gates.
- **2026-03-27** - Package listed in `PROJECT_TRACKER.md` backlog for execution scheduling.
- **2026-03-28** - Completed service contract hardening and collaborator extraction with strict required-source behavior on both legacy and carrier paths.
- **2026-03-28** - Closed validation gates and run-path acceptance evidence for `clogging-starch/disturbed9002-wbt-mofe`.

## Decisions

### 2026-03-27: Execute in four phases with explicit safety-first ordering
**Context**: QA review identified compliance risks plus maintainability debt in `service.py`.

**Options considered**:
1. One-shot broad refactor.
2. Safety-first hardening, then collaborator extraction, then policy/spec finalization, then closure gates.

**Decision**: Option 2.

**Impact**: Reduced regression risk by landing behavior-sensitive contract fixes before structural decomposition.

---

### 2026-03-27: Preserve external service API and run-path behavior during refactor
**Context**: Features export path is consumed by rq-engine and WEPPcloud routes; uncontrolled API drift would cascade regressions.

**Options considered**:
1. Allow API contract changes during refactor.
2. Keep public contracts stable and restrict changes to internals unless explicitly approved.

**Decision**: Option 2.

**Impact**: Limited blast radius and kept validation focused on behavior parity and quality improvements.

---

### 2026-03-28: Required sources are strict failures on both legacy and carrier paths
**Context**: QA found carrier discovery still warning-only for required missing/unsupported sources while legacy path was strict.

**Options considered**:
1. Keep warning degrade on carrier path for compatibility.
2. Enforce strict `materialization_error` policy everywhere required sources are unresolved.

**Decision**: Option 2.

**Impact**: Eliminated policy drift and aligned runtime behavior with specification contract language.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Contract drift during extraction causes route/rq regressions | High | Medium | Preserve service API; run microservice route tests on each phase | Closed |
| Required-source behavior change surprises existing runs | High | Medium | Make policy explicit, update spec, and add regression tests before merge | Closed |
| Refactor improves structure but misses quality violations | Medium | Medium | Run `check_broad_exceptions` and targeted QA/code review artifacts | Closed |
| Runtime regression on default export | Medium | Medium | Refresh cold/warm timing evidence against WP-8 baseline | Closed |

## Verification Checklist

### Code Quality
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/wp8_service_quality_code_quality.json --md-out /tmp/wp8_service_quality_code_quality.md`
- [x] No unresolved medium/high findings in code review artifact.
- [x] No unresolved medium/high findings in QA review artifact.

### Regression Tests
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
- [x] `wctl run-npm test -- features_export`

### Documentation
- [x] `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
- [x] `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/package.md`
- [x] `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/tracker.md`
- [x] `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/prompts/completed/features_export_service_quality_refactor_execplan.md`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`

### Run-Path Evidence
- [x] Ran default baseline export for `clogging-starch/disturbed9002-wbt-mofe`.
- [x] Verified exactly 2 layers with counts `66` and `27`.
- [x] Captured cold-cache and warm-cache runtimes.

## Progress Notes

### 2026-03-27: Package creation and execution planning
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold and active ExecPlan for full phased refactor execution.
- Converted QA findings into explicit phase milestones with concrete test and quality gates.
- Added backlog entry in `PROJECT_TRACKER.md` so package is discoverable for next execution cycle.

**Blockers encountered**:
- None.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/prompts/completed/features_export_service_quality_refactor_execplan.md` (pass)
- `wctl doc-lint --path PROJECT_TRACKER.md` (pass)

### 2026-03-28: End-to-end implementation and closure
**Agent/Contributor**: Codex

**Work completed**:
- Hardened `service.py` contracts:
  - removed arbitrary join-key fallback in `_ensure_join_key_column`;
  - required-source failures now emit explicit `materialization_error` reasons on legacy source merge path.
- Enforced carrier-path strictness in `discover_layer_sources` and translated `MaterializationContractError` to canonical service `materialization_error`.
- Extracted collaborators from `service.py`:
  - `wepppy/nodb/mods/features_export/column_selection.py`
  - `wepppy/nodb/mods/features_export/cache_rehydration.py`
- Expanded regression coverage in `tests/nodb/mods/test_features_export_service.py` for:
  - required-source dependency/file/kind/join failures,
  - join-key contract enforcement,
  - malformed cache-entry fallback behavior.
- Updated `wepppy/nodb/mods/features_export/specification.md` with strict required-source and explicit identity-key contract language.
- Captured cold/warm run-path acceptance evidence for `clogging-starch/disturbed9002-wbt-mofe`.

**Run-path evidence**:
- Cold job: `manual-wp8-cold-20260328043304050246`
  - runtime: `2.541s`
  - cache hit: `false`
  - artifact: `export/features/artifacts/cbaa1b76752641b980ee1a3f119e3456/features_export.gpkg`
  - manifest: `export/features/jobs/manual-wp8-cold-20260328043304050246/manifest.json`
- Warm job: `manual-wp8-warm-20260328043306591594`
  - runtime: `0.996s`
  - cache hit: `true`
  - artifact: same as cold
  - manifest: `export/features/jobs/manual-wp8-warm-20260328043306591594/manifest.json`
- Artifact feature tables:
  - `clogging_starch_sbs_map_subcatchments`: `66`
  - `clogging_starch_chan_map_channels`: `27`

**Validation results**:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (62 passed)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` (4 passed)
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` (10 passed)
- `wctl run-npm test -- features_export` (12 passed)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass; net delta `-1`)
- `python3 tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/wp8_service_quality_code_quality.json --md-out /tmp/wp8_service_quality_code_quality.md` (observe-only, pass)
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260327_features_export_service_quality_refactor/prompts/completed/features_export_service_quality_refactor_execplan.md` (pass)
- `wctl doc-lint --path PROJECT_TRACKER.md` (pass)
