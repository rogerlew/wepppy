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
| `GET /mcp/runs/{runid}` | Detailed run info (activation status, last refresh). | `runs:read` |
| `POST /mcp/runs/{runid}/activate` | Trigger catalogue activation; returns activation job status. | `runs:activate` |
| `GET /mcp/runs/{runid}/catalog` | Fetch the curated catalogue for a run (full dataset list, excluding internal files); supports `include_fields` and `limit[fields]` to tune schema verbosity. | `runs:read` |
| `GET /mcp/runs/{runid}/presets` | Retrieve curated query presets. | `runs:read` |
| `GET /mcp/runs/{runid}/prompt-template` | Hydrated Markdown prompt with schema snapshot and endpoint URLs. | `runs:read` |
| `POST /mcp/runs/{runid}/queries/validate` | Validate payload; respond with normalized payload and warnings. | `queries:validate` |
| `POST /mcp/runs/{runid}/queries/execute` | Execute payload; optional `dry_run` query parameter. | `queries:execute` |

- Every endpoint responds with JSON using: `{ "data": ..., "meta": ..., "errors": [...] }`.
- Errors include machine-readable `code` (`catalog_missing`, `validation_failed`, `permission_denied`, `rate_limited`, `activation_in_progress`, `internal_error`) and human `detail`.
- `GET` endpoints return metadata that includes the original catalogue totals and a trace identifier for diagnostics.
- Run-level responses include both `links.query_execute` and `links.query_validate`; the legacy `links.query` is maintained as a deprecated alias for `links.query_execute` to avoid breaking existing clients.

## 6. Request / Response Contracts

### 6.1 `GET /mcp/runs/{runid}`
- Returns a single run record including catalogue status metadata when available.
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

### 6.2 `GET /mcp/runs/{runid}/catalog`
- Returns the curated dataset catalogue (internal files such as `ash/H*.parquet` are excluded automatically).
- Query parameters: `include_fields` to toggle schema hydration and `limit[fields]` (`limit_fields`) to cap the number of fields per dataset in the response.
- Errors:
  - `404` (`not_found`) when the run is not visible to the token.
  - `404` (`catalog_missing`) when the catalogue has not been generated.
  - `400` (`invalid_request`) for malformed boolean or limit values.

### 6.3 `POST /mcp/runs/{runid}/queries/validate`
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

### 6.4 `POST /mcp/runs/{runid}/queries/execute`
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
- Entire `ash` datasets (e.g., `ash/` parquet outputs, `ash.nodb`) are excluded to keep catalogues concise.
- `limit_fields` trims schema field listings per dataset; all datasets are always returned.
- Provide `meta.catalog.total`, `meta.catalog.filtered`, and `meta.catalog.returned` so clients know how many items were produced and removed.
- `/mcp/runs/{runid}/catalog` query parameters:
  - `include_fields` (bool, default `true`) — when false, excludes schema information entirely.
  - `limit[fields]` / `limit_fields` — max number of fields per dataset schema when `include_fields=true`.
- `filters` support operators `=`, `!=`, `<`, `<=`, `>`, `>=`, `LIKE`, `ILIKE`, `IN`, `NOT IN`, `BETWEEN`, `IS NULL`, and `IS NOT NULL`. Provide arrays for `IN`/`NOT IN` (any length) and `BETWEEN` (two values, inclusive bounds).

## 8. Activation Workflow
- `POST /mcp/runs/{runid}/activate` responds with:
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
- When the job is accepted but still running, the API returns `202 Accepted`, sets a `Retry-After` header, and includes `meta.poll_after_seconds` to guide status polling.
- If activation is already running, return `202` with `status: "in_progress"` and include both a `Retry-After` header and `meta.poll_after_seconds`.
- A `409` response is under consideration for clients that prefer an immediate conflict signal instead of polling; the current behaviour remains `202 Accepted`.
- Upon completion, `GET /mcp/runs/{runid}` reflects updated `last_catalog_refresh`.

## 9. Prompt Template Endpoint
- Returns Markdown similar to the current console template.
- Injects:
  - `runid`
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
- Tag every request with `mcp.endpoint`, `mcp.scope`, `runid`, and `trace_id`.
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

---

# Query Construction Guide for Humans

This section provides practical guidance for constructing queries against the WEPPcloud Query Engine. The query engine exposes watershed modeling outputs (landuse, soils, climate, WEPP results) as queryable datasets using DuckDB-powered SQL generation.

