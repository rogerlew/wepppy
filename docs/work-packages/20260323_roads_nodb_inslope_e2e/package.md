# Roads NoDb Inslope End-to-End Implementation

**Status**: Closed (2026-04-10)

## Overview
This work package plans and then executes the first end-to-end WEPPcloud Roads NoDb integration for inslope road designs (`Inslope_bd`, `Inslope_rd`). The goal is to deliver a complete, queue-backed Roads workflow that starts from uploaded road GeoJSON, produces segment WEPP runs, injects road effects into watershed routing, and exposes observable run-page/preflight/report behavior.

## Objectives
- Implement a first-class `Roads(NoDbBase)` controller with a stable run-scoped persisted state contract (`roads.nodb`).
- Wire Roads enablement through canonical `/tasks/set_mod` with explicit WBT backend gating and no hidden fallback paths.
- Integrate Roads across run header, run page, TOC/preflight, task enum, Flask routes, rq-engine routes, and RQ workers.
- Complete phase-1 segment utility behavior (`Inslope_bd` + `Inslope_rd`), single-OFE run assembly, and pass-file combination per Roads spec.
- Deliver implementation-ready validation gates, including fixture-backed integration/e2e checks on `clogging-starch`.

## Scope
This package includes all implementation and validation work required by `wepppy/nodb/mods/roads/specification.md` for phase-1 inslope Roads integration.

### Included
- Roads controller, API routes, queue workers, and run-page/report integration.
- Mod registration and enable/disable behavior through `set_mod`.
- WBT-only backend guard for Roads enablement.
- Task/preflight wiring (`TaskEnum.run_roads`, emoji `🚗`, checklist key `roads`, TOC selector map).
- Monotonic segment utility parity for both inslope designs plus lowpoint channel/hillslope attribution.
- Single-OFE WEPP road segment run assembly and watershed rerun via pass injection.
- Pass combiner implementation in `wepppyo3` using the phase-1 rules in the Roads specification.
- Roads artifact layout under `wepp/roads/{segments,runs,output}` with watershed reruns launched from `wepp/roads/runs/pw0.run`.
- Queue-governance updates (`wepppy/rq/job-dependencies-catalog.md`, `wctl check-rq-graph`).
- Targeted, integration, and fixture-backed e2e validation.

### Explicitly Out of Scope
- Non-inslope road designs (`Outslope_*`, etc.).
- Exact legacy WEPP:Road 3-OFE parity in phase 1.
- New fallback wrappers that mask missing dependencies or unsupported backends.
- UI redesign beyond required Roads section placement and control/report inclusion.

## Stakeholders
- **Primary**: WEPPcloud users running disturbed watershed scenarios that require Roads impact analysis.
- **Reviewers**: NoDb maintainers, WEPPcloud route/UI maintainers, rq-engine maintainers, `wepppyo3` maintainers.
- **Informed**: Preflight service maintainers, operations owners monitoring queue/job graph drift.

## Success Criteria
- [x] `Roads(NoDbBase)` exists with the specified state contract and lifecycle transitions.
- [x] Roads can be enabled only via `/tasks/set_mod` and returns an explicit error on non-WBT runs.
- [x] Run header `Mods` includes Roads and run page renders Roads immediately after Debris Flow (TOC + content).
- [x] `TaskEnum.run_roads` (`🚗`) and preflight checklist key `roads` are integrated, with Roads completion dependent on WEPP completion.
- [x] Roads API/blueprint routes and rq-engine/RQ jobs execute prepare + run stages asynchronously with observable status updates.
- [x] Segment utility meets inslope parity/invariant requirements from the Roads spec (`topaz_id_chn_lowpoint`, `topaz_id_hill_lowpoint`).
- [x] Single-OFE run assembly and pass combiner produce a successful watershed rerun with all hillslope pass references resolved from `wepp/roads/output`.
- [x] Queue governance checks pass (`wepppy/rq/job-dependencies-catalog.md` updated, `wctl check-rq-graph` clean).
- [x] Required targeted tests, lint/doc checks, and fixture e2e checks pass using `clogging-starch` defaults.

