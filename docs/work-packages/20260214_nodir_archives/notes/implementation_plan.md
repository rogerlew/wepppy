# NoDir Implementation Plan (Multi-Phase)

**Work package:** `docs/work-packages/20260214_nodir_archives/package.md`  
**Last updated:** 2026-02-16  
**Primary specs:** `docs/schemas/nodir-contract-spec.md`, `docs/schemas/nodir-thaw-freeze-contract.md`

## Current State (Snapshot)

Completed:
- Contract docs are in place: directory vs archive semantics, URL boundaries, error codes, parquet sidecars, and thaw/freeze state schema.
- Normative behavior matrix exists for all major surfaces (browse/files/download, query engine, mutations/migrations).
- Parquet sidecar resolution is implemented (`wepppy/nodir/parquet_sidecars.py`) and adopted by query engine + migrations.
  - Query engine path validation now prevents catalog entries from escaping the run boundary (and supports parent-run reads for `_pups/...` layouts).
- RQ dependency catalog updated to treat NoDir parquet prerequisites as logical ids (physical sidecar resolution is internal).
- Targeted regression tests added for parquet sidecars and SWAT interchange sidecar reads.
- Phase 2 shared NoDir core library is complete (two review rounds; see commits `cc8dc214e`, `d559bc8c0`):
  - `wepppy/nodir/errors.py`, `wepppy/nodir/paths.py`, `wepppy/nodir/fs.py`, `wepppy/nodir/symlinks.py`, `wepppy/nodir/parquet_sidecars.py`, `wepppy/nodir/__init__.py`.
  - Allowlisted boundary parsing + admin alias semantics, `resolve()` view semantics (`effective|dir|archive`), mixed/invalid/transitional error handling, archive-native list/stat/open (no extraction), sidecar precedence, and archive parquet no-fallback behavior.
  - Security hardening: symlink/path validation, zip-entry safety checks, size-limit guards, and sidecar symlink restrictions.
  - Validation: `wctl run-pytest tests/nodir` -> 46 passed, 0 failed.
- Phase 3 browse/files/download integration is complete (commit `6c7694508`):
  - NoDir archive-native browse/files/download wiring landed with allowlisted boundary semantics and admin alias support.
  - Mixed-state and invalid-archive semantics were enforced across surfaces with admin/non-admin deltas.
  - `.nodir` remains directory-like in listing/sort behavior; `aria2c.spec` keeps `.nodir` as file-only (no expansion).
  - Browse mixed-state warning block is rendered below pagination.
  - Validation:
    - `wctl run-pytest tests/microservices -k "browse or files or download or nodir"` -> 207 passed, 1 skipped, 192 deselected.
    - `wctl run-pytest tests --maxfail=1` -> 1444 passed, 27 skipped.

In progress / partially done:
- Migration crawler behavior (safety gates, audit logs, resumability, rollback) is not yet specified/implemented.
- Perf targets are not yet defined (browse p95 listing, archive build time, inode reduction, etc.).

Not started (core remaining scope):
- Materialization implementation (`materialize(file|subset)`) and integration into FS-boundary endpoints (dtale/gdalinfo/diff/exports).
- Thaw/freeze implementation (state file writes, locks, crash recovery, temp marker handling).
- Mutation workflows (RQ-engine/controller/mods/migrations) for archive-backed roots via thaw/modify/freeze.
- Bulk migrator / crawler for `/wc1/runs` (and legacy trees) with `WD/READONLY` gating and auditing.
- Default new-run behavior: prefer `.nodir` for allowlisted roots while keeping Dir form first-class for unmigrated runs.

## Phase Plan

### Phase 0: Contracts and Guardrails (DONE)
Deliverables:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

Exit criteria:
- Docs lint clean (`wctl doc-lint`).
- No conflicting sources of truth (contracts reference each other instead of duplicating).

### Phase 1: Parquet Sidecars (DONE)
Goal:
- Make query engine + migrations treat parquet under NoDir roots as WD-level sidecars while keeping logical ids stable.

