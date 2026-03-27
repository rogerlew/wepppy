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
- [x] (2026-03-27 01:04Z) Fixed post-integration submit regression (`DependencyResolutionError: nodb_ref locator requires an explicit nodb_ref_resolver callback`) by wiring service-level nodb_ref resolution and adding regression coverage.
- [x] (2026-03-27 11:22Z) Fixed temporal compatibility regression so atemporal layers (`temporal.supported_modes=[]`) are not excluded when a request includes temporal selectors; added planner regression coverage and spec clarification.
- [x] (2026-03-27 12:18Z) Realigned Features Export status panel/job-id handling with canonical controller patterns: switched template to `status_panel_options` (`wc-status-panel` theming) and hardened submit/bootstrap job-id resolution for wrapped/keyed payload variants.
- [x] (2026-03-27 12:44Z) Brought Features Export control inputs/layout into UI-contract compliance by replacing ad-hoc radio/checkbox markup with canonical choice controls and updating JS-rendered catalog layer checkboxes to `wc-choice` styling.
- [x] (2026-03-27 14:22Z) Fixed artifact delivery integrity regressions: features-export job results now emit browser-session `browse/download` URLs, stale cache-hit `.gpkg` artifacts with non-SQLite signatures are invalidated/rebuilt, and geodatabase staging now uses real GeoPackage bytes instead of synthesized JSON payload bytes.
- [x] (2026-03-27 16:18Z) Closed reviewer follow-up findings: switched GeoPackage container creation to GDAL/OGR-backed output (interoperable with `f_esri` conversion), enforced enqueue-time cache-hit eligibility checks so invalid cache entries route to full worker execution, and fixed GeoPackage temp-file cleanup/dead-code issues.

## Surprises & Discoveries

- Observation: `run_0` dynamic mod insertion depends on both route-side `MOD_UI_DEFINITIONS` and client-side `Project` bootstrap map, so missing either side causes runtime "mod enabled but no control bootstrapped" behavior.
  Evidence: `run_0_bp.py:view_mod_section` + `project.js:set_mod` + `MOD_BOOTSTRAP_MAP` control bootstrap path.
- Observation: Features Export smoke workflow could not execute without explicit UI pre-selection because submit stays disabled until validation passes.
  Evidence: `controller-regression.spec.js` expects enabled action before click; `features_export` needed new `prepareFeaturesExport` helper in `controller-cases.js`.
- Observation: Full-suite route-contract guards enforce frozen artifact parity beyond WP-5 files; adding new agent-facing routes required synchronized updates to endpoint inventory/checklist and response-rule catalog.
  Evidence: `tests/tools/test_endpoint_inventory_guard.py`, `tests/tools/test_route_contract_checklist_guard.py`, and `tests/microservices/test_rq_engine_openapi_contract.py` failed until artifacts/rules were aligned.
- Observation: Real submit flow surfaced a runtime-only dependency resolver gap not exercised by existing route tests: `prepare_export_submission` invoked dependency snapshot building without `nodb_ref_resolver`.
  Evidence: live traceback at `wepppy/nodb/mods/features_export/dependency_tracker.py` raising `DependencyResolutionError` for `nodb_ref` during `/export/features` submit.
- Observation: Planner treated `temporal.supported_modes=[]` as "supports nothing" rather than "atemporal", which caused legitimate static layers to be dropped with `layer_unavailable` warnings and produced nearly-empty artifacts.
  Evidence: live run warnings for `landuse.dominant`, `soils.dominant`, `watershed.channels`, and `watershed.subcatchments` under `annual_average`.
- Observation: Features Export used a custom status panel override that diverged from canonical `wc-status-panel` markup and had stricter-than-canonical submit parsing (`body.job_id` only), making job-id rendering brittle when payload wrappers differ.
  Evidence: live UI submit failures with missing job-id surfacing despite successful/wrapped backend contracts in related controllers.
- Observation: Returning `download_url` as `/rq-engine/api/.../download` from job results is incompatible with normal browser clicks because rq-engine download endpoints require explicit bearer JWT headers.
  Evidence: live UI/browser attempts returned `401 Missing Authorization header` for rq-engine features-export download links.
- Observation: Legacy cache entries created before GeoPackage writer hardening can persist JSON bytes with `.gpkg` extension, causing cache-hit reuse of invalid artifacts after code upgrades.
  Evidence: live artifact under `export/features/artifacts/*/features_export.gpkg` decoded as JSON text and was only served when `cache_hit=true`.
- Observation: Validating cache eligibility only inside the worker is insufficient when submit-time queue selection forces `run_features_export_cache_hit_rq`; stale/invalid cache entries can still fail before fallback logic executes.
  Evidence: rq-engine enqueue selected cache-hit worker from cache-index presence alone while service-level invalidation rejected the same cache entry under `force_cache_hit=True`.
