# Mini Work Package: WEPP Prep-Only Button and Input-Only Pipeline ExecPlan
Status: Completed
Last Updated: 2026-03-04
Primary Areas: `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/wepp_bin.htm`, `wepppy/weppcloud/controllers_js/wepp.js`, `wepppy/weppcloud/static/js/controllers-gl.js`, `wepppy/microservices/rq_engine/wepp_routes.py`, `wepppy/rq/wepp_rq.py`, `wepppy/rq/wepp_rq_pipeline.py`, `wepppy/rq/wepp_rq_stage_finalize.py`, `tests/microservices/test_rq_engine_wepp_routes.py`, `tests/microservices/test_rq_engine_openapi_contract.py`, `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js`, `tests/rq/test_wepp_rq_pipeline.py`, `tests/rq/test_bootstrap_autocommit_rq.py`, `wepppy/rq/job-dependencies-catalog.md`, `wepppy/rq/job-dependency-graph.static.json`, `tools/rq_engine_contract_rules.py`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`, `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users currently need WEPP run files under `wepp/runs/` so they can edit those inputs before execution, but the current UI flow forces a full WEPP run first. That wastes time and produces outputs users immediately discard.

After this change, users can click a new `Prep Only` button above `Run WEPP Watershed` in the WEPP Exec card. The system will build hillslope and watershed run inputs (`wepp/runs/*`) without running hillslope or watershed WEPP executables. This enables an edit-first workflow and avoids waiting for throwaway model outputs.

## Progress

- [x] (2026-03-03 23:40Z) Mapped current button/template, controller actions, rq-engine routes, RQ entrypoints, and pipeline stages for full-run and no-prep flows.
- [x] (2026-03-03 23:55Z) Authored this mini-work-package ExecPlan with concrete file-level implementation and validation steps.
- [x] (2026-03-03 07:43Z) Milestone 1 complete: added `prep-wepp-watershed` rq-engine route, `prep_wepp_watershed_rq`, prep-only pipeline, prep-only finalize event, and stub updates.
- [x] (2026-03-03 07:55Z) Milestone 2 complete: added `Prep Only` button, controller action/delegate wiring, prep-only completion event handling, bootstrap job-id restoration, and rebuilt `controllers-gl.js`.
- [x] (2026-03-03 08:03Z) Milestone 3 complete: extended pytest/Jest coverage for prep-only route, prep-only queue graph, prep-only finalize semantics, and frontend prep-only interaction/completion.
- [x] (2026-03-03 08:10Z) Milestone 4 complete: updated queue dependency artifacts after `wctl check-rq-graph` drift report by running `python tools/check_rq_dependency_graph.py --write`, then re-validated with `wctl check-rq-graph`.
- [x] (2026-03-03 08:18Z) Milestone 5 complete: ran required validation commands and captured outcomes.
- [x] (2026-03-04 05:57Z) Route-contract parity fixes complete for new endpoint (`endpoint_inventory_freeze_20260208.md`, `route_contract_checklist_20260208.md`, `test_rq_engine_openapi_contract.py`), followed by clean full-suite validation.

## Surprises & Discoveries

- Observation: Existing WEPP completion handling always assumes a model run completed and triggers report refresh.
  Evidence: `wepppy/weppcloud/controllers_js/wepp.js` handles `WEPP_RUN_TASK_COMPLETED` by calling `wepp.report()` and `Observed.getInstance().onWeppRunCompleted()`.

- Observation: Existing finalize stage unconditionally timestamps `TaskEnum.run_wepp_watershed`.
  Evidence: `wepppy/rq/wepp_rq_stage_finalize.py::_log_complete_rq` always calls `prep.timestamp(TaskEnum.run_wepp_watershed)`.

- Observation: Run-results staleness depends on `timestamps:run_wepp_watershed`.
  Evidence: `wepppy/weppcloud/routes/nodb_api/wepp_bp.py::_wepp_results_invalidated` compares build timestamps against `run_wepp_watershed` (or legacy `run_wepp`).

