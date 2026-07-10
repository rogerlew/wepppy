# AgFields Runs-Page UI ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, an AgFields run on WEPPcloud has a runs-page control: four labeled stages that walk a user from boundary upload through per-sub-field WEPP runs, with a modal for crop-to-management mapping and a map overlay for reviewing sub-field geometry. The backend surface already exists and is tested (`20260709_ag_fields_backend_readiness`); this package is template, controller JS, and runs-page wiring only.

The design document is `wepppy/nodb/mods/ag_fields/ui_control_layout.md`. Read it in full before writing anything. It is prescriptive on purpose: §2 wireframes, §3 stage definitions with exact copy behavior, §5 modal semantics, §6 DOM hooks, §7 controller lifecycle, §8 copy rules, §9 the as-built route contract, §11 accessibility, §12 tests. The Design Mandate section is the review standard — the UI presents four user decisions; backend method names must not appear as button labels or instruction text.

A user can see this working by opening a run created from the `ag-fields` config and finding the Agricultural Fields control with stage 1 ready, stages 2-4 blocked with plain-language chips, and — after driving the stages — sub-field outputs and a map overlay.

## Progress

- [x] (2026-07-09 23:53 UTC) Milestone 1: implemented the four-stage control template and rotation mapping modal with the required DOM and accessibility hooks.
- [x] (2026-07-09 23:53 UTC) Milestone 2: implemented the dynamic-safe singleton controller, snapshot hydration, upload/mapping flows, all three job families, terminal re-hydration, and 409 handling.
- [x] (2026-07-09 23:53 UTC) Milestone 3: wired initial and dynamic runs-page rendering and promoted the registry entry to user-visible `experimental` maturity.
- [x] (2026-07-09 23:53 UTC) Milestone 4: registered an authenticated `addGeoJsonOverlay` loader and rebuild refresh behavior.
- [x] (2026-07-09 23:53 UTC) Milestone 5: added Jest/Python regression coverage, passed frontend lint and the full Jest suite, and rebuilt `controllers-gl.js`.
- [x] (2026-07-10 16:38 UTC) Follow-up: added a persisted uploaded-boundary-filename display to Stage 1, backed by the additive `boundary.filename` snapshot field, source-basename NoDb metadata, historical-project fallback, and reload regression coverage.
- [x] (2026-07-10 16:57 UTC) Follow-up: made project-UTM acceptance explicit in rasterization and the specification, added ambiguous-CRS diagnostics with project EPSG/bounds, and covered both paths.
- [x] (2026-07-10 21:52 UTC) Follow-up: replaced the Stage 4 worker control with a persisted WEPP Exec selector, defaulted new `ag-fields` projects to `wepp_dcc52a6`, pinned and propagated the selected executable to sub-field runs, and made the clear action content-width.
- [ ] (2026-07-10 22:43 UTC) Post-close follow-up in progress: state the field-boundary projection requirements directly in Stage 1 and show the assigned project EPSG as a conditional pill in run-header title rows.
- [x] (2026-07-10 22:40 UTC) Milestone 6: full Stage 4 run on
  `sacral-self-discipline` completed and maintainer-validated. Artifact
  evidence in `../../tracker.md` Validation: 6,626 sub-field runs, 46,382
  output files, `VERSION 2020.500` stamp consistent with `wepp_dcc52a6`.
  Package closed; the ExecPlan stays in `prompts/active/` only while the
  post-close projection-feedback follow-up above is in flight.

## Surprises & Discoveries

- Observation: Dynamic mod rendering uses `feature_registry.yaml:section_template`; runs-page markup alone would have left runtime enablement on the internal placeholder.
  Evidence: `run_0_bp.py:view_mod_section` resolves the registry template and `project.js` separately resolves the controller bootstrap map.
- Observation: The sub-fields overlay route requires an rq-engine bearer token, while `addGeoJsonOverlay` previously loaded only through unauthenticated `WCHttp.getJson`.
  Evidence: `ag_fields_routes.py:subfields_overlay` requires `rq:status`; the map helper now accepts an optional `loadJson` callback, covered by `map_gl.test.js`.
- Observation: The required full Python sweep is blocked by deterministic, unrelated Batch Runner test debt.
  Evidence: `wctl run-pytest tests --maxfail=1` stopped after `2070 passed, 41 skipped` at `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled`; the isolated rerun fails because `clear_nodb_file_cache()` resolves `/wc1/batch/...` outside the test's patched `batch_runner_mod.get_wd`.
