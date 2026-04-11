# Operator Smoke Evidence - RQ Operator Experience Hardening

**Package**: `20260411_rq_operator_experience_hardening`  
**Date**: 2026-04-11 UTC  
**Scope**: API-only operator acceptance (no `wctl` in operator flow), machine-safe bootstrap, discovery/read/mutation/poll sequence, revision/freshness parity checks.

## Environment
- RQ Engine base URL: `http://localhost:8042`
- WEPPcloud auth base URL: `http://localhost:8000`
- Source bearer token for bootstrap: pre-issued maintainer token minted without `wctl` via `docker compose exec` in the local `weppcloud` container (token not persisted in evidence artifact).
- Created smoke run: `exclusive-ding-dong/disturbed9002_wbt`
- Create redirect location: `/weppcloud/runs/exclusive-ding-dong/disturbed9002_wbt`
- Mutation job id: `ad4e8b93-b6aa-46c2-84f1-a13f5f808ae6`

## Maintainer Preflight Gate (Phase A)
Executed per canonical runbook command set (contract/route parity gate) before operator acceptance:
- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py ... tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> **251 passed**
- `python tools/check_endpoint_inventory.py` -> **Endpoint inventory check passed**
- `python tools/check_route_contract_checklist.py` -> **Route contract checklist check passed**
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> **2 passed**

## Machine-Safe Bootstrap Evidence
Bootstrap endpoint call:
- `POST /api/auth/rq-engine-operator-token` -> `200`
- redacted response excerpt:

```json
{
  "token_class": "user",
  "audience": "rq-engine",
  "requested_scopes": [
    "rq:status",
    "rq:enqueue"
  ],
  "granted_scopes": [
    "rq:status",
    "rq:enqueue"
  ],
  "expires_in": 900,
  "issued_at": 1775892802,
  "expires_at": 1775893702
}
```

Session-token compatibility check (redacted):

```json
{
  "token_class": "session",
  "runid": "exclusive-ding-dong",
  "config": "disturbed9002_wbt",
  "session_id": "<redacted-session-id>",
  "expires_at": 1776238402,
  "scopes": [
    "rq:read",
    "rq:status",
    "rq:enqueue",
    "rq:export"
  ],
  "audience": null
}
```

## API Call Evidence (UTC Method/Path/Status)

```text
2026-04-11T07:33:19Z | POST /create/ | 303 | create_run | body_file=/tmp/rq_operator_smoke_20260411T073319Z/create_run.json | location=/weppcloud/runs/exclusive-ding-dong/disturbed9002_wbt
2026-04-11T07:33:22Z | POST /api/auth/rq-engine-operator-token | 200 | operator_bootstrap | body_file=/tmp/rq_operator_smoke_20260411T073319Z/operator_bootstrap.json
2026-04-11T07:33:22Z | POST /api/runs/exclusive-ding-dong/disturbed9002_wbt/session-token | 200 | session_token_source | body_file=/tmp/rq_operator_smoke_20260411T073319Z/session_token_source.json
2026-04-11T07:33:22Z | GET /api/configs | 200 | configs | body_file=/tmp/rq_operator_smoke_20260411T073319Z/configs.json
2026-04-11T07:33:23Z | GET /api/endpoints | 200 | endpoints | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoints.json
2026-04-11T07:33:23Z | GET /api/endpoints/rq_engine_create/schema | 200 | endpoint_create_schema | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoint_create_schema.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/pipeline | 200 | pipeline | body_file=/tmp/rq_operator_smoke_20260411T073319Z/pipeline.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/readiness | 200 | readiness | body_file=/tmp/rq_operator_smoke_20260411T073319Z/readiness.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/controllers | 200 | controllers | body_file=/tmp/rq_operator_smoke_20260411T073319Z/controllers.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/controllers/watershed/schema | 200 | controller_watershed_schema | body_file=/tmp/rq_operator_smoke_20260411T073319Z/controller_watershed_schema.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/endpoints | 200 | endpoints_run | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoints_run.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/endpoints/rq_engine_build_climate/schema | 200 | endpoint_build_climate_schema | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoint_build_climate_schema.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/endpoints/rq_engine_build_climate/defaults | 200 | endpoint_build_climate_defaults | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoint_build_climate_defaults.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/endpoints/rq_engine_build_climate/errors | 200 | endpoint_build_climate_errors | body_file=/tmp/rq_operator_smoke_20260411T073319Z/endpoint_build_climate_errors.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/geospatial-metadata | 200 | geospatial_metadata | body_file=/tmp/rq_operator_smoke_20260411T073319Z/geospatial_metadata.json
2026-04-11T07:33:23Z | GET /api/runs/exclusive-ding-dong/disturbed9002_wbt/outputs | 200 | outputs | body_file=/tmp/rq_operator_smoke_20260411T073319Z/outputs.json
2026-04-11T07:33:23Z | POST /api/runs/exclusive-ding-dong/disturbed9002_wbt/session-token | 200 | session_token_bridge | body_file=/tmp/rq_operator_smoke_20260411T073319Z/session_token_bridge.json
2026-04-11T07:33:23Z | POST /api/runs/exclusive-ding-dong/disturbed9002_wbt/fork | 200 | fork_mutation | body_file=/tmp/rq_operator_smoke_20260411T073319Z/fork_mutation.json
2026-04-11T07:33:23Z | GET /api/jobstatus/ad4e8b93-b6aa-46c2-84f1-a13f5f808ae6 | 200 | jobstatus_initial | body_file=/tmp/rq_operator_smoke_20260411T073319Z/jobstatus_initial.json
2026-04-11T07:33:25Z | GET /api/jobstatus/ad4e8b93-b6aa-46c2-84f1-a13f5f808ae6 | 200 | jobstatus_second | body_file=/tmp/rq_operator_smoke_20260411T073319Z/jobstatus_second.json
```