## Quick Start

### Minimal Query
The simplest query fetches all columns from a single dataset:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "limit": 25
}
```

### Adding Schema Information
Include schema metadata to see column types and structure:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "limit": 25,
  "include_schema": true
}
```

### Viewing Generated SQL
Inspect the SQL generated by the query engine for debugging:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "limit": 25,
  "include_sql": true
}
```

## Core Query Structure

A query payload is a JSON object with these top-level properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `datasets` | array | **Yes** | One or more dataset paths or dataset objects |
| `columns` | array | No | Column selection with optional aliases (defaults to `*`) |
| `filters` | array | No | WHERE clause conditions |
| `joins` | array | No | Join specifications (required if multiple datasets) |
| `group_by` | array | No | GROUP BY column list |
| `aggregations` | array | No | Aggregate functions (SUM, COUNT, AVG, etc.) |
| `order_by` | array | No | ORDER BY expressions |
| `computed_columns` | array | No | Calculated columns with SQL expressions |
| `limit` | integer | No | Maximum rows to return |
| `include_schema` | boolean | No | Include schema metadata in response |
| `include_sql` | boolean | No | Include generated SQL in response |
| `reshape` | object | No | Reshape results (timeseries transformations) |

## Dataset Selection

### Simple Path Reference
Reference datasets by their catalog path:
```json
{
  "datasets": ["landuse/landuse.parquet"]
}
```

### Dataset with Alias
Provide explicit aliases for clarity (especially useful in joins):
```json
{
  "datasets": [
    {
      "path": "landuse/landuse.parquet",
      "alias": "lu"
    }
  ]
}
```

### Selecting Specific Columns from Dataset
Limit which columns are read from a dataset (improves performance):
```json
{
  "datasets": [
    {
      "path": "landuse/landuse.parquet",
      "alias": "lu",
      "columns": ["TopazID", "key", "desc", "area"]
    }
  ]
}
```

### Multiple Datasets (Requires Joins)
When querying multiple datasets, you **must** specify joins:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [
    {
      "left": "lu",
      "right": "s",
      "on": ["TopazID"]
    }
  ]
}
```

## Column Selection

### All Columns
Omit the `columns` property or use an empty array to select all columns:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "limit": 10
}
```

### Specific Columns
List column names to return only those columns:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "columns": ["TopazID", "key", "desc", "area"],
  "limit": 10
}
```

### Column Aliases
Use SQL `AS` syntax to rename columns in the result:
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": [
    "lu.TopazID AS topaz_id",
    "lu.desc AS landuse_description",
    "lu.area AS area_sq_m"
  ],
  "limit": 10
}
```

### Qualified Column Names
Always qualify columns with their dataset alias when using multiple datasets:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [{"left": "lu", "right": "s", "on": ["TopazID"]}],
  "columns": [
    "lu.TopazID",
    "lu.desc AS landuse",
    "s.simple_texture AS soil_texture"
  ],
  "limit": 10
}
```

### Handling Reserved SQL Keywords
If a column name is a SQL reserved word (like `desc`, `order`, `select`), qualify it with the dataset alias:
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["lu.desc AS description"],
  "limit": 10
}
```

## Filtering Data

Filters define WHERE clause conditions. Each filter is an object with `column`, `operator`, and (usually) `value`.

### Supported Operators

| Operator | Description | Value Type | Example |
|----------|-------------|------------|---------|
| `=` | Equals | scalar | `{"column": "key", "operator": "=", "value": 42}` |
| `!=` | Not equals | scalar | `{"column": "key", "operator": "!=", "value": 42}` |
| `<` | Less than | scalar | `{"column": "area", "operator": "<", "value": 1000}` |
| `<=` | Less than or equal | scalar | `{"column": "area", "operator": "<=", "value": 1000}` |
| `>` | Greater than | scalar | `{"column": "area", "operator": ">", "value": 500}` |
| `>=` | Greater than or equal | scalar | `{"column": "area", "operator": ">=", "value": 500}` |
| `LIKE` | Pattern match | string | `{"column": "desc", "operator": "LIKE", "value": "%Forest%"}` |
| `ILIKE` | Case-insensitive pattern | string | `{"column": "desc", "operator": "ILIKE", "value": "%forest%"}` |
| `IN` | In list | array | `{"column": "key", "operator": "IN", "value": [42, 43, 45]}` |
| `NOT IN` | Not in list | array | `{"column": "key", "operator": "NOT IN", "value": [11, 12]}` |
| `BETWEEN` | Range (inclusive) | 2-element array | `{"column": "area", "operator": "BETWEEN", "value": [100, 1000]}` |
| `IS NULL` | Null check | none | `{"column": "cancov_override", "operator": "IS NULL"}` |
| `IS NOT NULL` | Not null check | none | `{"column": "cancov_override", "operator": "IS NOT NULL"}` |

### Basic Filter Examples

**Single equality filter:**
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "filters": [
    {"column": "key", "operator": "=", "value": 42}
  ],
  "limit": 10
}
```

