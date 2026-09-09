# Staley watershed/engine tracker

Status: complete, 2026-09-09 UTC; offline scope only. Execution baseline:
`db03285e986c7d42afb65434429e02eff66a2b48`, initially clean working tree.
Completion date: 2026-09-09 UTC.

## Task board

- [x] Record owner-selected single project watershed/outlet scope in ADR-0055,
  specification and roadmap; scaffold this package.
- [x] Resolve numerical decision register; write canonical engine contract/ADR.
- [x] Check publication coefficients independently and audit existing watershed
  mask/grid/outlet authority using read-only project fixtures.
- [x] Implement pure engine and independent analytical/edge-case tests.
- [x] Generate inspectable example outputs and obtain correctness review.
- [x] Pass focused/full tests, update current docs, archive plan with outcomes.

## Decisions and blockers

2026-09-09 04:18 UTC: user selected the existing project watershed and outlet;
users manually isolate suspected burned basins. Nested catchments are excluded.
2026-09-09 UTC: owner explicitly approved N01–N04 in the detailed contract;
ADR-0056 records numerical policies before implementation. Independent review
found adjacent-intercept cancellation and inverse underflow, both resolved
with exact reachability checks, stable log-odds and explicit unavailability.

## Evidence and next steps

Publication equations and all six coefficient rows match the local manuscript.
The container audit confirms 49,917 watershed cells, outlet inclusion, matching
grid/polygon/subcatchment support and unchanged hashes. See
[coefficient check](artifacts/coefficient_check.md),
[watershed audit](artifacts/watershed_artifact_audit.md), and
[validation](artifacts/validation.md).

Use container `wctl run-python` and `wctl run-pytest`, with WBT at
`/workdir/weppcloud-wbt`, per owner direction. Final focused suite: 145 passed;
independent reviewer also checked 108 Decimal branch-boundary cases. API/stub
and docs checks pass. Full suite: 7,959 passed, 72 skipped (791.10 s).
Generated synthetic examples cover all six rows and unavailable/nonunique
outcomes. Independent review has no open findings. Roadmap stages 1–2 are
complete and the plan is archived under `prompts/completed/`. Successors retain
predictor, rainfall/results and production workflow responsibilities.
