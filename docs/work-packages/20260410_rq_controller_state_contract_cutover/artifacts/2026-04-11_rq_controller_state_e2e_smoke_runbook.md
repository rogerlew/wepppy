# RQ Controller State End-to-End Smoke Runbook (Frozen Baseline)

## Purpose

This runbook verifies the row-8 frozen controller-state baseline end to end.
It covers:
- contract/guard preflight checks,
- route/checklist freeze parity,
- live API smoke over setup discovery plus run-scoped controller-state surfaces.

Baseline references:
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- `docs/schemas/rq-controller-state-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`

## Preconditions

- Working directory: `/workdir/wepppy`
- Dev stack running (`docker/docker-compose.dev.yml`).
- Valid bearer token with required scopes for target checks:
  - `rq:read` for read-only controller-state routes
  - `rq:status` required for the session-token bridge smoke step
- Accessible `runid/config` pair for run-scoped checks.
- Tools available: `wctl`, `python`, `curl`, `jq`.

Quick setup pointers:
- Token acquisition: `docs/schemas/rq-engine-agent-api-contract.md`
  (`## Dev-Agent Local Workflow`, mint via
  `POST /weppcloud/profile/mint-token`).
- `RUNID/CONFIG` source:
  - existing run URL (`/runs/{runid}/{config}`), or
  - create/fork flow described in
    `docs/schemas/rq-controller-state-contract.md` (`## Supported End-to-End Workflows`).

## Phase A: Automated Contract/Route Smoke (Required)

Run the consolidated contract smoke suite:

```bash
wctl run-pytest \
  tests/microservices/test_rq_engine_setup_discovery_routes.py \
  tests/microservices/test_rq_engine_orchestration_read_routes.py \
  tests/microservices/test_rq_engine_schema_defaults_routes.py \
  tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py \
  tests/microservices/test_rq_engine_upload_climate_routes.py \
  tests/microservices/test_rq_engine_upload_disturbed_routes.py \
  tests/microservices/test_rq_engine_watershed_routes.py \
  tests/microservices/test_rq_engine_errors_progress_outputs_routes.py \
  tests/microservices/test_rq_engine_auth_concurrency_routes.py \
  tests/microservices/test_rq_engine_auth.py \
  tests/microservices/test_rq_engine_session_routes.py \
  tests/microservices/test_rq_engine_openapi_contract.py \
  --maxfail=1

python tools/check_endpoint_inventory.py
python tools/check_route_contract_checklist.py
wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1
```

Expected outcomes:
- pytest command passes (current baseline reference: `248 passed`).
- `check_endpoint_inventory.py` prints `Endpoint inventory check passed`.
- `check_route_contract_checklist.py` prints `Route contract checklist check passed`.
- guard pytest command passes (`2 passed`).

## Phase B: Live API Surface Smoke (Manual)

Set environment variables:

```bash
export BASE_URL="http://localhost/rq-engine/api"
export TOKEN="<bearer-token>"
export RUNID="<existing-runid>"
export CONFIG="<existing-config>"
```

Setup discovery checks:

```bash
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/configs" | jq '.configs | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/endpoints" | jq '.operations | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/endpoints/rq_engine_create/schema" | jq '.operation_descriptor.operation_id'
```

Run-scoped orchestration + metadata checks:

```bash
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/pipeline" | jq '.steps | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/readiness" | jq '.next_actionable_steps'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/controllers" | jq '.controllers | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/controllers/watershed/schema" | jq '.controller'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/endpoints" | jq '.operations | length'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/schema" | jq '.operation_descriptor.operation_id'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/defaults" | jq '.operation_id'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/errors" | jq '.operation_id'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/geospatial-metadata" | jq '.runid'
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/outputs" | jq '.artifacts | length'
```

Session-token compatibility bridge check:

```bash
curl -sf -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/runs/$RUNID/$CONFIG/session-token" \
  -d '{}' | jq '.scopes'
```

Optional active-job poll check (if pipeline reports `active_job_id`):

```bash
ACTIVE_JOB_ID=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/runs/$RUNID/$CONFIG/pipeline" | jq -r '.steps[] | select(.active_job_id != null) | .active_job_id' | head -n1)
if [ -n "$ACTIVE_JOB_ID" ]; then
  curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/jobstatus/$ACTIVE_JOB_ID" | jq '.status'
fi
```

## Pass/Fail Criteria

Pass if all are true:
- Phase A commands pass with no failures.
- Setup discovery endpoints return `200` payloads with non-empty catalogs.
- Run-scoped endpoints (`pipeline`, `readiness`, controller/endpoint schema/default/error, `geospatial-metadata`, `outputs`) return `200` with contract-shaped payloads.
- Session-token endpoint returns `200` with a token/scopes payload.
- No unexpected `5xx` responses are observed.

Fail if any required command fails, parity checks report drift, or live API smoke returns unexpected `4xx/5xx` responses for valid inputs.

## Triage Links

- Contract baseline: `docs/schemas/rq-controller-state-contract.md`
- Agent API/auth baseline: `docs/schemas/rq-engine-agent-api-contract.md`
- Frozen route inventory: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- Frozen route checklist: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Cutover tracker evidence: `docs/work-packages/20260410_rq_controller_state_contract_cutover/tracker.md`