**Multiple filters (AND logic):**
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "filters": [
    {"column": "lu.key", "operator": "=", "value": 42},
    {"column": "lu.cancov", "operator": "<", "value": 0.6}
  ],
  "limit": 50
}
```

**IN operator (multiple values):**
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "filters": [
    {"column": "key", "operator": "IN", "value": [105, 118, 42]}
  ],
  "order_by": ["TopazID"],
  "limit": 100
}
```

**BETWEEN operator (range):**
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "filters": [
    {"column": "area", "operator": "BETWEEN", "value": [100, 1000]}
  ],
  "limit": 50
}
```

**LIKE operator (pattern matching):**
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "filters": [
    {"column": "desc", "operator": "LIKE", "value": "%Forest%"}
  ],
  "limit": 50
}
```

**NULL checks:**
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "filters": [
    {"column": "cancov_override", "operator": "IS NOT NULL"}
  ],
  "limit": 50
}
```

### Type Coercion
The query engine automatically coerces filter values based on the column's data type from the catalog schema. For example, if `key` is an `int64`, the string `"42"` in a filter value will be coerced to integer `42`.

## Joining Datasets

When querying multiple datasets, you must define how they relate via joins.

### Simple Join (Same Column Name)
When join columns have the same name in both tables:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [
    {
      "left": "lu",
      "right": "s",
      "on": ["TopazID"]
    }
  ],
  "columns": ["lu.TopazID", "lu.desc", "s.simple_texture"],
  "limit": 10
}
```

### Join with Different Column Names
When join columns have different names:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "some_other_dataset.parquet", "alias": "other"}
  ],
  "joins": [
    {
      "left": "lu",
      "right": "other",
      "left_on": ["TopazID"],
      "right_on": ["hillslope_id"]
    }
  ],
  "limit": 10
}
```

### Multi-Column Joins
Join on multiple columns simultaneously:
```json
{
  "datasets": [
    {"path": "dataset1.parquet", "alias": "d1"},
    {"path": "dataset2.parquet", "alias": "d2"}
  ],
  "joins": [
    {
      "left": "d1",
      "right": "d2",
      "left_on": ["year", "month"],
      "right_on": ["year", "month"]
    }
  ],
  "limit": 10
}
```

### Join Types
Specify the join type with the `type` property:

| Join Type | SQL | Description |
|-----------|-----|-------------|
| `inner` (default) | `INNER JOIN` | Only matching rows from both tables |
| `left` | `LEFT JOIN` | All rows from left, matching from right |
| `right` | `RIGHT JOIN` | All rows from right, matching from left |
| `full` / `outer` | `FULL OUTER JOIN` | All rows from both tables |

```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [
    {
      "left": "lu",
      "right": "s",
      "on": ["TopazID"],
      "type": "left"
    }
  ],
  "limit": 10
}
```

### Multiple Joins (Chain)
Join three or more datasets by chaining joins:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"},
    {"path": "climate/daymet_1986-2023.parquet", "alias": "c"}
  ],
  "joins": [
    {"left": "lu", "right": "s", "on": ["TopazID"]},
    {"left": "s", "right": "c", "on": ["TopazID"]}
  ],
  "columns": ["lu.TopazID", "lu.desc", "s.simple_texture", "c.year"],
  "limit": 10
}
```

## Aggregations

Aggregations compute summary statistics. When using aggregations, non-aggregated columns must appear in `group_by`.

### Aggregate Functions

Common aggregate functions:
- `SUM(column)` - Sum of values
- `COUNT(column)` or `COUNT(*)` - Count of rows
- `AVG(column)` - Average of values
- `MIN(column)` - Minimum value
- `MAX(column)` - Maximum value
- `STDDEV(column)` - Standard deviation
- `ANY_VALUE(column)` - Arbitrary value from group (useful for grouping)

### Aggregation Specification Formats

