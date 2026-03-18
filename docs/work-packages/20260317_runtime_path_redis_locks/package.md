# Runtime Path Locks: Redis Migration

**Status**: Closed (2026-03-17)

## Overview
Runtime directory maintenance locks currently use per-container local files under `/tmp`, which causes cross-worker inconsistency and stale lock incidents when jobs are terminated mid-flight on one worker and retried on another. This package migrates runtime-path locking to Redis so lock state is globally visible and operable across all workers.

The migration intentionally does not preserve compatibility with legacy file lock artifacts for in-flight or previously locked projects. Existing file locks are treated as obsolete operational debris once Redis locking is deployed.

## Objectives
- Replace file-based runtime-path maintenance locks with Redis-backed distributed locks.
- Ensure lock acquire/release semantics are consistent across all RQ workers and hosts.
- Add first-class lock inspection and clear operations for runtime-path locks (parallel to NoDb lock operations).
- Improve `NODIR_LOCKED` operator guidance to include actionable remediation.
- Add regression and integration coverage for cross-worker lock behavior and stale-lock cleanup semantics.

## Scope

### Included
- Runtime-path lock implementation changes in `wepppy/runtime_paths/thaw_freeze.py` and related modules.
- Runtime-path lock clear/status endpoints and command-bar integration.
- Error payload/message improvements for `NODIR_LOCKED`.
- Tests in `tests/runtime_paths/` and `tests/weppcloud/routes/` covering new lock semantics and command-bar flow.
- Work-package and ExecPlan authoring for implementation.

### Explicitly Out of Scope
- Backward compatibility for active file locks in `/tmp/wepppy-runtime-path-locks`.
- Automatic migration of existing file lock payloads into Redis.
- Changes to NoDb lock schema/behavior beyond UI parity for clear/status actions.
- Queue topology or RQ dependency-graph redesign.

## Stakeholders
- **Primary**: WEPPcloud/RQ operators and runtime-path maintainers.
- **Reviewers**: NoDb and weppcloud route maintainers.
- **Informed**: Support users operating run triage from command bar and job dashboard.

## Success Criteria
- [x] `maintenance_lock` uses Redis as the lock source of truth and no longer relies on local `/tmp` lock files.
- [x] Concurrent lock contention across workers is deterministic and represented through `NODIR_LOCKED` with owner/expiry metadata.
- [x] Command bar supports clearing runtime-path directory locks for the active run.
- [x] `NODIR_LOCKED` guidance points operators to runtime lock clear action or wait-until-expiry behavior.
- [x] New tests validate acquire/release, stale lock reclaim, and command-bar clear flow.
- [x] Validation gates pass for touched suites (`runtime_paths`, `weppcloud routes`, plus pre-handoff sanity).

## Dependencies

### Prerequisites
- Existing Redis connectivity and `wepppy.config.redis_settings` helpers.
- Existing NoDb lock clear/status UX pattern in command bar and `project_bp`.
- Existing runtime-path lock call sites in RQ and rq-engine routes.

### Blocks
- Reliable cross-worker runtime-path lock behavior.
- Operator self-service recovery for stale runtime-path locks.

## Related Packages
- **Most recently completed**: [20260317_omni_contrast_hillslope_rerun](../20260317_omni_contrast_hillslope_rerun/package.md)
- **Follow-up candidates**: Runtime lock observability dashboard and lock ownership attribution improvements.

## Timeline Estimate
- **Expected duration**: 2-4 focused implementation sessions.
- **Complexity**: Medium-High.
- **Risk level**: High (cross-worker locking is a correctness boundary).

## References
- `wepppy/runtime_paths/thaw_freeze.py` - current file-lock implementation.
- `wepppy/runtime_paths/errors.py` - `NODIR_LOCKED` contract.
- `wepppy/weppcloud/routes/nodb_api/project_bp.py` - existing NoDb clear lock route.
- `wepppy/weppcloud/routes/command_bar/static/command-bar.js` - existing `clear locks` command UX.
- `docs/schemas/rq-response-contract.md` - response envelope contract.

## Deliverables
- Redis-backed runtime-path lock implementation.
- Runtime-path lock clear/status route + command-bar command.
- Updated operator-facing lock guidance in runtime lock errors.
- Regression/integration tests and updated work-package docs.

## Follow-up Work
- Evaluate periodic stale runtime-lock janitor telemetry once Redis lock model is stable.
- Consider exposing runtime lock inventory in job dashboard after command-bar parity lands.
