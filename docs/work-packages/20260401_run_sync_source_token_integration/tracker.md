# Tracker - Run Sync Dashboard Source Token Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-04-01  
**Current phase**: Complete  
**Last updated**: 2026-04-01  
**Next milestone**: None (package closed).

## Task Board

### Ready / Backlog
- [x] Update docs + queue dependency catalog for tokenized run-sync flow.

### In Progress
- [x] Implement run-sync source token support in UI and backend.

### Blocked
- [x] None.

### Done
- [x] Created work-package scaffold and active ExecPlan (2026-04-01).
- [x] Implemented optional `source_run_token` in Run Sync Dashboard form + payload.
- [x] Propagated source token through `/rq-engine/api/run-sync` into `run_sync_rq` enqueue args.
- [x] Added bearer-header support in `run_sync_rq` for `aria2c.spec` and aria2 fetches.
- [x] Added regression tests for token propagation/header behavior and job serialization arg indexes.
- [x] Updated run-sync docs and RQ dependency graph/catalog artifacts.
- [x] Completed code and QA review artifacts with medium/high findings resolved.

## Timeline

- **2026-04-01** - Package created and scoped.
- **2026-04-01** - Implemented dashboard/backend/worker integration and tests.
- **2026-04-01** - Completed validation, review artifacts, and package closure.

## Decisions Log

### 2026-04-01: Accept source run token as optional dashboard input
**Context**: Target host cannot reliably mint source-host-signed tokens for arbitrary remote hosts.

**Options considered**:
1. Auto-mint token on target host and use for remote source fetches.
2. Accept operator-supplied source-host token and forward to worker.

**Decision**: Implement option 2 (optional source token input + backend propagation).

**Impact**: Solves private-run sync for trusted hosts with minimal risk and no cross-host mint orchestration.

### 2026-04-01: Fix run-sync status arg-index fallback bug while integrating token flow
**Context**: `_serialize_job` used mismatched positional indexes for fallback `config`/`source_host` extraction.

**Decision**: Correct fallback indexes (`config -> args[4]`, `source_host -> args[1]`) and add regression coverage.

**Impact**: Dashboard status rows now report correct host/config for queued run-sync jobs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Token leakage in logs/status payloads | High | Low | Never include token in status messages/meta/provenance; pass only in worker request headers | Mitigated |
| Behavior regression for tokenless sync | Medium | Low | Keep token optional; preserve defaults/tests | Mitigated |
| Route/payload drift without tests | Medium | Medium | Added rq-engine + worker regression tests for propagation/header behavior | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted tests pass for rq-engine run-sync routes.
- [x] Targeted tests pass for `run_sync_rq` behavior.
- [x] No medium/high findings left unresolved.

### Documentation
- [x] run-sync dashboard usage docs updated.
- [x] queue dependency catalog updated.
- [x] package docs updated for closure.

### Testing
- [x] tokenized `aria2c.spec` download header path covered.
- [x] token omission path remains covered.
- [x] dashboard payload includes optional token field.

## Progress Notes

### 2026-04-01: Implementation + validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Updated dashboard UI + JS payload wiring:
  - `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`
  - `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`
- Updated rq-engine run-sync route and fixed status serialization fallback:
  - `wepppy/microservices/rq_engine/run_sync_routes.py`
- Updated worker/stub for optional source token bearer headers:
  - `wepppy/rq/run_sync_rq.py`
  - `wepppy/rq/run_sync_rq.pyi`
- Added tests:
  - `tests/microservices/test_rq_engine_run_sync_routes.py`
  - `tests/rq/test_run_sync_rq.py`
- Updated docs/artifacts:
  - `docs/run_migration_strategy.md`
  - `wepppy/rq/job-dependencies-catalog.md`
  - `wepppy/rq/job-dependency-graph.static.json`
  - `docs/standards/broad-exception-boundary-allowlist.md`
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`

**Test results**:
- `wctl run-pytest tests/microservices/test_rq_engine_run_sync_routes.py tests/rq/test_run_sync_rq.py --maxfail=1` -> `7 passed`
- `wctl run-npm lint` -> pass
- `wctl check-rq-graph` -> pass
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`
- `wctl doc-lint --path docs/run_migration_strategy.md --path wepppy/rq/job-dependencies-catalog.md --path docs/standards/broad-exception-boundary-allowlist.md --path docs/work-packages/20260401_run_sync_source_token_integration --path PROJECT_TRACKER.md` -> `7 files validated, 0 errors, 0 warnings`

## Communication Log

### 2026-04-01: Request framing
**Participants**: User, Codex  
**Topic**: Integrate admin run token with Run Sync Dashboard and backend.  
**Outcome**: Implemented and validated end-to-end; package closed.
