# Watershed Mutation Surface Stage B (Phase 6a)

Scope: define watershed mutation ownership, lock/state boundaries, and read-path behavior for NoDir adoption. This is design-only (no runtime changes).

## Canonical Mutation Entry Points

| Entry Point | File | Mutation Type | Requires Thaw | Lock Scope | State Transition | Failure Mode | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `abstract_watershed_rq(runid)` | `wepppy/rq/project_rq.py` | Root producer (`watershed` files + summaries + structure metadata) | Yes when root is archive form | `nodb-lock:<runid>:nodir/watershed` around mutation callback; existing NoDb locks remain internal | Archive form: `archived -> thawing -> thawed -> freezing -> archived`; Dir form: none | `409 NODIR_MIXED_STATE`, `500 NODIR_INVALID_ARCHIVE`, `503 NODIR_LOCKED`; callback exceptions abort mutation | Primary canonical watershed-root mutation boundary. |
| `build_subcatchments_and_abstract_watershed_rq(runid, updates)` | `wepppy/rq/project_rq.py` | Compound orchestration (`build_subcatchments` then `abstract_watershed`) | Conditional (thaw required for abstraction phase) | NoDb lock for options; NoDir maintenance lock for abstraction callback | NoDir transitions only for abstraction phase | Same canonical NoDir errors as above; dependency-job failures propagate | Keep enqueue choreography; attach NoDir orchestration at the abstraction step. |
| `test_run_rq(runid)` | `wepppy/rq/project_rq.py` | Full prep pipeline including watershed abstraction | Conditional (thaw required when abstraction path executes against archive form) | NoDir lock only around root-mutating watershed segment(s) | Same as `abstract_watershed_rq` for root-mutating segment | Same canonical NoDir errors where root mutation is invoked | Direct/smoke execution path must follow the same mutation contract as queued flows. |
| `Watershed.abstract_watershed()` | `wepppy/nodb/core/watershed.py` | Controller-level watershed-root producer | Yes when root is archive form | Caller owns NoDir maintenance lock; method-internal NoDb lock usage is unchanged | Inherited from caller wrapper | Same canonical NoDir errors at wrapper boundary; method exceptions propagate | All direct calls should be considered unsafe unless wrapped by NoDir mutation orchestration. |
| `Watershed._peridot_post_abstract_watershed()` | `wepppy/nodb/core/watershed.py` | Post-abstraction root writes (parquet sidecars, `structure.json`, summaries) | Yes when consuming archive-backed `watershed` internals | Existing `with self.locked()` (NoDb lock) inside NoDir lock window | Inherited from caller wrapper | Callback exception aborts and leaves thawed dirty state | Contains `_structure` serialized-path hazard write (`structure.json` path persistence). |
| `post_abstract_watershed(wd)` | `wepppy/topo/peridot/peridot_runner.py` | Peridot CSV-to-parquet rewrite + source CSV deletion | Yes when CSV sources are only present inside `watershed.nodir` | Caller-owned NoDir lock and thaw/freeze sequence | Inherited from caller wrapper | Same canonical NoDir errors; file-level conversion failures propagate | Internal mutation helper; should not self-manage lock/state transitions. |
| `Watershed._topaz_abstract_watershed()` (legacy) | `wepppy/nodb/core/watershed.py` | Legacy abstraction writes multiple slope/network artifacts under `WD/watershed` | Yes when root is archive form | NoDir maintenance lock outside existing NoDb lock block | Inherited from caller wrapper | Same canonical NoDir errors + legacy abstraction runtime failures | Legacy path still mutates root heavily; keep under same orchestration boundary. |
| `Watershed._write_structure_json(structure)` | `wepppy/nodb/core/watershed.py` | Internal metadata write (`WD/watershed/structure.json`) | Yes when root is archive form | Called inside NoDb lock; must execute within NoDir lock if archive-backed | Inherited from caller wrapper | Filesystem write failures propagate; mixed/invalid handled by caller preflight | Serialized-path hazard touchpoint; caller contract must treat as root mutation. |
| `migrate_watershed_outputs(wd, ...)` | `wepppy/topo/peridot/peridot_runner.py` | Migration rewrite of watershed sidecars/legacy files | Conditional (no thaw for sidecar-only rewrite; thaw for legacy in-root files) | NoDir lock required whenever reading/writing `WD/watershed/*` | Conditional transition (only when thaw path is taken) | Current blocker: `Watershed.getInstance()` can trigger mixed-state via eager `wat_dir` creation | Phase 6 implementation should decouple migration from controller init before archive-form use. |
| `migrate_watersheds(wd, ...)` | `wepppy/tools/migrations/watershed.py` | Watershed migration utility (sidecars + structure externalization) | Conditional (same sidecar-only vs in-root split) | NoDir lock required for in-root legacy inputs; sidecar-only flow can run without thaw | Conditional transition | Legacy file absence/read failures; canonical NoDir errors if wrapper detects mixed/invalid/locked | Already avoids `Watershed.getInstance()`; keep this utility as migration-safe boundary. |
| `build_channels_rq(runid, ...)` | `wepppy/rq/project_rq.py` | Pre-abstraction delineation mutation | Yes in archive form (`materialize(root)+freeze` per behavior matrix watershed RQ row) | `nodb-lock:<runid>:nodir/watershed` around root mutation callback; existing NoDb locks remain internal | Archive form: `archived -> thawing -> thawed -> freezing -> archived`; Dir form: none | Canonical NoDir errors (`409`/`500`/`503`) at orchestration boundary | Behavior-matrix aligned baseline for Wave 2. Any future no-thaw carve-out requires behavior-matrix + Stage D gate updates in the same change. |
| `set_outlet_rq(runid, ...)` | `wepppy/rq/project_rq.py` | Outlet/state mutation | Yes in archive form (`materialize(root)+freeze` per behavior matrix watershed RQ row) | `nodb-lock:<runid>:nodir/watershed` around root mutation callback; existing NoDb locks remain internal | Archive form: `archived -> thawing -> thawed -> freezing -> archived`; Dir form: none | Canonical NoDir errors (`409`/`500`/`503`) at orchestration boundary | Same contract as `build_channels_rq`; keep classification explicit and contract-true. |
| `build_subcatchments_rq(runid, ...)` | `wepppy/rq/project_rq.py` | Subcatchment delineation + options mutation | Yes in archive form (`materialize(root)+freeze` per behavior matrix watershed RQ row) | `nodb-lock:<runid>:nodir/watershed` around root mutation callback; existing NoDb locks remain internal | Archive form: `archived -> thawing -> thawed -> freezing -> archived`; Dir form: none | Canonical NoDir errors (`409`/`500`/`503`) at orchestration boundary | Same contract as `build_channels_rq`/`set_outlet_rq`; no implicit carve-out. |