Deliverables (landed):
- `wepppy/nodir/parquet_sidecars.py`
- Updates to query engine activation and dataset path resolution.
- Updates to parquet migrations for `landuse`, `soils`, `watershed`.
- Test coverage for sidecar mapping and required call sites.

Exit criteria:
- Targeted pytest passes for sidecar behaviors.

### Phase 2: NoDir Core Library v1 (DONE, 2026-02-16)
Goal:
- One shared implementation of dir-vs-archive discovery and archive-native read/list/stat for allowlisted `.nodir` roots.

Deliverables (landed):
- `wepppy/nodir/errors.py`: typed errors with stable `{status, code}`.
- `wepppy/nodir/paths.py`: normalization + boundary parsing (`<root>.nodir/...`, admin alias `<root>/nodir/...`).
- `wepppy/nodir/fs.py` (or equivalent): `resolve`, `listdir`, `stat`, `open_read` for:
  - Dir form (filesystem),
  - Archive form (zip central directory + streamed entry reads),
  - Mixed state and invalid archive handling per matrix.
- Archive validation helpers:
  - allowlist enforcement,
  - entry-name normalization and path traversal rejection,
  - reject symlinks/non-regular entries.
- Transitional sentinel handling:
  - if `WD/<root>.thaw.tmp/` or `WD/<root>.nodir.tmp` exists, treat root as transitioning (locked) for request-serving and materialization.

Validation evidence:
- Latest hardening commits: `cc8dc214e`, `d559bc8c0`.
- Unit suite: `tests/nodir/` covering paths, resolve, archive fs, archive validation, parquet precedence, and symlink security.
- Latest run: `wctl run-pytest tests/nodir` -> 46 passed, 0 failed.
- No materialization workflows and no thaw/freeze mutation workflows were introduced in this phase.

**Phase 2 Handoff Summary**

- Branch: `nodir-thaw-freeze-contract`
- Latest commits:
1. `cc8dc214e` `nodir: harden symlink/path validation and archive-native ops`
2. `d559bc8c0` `nodir: tighten sidecar symlink validation and archive path normalization`

**Implemented Scope (Phase 2)**
- Shared NoDir core library created under `wepppy/nodir/`:
1. `wepppy/nodir/errors.py`
2. `wepppy/nodir/paths.py`
3. `wepppy/nodir/fs.py`
4. `wepppy/nodir/parquet_sidecars.py`
5. `wepppy/nodir/symlinks.py`
6. `wepppy/nodir/__init__.py` (explicit public exports)

- Required behaviors implemented:
1. Allowlisted boundary parsing for `.nodir` roots and admin alias handling.
2. `resolve()` with `effective|dir|archive` view semantics.
3. Mixed state enforcement (`409 NODIR_MIXED_STATE`) in `effective`.
4. Invalid archive enforcement (`500 NODIR_INVALID_ARCHIVE`) for archive/effective paths.
5. Transitional sentinel enforcement (`503 NODIR_LOCKED`) for read paths.
6. Archive-native `listdir/stat/open_read` via zip central directory only (no extraction).
7. Parquet sidecar precedence for logical parquet paths.
8. Archive parquet no-fallback behavior (archive form treats missing sidecar as missing dataset).

