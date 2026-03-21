# Tracker - RUSLE C Modes Implementation (`observed_rap` + `scenario_sbs`)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-21
**Current phase**: Completed
**Last updated**: 2026-03-21
**Next milestone**: None (package closed)
**Active ExecPlan**: `prompts/completed/rusle_c_modes_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed existing RUSLE, Disturbed, RAP, landuse, test, and work-package patterns (2026-03-21).
- [x] Authored package brief, tracker, and active ExecPlan (2026-03-21).
- [x] Implemented `C` formula helpers, lookup substrate, and integration runner (2026-03-21).
- [x] Added targeted regression tests for both `C` modes (2026-03-21).
- [x] Completed Milestone 4 correctness review artifact (`artifacts/milestone4_review.md`) with no unresolved high/medium findings (2026-03-21).
- [x] Completed Milestone 5 QA-review artifact (`artifacts/milestone5_qa_review.md`) with no unresolved high/medium findings (2026-03-21).
- [x] Completed final validation artifact (`artifacts/final_validation_summary.md`) (2026-03-21).
- [x] Passed targeted `RUSLE C` tests and the full WEPPpy sanity gate (`wctl run-pytest tests --maxfail=1`) (2026-03-21).
- [x] Closed package docs, archived the ExecPlan, and synchronized `PROJECT_TRACKER.md`, `AGENTS.md`, and `wepppy/nodb/mods/rusle/specification.md` (2026-03-21).

## Timeline

- **2026-03-21** - Package created and activated.
- **2026-03-21** - `observed_rap` and `scenario_sbs` implementation complete.
- **2026-03-21** - Correctness review, QA review, and final validation complete.
- **2026-03-21** - Package closed.

## Decisions

### 2026-03-21: Ship `C` as an integration runner now, not as the full future controller
**Context**: The spec still lists Milestones 6-7 as future controller work, but this package request is specifically for Milestone 5 `C`.

**Options considered**:
1. Wait for the future `Rusle` controller and implement `C` inside it.
2. Implement `C` now as a focused, auditable integration layer that the future controller can call.

**Decision**: Choose option 2.

**Impact**: Keeps scope bounded to the requested `C` feature while still delivering end-to-end factor artifacts and tests.

---

### 2026-03-21: Fail fast for unsupported non-burnable rows rather than inventing defaults
**Context**: The specification explicitly forbids silent fallbacks for unsupported unmasked classes and requires explicit unburned lookup rows where applicable.

**Options considered**:
1. Add convenience defaults for agriculture or other unsupported classes.
2. Require explicit rows and raise actionable errors when they are absent.

**Decision**: Choose option 2.

**Impact**: Runtime behavior stays auditable and aligned with the spec’s explicit-contract policy.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| RAP-to-DEM alignment changes values subtly across grids | High | Medium | Align directly to DEM profile and cover with synthetic-raster tests | Mitigated |
| Disturbed-family normalization drifts from Disturbed semantics | High | Medium | Use the disturbed mapping JSON contract and explicit normalization tests | Mitigated |
| Unsupported classes silently receive wrong `C` values | High | Low | Fail fast on missing required lookup rows or unsupported unmasked classes | Mitigated |
| Work-package docs drift from implementation | Medium | Medium | Update tracker and ExecPlan at each milestone | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted `RUSLE C` pytest suite passes.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master` reviewed (observe-only).

### Documentation
- [x] Package docs + ExecPlan synchronized with final milestone state.
- [x] `wepppy/nodb/mods/rusle/specification.md` milestone/open-question status updated if needed.
- [x] `wctl doc-lint --path docs/work-packages/20260321_rusle_c_modes_implementation` passes.
- [x] `wctl doc-lint --path PROJECT_TRACKER.md` passes.
- [x] `wctl doc-lint --path AGENTS.md` passes.

### Testing and Reviews
- [x] Correctness review artifact completed with no unresolved high/medium findings.
- [x] QA-review artifact completed with no unresolved high/medium findings.
- [x] Full WEPPpy sanity gate passes before closeout.

### Final Acceptance
- [x] Active ExecPlan moved from `prompts/active/` to `prompts/completed/`.
- [x] Package tracker/package/project tracker synchronized to completed state.
- [x] Root `AGENTS.md` active-plan pointer updated at closeout.

## Progress Notes

### 2026-03-21: Package creation and implementation surface lock
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed root and NoDb `AGENTS.md`, the ExecPlan template, the RUSLE specification, Disturbed docs, and the disturbed mapping JSON.
- Mapped current RUSLE factor-integration patterns (`ls_integration.py`, `k_integration.py`) and identified the appropriate `C` delivery surface as a focused integration runner.
- Confirmed existing raster contracts for:
  - DEM path (`Ron.dem_fn`)
  - NLCD landuse raster (`Landuse.lc_fn`)
  - DEM-aligned SBS cropping via `Disturbed.get_sbs()`
  - RAP multiband dataset access via `RangelandAnalysisPlatformV3`
- Created package docs and active ExecPlan scaffold.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement the shared `C` formula + lookup helpers.
2. Implement `observed_rap` and `scenario_sbs`.
3. Add targeted tests and execute gates.

**Test results**:
- Documentation/package authoring session only.

### 2026-03-21: End-to-end implementation, review, QA, and closeout
**Agent/Contributor**: Codex

**Work completed**:
- Implemented new RUSLE `C` modules and runtime lookup substrate.
- Added targeted regression tests covering both `C` modes and their artifact contracts.
- Completed dedicated correctness review, QA review, and final validation summary artifacts.
- Archived the ExecPlan and synchronized package/root tracking docs plus RUSLE milestone status.

**Blockers encountered**:
- `wctl doc-mv` could not archive the ExecPlan because it hit a permission-denied path under `.docker-data/postgres`; used a plain file move and updated references manually instead.

**Next steps**:
1. Follow on with Milestones 6-7: full `Rusle` controller integration and validation-run packages.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_rusle_c_formula.py tests/nodb/mods/test_rusle_c_lookup.py tests/nodb/mods/test_rusle_c_integration.py --maxfail=1` passed (`19 passed`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passed.
- `python3 tools/code_quality_observability.py --base-ref origin/master` completed (observe-only).
- `wctl run-pytest tests --maxfail=1` passed (`2429 passed, 34 skipped`).

## Communication Log

### 2026-03-21: Work-package request
**Participants**: User, Codex
**Question/Topic**: Create and execute a new work package for end-to-end RUSLE `C` implementation, including review/QA and closeout.
**Outcome**: Package created, implemented, validated, and closed.
