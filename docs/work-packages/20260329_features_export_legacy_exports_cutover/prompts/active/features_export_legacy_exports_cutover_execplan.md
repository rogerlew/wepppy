# Cut Over Legacy Prep Details and Geopackage Exports to Features Export

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this cutover, users still get working Prep Details and post-WEPP GeoPackage-style exports, but all execution paths run through `features_export` contracts rather than legacy writer modules. Operators and end users also get stable, composable download links through profile publication IDs (`prep-wepp`, `prep-details`) without exposing cache-hash internals. Success is visible when legacy entry points return correct artifacts via `features_export`, canonical job/published download routes work, and legacy modules are deleted only after explicit human approval backed by parity and e2e evidence.

## Progress

- [x] (2026-03-29 22:30Z) Authored package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-29 22:40Z) Updated `wepppy/nodb/mods/features_export/specification.md` with job/published download and publication-registry contracts.
- [x] (2026-03-29 23:10Z) Phase 1 complete: implemented canonical job download route (`/export/features/job/{job_id}/download`), removed compatibility route contract usage in rq-engine, and updated microservice route tests (`14 passed`).
- [x] (2026-03-29 23:55Z) Phase 2 complete: publication registry implemented at `export/features/published/index.json` with atomic writes and stale validation (`cache_key`, `request_hash`, dependency fingerprint checks), plus published download endpoint.
- [x] (2026-03-30 00:15Z) Phase 3 complete: legacy rq-engine export endpoints and post-run completion hooks rewired to `features_export` profile execution (`prep-wepp`, `prep-details`).
- [x] (2026-03-30 00:20Z) Phase 4 complete: removed artifact-bundled `profile.yml`/built-in profile docs/`README.md`; bundle now includes payload members + `manifest.json`.
- [x] (2026-03-30 00:45Z) Phase 5 complete: regression tests updated and passing across service/microservice/rq/weppcloud/js targets.
- [x] (2026-03-30 01:00Z) Phase 6 complete: manual e2e parity evidence captured on `/wc1/runs/cl/clogging-starch` with cold/warm timings and published registry proof.
- [x] (2026-03-30 01:05Z) Phase 7 complete: human approval gate artifact authored (`artifacts/human_approval_gate.md`) with explicit GO/NO-GO checklist.
- [x] (2026-03-30 02:10Z) Incremental cutover follow-up: `prep-details` default profile switched to CSV, post-run post-WEPP flow changed to single-run dual publication (`prep-wepp` + co-created `prep-wepp-geodatabase`), and WEPP Run Results now surfaces published export links.
- [x] (2026-03-30 02:35Z) Incremental cutover follow-up: published download filenames now resolve as `<runid>.<canonical-profile>.<format>.zip`, and WEPP Run Results export links point to `/rq-engine/.../export/features/published/{profile}/download` routes.
- [x] (2026-03-29 19:17Z) Phase 8 complete: deleted legacy export modules/stubs, removed dead callsites/imports, and executed final regression gates (`141` pytest pass set + route/js validations).

## Surprises & Discoveries

- Observation: Legacy exports are still wired in multiple places (rq-engine endpoints and post-WEPP completion hooks), not one single boundary.
  Evidence: `wepppy/microservices/rq_engine/export_routes.py`, `wepppy/rq/wepp_rq_pipeline.py`, `wepppy/rq/wepp_rq_stage_post.py`, `wepppy/nodb/core/wepp_run_service.py`.

- Observation: Existing features-export artifacts currently bundle profile/provenance documents, which is unnecessary for stable published download semantics.
  Evidence: `wepppy/nodb/mods/features_export/service.py` (`profile.yml`, `profiles/*`, `README.md` bundle-member assembly).

- Observation: Features-export control visibility is currently run-mod driven (`'features_export' in ron.mods`).
  Evidence: `wepppy/weppcloud/routes/run_0/run_0_bp.py`.

- Observation: Route migration for Phase 1 was isolated to rq-engine helper+route path and route tests; no additional callsites required code changes in this phase.
  Evidence: `wepppy/microservices/rq_engine/export_routes.py`, `tests/microservices/test_rq_engine_features_export_routes.py`.

- Observation: Built-in `post-wepp.yml` included a `tabular` block even though `format=geopackage`; this caused profile-backed cutover execution to fail validation.
  Evidence: runtime validation failure from `prepare_export_submission(...)` (`tabular options are only valid for format=csv|parquet.`), fixed by removing the block from `wepppy/nodb/mods/features_export/profiles/post-wepp.yml`.

- Observation: direct browser links to rq-engine export endpoints are not session-safe because rq-engine export routes require bearer auth headers; run-results export links must resolve through run-scoped file download paths instead.
  Evidence: `require_jwt(...)` contract in `wepppy/microservices/rq_engine/auth.py` and template link requirements for `wepp_reports.htm`.

## Decision Log

