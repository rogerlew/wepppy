# Partial-Year Climate and CLIGEN NAS Hardening

**Status**: Closed (2026-07-27)
**Timezone**: UTC

## Overview

This incident package restores complete WEPP climate years when current-year
GridMET or Daymet products contain a trailing unpublished-data interval. It
also prevents parallel multiple-interpolated climate builders from exposing a
partially copied CLIGEN station parameter file on slow NAS storage.

## Objectives

- Preserve a complete 365/366-day CLI while overlaying only finite observed
  values and retaining CLIGEN-generated values for the unpublished suffix.
- Reject internal missing-data holes instead of treating them as future
  publication lag.
- Finalize the shared station `.par` file before either the Daymet or GridMET
  multiple-interpolated CLIGEN process pool starts.
- Add exact regressions for the production failure signatures and complete
  independent code and QA reviews with findings disposition.

## Scope

### Included

- GridMET multiple-interpolated source-array missingness and CLI overlay logic.
- Shared observed-variable overlay validation used by Daymet and GridMET
  interpolated builders.
- Parent-process atomic station-file staging for both multiple-interpolated
  paths.
- Focused NAS-concurrency controls only where evidence supports them.
- Tests, ADR, durable climate documentation, validation, and review artifacts.

### Explicitly Out of Scope

- Guessing or synthesizing observed dewpoint, humidity, wind, or radiation.
- Weakening `ClimateFile.replace_var` NaN rejection.
- Changing single-location observed climate paths without a reproduced need.
- Production deployment, run mutation, or automatic retry of
  `mdobre-undimmed-cellulite`.

## Stakeholders

- **Primary**: WEPPpy maintainers and WEPPcloud operators.
- **Reviewers**: Independent code reviewer and independent QA reviewer.
- **Informed**: Users building current-year spatial observed climates.

## Success Criteria

- [x] A current-year GridMET multiple build treats unpublished source cells as
  missing rather than observed zero.
- [x] CLIGEN receives missing sentinels and emits a full calendar-year CLI.
- [x] Finite observed values replace generated values independently by
  variable; the trailing missing suffix remains generated.
- [x] An internal NaN hole fails with the variable and date in the error.
- [x] Daymet and GridMET multiple builds finalize the station `.par` before
  worker submission.
- [x] Targeted tests and the repository pre-handoff test gate pass or have an
  evidence-backed unrelated failure disposition.
- [x] Code and QA review findings are fully dispositioned.

## Compatibility and Regression Plan

Generated CLI filenames, NoDb keys, parquet columns, PRN columns, and
`sub_cli_fns`/`sub_par_fns` mappings remain unchanged. Complete historical
years remain byte-semantically equivalent apart from station staging timing.
For a partial current year, future zero overlays are replaced by existing
CLIGEN-generated values; finite observations remain authoritative. Regression
tests cover generated full-year length, trailing suffix preservation, internal
hole rejection, pre-pool station staging, and both Daymet/GridMET call paths.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link**:
  `docs/adrs/ADR-0026-partial-year-observed-climate-restoration.md`
- **Decision provenance captured**: yes

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: This changes run-scoped generated climate artifacts and
  local subprocess input staging without adding routes, auth behavior, secrets,
  queue wiring, external egress, or user-controlled path handling.

## Hardening Contract

- **Failure signatures**:
  - `replace_var received NaN value for colname='tdew' ... 2026-07-24`
  - `Fortran runtime error: End of file` while CLIGEN reads `id108062.par`
- **Scope freeze**: Repair partial-year overlay and shared station staging in
  multiple-interpolated Daymet/GridMET paths without redesigning climate
  retrieval or CLIGEN.
- **Hypothesis**: If unpublished suffixes remain missing until CLIGEN fills
  them and the station file is atomically finalized before worker creation,
  these two signatures will disappear without reducing CLI year completeness.
- **Health signals**: full-year CLI row counts, no emitted NaNs, no station-file
  EOF logs, and no operator retry required for the target signatures.
- **Danger signals**: observed dates replaced by generated data, internal gaps
  silently accepted, new NAS retries/delays, or incomplete CLI years.
- **Observation window**: 30 days after production deployment.
- **Temporary calluses**: none planned; a worker cap is accepted only as an
  explicit performance control, not a correctness dependency.

## Related Work

- `docs/standards/hardening-lifecycle-standard.md`
- `docs/mini-work-packages/20260501_cligen_observed_quality_guard_silent_pass_execplan.md`
- `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/`
- `docs/mini-work-packages/completed/20260220_nodb_climate_option2_facade_execplan.md`

## Deliverables

- Shared climate overlay and station-staging implementation.
- Exact unit/integration regression coverage.
- ADR-0026 and updated climate developer documentation.
- Code-review, QA-review, and validation artifacts.

## Closure

Implementation and focused validation are complete. Independent code and QA
reviews produced actionable findings; every finding was fixed and covered by a
regression. The full repository gate has one reproduced, unrelated usersum
baseline failure documented in the validation artifact. Production deployment,
the failed-run retry, and the 30-day observation window remain operator work.
