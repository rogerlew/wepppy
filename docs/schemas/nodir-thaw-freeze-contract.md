# NoDir Thaw/Freeze Contract (Maintenance State)
> **Archived / Deprecated (Historical, 2026-02-27):** This NoDir specification is retired from active contract flow after the directory-only reversal. It is retained only for historical/audit reference.

> Authoritative contract for the NoDir per-root maintenance state file (`WD/.nodir/<root>.json`) and the crash-safe thaw/modify/freeze workflow.
>
> **See also:** `docs/schemas/nodir-contract-spec.md`, `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`, `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`, `docs/schemas/rq-response-contract.md`

## Normative Status
- This document is normative for NoDir thaw/freeze state tracking and crash recovery.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.

## Scope
- Applies to allowlisted NoDir roots: `landuse`, `soils`, `climate`, `watershed`.
- Applies to any workflow that transitions a root between Directory form (`WD/<root>/`) and Archive form (`WD/<root>.nodir`):
  - migration tooling,
  - controller/RQ mutation workflows that must operate on a directory and then re-archive.
- Does not redefine archive semantics, security rules, browse URL parsing, or Parquet sidecars: see `docs/schemas/nodir-contract-spec.md`.
- Does not redefine per-entry materialization cache: see `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`.

## State File Location and Atomicity
- Per-root state file: `WD/.nodir/<root>.json`.
- `WD/.nodir/` is internal and MUST NOT be user-addressable via browse/files/download path resolution.
- State file writes MUST be atomic:
  - write to a sibling temp file (example: `WD/.nodir/<root>.json.tmp.<pid>.<rand>`),
  - `fsync()` the temp file (recommended),
  - install with `os.replace(temp, final)`.

If the state file is missing:
- Public read-only surfaces MUST continue to resolve representation via existence checks (dir vs archive) per `docs/schemas/nodir-contract-spec.md`.
- Maintenance/materialization code MUST treat the root as `state="unknown"` and use on-disk sentinels (`WD/<root>.thaw.tmp/`, `WD/<root>.nodir.tmp`) plus locks to avoid unsafe concurrent work.

## State Schema (WD/.nodir/<root>.json)

### Required Fields
- `schema_version` (int): starts at `1`.
- `root` (str): one of `landuse|soils|climate|watershed`.
- `state` (str enum): `archived|thawing|thawed|freezing`.
- `op_id` (str): uuid4 for the current thaw/freeze operation (stable across state updates within the operation).
- `host` (str): hostname writing the state file.
- `pid` (int): process id writing the state file.
- `lock_owner` (str): lock owner identifier (matches NoDb distributed lock payload `owner`, format `host:pid`).
- `dir_path` (str): relative path for Directory form (example: `"watershed"`).
- `archive_path` (str): relative path for Archive form (example: `"watershed.nodir"`).
- `dirty` (bool): whether the directory form is considered modified since the last successful freeze.
- `archive_fingerprint` (object):
  - `mtime_ns` (int)
  - `size_bytes` (int)
- `updated_at` (str): UTC ISO-8601 timestamp (example: `"2026-02-15T03:12:45Z"`).

Constraints:
- `dir_path` MUST equal `<root>` (v1) and MUST NOT contain `/`, `\\`, or `..` segments.
- `archive_path` MUST equal `<root>.nodir` (v1) and MUST NOT contain `/`, `\\`, or `..` segments.
- `lock_owner` MUST equal `${host}:${pid}` (v1).

### Optional Fields
- `note` (str): freeform operator/debug string (not machine-parsed).

### JSON Schema (Informative)
```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "root",
    "state",
    "op_id",
    "host",
    "pid",
    "lock_owner",
    "dir_path",
    "archive_path",
    "dirty",
    "archive_fingerprint",
    "updated_at"
  ],
  "properties": {
    "schema_version": { "type": "integer", "minimum": 1 },
    "root": { "type": "string", "enum": ["landuse", "soils", "climate", "watershed"] },
    "state": { "type": "string", "enum": ["archived", "thawing", "thawed", "freezing"] },
    "op_id": { "type": "string" },
    "host": { "type": "string" },
    "pid": { "type": "integer", "minimum": 1 },
    "lock_owner": { "type": "string" },
    "dir_path": { "type": "string" },
    "archive_path": { "type": "string" },
    "dirty": { "type": "boolean" },
    "archive_fingerprint": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mtime_ns", "size_bytes"],
      "properties": {
        "mtime_ns": { "type": "integer", "minimum": 0 },
        "size_bytes": { "type": "integer", "minimum": 0 }
      }
    },
    "updated_at": { "type": "string" },
    "note": { "type": "string" }
  }
}
```

## State Semantics and Invariants

### archive_fingerprint
- `archive_fingerprint` MUST reflect `stat(WD/<root>.nodir)` at the time the state record is written.
- Fingerprint definition:
  - `mtime_ns := st_mtime_ns`
  - `size_bytes := st_size`

### dirty
- `dirty=true` means the directory form is authoritative and the archive (if present) MUST be treated as stale for maintenance decisions.
- `dirty` is best-effort and MUST be treated conservatively:
  - any `thaw` MUST set `dirty=true`,
  - any successful `freeze` to an authoritative archive MUST set `dirty=false`.

