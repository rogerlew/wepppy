# AgFields Backend Readiness ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, the AgFields workflow is drivable over HTTP: a runs-page UI (successor package) can upload field boundaries, confirm schema, build sub-fields, manage plant files, save crop-to-management mappings, and run per-sub-field WEPP simulations — all through run-scoped routes and RQ jobs with status streaming. Today none of that surface exists and sub-field WEPP runs are broken outright by a `NameError`.

The authoritative requirements are in the UI spec: `wepppy/nodb/mods/ag_fields/ui_control_layout.md`, sections 9 (route and job contract) and 10 (backend prerequisites). Read both before starting. Do not restate them here; when reality forces a contract change, edit the spec first, then implement.

A user can see this package working by exercising the new routes against a seeded run: upload a boundary GeoJSON, confirm schema, enqueue build-subfields and watch the status channel, upload a plant zip, save a mapping, enqueue run-wepp, and receive per-sub-field completion lines followed by output files under `wepp/ag_fields/output/`.

## Progress

- [ ] Milestone 1: `wepp_bin` fix + regression test.
- [ ] Milestone 2: Controller contract gaps (staleness, structured lookup validation, plant-file semantics, mapping writer, readiness helpers).
- [ ] Milestone 3: RQ tasks with contractual job keys and status publishing.
- [ ] Milestone 4: HTTP routes per spec §9.
- [ ] Milestone 5: Test coverage and lint gates.
- [ ] Milestone 6: Docs refresh and package closure.

## Surprises & Discoveries

(record as encountered)

## Decision Log

(seed decisions live in `../../tracker.md`; add implementation-level decisions here with rationale, date, author)

## Outcomes & Retrospective

(pending)

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