## Dependencies

### Prerequisites
- `wepppy/nodb/mods/roads/specification.md` (canonical behavior/spec contract).
- Existing baseline WEPP outputs for fixture run `clogging-starch` in `/wc1/runs/cl/clogging-starch`.
- WBT delineation backend in fixture/config path (`disturbed9002-wbt-mofe.cfg`).
- `wepppyo3` checkout at `/workdir/wepppyo3` for pass combiner implementation.

### Blocks
- Future Roads phases (non-inslope designs, advanced hydrograph merge) depend on this phase-1 integration.
- Any Roads-related operational rollout depends on queue graph and route-contract governance updates landing with this package.

## Related Packages
- **Depends on**: Roads phase-1 specification (`wepppy/nodb/mods/roads/specification.md`).
- **Related**: `docs/work-packages/20260321_rusle_nodb_ui/` (recent NoDb mod + run-page + preflight integration pattern).
- **Follow-up**: Planned Roads phase-2 package for non-inslope designs and higher-fidelity hydrograph merging.

## Timeline Estimate
- **Expected duration**: 1-2 weeks (implementation + validation).
- **Complexity**: High.
- **Risk level**: High.

## References
- `wepppy/nodb/mods/roads/specification.md` - Canonical Roads phase-1 specification.
- `wepppy/weppcloud/routes/nodb_api/project_bp.py` - Canonical mod toggle endpoint and backend guards.
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` - Run-page mod registry, TOC task mapping, and mod section rendering.
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm` - Header Mods dropdown source.
- `wepppy/nodb/redis_prep.py` - `TaskEnum` and emoji/label contract.
- `services/preflight2/internal/checklist/checklist.go` - Checklist completion logic.
- `wepppy/rq/job-dependencies-catalog.md` - Queue dependency governance artifact.
- `/workdir/wepppyo3/wepp_interchange/src/hill_pass.rs` - Existing pass parser used as combiner foundation.
- Fixture defaults:
  - run id: `clogging-starch`
  - wd: `/wc1/runs/cl/clogging-starch`
  - config: `disturbed9002-wbt-mofe.cfg`
  - roads input: `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
  - DEM: `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Deliverables
- Completed ExecPlan: `prompts/completed/roads_nodb_inslope_e2e_execplan.md`.
- Package tracker with milestones, risks, and validation checklist: `tracker.md`.
- Implemented Roads phase-1 code and tests across NoDb, WEPPcloud, rq-engine, RQ, preflight2, and `wepppyo3`.
- Validation artifacts (e2e logs, review notes, final validation summary) under `artifacts/`.
- Closeout rollback evidence: `artifacts/20260410_closeout_rollback_validation.md`.

## Follow-up Work
- Road designs beyond `Inslope_bd` and `Inslope_rd`.
- Physics-aware hydrograph merge beyond phase-1 approximation rules.
- Additional production hardening from post-implementation telemetry.

## Closure Notes

**Closed**: 2026-04-10

**Summary**: Delivered full Roads phase-1 inslope NoDb integration end-to-end across NoDb controller state/lifecycle, WEPPcloud routes/templates/controllers, rq-engine/RQ queue surfaces, preflight/task wiring, and `wepppyo3` pass combination integration. Post-implementation review remediation and runtime fixes were completed, including watershed rerun pass formatting/staging correctness and queue single-flight protections.

Closeout included explicit rollback validation on `clogging-starch`: `roads` mod disable/enable roundtrip with `roads.nodb` backup/restore hash parity, verification that Roads output/report resource relpaths stay under `wepp/roads/*`, and queue rollback hygiene checks (no active Roads job and no residual submit/runtime lock keys). Targeted rollback-related route/RQ/controller tests were re-run and passing.

**Lessons Learned**: Closeout should reserve explicit time for rollback-path evidence even when implementation and full-gate validation are already complete; capturing this earlier would have reduced lifecycle drift in tracker status.

**Archive Status**: Package remains in `docs/work-packages/20260323_roads_nodb_inslope_e2e/` with tracker, completed ExecPlan, and closeout artifact retained for historical reference.
