# Upload Boundary Helpers Unification

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, upload-capable routes share a consistent non-ZIP boundary helper path for filename normalization, extension allowlist enforcement, size caps, and save semantics. Operators and clients get predictable upload boundary behavior across routes, and maintainers no longer have to patch duplicated helper logic in multiple route files.

ZIP handling remains unchanged in ownership: `wepppy/microservices/shape_converter/archive_validation.py` stays canonical, and culvert semantic payload checks remain in `wepppy/microservices/culvert_payload_validator.py`.

## Progress

- [x] (2026-04-12 16:11Z) Created package scaffold and activated this ExecPlan.
- [x] (2026-04-12 16:11Z) Captured hard requirement to keep canonical ZIP helpers in `shape_converter/archive_validation.py`.
- [x] (2026-04-12 16:11Z) Completed initial endpoint/helper inventory and identified duplicated helper routes (`ash`, `omni`, Flask `roads`).
- [x] (2026-04-12 16:18Z) Defined canonical non-ZIP helper API and migration guardrails.
- [x] (2026-04-12 16:22Z) Implemented helper core + framework adapters and compatibility wrappers.
- [x] (2026-04-12 16:27Z) Migrated duplicated helper routes to canonical helper usage.
- [x] (2026-04-12 16:29Z) Added/updated helper-level and route-level regression tests.
- [x] (2026-04-12 16:35Z) Ran targeted test gate and full suite gate.
- [x] (2026-04-12 16:39Z) Ran docs lint on changed docs and recorded closure evidence.
- [x] (2026-04-12 16:35Z) Completed security review disposition and package-close findings review.

## Surprises & Discoveries

- Observation: `ash_routes.py` and `omni_routes.py` duplicated the same filename/extension/size helpers instead of consuming existing shared rq-engine helper paths.
  Evidence: pre-migration helper stacks in both route modules (`_validate_upload_filename`, `_enforce_extension`, `_enforce_max_bytes`, `_save_upload`).
- Observation: Roads already had streaming and 413 handling semantics that map cleanly to a shared stream writer helper, so route behavior could be preserved without contract changes.
  Evidence: `roads_bp.py` prior `_save_roads_upload_with_limit(...)` semantics and post-migration parity tests.
- Observation: Existing upload contract matrix already had correct caps/allowlists; the migration was primarily implementation unification, not contract change.
  Evidence: `docs/schemas/upload-endpoint-contract.md`.

## Decision Log

- Decision: Keep ZIP helper canonical ownership in `shape_converter/archive_validation.py` and do not introduce new ZIP helper abstractions in this package.
  Rationale: ZIP safety controls are validated and already reused by culvert ingest; parallel ZIP helpers would recreate drift risk.
  Date/Author: 2026-04-12 / Codex.
- Decision: Introduce a shared cross-framework non-ZIP helper module at `wepppy/microservices/upload_boundary.py`.
  Rationale: `upload_helpers.py` alone did not cover Flask Roads or duplicated route-local helpers.
  Date/Author: 2026-04-12 / Codex.
- Decision: Preserve route-level error contract behavior while migrating internals, including `413` for explicit size-limit violations.
  Rationale: Clients and existing tests rely on these status semantics.
  Date/Author: 2026-04-12 / Codex.

## Outcomes & Retrospective

- Outcome: Added canonical non-ZIP helper layer (`wepppy/microservices/upload_boundary.py`) and migrated `upload_helpers.py`, `ash_routes.py`, `omni_routes.py`, and `roads_bp.py` to shared boundary logic.
- Outcome: Added regression tests for helper behavior and route-level oversize/type handling.
- Outcome: Test gates passed:
  - Targeted upload suites: `137 passed`.
  - Full suite: `3511 passed`, `36 skipped`.
- Outcome: Docs gate passed: `wctl doc-lint` -> `6 files validated, 0 errors, 0 warnings`.

## Context and Orientation

Upload boundary layers after implementation:

- Canonical ZIP boundary helpers:
  - `wepppy/microservices/shape_converter/archive_validation.py`
  - Includes `read_upload_bytes_with_limit(...)` and `validate_and_extract_zip_archive(...)`.
- Canonical non-ZIP boundary helpers:
  - `wepppy/microservices/upload_boundary.py`
  - Includes `prepare_filename(...)`, `enforce_extension(...)`, `write_stream_to_destination(...)`, and `save_upload_from_stream(...)`.
