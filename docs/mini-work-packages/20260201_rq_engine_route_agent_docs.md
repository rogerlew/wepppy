# Mini Work Package: RQ Engine Route Agent Documentation Pass
Status: Draft
Last Updated: 2026-02-01
Primary Areas: `wepppy/microservices/rq_engine/*.py`, `wepppy/weppcloud/routes/**`, `docs/schemas/rq-response-contract.md`, `docs/dev-notes/auth-token.spec.md`, `docs/dev-notes/endpoint_security_notes.md`, `wepppy/weppcloud/routes/rq/api/doc/*.md`

## Objective
Provide agent-ready route documentation with precise parameter specs and runnable examples for every rq-engine and run-scoped Flask route.

## Cursory Observations
- Route docs are uneven: some endpoints have README coverage, while most rq-engine modules have none.
- Existing docs list endpoints but often skip parameter constraints, example errors, and auth requirements.
- Examples frequently omit Authorization headers and session-token setup.
- Several docs hardcode a host; placeholders are safer for agents.

## Scope
- Inventory rq-engine route modules and run-scoped Flask blueprints (nodb_api, batch_runner, rq job dashboard, etc.).
- For each route, add or expand docs with parameter details and examples.
- Align success and error payloads to `docs/schemas/rq-response-contract.md`.
- Call out auth scopes, run access requirements, and session token issuance where needed.

## Non-goals
- Changing route behavior or payloads.
- Refactoring controller or client code.
- Producing a full OpenAPI spec.

## Route Documentation Guidelines (Apply to Each Route)

### Required Sections (Per Route or Route Group)
1. Route summary: path, method, purpose, idempotency, and side effects.
2. Auth: required scopes (`rq:enqueue`, `rq:status`, `rq:export`), token class, and run-access checks.
3. Parameters: table with name, location (path/query/header/body/form), type, required, default, allowed values, units, and notes.
4. Request examples:
   - Minimal success example (curl).
   - Full example with optional parameters.
   - Upload example with `curl -F` and field names when applicable.
5. Responses:
   - Success examples with status codes.
   - Job enqueue responses using canonical keys (`job_id`, `job_ids`, `status_url`, `message`).
   - Error responses using the canonical error payload (include at least one 4xx and one 5xx example when meaningful).
6. Outputs: files generated, output directories, or downstream routes to poll.
7. Related routes: jobstatus/jobinfo, downloads, follow-on tasks, or paired view routes.

### Parameter Documentation Rules
- Describe all path vars (`runid`, `config`, `job_id`) and their format expectations.
- Clarify boolean parsing rules (`true/false/on/off/1/0`) and list/array ordering.
- For enums, list allowed values or link to the defining enum.
- For numeric ranges, include min/max and units.
- For nested payloads, show the full JSON shape and which keys are optional.

### Example Rules
- Use placeholders (`https://{host}`, `{runid}`, `{config}`) instead of hardcoded hosts.
- Include `Authorization: Bearer <token>` or session-token guidance when required.
- For run-scoped endpoints, show `/rq-engine/api/runs/{runid}/{config}/...`.
- For job polling, show `GET /rq-engine/api/jobstatus/{job_id}` or `jobinfo` usage.
- Keep examples compact; trim large payloads with comments.

### Error and Edge Cases
- Use status-code-first semantics and the canonical error payload from `docs/schemas/rq-response-contract.md`.
- Document `not_found` for job polling where applicable.
- Note retry/idempotency behavior and what constitutes safe re-submission.

### Agent-Focused Notes
- Call out expected runtimes, timeouts, and large file size limits.
- Note temporary artifacts, cleanup expectations, and output locations.
- Flag prerequisites (for example, DEM required before watershed build routes).
- Identify read-only vs mutating routes (lock-required vs query-only).

## Suggested Doc Locations
- Add `README.md` in `wepppy/microservices/rq_engine/` as the primary index.
- Keep route-group README files alongside Flask blueprints (existing pattern in `wepppy/weppcloud/routes/**/README.md`).
- Store public API endpoint docs under `wepppy/weppcloud/routes/rq/api/doc/` when needed.

## Implementation Plan (Per Route Pass)
1. Build a route inventory from `wepppy/microservices/rq_engine/*.py` and `wepppy/weppcloud/routes/**`.
2. Add or expand README sections using the guidelines above.
3. Add parameter tables and examples that match `parse_request_payload()` handling.
4. Cross-link to tests, controller docs, and relevant dev notes.
5. Spot-check error payloads against `docs/schemas/rq-response-contract.md`.

## Validation
- Every route has a parameter table and at least one example request/response.
- Auth scopes and run-access rules are explicit and consistent.
- Error payload examples match the canonical schema.
- New docs use American English and avoid hardcoded hosts.

## Query Engine: Agent-Friendly Endpoints

The query-engine runs as a standalone Starlette service behind Caddy at `/query-engine`. See `wepppy/query_engine/README.md` for full documentation.

### Key Endpoints for Agents

| Route | Method | Purpose |
|-------|--------|---------|
| `/query-engine/runs/{runid}/{config}/schema` | GET | List available datasets with schema metadata |
| `/query-engine/runs/{runid}/{config}/query` | POST | Execute a query (JSON payload) |
| `/query-engine/runs/{runid}/{config}/query` | GET | Interactive console (HTML) |
| `/query-engine/runs/{runid}/{config}/activate` | POST | Generate catalog from run directory |

### Integration with /files API

Agents can discover queryable datasets by combining the `/files` API with query-engine:

```
1. GET /weppcloud/runs/{runid}/{config}/files/_query_engine/
   → Check if catalog.json exists (run is activated)

2. GET /weppcloud/runs/{runid}/{config}/files/wepp/output/?pattern=*.parquet
   → Discover available parquet files

3. POST /query-engine/runs/{runid}/{config}/query
   → Query discovered datasets with filters, joins, aggregations
```

### Reverse Proxy Configuration

The Caddy config routes `/query-engine*` to the service at port 8041:
- `handle_path` strips `/query-engine` prefix before forwarding
- `X-Forwarded-Prefix` header tells the service its external mount point
- Read timeout is 3 minutes (for large queries)

### Notes
- The query-engine is **read-only** and cannot modify datasets
- Each query runs in an isolated DuckDB connection
- Catalog must be activated before querying (POST to `/activate`)
- MCP routes under `/mcp` are designed for future authenticated access

## Follow-ups
- Consider a consolidated route index in `docs/` if agents need a single entry point.
- Optionally add a script to flag routes without doc sections.
