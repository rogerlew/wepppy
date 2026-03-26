# Features Export WP-5 Runs-Page UI Integration (E2E)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

WP-5 wires the new Features Export mod into the Runs page so users can discover the control in navigation, configure exports with progressive disclosure, submit JSON-only export jobs, and receive canonical async status/results/warnings/stacktrace behavior directly in the run UI. After this work, Features Export should behave like other modernized controls in the dynamic Mods workflow (initial render and runtime mod insertion), while staying aligned with the `features_export` contracts from WP-1..WP-4.

## Progress

- [x] (2026-03-26 20:12Z) Read required context: root `AGENTS.md`, `wepppy/weppcloud/AGENTS.md`, `wepppy/weppcloud/controllers_js/AGENTS.md`, features export `specification.md` (sections 10 and 14.1), and `ui_control_layout.md`.
- [x] (2026-03-26 20:13Z) Created this WP-5 ExecPlan at the required path.
- [x] (2026-03-26 21:05Z) Implemented Runs-page wiring updates (`run_0_bp.py`, `runs0_pure.htm`, `run_page_bootstrap.js.j2`, `_run_header_fixed.htm`, `project.js`) including TOC emoji mapping and dynamic mod definition for runtime `view/mod/<mod_name>` loading.
- [x] (2026-03-26 21:18Z) Added `controls/features_export_pure.htm` with required form id, data hooks, progressive groups, status panel, stacktrace panel, results region, and job-hint surface.
- [x] (2026-03-26 21:39Z) Added `controllers_js/features_export.js` with singleton bootstrap/re-hydration, delegated handlers, JSON script payload parsing, progressive disclosure/validation gating, `Load Defaults` (`gpkg_adjacent`), JSON-only submit, canonical async wiring (`set_rq_job_id` + `FEATURES_EXPORT_TASK_COMPLETED`), status stream attach with polling fallback, and one-fetch-per-cycle jobinfo rendering.
- [x] (2026-03-26 22:05Z) Added/extended tests: `controllers_js/__tests__/features_export.test.js`, `static-src/tests/smoke/controller-cases.js`, `tests/weppcloud/routes/test_pure_controls_render.py`, plus route coverage in `tests/weppcloud/routes/test_project_bp.py` and `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`.
- [x] (2026-03-26 23:09Z) Addressed review-driven medium findings by adding smoke `prepareFeaturesExport` pre-submit setup and focused helper coverage for run-page features-export bootstrap/catalog discovery logic.
- [x] (2026-03-26 23:18Z) Resolved checklist/openapi contract drift from full-suite guards by updating endpoint/checklist artifacts and `tools/rq_engine_contract_rules.py` (including `415` requirement for JSON-only submit contract).
- [x] (2026-03-27 00:02Z) Ran requested validation gates and full test sweep; all commands passed.
- [x] (2026-03-27 00:06Z) Ran `reviewer` + `qa_reviewer` agent loops, fixed all high/medium findings, and confirmed no remaining high/medium findings.
- [x] (2026-03-27 00:10Z) Updated WP-5 status block in `wepppy/nodb/mods/features_export/specification.md` with ExecPlan path/status and implementation clarifications.

## Surprises & Discoveries

- Observation: `run_0` dynamic mod insertion depends on both route-side `MOD_UI_DEFINITIONS` and client-side `Project` bootstrap map, so missing either side causes runtime "mod enabled but no control bootstrapped" behavior.
  Evidence: `run_0_bp.py:view_mod_section` + `project.js:set_mod` + `MOD_BOOTSTRAP_MAP` control bootstrap path.
- Observation: Features Export smoke workflow could not execute without explicit UI pre-selection because submit stays disabled until validation passes.
  Evidence: `controller-regression.spec.js` expects enabled action before click; `features_export` needed new `prepareFeaturesExport` helper in `controller-cases.js`.
- Observation: Full-suite route-contract guards enforce frozen artifact parity beyond WP-5 files; adding new agent-facing routes required synchronized updates to endpoint inventory/checklist and response-rule catalog.
  Evidence: `tests/tools/test_endpoint_inventory_guard.py`, `tests/tools/test_route_contract_checklist_guard.py`, and `tests/microservices/test_rq_engine_openapi_contract.py` failed until artifacts/rules were aligned.

## Decision Log

- Decision: Keep WP-5 data plumbing thin by building deterministic catalog/bootstrap payloads in `run_0_bp.py` from `layer_catalog.yaml` and run filesystem state (Omni/SWAT selectors), without adding new Flask routes.
  Rationale: User scope is UI integration, and existing run-page rendering already provides the right injection surface for script-node payloads.
  Date/Author: 2026-03-26 / Codex
- Decision: Add focused helper tests to `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` (instead of a new test module) for `_build_features_export_catalog_payload`, selector discovery, SWAT discovery, UTM resolution, and bootstrap payload assembly.
  Rationale: Keeps run_0 route bootstrap/render contract tests in one existing suite and closes uncovered medium-risk logic without introducing fragmented route test files.
  Date/Author: 2026-03-26 / Codex
- Decision: Treat `POST /api/runs/{runid}/{config}/export/features` as `rq:export` with required `415` in frozen contract artifacts and response-rule enforcement.
  Rationale: Route implementation and OpenAPI contract are JSON-only; guard artifacts must match canonical behavior to avoid drift and false failures.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

