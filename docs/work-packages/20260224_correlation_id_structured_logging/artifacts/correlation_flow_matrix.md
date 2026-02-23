# Correlation Flow Matrix

## Final State (Milestones 1-5)

| Boundary | Implementation path | Final behavior | Verification evidence |
|---|---|---|---|
| HTTP ingress -> `weppcloud` request context | `wepppy/weppcloud/app.py` | Binds valid inbound `X-Correlation-ID` or generates new ID, stores request context token, resets on teardown | Request lifecycle hooks + full suite pass (`wctl run-pytest tests --maxfail=1`) |
| `weppcloud` response emission | `wepppy/weppcloud/app.py` | Always emits `X-Correlation-ID` on response | Full suite route coverage + targeted config/logging checks |
| HTTP ingress -> `rq_engine` request context | `wepppy/microservices/rq_engine/__init__.py` | Middleware binds correlation at ingress, resets at request end | `tests/microservices/test_rq_engine_auth.py`, `tests/microservices/test_rq_engine_openapi_contract.py` |
| `rq_engine` response emission | `wepppy/microservices/rq_engine/__init__.py` | Always emits `X-Correlation-ID` | Same tests above |
| Enqueue propagation (`rq_engine`/`weppcloud` -> RQ) | `wepppy/rq/auth_actor.py` + hook install in `rq_engine` and `weppcloud` app startup | Active context correlation is persisted to `job.meta["correlation_id"]` if absent | `tests/rq/test_dependency_graph_tools.py::test_dependency_graph_auth_actor_hook_persists_correlation_id` |
| Worker context restore | `wepppy/rq/rq_worker.py` | Worker reads `job.meta["correlation_id"]`, binds context for execution logs, resets after job | Targeted rq tests + full suite |
| Logging field enrichment | `wepppy/observability/correlation.py` + service startup installers | Log records always have `correlation_id` (`-` fallback) and `trace_id` mapped to correlation | `tests/test_observability_correlation.py`, `tests/weppcloud/test_config_logging.py` |
| HTTP ingress -> `query_engine` (Starlette + MCP) | `wepppy/query_engine/app/server.py`, `wepppy/query_engine/app/mcp/router.py` | Middleware binds correlation context and emits `X-Correlation-ID` for query + MCP routes | `tests/query_engine/test_server_routes.py`, `tests/query_engine/test_mcp_router.py` |
| MCP payload compatibility | `wepppy/query_engine/app/mcp/router.py` (`_with_trace_id`) | Preserves `meta.trace_id`; maps to active correlation ID; includes `meta.correlation_id` | `tests/query_engine/test_mcp_router.py` |

## Contract Summary

- Canonical internal key: `correlation_id`
- Header contract: `X-Correlation-ID`
- Ingress behavior: accept valid inbound header; generate when missing/invalid
- Response behavior: always emit `X-Correlation-ID`
- Query-engine compatibility: `trace_id` remains present and equals mapped `correlation_id`
