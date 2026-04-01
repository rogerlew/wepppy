# Tracker - Features Export Live-Run E2E Matrix (Phase 2 Reopen)

## Quick Status

**Started**: 2026-03-29  
**Current phase**: Complete (Phase 3 bd variant rerun closed)  
**Last updated**: 2026-04-01  
**Next milestone**: Optional follow-up package for SWAT/AgFields live-run matrix parity.

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
- [x] Reopened package for Omni single-OFE scenario/contrast validation follow-up, reactivating tracker and active ExecPlan. (2026-03-29)
- [x] Added Phase-2 Omni harness support to `artifacts/run_live_matrix.py` (`--phase phase2_omni`, dynamic selector discovery, `H1-H4` groups). (2026-03-29)
- [x] Executed Omni sentinel matrix groups `H1-H2` on `walk-in-obsessive-compulsive/disturbed9002_wbt` (14/14 pass). (2026-03-29)
- [x] Executed Omni expansion groups `H3-H4` including selector negatives and scope/temporal compatibility checks (12/12 pass). (2026-03-29)
- [x] Appended Omni evidence to shared matrix ledger and generated dedicated Phase-2 evidence artifacts:
  - `artifacts/matrix_results.jsonl` (136 rows total, 0 failures)
  - `artifacts/manual_sanity_notes_phase2_omni.md`
  - `artifacts/defect_log_phase2_omni.md`
  (2026-03-29)
- [x] Added disturbed lookup `bd` variant matrix group `I1` in harness (`base|extended` x `blank|numeric`) with lookup precondition plumbing and state restore guards. (2026-04-01)
- [x] Executed full rerun matrix (Phase 1 + expansion + Phase 2 Omni) with timestamped rerun artifacts:
  - `artifacts/matrix_results_rerun_20260401_023942.jsonl` (140 rows, 0 failures)
  - `artifacts/manual_sanity_notes_rerun_20260401_023942_phase1.md`
  - `artifacts/defect_log_rerun_20260401_023942_phase1.md`
  - `artifacts/manual_sanity_notes_rerun_20260401_023942_phase2_omni.md`
  - `artifacts/defect_log_rerun_20260401_023942_phase2_omni.md`
  (2026-04-01)

## Timeline

- **2026-03-29** - Package created with core 78-case matrix (77 positive + 1 negative).
- **2026-03-29** - Scope expanded with execution gates and expansion groups (`F-G`) for cache/negative/oracle coverage.
- **2026-03-29** - Implemented matrix harness + auditor and ran first live Gate-1 execution.
- **2026-03-29** - Identified and fixed live defects (return-period selector, units conversion, mixed temporal wide, atemporal temporal inheritance, UI copy).
- **2026-03-29** - Re-ran matrix to closure with strict gate order and produced final evidence set (110/110 pass).
- **2026-03-29** - Completed required pytest/Jest validation commands.
- **2026-03-29** - Reopened package as Phase 2 to execute Omni scenarios/contrasts validation on `walk-in-obsessive-compulsive/disturbed9002_wbt` (single OFE context).
- **2026-03-29** - Completed Phase 2 Omni matrix execution (`H1-H4`: 26/26 pass) and published dedicated Omni evidence artifacts.
- **2026-04-01** - Extended matrix harness with disturbed lookup `bd` variant group `I1` (`base|extended` x `blank|numeric`) and lookup snapshot/restore safety.
- **2026-04-01** - Executed full rerun matrix with timestamped artifacts (`matrix_results_rerun_20260401_023942.jsonl`: 140/140 pass, includes `I1` 4/4).

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

### 2026-03-29: Reopen this package instead of creating a new Omni-only package
**Context**: Original package closure explicitly listed Omni-inclusive matrix execution as follow-up work.

**Options considered**:
1. Open a new standalone package for Omni scenario/contrast testing.
2. Reopen this package as Phase 2 and extend matrix scope.

**Decision**: Reopen this package as Phase 2.

**Impact**: Preserves one contiguous artifact/test history for Features Export live-run matrix evolution while adding the missing Omni scenario/contrast coverage.

### 2026-03-29: Discover Omni selectors from run-path datasets at execution time
**Context**: Omni scenario/contrast IDs vary by run and can drift from static fixtures.

