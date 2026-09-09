# Staley project watershed and numerical engine

Status: complete, 2026-09-09 UTC; offline watershed contract and engine.
Roadmap stages 1–2, with spatial predictor production reserved for stage 3.

## Purpose and scope

Deliver a tested local Python M1/M3 probability and rainfall-threshold engine
for supplied watershed predictors. Document and verify how the existing WBT
project delineation and resolved outlet supply one assessment domain. Users
manually isolate suspected burned basins when creating projects; this package
adds no nested catchment selection or new delineation workflow.

Read the [ExecPlan](prompts/completed/watershed_engine_execplan.md),
[tracker](tracker.md), and [decision register](artifacts/decision_register.md).
Current authority: the module [specification](../../../wepppy/nodb/mods/postfire_debris_flow/specification.md)
and [ADR-0055](../../adrs/ADR-0055-staley-project-watershed-scope.md).
The [roadmap](../../../wepppy/nodb/mods/postfire_debris_flow/implementation_roadmap.md)
tracks downstream integration.

## Deliverables and acceptance

- Canonical watershed/outlet artifact mapping, including mask support and
  existing-grid identity, established by repository inspection and read-only
  evidence from existing project fixtures. No new catchment enumeration.
- Independently checked publication coefficients and numerical contract/ADR
  before executable implementation. Resolve numerical decisions in the register.
- Pure `staley2017.py` interface and independently authored tests for both
  models, all three durations, forward/inverse consistency and numerical edges.
- Reproducible generated example results, focused/full validation, and an
  independent correctness review. Update specification and roadmap together.

This is a real offline numerical deliverable, not a production-ready model.
No new raster aggregation engine, Soils/RUSLE rebuild, climate adapter, network
acquisition, NoDb state, public API, upload, queue, UI, or deployment. No copying
or translating GPL pfdf code, tests, or documentation. Use published equations.

## Gates and handoff

Security impact: `none` for the proposed in-memory numerical library and docs;
read-only inspection uses existing trusted fixtures. New file readers/writers,
subprocess wrappers, or public transport require fresh triage and scope review.
Independent correctness review is required before closure. A dedicated security
artifact is required if scope changes to a high-impact surface.

The owner requested execution and container checks with WBT at
`/workdir/weppcloud-wbt`.
N01–N04 are owner-approved in the detailed engine contract and ADR-0056. UI/NoDb/RQ work is outside scope and would
require the separately approved, reviewed, committed contract checkpoint.
The successor M1 predictor package implements slope/SBS/K aggregation; the
rainfall/results package consumes this engine. Do not close those stages here.

## Outcome

Delivered canonical watershed artifact mapping, accepted ADR-0056/engine
contract, pure scalar M1/M3 forward/inverse API, synthetic examples and
independent correctness review with zero unresolved findings. Final focused
validation: 145 passed. Full suite: 7,959 passed, 72 skipped. See
[validation evidence](artifacts/validation.md). Roadmap stages 1–2 are complete;
project predictor production and all production integration remain pending.
