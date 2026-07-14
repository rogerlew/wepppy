# Route Contract Checklist (2026-02-08)

Checklist baseline for frozen `agent-facing` routes owned by `rq-engine`.

Guarded by:
- `tools/check_endpoint_inventory.py` (source route freeze parity)
- `tools/check_route_contract_checklist.py` (checklist row parity + non-empty contract fields)
- `tests/microservices/test_rq_engine_openapi_contract.py` (OpenAPI metadata/response contract + oversize budgets)

- Total frozen routes covered: **114**

Cutover reconciliation note (2026-04-11):
- Row-8 contract cutover package
  `20260410_rq_controller_state_contract_cutover` verified this checklist as
  the frozen contract baseline for agent-facing rq-engine routes.
- No checklist-row additions/removals were required at cutover closure; guard
  checks continue to enforce checklist parity and response-code contracts.
- Post-cutover parity refresh (2026-04-25) added eight landuse user-defined/map
  routes already present in the frozen endpoint inventory.

Inventory reconciliation note (2026-07-10):
- Added contract rows for the 13 AgFields workflow endpoints and the
  asynchronous ERMiT submit/download pair.
- AgFields routes are covered by their focused rq-engine suite; ERMiT routes
  retain the export-route coverage in addition to the shared OpenAPI guard.

Inventory reconciliation note (2026-07-13):
- Added the AgFields Concept 2 watershed enqueue and isolated-clear contracts.

## Contract Matrix

| Method | Path | Auth | Scope | Mutates | Execution | Required Responses | Contract Coverage |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/canceljob/{job_id}` | JWT Bearer | rq:status | mutating | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/configs` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `GET` | `/api/configs/{config}` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `POST` | `/api/culverts-wepp-batch/` | JWT Bearer | culvert:batch:submit | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/culverts-wepp-batch/{batch_uuid}/finalize` | JWT Bearer | culvert:batch:retry | mutating | async enqueue | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | JWT Bearer | culvert:batch:retry | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/endpoints` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `GET` | `/api/endpoints/{operation_id}/defaults` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `GET` | `/api/endpoints/{operation_id}/errors` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `GET` | `/api/endpoints/{operation_id}/schema` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_setup_discovery_routes.py` |
| `POST` | `/api/jobinfo` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `GET` | `/api/jobinfo/{job_id}` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 404, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `GET` | `/api/jobstatus/{job_id}` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 404, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `POST` | `/api/runs/{runid}/{config}/acquire-openet-ts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/acquire-polaris` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_polaris_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/acquire-rap-ts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/boundaries` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/build-subfields` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/clear` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/clear-watershed` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/agfields/management-options` | JWT Bearer | rq:status | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/agfields/plant-files` | JWT Bearer | rq:status | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `DELETE` | `/api/runs/{runid}/{config}/agfields/plant-files/{filename}` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/plant-database` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/agfields/rotation-mapping` | JWT Bearer | rq:status | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/rotation-mapping` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/run-wepp` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/run-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/agfields/schema` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/agfields/state` | JWT Bearer | rq:status | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/agfields/sub-fields.geojson` | JWT Bearer | rq:status | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_ag_fields_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/archive` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/controllers` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/hints` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/schema` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/controllers/{controller}/templates` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/checkout` | JWT Bearer | bootstrap:checkout | mutating | sync no queue | `200, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/bootstrap/commits` | JWT Bearer | bootstrap:read | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/bootstrap/current-ref` | JWT Bearer | bootstrap:read | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/enable` | JWT Bearer | bootstrap:enable | mutating | async enqueue | `200, 202, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/mint-token` | JWT Bearer | bootstrap:token:mint | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/build-climate` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/geneva/build-frequency-panel` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geneva_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/build-rusle` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-landuse` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/set-landuse-mode` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/set-landuse-db` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/modify-landuse-coverage` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/controllers/landuse/state` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/modify-landuse-mapping` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/modify-landuse` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/landuse-user-defined/catalog` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/landuse-user-defined/upload` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/landuse-user-defined/delete` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/landuse-user-defined/update-description` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/landuse-map/snapshot` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/landuse-map/save` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 428, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/landuse-map/clear-override` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_landuse_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/build-soils` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-treatments` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/delete-archive` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/delete-omni-contrasts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/endpoints` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/defaults` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/errors` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_errors_progress_outputs_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/endpoints/{operation_id}/schema` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_schema_defaults_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/export/ermit` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/export/ermit` | JWT Bearer | rq:export | mutating | async enqueue | `202, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_export_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/export/ermit/job/{job_id}/download` | JWT Bearer or public-run access | rq:export when authenticated | read-only | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_export_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/export/geodatabase` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/geopackage` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/prep_details` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/prep_details/` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/export/features` | JWT Bearer | rq:export | mutating | async enqueue | `202, 400, 401, 403, 404, 409, 415, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_features_export_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/export/features/profile/resolve` | JWT Bearer | rq:export | read-only | sync no queue | `200, 400, 401, 403, 415, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_features_export_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/export/features/job/{job_id}/download` | JWT Bearer | rq:export | read-only | sync no queue | `200, 401, 403, 404, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_features_export_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/export/features/published/{profile}/download` | JWT Bearer | rq:export | read-only | sync no queue | `200, 401, 403, 404, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_features_export_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/fetch-dem-and-build-channels` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/fork` | Optional JWT; anonymous CAPTCHA path | `rq:enqueue` (if bearer token is used) | mutating | async enqueue | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/geneva/state` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geneva_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/geospatial-metadata` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/outputs` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_errors_progress_outputs_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/pipeline` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_orchestration_read_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/post-dss-export-rq` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/prep-wepp-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/readiness` | JWT Bearer | rq:status or rq:read | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_orchestration_read_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/restore-archive` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-ash` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-debris-flow` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni-contrasts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | JWT Bearer | rq:enqueue | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/geneva/prepare-hrus` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geneva_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/prepare-roads` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_roads_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/geneva/run-batch` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geneva_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/geneva/run-workflow` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_geneva_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/run-rhem` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-roads` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_roads_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/run-swat` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-swat-noprep` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/run-wepp` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-wepp-npprep` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/run-wepp-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-wepp-watershed-no-prep` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/session-token` | Bearer or session cookie (public-run fallback) | `rq:status` (if bearer token is used) | mutating | sync no queue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/set-outlet` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/swat/print-prt` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/swat/print-prt/meta` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/tasks/upload-cli/` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/tasks/upload-cover-transform` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/tasks/upload-dem/` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/tasks/upload-sbs/` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/create/` | JWT/rq_token, same-origin session cookie, or CAPTCHA | `rq:enqueue` (token-auth paths) | mutating | sync redirect | `303, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |

## Notes

- This artifact tracks contract completeness for frozen agent-facing routes, not full behavioral test depth per endpoint.
- Polling routes remain open by policy (`RQ_ENGINE_POLL_AUTH_MODE=open`) and include `429` in required responses.
- Bootstrap routes require explicit Bootstrap scopes as documented in `docs/weppcloud-bootstrap-spec.md`.
