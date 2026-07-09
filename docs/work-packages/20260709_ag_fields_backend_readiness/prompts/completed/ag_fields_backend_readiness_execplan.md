# AgFields Backend Readiness ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Completion Outcome

Completed on 2026-07-09. The package delivered the AgFields controller fixes,
authenticated rq-engine routes, guarded RQ jobs, upload/archive controls,
staleness and readiness state, regression coverage, contract documentation, and
security review required to unblock the successor runs-page UI package.

## Purpose / Big Picture

After this package, the AgFields workflow is drivable over HTTP: a runs-page UI (successor package) can upload field boundaries, confirm schema, build sub-fields, manage plant files, save crop-to-management mappings, and run per-sub-field WEPP simulations — all through run-scoped routes and RQ jobs with status streaming. Today none of that surface exists and sub-field WEPP runs are broken outright by a `NameError`.

The authoritative requirements are in the UI spec: `wepppy/nodb/mods/ag_fields/ui_control_layout.md`, sections 9 (route and job contract) and 10 (backend prerequisites). Read both before starting. Do not restate them here; when reality forces a contract change, edit the spec first, then implement.

A user can see this package working by exercising the new routes against a seeded run: upload a boundary GeoJSON, confirm schema, enqueue build-subfields and watch the status channel, upload a plant zip, save a mapping, enqueue run-wepp, and receive per-sub-field completion lines followed by output files under `wepp/ag_fields/output/`.

## Progress

- [x] (2026-07-09 21:53 UTC) Loaded the authoritative UI contract, subsystem instructions, persistence/RQ contracts, and package security requirements.
- [x] (2026-07-09 21:57 UTC) Milestone 1: passed `wepp_bin` from the configured Wepp controller into each sub-field runner and added propagation/generated-artifact regressions.
- [x] (2026-07-09 22:07 UTC) Milestone 2: implemented controller staleness, structured mapping validation/writer, deterministic plant inventory/replace/delete, and readiness helpers; full NoDb mods suite passed.
- [x] (2026-07-09 22:19 UTC) Milestone 3: added guarded RQ tasks with contractual keys, JSON terminal payloads, completion triggers, and queue graph registration.
- [x] (2026-07-09 22:19 UTC) Milestone 4: added the authenticated run-scoped rq-engine surface from spec section 9 with upload/archive guards and route tests.
- [x] (2026-07-09 22:52 UTC) Milestone 5: completed targeted controller/RQ/route coverage, queue graph, stub, broad-exception, OpenAPI, docs, and live job-tree validation; confirmed one unrelated batch-runner baseline failure in the full-suite gate.
- [x] (2026-07-09 22:55 UTC) Milestone 6: refreshed module and contract docs, completed the security review, closed the package trackers, and archived this ExecPlan.

## Surprises & Discoveries

- Observation: The package scaffold classified the new upload and queue surfaces as `low` security impact, while `docs/work-packages/README.md` classifies both as `high` by default.
  Evidence: The tracker now links the required dedicated security artifact.
- Observation: Historical AgFields state has no build-source signatures, so existing sub-fields and WEPP runs cannot be proven current.
  Evidence: The controller conservatively reports those artifacts stale until they are rebuilt by the new workflow; the historical-state regression covers this default.
- Observation: The 13-route AgFields surface increased canonical rq-engine OpenAPI size from its 118,500-byte budget to 129,217 bytes.
  Evidence: The full suite stopped at `test_openapi_document_size_budget`; the documented ceiling is now 130,000 bytes while AgFields remains outside the frozen agent inventory at `internal` maturity.
- Observation: The repository-wide pytest gate has a reproducible baseline failure in `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled` because the test stubs `batch_runner.get_wd` while `clear_nodb_file_cache` imports the canonical helper directly.
  Evidence: The full run stopped after `2070 passed, 41 skipped`; the same failure reproduced alone, and this package does not modify `batch_runner.py`, `base.py`, or the failing test.

## Decision Log

