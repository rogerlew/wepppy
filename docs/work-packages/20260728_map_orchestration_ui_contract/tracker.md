# Tracker - Map Orchestration Controller Contract

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 UTC
**Current phase**: Closed
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for current test/documentation scope; re-triage any
production route change.

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Registered and scoped DOM-04A as one controller audit (2026-07-28 UTC).
- [x] Added actual-render action/target evidence and exact run-scoped elevation
  request evidence (2026-07-28 UTC).
- [x] Confirmed existing coordinate, ID-search, drilldown, elevation-service,
  and report-route behavior conforms; no production patch was needed
  (2026-07-28 UTC).
- [x] Passed focused Python tests, frontend lint, focused Map Jest, full
  frontend tests, and documentation lint (2026-07-28 UTC).
- [x] Ran the full Python suite; it stopped on an unrelated GridMET test
  harness failure after 2,451 passes (2026-07-28 UTC).

## Decisions Log

### 2026-07-28 UTC: Keep DOM-04A orchestration-only

**Decision**: Audit only map host/search, coordinate navigation, elevation, and
drilldown. Leave layer, scale, legend, remote-resource, and feature UI behavior
to DOM-04B.

**Impact**: The tests exercise the user-visible orchestration seam without
duplicating the helper package or expanding into public-route changes.

### 2026-07-28 UTC: Close without a production repair

**Decision**: Retain the two direct regressions and make no production change.

**Impact**: DOM-04A now proves the rendered action identities and exact
elevation request contract. Controller generation, RQ graph validation, and
production/security review are not applicable.

### 2026-07-28 UTC: Do not broaden DOM-04A for the full-suite GridMET failure

**Decision**: Record but do not repair the failing GridMET fake-units fixture.

**Rationale**: `tests/nodb/test_climate_gridmet_multiple_build_service.py` uses
`_FakeUnits` without `degC`; the failure occurs in
`wepppy/climates/gridmet/client.py` and is unrelated to Map template,
controller, elevation, or drilldown behavior.

**Impact**: DOM-04A closes on its passing focused gates. A climate owner should
repair the fixture/client compatibility separately before the repository-wide
Python gate can pass.

## Verification Checklist

- [x] Actual-render map action and target evidence passes.
- [x] Map controller coordinate/search/drilldown and exact elevation payload
  evidence passes.
- [x] Elevation microservice and report route tests pass.
- [x] Frontend lint and the full frontend suite pass after Jest test changes.
- [x] Full Python suite result recorded: 2,451 passed, 40 skipped, then one
  unrelated GridMET fake-units failure in 417.76 seconds.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] RQ graph validation is N/A: no queue wiring changed.
- [x] Production and security reviews are N/A: no production patch was made.