**Shorthand string (SQL expression rendered as-is):**
```json
{
  "aggregations": ["SUM(area)", "COUNT(*)"]
}
```

**Object with function and column:**
```json
{
  "aggregations": [
    {"fn": "sum", "column": "area", "alias": "total_area"},
    {"fn": "count", "column": "*", "alias": "hillslope_count"}
  ]
}
```

**Object with SQL expression:**
```json
{
  "aggregations": [
    {"expression": "SUM(area * 2)", "alias": "doubled_area"}
  ]
}
```

**Object with `sql` property (equivalent to `expression`):**
```json
{
  "aggregations": [
    {"sql": "AVG(cancov)", "alias": "avg_canopy"}
  ]
}
```

### GROUP BY Examples

**Group by single column:**
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["key"],
  "group_by": ["key"],
  "aggregations": [
    {"fn": "sum", "column": "area", "alias": "total_area"},
    {"fn": "count", "column": "*", "alias": "count"}
  ]
}
```

**Group by multiple columns:**
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["key", "lu.desc AS description"],
  "group_by": ["key", "description"],
  "aggregations": [
    {"fn": "sum", "column": "area", "alias": "total_area"}
  ],
  "order_by": ["total_area DESC"],
  "limit": 10
}
```

**Important:** All non-aggregated columns in the `columns` list must appear in `group_by`:
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "columns": ["key", "desc"],  // Both key and desc must be in group_by
  "group_by": ["key", "desc"],
  "aggregations": [{"fn": "sum", "column": "area"}]
}
```

### Complex Aggregation Example
Aggregate WEPP daily outputs:
```json
{
  "datasets": [{"path": "wepp/output/interchange/H.pass.parquet", "alias": "pass"}],
  "columns": ["pass.year", "pass.month", "pass.sim_day_index"],
  "group_by": ["year", "month", "sim_day_index"],
  "aggregations": [
    {"fn": "sum", "column": "pass.tdet", "alias": "detachment"},
    {"fn": "sum", "column": "pass.runvol", "alias": "runoff_volume"}
  ],
  "order_by": ["year", "month", "sim_day_index"],
  "include_schema": true,
  "include_sql": true
}
```

## Computed Columns

Computed columns create new columns from SQL expressions. They are evaluated before aggregations.

### Basic Computed Column
Convert area from square meters to hectares:
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["lu.TopazID", "lu.area"],
  "computed_columns": [
    {
      "alias": "area_hectares",
      "expression": "lu.area / 10000"
    }
  ],
  "limit": 10
}
```

### Multiple Computed Columns
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "computed_columns": [
    {"alias": "area_hectares", "expression": "lu.area / 10000"},
    {"alias": "area_acres", "expression": "lu.area / 4046.86"},
    {"alias": "canopy_pct", "expression": "lu.cancov * 100"}
  ],
  "columns": ["lu.TopazID", "area_hectares", "area_acres"],
  "limit": 10
}
```

### Using `sql` Property (Equivalent to `expression`)
```json
{
  "computed_columns": [
    {"alias": "area_hectares", "sql": "lu.area / 10000"}
  ]
}
```

### Date Computations
Create a date column from year, month, day components:
```json
{
  "computed_columns": [
    {
      "alias": "event_date",
      "date_parts": {
        "year": "year_col",
        "month": "month_col",
        "day": "day_col"
      }
    }
  ]
}
```

### Computed Columns with Joins
Use computed columns to calculate derived metrics across joined datasets:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [{"left": "lu", "right": "s", "on": ["TopazID"]}],
  "computed_columns": [
    {
      "alias": "weighted_clay",
      "expression": "s.clay * lu.area"
    }
  ],
  "columns": ["lu.TopazID", "weighted_clay"],
  "limit": 10
}
```

## Sorting Results

Use `order_by` to sort results. Specify columns or expressions with optional `ASC` (ascending, default) or `DESC` (descending).

### Simple Sorting
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "columns": ["TopazID", "area"],
  "order_by": ["area DESC"],
  "limit": 10
}
```

### Multi-Column Sorting
```json
{
  "datasets": ["landuse/landuse.parquet"],
  "order_by": ["key ASC", "area DESC"],
  "limit": 10
}
```

### Sorting by Computed or Aliased Columns
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["lu.TopazID", "lu.area AS area_sq_m"],
  "computed_columns": [
    {"alias": "area_hectares", "expression": "lu.area / 10000"}
  ],
  "order_by": ["area_hectares DESC"],
  "limit": 10
}
```