- Decision: Evolve persisted and generated schemas additively: retain the existing `rotation_lookup.tsv` columns, use safe defaults for new NoDb keys, and add route response fields without renaming existing RQ response keys.
  Rationale: Existing run directories and Python-driven AgFields workflows must remain readable while the HTTP surface is added.
  Date/Author: 2026-07-09 / Codex
- Decision: Treat every boundary upload as a schema reset, use boundary/schema/rotation source signatures for staleness, and conservatively report historical unsigned artifacts as stale.
  Rationale: A replacement boundary can invalidate both selected columns and every downstream artifact; unverified historical products must not be presented as current.
  Date/Author: 2026-07-09 / Codex
- Decision: Apply the upload quotas, observed-climate modes, per-run single-flight admission, and 130,000-byte OpenAPI budget recorded in ADR-0015.
  Rationale: These explicit limits protect upload and queue surfaces while keeping legitimate AgFields inputs and route discovery usable.
  Date/Author: 2026-07-09 / Codex
- Decision: Implement the exact run-scoped route and state contract in `ui_control_layout.md` section 9 and retain AgFields at `internal` agent maturity.
  Rationale: The successor UI needs a stable backend contract, while agent-facing maturity should change only when the user control ships.
  Date/Author: 2026-07-09 / Codex

## Outcomes & Retrospective

The controller now propagates the configured WEPP binary, performs atomic
boundary/schema/mapping mutations, tracks source signatures, validates
readiness, and manages plant archives deterministically. Three RQ entrypoints
and 13 authenticated rq-engine route shapes expose that behavior with scoped
cache invalidation, contractual status events, single-flight admission, and
bounded upload processing. Tests and documentation cover the persisted TSV and
NoDb compatibility surface, generated run artifacts, failure payloads, auth,
archive safety, and route contracts.

No seeded `/wc1/runs/*/ag_fields.nodb` project was available, so a real WEPP
binary end-to-end run was not possible. Regression coverage reaches the
`run_hillslope` boundary with generated inputs, and a live Redis job-tree check
verified all three RQ entrypoints. The runs-page UI and feature maturity bump
remain intentionally assigned to the successor package.

## Context and Orientation

`wepppy/nodb/mods/ag_fields/ag_fields.py` holds the `AgFields` NoDb controller. Its workflow methods are complete and documented in the module README, but they were only ever driven from Python. The module-level function `run_wepp_subfield` (used by `run_wepp_ag_fields` through a `ThreadPoolExecutor`) references `self.wepp_instance.wepp_bin` even though it has no `self` — every sub-field run raises `NameError` when it reaches `run_hillslope`. This is Milestone 1 and blocks everything in stage 4 of the UI spec.