- Observation: Manual SQLite synthesis for `.gpkg` passed byte-level checks but produced containers not readable by GDAL `GPKG` driver in conversion flow.
  Evidence: direct `f_esri.c2c_gpkg_to_gdb` probe failed against synthesized output and succeeded after OGR-backed GeoPackage creation.

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
- Decision: Resolve catalog `nodb_ref` locators in service orchestration by supplying a deterministic resolver callback (`watershed.*` support) to `build_dependency_snapshot` and returning canonical service errors when unsupported tokens are encountered.
  Rationale: Dependency tracking contract already requires explicit resolver callbacks for `nodb_ref`; wiring the callback in service is the minimal, explicit fix that preserves strict failure semantics.
  Date/Author: 2026-03-27 / Codex
- Decision: Interpret empty `temporal.supported_modes` as an explicit atemporal contract and bypass temporal-mode compatibility filtering for those layers.
  Rationale: Catalog uses `supported_modes: []` for static families, and temporal selectors should not suppress atemporal resources.
  Date/Author: 2026-03-27 / Codex
- Decision: Use `control_shell` `status_panel_options` for Features Export status markup and accept canonical job-id envelope variants (`job_id`, wrapped `Content`, keyed `job_ids`) in submit/bootstrap flows.
  Rationale: Keeps Features Export consistent with shared theming and resilient to canonical response/context payload shapes already used across WEPPcloud controllers.
  Date/Author: 2026-03-27 / Codex
- Decision: Emit completed features-export `download_url` values as browse-service paths (`/runs/{runid}/{config}/download/{artifact_relpath}`) rather than rq-engine job download endpoints.
  Rationale: Runs-page browser flows authenticate via session/cookies; browse/download is the canonical browser-facing download surface and avoids bearer-token-only failures.
  Date/Author: 2026-03-27 / Codex
- Decision: Validate cached geopackage artifacts on cache-hit reuse with a SQLite signature check and fall back to cache-miss regeneration when invalid.
  Rationale: Prevents stale legacy JSON-labeled `.gpkg` artifacts from being reused after writer contract changes while keeping cache behavior deterministic for valid artifacts.
  Date/Author: 2026-03-27 / Codex
- Decision: Generate GeoPackage artifacts with GDAL/OGR (`GPKG` driver, aspatial attribute layers) rather than hand-crafted SQLite schema assembly.
  Rationale: Ensures generated containers are interoperable with downstream GDAL/f_esri conversion paths and avoids brittle spec/schema drift in manual SQL.
  Date/Author: 2026-03-27 / Codex
- Decision: Gate cache-hit worker enqueue on validated cache-entry usability (`cache_entry_supports_cache_hit`) instead of cache-index presence alone.
  Rationale: Aligns rq-engine queue selection with service-level cache validation and prevents deterministic failures on stale/invalid cache entries.
  Date/Author: 2026-03-27 / Codex

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
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py --maxfail=1`

Reviewer outcomes:
- `reviewer` agent: reported one medium checklist contract mismatch; fixed via checklist/rules alignment; re-review reported no high/medium findings.
- `qa_reviewer` agent: reported two medium items (smoke pre-submit prep missing; uncovered run_0 helper logic); fixed via `prepareFeaturesExport` and new route-helper tests; re-review reported no high/medium findings.

## Interfaces and Dependencies

No new external dependencies are planned. WP-5 relies on existing WEPPcloud helpers (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`, `WCControllerBootstrap`) and existing rq-engine features export endpoints.

## Revision Notes

- 2026-03-26 (Codex): Created WP-5 ExecPlan with implementation sequence, validation gates, and reviewer loop requirements.
- 2026-03-27 (Codex): Marked implementation complete; recorded delivered wiring/template/controller/tests, review-loop fixes, guard-artifact alignments, and final validation outcomes.
- 2026-03-27 (Codex): Recorded and fixed post-integration nodb_ref dependency resolver regression with added service-level tests.
- 2026-03-27 (Codex): Recorded and fixed atemporal-layer temporal filtering regression in planner; added regression test and updated temporal semantics contract note.
- 2026-03-27 (Codex): Recorded canonical UI/theming + job-id parsing hardening for Features Export submit/bootstrap paths with updated Jest/route template coverage.
- 2026-03-27 (Codex): Recorded browse/download URL contract update for completed result links and cache-hit invalidation for legacy non-SQLite `.gpkg` artifacts; updated exporter/service tests accordingly.
- 2026-03-27 (Codex): Recorded GDAL/OGR GeoPackage writer cutover, enqueue-time cache-hit eligibility gating, and GeoPackage temp-file lifecycle fixes driven by reviewer high/medium findings.