### Invariants by state
- `state="archived"`:
  - `WD/<root>.nodir` MUST exist and validate as a NoDir archive (allowlisted + safe entry names).
  - `WD/<root>/` MUST NOT exist.
  - `dirty` MUST be `false`.
- `state="thawed"`:
  - `WD/<root>/` MUST exist.
  - `dirty` MAY be `true` or `false`.
  - `WD/<root>.nodir` MAY exist (stale or fresh), but mixed-state public semantics still apply (see `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`).
- `state="thawing"`:
  - `WD/<root>.thaw.tmp/` MAY exist.
  - `WD/<root>/` MUST NOT be considered stable/authoritative until thaw completes.
- `state="freezing"`:
  - `WD/<root>.nodir.tmp` MAY exist.
  - `WD/<root>.nodir` MUST NOT be considered updated/authoritative until freeze completes.

## Locking Contract (Required)
- Any code that writes any of:
  - `WD/.nodir/<root>.json`,
  - `WD/<root>.thaw.tmp/`,
  - `WD/<root>.nodir.tmp`,
  - `WD/<root>.nodir`,
  - `WD/<root>/` deletion,
  MUST acquire the NoDir maintenance lock first.
- Lock key: `nodb-lock:<runid>:nodir/<root>`.
- Bulk migrators SHOULD require `WD/READONLY` to be present (and refuse to run otherwise).
- If a workflow needs multiple roots, it MUST acquire locks in deterministic order (alphabetical by `<root>`) and fail fast on the first lock acquisition failure.

## Thaw (Archive -> Directory)
Preconditions:
- Caller MUST hold `nodb-lock:<runid>:nodir/<root>`.
- `WD/<root>.nodir` MUST exist and validate.
- `WD/<root>/` MUST NOT exist (mixed-state is not a valid thaw target).

Procedure:
1. Write state: `state="thawing"`, `dirty=true`, `archive_fingerprint=stat(WD/<root>.nodir)` (and include required op/lock fields).
2. Ensure `WD/<root>.thaw.tmp/` does not exist (if it does, treat as crash recovery; see below).
3. Extract archive to `WD/<root>.thaw.tmp/` with zip-slip defenses and strict entry validation.
4. Atomically rename `WD/<root>.thaw.tmp/` -> `WD/<root>/`.
5. Write state: `state="thawed"`, `dirty=true`, `archive_fingerprint=stat(WD/<root>.nodir)` (best-effort; archive may be deleted out-of-band).

Crash recovery:
- If `state="thawing"`:
  - If `WD/<root>.thaw.tmp/` exists and `WD/<root>/` does not: tooling SHOULD delete the temp dir and restart the thaw (preferred) or resume extraction if it can prove completeness.
  - If `WD/<root>/` exists: tooling SHOULD treat the thaw as complete and delete `WD/<root>.thaw.tmp/` if present.

## Modify (Directory Authoritative)
- While `state="thawed"`, mutations MUST target `WD/<root>/` only.
- Any mutation path SHOULD set `dirty=true` in `WD/.nodir/<root>.json` (best-effort).

## Freeze (Directory -> Archive)
Preconditions:
- Caller MUST hold `nodb-lock:<runid>:nodir/<root>`.
- `WD/<root>/` MUST exist.
- `WD/<root>.nodir.tmp` MUST NOT be treated as a usable archive.

Procedure:
1. Write state: `state="freezing"` (leave `dirty` as-is).
2. Build `WD/<root>.nodir.tmp` from `WD/<root>/`:
  - dereference symlinked files into regular archive entries (no symlink metadata),
  - enforce Parquet sidecar rules (no `.parquet` entries inside `.nodir`),
  - validate archive entry paths are safe/normalized.
3. Verify `WD/<root>.nodir.tmp` is readable and validates as a NoDir archive.
4. Atomically rename `WD/<root>.nodir.tmp` -> `WD/<root>.nodir`.
5. Remove `WD/<root>/` after successful archive verification (required; mixed state is an error).
6. Write state: `state="archived"`, `dirty=false`, `archive_fingerprint=stat(WD/<root>.nodir)`.

Crash recovery:
- If `state="freezing"` and `WD/<root>.nodir.tmp` exists: tooling SHOULD delete the temp archive and rebuild it.

## Interactions (Materialization + Public Surfaces)
- If `state in {"thawing","freezing"}` (when a state file exists), `materialize(file)` MUST fail fast with `503; code=NODIR_LOCKED` per `nodir_materialization_contract.md`.
- Public browse/files/download endpoints MUST NOT trigger thaw or freeze; they remain archive-native streaming (or FS-native for Dir form) per the behavior matrix.

## Transitional Sentinels (Missing State File)
If the state file is missing but either of these exist:
- `WD/<root>.thaw.tmp/`
- `WD/<root>.nodir.tmp`

Then the root MUST be treated as transitioning:
- Request-serving code (browse/files/download/query-engine/dtale/gdalinfo) MUST NOT attempt cleanup.
- FS-boundary materialization MUST fail fast with `503; code=NODIR_LOCKED`.
- Only maintenance tooling holding `nodb-lock:<runid>:nodir/<root>` may clean up temp artifacts and write a new state file.