`CropRotationManager` (same file) validates `rotation_lookup.tsv` and resolves crops to management files from either the weppcloud management database (integer id, resolved via `get_management_summary` with the run's landuse mapping) or `ag_fields/plant_files/` (`.man` filename). `validate_rotation_lookup` currently pretty-prints and returns nothing. There is a debug dump method writing `rotation_lookup_dump.tsv`; there is no writer that builds canonical `rotation_lookup.tsv` from structured input.

`handle_plant_file_db_upload` extracts `.man` entries (lowercase suffix match only) from a zip already placed in `ag_fields/`, sniffs first lines for 2017.1 format, flattens directories with space-to-underscore normalization, suffixes flatten-collisions, downgrades 2017.1 files to 98.4, validates with `read_management`, and persists only the valid list. Zip-slip guards (absolute paths, `..` parts) exist and must be preserved. Invalid files are only logged; same-named re-uploads have accidental semantics; a single unreadable 2017.1 file aborts the whole upload.

There are no AgFields routes anywhere in `wepppy/weppcloud/routes/` or `wepppy/microservices/rq_engine/`, and no AgFields tasks in `wepppy/rq/`. Route precedents: `rq_engine/treatments_routes.py` for multipart upload plus enqueue, `rq_engine/upload_disturbed_routes.py` for synchronous rq-engine upload, and `routes/nodb_api/roads_bp.py` for serving a run-artifact GeoJSON resource. All rq-engine routes must call `authorize_run_access`.

Readiness facts the state snapshot must derive: observed-climate readiness comes from `Climate.climate_mode` plus integer-parseable `observed_start_year`/`observed_end_year` (there is no `is_observed` helper); watershed abstraction readiness is the presence of `dem/wbt/flovec.tif`; parent-WEPP readiness is the presence of `wepp/runs/p{wepp_id}.sol`/`.cli` files that `run_wepp_subfield` symlinks against.

Tests live under `tests/nodb/mods/` (see `tests/AGENTS.md` for stub management; run `wctl check-test-stubs` if imports fail). The existing `test_ag_fields_rasterize_crs.py` shows the module's test conventions.

## Plan of Work

Milestone 1 first, alone, as a small reviewable change: make `wepp_bin` a parameter of `run_wepp_subfield`, resolved in `run_wepp_ag_fields` from the Wepp NoDb instance and passed through the executor submission. The regression test must fail against the pre-fix code.

Milestone 2 changes the controller in place. Staleness: on boundary re-upload, record enough state (the geojson hash sub-fields were built from, or explicit dirty flags) that a state snapshot can report spec §4 staleness without client-side inference; decide and document whether re-upload clears `field_id_key`/`rotation_accessor` or flags them stale. Plant files: deterministic replace of same-named files, an explicit delete method, persisted invalid-file reasons alongside the valid list, case-insensitive `.man` matching. Mapping: a writer that produces canonical `rotation_lookup.tsv` from structured rows and a `validate_rotation_lookup` that returns per-crop results without printing. Keep all mutations under the NoDb locking conventions (`with self.locked()`, persist on success).

Milestone 3 adds an AgFields task module under `wepppy/rq/` following the neighboring task modules: three job families with the exact job keys from spec §7 (`agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`), status publishing to the run's Redis DB 2 channel, and terminal events carrying the payloads the spec names (valid/invalid plant summary; failed `sub_field_id` and parent `field_id`).

Milestone 4 stands up the routes in spec §9's table, matching the Treatments/Disturbed-SBS precedents for URL style and auth. The schema-confirm route owns atomicity: validate both values before persisting either. The state snapshot route aggregates everything spec §4 hydrates from; it should be cheap (NoDb properties and file-existence checks, no raster reads).

Milestone 5 is test coverage per the package success criteria, plus `python tools/check_broad_exceptions.py --enforce-changed` and stub checks.

Milestone 6 refreshes `wepppy/nodb/mods/ag_fields/README.md` for the changed plant-file and lookup-validation behavior and the new HTTP/RQ surface, updates the tracker and root `PROJECT_TRACKER.md` lifecycle, and moves this ExecPlan to `prompts/completed/`.

## Validation

- `wctl run-pytest tests/nodb/mods/` for controller and regression coverage.
- Targeted pytest for new routes and RQ tasks (paths chosen at implementation time; record commands and outputs in the tracker).
- `python tools/check_broad_exceptions.py --enforce-changed` must pass.
- Record all validation evidence in `../../tracker.md` under Validation with actual command output, not paraphrase.

Recorded outcome:

- Focused AgFields controller/RQ/route set: `52 passed, 9 warnings in 15.86s`.
- NoDb mods suite: `748 passed, 23 skipped, 17 warnings in 27.57s`.
- rq-engine OpenAPI contract module: `10 passed, 5 warnings in 12.78s`.
- RQ graph, runtime stubtest, test-stub completeness, broad-exception enforcement, docs lint, and live Redis job-tree checks passed.
- Repository-wide `wctl run-pytest tests --maxfail=1`: stopped at the unrelated, independently reproducible batch-runner baseline failure after `2070 passed, 41 skipped, 35 warnings in 300.01s`.

## Revision Note

Revised on 2026-07-09 at package closure to record implementation decisions,
validation evidence, the reproducible baseline suite failure, residual
end-to-end limitation, and final outcome before archival.
