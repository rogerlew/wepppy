# Runtime Path Locks Redis Migration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Operators should be able to run and retry jobs across multiple RQ workers without stale directory maintenance locks blocking progress due to host-local `/tmp` state. After this change, runtime-path maintenance locks are stored in Redis as a globally visible source of truth, and operators can clear runtime directory locks from the command bar using a run-scoped action.

Observable result:
- `NODIR_LOCKED` ownership is consistent across workers.
- `clear directory_locks` succeeds regardless of which host originally acquired the lock.
- stale lock recovery is an explicit operator flow rather than host-specific shell triage.

## Progress

- [x] (2026-03-17 17:35 PT) Documented incident evidence proving stale host-local file lock behavior.
- [x] (2026-03-17 17:35 PT) Authored work package (`package.md`, `tracker.md`) and registered active plan pointers.
- [x] (2026-03-17 19:40 PT) Milestone 1: Implemented Redis runtime lock primitive and integrated `thaw_freeze.acquire_maintenance_lock`/`release_maintenance_lock`.
- [x] (2026-03-17 20:05 PT) Milestone 2: Added runtime lock clear/status route and command-bar `clear directory_locks`.
- [x] (2026-03-17 20:20 PT) Milestone 3: Updated `NODIR_LOCKED` operator guidance and maintained canonical route payload handling.
- [x] (2026-03-17 20:35 PT) Milestone 4: Added/adjusted runtime-path and route tests, including clear-token safety and runtime lock route failure paths.
- [x] (2026-03-17 21:05 PT) Milestone 5: Ran validation gates and prepared package closure artifacts.

## Surprises & Discoveries

- Observation: Runtime locks are file-backed at `WEPP_RUNTIME_PATH_LOCK_ROOT` (default `/tmp/wepppy-runtime-path-locks`), not Redis-backed.
  Evidence: `wepppy/runtime_paths/thaw_freeze.py` lock acquire path uses file creation with `os.O_EXCL`.

- Observation: Stale lock file persisted after forced job termination (`Killed horse pid`) and blocked retries for several hours.
  Evidence: `docker-rq-worker-1` logs on `wepp2` and lock payload for `desolate-permutation` with dead owner PID.

- Observation: `POST` clear endpoint in command bar introduced CSRF mismatch risk compared to existing `GET` clear commands.
  Evidence: Subagent code-review finding before closure; switched `clear_directory_locks` to `GET` for parity.

- Observation: Runtime lock clear needed token-safe deletion to avoid deleting a newly reacquired lock between status scan and delete.
  Evidence: Subagent QA finding; updated `clear_runtime_locks` to release by token match and added regression test.

## Decision Log

- Decision: Replace runtime lock backend with Redis and remove file-lock hot-path behavior.
  Rationale: Distributed workers require globally coherent lock ownership and TTL semantics.
  Date/Author: 2026-03-17 / Codex.

- Decision: Do not preserve backward compatibility for existing file-lock artifacts.
  Rationale: User explicitly requested no compatibility path for currently locked projects.
  Date/Author: 2026-03-17 / Codex.

## Outcomes & Retrospective

Completed on 2026-03-17.

Delivered outcomes:
- Runtime-path directory maintenance locks now use Redis as source of truth.
- Added operator-facing command bar support for runtime directory lock status/clear.
- `NODIR_LOCKED` now includes explicit remediation guidance (`:clear directory_locks` or wait for expiry).
- Added and updated route/runtime tests for clear/status behavior and race-safe clear semantics.
- Ran subagent review before closure and addressed all medium/high findings.

Validation evidence:
- `wctl run-pytest tests/runtime_paths --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests --maxfail=1` (pass: `2333 passed, 34 skipped`)

## Context and Orientation

Current runtime lock behavior lives in:
- `wepppy/runtime_paths/thaw_freeze.py`
  - `_lock_path`, `_read_lock_payload`, `_active_lock_payload`, `acquire_maintenance_lock`, `release_maintenance_lock`.
  - uses lock files and JSON payloads with `owner`, `expires_at`, `token`, `scope_token`.
- `wepppy/runtime_paths/errors.py`
  - `NoDirError` and `nodir_locked(...)` contract (`code="NODIR_LOCKED"`, HTTP 503).
- lock call sites in:
  - `wepppy/rq/project_rq.py`
  - `wepppy/rq/culvert_rq.py`
  - `wepppy/rq/land_and_soil_rq.py`
  - `wepppy/microservices/rq_engine/*`

