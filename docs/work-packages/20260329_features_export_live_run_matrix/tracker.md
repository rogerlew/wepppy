# Tracker - Features Export Live-Run E2E Matrix (clogging-starch)

## Quick Status

**Started**: 2026-03-29  
**Current phase**: Closed  
**Last updated**: 2026-03-29  
**Next milestone**: None - package execution complete.

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, active ExecPlan) with full matrix definition. (2026-03-29)
- [x] Expanded package scope to include gate execution, data oracles, cache-hit checks, additional negative coverage, format-specific probes, and UI regression checks. (2026-03-29)
- [x] Implemented matrix harness and artifact auditor (`artifacts/run_live_matrix.py`) with deterministic gate execution and evidence generation. (2026-03-29)
- [x] Executed `Gate-1` sentinel suite (7 format successes + 3 contract negatives) and recorded evidence artifacts. (2026-03-29)
- [x] Executed `Gate-2` core matrix groups `A-E` after Gate-1 pass and triaged live defects. (2026-03-29)
- [x] Executed expansion groups `F-G` (cache replay, additional negative contract, units numeric oracles, UI regressions). (2026-03-29)
- [x] Patched defects discovered during execution:
  - return-period selector materialization (`wepp.temporal.events`)
  - unit conversion application in export values
  - mixed temporal wide planner acceptance
  - atemporal layer temporal-mode inheritance
  - UI typo (`Unitzer` -> `Unitizer`)
  (2026-03-29)
- [x] Added regression tests for planner/materializer/service and route/template slices, then reran required suites. (2026-03-29)
- [x] Captured final evidence artifacts:
  - `artifacts/matrix_results.jsonl` (110 rows, 0 failures)
  - `artifacts/manual_sanity_notes.md`
  - `artifacts/defect_log.md`
  (2026-03-29)

## Timeline

- **2026-03-29** - Package created with core 78-case matrix (77 positive + 1 negative).
- **2026-03-29** - Scope expanded with execution gates and expansion groups (`F-G`) for cache/negative/oracle coverage.
- **2026-03-29** - Implemented matrix harness + auditor and ran first live Gate-1 execution.
- **2026-03-29** - Identified and fixed live defects (return-period selector, units conversion, mixed temporal wide, atemporal temporal inheritance, UI copy).
- **2026-03-29** - Re-ran matrix to closure with strict gate order and produced final evidence set (110/110 pass).
- **2026-03-29** - Completed required pytest/Jest validation commands.

## Decisions

### 2026-03-29: Use clogging-starch roads-capable run as first-pass canonical anchor
**Context**: Need live-run coverage first before broadening to other family-specific runs.

**Options considered**:
1. Start with synthetic fixture-only tests.
2. Start with one real run that exercises baseline+roads and temporal paths.
3. Start with multi-run matrix immediately.

**Decision**: Start with one real run (`clogging-starch/disturbed9002-wbt-mofe`) and lock matrix tooling/contracts first.

**Impact**: Faster defect discovery on real data contracts; SWAT/Omni/AgFields breadth can be added in follow-up package.

### 2026-03-29: Reinitialize features export cache index before final matrix replay
**Context**: Cache entries created before fixes could hide post-fix behavior and produce stale artifact reuse.

**Options considered**:
1. Reuse existing cache entries and rely on changed cache keys only.
2. Clear and recreate cache index while preserving schema.
3. Disable cache entirely for matrix execution.

**Decision**: Backup cache index, then reinitialize with valid schema payload (`{"schema_version":1,"entries":{}}`) for final run.

**Impact**: Ensured deterministic post-fix validation for cache and artifact replay contract without schema regression.

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| Matrix runtime is too long (78+ cases) | Medium | High | Run sentinel subset first; gate progression enforced in runner | Closed |
| Live run data drift invalidates expected counts | Medium | Medium | Derive expected counts from carrier/manifest contracts and audited integrity checks | Closed |
| False positives on null checks for optional temporal columns | Medium | Medium | Restrict strict checks to required identity columns and verified key-domain oracles | Closed |
| CRS assertions vary by format tooling | Low | Medium | Use format-specific probes and file-level EPSG assertions in auditor | Closed |
| Sentinel and full matrix drift apart | Medium | Medium | Generate all gates from one case catalog source with deterministic case IDs | Closed |

## Verification Checklist

### Core Commands
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- [x] `wctl run-npm test -- features_export`

### Manual Sanity Evidence
- [x] `Gate-1`: one successful manual case per format with evidence under `artifacts/`.
- [x] Manual validation of CRS and units behavior for representative spatial and tabular outputs.
- [x] Manual validation of yearly/event selectors and year selection behavior.

### Matrix Completion
- [x] `Gate-1` sentinel suite passed (10/10).
- [x] Core matrix groups A-E executed (80/80).
- [x] Expansion groups F-G executed (20/20).
- [x] Group E integrity audits executed across all successful outputs.
- [x] Failures triaged with linked fixes; no deferred follow-ups remain in this package.

## Progress Notes

### 2026-03-29 - Package Authoring
**Agent**: Codex

**Completed**:
- Authored new work-package scaffold at `docs/work-packages/20260329_features_export_live_run_matrix/`.
- Defined full matrix (78 runs) including formats, CRS, units, temporal combinations, roads scope, and integrity audits.
- Defined explicit requirement to fix UI label typo to `Unitizer Selections`.

**Next Steps**:
- Implement matrix runner + artifact auditor.
- Execute sentinel manual checks and begin defect triage/fixes.

### 2026-03-29 - Matrix Execution and Defect Remediation
**Agent**: Codex

**Completed**:
- Implemented matrix runner/auditor and executed gates in required order (`Gate-1` -> `Gate-2` -> `F-G`).
- Fixed live defects in materializer/planner/service/template paths and added focused regressions.
- Replayed matrix after fixes and reached full pass:
  - Gate-1: 10/10
  - Gate-2: 80/80
  - Expansion: 20/20
  - Total: 110/110 (`matrix_results.jsonl`)
- Confirmed payload/member signatures across all 7 formats, spatial/tabular CRS behavior, units conversion oracles (`project/si/english`), temporal selector/year selection behavior, identity/key-domain integrity, and cache replay contract.
- Verified UI regression requirements:
  - `Unitizer Selections` copy present
  - no temporal-change reload regression via `features_export` Jest suite
  - export-button unlock behavior retained

**Evidence**:
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results.jsonl`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes.md`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log.md`

**Next Steps**:
- None in this package; ready for reviewer handoff.
