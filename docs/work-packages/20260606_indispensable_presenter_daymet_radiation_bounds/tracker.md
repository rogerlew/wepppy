# Tracker - Indispensable Presenter Daymet Radiation Bounds Investigation

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-06 20:01 UTC
**Current phase**: Complete
**Last updated**: 2026-06-06 21:07 UTC
**Next milestone**: Regenerate downstream openWEPP validation inputs before
resuming WBVAL03
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] Regenerate or rebuild downstream openWEPP WBVAL03 validation inputs from
      corrected WEPPpy observed-Daymet artifacts.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package scaffold, active ExecPlan, and initial evidence artifact
      (2026-06-06 20:01 UTC).
- [x] Registered package in `PROJECT_TRACKER.md` backlog
      (2026-06-06 20:01 UTC).
- [x] Reproduced the downstream `CLIM-RUNTIME-E-017` source-bound signature
      from saved `indispensable-presenter` artifacts (2026-06-06 21:03 UTC).
- [x] Traced Daymet radiation through `build_observed_daymet()` and
      `ClimateFile.replace_var()` (2026-06-06 21:03 UTC).
- [x] Compared Daymet-derived `srad(l/day)` and CLI `rad` against baseline
      `sunmap.r3` horizontal daily potential (2026-06-06 21:03 UTC).
- [x] Classified ownership as WEPPpy observed-Daymet producer-boundary
      normalization for genuine Daymet over-TOA rows (2026-06-06 21:03 UTC).
- [x] Added ADR-0006, regression tests, production normalization, real-run
      validation evidence, and closure artifacts (2026-06-06 21:07 UTC).

## Timeline

- **2026-06-06 20:01 UTC** - Package created and scoped from openWEPP WBVAL03
  HOLD plus local `indispensable-presenter` climate artifacts.

## Decisions Log

### 2026-06-06 20:01 UTC: Treat this as producer-boundary defect closure

**Context**: openWEPP WBVAL03 cannot reach its snowmelt/water-balance validation
surface because climate radiation is rejected first. Local WEPPpy artifacts show
observed-Daymet mode published high daily radiation values into `wepp.cli`.

**Options considered**:
1. Relax the downstream openWEPP guard.
2. Clamp WEPPpy radiation during publication.
3. Investigate the producer source chain and only fix or branch after mechanism
   and ownership are proven.

**Decision**: Option 3.

**Impact**: The package forbids silent clipping and requires a named mechanism,
ownership classification, and regression evidence before closure.

### 2026-06-06 20:55 UTC: Normalize genuine Daymet over-TOA source rows

**Context**: The user clarified desired behavior if investigation proves Daymet
is the genuine source of radiation values above the accepted physical maximum.

**Options considered**:
1. Treat genuine over-TOA Daymet values as an external-data HOLD.
2. Fail closed before CLI publication.
3. Clamp only affected rows to the computed maximum clear-sky/TOA daily
   radiation with ADR-backed rule, tests, and artifact provenance.

**Decision**: Option 3.

**Impact**: The package may close a genuine Daymet over-TOA source defect inside
WEPPpy, but only as bounded normalization with original value, computed bound,
date, units, station/run context, and downstream acceptance evidence recorded.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Existing `/wc1/runs` artifact expires before execution | High | Medium | Initial evidence artifact captures current key values and file paths | Closed |
| Unit semantics differ between Daymet docs, WEPP CLI, and openWEPP runtime | High | Medium | Authority comparison used baseline `sunmap.r3` and source artifact evidence | Closed |
| A quick clamp hides invalid physics | High | Medium | ADR-backed bounded normalization preserves source values and emits provenance | Closed |
| Bounded normalization changes domain/parameterization behavior | High | Medium | ADR-0006, regression tests, and real-run affected-row evidence recorded | Closed |
| Defect ownership is outside WEPPpy | Medium | Medium | Ownership classified inside WEPPpy producer boundary | Closed |

## Hardening Signal Log

- **Baseline health signals**:
  - `indispensable-presenter` climate mode is `observed_daymet`.
  - `climate/wepp_cli.parquet` has `rad` maximum `989.0` L/day.
  - openWEPP WBVAL03 evidence reports `CLIM-RUNTIME-E-017` for `radly=486`.
- **Post-change health signals**:
  - `indispensable-presenter` normalization affects 53 rows.
  - Post-normalization max excess over baseline `sunmap.r3` is `0.0`.
  - The `1990-02-18` source row normalizes from `486.398513 Ly/day` to
    publication-safe `453 Ly/day`.
