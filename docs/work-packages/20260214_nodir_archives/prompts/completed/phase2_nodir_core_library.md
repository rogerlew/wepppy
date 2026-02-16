# Agent Prompt: Phase 2 (NoDir Core Library v1)

## Mission
Implement Phase 2: a shared, unit-testable Python NoDir core library that centralizes dir-vs-archive discovery, archive-boundary parsing, and archive-native list/stat/open for allowlisted `*.nodir` roots.

You are NOT implementing browse/files/download integration (Phase 3), materialization (Phase 4), or thaw/freeze workflows (Phase 5) beyond what is required to correctly *detect* transitional sentinels and return the correct error.

## Specs (Read First)
Normative:
- `docs/schemas/nodir_interface_spec.md`
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Reference:
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md` (Phase 4; only relevant for error codes + transitional locking rules)

## Scope Constraints
- No speculative abstractions. Implement only what Phase 2 needs.
- Do not add silent fallbacks that mask invalid archives or mixed state.
- No extract-to-disk for list/stat/open (archive form).
- No network.

## Target Package Layout
Create/extend `wepppy/nodir/`:
- `wepppy/nodir/__init__.py`: explicit `__all__` exports for the public API.
- `wepppy/nodir/errors.py`: typed exception(s) carrying `{http_status, code, message}`.
- `wepppy/nodir/paths.py`: relpath normalization + archive-boundary parsing.
- `wepppy/nodir/fs.py`: `resolve`, `listdir`, `stat`, `open_read`.

Use `wepppy/nodir/parquet_sidecars.py` for parquet sidecar mapping.

## Required Behaviors
### 1) Allowlist + Boundary Parsing
Implement `parse_external_subpath(rel: str, *, allow_admin_alias: bool) -> tuple[str, NoDirView]` per spec:
- Normalize slashes and reject `\x00`, absolute paths, and any `..` segment.
- Detect archive-boundary syntax: `<root>.nodir/<inner>` selects `view="archive"` only when `<root>` is allowlisted (`landuse|soils|climate|watershed`).
- Admin alias: `<root>/nodir/<inner>` selects `view="archive"` only when `allow_admin_alias=True`.

### 2) Representation Discovery
Implement `resolve(wd: str, rel: str, *, view: NoDirView = "effective") -> ResolvedNoDirPath | None` per spec.
- Return `None` when `rel` is not under an allowlisted NoDir root.
- Enforce mixed state in `view="effective"` as `409; code=NODIR_MIXED_STATE`.
- Enforce invalid allowlisted archive (zip validation failure) as `500; code=NODIR_INVALID_ARCHIVE` for `view in {"effective","archive"}`.
- Transitional sentinels:
  - If `WD/<root>.thaw.tmp/` OR `WD/<root>.nodir.tmp` exists, treat the root as transitioning and raise `503; code=NODIR_LOCKED` for `view in {"effective","archive"}`.
  - This is **read path** behavior for Phase 2 (do not attempt cleanup).

### 3) Parquet Sidecars
Inside `resolve/stat/open_read`:
- For logical `*.parquet` under allowlisted roots, prefer the WD-level sidecar mapping.
- MUST NOT fall back to a zip entry for parquet when in Archive form.

### 4) Archive-Native list/stat/open_read
Implement:
- `listdir(target: ResolvedNoDirPath) -> list[NoDirDirEntry]`
- `stat(target: ResolvedNoDirPath) -> NoDirDirEntry`
- `open_read(target: ResolvedNoDirPath) -> BinaryIO`

Archive form requirements:
- Use zip central directory to derive entries.
- No extraction.
- Reject unsafe names (absolute, `..`, null bytes, path normalization escaping root).
- Reject non-regular file types (symlinks, etc.) per contract.

Dir form:
- Use filesystem operations under `WD/<root>/...`.

## Tests (Must Add)
Add new unit tests under `tests/nodir/` (keep fast, no Redis required):
- Path normalization rejects traversal and normalizes `\\` to `/`.
- Boundary parsing:
  - `watershed.nodir/a/b` selects archive view.
  - `foo.nodir/a` is NOT treated as archive boundary (non-allowlisted) and remains `effective`.
  - Admin alias parsing only when `allow_admin_alias=True`.
- `resolve`:
  - Mixed state returns `NODIR_MIXED_STATE`.
  - Invalid archive returns `NODIR_INVALID_ARCHIVE`.
  - Transitional sentinel (`*.thaw.tmp/` or `*.nodir.tmp`) returns `NODIR_LOCKED`.
- Archive-native list/stat/open_read:
  - Create a small `.nodir` zip with nested files; verify `listdir` returns expected immediate children.
  - Verify `open_read` returns correct bytes for an entry.

## Commands
Run tests in the canonical environment:
```bash
wctl run-pytest tests/nodir
```
If you touch call sites outside `tests/nodir/`, also run:
```bash
wctl run-pytest tests --maxfail=1
```

## Acceptance Criteria
- Phase 2 API exists and matches `docs/schemas/nodir_interface_spec.md`.
- All new/updated tests pass via `wctl run-pytest ...`.
- No extraction-to-disk for list/stat/open (archive form).
- Error codes and statuses match the contracts exactly.
