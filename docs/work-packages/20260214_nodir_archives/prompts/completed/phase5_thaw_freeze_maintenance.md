# Agent Prompt: Phase 5 (Thaw/Freeze + Maintenance Plumbing)

## Mission
Implement Phase 5: the crash-safe NoDir thaw/freeze state machine and maintenance plumbing.

Phases 2-4 are complete. This phase adds authoritative maintenance/state transitions for NoDir roots and prepares mutation workflows for Phase 6.

## Specs (Read First)
Normative:
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Interaction contract:
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`

## Scope Constraints
- In scope:
  - state file model + atomic writes,
  - maintenance lock acquisition and ownership wiring,
  - thaw(root) and freeze(root) workflows,
  - crash recovery for `.thaw.tmp` and `.nodir.tmp`,
  - maintenance-only cleanup routines.
- Out of scope:
  - broad root-by-root mutation adoption in controllers/RQ/mods (Phase 6),
  - migration crawler rollout (Phase 7),
  - changing browse/files/download/archive-read semantics from Phase 3.
- Mixed state remains an error outside admin observability; do not introduce keep-directory mode.

## Implementation Targets
Create/extend under `wepppy/nodir/`:
- `wepppy/nodir/state.py` (new)
- `wepppy/nodir/thaw_freeze.py` (new)
- `wepppy/nodir/__init__.py` exports

Integrate with existing components:
- `wepppy/nodir/materialize.py` (transitional-state/lock interactions)
- any existing lock utilities used by NoDb distributed locks

## Required Behaviors
### 1) State File Schema and Atomicity
Implement state read/write for `WD/.nodir/<root>.json` with required fields:
- `schema_version`, `root`, `state`, `op_id`, `host`, `pid`, `lock_owner`, `dir_path`, `archive_path`, `dirty`, `archive_fingerprint`, `updated_at`

Rules:
- atomic write (`tmp + fsync + os.replace`)
- strict validation for required fields and allowed enums
- `dir_path == <root>` and `archive_path == <root>.nodir` (v1 constraints)
- `lock_owner == "{host}:{pid}"`

### 2) Maintenance Locking
Acquire maintenance lock before any writes to:
- state file,
- `WD/<root>.thaw.tmp/`,
- `WD/<root>.nodir.tmp`,
- `WD/<root>.nodir`,
- directory deletion.

Lock key:
- `nodb-lock:<runid>:nodir/<root>`

Rules:
- fail-fast on lock contention
- deterministic ordering for multi-root ops (alphabetical)
- include lock-owner metadata in state transitions

### 3) Thaw Workflow (Archive -> Directory)
Implement `thaw_root(...)` (name may vary) with:
1. lock acquired
2. state -> `thawing`, `dirty=true`, set op/lock metadata + archive fingerprint
3. extract to `WD/<root>.thaw.tmp/` with zip-slip/type defenses
4. atomic rename `WD/<root>.thaw.tmp/` -> `WD/<root>/`
5. state -> `thawed`, `dirty=true`

Crash recovery behavior:
- if `state=thawing` and temp exists with no final dir: cleanup/restart (or safe resume if provable)
- if final dir exists: treat thaw as complete and remove stale temp

### 4) Freeze Workflow (Directory -> Archive)
Implement `freeze_root(...)` with:
1. lock acquired
2. state -> `freezing`
3. build `WD/<root>.nodir.tmp` from `WD/<root>/`:
  - dereference symlinked files to regular entries
  - apply allowlist validation for symlink targets
  - enforce parquet sidecar rules (no parquet inside `.nodir`)
  - validate entry names/types
4. verify temp archive readable + valid
5. atomic rename temp archive -> `WD/<root>.nodir`
6. remove `WD/<root>/` (required to avoid mixed state)
7. state -> `archived`, `dirty=false`, fingerprint updated

Crash recovery behavior:
- if `state=freezing` and `.nodir.tmp` exists: delete/rebuild temp archive

### 5) Transitional Sentinel and Materialization Interaction
- If state is `thawing` or `freezing`, materialization must continue to return `503 NODIR_LOCKED`.
- If state file is missing but temp sentinel exists (`*.thaw.tmp` / `*.nodir.tmp`), treat as transitioning/locked for request-serving and materialization paths.
- Request-serving code must not perform automatic cleanup; cleanup is maintenance-only under maintenance lock.

### 6) Observability and Logs
Emit structured logs for:
- `runid`, `root`, `op_id`, `state_before`, `state_after`, `lock_owner`
- archive fingerprint before/after
- crash-recovery actions taken (cleanup/restart/rebuild)

## Tests (Must Add/Update)
Add focused tests under `tests/nodir/` (and integration tests only where needed).

Minimum state/thaw/freeze tests:
1. state file write/read round-trip with required fields and constraints
2. atomic write behavior (no partial final JSON)
3. thaw happy path (archive -> dir + state transitions)
4. freeze happy path (dir -> archive + dir removal + state transitions)
5. crash recovery: stale `.thaw.tmp` handling
6. crash recovery: stale `.nodir.tmp` handling
7. lock contention returns canonical locked error
8. missing state + temp sentinel treated as locked
9. mixed-state prevention during freeze (final state not mixed)

Materialization interaction tests:
1. `state=thawing` causes materialize to return `503 NODIR_LOCKED`
2. `state=freezing` causes materialize to return `503 NODIR_LOCKED`

## Commands
Iterate quickly:
```bash
wctl run-pytest tests/nodir -k "state or thaw or freeze or materialize or nodir"
```

Before handoff:
```bash
wctl run-pytest tests --maxfail=1
```

## Acceptance Criteria
- `state.py` and `thaw_freeze.py` implement the contract with atomic writes and lock discipline.
- Thaw/freeze workflows are crash-safe and enforce strict mixed-state avoidance.
- Transitional states/sentinels properly gate materialization and request-serving behaviors.
- Regression tests pass in `wctl` containerized runs.