Command-bar and lock operations currently include:
- NoDb clear-lock endpoint: `wepppy/weppcloud/routes/nodb_api/project_bp.py` (`/tasks/clear_locks`).
- Command-bar clear command: `wepppy/weppcloud/routes/command_bar/static/command-bar.js` (`clear locks`, `clear nodb_cache`).
- Command-bar route module: `wepppy/weppcloud/routes/command_bar/command_bar.py`.

Redis settings helpers are available via:
- `wepppy/config/redis_settings.py`

## Plan of Work

Milestone 1 - Redis runtime lock primitive

Replace file lock storage with Redis lock records keyed by runtime scope/root. Acquire must be atomic (`SET key value NX EX ttl` or equivalent), release must be token-validated, and lock payload must preserve current metadata (`owner`, `expires_at`, `token`, `scope_token`, `purpose`, `runid`, `root`). Remove lock-file path reliance from acquire/release flow.

Milestone 2 - Runtime lock clear/status operations

Introduce run-scoped runtime lock clear/status helper(s) that can find lock keys for supported roots and remove stale or active locks intentionally via explicit operator route. Expose route(s) that follow canonical response envelopes.

Milestone 3 - Command-bar integration and operator guidance

Add `clear directory_locks` (and aliases) in command bar. Keep existing `clear locks` behavior for NoDb locks unchanged. Update help text and result messaging to distinguish NoDb locks vs runtime directory locks. Improve `NODIR_LOCKED` message guidance to mention clear command and wait-for-expiry path.

Milestone 4 - Test coverage

Add/adjust tests for:
- runtime lock contention and release semantics (including token mismatch safety),
- TTL/expiry reclaim behavior,
- route responses for clear/status runtime locks,
- command-bar parser/handler coverage for `clear directory_locks`.

Milestone 5 - Validation and closure

Run focused and broad validation, update tracker and package closure notes, and move this ExecPlan to `prompts/completed/` when done.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement Redis lock backend in runtime paths.

    edit wepppy/runtime_paths/thaw_freeze.py
    edit wepppy/runtime_paths/__init__.py (if exports change)
    edit related helper module(s) if extracted

2. Add clear/status runtime lock helpers and route wiring.

    edit wepppy/weppcloud/routes/nodb_api/project_bp.py
    edit wepppy/weppcloud/routes/command_bar/command_bar.py (if route-local endpoint preferred)

3. Update command bar UX for runtime lock clear.

    edit wepppy/weppcloud/routes/command_bar/static/command-bar.js
    edit wepppy/weppcloud/routes/command_bar/README.md

4. Add/adjust tests.

    edit tests/runtime_paths/<new_or_existing_tests>.py
    edit tests/weppcloud/routes/<new_or_existing_tests>.py

5. Validate.

    wctl run-pytest tests/runtime_paths --maxfail=1
    wctl run-pytest tests/weppcloud/routes --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance is complete when:
- Runtime locks are stored and managed in Redis only during normal lock operations.
- Two workers contending for the same run/root report consistent ownership and expiry.
- `clear directory_locks` removes runtime lock records for the run and unblocks retry.
- `NODIR_LOCKED` includes actionable remediation text and still returns canonical error structure.
- Targeted runtime-path and route tests pass, followed by pre-handoff full-suite sanity.

## Idempotence and Recovery

- Redis lock acquire/release operations must be idempotent under retries and worker restarts.
- Release operation must remove only lock records whose token matches the caller lock token.
- If deployment occurs with in-flight jobs, worker restart order should be controlled to minimize mixed backend behavior; any leftover file locks may be manually deleted without affecting Redis lock correctness.

## Artifacts and Notes

Expected implementation artifacts:
- Updated runtime lock implementation (`thaw_freeze.py`).
- Route/command-bar handlers for runtime lock clear.
- Test evidence from runtime paths + route suites.
- Tracker updates summarizing design deltas discovered during implementation.

## Interfaces and Dependencies

Target interfaces to exist after implementation:
- Runtime lock acquire/release functions in `wepppy.runtime_paths.thaw_freeze` with existing call signatures preserved for callers.
- Run-scoped runtime lock clear operation exposed via HTTP route returning canonical success/error payload.
- Command-bar clear subcommand for runtime directory locks.

Dependencies:
- Redis RQ connection settings from `wepppy.config.redis_settings`.
- Existing auth/run-context route guards and response helpers.

---
Revision Note (2026-03-17, Codex): Initial ExecPlan drafted from live stale lock incident and user direction to migrate runtime directory locks to Redis without backward compatibility for legacy file-lock state.
Revision Note (2026-03-17, Codex): Completed implementation, added runtime lock command-bar controls/tests, resolved pre-closure subagent findings, and finalized validation evidence.
