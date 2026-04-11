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
- Operator-path tools: `python`, `curl`, `jq`.
- Maintainer preflight tools: `wctl` (required for Phase A only).

Quick setup pointers:
- Token acquisition: `docs/schemas/rq-engine-agent-api-contract.md`
  (`## Dev-Agent Local Workflow`, mint via
  `POST /weppcloud/profile/mint-token`).
- Machine-safe operator bootstrap (shipped):
  - `POST /weppcloud/api/auth/rq-engine-operator-token`
  - Bearer-auth only, scope-constrained minting (`requested_scopes`),
    rate-limited, and audited.
  - Request only scopes present on the source bearer token. Example:
    source bearer with `rq:status` only + `requested_scopes=["rq:read"]` returns
    `403`; use `requested_scopes=["rq:status"]`.
  - Source bearer token must include `jti`; revoked tokens are rejected.
  - Revocation backend unavailability returns `503` (retryable).
  - Use this path for non-browser/operator flows when a pre-issued
    bearer token is available.
- `RUNID/CONFIG` source:
  - existing run URL (`/runs/{runid}/{config}`), or
  - create/fork flow described in
    `docs/schemas/rq-controller-state-contract.md` (`## Supported End-to-End Workflows`).
  - create route path is canonical `POST /create/`; runtime alias
    `POST /api/create/` is also accepted for operator compatibility.

## Phase A: Maintainer Contract/Route Preflight

Required when maintaining/updating contract surfaces. API operators running
smoke without `wctl` SHOULD use most recent CI evidence for this phase and then
execute Phase B.

Operator-path CI evidence rule (when skipping local Phase A):
- CI evidence MUST be for the exact commit SHA under test.
- Required jobs MUST be green for the workflow that runs the Phase A command
  set.
- Evidence MUST include CI run URL/ID and completion timestamp recorded in the
  Phase B evidence log.

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
- pytest command exits `0` (exact pass count may evolve as tests are added or retired).
- `check_endpoint_inventory.py` prints `Endpoint inventory check passed`.
- `check_route_contract_checklist.py` prints `Route contract checklist check passed`.
- guard pytest command exits `0`.

## Phase B: Live API Surface Smoke (Operator Path)

Set environment variables:

```bash
export BASE_URL="http://localhost/rq-engine/api"
export TOKEN="<bearer-token>"
export RUNID="<existing-runid>"
export CONFIG="<existing-config>"
```

Security notes:
- `http://localhost` is local-dev only. For any non-local host, use `https://`.
- Avoid persisting bearer tokens in shell history or plaintext logs.

Evidence capture (required):

```bash
set -euo pipefail
umask 077
export EVIDENCE_LOG="./rq_controller_state_smoke_$(date -u +%Y%m%dT%H%M%SZ).log"
export EVIDENCE_TMP_DIR="$(mktemp -d /tmp/rq_controller_state_smoke.XXXXXX)"
trap 'rm -rf "$EVIDENCE_TMP_DIR"' EXIT
api_call() {
  method="$1"; path="$2"; label="$3"; body="${4:-}"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  url="$BASE_URL$path"
  body_file="$EVIDENCE_TMP_DIR/${label}.json"
  if [ -n "$body" ]; then
    code="$(curl -sS -X "$method" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$body" -o "$body_file" -w '%{http_code}' "$url")"
  else
    code="$(curl -sS -X "$method" -H "Authorization: Bearer $TOKEN" -o "$body_file" -w '%{http_code}' "$url")"
  fi
  LAST_BODY_FILE="$body_file"
  echo "$ts | $method $path | $code | $label | body_file=$body_file" | tee -a "$EVIDENCE_LOG"
  case "$code" in
    2*) ;;
    *)
      echo "$ts | ERROR non-2xx for $label ($method $path): $code" | tee -a "$EVIDENCE_LOG" >&2
      return 1
      ;;
  esac
}
show_body_redacted() {
  jq 'if type=="object" then del(.token, .access_token, .refresh_token, .id_token, .session_token, .browse_token) else . end' "$1"
}
```

