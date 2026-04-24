# Landuse Phase 3 Hardening Parity Test Matrix

## Purpose
This matrix defines the minimum blocking test coverage for Gate 3 route movement of landuse map/catalog/file surfaces from WEPPcloud Flask routes to rq-engine routes.

Gate 3 cannot pass unless every `Required` row is green for both:
- baseline WEPPcloud behavior (`tests/weppcloud/routes/test_landuse_bp.py`), and
- rq-engine Phase 3 replacement behavior (`tests/microservices/test_rq_engine_landuse_routes.py` or dedicated Phase 3 split module).

## Surface Inventory
- Catalog read: `/api/landuse/user_defined/catalog`
- Catalog mutators: `/tasks/landuse/user_defined/upload|delete|update-description`
- Map read: `/api/landuse/map_snapshot`
- Map mutators: `/tasks/landuse/map/save|clear-override`
- Legacy batch mutator: `/tasks/modify_landuse/`

## Blocking Matrix

| ID | Threat Class | Legacy Flask Assertion (baseline) | rq-engine Parity Assertion (required) | Baseline Test Ref | rq-engine Test Ref | Required |
|---|---|---|---|---|---|---|
| HP-01 | Run-root containment | Symlink/escape path rejected as `400` with `INVALID_RUN_PATH`. | Identical rejection semantics for moved routes. | `test_landuse_user_defined_upload_rejects_symlink_escape` | `test_landuse_phase3_upload_rejects_symlink_escape` | Yes |
| HP-02 | Archive member policy | ZIP members must be root-level `.man`; nested/non-man rejected `400`. | Identical archive member policy and status/code. | `test_landuse_user_defined_catalog_rejects_zip_with_non_man_members` | `test_landuse_phase3_upload_rejects_zip_with_non_man_members` | Yes |
| HP-03 | Upload boundary caps | `.man` and `.zip` uploads enforce max-byte limits before write/extract. | Same max-byte policy and explicit rejection contract. | `test_landuse_user_defined_upload_enforces_boundary_caps_and_conflicts` | `test_landuse_phase3_upload_enforces_max_bytes_and_conflict_contract` | Yes |
| HP-04 | Catalog conflict behavior | Upload conflict without `replace=true` returns `409` (`CATALOG_CONFLICT`). | Same conflict code/status and no partial writes. | `test_landuse_user_defined_upload_enforces_boundary_caps_and_conflicts` | `test_landuse_phase3_upload_enforces_max_bytes_and_conflict_contract` | Yes |
| HP-05 | Catalog CRUD integrity | Upload -> list -> update-description -> delete preserves metadata/file consistency. | Same lifecycle behavior and metadata schema. | `test_landuse_user_defined_catalog_upload_update_delete` | `test_landuse_phase3_catalog_upload_update_delete_via_rq_engine` | Yes |
| HP-06 | Snapshot freshness | `map_snapshot` returns deterministic rows/options/hash with no-store headers. | Same payload semantics and cache headers where applicable. | `test_landuse_map_snapshot_and_save` | `test_landuse_phase3_map_snapshot_and_save` | Yes |
| HP-07 | Precondition enforcement | Map save without match hash returns `428` (`PRECONDITION_REQUIRED`). | Same precondition contract. | `test_landuse_map_save_requires_if_match` | `test_landuse_phase3_map_save_requires_precondition` | Yes |
| HP-08 | Stale-write prevention | Stale hash returns `409` (`STALE_LOOKUP`) with expected/current hash details. | Same stale-write rejection contract and details shape. | `test_landuse_map_save_rejects_stale_lookup_hash` | `test_landuse_phase3_map_save_rejects_stale_hash` | Yes |
| HP-09 | Row schema validation | Invalid/duplicate/missing/unknown rows rejected with explicit validation error contract. | Same validation failure behavior and status/code. | `test_landuse_map_save_rejects_invalid_row_payloads` | `test_landuse_phase3_map_save_validates_rows_and_rolls_back_on_failure` (invalid rows case) | Yes |
| HP-10 | Atomic rollback on rebuild failure | Save failure during `build_managements` restores prior override file + relpath. | Same rollback guarantees for moved mutators. | `test_landuse_map_save_rolls_back_override_on_build_failure` | `test_landuse_phase3_map_save_validates_rows_and_rolls_back_on_failure` (rollback case) | Yes |
| HP-11 | Clear override safety | `clear-override` clears relpath + file atomically and timestamps prep task. | Same post-condition guarantees. | `test_landuse_map_clear_override_clears_path_and_file` | `test_landuse_phase3_clear_override_clears_path_and_file` | Yes |
| HP-12 | Legacy modify strictness | `modify_landuse` input coercion enforces integer topaz/landuse and explicit error messages. | Equivalent strict input behavior on replacement operation (if moved). | `test_task_modify_landuse_*` family | `test_landuse_phase3_modify_landuse_strict_input_and_auth` | Yes |
| HP-13 | Auth policy | Browser/session callers remain on WEPPcloud render routes without ownership widening. | `rq:enqueue` + run access + token-class policy enforcement for moved mutators, `rq:read|rq:status` on moved reads. | `test_view_landuse_user_defined_renders_rq_engine_routes`, `test_view_landuse_map_renders_rq_engine_routes` | `test_landuse_phase3_modify_landuse_strict_input_and_auth`, `test_landuse_phase3_read_routes_require_read_scope` | Yes |
| HP-14 | Browser transport | Browser pages calling moved routes use token bridge transport. | `requestWithSessionToken` used for moved surfaces; no cookie fallback. | `controllers_js/__tests__/landuse.test.js`, `controllers_js/__tests__/landuse_modify_gl.test.js`, plus render route config tests above | same | Yes |
| HP-15 | Discovery/OpenAPI parity | Moved operations represented in run endpoint catalog and docs contracts. | Catalog/OpenAPI/contract docs updated and tested. | N/A | `test_landuse_operations_are_discoverable_with_schema_and_defaults`, `test_rq_engine_openapi_contract.py` | Yes |
| HP-16 | Error-contract parity | Error responses remain explicit, no silent fallbacks, no implicit mutation fallback. | Same canonical error contract behavior for moved surfaces. | `test_landuse_*` hardening error assertions in `test_landuse_bp.py` | `test_landuse_phase3_*` hardening error assertions in `test_rq_engine_landuse_routes.py` | Yes |

## Gate 3 Pass Rule
Gate 3 is `PASS` only when:
1. Every `Required` matrix row has passing baseline and rq-engine tests.
2. Security artifact records no unresolved medium/high findings for moved surfaces.
3. OpenAPI/discovery/docs contract checks pass for all moved operations.
4. Browser transport tests confirm moved routes call rq-engine via `requestWithSessionToken` and do not reintroduce cookie fallback.