**Security/Hardening Landed**
1. Drive-letter absolute-path bypass fixed in relpath normalization tests.
2. Unsafe zip entry names/types rejected (`/`, `..`, `\`, drive letters, malformed forms like `a//`, special file types, ambiguity conflicts).
3. Size-limit guard in archive `open_read()` with `NODIR_LIMIT_EXCEEDED`.
4. Symlink policy added for NoDir reads, including Omni/shared-root allowlist behavior.
5. `.nodir` symlink handling now validates allowed roots before target stat/use.
6. Parquet sidecar symlink handling now requires target regular file within allowed roots.
7. `resolve(view="dir")` now populates `archive_fp` when archive exists and is fingerprintable.

**Tests Added/Updated**
- New NoDir unit suite under `tests/nodir/`:
1. `test_paths.py`
2. `test_resolve.py`
3. `test_archive_fs.py`
4. `test_archive_validation.py`
5. `test_parquet_precedence_fs.py`
6. `test_parquet_sidecars.py`
7. `test_symlink_security.py`

- Latest validation:
1. `wctl run-pytest tests/nodir`
2. Result: **46 passed**, **0 failed**, 2 third-party deprecation warnings.

**Out of Scope (Not Implemented in Phase 2)**
1. Browse/files/download endpoint integration wiring (Phase 3).
2. Materialization APIs/workflow (Phase 4).
3. Thaw/freeze mutation workflows beyond read-path transitional lock detection (Phase 5).

### Phase 3: Browse/Files/Download Archive-Native Support (DONE, 2026-02-16)
Goal:
- Allow `/browse`, `/files`, `/download` to navigate into `.nodir` archives for allowlisted roots without extraction.

Deliverables (landed):
- Wired `wepppy/microservices/browse/listing.py`, `wepppy/microservices/browse/files_api.py`, and `wepppy/microservices/browse/_download.py` through the Phase 2 NoDir API.
- Mixed-state behavior:
  - non-admin hides both representations and returns `409; code=NODIR_MIXED_STATE` on direct navigation,
  - admin browse provides dual view for observability only.
- Invalid allowlisted archive handling:
  - archive-as-directory returns `500; code=NODIR_INVALID_ARCHIVE`.
- `.nodir` rendered as directory-like in listings/sort order.
- `aria2c.spec` continues to list `.nodir` as files only (no inner expansion).
- Browse mixed-state warning block rendered below pagination.

Validation evidence:
- Latest integration commit: `6c7694508`.
- Targeted microservice run: `wctl run-pytest tests/microservices -k "browse or files or download or nodir"` -> 207 passed, 1 skipped, 192 deselected.
- Full regression gate: `wctl run-pytest tests --maxfail=1` -> 1444 passed, 27 skipped.

**Phase 3 Handoff Summary**
- Completed browse/files/download NoDir integration with archive-native list/stat/read/download paths using shared NoDir core.
- Implemented allowlisted archive boundary support for `<root>.nodir/<inner>` and admin browse alias `<root>/nodir/<inner>`.
- Enforced mixed-state semantics across surfaces, including admin/non-admin deltas and raw `.nodir` download rules.
- Ensured invalid allowlisted archives return canonical `500 NODIR_INVALID_ARCHIVE` for archive-as-directory operations.
- Kept `.nodir` directory-like in listings/sort order and kept `aria2c.spec` as file-only for `.nodir` (no expansion).
- Added browse HTML mixed-state warning block below pagination.
- Added/updated route-level tests for archive/mixed/invalid/admin behaviors, including non-slashed and trailing-slash edge cases.

**Review Findings And Resolutions**
1. Non-slashed `.nodir` bypass in `/browse` and `/files` mixed/invalid paths: fixed by forcing allowlisted raw `.nodir` into archive-boundary parse semantics.
2. `/download/<root>.nodir/` treated as raw archive bytes: fixed by raw-candidate normalization (`lstrip`), so trailing slash no longer hits raw shortcut.
3. Archive entry download full-buffer memory risk: fixed by chunked streaming response and `readinto()` support in NoDir zip stream.
4. Test coverage gaps for mixed/admin/non-slashed paths: fixed with new route tests.
5. Admin `/files/` mixed-state observability ambiguity: resolved per your direction by codifying admin root-list visibility in contract/matrix and enforcing with test.
6. Contract inconsistency (`interface` vs `contract` docs): fixed by updating `docs/schemas/nodir_interface_spec.md`.
7. Missing browse mixed-state warning block: implemented in template/render path and covered by test.

**Validation**
- `wctl run-pytest tests/microservices -k "browse or files or download or nodir"`  
  - `207 passed, 1 skipped, 192 deselected`
- `wctl run-pytest tests --maxfail=1`  
  - `1444 passed, 27 skipped`

### Phase 4: Materialization v1 + FS-Boundary Endpoints (DONE)
Goal:
- Support endpoints that require real filesystem paths for archive entries (dtale, gdalinfo, diff, exports).

Deliverables:
- `wepppy/nodir/materialize.py` implementing:
  - cache layout under `WD/.nodir/cache/`,
  - per-entry distributed locks (`nodb-lock:<runid>:nodir-materialize/<root>/<entry_id>`),
  - sidecar extraction groups (SHP, TIF sidecars),
  - explicit limits (`413; NODIR_LIMIT_EXCEEDED`),
  - transitional locking (`503; NODIR_LOCKED`) when `state in {thawing, freezing}` or temp markers exist.
- Wire materialization into:
  - `wepppy/microservices/browse/dtale.py`
  - `wepppy/microservices/_gdalinfo.py`
  - `wepppy/weppcloud/routes/diff/diff.py`
  - export code paths that hand paths to external tooling.

Exit criteria:
- Tests for cache hit/miss, lock contention behavior, and limit enforcement (no partial files).
- Manual validation: materialize a raster and a shapefile from a `.nodir` and run dtale/gdalinfo successfully.

**Phase 4 Handoff Summary**

Commit pushed: `f917171b0` on `origin/nodir-thaw-freeze-contract`.

1. **Scope delivered**
1. In-scope completed: NoDir materialization core + FS-boundary wiring for `dtale`, `gdalinfo`, `diff`, and export paths that need real files.
2. Out-of-scope remained unchanged: browse/files/download extraction behavior, thaw/freeze mutation workflows, bulk crawler.

2. **Core materialization implementation**
1. New module: `wepppy/nodir/materialize.py:1`.
2. Cache layout + entry targeting: `WD/.nodir/cache/<root>/<archive_fp>/<entry_hash>` at `wepppy/nodir/materialize.py:706`.
3. Archive/entry fingerprints + cache validation metadata at `wepppy/nodir/materialize.py:141`, `wepppy/nodir/materialize.py:150`, `wepppy/nodir/materialize.py:199`.
4. Per-entry Redis lock acquire/release/renew at `wepppy/nodir/materialize.py:415`, `wepppy/nodir/materialize.py:446`, `wepppy/nodir/materialize.py:477`.
5. Renew is fail-closed if ownership is lost or atomic renew is unavailable at `wepppy/nodir/materialize.py:495`, `wepppy/nodir/materialize.py:498`.
6. Sidecar extraction groups for SHP/TIF with case-insensitive matching at `wepppy/nodir/materialize.py:532`, `wepppy/nodir/materialize.py:559`.
7. Limits enforcement (`max files`, `max bytes`, compression-ratio guard) at `wepppy/nodir/materialize.py:349`.
8. Atomic extraction (`tmp` + `os.replace`) and cleanup/no partial output at `wepppy/nodir/materialize.py:595`, `wepppy/nodir/materialize.py:637`, `wepppy/nodir/materialize.py:639`.

3. **FS-boundary integrations**
1. `dtale` archive-boundary preflight with `view="effective"` and archive materialization at `wepppy/microservices/browse/dtale.py:164`, `wepppy/microservices/browse/dtale.py:202`.
2. `gdalinfo` archive-boundary preflight with `view="effective"` and materialization at `wepppy/microservices/_gdalinfo.py:70`, `wepppy/microservices/_gdalinfo.py:100`.
3. `diff` route NoDir-aware resolution using effective view at `wepppy/weppcloud/routes/diff/diff.py:75`, `wepppy/weppcloud/routes/diff/diff.py:81`.
4. ERMiT mixed-state fail-fast guard at `wepppy/export/ermit_input.py:216`.
5. GeoPackage export real-file materialization for shapefiles at `wepppy/export/gpkg_export.py:125`, `wepppy/export/gpkg_export.py:249`.
6. Export API NoDir error propagation at `wepppy/microservices/rq_engine/export_routes.py:97`.
7. Public NoDir exports updated at `wepppy/nodir/__init__.py:10`.

4. **Canonical NoDir errors**
1. Enforced/propagated as required across materialization + boundary endpoints:
`409 NODIR_MIXED_STATE`, `500 NODIR_INVALID_ARCHIVE`, `503 NODIR_LOCKED`, `413 NODIR_LIMIT_EXCEEDED`.

5. **Test coverage added**
1. Materialization contract coverage in `tests/nodir/test_materialize.py:95` through `tests/nodir/test_materialize.py:493`.
2. Includes cache hit/miss/rebuild, contention→503, limits→413, invalid/unsafe→500, no partial outputs, SHP/TIF sidecars, renewal-loss and no-`eval` fail-closed behavior.
3. dtale/gdalinfo archive-backed integration + state propagation + 413 route propagation in `tests/microservices/test_files_routes.py:2228`.
4. Diff archive-backed integration + state propagation in `tests/microservices/test_diff_nodir.py:59`.
5. Export route NoDir propagation in `tests/microservices/test_rq_engine_export_routes.py:26`.

6. **Validation runs**
1. `wctl run-pytest tests/nodir -k "materialize or nodir"` → `62 passed`
2. `wctl run-pytest tests/microservices -k "dtale or gdalinfo or diff or nodir"` → `66 passed, 1 skipped`
3. `wctl run-pytest tests --maxfail=1` → `1483 passed, 27 skipped`

No JS files were changed, so `wctl run-npm test` was not required for this phase.

### Phase 5: Thaw/Freeze Implementation + Maintenance Plumbing (TODO)
Goal:
- Implement the crash-safe thaw/freeze state machine and integrate with mutation workflows.

Deliverables:
- `wepppy/nodir/state.py` + `wepppy/nodir/thaw_freeze.py` (or equivalent):
  - atomic state file writes (`WD/.nodir/<root>.json`) including `op_id/host/pid/lock_owner`,
  - maintenance lock acquisition (`nodb-lock:<runid>:nodir/<root>`),
  - `thaw(root)`, `freeze(root)`, crash recovery behavior,
  - strict “mixed state is error” policy (no supported keep-directory mode).
- Maintenance-only cleanup of temp markers (`*.thaw.tmp/`, `*.nodir.tmp`) under lock.

Exit criteria:
- Tests that simulate crash points (temp dir/archive left behind) and verify safe recovery.
- Clear operator logs for op id + lock owner, without needing Redis spelunking.

### Phase 6: Root-by-Root Mutation Adoption (TODO; Multi-Phase Per Root)
Goal:
- Ensure controller/RQ/migration/mod mutation paths work for both Dir form and Archive form (via thaw/modify/freeze), without persisting representation in `.nodb`.

Approach:
- Implement a single “mutate NoDir root” helper (maintenance lock + thaw if needed + run mutation + freeze).
- Convert producers first, then handle “serialized-path hazards” (objects storing `*_dir` paths) so runtime does not assume real directories.

Subphases (suggested order):
1. `watershed`: highest inode pressure; many external-tool touchpoints (Peridot, exports, slope files).
2. `soils`: large file fanout; many mods; WinWEPP export copytree.
3. `landuse`: treatments/omni direct `.man` writes; user-defined flows.
4. `climate`: CLI upload/validation and reporting artifacts.

Exit criteria:
- Behavior matrix conformance for each root’s producers and FS-boundary consumers.
- Targeted regression tests for each root’s “archive form” mutation and subsequent browse/download behavior.

### Phase 7: Bulk Migration Crawler + Default-to-NoDir Rollout (TODO)
Goal:
- Archive high-fanout roots across existing runs safely, and make new runs prefer `.nodir` by default.

Deliverables:
- Crawler/migrator CLI:
  - requires `WD/READONLY`,
  - lock + fail-fast on active roots,
  - resumable pass with audit logs (jsonl),
  - `--dry-run`, `--limit`, `--runid`, `--root` filters.
- “New runs default nodir” wiring:
  - build roots normally, then freeze once ready (or build directly into `.nodir` with tmp dir),
  - avoid creating mixed state.

Exit criteria:
- Documented before/after inode counts and browse p95 improvements on representative runs.
- Operational runbook: rollback, forensics (admin raw `.nodir` downloads), and audit log interpretation.

## Perf Targets (To Define Early)
- Browse listing p95 on a large `watershed.nodir` (both HTML and `/files` JSON).
- Download stream throughput for a large entry (no extract).
- Materialize(file) wall time for typical raster/shapefile.
- Archive build time for each root at representative sizes.
- Inode reduction per run (before/after) and NAS stat pressure notes.
