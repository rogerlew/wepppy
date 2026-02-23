# Tracker - Correlation ID Structured Logging End-to-End

## Quick Status

**Started**: 2026-02-23  
**Current phase**: Closed (Milestone 5 complete)  
**Last updated**: 2026-02-23  
**Next milestone**: none

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Package scaffold + active ExecPlan path created.
- [x] Milestone 0 baseline inventory + architecture decision note completed.
- [x] Required orchestration completed: baseline explorer + workers A-D + final explorer.
- [x] Shared correlation utility implemented (`wepppy/observability/correlation.py`).
- [x] Ingress/response behavior implemented for `weppcloud`, `rq_engine`, `query_engine` and MCP.
- [x] RQ enqueue/worker propagation implemented.
- [x] Query-engine compatibility (`trace_id`) preserved and mapped.
- [x] Required tests and gate commands passed.
- [x] Required artifacts finalized.
- [x] Closeout synchronization complete (ExecPlan/tracker/project tracker/root pointer).
- [x] Reviewer + QA reviewer follow-up pass completed; enqueue metadata hardening, logging `extra` collision handling, and preflight header continuity gaps resolved.

## Milestones

- [x] Milestone 0: baseline inventory artifact + architecture decision note.
- [x] Milestone 1: shared correlation context utility + unit tests.
- [x] Milestone 2: ingress middleware in `weppcloud`/`rq_engine`/`query_engine`.
- [x] Milestone 3: RQ enqueue/worker propagation and logging integration.
- [x] Milestone 4: compatibility updates (`trace_id`) + docs/tests alignment.
- [x] Milestone 5: final validation, artifact snapshots, closeout.

## Decisions

### 2026-02-23: Canonical key + header contract

**Decision**: Internal key is `correlation_id`; wire contract is `X-Correlation-ID`.

**Impact**: One cross-service correlation primitive with consistent ingress/egress behavior.

### 2026-02-23: Shared utility module location

**Decision**: Implement shared utility in `wepppy/observability/correlation.py`.

**Impact**: Keeps correlation handling neutral and reusable across Flask/FastAPI/Starlette + worker code.

### 2026-02-23: Query-engine compatibility strategy

**Decision**: Preserve `meta.trace_id`, map to active correlation context, and include `meta.correlation_id`.

**Impact**: Backward compatibility for existing clients/tests while surfacing canonical key.

### 2026-02-23: Flask enqueue propagation follow-through

**Decision**: Install `install_rq_auth_actor_hook()` in `wepppy/weppcloud/app.py` to ensure direct Flask enqueue paths propagate correlation metadata.

**Impact**: Closes request->enqueue->worker continuity gap identified in final explorer review.

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Contract drift for query-engine `trace_id` | High | Low | Keep `trace_id` required/present and mapped in tests | Closed |
| Correlation leakage across requests/jobs | High | Medium | explicit context reset in request middleware and worker teardown | Closed |
| Formatter failures for missing field | High | Medium | global log record factory injects fallback `correlation_id='-'` | Closed |
| Flask direct enqueue propagation gap | High | Medium | install enqueue hook in Flask app startup | Closed |

## Verification Checklist

- [x] Targeted tests pass.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [x] `python3 tools/code_quality_observability.py --base-ref origin/master` runs.
- [x] `wctl run-pytest tests --maxfail=1` passes.
- [x] `wctl check-rq-graph` passes (after regeneration).
- [x] Required artifacts updated with final evidence.

## Progress Notes

### 2026-02-23: Milestone 0 baseline

- Completed baseline inventory and architecture decision note.
- Identified canonical insertion points for middleware, enqueue hook, worker context restore, and query-engine compatibility.

### 2026-02-23: Implementation and validation closeout

- Integrated shared utility, service middleware, queue propagation, and compatibility mappings.
- Ran required validation suite + gates to completion.
- Final explorer review executed; one high-severity propagation gap identified and fixed.
- Post-fix explorer verification reported no remaining high/medium regressions.
- Final artifacts and closeout synchronization completed.

### 2026-02-23: Reviewer + QA follow-up

- Ran correctness-focused and QA-focused review passes on the finished package changes.
- Identified and fixed enqueue hardening gap: malformed pre-existing `job.meta["correlation_id"]` values are now replaced with the active valid correlation ID during enqueue.
- Identified and fixed high-severity logging injection gap: `extra={"correlation_id": ...}` now works without `KeyError` while retaining fallback enrichment.
- Identified and fixed query-engine preflight gap: `OPTIONS` responses now include `X-Correlation-ID`.
- Reduced middleware precedence drift risk by centralizing inbound correlation selection in `wepppy/observability/correlation.py`.
- Added regression coverage in `tests/rq/test_dependency_graph_tools.py`, `tests/test_observability_correlation.py`, and `tests/query_engine/test_server_routes.py`.
