# NoDb Persistence and Concurrency Contract
> Authoritative contract for `NoDbBase` lock ownership, cache hydration, and atomic `.nodb` persistence behavior.
> **See also:** `docs/schemas/rq-response-contract.md`, `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`, `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md`, `tests/nodb/test_base_boundary_characterization.py`

## Normative Status
- This document is normative and authoritative for NoDb persistence/concurrency behavior.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.
- If implementation and this contract diverge, either:
  - implementation MUST be corrected, or
  - this contract MUST be updated in the same change set.

## Scope
- Covers `wepppy/nodb/base.py` behavior for:
  - distributed lock acquisition/release,
  - cache and hydration semantics,
  - stale-write rejection,
  - atomic file persistence and cleanup behavior.
- Applies to all NoDb controllers inheriting `NoDbBase`.
- Does not redefine RQ/API payload schema (see `docs/schemas/rq-response-contract.md`).

## Canonical Storage Model
- Each NoDb controller persists to exactly one `.nodb` JSON file under the run working directory.
- The NoDb file is the durable state source of truth.
- Redis cache mirrors are performance accelerators and MUST be treated as non-authoritative mirrors.
- Redis decode/write failures are handled as best-effort paths; Redis read/connect failures may still surface to callers unless explicitly guarded by the caller path.

## Distributed Lock Contract
### Keying and ownership
- Lock key format MUST be `nodb-lock:<runid>:<relpath>`.
- `relpath` normalization MUST use forward slashes.
- Lock payload MUST include:
  - `token`,
  - `owner` (`<hostname>:<pid>`),
  - `acquired_at`,
  - `expires_at`,
  - `ttl`.
- Lock acquisition MUST write with Redis `SET key payload NX EX <ttl>`.
- Legacy hash fields (`locked:<relpath>`) MAY be mirrored for compatibility, but distributed lock keys are authoritative.

### Acquisition and failure semantics
- `lock()` on a writable run MUST:
  - attempt distributed lock acquisition,
  - raise `NoDbAlreadyLockedError` when lock is already held,
  - record local lock token on success.
- `lock()` on a `READONLY` run MUST fail explicitly.

### Unlock semantics
- `unlock()` without force MUST require matching local token ownership.
- `unlock("-f" | "--force")` MAY release a non-owned lock for operator recovery paths.
- If distributed lock key is already absent, `unlock()` MUST normalize legacy hash state to `false` and clear local token.

### TTL and non-goals
- Default TTL MUST come from `WEPPPY_LOCK_TTL_SECONDS`, fallback `21600` seconds (6 hours).
- Locking is cooperative and participant-scoped:
  - it coordinates writers that use `NoDbBase.lock()/locked()/dump()`,
  - it does not protect against out-of-band file mutation by non-participating processes.
- Locking currently has no built-in heartbeat/renewal; long-running critical sections SHOULD avoid exceeding TTL.
- Lock ownership is validated before persistence and not continuously revalidated during every write step; TTL expiry mid-operation remains a contention risk boundary.

## Hydration and Cache Contract
### `getInstance(...)` singleton semantics
- `getInstance(wd)` SHOULD reuse one in-process cached singleton per controller class and absolute working directory for writable paths.
- `readonly` and `ignore_lock` paths MAY bypass singleton cache insertion/reuse and return detached-style instances.
- Cached singleton reuse MUST be invalidated when on-disk signature differs from tracked signature.
- Signature comparison MUST include `(mtime, size)` checks.
- On signature mismatch, rehydration MUST replace stale cached instance state in place when needed.

### `load_detached(...)` semantics
- `load_detached(wd)` MUST bypass singleton cache insertion and logging initialization side effects.
- It MUST still enforce signature checks when using Redis cache payloads.

### Redis cache usage
- Redis cache reads MAY be used before disk hydration.
- Corrupt cache payload decode failures MUST NOT block disk fallback.
- Stale cache payloads with signature mismatch MUST be ignored and refreshed from disk.
- Callers SHOULD treat transient Redis read/connect errors as operational incidents; some hydrate paths currently surface those failures directly.

## Persistence Contract (`dump`)
### Preconditions
- `dump()` MUST fail when distributed lock ownership is missing or token does not match.
- `dump()` MUST reject stale writes when tracked pre-write `(mtime, size)` does not match current on-disk signature, raising `NoDbStaleWriteError`.

