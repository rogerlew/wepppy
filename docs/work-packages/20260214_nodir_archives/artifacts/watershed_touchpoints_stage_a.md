# Watershed Touchpoints Stage A (Phase 6a)

Scope: reconcile watershed touchpoints against current code and classify readiness for NoDir mutation adoption.

| Touchpoint | File | Class | Current Behavior | NoDir Readiness | Notes/Blocker |
| --- | --- | --- | --- | --- | --- |
| Watershed controller bootstrap (`wat_dir` mkdir) | `wepppy/nodb/core/watershed.py` | producer | `Watershed.__init__` creates `WD/watershed` when missing. | blocked | Creates mixed state when `WD/watershed.nodir` exists. |
| Watershed abstraction orchestration | `wepppy/nodb/core/watershed.py` | producer, FS-boundary | `abstract_watershed()` runs Peridot/TOPAZ abstraction and writes watershed outputs under `wat_dir`. | thaw-required | Must run in thaw/modify/freeze wrapper. |
| Legacy TOPAZ abstraction writes | `wepppy/nodb/core/watershed.py` | producer, FS-boundary | `_topaz_abstract_watershed()` writes `channels.slp`, `hill_*.slp`, flowpath files, and structure metadata. | thaw-required | Heavy direct filesystem writes under `WD/watershed`. |
| Structure persistence and `_structure` serialization | `wepppy/nodb/core/watershed.py` | producer, consumer, serialized-path hazard | `_structure` may hold a `structure.json` path; property reads/writes `WD/watershed/structure.json`. | blocked | Serialized absolute/relative path semantics couple runtime behavior to directory form. |
| Network reads from `wat_dir` | `wepppy/nodb/core/watershed.py` | consumer | `network` property reads `WD/watershed/network.txt` directly. | thaw-required | Needs materialize/read boundary when source is archived. |
| Parquet-backed watershed summaries | `wepppy/nodb/core/watershed.py` | consumer | `sub_summary`/`subs_summary`/`chn_summary`/`chns_summary`/`fps_summary` use sidecar-first parquet lookup. | archive-ready | Already uses logical IDs + sidecar resolution. |
| Slope path helpers | `wepppy/nodb/core/watershed.py` | consumer | `hillslope_slp_fn` returns `WD/watershed/<slp_rel_path>` and callers expect a real file. | thaw-required | Needs FS-boundary wrapper/materialization at call sites. |
| Peridot post-processing outputs | `wepppy/topo/peridot/peridot_runner.py` | producer, FS-boundary | `post_abstract_watershed()` rewrites `watershed/*.csv` to `WD/watershed.*.parquet` sidecars and removes CSVs. | thaw-required | Requires writable thawed tree. |
| Peridot watershed migration | `wepppy/topo/peridot/peridot_runner.py` | producer | `migrate_watershed_outputs()` normalizes watershed sidecars but instantiates `Watershed` first. | blocked | Inherits controller mkdir mixed-state blocker before migration work starts. |
| Watershed abstraction engine (`WatershedAbstraction`) | `wepppy/topo/watershed_abstraction/watershed_abstraction.py` | producer, consumer, FS-boundary | Requires existing `wat_dir`; reads TOPAZ rasters and writes slope/network outputs. | thaw-required | Directory-form runtime requirement is explicit. |
| Project bootstrap orchestration | `wepppy/rq/project_rq.py` | producer, consumer | `project_execute_rq()` and `test_run_rq()` fetch `Watershed` and run watershed build/abstraction paths. | thaw-required | Should route watershed mutations through thaw wrapper. |
| Watershed RQ mutation jobs | `wepppy/rq/project_rq.py` | producer | `build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq`, `abstract_watershed_rq` mutate watershed state/files. | thaw-required | Mutation jobs are current ownership boundary. |
| RQ-engine watershed routes | `wepppy/microservices/rq_engine/watershed_routes.py` | producer, consumer | Route handlers call `Watershed.getInstance()` and mutate options or enqueue mutation jobs. | thaw-required | Route-layer mutation entrypoints need thaw-aware orchestration. |
| WEPP watershed prep/run queue flow | `wepppy/rq/wepp_rq.py` | consumer, FS-boundary | `_prep_watershed_rq` + translator flows consume watershed slopes/network via `wepp.prep_watershed()`. | thaw-required | Depends on directory-backed slope assets today. |
| Prep-details export | `wepppy/export/prep_details.py` | consumer | Reads watershed parquets via `pick_existing_parquet_path()`. | archive-ready | No direct `wat_dir` traversal for watershed tables. |
| GeoPackage export | `wepppy/export/gpkg_export.py` | consumer, FS-boundary | Uses `materialize_path_if_archive()` for watershed vectors and sidecar parquet joins for attributes. | archive-ready | Archive-aware for watershed geometry + tables. |
| ERMiT export | `wepppy/export/ermit_input.py` | consumer, FS-boundary | Calls `nodir_resolve` but then uses `Watershed.getInstance()`, `_subs_summary`, and `wat_dir` slope loops (partial materialize fallback). | blocked | Still relies on controller initialization + in-memory summaries tied to dir workflows. |
| WinWEPP export | `wepppy/export/export.py` | consumer, FS-boundary | Builds export bundle from NoDb controllers and translator-backed watershed metadata. | thaw-required | Runtime path assumptions remain in watershed-dependent prep stack. |
| Browse HTML handler | `wepppy/microservices/browse/browse.py` | consumer | `parse_external_subpath` + `nodir_resolve`; uses `nodir_listdir`/`nodir_open_read`; enforces mixed-state precedence. | archive-ready | Watershed archive browsing works through NoDir API. |
| Files JSON API | `wepppy/microservices/browse/files_api.py` | consumer | Uses `nodir_stat`/`nodir_listdir` for metadata/listing with mixed-state guards. | archive-ready | NoDir-aware path and metadata handling. |
| Download API | `wepppy/microservices/browse/_download.py` | consumer, FS-boundary | Streams archive entries with `nodir_open_read`; supports raw root archive download and mixed-state checks. | archive-ready | Watershed archive content download is wired. |
| D-Tale bridge | `wepppy/microservices/browse/dtale.py` | consumer, FS-boundary | Resolves NoDir targets and materializes archive files before D-Tale load. | archive-ready | Boundary contract implemented via `materialize_file()`. |
| GDAL info endpoint | `wepppy/microservices/_gdalinfo.py` | consumer, FS-boundary | Resolves NoDir targets and materializes archive files before running `gdalinfo`. | archive-ready | Boundary contract implemented via `materialize_file()`. |
| Query-engine watershed cataloging | `wepppy/query_engine/activate.py` | consumer | Canonicalizes `watershed.*.parquet` sidecars to logical `watershed/*.parquet` entries during catalog build/update. | thaw-required | Sidecar datasets are handled, but non-sidecar archive internals still require explicit strategy. |
| SWAT downstream topology mapping | `wepppy/nodb/mods/swat/swat.py` | consumer | Reads watershed parquets sidecar-first, then `_build_downstream_map()` directly reads `WD/watershed/network.txt` if present. | thaw-required | `network.txt` read path is directory-coupled. |
| RHEM hillslope prep | `wepppy/nodb/mods/rhem/rhem.py` | consumer, FS-boundary | Uses `Watershed.getInstance()` and opens watershed slope files under `wat_dir`. | thaw-required | Needs thaw/materialize boundary for slope-file reads. |
| Path-CE data loader | `wepppy/nodb/mods/path_ce/data_loader.py` | consumer | Reads `watershed/hillslopes.parquet` through sidecar-first resolver. | archive-ready | Parquet-driven workflow already NoDir-compatible. |
| OMNI scenario clone (`watershed` root handling) | `wepppy/nodb/mods/omni/omni.py` | producer, consumer | Clone logic links `climate`/`watershed` as either dir or `.nodir` archive based on source form. | archive-ready | Root-form aware at clone boundary. |
| Salvage flowpath utility | `wepppy/nodb/mods/salvage_logging/flowpaths.py` | consumer | Uses `Watershed.getInstance()` and globs `WD/watershed/flowpaths/*.npy`. | thaw-required | Direct path/glob coupling to directory form. |
| DuckDB watershed query helpers | `wepppy/nodb/duckdb_agents.py` | consumer | Watershed helper queries use sidecar-first parquet resolution. | archive-ready | Logical dataset mapping is already stable. |
| Watershed migration utility | `wepppy/tools/migrations/watershed.py` | producer, consumer | Migrates watershed tables/sidecars and externalizes inline `_structure` to `structure.json`. | archive-ready | Does not require `Watershed.getInstance()` for migration operations. |
| Core WEPP watershed input prep | `wepppy/nodb/core/wepp.py` | consumer, FS-boundary | Watershed prep paths (`_prep_slopes*`, flowpath prep, channel slope prep) read `wat_dir` slope/network files directly. | thaw-required | Requires thaw/materialize handling for slope-file inputs. |

## Stage A Totals

### Counts by Class
- `producer`: 12
- `consumer`: 26
- `FS-boundary`: 13
- `serialized-path hazard`: 1

### Counts by Readiness
- `archive-ready`: 12
- `thaw-required`: 16
- `blocked`: 4

### Top Blockers
- `wepppy/nodb/core/watershed.py`: `Watershed.__init__` eagerly creates `WD/watershed`, creating mixed state when only `watershed.nodir` should exist.
- `wepppy/nodb/core/watershed.py`: `_structure` persistence uses path-string semantics (`structure.json`) that are directory-form specific.
- `wepppy/topo/peridot/peridot_runner.py`: `migrate_watershed_outputs()` calls `Watershed.getInstance()` and inherits the constructor mixed-state blocker.
- `wepppy/export/ermit_input.py`: export path still depends on `Watershed.getInstance()`, `_subs_summary`, and direct `wat_dir` slope iteration.
