# Tracker - Peridot Side-Hillslope Length Capping + Provenance Mode

> Living document tracking planning, decisions, risks, and implementation progress for side-hillslope length stabilization.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-23 01:24 UTC  
**Current phase**: Closed  
**Last updated**: 2026-04-23 03:00 UTC  
**Next milestone**: N/A (package closed; follow-on package created)  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-23 01:25 UTC).
- [x] Authored package brief with compatibility/regression plan and explicit scope boundaries (2026-04-23 01:26 UTC).
- [x] Drafted active ExecPlan capturing side-hillslope cap behavior, output provenance fields, and validation gates (2026-04-23 01:27 UTC).
- [x] Registered package in root `PROJECT_TRACKER.md` under `In Progress` (2026-04-23 01:29 UTC).
- [x] Implemented side-hillslope cap logic in non-representative abstraction (`L_final = min(L_area, L_edge)` with explicit no-edge fallback) (2026-04-23 01:41 UTC).
- [x] Implemented equivalent side-hillslope cap logic in representative abstraction using source-cell flowpath medians for `L_edge` (2026-04-23 01:42 UTC).
- [x] Added additive hillslope provenance outputs (`length_estimate_mode`, `length_area_over_channel`, `length_edge_median`) in metadata writers/schemas and flowpath model (2026-04-23 01:43 UTC).
- [x] Updated schema/contract documentation in Peridot/WEPPpy docs for new side-hillslope length semantics and additive fields (2026-04-23 01:44 UTC).
- [x] Added regression tests for cap activation, fallback/non-activation, area preservation, and representative/non-representative side-mode semantics (2026-04-23 01:44 UTC).
- [x] Ran targeted Peridot validations and recorded outcomes (2026-04-23 01:45 UTC).
- [x] Ran `wctl doc-lint` on package and updated contract docs with clean results (2026-04-23 01:47 UTC).
- [x] Archived active ExecPlan to `prompts/completed/` with outcome note and closed package docs (2026-04-23 03:00 UTC).
- [x] Opened follow-on package for MOFE segmentation migration/performance path (`segmented_multiple_ofe` -> `wepppyo3`, process-pool refactor) (2026-04-23 03:00 UTC).

## Timeline

- **2026-04-23 01:24 UTC** - Package initiated from user request to stabilize side-hillslope lengths and add provenance.
- **2026-04-23 01:27 UTC** - Active ExecPlan authored.
- **2026-04-23 01:29 UTC** - Root project tracker updated with package entry.
- **2026-04-23 01:41 UTC** - Non-representative side hillslope abstraction updated to cap side length by median edge/source evidence with fallback to area/channel estimate.
- **2026-04-23 01:42 UTC** - Representative side hillslope abstraction updated with equivalent cap semantics using source-cell flowpath medians.
- **2026-04-23 01:43 UTC** - Hillslope metadata schema/writers/manifest updated to emit additive length provenance fields.
- **2026-04-23 01:44 UTC** - Regression tests added for cap activation, fallback, area preservation, and side-mode parity across abstraction paths.
- **2026-04-23 01:45 UTC** - Targeted validation commands executed successfully in `/workdir/peridot`.
- **2026-04-23 01:47 UTC** - Package and contract docs linted with `wctl doc-lint` (0 errors, 0 warnings).
- **2026-04-23 01:49 UTC** - Added explicit length-provenance mode/value semantics to data-table contract notes and re-ran doc lint cleanly.
- **2026-04-23 03:00 UTC** - Package closed; ExecPlan archived to `prompts/completed/`; follow-on MOFE segmentation/performance package initiated.

## Decisions Log

### 2026-04-23 01:25 UTC: Keep top/source hillslope logic unchanged in this package
**Context**: User concern and proposed fix target side hillslopes with inflated `area/channel_length` estimates.