### Atomic write protocol
- Persistence MUST use write-to-temp + atomic replace in the same directory:
  1. create temp file `.<target-basename>.*.tmp` under target directory,
  2. apply target mode (`existing mode` or first-create `0o666 & ~umask`),
  3. write payload, flush, `fsync(temp_fd)`,
  4. atomically `os.replace(temp_path, target_path)`,
  5. best-effort `fsync(parent_dir)`.
- This protocol exists to prevent readers from observing truncate/write partial JSON windows.
- Temp files MUST be cleaned up on failed writes/replaces.
- Internal signature (`_nodb_mtime`, `_nodb_size`) MUST update only after committed write.

### Monotonic signature enforcement
- For same-size rapid rewrites, implementation MUST enforce monotonic post-write mtime so detached stale writers remain rejectable.
- When monotonic mtime advancement cannot be guaranteed, `dump()` MUST fail with `NoDbStaleWriteError` rather than silently persisting ambiguous state.

### Best-effort post-write mirrors
- After a successful durable write, implementation SHOULD best-effort:
  - mirror serialized state to Redis NoDb cache,
  - update run `last_modified` metadata,
  - mirror `last_modified` into Redis lock hash.
- Failures in these mirrors MUST NOT reclassify a committed file write as failed persistence.

## Why Temp Files Are Required
- Direct truncate/write is unsafe under concurrency because readers can observe:
  - empty file at open time,
  - partial JSON snapshots.
- The atomic replace protocol avoids this by publishing either:
  - previous complete payload, or
  - next complete payload.
- The prior truncate/write deficiency is intentionally characterized in
  `tests/nodb/test_base_boundary_characterization.py::test_legacy_truncate_write_window_can_raise_jsondecodeerror`.

## Why Redis Locking Alone Is Not Sufficient
- Redis lock correctness depends on all writers participating in the lock protocol.
- Lock expiry can allow a second writer while the first writer still runs if critical section time exceeds TTL.
- Filesystem-level atomicity and stale-signature validation are required in addition to lock coordination:
  - lock protocol prevents most concurrent writers,
  - stale-write guard rejects detached stale writers,
  - atomic replace prevents decode windows for readers.

## NFS Durability and Error Classification
- Parent directory `fsync` MAY fail on NFS after a successful `os.replace` (for example ESTALE-like conditions).
- When replace has committed and parent-dir fsync fails, implementation SHOULD treat this as a durability warning path, not a stale-write rejection by default.
- Stale-write checks depend on observed `(mtime,size)` signatures; NFS attribute-cache timing and metadata visibility latency can affect when competing writes become visible across clients.
- Operational triage for NFS anomalies and stale-handle symptoms is documented in:
  - `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md`.

## Decoding Expectations and Failure Mode
- `.nodb` payloads MUST always be valid JSON-compatible `jsonpickle` payloads.
- `json.decoder.JSONDecodeError` at `line 1 column 1 (char 0)` is a high-signal indicator of empty/invalid payload ingestion and SHOULD trigger:
  - run-path artifact inspection,
  - cache/file consistency checks,
  - lock/write-path incident triage.

## Cache/Lock Repair Utilities
- `clear_nodb_file_cache(runid, pup_relpath=...)` MAY be used to clear stale Redis cache entries with run-root path safety checks.
- Lock clear utilities MAY normalize legacy hash flags and distributed lock keys for recovery operations.

## Required Regression Coverage
- Changes to lock/persistence behavior MUST maintain or extend targeted regression coverage in:
  - `tests/nodb/test_base_boundary_characterization.py`
- At minimum, coverage MUST include:
  - stale-write rejection,
  - atomic replace contention safety,
  - temp-file cleanup on failure,
  - signature behavior across same-size rewrites,
  - decode-window characterization guardrails.
- Baseline validation commands:
  - `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1`
  - `wctl run-pytest tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1`

## Change Management
- Any change to lock semantics, signature checks, write protocol, or error classification MUST update this contract in the same change set.
- `wepppy/nodb/README.md` and `wepppy/nodb/AGENTS.md` pointers MUST stay aligned with this document.
- Root `AGENTS.md` repository contract pointers MUST include this contract.

## Implementation References
- `wepppy/nodb/base.py`
- `wepppy/nodb/README.md`
- `wepppy/nodb/AGENTS.md`
- `tests/nodb/test_base_boundary_characterization.py`