- Observation: Module-level AgFields `stubtest` has 21 existing surface errors unrelated to the new source-filename property and validation keyword; repository `check-test-stubs` remains green.
  Evidence: The reported omissions are older runtime exports and methods already absent from the HEAD stub; neither changed symbol appears in the failure list.
- Observation: The first fresh-project acceptance attempt reached Stage 2 but the uploaded file is neither WGS84 nor project UTM despite GDAL defaulting the unlabeled GeoJSON to `EPSG:4326`.
  Evidence: `sacral-self-discipline` uses DEM `EPSG:32611` with bounds approximately `(493891, 5208829, 523081, 5232109)`, while uploaded bounds are approximately `(-1591832, 2847952, -1569162, 2867454)`. Transforming a representative point as `EPSG:5070` lands inside the project near `(507110, 5220699)`, so the source appears CONUS Albers-like but cannot be guessed safely without metadata.
- Observation: Corrected UTM boundaries advanced acceptance through management
  setup to the real WEPP binary.
  Evidence: p3733 first failed at `ncrop=50`; after synthesis compaction and
  ADR-0016 residue-height normalization it enters simulation, then SIGFPEs at
  `frcfac.for:184` on zero random roughness. This is the current acceptance
  blocker and is not masked by the ingestion patch.
- Observation: The controller's existing disable helper was button-specific and
  rewrote `textContent`; applying it to the new select removed every option.
  Evidence: The first focused Jest run returned an empty selected value. The
  helper now invokes busy-label restoration only for `BUTTON` elements, and all
  10 AgFields tests plus the 619-test frontend suite pass.

## Decision Log

- Decision: Ship the registry entry with `section_template: controls/ag_fields_pure.htm`, `maturity: experimental`, and `min_role: user`.
  Rationale: The control must load both initially and after a user enables the mod; retaining the placeholder or Dev-only role would contradict the package's ship milestone.
  Date/Author: 2026-07-09 / Codex.
- Decision: Extend `MapController.addGeoJsonOverlay` with an optional `loadJson` callback instead of exposing bearer tokens in URLs or adding an unauthenticated backend alias.
  Rationale: This preserves the existing auth surface and keeps public overlays on their current default loader.
  Date/Author: 2026-07-09 / Codex.
- Decision: Keep this ExecPlan active after Milestones 1-5.
  Rationale: Package acceptance explicitly requires a fresh-project browser walkthrough and real-binary output evidence that were unavailable during implementation.
  Date/Author: 2026-07-09 / Codex.
- Decision: Keep the v1 workflow in the repository's one-controller-per-control structure through acceptance, despite `ag_fields.js` entering the observability yellow band for JavaScript file size.
  Rationale: Boundary/schema, sub-field, mapping, run, and modal behavior share one snapshot and job lifecycle. Splitting before the first browser walkthrough would add speculative module boundaries; reassess after acceptance if maintenance friction is observed.
  Date/Author: 2026-07-09 / Codex.
- Decision: Expose the persisted source basename as optional `boundary.filename`, fall back to the canonical artifact basename for historical projects, and hide its display when neither exists.
  Rationale: This is backward-compatible for older NoDb state and snapshots and restores the accepted-upload context that the browser file input necessarily loses on reload, without changing project artifact names.
  Date/Author: 2026-07-10 / Codex.
- Decision: Prefer exact project-UTM boundary coordinates, continue accepting WGS84 and correctly declared projected CRSs, and reject rather than guess ambiguous projected coordinates.
  Rationale: Project UTM avoids unnecessary reprojection and preserves raster-grid precision. Guessing among arbitrary projected CRSs from coordinate magnitudes can silently place fields in the wrong location; actionable EPSG/bounds diagnostics make re-export deterministic.
  Date/Author: 2026-07-10 / Codex.
- Decision: Give AgFields its own persisted WEPP executable, default new `ag-fields.cfg` projects to `wepp_dcc52a6`, and retain the parent-WEPP executable as the fallback only for historical NoDb payloads lacking the new field.
  Rationale: The exact repaired p3733 replay completes under `wepp_dcc52a6` while `wepp_260430` and `wepp_260606` SIGFPE at `frcfac.for:184`. An additive AgFields-owned setting makes that compatibility choice explicit without rewriting existing project state. ADR-0017 records the parameterization decision.
  Date/Author: 2026-07-10 / Roger Lew and Codex.

## Outcomes & Retrospective