Implication: prep-only completion must not reuse run-complete semantics, otherwise stale-output detection and UI lifecycle events become incorrect.

- Observation: `wctl run-npm test -- wepp` currently executes many cross-controller suites and fails on pre-existing call-signature expectation drift (`jobinfo` fetch now includes an options argument), not just WEPP-prep changes.
  Evidence: failures across multiple controller suites all report expected `"/rq-engine/api/jobinfo/job-123"` vs received `"/rq-engine/api/jobinfo/job-123", {"params": undefined}`.

- Observation: broad pytest guardrails include route-freeze and checklist parity tests, so adding an rq-engine endpoint requires synchronized updates to inventory/checklist artifacts and frozen route-count expectations.
  Evidence: initial `wctl run-pytest tests --maxfail=1` failed at `tests/microservices/test_rq_engine_openapi_contract.py::test_frozen_agent_route_count_is_expected` and `tests/tools/test_route_contract_checklist_guard.py::test_route_contract_checklist_guard_reports_no_drift` until those artifacts were updated.

## Decision Log

- Decision: Add a dedicated prep-only rq-engine endpoint and dedicated RQ entrypoint/pipeline, rather than overloading existing run routes.
  Rationale: Avoids ambiguous behavior switches and keeps run-vs-prep contracts explicit.
  Date/Author: 2026-03-03 / Codex.

- Decision: Add a dedicated prep-only completion event (`WEPP_PREP_TASK_COMPLETED`) and finalize path that does not set `run_wepp_watershed` timestamps.
  Rationale: Prevents false "run complete" semantics in controller/UI and stale-result logic.
  Date/Author: 2026-03-03 / Codex.

- Decision: Prep-only path should execute both hillslope prep and watershed prep stages, and must not execute `_run_hillslopes_rq`, `run_watershed_rq`, or post-run interchange/export stages.
  Rationale: Matches feature request: generate `wepp/runs/*` inputs only.
  Date/Author: 2026-03-03 / Codex.

- Decision: Route will continue to parse and persist WEPP run-option payload fields before enqueue, consistent with existing run routes.
  Rationale: Users expect option selections in the UI to apply to generated input files.
  Date/Author: 2026-03-03 / Codex.

- Decision: Prep-only completion should keep status-stream teardown and completion-event idempotency, but must not trigger `wepp.report()` or `Observed.onWeppRunCompleted()`.
  Rationale: Preserves existing run lifecycle behavior while preventing false run-complete side effects.
  Date/Author: 2026-03-03 / Codex.

## Outcomes & Retrospective

Implementation outcome:
- Backend: added dedicated prep-only enqueue surface and queue path that stops at prep stages and emits `WEPP_PREP_TASK_COMPLETED`.
- Frontend: added `Prep Only` control and prep-only completion handling that avoids report refresh/run-complete callbacks.
- Tests: added regression coverage for route enqueueing, prep-only pipeline composition, prep-finalize semantics, and controller prep-only behavior.
- Queue artifacts: initial drift detected, regenerated, and re-validated (`wctl check-rq-graph` pass after `python tools/check_rq_dependency_graph.py --write`).

Validation retrospective:
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`: pass.
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py --maxfail=1`: pass.
- `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1`: pass.
- `wctl run-npm test -- wepp`: fail (pre-existing cross-suite expectation drift on `jobinfo` call signature; includes updated WEPP suite run).
- `wctl run-npm lint`: pass.
- `wctl check-rq-graph`: pass (`RQ dependency graph artifacts are up to date`).
- `wctl run-pytest tests --maxfail=1`: pass (`2176 passed, 29 skipped`), after route-contract parity updates for the new prep-only endpoint.
- `wctl doc-lint --path docs/mini-work-packages/20260303_wepp_prep_only_button_execplan.md`: pass.

