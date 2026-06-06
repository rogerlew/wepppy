# Indispensable Presenter Daymet Radiation Bounds Investigation

**Status**: Complete (2026-06-06)
**Timezone**: UTC

## Overview

This package investigated why WEPPpy produced observed-Daymet climate radiation
values for `/wc1/runs/in/indispensable-presenter` that downstream openWEPP
rejected as outside its radiation-domain contract. Execution proved genuine
Daymet over-TOA source rows at the WEPPpy producer boundary and implemented
ADR-backed bounded normalization before generated CLI publication.

This was a defect-closure package, not a clamp-and-proceed package. The
mechanism, owner, bound, implementation, tests, and run-artifact validation are
recorded in `artifacts/execution_evidence.md`.

## Objectives

- Reproduce and preserve the observed radiation evidence from
  `/wc1/runs/in/indispensable-presenter`.
- Trace observed-Daymet radiation from retrieval through CLI publication:
  `srad(W/m^2)` and `dayl(s)` to `srad(l/day)` to CLIGEN/WEPP CLI `rad`.
- Determine whether the invalid values are caused by WEPPpy unit conversion,
  daylength handling, temporal alignment, CLIGEN `replace_var()` publication,
  source Daymet data, or an openWEPP contract/bound mismatch.
- If WEPPpy owns the mechanism, implement a tested correction or typed
  fail-closed validation before invalid radiation reaches generated CLI files.
- If Daymet is proven to be the genuine source of over-TOA daily radiation,
  implement bounded normalization to the computed maximum clear-sky/TOA daily
  radiation, with per-row provenance and regression evidence.
- Produce acceptance evidence that `indispensable-presenter` no longer hands
  unphysically bounded radiation to openWEPP, or produce a branch-out package
  with evidence that WEPPpy is not the owner.

## Scope

### Included

- The concrete reproduction run:
  `/wc1/runs/in/indispensable-presenter`.
- Climate artifacts for that run:
  - `climate/wepp.cli`
  - `climate/daymet_1990-1995.parquet`
  - `climate/wepp_cli.parquet`
  - `climate.log`
  - `climate.nodb`
- Producer code paths:
  - `wepppy/nodb/core/climate.py`
  - `wepppy/nodb/core/climate_build_helpers.py`
  - `wepppy/climates/daymet/`
  - `wepppy/climates/cligen/`
  - `wepppy/nodb/core/climate_artifact_export_service.py`
- Focused tests under `tests/nodb/`, `tests/climate/`, and
  `wepppy/climates/daymet/` as needed to prove the correction.
- Documentation, package artifacts, and tracker updates.

### Explicitly Out of Scope

- Relaxing or removing openWEPP fail-closed radiation guards.
- Changing openWEPP kernel/runtime behavior from this WEPPpy package.
- Broad climate-provider rewrites unrelated to the observed-Daymet radiation
  boundary.
- Retrospective mutation of existing run directories beyond reproducible local
  evidence capture, unless the final fix explicitly includes a safe rebuild or
  repair plan.
- Silent clipping, unbounded clamping, or treating physically invalid
  radiation as valid input.
- Radiation normalization without an ADR, explicit physical bound, affected-row
  evidence, and artifact provenance.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`.
- **Authoritative source path(s)**:
  - WEPPpy producer behavior:
    `wepppy/nodb/core/climate_build_helpers.py::build_observed_daymet`
  - Daymet conversion documentation:
    `wepppy/climates/daymet/solar_radiation_readme.md`
  - CLIGEN/CLI publication behavior:
    `wepppy/climates/cligen/`
  - Downstream observed failure evidence:
    `/workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/artifacts/disposition.md`
- **Cutover proof required**:
  - A rebuilt or revalidated `indispensable-presenter` climate artifact does
    not reproduce the invalid radiation handoff when WEPPpy owns the fix.
  - If WEPPpy does not own the fix, the package must identify the owning
    boundary and provide exact evidence for the branch-out.
- **Acceptance evidence type**: `both` (run-artifact evidence and regression
  test evidence).

## Stakeholders

- **Primary**: WEPPpy climate producer maintainers and openWEPP validation
  maintainers.
- **Reviewers**: NoDb climate maintainers and WBVAL package maintainers.
- **Security Reviewer**: Not required by current triage.
- **Informed**: WEPPcloud operators using observed Daymet climate mode.

## Success Criteria

- [x] Initial reproduction records the exact invalid values, source rows, and
      downstream failure signature.
- [x] The mechanism is named and supported by source-code plus artifact
      evidence; "needs more tracing" is not a closeout state.
- [x] Ownership is classified as `WEPPpy producer`, `upstream Daymet/source
      input`, or `openWEPP bound/contract`, with falsifiable evidence.
- [x] If WEPPpy owns the mechanism, production code is corrected or guarded
      before CLI publication, with regression tests that fail before and pass
      after the change.
- [x] If Daymet source data is genuinely over-TOA, WEPPpy clamps only those
      rows to the computed maximum clear-sky/TOA daily radiation, records
      affected dates/original values/bounds/provenance, and emits generated CLI
      values that no longer exceed the accepted radiation bound.
- [x] Branch-out is not required because the mechanism is owned at the WEPPpy
      observed-Daymet producer boundary.
- [x] No fix silently clips radiation, weakens validation, or hides unit/physics
      violations.
- [x] Work-package tracker, ExecPlan, evidence artifact, and project tracker
      entries are updated before closure.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`.
