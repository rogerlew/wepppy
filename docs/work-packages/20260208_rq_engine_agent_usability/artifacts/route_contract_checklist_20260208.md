# Route Contract Checklist (2026-02-08)

Checklist baseline for frozen `agent-facing` routes owned by `rq-engine`.

Guarded by:
- `tools/check_endpoint_inventory.py` (source route freeze parity)
- `tools/check_route_contract_checklist.py` (checklist row parity + non-empty contract fields)
- `tests/microservices/test_rq_engine_openapi_contract.py` (OpenAPI metadata/response contract + oversize budgets)

- Total frozen routes covered: **53**

## Contract Matrix

| Method | Path | Auth | Scope | Mutates | Execution | Required Responses | Contract Coverage |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/canceljob/{job_id}` | JWT Bearer | rq:status | mutating | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/culverts-wepp-batch/` | JWT Bearer | culvert:batch:submit | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/culverts-wepp-batch/{batch_uuid}/finalize` | JWT Bearer | culvert:batch:retry | mutating | async enqueue | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | JWT Bearer | culvert:batch:retry | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/jobinfo` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `GET` | `/api/jobinfo/{job_id}` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 404, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `GET` | `/api/jobstatus/{job_id}` | Open by default (`RQ_ENGINE_POLL_AUTH_MODE`) | `rq:status` when auth mode validates JWT | read-only | sync | `200, 401, 403, 404, 429, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_jobinfo.py` |
| `POST` | `/api/runs/{runid}/{config}/acquire-openet-ts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/acquire-rap-ts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/archive` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/checkout` | JWT Bearer | bootstrap:checkout | mutating | sync no queue | `200, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/bootstrap/commits` | JWT Bearer | bootstrap:read | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `GET` | `/api/runs/{runid}/{config}/bootstrap/current-ref` | JWT Bearer | bootstrap:read | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/enable` | JWT Bearer | bootstrap:enable | mutating | async enqueue | `200, 202, 400, 401, 403, 409, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/bootstrap/mint-token` | JWT Bearer | bootstrap:token:mint | mutating | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py`<br>`tests/microservices/test_rq_engine_bootstrap_routes.py` |
| `POST` | `/api/runs/{runid}/{config}/build-climate` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-landuse` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-soils` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/build-treatments` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/delete-archive` | JWT Bearer | rq:enqueue | mutating | sync no queue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/delete-omni-contrasts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/ermit` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/geodatabase` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/geopackage` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/prep_details` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `GET` | `/api/runs/{runid}/{config}/export/prep_details/` | JWT Bearer | rq:export | read-only | sync | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/fetch-dem-and-build-channels` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/fork` | Optional JWT; anonymous CAPTCHA path | `rq:enqueue` (if bearer token is used) | mutating | async enqueue | `200, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/post-dss-export-rq` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/prep-wepp-watershed` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/restore-archive` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 404, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-ash` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-debris-flow` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni-contrasts` | JWT Bearer | rq:enqueue | mutating | async enqueue | `202, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-omni-contrasts-dry-run` | JWT Bearer | rq:enqueue | read-only | sync no queue | `200, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
| `POST` | `/api/runs/{runid}/{config}/run-rhem` | JWT Bearer | rq:enqueue | mutating | async enqueue | `200, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |
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
| `POST` | `/create/` | JWT/rq_token or CAPTCHA | `rq:enqueue` (token-auth paths) | mutating | sync redirect | `303, 400, 401, 403, 500` | `tests/microservices/test_rq_engine_openapi_contract.py` |

## Notes

- This artifact tracks contract completeness for frozen agent-facing routes, not full behavioral test depth per endpoint.
- Polling routes remain open by policy (`RQ_ENGINE_POLL_AUTH_MODE=open`) and include `429` in required responses.
- Bootstrap routes require explicit Bootstrap scopes as documented in `docs/weppcloud-bootstrap-spec.md`.
