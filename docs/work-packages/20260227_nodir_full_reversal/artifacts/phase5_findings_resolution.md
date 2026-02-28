# Phase 5 Findings Resolution Log

## Resolution Summary

All high/medium findings raised during the mandatory subagent loop were resolved and revalidated. Final unresolved high/medium count is zero.

## Findings

### FND-P5-001
- Source: reviewer cycle 1
- Severity: high
- Issue: subagent runtime could not execute shell/file operations.
- Resolution: reran review with in-band packet containing exact Phase 5 changes + validation results.
- Status: closed

### FND-P5-002
- Source: test_guardian cycle 2
- Severity: medium
- Issue: assertion depth for updated mixed-state omni preflight test was incomplete.
- Resolution:
  - updated `tests/microservices/test_rq_engine_omni_routes.py` to assert `code`, `http_status`, and exact `message` in addition to no-mutation existence checks.
  - command: `wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py`
  - result: `43 passed`.
- Status: closed

### FND-P5-003
- Source: test_guardian cycle 2
- Severity: medium
- Issue: NoDb replacement coverage mapping after NoDir-only test removals was not explicit.
- Resolution:
  - documented replacement coverage evidence in Phase 5 suites:
    - `tests/nodb/mods/test_ash_transport_run_ash.py`
    - `tests/nodb/mods/test_observed_processing.py`
    - `tests/nodb/mods/test_omni.py`
  - validating command: `wctl run-pytest tests/nodb --maxfail=1` (pass)
- Status: closed

### FND-P5-004
- Source: test_guardian cycle 2
- Severity: medium
- Issue: RQ-layer replacement coverage mapping after NoDir-only test removals was not explicit.
- Resolution:
  - documented replacement coverage evidence in Phase 5 suites:
    - `tests/rq/test_omni_rq.py`
    - `tests/rq/test_path_ce_rq.py`
    - `tests/rq/test_project_rq_ash.py`
    - `tests/rq/test_project_rq_debris_flow.py`
  - validating command: `wctl run-pytest tests/rq --maxfail=1` (pass)
- Status: closed

### FND-P5-005
- Source: test_guardian cycle 2
- Severity: medium
- Issue: `nodir_bulk` retirement behavior coverage concern.
- Resolution:
  - confirmed Phase 3 policy retained `nodir_bulk` only as historical rollback tooling, outside active runtime contract flow.
  - Phase 5 action removed NoDir-only test surface by matrix (`tests/tools/test_migrations_nodir_bulk.py`).
  - active docs updated to mark `nodir_bulk.py` as historical/retired in `wepppy/tools/migrations/README.md`.
  - no active runtime route/RQ references to `nodir_bulk` remain.
- Status: closed

## Final Verification

- reviewer rerun: no unresolved high/medium findings
- test_guardian rerun: no unresolved high/medium findings
- unresolved high findings: `0`
- unresolved medium findings: `0`
