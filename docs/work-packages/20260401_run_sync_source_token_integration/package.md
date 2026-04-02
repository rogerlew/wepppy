# Run Sync Dashboard Source Token Integration

**Status**: Complete (2026-04-01)

## Overview
This package integrates admin run-scoped service tokens into the Run Sync Dashboard and run-sync backend so sync jobs can authenticate when pulling private runs from remote WEPPcloud hosts. The goal is to eliminate anonymous `aria2c.spec` fetches that currently fail with `401` on private runs.

## Objectives
- Add a run-sync dashboard input for source run token usage during sync.
- Thread the token through rq-engine enqueue payloads into `run_sync_rq`.
- Use bearer auth headers in `run_sync_rq` for `aria2c.spec` download and aria2c file fetch operations.
- Add regression tests for rq-engine payload wiring and worker header behavior.
- Update docs and queue dependency notes for the new run-sync credential flow.

## Scope
This package covers Run Sync Dashboard UI payload wiring, rq-engine run-sync route payload handling, RQ worker sync header behavior, and related tests/docs.

### Included
- Run Sync Dashboard form/payload support for source run token.
- rq-engine `/api/run-sync` parsing + enqueue propagation for source token.
- `run_sync_rq` optional token support and bearer header usage.
- Regression tests in `tests/microservices/test_rq_engine_run_sync_routes.py` and `tests/rq/test_run_sync_rq.py`.
- Documentation updates for run-sync tokenized import flow.

### Explicitly Out of Scope
- Auto-minting source-host tokens across remote hosts.
- Non-admin expansion of run-sync permissions.
- Broader run-sync protocol redesign beyond authenticated header support.

## Stakeholders
- **Primary**: Admin/operators using Run Sync Dashboard for private run imports.
- **Reviewers**: rq-engine, RQ worker, and WEPPcloud route maintainers.
- **Informed**: Auth-token and operations documentation maintainers.

## Success Criteria
- [x] Dashboard submits optional source run token in run-sync payload.
- [x] rq-engine run-sync route accepts token and passes it to `run_sync_rq`.
- [x] `run_sync_rq` uses bearer auth headers for private source fetches when token is present.
- [x] Existing run-sync behavior remains unchanged when token is omitted.
- [x] Regression tests cover token wiring and header usage.
- [x] Docs and queue dependency catalog are updated.
- [x] Medium/high code+QA findings are resolved before closure.

## Dependencies

### Prerequisites
- Existing admin run token minting endpoint: `POST /runs/<runid>/<config>/mint-run-token`.
- Existing run-sync stack: dashboard (`/rq/run-sync`), rq-engine route, `run_sync_rq` worker.

### Blocks
- Reliable private-run remote sync through dashboard without manual worker patching.

## Related Packages
- **Depends on**: `docs/work-packages/20260401_admin_run_token_minting/`
- **Related**: `docs/work-packages/20260208_rq_engine_agent_usability/`
- **Follow-up**: optional remote token-mint orchestration for source-host auto-auth.

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py`
- `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`
- `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`
- `wepppy/microservices/rq_engine/run_sync_routes.py`
- `wepppy/rq/run_sync_rq.py`
- `tests/microservices/test_rq_engine_run_sync_routes.py`
- `tests/rq/test_run_sync_rq.py`

## Deliverables
- Dashboard + backend tokenized run-sync integration.
- Tests proving token propagation + header usage.
- Updated docs and queue dependency notes.
- Review artifacts:
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/qa_review_findings.md`

## Follow-up Work
- Optional secure token reference indirection (to avoid token-in-job-args persistence).
- Optional dashboard UX for masked token entry and token-health hints.
