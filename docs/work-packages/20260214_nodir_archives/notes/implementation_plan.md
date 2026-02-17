# NoDir Implementation Plan (Multi-Phase)

**Work package:** `docs/work-packages/20260214_nodir_archives/package.md`  
**Last updated:** 2026-02-17  
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
- Phase 4 materialization implementation is complete (commit `f917171b0`):
  - `wepppy/nodir/materialize.py` landed with cache/lock/limit semantics and FS-boundary integrations.
  - Validation:
    - `wctl run-pytest tests/nodir -k "materialize or nodir"` -> 62 passed.
    - `wctl run-pytest tests --maxfail=1` -> 1483 passed, 27 skipped.
- Phase 5 thaw/freeze state machine and maintenance plumbing is complete (commit `046d57a42` + follow-up hardening):
  - `wepppy/nodir/state.py` and `wepppy/nodir/thaw_freeze.py` landed with crash-safe transitions, lock enforcement, and maintenance recovery.
  - Transitional-state behavior was unified in `resolve()` and `materialize_file()`.
  - Validation:
    - `wctl run-pytest tests/nodir -k "state or thaw or freeze or materialize or nodir"` -> 85 passed.
    - `wctl run-pytest tests --maxfail=1` -> 1512 passed, 27 skipped.

In progress / partially done:
- Migration crawler behavior (safety gates, audit logs, resumability, rollback) is not yet specified/implemented.
- Perf targets are not yet defined (browse p95 listing, archive build time, inode reduction, etc.).

Not started (core remaining scope):
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

### Phase 5: Thaw/Freeze Implementation + Maintenance Plumbing (DONE, 2026-02-16)
Goal:
- Implement the crash-safe thaw/freeze state machine and maintenance lock plumbing for allowlisted NoDir roots.

Deliverables (landed):
- New NoDir maintenance-state module: `wepppy/nodir/state.py`.
  - Per-root state file at `WD/.nodir/<root>.json` with required contract fields.
  - Atomic state writes via temp + `fsync` + `os.replace`.
  - Strict payload validation (UUID4 op ids, integer typing, `lock_owner == host:pid`).
  - Transitional lock detection from both state values and temp sentinels.
- New thaw/freeze maintenance module: `wepppy/nodir/thaw_freeze.py`.
  - Maintenance lock key `nodb-lock:<runid>:nodir/<root>` with fail-fast acquisition.
  - `thaw(root)` implementing `thawing -> thawed` with pre-validation and zip-slip/type defenses.
  - `freeze(root)` implementing `freezing -> archived` with temp-archive build/verify/replace and required directory removal.
  - Maintenance-only recovery for stale `.thaw.tmp` and `.nodir.tmp` artifacts.
  - Crash-recovery finalize path for `state="freezing"` when directory is missing but archive is valid.
- Transitional-state integration updates:
  - `wepppy/nodir/fs.py` now uses shared transitional lock checks.
  - `wepppy/nodir/materialize.py` now uses shared transitional lock checks.
- Public exports updated in `wepppy/nodir/__init__.py`.

Validation evidence:
- Targeted NoDir suite:
  - `wctl run-pytest tests/nodir -k "state or thaw or freeze or materialize or nodir"` -> `85 passed`.
- Full regression gate:
  - `wctl run-pytest tests --maxfail=1` -> `1512 passed, 27 skipped`.

**Phase 5 Handoff Summary**

- Branch: `nodir-thaw-freeze-contract`
- Primary commit: `046d57a42` (`nodir: implement crash-safe thaw/freeze maintenance state machine`)
- Follow-up hardening included in the final working tree before handoff:
1. Case-insensitive parquet sidecar migration during freeze.
2. Thaw pre-validation of archive structure before extraction.
3. Freeze crash-recovery finalization when state is `freezing` and directory is missing.
4. Strict write-path validation for integer-typed fields (including explicit `bool` rejection) and UUID4 `op_id` checks.