## Limiting Results

Use `limit` to restrict the number of rows returned. This is especially important for large datasets to avoid excessive response sizes.

```json
{
  "datasets": ["landuse/landuse.parquet"],
  "limit": 100
}
```

**Best practice:** Always include a reasonable `limit` when exploring datasets interactively.

## Response Structure

Query responses are JSON objects with these properties:

### Successful Query Response
```json
{
  "records": [
    {
      "TopazID": 121,
      "landuse": "Evergreen Forest",
      "simple_texture": "loam",
      "area": 675.18,
      "area_hectares": 0.0675
    }
  ],
  "row_count": 1,
  "schema": [
    {"name": "TopazID", "type": "int64"},
    {"name": "landuse", "type": "string"},
    {"name": "simple_texture", "type": "string"},
    {"name": "area", "type": "double"},
    {"name": "area_hectares", "type": "double"}
  ],
  "sql": "SELECT lu.TopazID, lu.desc AS landuse, s.simple_texture, lu.area, lu.area / 10000 AS area_hectares FROM read_parquet(...) AS lu INNER JOIN read_parquet(...) AS s ON lu.TopazID = s.TopazID WHERE lu.key = 42 ORDER BY lu.area DESC LIMIT 1"
}
```

### Error Response
When a query fails, the response includes error details:
```json
{
  "error": "Query execution failed: Binder Error: column \"desc\" must be quoted...",
  "stacktrace": "Traceback (most recent call last):\n  File ...",
  "stacktrace_lines": ["Traceback...", "  File ..."],
  "exc_info": "Full exception info...",
  "status_code": 500
}
```

## Common Patterns and Examples

### Pattern: Landuse Summary by Type
Get total area and hillslope count for each landuse type:
```json
{
  "datasets": [{"path": "landuse/landuse.parquet", "alias": "lu"}],
  "columns": ["key", "lu.desc AS landuse_type"],
  "group_by": ["key", "landuse_type"],
  "aggregations": [
    {"fn": "sum", "column": "area", "alias": "total_area"},
    {"fn": "count", "column": "*", "alias": "hillslope_count"},
    {"fn": "avg", "column": "cancov", "alias": "avg_canopy"}
  ],
  "order_by": ["total_area DESC"],
  "include_schema": true
}
```

### Pattern: Soil Texture Distribution
Find distribution of soil textures across the watershed:
```json
{
  "datasets": ["soils/soils.parquet"],
  "columns": ["simple_texture"],
  "group_by": ["simple_texture"],
  "aggregations": [
    {"fn": "sum", "column": "area", "alias": "total_area"},
    {"fn": "count", "column": "*", "alias": "hillslope_count"}
  ],
  "order_by": ["total_area DESC"]
}
```

### Pattern: Filtered Join with Computed Metrics
Join landuse and soils, filter to forest areas, compute weighted soil properties:
```json
{
  "datasets": [
    {"path": "landuse/landuse.parquet", "alias": "lu"},
    {"path": "soils/soils.parquet", "alias": "s"}
  ],
  "joins": [{"left": "lu", "right": "s", "on": ["TopazID"]}],
  "filters": [
    {"column": "lu.desc", "operator": "LIKE", "value": "%Forest%"}
  ],
  "computed_columns": [
    {"alias": "weighted_clay", "expression": "s.clay * lu.area"},
    {"alias": "area_hectares", "expression": "lu.area / 10000"}
  ],
  "columns": [
    "lu.TopazID",
    "lu.desc",
    "s.simple_texture",
    "area_hectares",
    "weighted_clay"
  ],
  "order_by": ["area_hectares DESC"],
  "limit": 50,
  "include_schema": true,
  "include_sql": true
}
```

### Pattern: RAP Timeseries for Specific Hillslope
Retrieve all RAP (Rangeland Analysis Platform) band values for a specific hillslope over time:
```json
{
  "datasets": [{"path": "rap/rap_ts.parquet", "alias": "rap"}],
  "columns": ["rap.year", "rap.band", "rap.value"],
  "filters": [
    {"column": "rap.topaz_id", "operator": "=", "value": 23}
  ],
  "order_by": ["rap.year", "rap.band"],
  "include_schema": true
}
```

## Troubleshooting

### Common Errors and Solutions