**Options considered**:
1. Apply cap logic to all hillslope classes (`%10 in {1,2,3}`).
2. Restrict cap logic to side hillslopes (`%10 in {2,3}`) and retain top/source behavior.

**Decision**: Option 2.

**Impact**: Limits behavioral change to the identified failure mode and lowers hydrologic-regression surface.

---

### 2026-04-23 01:26 UTC: Make output contract additive with explicit provenance fields
**Context**: Analysts need to know which length mode produced each hillslope length.

**Options considered**:
1. Replace existing `length` semantics without extra provenance fields.
2. Keep existing fields and add explicit provenance fields (mode + candidate values).

**Decision**: Option 2.

**Impact**: Improves auditability and downstream interpretability while preserving backward compatibility for consumers expecting `length`.

---

### 2026-04-23 01:42 UTC: Keep top/source mode labels path-specific and side mode labels shared
**Context**: Side-hillslope parity was required across representative and non-representative abstractions, while top/source behavior was required to remain unchanged.

**Options considered**:
1. Force one shared top/side mode vocabulary across both abstraction paths.
2. Keep top/source labels path-specific (`top_edge_median` vs `top_representative_flowpath`) but enforce identical side labels and semantics.

**Decision**: Option 2.

**Impact**: Preserves top/source behavior traceability per abstraction path while keeping side-capping semantics directly comparable.

---

### 2026-04-23 01:43 UTC: Emit candidate values as nullable columns for diagnostics
**Context**: A single mode field indicates branch choice but does not expose candidate magnitudes used in that branch.

**Options considered**:
1. Emit mode only (`length_estimate_mode`).
2. Emit mode plus candidate fields (`length_area_over_channel`, `length_edge_median`).

**Decision**: Option 2.

**Impact**: Enables post hoc QA and hydrologic interpretation audits without recomputing candidates from raster primitives.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Cap logic changes runoff/erosion outcomes for existing projects | High | Medium | Restrict to side hillslopes, add focused regression coverage, and document behavior change clearly | Mitigated (behavior change is intentional and bounded) |
| Edge/source median unavailable or unstable on some hillslopes | Medium | Medium | Define explicit fallback to `area/channel_length` and encode mode in output fields | Mitigated (fallback implemented + tested) |
| Downstream readers assume fixed hillslopes schema | Medium | Medium | Add columns additively, update schema docs, and verify WEPPpy readers tolerate extra columns | Mitigated (additive fields + docs updated; downstream runtime audit still recommended) |
| Representative path diverges from non-representative path | Medium | Low | Implement parallel logic in both paths and test both code paths | Mitigated (shared side mode semantics verified by tests) |

## Verification Checklist

### Code Quality
- [x] Peridot targeted tests pass for updated hillslope length behavior.
- [x] No new broad exception handling introduced in changed production paths.

### Documentation
- [x] Work-package docs initialized and linked.
- [x] Output contract docs updated for additive provenance fields.
- [x] Manifest/schema summaries updated where produced.
- [x] `wctl doc-lint` passes for package + touched contract docs.

### Testing
- [x] Cap-activation regression fixture passes (`median_edge_source < area/channel_length`).
- [x] Non-activation regression fixture passes (`median_edge_source >= area/channel_length` or unavailable).
- [x] Area-preservation assertions pass for modified side hillslopes.
- [x] Representative and non-representative path tests both cover mode selection.

### Deployment/Operational
- [x] Optional run-level before/after diagnostic explicitly deferred to follow-on package by user direction.

## Progress Notes

### 2026-04-23 03:00 UTC: Package closure + follow-on handoff
**Agent/Contributor**: Codex

**Work completed**:
- Closed package docs (`package.md`, `tracker.md`) after implementation and targeted validation were complete.
- Archived active ExecPlan into `prompts/completed/` and added outcome note documenting delivered behavior + residuals.
- Captured follow-on scope for MOFE segmentation migration/performance work in a new work package.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute the follow-on MOFE segmentation/performance package.

