# Baseline Scope Inventory — Residual Broad-Exception Finish Line

Date: 2026-02-23

Input:
- `docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/baseline_broad_exceptions.json`

Scope files:
- `wepppy/query_engine/app/mcp/router.py`
- `wepppy/weppcloud/app.py`

## Baseline Summary

- In-scope unresolved findings: `8`
- Kinds: `except-Exception` only
- Distribution:
  - `wepppy/query_engine/app/mcp/router.py`: `7`
  - `wepppy/weppcloud/app.py`: `1`

## In-Scope Findings and Disposition Plan

1. `wepppy/query_engine/app/mcp/router.py:177` (`except-Exception`)
- Area: `_load_catalog_metadata`
- Planned disposition: `narrow`
- Contract risk: run metadata fallback semantics for malformed catalog parsing.

2. `wepppy/query_engine/app/mcp/router.py:298` (`except-Exception`)
- Area: `_prepare_query_request`
- Planned disposition: `narrow`
- Contract risk: `catalog_invalid` error mapping in query validation/execute paths.

3. `wepppy/query_engine/app/mcp/router.py:700` (`except-Exception`)
- Area: `get_catalog`
- Planned disposition: `narrow`
- Contract risk: `500 catalog_invalid` response envelope preservation.

4. `wepppy/query_engine/app/mcp/router.py:918` (`except-Exception`)
- Area: `execute_query` context resolution boundary
- Planned disposition: `true-boundary`
- Contract risk: preserve `context_unavailable` response contract and correlation metadata.

5. `wepppy/query_engine/app/mcp/router.py:930` (`except-Exception`)
- Area: `execute_query` run-query execution boundary
- Planned disposition: `true-boundary`
- Contract risk: preserve `execution_failed` response contract and correlation metadata.

6. `wepppy/query_engine/app/mcp/router.py:996` (`except-Exception`)
- Area: `activate_run_endpoint` activation boundary
- Planned disposition: `true-boundary`
- Contract risk: preserve `activation_failed` response contract and correlation metadata.

7. `wepppy/query_engine/app/mcp/router.py:1084` (`except-Exception`)
- Area: `get_prompt_template`
- Planned disposition: `narrow`
- Contract risk: preserve best-effort prompt-template response behavior when catalog is malformed.

8. `wepppy/weppcloud/app.py:197` (`except-Exception`)
- Area: `Run.meta`
- Planned disposition: `true-boundary`
- Contract risk: preserve metadata fallback (`None`) and request-lifecycle/correlation cleanup behavior.

## Dependent Tests

Required commands from package contract:
- `wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py`
- `wctl run-pytest tests/weppcloud/test_config_logging.py tests/test_observability_correlation.py`
- `wctl run-pytest tests --maxfail=1`

Recommended additional coverage to add when touching behavior:
- malformed-catalog error-path coverage for MCP catalog/query/prompt-template endpoints
- explicit query execution and activation unexpected-error path coverage
- `Run.meta` unexpected `Ron.getInstance` failure coverage in `weppcloud/app.py`