- Decision: Canonical job downloads use `/export/features/job/{job_id}/download` and do not keep `/export/features/{job_id}/download` as long-term API.
  Rationale: Eliminates route ambiguity and cleanly separates job-id and profile publication lookups.
  Date/Author: 2026-03-29 / User + Codex.

- Decision: Published profile downloads are backed by one explicit run-scoped registry file (`export/features/published/index.json`).
  Rationale: Stable user-facing links with explicit ownership and no new NoDb controller model.
  Date/Author: 2026-03-29 / User + Codex.

- Decision: Legacy module deletion requires an explicit human approval gate after parity and e2e evidence.
  Rationale: High-impact retirement step needs auditable signoff.
  Date/Author: 2026-03-29 / User + Codex.

## Outcomes & Retrospective

Phases 1-7 completed successfully:
- Canonical job download route switched to `/export/features/job/{job_id}/download` and result payloads now emit that route.
- Publication registry contract is implemented at `export/features/published/index.json` with atomic writes and stale-publication validation.
- Legacy export routes and completion hooks now execute through `features_export` profile requests (`prep-wepp`, `prep-details`), including published-profile updates.
- Post-WEPP completion export now executes one dual-publication orchestration profile (`prep-wepp-gpkg-gdb`) that publishes both GeoPackage (`prep-wepp`) and co-created FileGDB (`prep-wepp-geodatabase`) without a second profile materialization run.
- Prep-details canonical profile now defaults to CSV (`features_export.csv.zip`) for legacy replacement behavior.
- Artifact bundles were simplified to payload members + `manifest.json` only.
- Regression suites across microservice/service/rq/weppcloud/js targets are green.
- E2E evidence captured cold/warm timings and published artifact paths on representative run `/wc1/runs/cl/clogging-starch`.
- Human approval gate artifact is authored with explicit GO/NO-GO decision checklist.

Work package is fully complete after GO approval and Phase 8 deletion/validation execution.

## Context and Orientation

This cutover spans NoDb export orchestration, rq-engine API adapters, run-completion hooks, and run-page integration.

Primary modules:

- `wepppy/nodb/mods/features_export/service.py` orchestrates request planning, cache behavior, artifact writing, and job-manifest mapping.
- `wepppy/microservices/rq_engine/export_routes.py` owns legacy export endpoints and existing features-export submit/profile/download endpoints.
- `wepppy/rq/wepp_rq_pipeline.py` and `wepppy/rq/wepp_rq_stage_post.py` enqueue/execute post-WEPP completion exports.
- `wepppy/nodb/core/wepp_run_service.py` now maps completion-export flags to profile-backed `features_export` execution.
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/prep_details.htm` still exposes legacy post-completion toggles.
- `wepppy/export/gpkg_export.py` and `wepppy/export/prep_details.py` are deletion targets after approval.

Terms used in this plan:

- Publication registry: run-scoped JSON mapping from profile ID to the currently published artifact metadata.
- Job download endpoint: endpoint keyed by asynchronous export job ID.
- Published download endpoint: endpoint keyed by stable profile ID (`prep-wepp`, `prep-details`).
- Human approval gate: explicit artifact documenting a maintainer go/no-go before destructive legacy deletion.

## Plan of Work

Phase 1 introduces route contract changes first, with tests, while leaving legacy internals intact. `export_routes.py` gains `/export/features/job/{job_id}/download`; compatibility `/export/features/{job_id}/download` is removed in this package (no lingering alias). Any JS/template references are updated to use the job route returned by submit/jobinfo payloads.

Phase 2 implements publication registry collaborators under `wepppy/nodb/mods/features_export/` and exposes `/export/features/published/{profile}/download`. Publication reads always consult `export/features/published/index.json`. Registry entries include artifact mapping and cache/dependency fingerprints so stale publication can return conflict instead of silently serving drifted artifacts.

Phase 3 rewires legacy export behavior to `features_export` profiles. Legacy endpoints (`/export/geopackage`, `/export/prep_details`) and post-WEPP completion hooks switch from direct legacy writers to invoking `features_export` with profile-resolved requests. For this package, profile IDs used by publication are canonicalized to `prep-wepp` and `prep-details`.

Phase 4 simplifies artifact packaging. Remove profile/provenance bundle members from `features_export` zip artifacts and keep payload members plus `manifest.json`. Preserve replay/provenance via manifest request metadata and profile resolver endpoints rather than embedded profile files.

Phase 5 adds or updates tests:

- service tests for publication registry reads, stale registry behavior, and packaging members.
- rq-engine route tests for job and published download endpoints.
- legacy endpoint parity tests proving features-export-backed behavior.
- route/controller tests if UI-visible download links or status payloads change.

Phase 6 runs manual e2e parity checks on representative runs (including one with known baseline counts) and captures concrete evidence: run ID, job ID, endpoint used, artifact relpath, layer counts/table counts, and cold/warm timings.

Phase 7 records human approval in `artifacts/human_approval_gate.md`, including reviewer name/date and explicit authorization to delete legacy modules.

Phase 8 performs deletion and closeout: remove `wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py`, remove dead imports/callsites, run final tests, and update tracker/spec/package closure notes.

## Concrete Steps

All commands run from `/workdir/wepppy` unless noted.

1. Implement route and service changes.

    rg -n "export/features/.*/download|export/geopackage|export/prep_details" wepppy/microservices/rq_engine/export_routes.py
    rg -n "gpkg_export|prep_details" wepppy/nodb/core/wepp_run_service.py wepppy/rq/wepp_rq_pipeline.py wepppy/rq/wepp_rq_stage_post.py

2. Implement publication registry collaborators and tests.

    rg -n "cache_key|manifest_relpath|artifact_relpath" wepppy/nodb/mods/features_export/service.py
    wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1

3. Validate rq-engine export routes.

    wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1

4. Validate run-page integrations when route payloads change.

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1
    wctl run-npm test -- features_export

5. Manual e2e evidence (example target run):

    - Trigger prep-wepp publication export and capture `job_id`, `artifact_relpath`, `manifest_relpath`, wall time.
    - Trigger prep-details publication export and capture same fields.
    - Verify `GET /rq-engine/api/runs/{runid}/{config}/export/features/published/{profile}/download` returns expected artifact for each profile.
    - Verify a stale publication scenario returns conflict and does not serve drifted artifact.

6. Human approval gate:

    - Write `docs/work-packages/20260329_features_export_legacy_exports_cutover/artifacts/human_approval_gate.md` with:
      - evidence summary,
      - unresolved risk list,
      - explicit go/no-go decision,
      - approver and date.

7. Remove legacy modules and run final validation:

    wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1
    wctl run-npm test -- features_export
    wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md
    wctl doc-lint --path docs/work-packages/20260329_features_export_legacy_exports_cutover/

## Validation and Acceptance

Acceptance requires all of the following:

- Legacy `/export/geopackage` and `/export/prep_details` paths continue to function for users but execute through `features_export` internals.
- Job download endpoint is `GET /rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download`.
- Published endpoint is `GET /rq-engine/api/runs/{runid}/{config}/export/features/published/{profile}/download` and resolves solely via `export/features/published/index.json`.
- Profile IDs `prep-wepp` and `prep-details` map to valid artifacts and return deterministic behavior.
- Artifact bundles contain payload members + `manifest.json` only.
- Required automated suites pass.
- Manual e2e artifacts capture run/job/path/timing evidence for both profiles.
- Human approval gate artifact exists and explicitly approves deletion.
- Legacy modules and dead callsites are removed after approval and regression suites remain green.

## Idempotence and Recovery

- Publication registry writes must be atomic so repeated publish actions overwrite profile entries safely.
- Endpoint and packaging changes should be additive until human approval gate is complete; destructive file deletion is deferred to final phase.
- If parity fails before approval, revert to pre-deletion state by leaving legacy modules untouched and keeping cutover branch open.
- If stale-publication checks are too strict for valid artifacts, adjust registry validation rules and re-run route/service tests before proceeding.

## Artifacts and Notes

Required artifacts for closure:

- `docs/work-packages/20260329_features_export_legacy_exports_cutover/artifacts/human_approval_gate.md`
- `docs/work-packages/20260329_features_export_legacy_exports_cutover/artifacts/e2e_validation_summary.md`
- `docs/work-packages/20260329_features_export_legacy_exports_cutover/artifacts/code_review.md`
- `docs/work-packages/20260329_features_export_legacy_exports_cutover/artifacts/qa_review.md`

Evidence snippets should include:

- concrete run IDs and config,
- job IDs and endpoint URLs used,
- artifact and manifest relpaths,
- cold-cache and warm-cache timings,
- parity notes versus legacy output expectations.

## Interfaces and Dependencies

End-state interfaces:

- `export_routes` exposes:
  - `POST /rq-engine/api/runs/{runid}/{config}/export/features`
  - `GET /rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download`
  - `GET /rq-engine/api/runs/{runid}/{config}/export/features/published/{profile}/download`
- `features_export` service exposes helpers to resolve job download artifacts and published profile artifacts.
- Published registry contract is JSON-file based (`export/features/published/index.json`) and not represented as a NoDb model class.
- Legacy modules are absent after approval and all prior callsites are routed through `features_export`.

---

Revision note (2026-03-29 22:40Z): Initial ExecPlan authored for legacy prep/geopackage replacement cutover with publication registry source-of-truth, explicit human approval gate, and post-approval legacy module deletion.

Revision note (2026-03-29 23:10Z): Updated Progress/Discoveries/Outcomes after Phase 1 route implementation and targeted route-test validation.

Revision note (2026-03-30 01:05Z): Completed Phases 2-7 (publication registry, legacy route/hook rewiring, packaging simplification, regression validation, e2e evidence capture, and human gate artifact preparation). Phase 8 deletion remains pending explicit human GO.

Revision note (2026-03-29 19:17Z): Human GO executed. Phase 8 completed with legacy module deletion (`wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py` + `.pyi`), dead import/callsite cleanup, and final regression matrix pass.