**Test results**:
- No new runtime tests in this closeout-only update.

### 2026-04-23 01:47 UTC: ExecPlan implementation + targeted validation
**Agent/Contributor**: Codex

**Work completed**:
- Implemented side-hillslope capping in non-representative abstraction (`abstract_subcatchment`) using `min(L_area, L_edge)` with explicit no-edge fallback.
- Implemented equivalent side-hillslope capping in representative abstraction (`build_representative_hillslope`) using source-cell flowpath medians as `L_edge`.
- Added additive provenance fields (`length_estimate_mode`, `length_area_over_channel`, `length_edge_median`) to flowpath model and hillslope metadata parquet/csv/schema/manifest writers.
- Updated docs for additive hillslope provenance and side-length cap semantics in Peridot/WEPPpy contract surfaces.
- Recorded validation artifact at `docs/work-packages/20260422_peridot_side_hillslope_length_capping/artifacts/validation_summary.md`.

**Blockers encountered**:
- No external blockers.

**Next steps**:
1. Optional: run a full watershed diagnostic for the specific `topaz_id=11132` case.

**Test results**:
- `cargo test --test hillslope_slope_scalar -- --nocapture` -> PASS (`2 passed; 0 failed`).
- `cargo test representative_hillslope_length_modes_follow_selection_contract -- --nocapture` -> PASS (`1 passed; 0 failed`).
- `cargo test --test watershed_parquet_manifest -- --nocapture` -> PASS (`3 passed; 0 failed`).
- `cargo test side_length_selection -- --nocapture` -> PASS (`3 passed; 0 failed`).
- `wctl doc-lint --path docs/work-packages/20260422_peridot_side_hillslope_length_capping` -> PASS (`4 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path docs/schemas/output-scope-contract.md` -> PASS (`1 files validated, 0 errors, 0 warnings`).
- `wctl doc-lint --path docs/dev-notes/data_tables_standardization.spec.md` -> PASS (`1 files validated, 0 errors, 0 warnings`).

### 2026-04-23 01:24 UTC: Package authoring session
**Agent/Contributor**: Codex

**Work completed**:
- Created a new work package for side-hillslope length stabilization and output provenance tracking.
- Captured user-proposed behavior contract (`min(area/channel, median edge/source)`) and area-preservation requirement in package scope and success criteria.
- Added compatibility/regression plan emphasizing additive schema evolution and explicit fallback modes.
- Authored active ExecPlan for implementation in `/workdir/peridot` and documentation updates in `wepppy`.

**Blockers encountered**:
- None during authoring.

**Next steps**:
1. Execute the active ExecPlan in `/workdir/peridot` with targeted tests.
2. Update WEPPpy-side output contract docs for new provenance fields.
3. Capture before/after diagnostics for known inflated side hillslopes.

**Test results**:
- Docs-only session; no runtime/model tests executed.

## Communication Log

### 2026-04-23 03:00 UTC: Close package and open follow-on MOFE package
**Participants**: User, Codex  
**Question/Topic**: Close current side-hillslope package and author a new package for `segmented_multiple_ofe` migration/deprecation + process-pool refactor.  
**Outcome**: Current package closed and archived; new follow-on work package created with active ExecPlan.

### 2026-04-23 01:31 UTC: Execute active work package end-to-end
**Participants**: User, Codex  
**Question/Topic**: Execute package implementation milestones without extra confirmation unless blocked, including tests/docs/tracker updates.  
**Outcome**: Implementation executed across Peridot + WEPPpy docs; targeted tests passed; tracker/ExecPlan updated as living artifacts.

### 2026-04-23 01:24 UTC: Work-package request
**Participants**: User, Codex  
**Question/Topic**: Author a work package to implement side-hillslope length stabilization and length-estimation provenance.  
**Outcome**: New package scaffolded with package brief, tracker, active ExecPlan, and project-tracker registration.
