# Correlation ID Structured Logging End-to-End ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are updated as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, core WEPPpy service requests and downstream RQ worker execution can be traced with one stable correlation identifier. Every ingress path accepts or generates an ID, every response emits `X-Correlation-ID`, logs can always render `correlation_id`, and query-engine keeps `trace_id` compatibility while mapping to the same value.

## Progress

- [x] (2026-02-23 18:22Z) Package scaffold and active prompt path established.
- [x] (2026-02-23 18:30Z) Milestone 0 baseline explorer + inventory artifacts complete.
- [x] (2026-02-23 18:40Z) Required worker orchestration executed (A/B/C/D).
- [x] (2026-02-23 18:55Z) Shared utility + ingress middleware + RQ propagation + query compatibility code integrated.
- [x] (2026-02-23 19:30Z) Milestone 5 validation gates complete.
- [x] (2026-02-23 19:40Z) Final explorer regression/observability review complete.
- [x] (2026-02-23 19:45Z) Closeout docs/tracker/project tracker sync and root pointer reset to `none` completed.
- [x] (2026-02-23 20:10Z) Reviewer + QA reviewer pass completed; resolved enqueue metadata hardening, `extra={"correlation_id": ...}` logging collision risk, and query-engine CORS preflight header propagation.

## Surprises & Discoveries

- Observation: `wepppy/rq` is not a neutral shared namespace because `wepppy/rq/__init__.py` imports worker code.
  Evidence: Baseline source review.
- Observation: query-engine tests enforce `meta.trace_id` presence across many routes.
  Evidence: `tests/query_engine/test_mcp_router.py` coverage.
- Observation: final explorer review identified a real propagation gap for direct Flask enqueue paths.
  Evidence: hook installation was present in `rq_engine` and worker startup but not Flask app startup; fixed by installing enqueue hook in `wepppy/weppcloud/app.py`.
- Observation: enqueue hook preserved malformed pre-populated `job.meta["correlation_id"]` values, allowing worker context restore to drop correlation IDs.
  Evidence: reviewer pass over `wepppy/rq/auth_actor.py` and regression test added in `tests/rq/test_dependency_graph_tools.py`.
- Observation: injecting correlation fields directly in the LogRecord factory caused `KeyError` when callers supplied `extra={"correlation_id": ...}`.
  Evidence: reviewer pass and new regression coverage in `tests/test_observability_correlation.py`.
- Observation: query-engine preflight (`OPTIONS`) responses missed `X-Correlation-ID` because CORS middleware short-circuited before correlation middleware.
  Evidence: targeted container repro and regression coverage in `tests/query_engine/test_server_routes.py`.
- Observation: duplicated middleware precedence logic across query-engine and MCP increased drift risk.
  Evidence: QA review; mitigated by adding shared `select_inbound_correlation_id(...)` helper in `wepppy/observability/correlation.py`.

## Decision Log

- Decision: Canonical key is `correlation_id`; transport header is `X-Correlation-ID`.
  Rationale: Stable, service-agnostic propagation primitive.
  Date/Author: 2026-02-23 / Codex
- Decision: Shared implementation lives in `wepppy/observability/correlation.py`.
  Rationale: Reusable across Flask/FastAPI/Starlette and worker code without coupling to `wepppy.rq` package side effects.
  Date/Author: 2026-02-23 / Codex
- Decision: Keep `trace_id` in query-engine responses and map it to active correlation context.
  Rationale: Preserve compatibility while introducing canonical key.
  Date/Author: 2026-02-23 / Codex
- Decision: Install enqueue hook in Flask startup as final follow-through.
  Rationale: Ensures correlation continuity for direct Flask enqueue routes, not only rq_engine.
  Date/Author: 2026-02-23 / Codex

## Outcomes & Retrospective

Milestones 0-5 completed. Correlation ID is now bound at ingress for `weppcloud`, `rq_engine`, and `query_engine`; responses emit `X-Correlation-ID`; queue metadata propagation and worker restore are active; query-engine `trace_id` contract remains compatible. Required validation gates passed, artifacts were published, and post-fix explorer verification reported no remaining high/medium regressions. A post-close reviewer/QA pass also closed malformed enqueue metadata handling, removed logging `extra` collision risk, and ensured query-engine preflight responses emit correlation headers.

## Context and Orientation

Relevant modules:

- `wepppy/observability/correlation.py`: shared contextvar + validation/generation + logging record enrichment.
- `wepppy/weppcloud/app.py`: Flask lifecycle binding/emission/reset + enqueue hook installation.
- `wepppy/microservices/rq_engine/__init__.py`: FastAPI middleware binding/emission/reset.
- `wepppy/query_engine/app/server.py`: Starlette middleware binding/emission/reset.
- `wepppy/query_engine/app/mcp/router.py`: `trace_id` compatibility mapping + MCP middleware.
- `wepppy/rq/auth_actor.py`: enqueue metadata propagation.
- `wepppy/rq/rq_worker.py`: worker metadata restore and reset.

## Plan of Work

Completed as planned: baseline inventory, shared utility, ingress middleware, logging enrichment, RQ propagation, compatibility updates, test/gate validation, final explorer review, and closeout documentation sync.

## Concrete Steps

Executed commands from `/workdir/wepppy`:

    wctl run-pytest tests/test_observability_correlation.py tests/weppcloud/test_config_logging.py tests/microservices/test_rq_engine_auth.py tests/microservices/test_rq_engine_openapi_contract.py tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py tests/rq/test_dependency_graph_tools.py

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl run-pytest tests --maxfail=1

    wctl check-rq-graph
    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph

## Validation and Acceptance

Acceptance achieved:

- `X-Correlation-ID` generated/accepted at ingress and emitted on response.
- `correlation_id` appears in logs through injected record fields with safe fallback.
- RQ enqueue + worker metadata continuity implemented.
- Query-engine `trace_id` compatibility preserved.
- Required tests/gates passed.
- Required artifacts complete.

## Idempotence and Recovery

Changes are additive and idempotent. Queue graph drift was handled through standard regeneration command and re-check.

## Artifacts and Notes

- `artifacts/baseline_correlation_inventory.md`
- `artifacts/correlation_flow_matrix.md`
- `artifacts/postfix_validation_summary.md`
- `artifacts/sample_log_lines.md`

## Interfaces and Dependencies

Shared API from `wepppy/observability/correlation.py`:

- `CORRELATION_ID_HEADER`
- `normalize_correlation_id`
- `generate_correlation_id`
- `bind_correlation_id`
- `reset_correlation_id`
- `install_correlation_log_record_factory`

Revision note (2026-02-23 19:45Z): Finalized Milestones 0-5, incorporated final explorer findings/fix, and synchronized closure state including root pointer reset.
