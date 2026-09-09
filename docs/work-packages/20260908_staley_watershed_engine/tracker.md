# Staley watershed/engine tracker

Status: scaffolded, not started. Baseline: `923377a04`; scope documentation
changes are uncommitted at scaffolding. Timestamp: 2026-09-09 04:18 UTC.

## Task board

- [x] Record owner-selected single project watershed/outlet scope in ADR-0055,
  specification and roadmap; scaffold this package.
- [ ] Resolve numerical decision register; write canonical engine contract/ADR.
- [ ] Check publication coefficients independently and audit existing watershed
  mask/grid/outlet authority using read-only project fixtures.
- [ ] Implement pure engine and independent analytical/edge-case tests.
- [ ] Generate inspectable example outputs and obtain correctness review.
- [ ] Pass focused/full tests, update current docs, archive plan with outcomes.

## Decisions and blockers

2026-09-09 04:18 UTC: user selected the existing project watershed and outlet;
users manually isolate suspected burned basins. Nested catchments are excluded.
Scaffolding does not approve pending numerical defaults. See
[decision register](artifacts/decision_register.md). Source verification and
artifact inventory can proceed independently when execution is requested.

## Evidence and next steps

No implementation, tests, generated model outputs, or deployment in this
scaffold. Next agent starts with the active
[ExecPlan](prompts/active/watershed_engine_execplan.md), verifies the working
revision, and resolves the numerical contract before adding executable logic.
Maintain this tracker and the module roadmap at every handoff.
