# Tracker - SHR-05 Pure UI Unitizer Preferences Contract

## Status

Closed 2026-07-28 UTC.

## Progress

- [x] Registered SHR-05 after SHR-04A, SHR-04B, and SURF-12.
- [x] Ratified the concise rendered/client/route/persistence/reload contract.
- [x] Added direct rendered-template and Unitizer-client regressions.
- [x] Ran and extended Project, route, NoDb, and generated-map evidence.
- [x] Repaired regression-proven mixed/global-selector/event-owner mismatches.
- [x] Completed validation, parent reconciliation, security review, and closeout.

## Decisions

- Preserve every existing conversion formula, precision, category, token, and
  default; this package audits behavior rather than parameterization.
- Treat malformed/unknown preference filtering as compatibility behavior while
  requiring accepted values to persist and reload.

## Validation

- Actual rendered-template suite: 114 passed.
- Unitizer client/map/route/NoDb focused set: 16 passed.
- Project Jest: 1 suite and 31 tests passed.
- Full frontend lint/test: 89 suites and 670 tests passed.
- Broad Python: known unrelated GridMET `_FakeUnits.degC` fixture failure
  recurred after 2,452 passed and 40 skipped.
- Dedicated security review: PASS/SHIP, 0 unresolved findings.
- Documentation and diff gates: passed.