## Revision/Freshness Parity Checks
Pipeline summary:

```json
{
  "domain": "orchestration",
  "revision": "runstate:exclusive-ding-dong:eb00298205b0",
  "vector": {
    "orchestration_revision": "runstate:exclusive-ding-dong:eb00298205b0",
    "metadata_revision": null,
    "outputs_revision": null
  },
  "updated_at": "2026-04-11T07:33:22Z",
  "data_state": "materialized",
  "data_updated_at": "2026-04-11T07:33:22Z"
}
```

Readiness summary:

```json
{
  "domain": "orchestration",
  "revision": "runstate:exclusive-ding-dong:eb00298205b0",
  "vector": {
    "orchestration_revision": "runstate:exclusive-ding-dong:eb00298205b0",
    "metadata_revision": null,
    "outputs_revision": null
  },
  "updated_at": "2026-04-11T07:33:22Z",
  "data_state": "materialized",
  "data_updated_at": "2026-04-11T07:33:22Z"
}
```

Geospatial summary:

```json
{
  "domain": "metadata",
  "revision": "runstate:exclusive-ding-dong:a18353c52796",
  "vector": {
    "orchestration_revision": null,
    "metadata_revision": "runstate:exclusive-ding-dong:a18353c52796",
    "outputs_revision": null
  },
  "updated_at": "2026-04-11T07:33:22Z",
  "data_state": "materialized",
  "data_updated_at": "2026-04-11T07:33:22Z"
}
```

Outputs summary:

```json
{
  "domain": "outputs",
  "revision": "runstate:exclusive-ding-dong:4374923e34a5",
  "vector": {
    "orchestration_revision": null,
    "metadata_revision": "runstate:exclusive-ding-dong:a18353c52796",
    "outputs_revision": "runstate:exclusive-ding-dong:4374923e34a5"
  },
  "updated_at": "2026-04-11T07:33:22Z",
  "data_state": "not_materialized",
  "data_updated_at": null
}
```

Observed parity invariants:
- `pipeline` and `readiness` share the same `run_state_domain=orchestration` and same `run_state_revision`.
- `geospatial-metadata` reports `run_state_domain=metadata` and aligns `run_state_vector.metadata_revision` to its `run_state_revision`.
- `outputs` reports `run_state_domain=outputs`, aligns `run_state_vector.outputs_revision` to its `run_state_revision`, and carries the current metadata revision in `run_state_vector.metadata_revision`.
- Snapshot freshness fields are coherent (`updated_at` non-null UTC, explicit `data_state`, and `data_updated_at` semantics).

## Mutation + Poll Evidence
Fork mutation response excerpt:

```json
{
  "job_id": "ad4e8b93-b6aa-46c2-84f1-a13f5f808ae6",
  "new_runid": "unbelted-thumb",
  "undisturbify": false
}
```

Terminal poll excerpt:

```json
{
  "job_id": "ad4e8b93-b6aa-46c2-84f1-a13f5f808ae6",
  "status": "finished",
  "started_at": "2026-04-11 07:33:23.562915",
  "ended_at": "2026-04-11T07:33:25Z",
  "progress": {
    "completed": 1,
    "total": 1,
    "unit": "jobs",
    "percent": 100.0,
    "updated_at": "2026-04-11T07:33:25Z"
  }
}
```

## Redaction and Handling Notes
- Raw bearer/session tokens were not persisted in this artifact.
- Token-bearing payloads were redacted to contract-shape fields only.
- Evidence records UTC timestamp + method + path + status for every operator call.
- Raw evidence directory for this run: `/tmp/rq_operator_smoke_20260411T073319Z`.
