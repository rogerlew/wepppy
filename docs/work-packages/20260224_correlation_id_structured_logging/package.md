# Correlation ID Structured Logging End-to-End

**Status**: Closed (2026-02-23)

## Overview

Implemented end-to-end correlation ID handling and structured logging enrichment across core WEPPpy service boundaries. Core ingress surfaces now accept/emit `X-Correlation-ID`, RQ enqueue/worker paths preserve correlation metadata, and query-engine compatibility keeps `trace_id` stable while mapping to canonical `correlation_id`.

## Objectives

- Establish one canonical key: `correlation_id`.
- Accept/emit `X-Correlation-ID` at ingress/egress boundaries.
- Add logging enrichment so records can safely include `correlation_id` with fallback `-`.
- Propagate correlation context through RQ enqueue + worker execution.
- Preserve query-engine `trace_id` compatibility by mapping it to correlation context.

## Scope

### Included

- `wepppy/weppcloud/**`
- `wepppy/microservices/rq_engine/**`
- `wepppy/query_engine/**`
- `wepppy/rq/**`
- Required test/doc/artifact updates.

### Explicitly Out of Scope

- Broad logging framework rewrites unrelated to correlation propagation.
- API contract breaks outside explicit compatibility updates.
- Queue topology redesign unrelated to correlation metadata propagation.

## Success Criteria

- [x] Shared correlation utility exists with contextvar + generate/validate/reset helpers.
- [x] All ingress surfaces emit `X-Correlation-ID` and bind request lifecycle context.
- [x] Logs in boundary services can render `correlation_id` without formatter failures.
- [x] RQ enqueue + worker execution preserve correlation metadata continuity.
- [x] Query-engine `trace_id` contract remains compatible.
- [x] Required tests and gates pass.
- [x] Package docs/tracker/ExecPlan/PROJECT tracker/root pointer synchronized at closeout.

## Deliverables

- `docs/work-packages/20260224_correlation_id_structured_logging/package.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/tracker.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/prompts/active/correlation_id_structured_logging_execplan.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/artifacts/baseline_correlation_inventory.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/artifacts/correlation_flow_matrix.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/artifacts/postfix_validation_summary.md`
- `docs/work-packages/20260224_correlation_id_structured_logging/artifacts/sample_log_lines.md`

## References

- `AGENTS.md`
- `wepppy/weppcloud/AGENTS.md`
- `wepppy/microservices/rq_engine/AGENTS.md`
- `tests/AGENTS.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `wepppy/rq/auth_actor.py`
- `wepppy/profile_coverage/runtime.py`

## Closure Notes

- Correlation utility added: `wepppy/observability/correlation.py`.
- Ingress/egress correlation middleware added for Flask/FastAPI/Starlette/MCP.
- RQ enqueue metadata propagation + worker context restore completed.
- Query-engine `trace_id` compatibility preserved and mapped to `correlation_id`.
- Validation summary:
  - targeted suites: PASS (`92 passed`)
  - broad-exception changed-file enforcement: PASS
  - code-quality observability: PASS (observe-only)
  - full suite: PASS (`2086 passed, 29 skipped`)
  - RQ dependency graph check: PASS after regeneration
