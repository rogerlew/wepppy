# WEPPcloud Query Engine MCP API Specification

## OpenAPI Specification
- The machine-readable OpenAPI definition lives in `wepppy/query_engine/docs/mcp_openapi.yaml`. LLM agents and tooling can ingest it directly to discover endpoints, schemas, and authentication requirements.
- Update the OpenAPI file alongside this document when endpoints or payload contracts change.

## 1. Purpose and Scope
- Enable MCP-compatible LLM agents and tooling to explore, validate, and execute WEPPcloud Query Engine jobs in a safe and observable way.
- Provide a uniform JSON interface that mirrors the existing Starlette console features (run activation, schema browsing, preset payloads, query execution).
- Support both read-only catalogue discovery and opt-in query execution with clear permission boundaries.

## 2. Architectural Context
- The MCP API is delivered as part of the existing Starlette application under the `/mcp` URL prefix (behind the same reverse proxy as `/query-engine`).
- Each call is stateless and authenticated via bearer token. Tokens embed run-level scopes.
- The API builds on existing modules:
  - `query_engine.activate_query_engine` for activation.
  - `query_engine.resolve_run_context` for catalogue access.
  - `query_engine.run_query` for execution.
  - `query_engine.app.query_presets.QUERY_PRESETS` for curated examples.

## 3. Authentication and Authorization
- **Scheme**: `Authorization: Bearer <token>`.
- **Scopes**:
  - `runs:read` – discover accessible runs and catalogue metadata.
  - `runs:activate` – initiate catalogue activation.
  - `queries:validate` – call validation endpoint.
  - `queries:execute` – execute queries (implies validate).
- Tokens are mapped to a user identity and an allow-list of run IDs. All endpoints verify both scope and run ownership.
- Optional per-run rate limits are enforced per token to prevent abuse.

## 4. Resource Model

| Resource | Description |
| --- | --- |
| `Run` | A WEPPcloud run directory available to the user. |
| `CatalogEntry` | Filtered dataset metadata (path, schema, units, modified timestamp). |
| `PresetCollection` | Named example payloads grouped by category. |
| `QueryRequest` | Validated request to `run_query`. |
| `QueryValidation` | Normalized payload plus warnings returned by the validation endpoint. |
| `QueryExecute` | Execution result with records, schema, SQL, and runtime metadata. |
| `PromptTemplate` | Markdown guidance for LLM agents. |

## 5. Endpoints

| Method & Path | Description | Required Scope |
| --- | --- | --- |
| `GET /mcp/ping` | Health probe; returns service metadata. | none |
| `GET /mcp/runs` | List runs visible to the caller; supports `page[size]`, `page[number]`, `page[offset]` (aliases `page_size`, `page_number`, `page_offset`). | `runs:read` |
| `GET /mcp/runs/{run_id}` | Detailed run info (activation status, last refresh). | `runs:read` |
| `POST /mcp/runs/{run_id}/activate` | Trigger catalogue activation; returns activation job status. | `runs:activate` |
| `GET /mcp/runs/{run_id}/catalog` | Fetch catalogue subset; supports `include_fields`, `limit[datasets]`/`limit_datasets`, `limit[fields]`/`limit_fields`, `page[size]`/`page_size`, `page[number]`/`page_number`, `page[offset]`/`page_offset`. | `runs:read` |
| `GET /mcp/runs/{run_id}/presets` | Retrieve curated query presets. | `runs:read` |
| `GET /mcp/runs/{run_id}/prompt-template` | Hydrated Markdown prompt with schema snapshot and endpoint URLs. | `runs:read` |
| `POST /mcp/runs/{run_id}/queries/validate` | Validate payload; respond with normalized payload and warnings. | `queries:validate` |
| `POST /mcp/runs/{run_id}/queries/execute` | Execute payload; optional `dry_run` query parameter. | `queries:execute` |

- Every endpoint responds with JSON using: `{ "data": ..., "meta": ..., "errors": [...] }`.
- Errors include machine-readable `code` (`catalog_missing`, `validation_failed`, `permission_denied`, `rate_limited`, `activation_in_progress`, `internal_error`) and human `detail`.
- `GET` endpoints accept `page[size]`/`page_size`, `page[number]`/`page_number` for pagination; `sort` for ordering (e.g., `sort=-modified` on catalog).
- Run-level responses include both `links.query_execute` and `links.query_validate`; the legacy `links.query` is maintained as a deprecated alias for `links.query_execute` to avoid breaking existing clients.

## 6. Request / Response Contracts

