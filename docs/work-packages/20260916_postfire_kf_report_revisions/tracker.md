# Kf and rainfall-response revisions tracker

Status: **Complete**, 2026-09-16 UTC. Development acceptance on forest.
Contract ancestor: `9395f4722`. Implementation: `d5646ca95`.
No push or production deployment. Unrelated workspace changes were preserved.

## Completed milestones

- [x] M1: resolve supported Kf field, units, aggregation and source evidence.
- [x] M2: canonical contracts, two independent reviews and ancestor checkpoint.
- [x] M3: wire attempt-owned Kf/schema 3 and remove new-run RUSLE coupling.
- [x] M4: curve, P50, numeric/CSV equivalent and rainfall-origin labels.
- [x] M5: regression, actual source/worker/browser, independent reviews and archive.
- [x] Mandatory live gate: restart forest, verify updated services, run
  nervous-mesquite through UI/RQ and check report/export/reload and protected inputs.
- [x] M6: durable documentation, review disposition and implementation closeout.

## Decisions and rationale

Owner's 2026-09-16 execution/completion direction superseded scaffold-only limits
and authorized required reviews/commits plus the forest restart and named run.
Restart and end-to-end verification are explicit completion gates, not follow-ups.
No other existing project mutation or host deployment was inferred.

New M1 consumes original USSOILS KFFACT through the approved USGS COG. Original
field/aggregation metadata and 301,379 exact polygon/raster comparisons resolve
the publisher's incorrect conductivity label. Preserve that discrepancy; do not
claim a publisher correction. Do not fit the historical Thomas Kf scalar.

Durable policy and rationale: module `docs/kf_source.md`, ADR-0068 and the
2026-09-16 report/control contract amendments. New attempts own fresh receipts,
rasters and predictor bundles. Legacy M1 remains honestly POLARIS-labeled; M3,
delineation, equations and standalone RUSLE are preserved.

## Acceptance evidence

- [Restart and recovery](artifacts/forest_restart_validation.md): idle queues,
  rebuilt preflight/UI, full stack restart, Redis-loading recovery and health.
- [Named acceptance](artifacts/nervous_mesquite_e2e.md): attempt
  `0ea9c1f5b0964b22ba7f1b457c1a6c9f`, Kf 0.139396 and I15=24 probability 72.19%.
- [Generic/M3 acceptance](artifacts/generic_e2e.md): actual no-RUSLE source/worker
  workflow, immediate/two-reload removal checks, unchanged legacy M3 report.
- [Validation](artifacts/validation.md): full pytest 8,693 passed / 103 skipped;
  frontend 112 suites / 899 tests; targeted source, routes, Go, stubs and archive.
- [Final disposition](artifacts/final_review_disposition.md): correctness,
  security, dedicated UX and root QA pass; zero unresolved findings.
- Actual generated records survive canonical archive/restore: 137 named-run files
  and 62 fixture files. Protected scientific inputs and prior attempts preserved.

## Retrospective

The earlier scaffold/checkpoint was not delivered functionality. Completion now
requires evidence from restarted web/workers and normal browser actions. The
first browser harness watched the legacy run URL, then resumed the actual new
job rather than rerunning a successful assessment. Retained diagnostics distinguish
harness/setup failures from model failures. Preflight's Redis-LOADING startup
retry is a small separate follow-up; recovery here needed no data reset.
