# Tracker - Runtime Path Locks: Redis Migration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-17  
**Current phase**: Closed - implementation and validation complete  
**Last updated**: 2026-03-17  
**Next milestone**: None (package closed)  
**Implementation plan**: `docs/work-packages/20260317_runtime_path_redis_locks/prompts/completed/runtime_path_redis_locks_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Captured production failure mode for stale file lock (`NODIR_LOCKED`, owner PID dead, lock file persisted on remote worker) (2026-03-17).
- [x] Confirmed file-lock implementation is local-path based (`/tmp/wepppy-runtime-path-locks`) and therefore non-global across workers (2026-03-17).
- [x] Authored work-package scaffold and active ExecPlan for Redis migration (2026-03-17).
- [x] Registered package in `PROJECT_TRACKER.md` and set active ExecPlan pointer in `AGENTS.md` (2026-03-17).
- [x] Replaced runtime-path file locks with Redis-backed locks in `wepppy/runtime_paths/thaw_freeze.py`, including run-scoped status/clear helpers (2026-03-17).
- [x] Added command-bar runtime directory lock endpoints and frontend commands (`get directory_locks`, `clear directory_locks`) (2026-03-17).
- [x] Added/updated tests for runtime lock clear safety and command-bar runtime lock routes (2026-03-17).
- [x] Addressed subagent review findings (HTTP verb/CSRF parity, token-safe clear, negative-path route coverage) (2026-03-17).
- [x] Completed validation gates (`tests/runtime_paths`, `tests/weppcloud/routes`, broad-exception guard, full `tests --maxfail=1`) (2026-03-17).

## Timeline

- **2026-03-17** - Package created from live stale-lock incident.
- **2026-03-17** - Active ExecPlan drafted and linked.
- **2026-03-17** - Milestone 1 complete (Redis runtime lock backend in place).
- **2026-03-17** - Milestone 2 complete (command-bar clear/status operations + guidance).
- **2026-03-17** - Milestone 3 complete (tests, validation, and package closure).

## Decisions

### 2026-03-17: Make Redis the only runtime lock backend
**Context**: Local file locks in `/tmp` are host/container scoped and cannot represent global lock ownership in a multi-worker fleet.

**Options considered**:
1. Keep file locks and add cross-host fanout clear tooling.
2. Move runtime locks to shared filesystem path.
3. Move runtime locks to Redis (global distributed source of truth).

**Decision**: Option 3.

**Impact**: Removes cross-host lock ambiguity and aligns runtime lock operability with existing Redis-first control surfaces.

---

### 2026-03-17: Do not preserve compatibility for legacy file lock artifacts
**Context**: User requested no compatibility for currently locked projects.

**Options considered**:
1. Dual-read old file locks and new Redis locks during transition.
2. One-way migration script from file locks to Redis.
3. Cut over directly to Redis and treat old files as irrelevant.

**Decision**: Option 3.

**Impact**: Simpler implementation and fewer split-brain semantics; operators may need one-time manual cleanup of old lock files.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Lock semantics regress under contention | High | Medium | Added contention + clear token-safety tests in `tests/runtime_paths/test_mutations_thaw_freeze_contract.py` | Mitigated |
| Redis outage affects runtime lock acquire paths | High | Low-Med | Runtime lock command-bar endpoints map runtime lock errors to 503 with canonical payloads | Mitigated |
| In-flight jobs during deploy may observe mixed lock backend | Medium | Medium | File-lock path removed from hot path; package explicitly excludes file-lock compatibility | Accepted |
| Command-bar route deviates from canonical error envelope | Medium | Low | Added explicit runtime error handling and route tests for 503 flows | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/runtime_paths --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes --maxfail=1`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] `wctl run-pytest tests --maxfail=1`

### Documentation
- [x] `wctl doc-lint --path docs/work-packages/20260317_runtime_path_redis_locks`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path AGENTS.md`

### Behavioral Validation
- [x] Runtime lock contention across workers returns deterministic `NODIR_LOCKED`.
- [x] Runtime lock clear command removes active Redis runtime lock for run/root scope.
- [x] Error guidance provides actionable operator instructions.

## Progress Notes

### 2026-03-17: Incident triage and package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Investigated `desolate-permutation` lock incident across `wepp1` and `wepp2`.
- Confirmed stale runtime lock file persisted after `Killed horse pid` event.
- Validated root cause was local file lock state on remote worker.
- Authored this work package and active ExecPlan with Redis migration scope.

**Blockers encountered**:
- None for planning.

**Next steps**:
1. Implement Redis lock primitive in `thaw_freeze.py`.
2. Add runtime lock clear route + command-bar integration.
3. Add tests and execute validation gates.

**Test results**:
- Planning/documentation session only; no code-change tests executed.

### 2026-03-17: Implementation and closure
**Agent/Contributor**: Codex

**Work completed**:
- Migrated runtime lock acquire/release/status/clear operations to Redis-backed keys.
- Added command-bar runtime directory lock endpoints and frontend commands.
- Added operator guidance in `NODIR_LOCKED` messages (`:clear directory_locks`).
- Ran subagent code review + QA review and resolved identified issues before closure.

**Blockers encountered**:
- None. Subagent runtime had transient sandbox tooling noise, but findings were delivered and addressed.

**Test results**:
- `wctl run-pytest tests/runtime_paths --maxfail=1` -> pass
- `wctl run-pytest tests/weppcloud/routes --maxfail=1` -> pass
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass
- `wctl run-pytest tests --maxfail=1` -> pass (`2333 passed, 34 skipped`)

## Communication Log

### 2026-03-17: User direction on migration strategy
**Participants**: User, Codex  
**Question/Topic**: Choose cross-worker runtime lock strategy and author work package.  
**Outcome**: Selected Redis lock backend (option 2 from discussion), with explicit no-compatibility stance for existing locked projects; work package created.

### 2026-03-17: Pre-closure review request
**Participants**: User, Codex, reviewer subagents  
**Question/Topic**: Run code review + QA review before closure.  
**Outcome**: Incorporated findings (GET verb parity for clear endpoint, token-safe clear race fix, added failure-path tests) and revalidated all required gates.