### 6.1 `GET /mcp/runs`
```json
{
  "data": [
    {
      "id": "copacetic-note",
      "type": "run",
      "attributes": {
        "path": "/wc1/runs/co/copacetic-note",
        "activated": true,
        "last_catalog_refresh": "2024-05-07T16:33:22Z",
        "dataset_count": 84
      },
      "links": {
        "self": "https://host/query-engine/mcp/runs/copacetic-note",
        "catalog": "https://host/query-engine/mcp/runs/copacetic-note/catalog",
        "query": "https://host/query-engine/mcp/runs/copacetic-note/queries/execute",
        "query_execute": "https://host/query-engine/mcp/runs/copacetic-note/queries/execute",
        "query_validate": "https://host/query-engine/mcp/runs/copacetic-note/queries/validate",
        "activate": "https://host/query-engine/mcp/runs/copacetic-note/activate"
      }
    }
  ],
  "meta": {
    "page": {
      "size": 50,
      "number": 1,
      "total_pages": 3
    }
  }
}
```

### 6.2 `GET /mcp/runs/{id}`
- Returns a single run record with the same shape as `GET /mcp/runs`, plus `meta.catalog` stats when the catalogue is active.
- Errors:
  - `404` when the run is not visible to the current token.
  - `403` if the run exists but the token lacks `runs:read`.
```json
{
  "data": {
    "id": "copacetic-note",
    "type": "run",
    "attributes": {
      "path": "/wc1/runs/co/copacetic-note",
      "activated": true,
      "last_catalog_refresh": "2024-05-07T16:33:22Z",
      "dataset_count": 84
    },
    "links": {
      "self": "https://host/query-engine/mcp/runs/copacetic-note",
      "catalog": "https://host/query-engine/mcp/runs/copacetic-note/catalog",
      "query": "https://host/query-engine/mcp/runs/copacetic-note/queries/execute",
      "query_execute": "https://host/query-engine/mcp/runs/copacetic-note/queries/execute",
      "query_validate": "https://host/query-engine/mcp/runs/copacetic-note/queries/validate",
      "activate": "https://host/query-engine/mcp/runs/copacetic-note/activate"
    }
  },
  "meta": {
    "catalog": {
      "activated": true,
      "dataset_count": 84,
      "generated_at": "2024-05-07T16:33:22Z"
    }
  }
}
```

### 6.3 `GET /mcp/runs/{id}/catalog`
- Returns the dataset catalogue after applying prefix filtering and optional limits.
- Query parameters: `include_fields`, `limit[datasets]` (`limit_datasets` alias), `limit[fields]` (`limit_fields` alias), `page[size]` (`page_size` alias), `page[number]` (`page_number` alias), `page[offset]` (`page_offset` alias) (see §7).
- Errors:
  - `404` (`not_found`) when the run is not visible to the token.
  - `404` (`catalog_missing`) when the catalogue has not been generated.
  - `400` (`invalid_request`) for malformed boolean or limit values.

### 6.4 `POST /mcp/runs/{id}/queries/validate`
- Returns a normalized payload and warnings when validation succeeds.
- Requires `queries:validate` (or `queries:execute`) scope in addition to `runs:read`.
- `aggregations` entries can be supplied either as shorthand strings (rendered verbatim) or as objects defining `fn`/`column`, `expression`, or `sql`.
- `computed_columns` require an `alias` and exactly one of `sql`, `expression`, or `date_parts`.
- Errors:
  - `400` (`invalid_request`) for invalid JSON bodies.
  - `404` (`catalog_missing`) when the catalogue has not been generated.
  - `422` (`invalid_payload`, `dataset_missing`) for payload validation issues.
```json
{
  "data": {
    "type": "query_validation",
    "attributes": {
      "normalized_payload": {
        "datasets": [{"path": "datasets/one.parquet", "alias": "datasets_one"}],
        "limit": 10,
        "include_schema": true
      },
      "warnings": [],
      "missing_datasets": []
    }
  },
  "meta": {
    "catalog": {
      "generated_at": "2024-05-07T16:33:22Z",
      "dataset_count": 84
    }
  }
}
```

### 6.5 `POST /mcp/runs/{id}/queries/execute`
- Executes a validated payload and returns result records. Set `dry_run=true` to perform validation without execution.
- Requires `queries:execute` scope in addition to `runs:read`.
- `result.schema` entries mirror Arrow field metadata; `result.records` are truncated by `limit` unless `dry_run=true`.
- Errors mirror the validation endpoint plus:
  - `500` (`context_unavailable`, `execution_failed`) for runtime issues.
