# Baseline Correlation Inventory

## Snapshot

- Date (UTC): 2026-02-23
- Scope: `wepppy/weppcloud/**`, `wepppy/microservices/rq_engine/**`, `wepppy/query_engine/**`, `wepppy/rq/**`

## Existing Patterns Found in Baseline

- `wepppy/rq/auth_actor.py`: contextvar + enqueue hook pattern persisting `auth_actor` metadata.
- `wepppy/profile_coverage/runtime.py`: contextvar + enqueue hook pattern persisting `profile_trace_slug` metadata.
- `wepppy/rq/rq_worker.py`: worker restores existing metadata-backed context (`auth_actor`/profile slug).
- `wepppy/query_engine/app/mcp/router.py`: `meta.trace_id` exists as compatibility contract.

## Ingress Surfaces

- Flask ingress: `wepppy/weppcloud/app.py`.
- FastAPI ingress: `wepppy/microservices/rq_engine/__init__.py`.
- Starlette ingress: `wepppy/query_engine/app/server.py` and mounted MCP app.

## Baseline Gaps

- No canonical shared correlation context utility.
- No uniform `X-Correlation-ID` acceptance/emission in all ingress services.
- No queue/worker propagation for a canonical correlation key.
- No global logging field fallback for `correlation_id` in all service paths.

## Architecture Decision Note

1. Canonical key: `correlation_id`.
2. Header contract: `X-Correlation-ID` accepted and emitted.
3. Shared implementation location: `wepppy/observability/correlation.py`.
4. Query-engine compatibility: preserve `meta.trace_id`, map from active correlation context, and include `meta.correlation_id`.
5. Queue propagation: extend existing enqueue hook pattern and restore context in worker execution.
