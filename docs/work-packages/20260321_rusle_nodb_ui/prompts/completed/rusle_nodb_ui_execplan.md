# RUSLE NoDb + UI End-to-End Integration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` were kept current during execution.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Deliver Milestones 6-7 from the RUSLE specification so a disturbed run can enable `rusle`, configure mode controls on the run page, enqueue `build-rusle` through RQ, and get auditable mode-specific artifacts including final `A`. Preflight shows a dedicated Rusle task (`🔱`) and clears completion when climate or SBS changes make results stale.

## Progress

- [x] (2026-03-21) Reviewed required docs/files and mapped LS/K/C, run-page mod rendering, project mod toggle, rq-engine, and preflight surfaces.
- [x] (2026-03-21) Created and activated work-package scaffold (`package.md`, `tracker.md`, active ExecPlan, artifacts dir).
- [x] (2026-03-21) Implemented `Rusle` NoDb controller orchestration (LS/R/K/C/P + final A + selected-mode output behavior + POLARIS/RAP/SBS contracts).
- [x] (2026-03-21) Implemented RQ/API wiring (`build_rusle_rq`, rq-engine `build-rusle` route).
- [x] (2026-03-21) Implemented run-header/run-page/project controller mod-toggle + dynamic section rendering for `rusle`.
- [x] (2026-03-21) Integrated TaskEnum + preflight checklist + TOC/selector mapping and stale invalidation.
- [x] (2026-03-21) Added/updated tests for NoDb behavior, RQ/API wiring, preflight integration, stale invalidation, and UI placement/gating.
- [x] (2026-03-21) Ran required validation gates.
- [x] (2026-03-21) Produced review/QA/final-validation artifacts.
- [x] (2026-03-21) Closed package: archived ExecPlan and synchronized trackers/pointers/spec status.

## Surprises & Discoveries

- Observation: Full-suite route guard checks include two frozen artifacts and a frozen-count assertion in addition to route code.
  Evidence: `tests/tools/test_endpoint_inventory_guard.py`, `tests/tools/test_route_contract_checklist_guard.py`, and `tests/microservices/test_rq_engine_openapi_contract.py` failed until all three were synchronized for `build-rusle`.

- Observation: Existing `scenario_sbs` behavior in `c_integration.py` required no-SBS support changes for this package contract.
  Evidence: The prior implementation required SBS and wrote `sbs_4class.tif`; tests now enforce unburned fallback and no synthetic `sbs_4class.tif` when SBS is absent.

- Observation: Existing K integration wrote both estimator outputs by default.
  Evidence: `k_integration.py` was updated for selected-mode-only output emission in user-facing builds.

## Decision Log

- Decision: Implement a dedicated `Rusle` NoDb facade and use it as the single orchestration surface for route/RQ/UI flows.
  Rationale: Centralizes persisted options, dependency checks, and final artifact behavior.
  Date/Author: 2026-03-21 / Codex.

- Decision: Keep `rusle` eligibility disturbed-gated and keep enable action registration-only.
  Rationale: Matches requested UX contract and avoids unexpected work on toggle.
  Date/Author: 2026-03-21 / Codex.

- Decision: Resolve route-freeze drift in-package rather than deferring as follow-up.
  Rationale: Full-suite closure required contract parity for the new agent-facing route.
  Date/Author: 2026-03-21 / Codex.

## Outcomes & Retrospective

Delivered outcomes:

- New NoDb facade: `wepppy/nodb/mods/rusle/rusle.py`.
- New RQ worker + route:
  - `wepppy/rq/project_rq.py::build_rusle_rq`
  - `wepppy/microservices/rq_engine/rusle_routes.py`
- UI wiring:
  - header toggle + disturbed gating
  - run-page placement after WEPP
  - controller bootstrap/mod updates
  - dedicated Rusle control/template/controller
- Preflight integration:
  - `TaskEnum.build_rusle` (`🔱`)
  - checklist/TOC mapping
  - stale invalidation on climate rebuild and SBS upload/change/removal.
- Contract freeze sync for new route:
  - endpoint inventory
  - route contract checklist
  - frozen agent-route count expectation.

Validation retrospective:

- Required gates passed:
  - `wctl run-pytest tests/nodb --maxfail=1`
  - `wctl run-pytest tests/weppcloud --maxfail=1`
  - `wctl run-npm lint`
  - `wctl run-npm test`
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  - `python3 tools/code_quality_observability.py --base-ref origin/master`
  - `wctl run-pytest tests --maxfail=1` (`2443 passed, 34 skipped`).

- Review/QA artifacts completed with no unresolved high/medium findings:
  - `artifacts/milestone4_review.md`
  - `artifacts/milestone5_qa_review.md`
  - `artifacts/final_validation_summary.md`

## Context and Orientation

Primary implementation surfaces used:

- RUSLE NoDb: `wepppy/nodb/mods/rusle/`
- RQ worker wiring: `wepppy/rq/project_rq.py`
- rq-engine routes: `wepppy/microservices/rq_engine/*.py`
- Mod toggle and run-page surfaces:
  - `wepppy/weppcloud/routes/nodb_api/project_bp.py`
  - `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
  - `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
  - `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
  - `wepppy/weppcloud/controllers_js/project.js`
- Preflight surfaces:
  - `wepppy/weppcloud/static/js/preflight.js`
  - `services/preflight2/internal/checklist/checklist.go`
  - `wepppy/nodb/redis_prep.py`

## Plan of Work

Milestones were executed in order:

1. NoDb Rusle orchestration and substrate contracts.
2. Async route/RQ worker wiring.
3. UI + mod toggle rendering.
4. Preflight task + stale invalidation.
5. Focused tests.
6. Full validation gates + review/QA artifacts + closeout docs.

## Validation and Acceptance

Accepted outcome confirmed:

- `rusle` toggle is disturbed-gated and reveal-only.
- `build-rusle` executes through RQ with standard control UX.
- `scenario_sbs` no-SBS fallback uses unburned parameters and does not emit synthetic `sbs_4class.tif`.
- RAP year selector source is pulled from RAP implementation surface with latest completed year default.
- POLARIS internal acquisition uses explicit Rusle payload and required aligned layer set.
- Preflight Rusle task (`🔱`) appears and clears on climate/SBS invalidation until rebuild.
- Required gates pass.

## Artifacts and Notes

Package artifacts:

- `docs/work-packages/20260321_rusle_nodb_ui/artifacts/milestone4_review.md`
- `docs/work-packages/20260321_rusle_nodb_ui/artifacts/milestone5_qa_review.md`
- `docs/work-packages/20260321_rusle_nodb_ui/artifacts/final_validation_summary.md`

---
Revision Note (2026-03-21, Codex): Plan completed and archived under `prompts/completed/`.
