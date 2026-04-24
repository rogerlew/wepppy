# Landuse User-Defined Management Catalog + Mapping Editor

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package is complete, a power user can upload `.man` files (individually or as a `.zip`) into a run-scoped catalog and then map landuse keys/disturbed classes to those management files from a dedicated mapping editor page. The selected mapping is saved in the run `landuse/` directory and becomes the authoritative mapping used by NoDb and prep flows, including robust multi-year management expansion in single and multi-OFE runs.

## Progress

- [x] (2026-04-24 02:32 UTC) Created package scaffold and authored initial package/tracker/ExecPlan/security artifacts.
- [x] (2026-04-24 02:32 UTC) Completed discovery pass across UI, route, NoDb, upload, archive-validation, and prep-time management touchpoints.
- [x] (2026-04-24 02:32 UTC) Recorded initial contract decisions (upload limits, archive semantics, mapping save semantics, NoDb preference, compatibility).
- [x] (2026-04-24 07:11 UTC) Implemented catalog API routes and storage layout under `landuse/user-defined/`.
- [x] (2026-04-24 07:14 UTC) Implemented PowerUser-linked page: `Landuse User-Defined`.
- [x] (2026-04-24 07:18 UTC) Implemented PowerUser-linked page: `Landuse Map`.
- [x] (2026-04-24 07:26 UTC) Implemented run-scoped mapping persistence and `Landuse` custom mapping preference logic.
- [x] (2026-04-24 07:44 UTC) Added regression suites and passed targeted validation across Flask/rq-engine/NoDb/management templates.
- [x] (2026-04-24 07:47 UTC) Closed security findings and completed package closeout updates.

## Surprises & Discoveries

- Observation: `load_map(_map)` in `wepppy/wepp/management/managements.py` currently selects built-in JSON by substring and does not support explicit run-local map file paths.
  Evidence: function branch table only matches known keys (`disturbed`, `eu-disturbed`, `revegetation`, etc.), otherwise defaults to `map.json`.

- Observation: The repository already has hardened ZIP extraction primitives (`validate_and_extract_zip_archive`) and non-archive upload boundary helpers.
  Evidence: `wepppy/microservices/shape_converter/archive_validation.py` and `wepppy/microservices/upload_boundary.py`.

- Observation: Existing editable table page pattern already provides optimistic concurrency and theme-ready styling.
  Evidence: `wepppy/weppcloud/templates/controls/edit_csv.htm`, with `data-lookup-snapshot-url` and `X-If-Match-Sha256` usage in disturbed/geneva routes.

- Observation: Multi-year management repetition is already standardized in both prep paths.
  Evidence: `Management.build_multiple_year_man(...)` is used in `wepppy/nodb/core/wepp_prep_service.py` and `wepppy/nodb/core/wepp.py::prep_multi_ofe_hillslope`.

- Observation: rq-engine test doubles for `landuse` do not uniformly expose `get_mapping_dict()`.
  Evidence: existing route tests stub selected controller methods only; route-side effective-map validation needed a compatibility guard for missing method on legacy stubs.

## Decision Log

- Decision: Two dedicated pages are required (`Landuse User-Defined`, `Landuse Map`) and both are linked from PowerUser Actions.
  Rationale: User explicitly requested page split and this keeps catalog CRUD separate from mapping assignment.
  Date/Author: 2026-04-24 / Codex.

- Decision: Package is high-security and must carry a dedicated security review artifact.
  Rationale: Scope includes untrusted upload, archive handling, and run-tree writes.
  Date/Author: 2026-04-24 / Codex.

- Decision: Archive imports and mapping saves are all-or-nothing.
  Rationale: Partial apply creates hard-to-debug mixed state across catalog files and mapping metadata.
  Date/Author: 2026-04-24 / Codex.

- Decision: Run-scoped mapping file persisted in `landuse/` is authoritative when configured.
  Rationale: User explicitly requires project-local saved mapping and NoDb preference.
  Date/Author: 2026-04-24 / Codex.