- Compatibility wrapper for rq-engine route callers:
  - `wepppy/microservices/rq_engine/upload_helpers.py` (`save_upload_file(...)`).

Contract and policy references:

- Upload endpoint matrix and limits:
  - `docs/schemas/upload-endpoint-contract.md`
- Canonical response contract:
  - `docs/schemas/rq-response-contract.md`
- Security review template:
  - `docs/prompt_templates/security_review_template.md`

## Plan of Work

Milestone 1 - Helper API and boundary contract freeze:

- Define canonical non-ZIP helper API and module location.
- Freeze migration invariants:
  - caps and extension allowlists unchanged,
  - status behavior preserved (400 validation/type, 413 size where currently enforced),
  - response envelope remains canonical.

Milestone 2 - Implement helper core and adapters:

- Implement shared helper core for filename/extension/size/save semantics.
- Route existing `upload_helpers.py` behavior through shared core.
- Add cross-framework stream write helper for Flask call sites.

Milestone 3 - Route migration:

- Migrate duplicated helper call sites in:
  - `ash_routes.py`,
  - `omni_routes.py`,
  - `roads_bp.py`.
- Keep ZIP helper authority and culvert semantic validator ownership unchanged.

Milestone 4 - Tests, docs, and security closeout:

- Add helper-level tests for boundary behavior.
- Update route tests for migration parity and 400/413 handling.
- Update upload contract helper ownership notes.
- Complete security artifact disposition and validation evidence.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Inventory and design validation:
   - `rg -n "UploadFile|request\.files|save_upload_file\(|_save_upload\(" wepppy/microservices/rq_engine wepppy/weppcloud/routes`

2. Implement helper core and migrate routes:
   - Edit helper modules and target routes.

3. Targeted tests:
   - `wctl run-pytest tests/microservices/test_upload_boundary_helpers.py tests/microservices/test_rq_engine_upload_disturbed_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/microservices/test_rq_engine_upload_batch_runner_routes.py tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_treatments_routes.py tests/microservices/test_rq_engine_culverts.py tests/microservices/test_rq_engine_ash_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_roads_bp.py --maxfail=1`

4. Full regression gate:
   - `wctl run-pytest tests --maxfail=1`

5. Docs gate:
   - `wctl doc-lint --path docs/work-packages/20260412_upload_boundary_helpers_unification/package.md --path docs/work-packages/20260412_upload_boundary_helpers_unification/tracker.md --path docs/work-packages/20260412_upload_boundary_helpers_unification/prompts/active/upload_boundary_helpers_unification_execplan.md --path docs/work-packages/20260412_upload_boundary_helpers_unification/artifacts/2026-04-12_security_review.md --path docs/schemas/upload-endpoint-contract.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Acceptance is complete when:

- Duplicated helper implementations in target routes are removed or reduced to thin adapters over canonical helpers.
- All migrated endpoints preserve declared caps/extension policies in `docs/schemas/upload-endpoint-contract.md`.
- ZIP handling remains canonical in `shape_converter/archive_validation.py`; no new ZIP helper layer is introduced.
- Targeted route suites and full suite pass.
- Security artifact is closed with no unresolved medium/high findings.
- Docs lint passes on changed package/contract tracker docs.

## Idempotence and Recovery

- Route migrations are file-local and can be applied incrementally.
- If a migration regresses behavior, revert only the affected route to previous helper path, keep shared helper core, and rerun targeted tests.
- Do not modify `wepppy/weppcloud/routes/usersum/generated/docs_index.json` if dirty.

## Artifacts and Notes

- Security artifact path:
  - `docs/work-packages/20260412_upload_boundary_helpers_unification/artifacts/2026-04-12_security_review.md`
- Package tracker:
  - `docs/work-packages/20260412_upload_boundary_helpers_unification/tracker.md`

## Interfaces and Dependencies

Expected helper interfaces after implementation:

- Non-ZIP canonical helper API consumed by both FastAPI and Flask upload routes.
- Existing route contracts preserved through compatibility wrappers/adapters.
- Canonical ZIP helpers unchanged and imported from:
  - `wepppy/microservices/shape_converter/archive_validation.py`

Dependencies:

- Existing route tests in `tests/microservices/` and `tests/weppcloud/routes/`.
- Upload contract documentation in `docs/schemas/upload-endpoint-contract.md`.

---
Revision Note (2026-04-12 / Codex): ExecPlan updated through implementation, test/docs gate completion, and final security disposition.
