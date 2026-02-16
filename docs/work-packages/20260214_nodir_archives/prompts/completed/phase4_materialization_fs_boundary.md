# Agent Prompt: Phase 4 (Materialization + FS-Boundary Endpoints)

## Mission
Implement Phase 4: add NoDir materialization for archive-backed entries and wire FS-boundary endpoints that require real filesystem paths.

Phase 2 and Phase 3 are complete. Reuse shared NoDir core APIs and keep browse/files/download archive-native (no extraction in those surfaces).

## Specs (Read First)
Normative:
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Reference:
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

## Scope Constraints
- In scope:
  - implement materialization core,
  - wire FS-boundary endpoints (dtale, gdalinfo, diff, exports) to use materialization when archive-backed.
- Out of scope:
  - browse/files/download extraction (must remain archive-native),
  - thaw/freeze mutation workflows (Phase 5),
  - bulk migration crawler (Phase 7).
- No silent fallbacks.
- Fail fast on mixed/invalid/locked states with canonical error codes.

## Implementation Targets
Create/extend:
- `wepppy/nodir/materialize.py` (new)
- `wepppy/nodir/__init__.py` exports (add materialization public API)

Integrate into FS-boundary surfaces:
- `wepppy/microservices/browse/dtale.py`
- `wepppy/microservices/_gdalinfo.py`
- `wepppy/weppcloud/routes/diff/diff.py`
- Export call paths that require real files (trace from touchpoints inventory)

## Required Behaviors
### 1) Cache Layout + Fingerprints
Implement cache paths exactly per contract:
- `WD/.nodir/cache/<root>/<archive_fp>/<entry_id>/...`
- `WD/.nodir/tmp/<root>/<archive_fp>/<uuid4>/...` for subset extraction

Use:
- archive fingerprint: `(mtime_ns, size_bytes)`
- entry fingerprint: central directory metadata (`inner_path`, crc32, sizes, method)

### 2) Locking
- Per-entry materialization lock key:
  - `nodb-lock:<runid>:nodir-materialize/<root>/<entry_id>`
- Fail-fast lock behavior:
  - contention -> `503; code=NODIR_LOCKED`

### 3) Preconditions and Error Semantics
Before extraction:
- mixed state -> `409; code=NODIR_MIXED_STATE`
- invalid allowlisted archive -> `500; code=NODIR_INVALID_ARCHIVE`
- transitioning root (`state in {thawing, freezing}` or temp sentinels per contract) -> `503; code=NODIR_LOCKED`
- limits exceeded -> `413; code=NODIR_LIMIT_EXCEEDED`

### 4) Extraction Safety and Atomicity
- Never return partial files.
- Write temp files under entry dir, verify size + CRC, then `os.replace()`.
- Treat zip entries as untrusted; enforce path normalization and reject non-regular types.
- No symlink creation from archive metadata.

### 5) Sidecar Group Handling
Implement required grouped extraction:
- `.shp` request must also include required/optional sidecars per contract.
- `.tif/.tiff` should include known sidecars when present.

### 6) FS-Boundary Integration Rules
- Endpoints that need real paths must call `materialize_file(...)` when archive-backed.
- Endpoints must not treat archive form as “not found.”
- Browse/files/download endpoints must not call materialization.

## Tests (Must Add/Update)
Add tests for `wepppy/nodir/materialize.py` and integrations.

Minimum materialization tests:
1. Cache hit returns existing path without re-extraction.
2. Cache mismatch triggers rebuild.
3. Lock contention returns `503 NODIR_LOCKED`.
4. Limit enforcement returns `413 NODIR_LIMIT_EXCEEDED`.
5. Invalid archive / unsafe entry returns `500 NODIR_INVALID_ARCHIVE`.
6. Atomicity: failed extraction leaves no partial final files.
7. SHP/TIF sidecar grouping behavior.

Minimum integration tests:
1. `dtale` archive-backed file path materializes and succeeds.
2. `gdalinfo` archive-backed file path materializes and succeeds.
3. `diff` archive-backed file path materializes (or returns explicit unsupported error if contract says so).
4. Mixed/invalid/locked states are surfaced with canonical codes.

## Commands
Iterate with focused tests first:
```bash
wctl run-pytest tests/nodir -k "materialize or nodir"
wctl run-pytest tests/microservices -k "dtale or gdalinfo or diff or nodir"
```

Before handoff, run full regression gate:
```bash
wctl run-pytest tests --maxfail=1
```

If frontend JS touched:
```bash
wctl run-npm test
```

## Acceptance Criteria
- `wepppy/nodir/materialize.py` implemented per contract (cache, lock, limits, safety).
- FS-boundary endpoints correctly materialize archive-backed paths.
- Canonical status/code mapping is preserved (`409/500/503/413`).
- Browse/files/download remain archive-native (no extraction).
- New and updated tests pass via `wctl` in container.
