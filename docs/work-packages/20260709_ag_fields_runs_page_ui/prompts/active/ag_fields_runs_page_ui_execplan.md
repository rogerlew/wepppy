# AgFields Runs-Page UI ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, an AgFields run on WEPPcloud has a runs-page control: four labeled stages that walk a user from boundary upload through per-sub-field WEPP runs, with a modal for crop-to-management mapping and a map overlay for reviewing sub-field geometry. The backend surface already exists and is tested (`20260709_ag_fields_backend_readiness`); this package is template, controller JS, and runs-page wiring only.

The design document is `wepppy/nodb/mods/ag_fields/ui_control_layout.md`. Read it in full before writing anything. It is prescriptive on purpose: §2 wireframes, §3 stage definitions with exact copy behavior, §5 modal semantics, §6 DOM hooks, §7 controller lifecycle, §8 copy rules, §9 the as-built route contract, §11 accessibility, §12 tests. The Design Mandate section is the review standard — the UI presents four user decisions; backend method names must not appear as button labels or instruction text.

A user can see this working by opening a run created from the `ag-fields` config and finding the Agricultural Fields control with stage 1 ready, stages 2-4 blocked with plain-language chips, and — after driving the stages — sub-field outputs and a map overlay.

## Progress

- [ ] Milestone 1: control template + modal.
- [ ] Milestone 2: controller JS.
- [ ] Milestone 3: runs-page wiring + registry maturity.
- [ ] Milestone 4: map overlay.
- [ ] Milestone 5: Jest + frontend gates.
- [ ] Milestone 6: acceptance walkthrough on a fresh project (external dependency: project creation).

## Surprises & Discoveries

(record as encountered)

## Decision Log

(seed decisions live in `../../tracker.md`; add implementation-level decisions here with rationale, date, author)

## Outcomes & Retrospective

(pending)

## Context and Orientation

Templates: `wepppy/weppcloud/templates/controls/` holds the pure controls; `_pure_macros.html` provides `control_shell`, `collapsible_card`, `file_upload`, `select_field`, `numeric_field`, `radio_group`, `table_block`, and status/stacktrace panel plumbing. The Batch Runner template (`routes/batch_runner/templates/batch_runner_pure.htm`) is the styling and `data-role` precedent for staged intake; the Disturbed modal (`controls/disturbed_modal.htm`) is the modal precedent, included unconditionally from `runs0_pure.htm` and self-gated on the run's mods. The runs page (`routes/run_0/templates/runs0_pure.htm`) gates mod sections with `show_*` flags, `data-mod-nav` nav items, and `data-mod-section` panels — all three pieces are explicit template work for a new mod control.

Controller JS: `wepppy/weppcloud/controllers_js/` modules are bundled by `build_controllers_js.py` (auto-discovery). `control_base.js` provides `attach_status_stream`, `set_rq_job_id`, and poll fallback; `bootstrap.js` provides `WCControllerBootstrap.resolveJobId`, which matches exact job keys — the AgFields keys are `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`. `batch_runner.js` shows the hydration/rehydration pattern; `roads_gl.js` plus `map_gl.js` (`addGeoJsonOverlay`) show the overlay pattern. Jest tests live in `controllers_js/__tests__/` and run via `wctl run-npm test`.

Routes the UI consumes are all under the rq-engine `/api` prefix, documented in spec §9 with the state-snapshot shape and the 409 `agfields_job_active` semantics (on 409, keep the currently attached stream; do not replace the job id). The browser obtains a session bearer token through the existing rq-engine session-token mechanism used by other controls.

Feature registry: `wepppy/weppcloud/feature_registry/feature_registry.yaml` holds AgFields at `maturity: internal`; this package moves it to `experimental` and resolves the control shell's feature id (either a `_feature_form_map` entry for `ag_fields_form` in `_pure_macros.html` or an explicit `feature_id` argument).

The state snapshot is the single source of gating truth. The controller renders from it and re-fetches it on terminal job events; it never computes workflow state client-side except the crop-year pattern *suggestion* (spec §3 stage 1), which is UX sugar validated server-side on confirm.

## Plan of Work

Milestone 1 builds the template statically first: shell, four stage panels with ids `agfields_stage_boundaries`, `agfields_stage_subfields`, `agfields_stage_managements`, `agfields_stage_run`, every `data-role` hook from the §6 table, collapsibles collapsed by default, chips with `:empty` hiding, and the modal with its table skeleton. Copy comes from §3 and §8 verbatim where the spec gives it.

Milestone 2 implements `ag_fields.js` against the template: bootstrap, snapshot hydration, upload flows (multipart, busy states, server-error chips), schema confirm with the three-outcome pattern detection, enqueue flows for the three jobs, stream attach and terminal-event re-hydration, modal open/fetch/save with per-row error rendering, and 409 handling. Fixture-driven Jest tests accompany each behavior; the spec §12.1 list is the floor, not the ceiling.

Milestone 3 wires the runs page and registry. Milestone 4 adds the overlay with rebuild refresh. Milestone 5 runs the frontend gates and any pytest touched by template-context changes.

Milestone 6 is the acceptance walkthrough on a freshly created small-watershed AgFields project (created by the maintainer once Milestones 1-5 land): all four stages driven through the UI, outputs verified under `wepp/ag_fields/output/`, evidence recorded in the tracker. This closes the backend package's recorded real-binary E2E limitation as well; update its closure notes when done.

## Validation

- `wctl run-npm lint` and `wctl run-npm test` after Milestones 2-5.
- `wctl run-pytest` for any touched Python (template context, registry).
- Milestone 6 walkthrough evidence recorded in `../../tracker.md` with stage-by-stage notes and an output listing; no claim of end-to-end success without the walkthrough actually performed.