## Read-Path Behavior (Pass-Through vs FS Boundary)

| Read Path | File | Expected Behavior | NoDir API Surface | Notes |
| --- | --- | --- | --- | --- |
| Browse HTML (`/browse/...`) | `wepppy/microservices/browse/browse.py` | Pure pass-through/native read. Never thaw/freeze. | `resolve` + `listdir` + `open_read` | Mixed state returns `409`; invalid archive returns `500`; archive entries stream natively. |
| Files JSON (`/files/...`) | `wepppy/microservices/browse/files_api.py` | Pure pass-through/native metadata/listing. Never thaw/freeze. | `resolve` + `listdir` + `stat` | Preserve mixed-state/role semantics from behavior matrix. |
| Download API (`/download/...`) | `wepppy/microservices/browse/_download.py` | Pure pass-through/native streaming. Never thaw/freeze. | `resolve` + `open_read` | Raw `<root>.nodir` admin forensic path remains contract-defined. |
| Query-engine catalog + query parquet resolution | `wepppy/query_engine/activate.py`, `wepppy/nodb/duckdb_agents.py`, `wepppy/export/prep_details.py`, `wepppy/nodb/mods/path_ce/data_loader.py` | Pass-through read via logical sidecar parquet paths; no thaw/freeze. | `pick_existing_parquet_path` (+ catalog canonicalization) | Sidecar-first behavior is already archive-compatible for watershed parquet datasets. |
| GeoPackage export vector sources | `wepppy/export/gpkg_export.py` | FS-boundary read: Dir form pass-through, archive form materialize file/path only. | `materialize_path_if_archive` + `pick_existing_parquet_path` | Keep root-level thaw disabled; materialize only required vector files. |
| D-Tale dataset open | `wepppy/microservices/browse/dtale.py` | FS-boundary read: archive entries materialize per file. | `resolve` + `materialize_file` | Transition states must fail fast with `503 NODIR_LOCKED`. |
| GDAL info endpoint | `wepppy/microservices/_gdalinfo.py` | FS-boundary read: archive entries materialize per file. | `resolve` + `materialize_file` | Same lock/error semantics as D-Tale. |
| WEPP watershed prep (`wepp.prep_watershed`) | `wepppy/nodb/core/wepp.py` | Read-only from watershed perspective, but requires real slope/network files. | Current: direct `wat_dir` paths (needs FS-boundary wrapper in Phase 6) | Keep as read-path class; do not route through thaw/freeze mutation helper unless file-level materialization is insufficient. |
| ERMiT watershed export reads | `wepppy/export/ermit_input.py` | Non-browse read path; should remain no-thaw for pure reads, with file-level materialize where needed. | Current: `nodir_resolve` + `materialize_path_if_archive` + direct `Watershed.getInstance()` | Current controller init dependency is a blocker until constructor mixed-state behavior is addressed. |
| Mod consumers (`SWAT`, `RHEM`, salvage flowpaths) | `wepppy/nodb/mods/swat/swat.py`, `wepppy/nodb/mods/rhem/rhem.py`, `wepppy/nodb/mods/salvage_logging/flowpaths.py` | Read-only consumption should remain thaw-free, using file-level materialization for archive form. | Current: direct `wat_dir`/`network.txt`/glob reads | Phase 6 should replace direct path assumptions at FS-boundary call sites. |

