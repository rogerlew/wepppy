# Milestone 6 Catch Diff

## Scope

Milestone 6 query-engine/services tail cleanup batch:

- `wepppy/query_engine/app/server.py`
- `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`

Regression tests added/updated:
- `tests/query_engine/test_server_routes.py`
- `services/cao/test/services/test_inbox_service.py`

## Catch Count Delta (Touched Files)

Checker source: `python3 tools/check_broad_exceptions.py --json`

| File | Before | After | Delta |
|------|-------:|------:|------:|
| `wepppy/query_engine/app/server.py` | 7 | 6 | -1 |
| `services/cao/src/cli_agent_orchestrator/services/inbox_service.py` | 6 | 5 | -1 |
| **Total (touched files)** | **13** | **11** | **-2** |

Global checker summary:
- Before Milestone 6 (from Milestone 5 snapshot): `1105` unsuppressed broad catches.
- After Milestone 6: `1103` unsuppressed broad catches.
- Net reduction: `-2`.

## Commands Run

- `python3 tools/check_broad_exceptions.py wepppy/query_engine/app/server.py services/cao/src/cli_agent_orchestrator/services/inbox_service.py` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 tools/check_broad_exceptions.py wepppy services` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 -m py_compile wepppy/query_engine/app/server.py services/cao/src/cli_agent_orchestrator/services/inbox_service.py tests/query_engine/test_server_routes.py services/cao/test/services/test_inbox_service.py` -> pass.
- `wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py --maxfail=1` -> pass (`26 passed`).
- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1` -> pass (`4 passed`).

## Residual Risks / Deferred Items

- Query payload validation now maps `TypeError`/`ValueError` to 422; unexpected exception types from `QueryRequest` will now follow the global 500 handler path.
- `_get_log_tail` now only swallows expected subprocess/fs runtime failures; unexpected exceptions intentionally propagate to caller boundaries.