WP-5 is complete. Features Export is now fully wired into Runs-page navigation/sections, dynamic mod loading, and controller bootstrap, with a dedicated control template and a data-driven JS controller that follows canonical async/status contracts.

The implementation delivered all requested surfaces: separate status text/log, job hint, results/warnings, and stacktrace handling; delegated event wiring; progressive disclosure cards; JSON-only submission; and one jobinfo fetch per completion cycle. Runs-page bootstrap now provides catalog/bootstrap payloads (including UTM availability/defaults/selectors) without hardcoded frontend layer maps.

Validation gates and full-suite tests passed after resolving guard drift in frozen contract artifacts. Reviewer and QA reviewer loops were executed; all reported high/medium findings were fixed and both agents confirmed no remaining high/medium findings.

## Context and Orientation

WP-5 touches five run-page integration files plus one new control template and one new controller:
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- `wepppy/weppcloud/controllers_js/project.js`
- `wepppy/weppcloud/templates/controls/features_export_pure.htm` (new)
- `wepppy/weppcloud/controllers_js/features_export.js` (new)

The Runs page supports both initial server render and runtime mod insertion through the Mods menu (`tasks/set_mod` + `view/mod/<mod_name>`). Features Export must work in both modes.

`features_export` backend submit/download contracts already exist in rq-engine (`/rq-engine/api/runs/{runid}/{config}/export/features` and `/download`). WP-5 should consume these contracts, not redefine them.

## Plan of Work

First, wire `features_export` as a first-class mod in the run route/template/bootstrap/header/project stacks, including preflight TOC emoji mapping and dynamic mod bootstrap.

Second, add a new control template with the required DOM/data hook contract and script-node JSON payloads (`catalog` + `bootstrap`). The template will expose separate regions for status text, job hint, warnings/results, and stacktrace.

Third, implement `features_export.js` as a modern singleton controller: delegated handlers only, robust bootstrap re-hydration, progressive disclosure and validation gating, `Load Defaults` profile application, JSON-only submit, canonical `set_rq_job_id` + `poll_completion_event="FEATURES_EXPORT_TASK_COMPLETED"`, and status stream attachment on `features_export` with polling fallback.

Fourth, add targeted tests (Jest + smoke case config + route/template invariants) and run the requested validation suite.

Finally, run reviewer loops, apply fixes, then update this plan and the feature specification WP-5 status.

## Concrete Steps

From `/workdir/wepppy`:

1. Implement run-page wiring and payload helpers.
2. Add `wepppy/weppcloud/templates/controls/features_export_pure.htm`.
3. Add `wepppy/weppcloud/controllers_js/features_export.js`.
4. Add/update tests:
   - `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`
   - `wepppy/weppcloud/static-src/tests/smoke/controller-cases.js`
   - `tests/weppcloud/routes/test_pure_controls_render.py`
5. Run validation gates:
   - `wctl run-npm lint`
   - `wctl run-npm test -- features_export`
   - `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
   - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
   - `wctl check-test-stubs` (if Python public surfaces changed)
   - `wctl run-pytest tests --maxfail=1` (if feasible)
6. Run reviewer + qa_reviewer agent loops; resolve high/medium findings.
7. Update WP-5 status in `wepppy/nodb/mods/features_export/specification.md` and finalize this ExecPlan.

## Validation and Acceptance

WP-5 is accepted when:
- Features Export appears as a Runs-page mod with nav and section placement.
- Dynamic mod insertion via Mods menu loads the control and bootstraps the controller.
- Template satisfies required DOM hooks/groups from `ui_control_layout.md`.
- Controller uses JSON-only submit, canonical async contracts, and status stream with polling fallback.
- Completion fetches `jobinfo` once per completion cycle and renders result/warning metadata.
- Requested validation commands and reviewer loops complete with no open high/medium findings.

## Idempotence and Recovery

All changes are additive and safe to rerun. If a validation step fails, patch the relevant files and rerun only failing targeted commands first, then rerun the requested command set.

## Artifacts and Notes

Validation commands executed (all pass):
- `wctl run-npm lint`
- `wctl run-npm test -- features_export`
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl check-test-stubs`
- `wctl run-pytest tests --maxfail=1`

Reviewer outcomes:
- `reviewer` agent: reported one medium checklist contract mismatch; fixed via checklist/rules alignment; re-review reported no high/medium findings.
- `qa_reviewer` agent: reported two medium items (smoke pre-submit prep missing; uncovered run_0 helper logic); fixed via `prepareFeaturesExport` and new route-helper tests; re-review reported no high/medium findings.

## Interfaces and Dependencies

No new external dependencies are planned. WP-5 relies on existing WEPPcloud helpers (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`, `WCControllerBootstrap`) and existing rq-engine features export endpoints.

## Revision Notes

- 2026-03-26 (Codex): Created WP-5 ExecPlan with implementation sequence, validation gates, and reviewer loop requirements.
- 2026-03-27 (Codex): Marked implementation complete; recorded delivered wiring/template/controller/tests, review-loop fixes, guard-artifact alignments, and final validation outcomes.