**Error: `column "desc" must appear in the GROUP BY clause`**
- **Cause:** Using aggregations without including all non-aggregated columns in `group_by`.
- **Solution:** Add all non-aggregated columns from `columns` to `group_by`, or use an aggregate function like `ANY_VALUE(desc)`.

**Error: `syntax error at or near "desc"`**
- **Cause:** `desc` is a SQL reserved keyword.
- **Solution:** Qualify the column with the dataset alias: `lu.desc` instead of `desc`.

**Error: `Table "lu" does not have a column named "topaz_id"`**
- **Cause:** Column name mismatch (case sensitivity or typo).
- **Solution:** Check the actual column names using `include_schema: true`. The catalog may use `TopazID` (capitalized) instead of `topaz_id`.

**Error: `No join specified for dataset alias(es)`**
- **Cause:** Multiple datasets in the query but no joins defined.
- **Solution:** Add a `joins` array linking all datasets together.

**Error: `Join alias 'X' referenced multiple times in join list`**
- **Cause:** A dataset appears as the `right` side of multiple joins.
- **Solution:** Structure joins as a chain where each dataset is joined once: `A → B → C` instead of `A → B, A → C`.

**Error: `datasets entries must be strings or objects with a 'path'`**
- **Cause:** Invalid dataset specification format.
- **Solution:** Use either a string path `"landuse/landuse.parquet"` or an object `{"path": "landuse/landuse.parquet", "alias": "lu"}`.

### Debugging Tips

1. **Start simple:** Begin with a minimal query and add complexity incrementally.
2. **Use `include_sql: true`:** Inspect the generated SQL to understand how your query is translated.
3. **Use `include_schema: true`:** Verify column names and types before constructing complex queries.
4. **Test filters individually:** Add filters one at a time to isolate issues.
5. **Check catalog paths:** Ensure dataset paths match exactly (case-sensitive).
6. **Qualify all columns:** When in doubt, always use `alias.column_name` syntax.
7. **Use `limit` during development:** Keep result sets small while iterating on query design.

## Advanced Topics

### Query Performance Considerations

1. **Dataset Column Selection:** Specify `columns` in the dataset object to limit which columns are read from Parquet files (reduces I/O).
2. **Filter Early:** Apply filters before joins when possible to reduce intermediate result sizes.
3. **Index-Friendly Filters:** Filters on indexed columns (like `TopazID`) are faster.
4. **Limit Results:** Always use `limit` during development and exploration.
5. **Aggregate Efficiently:** Group by high-cardinality columns only when necessary.

### Catalog Schema Inspection

Before constructing complex queries, inspect the catalog to see available datasets and their schemas:

**Using the Console UI:**
- Navigate to the query console
- The "Sample datasets" section lists available files
- Use a minimal query with `include_schema: true` to see column structures

**Using curl:**
```bash
curl -X POST "https://wc-prod.bearhive.duckdns.org/query-engine/runs/batch;;nasa-roses-2025;;wa-72/query" \
  -H "Content-Type: application/json" \
  -d '{"datasets": ["landuse/landuse.parquet"], "limit": 1, "include_schema": true}'
```

### Working with Spatial Datasets

The query engine automatically detects spatial file formats (`.geojson`, `.fgb`, `.gpkg`, `.shp`) and uses DuckDB's spatial extension (`ST_Read`).

**Query GeoJSON:**
```json
{
  "datasets": ["dem/wbt/subcatchments.geojson"],
  "columns": ["TopazID", "Area"],
  "limit": 10
}
```

**Join spatial and tabular data:**
```json
{
  "datasets": [
    {"path": "dem/wbt/subcatchments.geojson", "alias": "geom"},
    {"path": "landuse/landuse.parquet", "alias": "lu"}
  ],
  "joins": [{"left": "geom", "right": "lu", "on": ["TopazID"]}],
  "columns": ["geom.TopazID", "geom.Area", "lu.desc"],
  "limit": 10
}
```

### Reshaping Results (Timeseries)

The `reshape` feature transforms row-based timeseries data into structured formats suitable for charting. This is an advanced feature; consult the MCP API specification for full details.

## Further Reading

- **MCP API Specification:** Complete endpoint documentation and authentication details (sections 1-13 above)
- **Query Presets:** Explore `wepppy/query_engine/app/query_presets.py` for more example queries
- **DuckDB Documentation:** [https://duckdb.org/docs/](https://duckdb.org/docs/) for SQL function reference
- **OpenAPI Spec:** `wepppy/query_engine/docs/mcp_openapi.yaml` for machine-readable API definition