**Implemented Scope (Phase 5)**
1. Canonical NoDir maintenance state model (`schema_version=1`) with required fields and strict validation.
2. Crash-safe thaw sequence with explicit `thawing` and `thawed` state transitions under maintenance lock.
3. Crash-safe freeze sequence with explicit `freezing` and `archived` state transitions under maintenance lock.
4. Maintenance-only cleanup behavior for stale transitional artifacts.
5. Unified `503 NODIR_LOCKED` behavior for transitional states/sentinels in `resolve()` and `materialize_file()`.

**Review Findings And Resolutions (Phase 5)**
1. Uppercase/mixed-case parquet sidecar risk during freeze: fixed by case-insensitive parquet detection and sidecar remap.
2. Thaw validation gap for duplicate/conflicting archive entries: fixed by pre-extraction archive verification.
3. Freeze crash window leaving roots stuck in `freezing`: fixed by maintenance finalize path when archive is valid.
4. State validation strictness gaps (UUID and integer typing): fixed with strict validation and added regression coverage.

**Tests Added/Updated (Phase 5)**
1. New state schema/atomicity coverage in `tests/nodir/test_state.py`.
2. New thaw/freeze happy-path and crash-recovery coverage in `tests/nodir/test_thaw_freeze.py`.
3. Transitional lock behavior coverage extended in `tests/nodir/test_materialize.py` and `tests/nodir/test_resolve.py`.
4. Additional edge-case regressions:
  - duplicate archive entry rejection,
  - file/directory prefix conflict rejection,
  - uppercase parquet sidecar preservation,
  - write-path bool-as-int rejection for state integers.

Out of scope for Phase 5 handoff:
1. Broad root-by-root mutation adoption across all producers/consumers (Phase 6) - complete as of 2026-02-17.
2. Bulk migration crawler and default-to-NoDir rollout (Phase 7) - still pending.

### Phase 6: Root-by-Root Mutation Adoption (DONE, 2026-02-17)
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

### Phase 6a: Watershed Touchpoint Review + Multi-Stage Adoption Plan (DONE, 2026-02-17)
Goal:
- Produce a watershed-specific, multi-stage implementation plan for Phase 6 execution based on real touchpoints, mutation risk, and validation depth.

Scope (planning only):
- Review watershed touchpoints end-to-end (controllers, RQ routes/jobs, exports, query engine, mods, migrations, and FS-boundary endpoints).
- Confirm exact mutation/read boundaries for `watershed` under Dir form vs Archive form.
- Define an ordered execution plan with explicit cut lines, risk gates, and test gates.

Planned stages (deliverable of this phase):
1. Stage A: Touchpoint inventory reconciliation
  - Reconcile `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md` against current code.
  - Classify each watershed call site as producer, consumer, FS-boundary, or serialized-path hazard.
  - Mark each as archive-ready, thaw-required, or blocked.
2. Stage B: Mutation-surface design
  - Define the canonical watershed mutation entry points that must run under thaw/modify/freeze.
  - Specify lock/state boundaries for each mutation class.
  - Specify no-op/pass-through behavior for pure read paths.
3. Stage C: Execution waves
  - Wave 1: low-risk internal migration/migration-tooling call sites.
  - Wave 2: RQ-engine watershed build flows and peridot-linked producers.
  - Wave 3: exports/mod integrations with watershed writes.
  - Wave 4: cleanup of legacy serialized-path assumptions and final hardening.
4. Stage D: Validation and rollout gates
  - Define required regression suites per wave.
  - Define mixed/invalid/transitional state probes.
  - Define rollback and forensic checks for each wave.

Stage A findings summary (reconciled against current code, 2026-02-16):
- Touchpoints inventoried: 32 (`docs/work-packages/20260214_nodir_archives/artifacts/watershed_touchpoints_stage_a.md`)
- Counts by class:
  - `producer`: 12
  - `consumer`: 26
  - `FS-boundary`: 13
  - `serialized-path hazard`: 1
- Counts by readiness:
  - `archive-ready`: 12
  - `thaw-required`: 16
  - `blocked`: 4