Milestones 1-5 now deliver the complete automated UI implementation. The design mandate is preserved: the visible workflow exposes four user decisions while mechanical backend methods remain confined to logs. Stage 1 retains visible current-file context after reload, and Stage 4 now exposes the AgFields-specific executable instead of worker tuning. New projects persist `wepp_dcc52a6`; historical state remains additive and compatible. The main integration lesson was that both registry-driven dynamic loading and rq-engine overlay authentication had to be wired explicitly; neither was satisfied by adding the static runs-page include alone.

The remaining gap is operational acceptance, not code implementation. Milestone 6 needs a fresh small-watershed run and cannot be replaced by fixture-driven Jest coverage. The unrelated full-Python Batch Runner failure is recorded as repository test debt and was not expanded into this UI package.

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

The Stage 4 executable follow-up adds `_wepp_bin` to newly initialized `AgFields` state from `[ag_fields] bin`, exposes it as `wepp.wepp_bin` in the hydration snapshot, and accepts a whitelisted `wepp_bin` in the existing run request before enqueue. Existing serialized projects without `_wepp_bin` remain readable and fall back to the parent Wepp NoDb executable until the user submits a selection. The browser removes `max_workers`, hydrates the executable select from state, submits that selection, and styles only the clear button at intrinsic width. Regression coverage proves initialization, historical fallback, RQ propagation, route validation/persistence, reload hydration, and removal of the worker DOM hook.

Milestone 6 is the acceptance walkthrough on a freshly created small-watershed AgFields project (created by the maintainer once Milestones 1-5 land): all four stages driven through the UI, outputs verified under `wepp/ag_fields/output/`, evidence recorded in the tracker. This closes the backend package's recorded real-binary E2E limitation as well; update its closure notes when done.

## Concrete Steps

Implementation was performed from `/home/workdir/wepppy`. The controller bundle was rebuilt with `python wepppy/weppcloud/controllers_js/build_controllers_js.py`. Focused iteration used `wctl run-npm test -- ag_fields`, `wctl run-npm test -- map_gl`, `wctl run-npm test -- project`, and the three affected Python modules under `tests/weppcloud/routes/`. Final frontend validation used `wctl run-npm lint` and `wctl run-npm test`.

For Milestone 6, create a run from the `ag-fields` config, complete the base watershed and observed climate, then drive the four numbered panels. Record the run id, each stage result, and `wepp/ag_fields/output/` listing in `../../tracker.md`. Only after that evidence exists should this prompt move from `prompts/active/` to `prompts/completed/`.

## Validation

- `wctl run-npm lint` and `wctl run-npm test` after Milestones 2-5.
- `wctl run-pytest` for any touched Python (template context, registry).
- Milestone 6 walkthrough evidence recorded in `../../tracker.md` with stage-by-stage notes and an output listing; no claim of end-to-end success without the walkthrough actually performed.

Observed automated results are recorded in `../../tracker.md`. The focused AgFields Jest suite passes 10 tests, the original affected Python route/template/registry group passes 135 tests, and the current-file follow-up NoDb/route/template group passes. Frontend lint, `check-test-stubs`, the full Jest suite, and the bundle build pass. The module-level `stubtest` and repository-wide Python sweep have unrelated existing failures described under `Surprises & Discoveries`.

## Idempotence and Recovery

Controller bootstrap and state hydration are idempotent and re-query the DOM after dynamic mod insertion. Repeated bundle builds replace the generated asset deterministically. If a mutation receives `agfields_job_active`, the controller re-fetches state and keeps the server-reported job stream rather than assigning a speculative id. If acceptance exposes a backend defect, record it as a package finding and fix it in a scoped follow-up, consistent with `package.md`.

## Artifacts and Notes

The implementation evidence is the new `ag_fields.test.js` suite, the affected map/project tests, the Python render/registry/bootstrap assertions, and the command transcripts summarized in `../../tracker.md`. No screenshot or real-run output artifact exists yet because Milestone 6 has not run.

Revision note (2026-07-09, Codex): Updated the living plan after implementing Milestones 1-5, documented dynamic registry and authenticated overlay decisions, recorded automated validation and unrelated suite debt, and kept Milestone 6 explicitly open for fresh-project acceptance.

Revision note (2026-07-10, Codex): Added the Stage 4 WEPP executable follow-up, its backward-compatibility plan, ADR requirement, UI simplification, and focused regression scope after the real p3733 binary comparison.