## Proposed Orchestration Contract (Design Only)

Recommended helper boundary for Phase 6 implementation:
- Preferred home: `wepppy/nodir/` alongside `thaw_freeze.py` (thin orchestration wrapper over `maintenance_lock()`, `thaw()`, `freeze()`).
- Primary callers: watershed mutation owners in `wepppy/rq/project_rq.py` and watershed migration utilities.
- Route handlers in `wepppy/microservices/rq_engine/watershed_routes.py` remain validation/enqueue surfaces (no thaw/freeze logic in HTTP layer).

Proposed sequence (single root: `watershed`):
1. Preflight checks:
- Determine whether the operation can write under `WD/watershed/*` (`touches_root` classification).
- If `touches_root` is false: run callback directly (no thaw/freeze).
- If `touches_root` is true: reject mixed/invalid/transitional states with canonical NoDir errors.
2. Lock acquisition:
- Acquire `nodb-lock:<runid>:nodir/watershed` before any thaw/freeze/state-file/temp-sentinel writes.
- Lock order rule: NoDir maintenance lock outermost, NoDb locks inside callback.
3. Thaw decision:
- Dir form: no-op (callback executes against `WD/watershed/`).
- Archive form: call `thaw(wd, "watershed")` before callback.
4. Mutation callback boundary:
- Execute the existing mutation owner (`abstract_watershed`, migration function, etc.) unchanged.
5. Freeze/finalize:
- If helper thawed the root and callback succeeded: call `freeze(wd, "watershed")`.
- If callback succeeded with no thaw: finalize with no state transition.
6. Rollback/error behavior:
- If callback fails after thaw: do not auto-freeze; keep root thawed with `dirty=true`, propagate failure.
- If freeze fails: propagate failure and preserve thawed state for deterministic recovery.
- Request-serving surfaces never clean transitional sentinels; only maintenance tooling may do so.

## Unresolved Decisions
- Resolve `Watershed.__init__` eager `wat_dir` creation so archive-form read paths can instantiate controller state without mixed-state side effects.
- Resolve `_structure` serialized-path hazard (`structure.json` path-string persistence) before finalizing freeze-era invariants.
- Decide high-fanout slope/network read strategy for `wepp.prep_watershed` and mod consumers: per-file materialization vs bounded read-session helper.
