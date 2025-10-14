# WEPPcloud Query Engine MCP API Specification

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
| `Preset` | Named example payload with description. |
| `QueryRequest` | Validated request to `run_query`. |
| `QueryValidation` | Normalized payload plus warnings returned by the validation endpoint. |
| `QueryResult` | Execution result with records, schema, SQL, and runtime information. |
| `PromptTemplate` | Markdown guidance for LLM agents. |

## 5. Endpoints

| Method & Path | Description | Required Scope |
| --- | --- | --- |
| `GET /mcp/ping` | Health probe; returns service metadata. | none |
| `GET /mcp/runs` | List runs visible to the caller (pagination, filtering). | `runs:read` |
| `GET /mcp/runs/{run_id}` | Detailed run info (activation status, last refresh). | `runs:read` |
| `POST /mcp/runs/{run_id}/activate` | Trigger catalogue activation; returns activation job status. | `runs:activate` |
| `GET /mcp/runs/{run_id}/catalog` | Fetch catalogue subset; supports `include_fields`, `limit_datasets`, `limit_fields`. | `runs:read` |
| `GET /mcp/runs/{run_id}/presets` | Retrieve curated query presets. | `runs:read` |
| `GET /mcp/runs/{run_id}/prompt-template` | Hydrated Markdown prompt with schema snapshot and endpoint URLs. | `runs:read` |
| `POST /mcp/runs/{run_id}/queries/validate` | Validate payload; respond with normalized payload and warnings. | `queries:validate` |
| `POST /mcp/runs/{run_id}/queries/execute` | Execute payload; optional `dry_run` query parameter. | `queries:execute` |

- Every endpoint responds with JSON using: `{ "data": ..., "meta": ..., "errors": [...] }`.
- Errors include machine-readable `code` (`catalog_missing`, `validation_failed`, `permission_denied`, `rate_limited`, `activation_in_progress`, `internal_error`) and human `detail`.
- `GET` endpoints accept `page[size]`, `page[number]` for pagination; `sort` for ordering (e.g., `sort=-modified` on catalog).

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
        "catalog": "https://host/query-engine/mcp/runs/copacetic-note/catalog"
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

### 6.2 `POST /mcp/runs/{id}/queries/validate`
Request body:
```json
{
  "payload": {
    "datasets": ["ag_fields/soil_loss.parquet"],
    "limit": 5,
    "include_schema": true,
    "aggregations": [{"sql": "SUM(fields.soil_loss)", "alias": "total_soil_loss"}]
  }
}
```

Response:
```json
{
  "data": {
    "type": "query_validation",
    "attributes": {
      "normalized_payload": { "datasets": [...], "limit": 5, "include_schema": true },
      "warnings": [],
      "missing_datasets": [],
      "missing_columns": []
    }
  },
  "meta": {
    "execution": {
      "validation_ms": 12
    }
  }
}
```

- If validation fails, `errors` contains entries with `code` (`missing_dataset`, `column_not_found`, `schema_missing`) and `detail`.
- `dry_run` query parameter on execute returns `meta.execution.estimates` and skips actual computation.
- Execution responses may include `data.attributes.stream_url` if the client requests streaming (`Prefer: respond-async`).

## 7. Catalogue Filtering Rules
- Skip entries whose path starts with `.mypy_cache/`, `_query_engine/`, or any value configured in `IGNORED_CATALOG_PREFIXES`.
- `limit_fields` trims schema field listings per dataset; `limit_datasets` caps dataset count in the response.
- For each field include `name`, `type`, optional `units`, `description`.
- Provide `meta.catalog.filtered_count` so clients know the original dataset count.

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