- **ADR required**: `yes for any clamp/normalization formula, threshold, unit
  conversion, fallback rule, or domain bound`.
- **ADR link(s)**:
  `docs/adrs/ADR-0006-observed-daymet-radiation-toa-normalization.md`.
- **Decision provenance captured**: `yes, in tracker decision log before
  implementation`.

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- Local access to `/wc1/runs/in/indispensable-presenter` while the run artifact
  still exists.
- Local openWEPP WBVAL03 artifacts remain available for downstream failure
  context.
- `wctl` and the repo-local `.venv` remain available for focused tests and
  parquet inspection.

### Blocks

- openWEPP WBVAL03 snowmelt/water-balance validation cannot resume until the
  radiation source-boundary blocker is classified and corrected or branch-owned.

## Related Packages

- **Depends on context from**:
  `/workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/package.md`
- **Blocks**:
  `/workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/`
- **Follow-up**: Regenerate or rebuild downstream openWEPP validation inputs
  from corrected WEPPpy observed-Daymet climate artifacts, then resume WBVAL03.

## Timeline Estimate

- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: High for scientific correctness, low for application
  security.

## Security Impact and Review Gate

- **Security impact triage**: `none`.
- **Dedicated security review required**: `no`.
- **Triage rationale**: The package investigates and may correct local climate
  data production and validation. It does not add auth, public routes, secrets,
  new egress surfaces, queue wiring, uploads, downloads, or subprocess
  permissions.
- **Security review artifact**: `N/A`.

## Hardening and Callus Softening

- **Failure signature(s)**:
  - Downstream openWEPP failure:
    `CLIM-RUNTIME-E-017: runtime context symbol radly=486 is out of domain`
  - Source run:
    `/wc1/runs/in/indispensable-presenter`
  - WEPPpy climate mode:
    `observed_daymet`
- **Related prior hardening efforts**:
  - openWEPP WBVAL02 radiation source-boundary closure.
  - openWEPP WBVAL03 snowmelt/water-balance closure HOLD.
- **Health signals**:
  - Observed-Daymet producer emits physically valid, contract-compatible
    radiation values or fails closed with typed evidence.
  - `indispensable-presenter` can be used as a WBVAL climate source without
    triggering `CLIM-RUNTIME-E-017`.
- **Danger signals**:
  - Radiation values are clipped without authority.
  - Over-TOA values are clamped without recording original source value,
    computed bound, date, station/run context, and downstream acceptance effect.
  - Unit conversions are changed without ADR/provenance.
  - Invalid source input is allowed to continue through generated CLI files.
- **Observation window**: Validate on `indispensable-presenter` and at least one
  focused fixture before package closure.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis**: Not applicable.

## References

- `wepppy/nodb/core/climate.py`
- `wepppy/nodb/core/climate_build_helpers.py`
- `wepppy/climates/daymet/solar_radiation_readme.md`
- `wepppy/climates/cligen/`
- `tests/nodb/test_climate_build_helpers.py`
- `tests/nodb/test_climate_artifact_export_service.py`
- `tests/climate/test_cligen_peak_intensity_contract.py`
- `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/initial_radiation_evidence.md`
- `/workdir/openWEPP/docs/work-packages/20260606-wbval03-snowmelt-wb-closure-defect-closure-001/artifacts/disposition.md`

## Deliverables

- Updated evidence artifact naming the exact mechanism and owner.
- Regression tests for any WEPPpy-owned correction.
- Producer-side code fix or typed fail-closed guard if WEPPpy owns the
  mechanism.
- ADR-backed bounded over-TOA normalization when Daymet source data is proven to
  be the genuine over-bound source.
- Branch-out package or handoff if ownership lies outside WEPPpy.
- Updated package/tracker/ExecPlan and `PROJECT_TRACKER.md` lifecycle entry.

## Follow-up Work

- Resume openWEPP WBVAL03 after regenerating or rebuilding its
  `indispensable-presenter` observed-Daymet climate artifacts with the corrected
  WEPPpy producer.
- Track the separate Daymet interpolation conversion inconsistency noted during
  execution if interpolated observed-Daymet radiation parity becomes a concrete
  blocker; this package only needed the single-location path for the observed
  failure and added the same TOA guard to the interpolated publication helper.

## Kickoff Prompt

- Completed ExecPlan:
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/prompts/completed/daymet_radiation_bounds_execplan.md`