- Top blockers:
  - `wepppy/nodb/core/watershed.py`: `Watershed.__init__` eagerly creates `WD/watershed`, causing mixed-state conflicts when `watershed.nodir` is canonical.
  - `wepppy/nodb/core/watershed.py`: `_structure` path-string persistence (`structure.json`) is a serialized-path hazard tied to directory form.
  - `wepppy/topo/peridot/peridot_runner.py`: `migrate_watershed_outputs()` calls `Watershed.getInstance()` and inherits the constructor mixed-state blocker.
  - `wepppy/export/ermit_input.py`: still depends on `Watershed.getInstance()`, `_subs_summary`, and direct `wat_dir` slope iteration.

Stage B mutation-surface summary (design baseline, 2026-02-16):
- Canonical mutation entry points (`docs/work-packages/20260214_nodir_archives/artifacts/watershed_mutation_surface_stage_b.md`):
  - Root-mutating boundaries: `abstract_watershed_rq`, `build_subcatchments_and_abstract_watershed_rq` (abstraction phase), `Watershed.abstract_watershed`, `_peridot_post_abstract_watershed`, `_topaz_abstract_watershed`, `post_abstract_watershed`, and watershed migration utilities when they touch `WD/watershed/*`.
  - Watershed queue mutations (`build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq`) are classified as archive-form root mutations (`materialize(root)+freeze`) to match the behavior matrix watershed RQ row.
- Lock/state boundary rules:
  - Any root mutation touching `WD/watershed/*`, `WD/watershed.nodir*`, or `WD/.nodir/watershed.json` must run under `nodb-lock:<runid>:nodir/watershed`.
  - Lock order: NoDir maintenance lock outermost, NoDb lock(s) inside callback.
  - Archive-form mutation transition: `archived -> thawing -> thawed -> freezing -> archived`; Dir form remains no state transition.
  - Callback failure after thaw leaves `state=thawed` and `dirty=true` for deterministic retry/recovery (no implicit auto-freeze).
- Read-path pass-through rules:
  - Pure read surfaces (`/browse`, `/files`, `/download`) and sidecar parquet consumers remain thaw-free pass-through on NoDir APIs.
  - FS-boundary read surfaces (`dtale`, `gdalinfo`, selected exports) use file-level materialization only; no root thaw/freeze from request-serving code.
  - Transitional states (`thawing`/`freezing` or temp sentinels) fail fast with `503 NODIR_LOCKED`.
- Unresolved decisions:
  - Remove constructor-time `wat_dir` creation side effect in `Watershed.__init__` for archive-safe controller reads.
  - Eliminate `_structure` path-string serialized-path hazard (`structure.json`) before freeze-era invariants are finalized.
  - Choose final strategy for high-fanout watershed slope/network consumers (`wepp.prep_watershed`, `ERMiT`, `RHEM`, `SWAT`, salvage flowpaths): per-file materialization vs bounded read-session helper.

Stage C execution wave summary (rollout baseline, 2026-02-16):
- Wave 1 (foundation + migration tooling):
  - Objective: remove watershed archive-form blockers in low-risk internal paths before producer cutover.
  - Boundary: `wepppy/nodb/core/watershed.py` bootstrap/root-form guard, `wepppy/topo/peridot/peridot_runner.py` migration path, `wepppy/tools/migrations/watershed.py`, `wepppy/query_engine/activate.py`, and `wepppy/nodb/duckdb_agents.py`.
  - Excludes: RQ mutation flows, exports/mod integrations, and browse/files/download hardening.
- Wave 2 (RQ build flows + peridot producers):
  - Objective: apply canonical thaw/modify/freeze orchestration to watershed mutation owners.
  - Boundary: `wepppy/rq/project_rq.py`, `wepppy/microservices/rq_engine/watershed_routes.py`, `wepppy/nodb/core/watershed.py` abstraction methods, `wepppy/topo/peridot/peridot_runner.py` post-abstraction, and `wepppy/topo/watershed_abstraction/`.
  - Excludes: export/mod consumer integration and serialized-path cleanup.