## Context and Orientation

This feature crosses four surfaces:

1. UI template and controller action wiring.
`wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/wepp_bin.htm` currently contains `Run WEPP Watershed`.
`wepppy/weppcloud/controllers_js/wepp.js` currently wires `run`, `run-watershed`, `run-noprep`, and `run-watershed-noprep`.

2. rq-engine route for enqueueing WEPP jobs.
`wepppy/microservices/rq_engine/wepp_routes.py` currently parses payloads, mutates NoDb state, resets run timestamps, and enqueues `run_wepp_rq` or `run_wepp_watershed_rq`.

3. RQ orchestration and dependency graph.
`wepppy/rq/wepp_rq.py` contains orchestrators.
`wepppy/rq/wepp_rq_pipeline.py` defines enqueue graphs for full run and no-prep variants.
`wepppy/rq/wepp_rq_stage_prep.py` already has all prep primitives needed for hillslope + watershed input generation.

4. Completion semantics and status events.
`wepppy/rq/wepp_rq_stage_finalize.py` currently emits run-completion trigger and timestamps.
`wepppy/weppcloud/controllers_js/wepp.js` currently treats run completion as output-ready and refreshes report panels.

Terminology used in this plan:

- "Prep-only" means generating WEPP input artifacts in `wepp/runs/` only.
- "Run-complete event" means status-stream trigger currently named `WEPP_RUN_TASK_COMPLETED`.
- "Prep-complete event" means new status-stream trigger for this feature that signals input generation completed without model execution.

## Plan of Work

### Milestone 1: Backend prep-only contract and queue path

Add a new authenticated rq-engine endpoint that reuses current WEPP payload parsing/mutation flow, but enqueues a new prep-only RQ function. Add a new RQ pipeline that stops after `_prep_watershed_rq` and finalizes with a prep-complete trigger.

At the end of this milestone, the backend can enqueue and execute a prep-only job graph that builds hillslope and watershed run inputs without WEPP execution.

### Milestone 2: Frontend button and completion behavior

Add `Prep Only` button markup directly above the existing `Run WEPP Watershed` button. Wire a new controller action to call the new endpoint and poll on prep-complete trigger. Extend completion handling so prep completion does not call WEPP report fetch.

At the end of this milestone, users can trigger prep-only from the WEPP Exec card and see correct completion status without fake run-complete side effects.

### Milestone 3: Regression tests

Extend Python and Jest suites to lock down route contract, queue graph shape, and controller behavior. Ensure tests explicitly verify no run-stage functions are enqueued in prep-only pipelines.

At the end of this milestone, the new behavior is covered and existing run/no-prep behavior remains intact.

### Milestone 4: Queue catalog/graph and final validation

Because enqueue sites/dependency edges change in `wepppy/rq/*.py` and rq-engine routes, update queue artifacts and run required graph checks. Run targeted and broad validation gates.

At the end of this milestone, queue documentation and verification tools are in sync with code.

## Plan of Work: File-Level Edits

1. `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/wepp_bin.htm`
Add a new button immediately above `Run WEPP Watershed`:
- label: `Prep Only`
- action hook: `data-wepp-action="prep-watershed"`
- id: `btn_prep_wepp_watershed` (or equivalent consistent naming).

2. `wepppy/microservices/rq_engine/wepp_routes.py`
Add endpoint:
- `POST /runs/{runid}/{config}/prep-wepp-watershed`
- operation id `prep_wepp_watershed` (via `rq_operation_id(...)`)
- route helper call should parse the same relevant WEPP fields used for hillslope/watershed prep generation.
- enqueue new job function with key `prep_wepp_watershed_rq`.

3. `wepppy/rq/wepp_rq.py`
Add new orchestrator:
- `prep_wepp_watershed_rq(runid: str) -> Job`
- include lock checks and prerequisite setup analogous to existing run orchestrators.
- enqueue new prep-only pipeline function.
- publish status messages to `runid:wepp`.

