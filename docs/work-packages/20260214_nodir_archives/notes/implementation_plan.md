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

### Phase 4: Materialization v1 + FS-Boundary Endpoints (READY)
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