- Wave 3 (exports + mods + WEPP consumer coupling):
  - Objective: remove archive-form read breakpoints in watershed-dependent consumers.
  - Boundary: `wepppy/rq/wepp_rq.py`, `wepppy/nodb/core/wepp.py`, watershed exports in `wepppy/export/`, and watershed mods in `wepppy/nodb/mods/*` (`swat`, `rhem`, `path_ce`, `omni`, `salvage_logging`).
  - Excludes: browse/files/download consistency hardening and final serialized-path remediation.
- Wave 4 (serialized-path cleanup + consistency hardening):
  - Objective: clear `_structure` serialized-path hazard and harden watershed NoDir semantics across public read surfaces.
  - Boundary: `wepppy/nodb/core/watershed.py` (`_structure`/`structure.json` handling) plus watershed checks for `browse`, `files`, `download`, `dtale`, and `gdalinfo` surfaces.
  - Excludes: new feature work outside watershed NoDir adoption.
- Dependencies and ordering rationale:
  - Wave 1 resolves blockers required by all later waves.
  - Wave 2 depends on Wave 1 to avoid mixed-state bootstrap failures during mutation cutover.
  - Wave 3 depends on Wave 2 producer stability before consumer integration.
  - Wave 4 depends on Waves 1-3 and is restricted to cleanup/hardening so final behavior-matrix conformance is measurable.
- Wave ownership map: `docs/work-packages/20260214_nodir_archives/artifacts/watershed_execution_waves_stage_c.md`.

Stage D validation/rollout summary (gate baseline, 2026-02-17):
- Per-wave test gates (`docs/work-packages/20260214_nodir_archives/artifacts/watershed_validation_rollout_stage_d.md`):
  - Wave 1: NoDir state/thaw/resolve + watershed migration/query-engine foundation gates.
  - Wave 2: watershed producer mutation gates (`rq_engine` watershed routes + dedicated legacy abstraction internals gate + thaw/freeze lock/state regressions).
  - Wave 3: watershed consumer gates (materialization, exports, mods, WEPP-prep coupling).
  - Wave 4: browse/files/download hardening gates + transitional lock regression checks.
  - All waves: docs contract lint gate when Stage artifacts or schemas are touched.
- Rollout gates:
  - Wave promotion is blocked unless the wave’s pre-merge and post-merge gate rows all pass with `0 failed` and contract status/code expectations.
  - Post-merge canary gates use standardized `tests/api/create-run` bootstrap + cleanup and must confirm no browse/files/download extraction side effects for watershed archive paths.
- Rollback triggers:
  - Any mixed-state regression in effective public paths (`409` contract drift), invalid-archive contract drift (`500`), transitional-lock drift (`503`), or producer/consumer parity regression on archive form.
  - Immediate action: stop forward rollout, revert active-wave merge commits, rerun that wave’s gate matrix before redeploy.
- Forensic requirements:
  - Capture `WD/.nodir/watershed.json`, temp sentinels, archive fingerprint (`stat WD/watershed.nodir`), gate command outputs, and relevant RQ/log artifacts before cleanup.
  - Use the Stage D forensics checklist command bundle for run-scoped evidence collection.

Phase 6 all-stages review summary (2026-02-17):
- Findings by severity:
  - High: Stage B watershed RQ subgroup thaw classification now explicitly matches the behavior matrix (`materialize(root)+freeze`).
  - High: Wave 4 post-merge no-extraction canary gate is now executable using standardized canary bootstrap/cleanup flow.
  - Medium: Wave 4 cross-surface rollback ownership is now explicit (`Browse/NoDir owner`).
  - Medium: Wave 2 gate set now includes a dedicated legacy abstraction internals command.
  - Low: Stage D forensic command precedence bug remains corrected.
- Cross-stage coverage status:
  - Stage A touchpoints mapped to Stage C waves: `32/32`.
  - Stage A touchpoints mapped to Stage D gate paths via wave ownership: `32/32`.
  - Coverage quality: `27 pass`, `5 partial` (partials are limited to known Stage A blocked touchpoints scheduled in Waves 1/3/4).
  - Full matrix and gate audit: `docs/work-packages/20260214_nodir_archives/artifacts/watershed_phase6_all_stages_review.md`.