4. `wepppy/rq/wepp_rq_pipeline.py`
Add new graph builder function, for example:
- `enqueue_wepp_prep_only_pipeline(...)`
- enqueue only:
  - `_prep_multi_ofe_rq` or (`_prep_slopes_rq`, `_prep_managements_rq`, `_prep_soils_rq`)
  - `_prep_climates_rq`
  - `_prep_remaining_rq`
  - `_prep_watershed_rq`
  - prep-only finalize job
- do not enqueue run stages, interchange, or post-run exports.

5. `wepppy/rq/wepp_rq_stage_finalize.py`
Add prep-only finalize function, for example `_log_prep_complete_rq(...)`:
- emits `TRIGGER   wepp WEPP_PREP_TASK_COMPLETED`
- does not timestamp `TaskEnum.run_wepp_watershed`
- may still support bootstrap auto-commit of inputs (explicitly controlled).

6. Type stubs (required for new callable surfaces):
- `wepppy/rq/wepp_rq.pyi`
- `wepppy/rq/wepp_rq_pipeline.pyi`
- `wepppy/rq/wepp_rq_stage_finalize.pyi`
- `stubs/wepppy/rq/wepp_rq.pyi`

7. `wepppy/weppcloud/controllers_js/wepp.js`
Add:
- new action method `prepWatershedOnly()` posting to `prep-wepp-watershed`.
- delegate binding for `[data-wepp-action="prep-watershed"]`.
- completion handling for `WEPP_PREP_TASK_COMPLETED` that:
  - disconnects status stream cleanly,
  - emits prep-only completion event(s),
  - does not call `wepp.report()` or observed-run completion callbacks.
- bootstrap job-id restoration for `prep_wepp_watershed_rq`.

8. Rebuild compiled controller bundle:
- regenerate `wepppy/weppcloud/static/js/controllers-gl.js`.

9. Queue docs/graph artifacts:
- `wepppy/rq/job-dependencies-catalog.md`
- `wepppy/rq/job-dependency-graph.static.json` (if drift reported).

## Concrete Steps

Run from `/workdir/wepppy` unless noted.

1. Implement backend prep-only route and RQ orchestration:

    Edit `wepppy/microservices/rq_engine/wepp_routes.py`.
    Edit `wepppy/rq/wepp_rq.py`.
    Edit `wepppy/rq/wepp_rq_pipeline.py`.
    Edit `wepppy/rq/wepp_rq_stage_finalize.py`.
    Edit associated `.pyi` and `stubs/` declarations.

2. Implement UI button and controller behavior:

    Edit `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/wepp_bin.htm`.
    Edit `wepppy/weppcloud/controllers_js/wepp.js`.
    Rebuild bundle:

    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py

3. Add tests:

    Edit `tests/microservices/test_rq_engine_wepp_routes.py`.
    Edit `tests/rq/test_wepp_rq_pipeline.py`.
    Edit `tests/rq/test_bootstrap_autocommit_rq.py` (or add focused RQ tests if cleaner).
    Edit `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js`.

4. Update queue graph docs and verify:

    wctl check-rq-graph

    If drift is reported:

    python tools/check_rq_dependency_graph.py --write

5. Run targeted tests and checks:

    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py --maxfail=1
    wctl run-pytest tests/rq/test_wepp_rq_pipeline.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1
    wctl run-npm test -- wepp
    wctl run-npm lint

6. Run broader confidence gates before handoff:

    wctl run-pytest tests --maxfail=1
    wctl check-rq-graph

7. Lint this mini work package doc after updates:

    wctl doc-lint --path docs/mini-work-packages/20260303_wepp_prep_only_button_execplan.md

## Validation and Acceptance

Acceptance is behavior-first and must be demonstrated:

1. UI placement and interaction:
- WEPP Exec card shows `Prep Only` directly above `Run WEPP Watershed`.
- Clicking `Prep Only` submits to `/rq-engine/api/runs/{runid}/{config}/prep-wepp-watershed`.

2. Queue behavior:
- Route returns canonical enqueue payload with `job_id`.
- Enqueued graph contains prep stages and prep finalize only.
- Graph excludes `_run_hillslopes_rq`, `run_watershed_rq`/`run_ss_batch_watershed_rq`, and post-run interchange/export stages.

3. File-system result:
- `wd/wepp/runs/` contains refreshed hillslope and watershed run inputs (for example `p*.run` and `pw0.*` family).
- No new WEPP hillslope/watershed output files are produced by prep-only execution.

4. Completion semantics:
- Status stream emits `WEPP_PREP_TASK_COMPLETED`.
- Frontend marks action complete without invoking report refresh.
- `timestamps:run_wepp_watershed` is not advanced by prep-only completion.

5. Regression safety:
- Existing `run-wepp`, `run-wepp-watershed`, `run-wepp-npprep`, and `run-wepp-watershed-no-prep` flows continue to pass existing tests.

## Idempotence and Recovery

Prep-only must be safe to run repeatedly:

- Re-running prep-only should overwrite/rebuild input files deterministically.
- If prep-only fails mid-run, user can rerun prep-only safely after fixing inputs or environment.
- If users need fresh outputs after prep-only, they can run standard WEPP run buttons; no migration step is required.

Failure and rollback strategy:

- If new completion event wiring causes UI regression, revert controller handling and temporarily map prep-only completion to a neutral status message while preserving backend prep behavior.
- If queue graph drift appears, regenerate static graph artifacts immediately and re-run `wctl check-rq-graph`.

## Artifacts and Notes

Evidence to capture during implementation:

- Route response example for prep-only enqueue (`job_id` payload).
- RQ graph snippet showing prep-only edges only.
- Manual check transcript showing `wepp/runs/*` created after prep-only.
- Confirmation that `run_wepp_watershed` timestamp remains unchanged for prep-only runs.

Store key evidence snippets in this section and append milestone outcomes in `Outcomes & Retrospective`.

## Interfaces and Dependencies

New/updated interface contracts expected after implementation:

- rq-engine endpoint:
  - `POST /api/runs/{runid}/{config}/prep-wepp-watershed`
  - auth: `rq:enqueue` + run authorization
  - response: canonical RQ enqueue payload (`job_id`).

- Redis prep job-id key:
  - `rq:prep_wepp_watershed_rq` (via `prep.set_rq_job_id(...)`).

- Status trigger:
  - new event token `WEPP_PREP_TASK_COMPLETED` on `runid:wepp` channel.

- Controller action hooks:
  - `data-wepp-action="prep-watershed"`
  - optional event bus emissions (`wepp:prep_only:*`) if added.

Dependencies to preserve:

- Canonical error/response payload shape from `docs/schemas/rq-response-contract.md`.
- Queue wiring catalog/graph obligations from root `AGENTS.md`.
- Controller bundle regeneration requirement from `wepppy/weppcloud/AGENTS.md`.

---
Revision Note (2026-03-03, Codex): Initial detailed mini-work-package ExecPlan authored for the WEPP prep-only button and input-only pipeline feature.
Revision Note (2026-03-03, Codex): Updated ExecPlan as a living implementation record with completed milestones, queue-artifact verification status, and required validation outcomes.
Revision Note (2026-03-03, Codex): Corrected validation/outcome records after first implementation pass.
Revision Note (2026-03-04, Codex): Corrected queue-drift handling and validation outcomes to match executed commands (`check_rq_dependency_graph.py --write`, broad pytest climate-lock failure, and current WEPP Jest status).
Revision Note (2026-03-04, Codex): Updated route-contract parity artifacts/checks for the new endpoint and refreshed validation outcomes after a clean full-suite pytest run.
