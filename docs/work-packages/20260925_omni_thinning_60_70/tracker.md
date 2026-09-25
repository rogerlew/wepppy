# Tracker: Omni thinning 60/70

Started 2026-09-25 UTC. Phase: completed code delivery and local validation.
Starting revision: `cf6437095fead72722f91ccc124119c7f824d65e`.

## Progress

- [x] Scope, compatibility, ADR and canonical contract drafted.
- [x] Two independent contract reviews; ancestor `9ed739875` committed.
- [x] Eight assets, five catalogs, CSV, selector and docs.
- [x] Generated artifact/frontend checks pass; broad run executed with baseline failure.
- [x] Independent final reviews and closeout; no package findings.

## Decisions

Retain 65% as a fully supported option to protect existing projects. Keep 40%
default. Reuse static files; no new infrastructure or production mutations.

## Validation progress

- Missing 60/90 catalog regression failed before production edits as expected.
- Focused Python: 308 passed, 12 subtests (41.93s); includes new single/MOFE
  management preparation, archive/restore, catalog snapshot, Omni parser and
  browse/download coverage.
- Frontend: 112 suites/913 tests pass; lint and canonical bundle build pass.
- Compatibility: 16 legacy files byte-identical; every old catalog record and CSV
  byte retained. Eight new files differ from 40% sources only in initial canopy.
- Full Python suite running. Independent correctness/QA review underway.

Implementation committed as `2d0891398` after contract ancestor `9ed739875`.
Both independent reviews approve source/test design with no findings; final
closure waits for the broad suite and expanded soil artifact cases. Existing
80-case Disturbed model-simulation matrix passed within the broad run.

All 230 real soil artifact cases passed within the broad run, including the
32 added 60/70 cases, legacy 65%, mulch and operator overrides. Remaining broader
NoDb tests are running.

## Closeout — 2026-09-25 UTC

Required broad suite stopped after 5,326 passed/54 skipped on the preexisting
single-OFE timeout assertion (60 expected versus 120 implemented). Unchanged
runner/test/ADR Git blobs retained in timeout-baseline-identity.json; later tests
were not executed. Full-suite success is not claimed. All 230 soil artifact cases,
including 32 new cases, passed. Independent source/management/UI/soil review has
zero findings; final dispositions retained in review artifacts.

Code/local delivery complete. Operator owns live browser, production execution
and deployment gates. Repository maintainers own the unrelated timeout test debt.
No production runs were mutated; preserve saved 60/70 hydration during any rollback.