Use `api_call` (or equivalent logging) for each endpoint invocation so every
request is captured as UTC `method/path/status` with redacted payload handling.
Do not print raw token-bearing response bodies.
Temporary body files are deleted automatically on shell exit by the trap above.

Setup discovery checks:

```bash
api_call GET "/configs" "configs"
jq '.configs | length' "$LAST_BODY_FILE"

api_call GET "/endpoints" "endpoints"
jq '.operations | length' "$LAST_BODY_FILE"

api_call GET "/endpoints/rq_engine_create/schema" "endpoint_create_schema"
jq '.operation_descriptor.operation_id' "$LAST_BODY_FILE"
```

Run-scoped orchestration + metadata checks:

```bash
api_call GET "/runs/$RUNID/$CONFIG/pipeline" "pipeline"
jq '.steps | length' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/readiness" "readiness"
jq '.next_actionable_steps' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/controllers" "controllers"
jq '.controllers | length' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/controllers/watershed/schema" "controller_watershed_schema"
jq '.controller' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/endpoints" "endpoints_run"
jq '.operations | length' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/schema" "endpoint_build_climate_schema"
jq '.operation_descriptor.operation_id' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/defaults" "endpoint_build_climate_defaults"
jq '.operation_id' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/endpoints/rq_engine_build_climate/errors" "endpoint_build_climate_errors"
jq '.operation_id' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/geospatial-metadata" "geospatial_metadata"
jq '.runid' "$LAST_BODY_FILE"

api_call GET "/runs/$RUNID/$CONFIG/outputs" "outputs"
jq '.artifacts | length' "$LAST_BODY_FILE"
```

Session-token compatibility bridge check:

```bash
api_call POST "/runs/$RUNID/$CONFIG/session-token" "session_token_bridge" '{}'
show_body_redacted "$LAST_BODY_FILE" | jq '.scopes'
```

Optional active-job poll check (if pipeline reports `active_job_id`):

```bash
api_call GET "/runs/$RUNID/$CONFIG/pipeline" "pipeline_for_active_job"
ACTIVE_JOB_ID=$(jq -r '.steps[] | select(.active_job_id != null) | .active_job_id' "$LAST_BODY_FILE" | head -n1)
if [ -n "$ACTIVE_JOB_ID" ]; then
  api_call GET "/jobstatus/$ACTIVE_JOB_ID" "jobstatus_active"
  jq '.status' "$LAST_BODY_FILE"
fi
```

## Pass/Fail Criteria

Pass if all are true:
- Phase A commands pass with no failures (maintainer path) or latest CI evidence
  shows passing Phase A equivalents (operator path without `wctl`).
- Setup discovery endpoints return `200` payloads with non-empty catalogs.
- Run-scoped endpoints (`pipeline`, `readiness`, controller/endpoint schema/default/error, `geospatial-metadata`, `outputs`) return `200` with contract-shaped payloads.
- Session-token endpoint returns `200` with a token/scopes payload.
- No unexpected `5xx` responses are observed.
- Evidence log captures UTC `method/path/status` for all Phase B calls with
  sensitive values redacted.
- If Phase A was skipped locally, CI evidence URL/ID + timestamp for the exact
  commit SHA under test is recorded in the evidence log.

Fail if any required command fails, parity checks report drift, or live API smoke returns unexpected `4xx/5xx` responses for valid inputs.

## Triage Links

- Contract baseline: `docs/schemas/rq-controller-state-contract.md`
- Agent API/auth baseline: `docs/schemas/rq-engine-agent-api-contract.md`
- Frozen route inventory: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- Frozen route checklist: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Cutover tracker evidence: `docs/work-packages/20260410_rq_controller_state_contract_cutover/tracker.md`