**Options considered**:
1. Hardcode selector IDs in the matrix catalog.
2. Inspect run-path `_pups/omni/...` directories and require required interchange files before selecting IDs.

**Decision**: Use runtime selector discovery in `run_live_matrix.py` for Phase 2 case generation.

**Impact**: Removed selector drift risk and guaranteed `H1-H4` coverage targets selectors with materializable source files.

### 2026-04-01: Model `bd` variant coverage as matrix preconditions, not payload mutations
**Context**: Need matrix coverage for disturbed lookup `bd` blank/numeric behavior across both lookup variants without changing features_export request contracts.

**Options considered**:
1. Add request payload parameters to control disturbed lookup variant and `bd` mode.
2. Apply deterministic disturbed lookup preconditions in the runner before each case and keep payload contract unchanged.

**Decision**: Add runner-level preconditions (`lookup_variant`, `bd_mode`) and restore disturbed lookup files + active variant after execution.

**Impact**: Added targeted `I1` coverage while preserving export API contracts and preventing lookup-state leakage across matrix runs.

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
- [x] Full rerun matrix (timestamped artifacts):
  - `wctl run-python -- docs/work-packages/20260329_features_export_live_run_matrix/artifacts/run_live_matrix.py --runid clogging-starch --config disturbed9002-wbt-mofe --results-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results_rerun_20260401_023942.jsonl --manual-notes-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase1.md --defect-log-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase1.md`
  - `wctl run-python -- docs/work-packages/20260329_features_export_live_run_matrix/artifacts/run_live_matrix.py --phase phase2_omni --runid walk-in-obsessive-compulsive --config disturbed9002_wbt --results-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results_rerun_20260401_023942.jsonl --append-results --manual-notes-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase2_omni.md --defect-log-path docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase2_omni.md`

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
- [x] Omni scenario sentinel cases pass on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
- [x] Omni contrast sentinel cases pass on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
- [x] Omni-focused matrix evidence appended to `artifacts/matrix_results.jsonl` and summarized in dedicated Phase-2 artifacts.

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

### 2026-03-29 - Phase 2 Reopen (Omni Scenarios/Contrasts, Single OFE)
**Agent**: Codex

**Completed**:
- Reopened package/tracker status from Closed to active Phase 2 follow-up.
- Captured target run context:
  - URL: `https://wc.bearhive.duckdns.org/weppcloud/runs/walk-in-obsessive-compulsive/disturbed9002_wbt/`
  - Focus: Omni scenarios and Omni contrasts in single-OFE configuration.
- Implemented Phase-2 harness extensions and executed Omni matrix groups:
  - `H1`: 7/7 (Omni scenario sentinel across all formats)
  - `H2`: 7/7 (Omni contrast sentinel across all formats)
  - `H3`: 4/4 (selector validation negatives)
  - `H4`: 8/8 (scope/temporal compatibility + multi-select assertions)
- Appended results to `artifacts/matrix_results.jsonl` (now 136 rows total) and generated:
  - `artifacts/manual_sanity_notes_phase2_omni.md`
  - `artifacts/defect_log_phase2_omni.md`

**Next Steps**:
- None in this package. Ready for final reviewer handoff.

### 2026-04-01 - Phase 3 Rerun (Disturbed `bd` Variant Coverage)
**Agent**: Codex

**Completed**:
- Extended `artifacts/run_live_matrix.py` with `I1` matrix group:
  - `i1_bd_base_blank`
  - `i1_bd_base_numeric`
  - `i1_bd_extended_blank`
  - `i1_bd_extended_numeric`
- Added disturbed lookup precondition plumbing to set target `bd` cell values per case and switch lookup variant deterministically.
- Added snapshot/restore of disturbed lookup state (`base`, `extended`, `active_lookup_variant`) so reruns are state-safe.
- Executed full matrix rerun with timestamped artifacts:
  - Total rows: 140
  - Passed: 140
  - Failed: 0
  - `I1`: 4/4

**Evidence**:
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results_rerun_20260401_023942.jsonl`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase1.md`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase1.md`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase2_omni.md`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase2_omni.md`

**Next Steps**:
- None in this package. Rerun closure evidence is complete.