- Decision: No silent fallback for configured custom-map failures.
  Rationale: Repository guidance favors explicit failure over hidden recovery paths for debugging clarity.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Current outcome:
- Package implementation is complete end-to-end.
- Two new PowerUser workflows are shipped:
  - Run-scoped user-defined management catalog page and APIs (upload/list/delete/description update).
  - Run-scoped landuse mapping editor page and APIs (snapshot/save/clear override).
- Run-local custom mapping persistence is implemented and authoritative when configured:
  - map persisted at `landuse/landuse_user_defined_mapping.json`
  - NoDb `Landuse` prefers `custom_mapping_relpath` and fails explicitly on missing/invalid configured maps.
- `load_map()` now supports explicit JSON mapping paths, enabling run-scoped mapping files with deterministic `ManagementDir` resolution.
- Hardened upload + archive behavior enforces `.man`/`.zip` policy, bounded member/size limits, and all-or-nothing install semantics.
- Targeted validation evidence:
  - `.venv/bin/pytest tests/wepp/management/test_management_map_loading.py tests/nodb/test_landuse_custom_mapping.py tests/microservices/test_rq_engine_landuse_routes.py tests/weppcloud/routes/test_landuse_bp.py tests/weppcloud/routes/test_pure_controls_render.py -q` -> `86 passed`
  - `wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map` -> `5 files validated, 0 errors, 0 warnings`
  - `wctl check-rq-graph` -> `RQ dependency graph artifacts are up to date`

Residual follow-up (non-blocking):
- Containerized `wctl run-pytest` against the same touched suite can be rerun later once compose/runtime tree sync is revalidated in local dev environment.
- Full-suite local pytest requires configured `SECRET_KEY`/`SECRET_KEY_FILE`; rerun pre-handoff global sanity after env secrets are present.

## Context and Orientation

Key modules and why they matter:
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm`:
  - Add links for the two new pages in the Actions column.
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`:
  - Existing run-scoped landuse task/query/report routes; logical home for new page endpoints and Flask-side mapping/catalog APIs.
- `wepppy/microservices/rq_engine/landuse_routes.py`:
  - Existing authenticated landuse mutation/upload APIs; likely home for secured upload + map-save endpoints if queue-backed behavior is needed.
- `wepppy/microservices/upload_boundary.py`:
  - Canonical helper for single-file upload validation (`secure_filename`, extension checks, size caps).
- `wepppy/microservices/shape_converter/archive_validation.py`:
  - Canonical helper for ZIP hardening (signature, traversal, member limits, encryption/compression policy).
- `wepppy/nodb/core/landuse.py`:
  - Owns `mapping`, `landuseoptions`, management builds, and is the required integration seam for custom map preference.
- `wepppy/wepp/management/managements.py`:
  - Owns map loading and management metadata (`ManagementFile`, `SoilFile`, `ManagementDir`).
- `wepppy/nodb/core/wepp_prep_service.py` and `wepppy/nodb/core/wepp.py`:
  - Consume management summaries and apply multi-year management synthesis; must remain behaviorally stable.
- `wepppy/weppcloud/templates/controls/edit_csv.htm` + disturbed/geneva routes:
  - Provides ready-to-reuse optimistic-concurrency editor pattern and theme-consistent UI.

## Plan of Work

Milestone 1 establishes storage and contracts. Create run-scoped catalog metadata and file layout under `landuse/user-defined/`, then implement upload/list/delete/description-update APIs with strict validation, canonical errors, and lock-safe writes.

Milestone 2 delivers UI page 1 (Landuse User-Defined). Add PowerUser link, render catalog table/form in Pure style, and wire JS actions for upload/delete/description updates with optimistic refresh behavior and accessible status messaging.

Milestone 3 delivers UI page 2 (Landuse Map). Render key/disturbed class/description rows with management-file selectors populated from catalog + built-ins, validate full-table edits, and persist one run-local mapping JSON using optimistic concurrency semantics.

