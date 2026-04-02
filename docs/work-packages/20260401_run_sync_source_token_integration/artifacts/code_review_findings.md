# Code Review Findings - Run Sync Source Token Integration

Date: 2026-04-01
Reviewer: Codex

## Summary
- High findings: 0 open
- Medium findings: 0 open
- Resolved during implementation: 1 medium

## Findings

### [Resolved][Medium] Run-sync status serialization used incorrect arg indexes
- Location: `wepppy/microservices/rq_engine/run_sync_routes.py::_serialize_job`
- Risk: queued/deferred run-sync jobs could display incorrect `config`/`source_host` in dashboard status rows because fallback arg indexes did not match `run_sync_rq` enqueue signature.
- Resolution:
  - Updated fallback extraction to use `args[4]` for `config` and `args[1]` for `source_host`.
  - Added regression test: `tests/microservices/test_rq_engine_run_sync_routes.py::test_serialize_job_uses_source_host_from_args_position_one`.

## Final Disposition
No open medium/high findings remain.