- Unresolved blockers:
  - None for Phase 6a planning package readiness.
- Readiness verdict: `ready`.
  - Phase 6a planning artifacts are execution-ready for watershed implementation waves.

Required outputs:
- Insert/refresh this Phase 6a section as the watershed planning source of truth.
- Add a dedicated watershed execution checklist doc under `docs/work-packages/20260214_nodir_archives/artifacts/`.
- Provide a wave-by-wave test matrix (what runs before merge vs post-merge).

Exit criteria:
- Every watershed touchpoint has an owner wave and expected behavior (native, thaw-required, or blocked).
- No unresolved ambiguity remains for watershed mutation ownership.
- The resulting plan is implementation-ready for Phase 6 watershed execution.

Phase 6 completion summary (2026-02-17):
- Shared orchestration landed under `wepppy/nodir/mutations.py` and was wired into root mutation owners in `wepppy/rq/project_rq.py` (`watershed`, `soils`, `landuse`, `climate`, and `upload_cli`).
- Route preflight + canonical NoDir error propagation was applied to root mutation routes:
  - `wepppy/microservices/rq_engine/watershed_routes.py`
  - `wepppy/microservices/rq_engine/soils_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/climate_routes.py`
  - `wepppy/microservices/rq_engine/upload_climate_routes.py`
- Root bootstrap blockers were removed by deleting eager constructor-time root directory creation in:
  - `wepppy/nodb/core/watershed.py`
  - `wepppy/nodb/core/soils.py`
  - `wepppy/nodb/core/landuse.py`
  - `wepppy/nodb/core/climate.py`
- Watershed serialized-path hazard cleanup completed (`_structure` no longer persists `structure.json` path strings in-memory).
- Root-specific Stage A-D artifacts are complete for all roots:
  - Watershed: `watershed_*_stage_*.md`
  - Soils: `soils_*_stage_*.md`
  - Landuse: `landuse_*_stage_*.md`
  - Climate: `climate_*_stage_*.md`
- Final cross-root review artifact: `docs/work-packages/20260214_nodir_archives/artifacts/phase6_all_roots_review.md`.

Phase 6 root status:
- `watershed`: complete
- `soils`: complete
- `landuse`: complete
- `climate`: complete

Phase 6 exit criteria status:
- Behavior-matrix mutation rows (`build-landuse`, `build-soils`, `build-climate`, watershed RQ group, `upload-cli`) are implemented with archive-form `materialize(root)+freeze` semantics through shared root mutation orchestration.
- Targeted root gate suites passed (see Stage D artifacts and all-roots review).
- Full-suite and final docs lint evidence is complete (`wctl run-pytest tests --maxfail=1` -> `1531 passed, 27 skipped`; `wctl doc-lint --path docs/work-packages/20260214_nodir_archives` -> `30 files validated, 0 errors, 0 warnings`).

### Phase 7: Bulk Migration Crawler + Default-to-NoDir Rollout (DONE, 2026-02-17)
Goal:
- Archive high-fanout roots across existing runs safely, and make new runs prefer `.nodir` by default.

Deliverables (landed):
- Bulk migration crawler CLI: `wepppy/tools/migrations/nodir_bulk.py`
  - enforces `WD/READONLY` for non-dry-run mutation,
  - fail-fast on active run locks (`lock_statuses(runid)`),
  - fail-fast on per-root maintenance lock contention (`NODIR_LOCKED`),
  - resumable JSONL audit logs (default resume; `--no-resume` override),
  - required filters: `--dry-run`, `--limit`, `--runid`, `--root`.