Milestone 4 updates NoDb preference and prep compatibility. Extend mapping resolution so a configured run-local map is loaded as authoritative; ensure `ManagementFile -> SoilFile` association follows map selections; verify single and multi-OFE prep still uses `build_multiple_year_man(...)` behavior.

Milestone 5 completes regression/security/documentation closure. Add route/controller/NoDb tests, close security findings, run required gates, and archive this ExecPlan with outcomes.

## Concrete Steps

Working directory: `/home/workdir/wepppy`

1. Implement catalog storage + API contracts.

    rg -n "landuse|upload|mapping|lookup_snapshot" \
      wepppy/weppcloud/routes/nodb_api/landuse_bp.py \
      wepppy/microservices/rq_engine/landuse_routes.py

2. Implement upload hardening with shared helpers.

    rg -n "save_upload_from_stream|validate_and_extract_zip_archive|ArchiveLimits" \
      wepppy/microservices/upload_boundary.py \
      wepppy/microservices/shape_converter/archive_validation.py

3. Implement UI pages and PowerUser links.

    rg -n "PowerUser|Actions|edit_csv|control_shell" \
      wepppy/weppcloud/templates/controls/poweruser_panel.htm \
      wepppy/weppcloud/templates/controls/edit_csv.htm

4. Implement NoDb mapping preference and map loading support.

    rg -n "mapping|load_map|landuseoptions|get_mapping_dict" \
      wepppy/nodb/core/landuse.py \
      wepppy/wepp/management/managements.py

5. Add/expand tests and run gates.

    wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1
    wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1
    wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js
    wctl check-rq-graph
    wctl doc-lint --path docs/work-packages/20260423_landuse_user_defined_management_catalog_map

## Validation and Acceptance

Acceptance requires:
- User can open both new PowerUser-linked pages and complete catalog + mapping workflows.
- `.man` and `.zip` upload flows enforce contract limits and reject unsafe payloads with canonical errors.
- Mapping save is deterministic and atomic; NoDb then uses the saved run-local map.
- Soil association follows management selection updates.
- Single and multi-OFE prep output remains valid and multi-year expansion behavior is unchanged.
- Security artifact gate passes with no unresolved medium/high findings.

## Idempotence and Recovery

- Upload/list/delete endpoints must be idempotent where practical (`delete` on missing file should be explicit and non-destructive).
- Mapping writes use optimistic concurrency; stale writes return conflict and require refresh.
- If a write fails after staging, no partial catalog/map state should remain (atomic temp-write + rename).
- Recovery path: remove run-local mapping override to return to built-in mapping behavior.

## Artifacts and Notes

- Tracker: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/tracker.md`
- Security review: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/artifacts/2026-04-24_security_review.md`
- Discovery notes: `docs/work-packages/20260423_landuse_user_defined_management_catalog_map/notes/2026-04-24_codebase_investigation.md`

## Interfaces and Dependencies

Primary interfaces:
- WEPPcloud Flask run routes (`authorize_and_handle_with_exception_factory`) for page render + session-protected mutations.
- rq-engine JWT-protected routes (`require_jwt` + `authorize_run_access`) for queue-backed or API-first upload/mapping operations.
- NoDb `Landuse` mapping source contract and management-summary hydration.
- Shared upload and archive validation helpers.

Contracts to preserve:
- Canonical error envelope from `docs/schemas/rq-response-contract.md`.
- CSRF expectations from `docs/schemas/weppcloud-csrf-contract.md` for browser-session mutation routes.
- NoDb directory-root lock behavior for `landuse` mutations.

## Revision Notes

- 2026-04-24 / Codex: Initial ExecPlan authored from feasibility investigation and user requirements.
- 2026-04-24 / Codex: Completed implementation milestones, refreshed validation evidence, and finalized closeout narrative for archive.