```json
{
  "data": {
    "type": "query_execute",
    "attributes": {
      "normalized_payload": { "datasets": [...], "limit": 25, "include_schema": true },
      "warnings": [],
      "dry_run": false,
      "result": {
        "records": [{"row": 1, "soil_loss": 0.42}],
        "row_count": 1,
        "schema": [{"name": "soil_loss", "type": "double"}],
        "sql": "SELECT ..."
      }
    }
  },
  "meta": {
    "catalog": {
      "generated_at": "2024-05-07T16:33:22Z",
      "dataset_count": 84
    },
    "execution": {
      "dry_run": false,
      "duration_ms": 123,
      "row_count": 1
    }
  }
}
```

## 7. Catalogue Filtering Rules
- Skip entries whose path starts with `.mypy_cache/`, `_query_engine/`, or any value configured in `IGNORED_CATALOG_PREFIXES`.
- `limit_fields` trims schema field listings per dataset; `limit_datasets` caps dataset count in the response.
- For each field include `name`, `type`, optional `units`, `description`.
- Provide `meta.catalog.filtered_count` so clients know the original dataset count.
- `/mcp/runs/{id}/catalog` query parameters:
  - `include_fields` (bool, default `true`) — when false, excludes schema information entirely.
  - `limit[datasets]` / `limit_datasets` — max number of datasets returned (after prefix filtering).
  - `limit[fields]` / `limit_fields` — max number of fields per dataset schema when `include_fields=true`.
  - `page[size]` / `page_size` and `page[number]` / `page_number` — paginate the filtered dataset list (defaults 50/1).
  - `page[offset]` / `page_offset` — zero-based offset alternative to `page[number]`.
- `filters` support operators `=`, `!=`, `<`, `<=`, `>`, `>=`, `LIKE`, `ILIKE`, `IN`, `NOT IN`, `BETWEEN`, `IS NULL`, and `IS NOT NULL`. Provide arrays for `IN`/`NOT IN` (any length) and `BETWEEN` (two values, inclusive bounds).

## 8. Activation Workflow
- `POST /mcp/runs/{id}/activate` responds with:
  ```json
  {
    "data": {
      "type": "activation_job",
      "id": "copacetic-note:20240507T1633Z",
      "attributes": {
        "status": "accepted",
        "submitted_at": "2024-05-07T16:33:22Z"
      },
      "links": {
        "status": "https://host/query-engine/mcp/runs/copacetic-note"
      }
    },
    "meta": {
      "poll_after_seconds": 10
    }
  }
  ```
- If activation is already running, return `202` with `status: "in_progress"` and include both a `Retry-After` header and `meta.poll_after_seconds`.
- A `409` response is under consideration for clients that prefer an immediate conflict signal instead of polling; the current behaviour remains `202 Accepted`.
- Upon completion, `GET /mcp/runs/{id}` reflects updated `last_catalog_refresh`.

## 9. Prompt Template Endpoint
- Returns Markdown similar to the current console template.
- Injects:
  - `run_id`
  - `query_endpoint` (full URL)
  - `schema_snapshot` (respecting dataset/field limits)
  - Default payload sample (first dataset or preset)
  - Requirements and pipeline bullet lists
- The template is sourced from `query_engine/app/prompt_templates/llm_query_prompt.md` to keep parity with the UI.

## 10. Error Handling
- Standard HTTP codes:
  - `400` validation errors (malformed payload).
  - `401` unauthenticated.
  - `403` insufficient scope or run access.
  - `404` run or dataset not found.
  - `409` activation conflict.
  - `422` payload schema mismatch.
  - `429` throttled.
  - `500` unexpected server error.
- Include `trace_id` in `meta` for observability.

## 11. Monitoring & Logging
- Tag every request with `mcp.endpoint`, `mcp.scope`, `run_id`, and `trace_id`.
- Log activation outcomes and query execution timing histogram.
- Emit Prometheus metrics: request counts per endpoint, validation failures, execution duration, activation failures.

## 12. Rate Limiting & Payload Limits
- Default per-token limits: 120 requests/minute, 5 concurrent query executions.
- Maximum payload size: 256 KB JSON body.
- Maximum result size before streaming requirement: 5 MB.
- Timeouts: validation 5s, activation 300s, query execution 120s (extendable via config).

## 13. Security Considerations
- Reject traversal attempts by normalizing run IDs.
- Ensure JSON parsing uses safe limits (e.g., `json.loads` with size guard).
- Sanitize errors to avoid leaking filesystem paths beyond run directory.
- All URLs incorporate reverse proxy `root_path` to function behind `/query-engine`.

## 14. Open Questions / Follow-Ups
- Decide on OAuth vs static tokens for MCP.
- Determine whether streaming should use SSE or WebSockets.
- Evaluate integration tests against staging MCP client before production roll-out.
