# Phase 7 Bulk Migration Rollout Review

Date: 2026-02-17 (UTC)

## Scope Reviewed

Phase 7 required:
1. bulk migration crawler with readonly/lock safety, resume, and JSONL audit logs;
2. new-run default NoDir rollout without mixed-state regressions;
3. perf targets and measured evidence;
4. operational runbook for rollback/forensics/audit interpretation;
5. full validation and plan closeout.

## Deliverable Status

- Bulk migration crawler CLI: complete.
  - Implemented in `wepppy/tools/migrations/nodir_bulk.py`.
  - Required filters implemented: `--dry-run`, `--limit`, `--runid`, `--root`.
  - Resume + JSONL audit log implemented (`--audit-log`, default resume, `--no-resume`).
  - Safety gates implemented: `READONLY` required for mutation, active run lock fail-fast, root maintenance lock fail-fast.

- New-run default NoDir rollout: complete.
  - New-run creation surfaces seed `WD/.nodir/default_archive_roots.json`:
    - `wepppy/microservices/rq_engine/project_routes.py`
    - `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
    - `wepppy/weppcloud/routes/test_bp.py`
  - Shared mutation flow honors the marker and auto-freezes configured dir-form roots post-callback:
    - `wepppy/nodir/mutations.py`

- Perf evidence: complete.
  - Artifact: `docs/work-packages/20260214_nodir_archives/artifacts/phase7_perf_targets_and_results.md`

- Operational runbook: complete.
  - Artifact: `docs/work-packages/20260214_nodir_archives/artifacts/phase7_operational_runbook.md`

- Validation: complete.
  - Required gates executed and passed (see command/results in this review and final report).

## Regression Coverage Added

- `tests/tools/test_migrations_nodir_bulk.py`
  - dry-run/filter/limit behavior;
  - archive+resume and explicit no-resume replay behavior;
  - readonly requirement;
  - active-run lock fail-fast;
  - root-lock fail-fast (`root_lock_failed` / `NODIR_LOCKED`);
  - canonical `NODIR_MIXED_STATE` propagation into audit events.

- `tests/nodir/test_mutations.py`
  - default marker auto-freeze for dir-form root mutations;
  - no-marker dir-form behavior unchanged;
  - malformed marker fail-fast behavior.

- `tests/microservices/test_rq_engine_project_routes.py`
  - create route seeds default NoDir marker for new runs.

- `tests/microservices/test_rq_engine_upload_huc_fire_routes.py`
  - HUC fire upload create path seeds default NoDir marker for new runs.

- `tests/weppcloud/routes/test_test_bp.py`
  - test-support `/tests/api/create-run` seeds default NoDir marker for new runs.

## Performance Summary

From `phase7_perf_targets_and_results.md`:
- Browse HTML p95: 183.27 ms -> 97.06 ms.
- `/files` JSON p95: 211.19 ms -> 54.03 ms.
- Download throughput: 139.19 MiB/s -> 137.73 MiB/s (near parity).
- Materialize wall time (archive): miss 191.78 ms, hit 2.31 ms.
- Archive build overhead (`nodir_bulk` vs direct freeze): within target (no positive overhead observed).
- Inode count: 10,313 -> 11 (99.89% reduction).

## Risks / Follow-Ups

- Performance evidence was captured on a synthetic large-run harness; production NAS runs should be spot-checked with the same metric shape before broad rollout waves.
- Existing runs remain opt-in for archive conversion via crawler; rollout scheduling should remain staged and audit-log driven.

## Readiness Verdict

`ready`

Phase 7 implementation is rollout-ready with required safety controls, tests, and operational documentation.