- **Danger signals observed**: None beyond baseline defect evidence.
- **Temporary callus register**: None.
- **Softening experiments**: Not applicable.

## Verification Checklist

### Code Quality

- [x] Focused climate producer tests pass.
- [x] No broad exception handling or silent fallback is added.
- [x] Any correction is localized to the producing boundary or branch-owned
      outside WEPPpy.

### Security

- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security review not required.

### Documentation

- [x] Work-package scaffold created.
- [x] Initial evidence artifact created.
- [x] `PROJECT_TRACKER.md` updated.
- [x] Package tracker and ExecPlan updated through closure.
- [x] ADR added if formulas, thresholds, unit conversions, or bounds change.
- [x] ADR added before implementing Daymet over-TOA bounded normalization.

### Testing

- [x] Unit/regression tests cover the exact failure mode if WEPPpy owns the
      mechanism.
- [x] `indispensable-presenter` validation evidence is recorded after any fix.
- [x] `wctl doc-lint` passes for package docs and `PROJECT_TRACKER.md`.

## Progress Notes

### 2026-06-06 20:01 UTC: Package scaffolded

**Agent/Contributor**: Codex

**Work completed**:
- Created work-package directory under
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/`.
- Captured current local run evidence for `indispensable-presenter`.
- Created a package-level ExecPlan focused on mechanism and ownership
  classification before correction.
- Added package to `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Completed during the 2026-06-06 21:07 UTC package execution recorded below.
2. The ExecPlan now lives at
   `prompts/completed/daymet_radiation_bounds_execplan.md`.
3. Follow-up is limited to regenerating downstream openWEPP validation inputs.

**Test results**:
- Not run during scaffold beyond local static artifact inspection.

### 2026-06-06 20:55 UTC: Conditional over-TOA clamp policy recorded

**Agent/Contributor**: Codex

**Work completed**:
- Updated package scope, success criteria, and ExecPlan to encode the
  user-approved conditional behavior: genuine Daymet over-TOA source values
  should be clamped to the computed maximum clear-sky/TOA daily radiation.
- Preserved the distinction between bounded, provenance-recorded normalization
  and silent clipping.
- Made ADR coverage explicit before implementing the clamp/normalization rule.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute mechanism and ownership classification.
2. If Daymet over-TOA source is proven, draft ADR and implement bounded
   normalization with tests and affected-row provenance.

**Test results**:
- Not run; documentation update pending doc lint.

### 2026-06-06 21:07 UTC: Package executed and closed

**Agent/Contributor**: Codex

**Work completed**:
- Reproduced the source-bound failure from saved `indispensable-presenter`
  artifacts: `1990-02-18` source `486.398513 Ly/day`, rounded CLI `rad=486`,
  baseline `sunmap.r3` bound `453.068716 Ly/day`.
- Classified the mechanism as genuine Daymet over-TOA source rows requiring
  WEPPpy producer-boundary bounded normalization.
- Added ADR-0006 and implemented normalization in
  `wepppy/nodb/core/climate_build_helpers.py` before CLI `rad` publication for
  observed-Daymet single-location and interpolated helpers.
- Added regression coverage in `tests/nodb/test_climate_build_helpers.py`.
- Validated the saved run artifact without mutating it: 53 affected rows and
  post-normalization max excess over bound `0.0`.
- Moved the ExecPlan to `prompts/completed/` and updated package closure docs.

**Blockers encountered**:
- None inside WEPPpy. Downstream openWEPP WBVAL03 still needs regenerated or
  rebuilt validation inputs before resuming.

**Next steps**:
1. Regenerate or rebuild openWEPP WBVAL03 climate inputs from corrected WEPPpy
   observed-Daymet artifacts.
2. Resume WBVAL03 from the snowmelt/water-balance package once the climate
   source-bound blocker is cleared.

**Test results**:
- `wctl run-pytest tests/nodb/test_climate_build_helpers.py --maxfail=1`
  (`20 passed`).
- `wctl run-pytest tests/nodb/test_climate_artifact_export_service.py
  tests/climate/test_cligen_peak_intensity_contract.py
  tests/nodb/test_climate_build_router_services.py
  tests/nodb/test_user_defined_cli_parquet.py --maxfail=1` (`29 passed`).

## Communication Log

### 2026-06-06 20:01 UTC: User requested WEPPpy package

**Participants**: User, Codex
**Question/Topic**: Create a `/workdir/wepppy/docs/work-packages` package to
investigate why the producer is generating unphysically bounded radiation values
for `indispensable-presenter`.
**Outcome**: Package scaffolded with reproduction evidence and active ExecPlan.