- “New runs default nodir” wiring:
  - new-run creation paths seed per-run marker `WD/.nodir/default_archive_roots.json` in:
    - `wepppy/microservices/rq_engine/project_routes.py`
    - `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
    - `wepppy/weppcloud/routes/test_bp.py`
  - shared mutation orchestration (`wepppy/nodir/mutations.py`) now auto-freezes configured dir-form roots post-callback, preserving canonical NoDir error behavior and avoiding persistent mixed-state output.
- Regression coverage added:
  - `tests/tools/test_migrations_nodir_bulk.py` (dry-run/filters, resume/no-resume, readonly gate, active-run lock fail-fast, root-lock fail-fast, canonical error propagation)
  - `tests/nodir/test_mutations.py` (default-marker/no-marker/malformed-marker flows)
  - `tests/microservices/test_rq_engine_project_routes.py` (marker creation on run create)
  - `tests/microservices/test_rq_engine_upload_huc_fire_routes.py` (marker creation on HUC fire upload create path)
  - `tests/weppcloud/routes/test_test_bp.py` (test-support create-run marker seeding)

Exit criteria status:
- Documented before/after perf + inode evidence: complete.
  - `docs/work-packages/20260214_nodir_archives/artifacts/phase7_perf_targets_and_results.md`
- Operational runbook (rollback, forensics, admin raw `.nodir` download, audit interpretation): complete.
  - `docs/work-packages/20260214_nodir_archives/artifacts/phase7_operational_runbook.md`
- Final rollout review artifact: complete.
  - `docs/work-packages/20260214_nodir_archives/artifacts/phase7_bulk_migration_rollout_review.md`

Validation evidence:
- `wctl run-pytest tests/nodir` -> `93 passed`
- `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_browse_security.py tests/microservices/test_files_routes.py tests/microservices/test_download.py tests/microservices/test_diff_nodir.py` -> `142 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_migration_routes.py tests/tools/test_migrations_runner.py tests/tools/test_migrations_parquet_backfill.py` -> `13 passed`
- New/modified Phase 7 tests:
  - `wctl run-pytest tests/nodir/test_mutations.py tests/tools/test_migrations_nodir_bulk.py tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/weppcloud/routes/test_test_bp.py` -> `22 passed`
- Full regression gate:
  - `wctl run-pytest tests --maxfail=1` -> `1540 passed, 27 skipped`

### Phase 7 Handoff Summary
- Rollout unit: root-scoped migration over allowlisted roots (`watershed`, `soils`, `landuse`, `climate`) using `wepppy/tools/migrations/nodir_bulk.py`.
- Safety gates in force for non-dry-run operations:
  - run must have `WD/READONLY`,
  - run must have no active NoDb locks,
  - root maintenance lock must be acquirable (`NODIR_LOCKED` fail-fast otherwise).
- New-run default NoDir is enabled by default and can be disabled immediately with `WEPP_NODIR_DEFAULT_NEW_RUNS=0` plus service restart.
- Crawler resume behavior is on by default and keyed by JSONL completion statuses (`archived`, `already_archive`, `missing_root`); use `--no-resume` to force replay.
- For incident handling and rollback workflows, use:
  - `docs/work-packages/20260214_nodir_archives/artifacts/phase7_operational_runbook.md`
- For release-readiness and test/perf closure audit, use:
  - `docs/work-packages/20260214_nodir_archives/artifacts/phase7_bulk_migration_rollout_review.md`

### Phase 7 Performance Metrics

| Metric | Target | Before | After / Result | Status |
|---|---:|---:|---:|---|
| Browse HTML p95 | <= 150 ms | 183.27 ms | 97.06 ms | pass |
| `/files` JSON p95 | <= 80 ms | 211.19 ms | 54.03 ms | pass |
| Download throughput (64 MiB stream) | >= 100 MiB/s | 139.19 MiB/s | 137.73 MiB/s | pass |
| `materialize(file)` cache miss | <= 300 ms | n/a | 191.78 ms | pass |
| `materialize(file)` cache hit | <= 10 ms | n/a | 2.31 ms | pass |
| Archive build overhead (`nodir_bulk` vs direct `freeze`) | <= +15% | baseline | no positive overhead observed (worst root delta: -1.69%) | pass |
| Inode reduction per large run | >= 95% | 10,313 entries | 11 entries (99.89% reduction) | pass |

Method notes and detailed per-root timings are documented in:
- `docs/work-packages/20260214_nodir_archives/artifacts/phase7_perf_targets_and_results.md`
