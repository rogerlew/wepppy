# NoDir Touchpoints Inventory (landuse/ soils/ climate/ watershed)

> Purpose: enumerate current read/write/mutate call sites that assume these roots are real directories, so NoDir integration can be planned/tested without “surprise” regressions.

## Legend
- **Producer**: creates/updates/deletes files under the root.
- **Consumer**: reads/globs/walks paths under the root.
- **FS-boundary**: shells out or hands an on-disk path to a tool/library that cannot read from an archive stream (requires materialize-or-error).
- **Mixed-state-sensitive**: will behave differently depending on whether `WD/<root>/` or `WD/<root>.nodir` exists (or both).

## Root: `landuse` (`WD/landuse/` or `WD/landuse.nodir`)

### Producers (writes/mutates)
- `wepppy/nodb/core/landuse.py`: owns `Landuse.lc_dir` (`WD/landuse`); `clean()` does `rmtree + mkdir`; `symlink_landuse_map()` creates/updates `nlcd.(tif|vrt)` (+ optional `.prj`) and may create symlinks; writes fractional JSON sidecars under `landuse/fractionals/...`; writes `landuse/landuse.parquet` + calls `update_catalog_entry(wd, "landuse/landuse.parquet")`. (Producer, mixed-state-sensitive)
- `wepppy/microservices/rq_engine/landuse_routes.py`: UserDefined flow saves upload to `WD/landuse/_{filename}` then writes `WD/landuse/nlcd.(tif|vrt)` via `raster_stacker(...)`. (Producer)
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`: mutates controller state; any handler that triggers rebuild will indirectly mutate `WD/landuse/*`. (Producer via controller)
- `wepppy/nodb/mods/treatments/treatments.py`: writes new management files directly to `WD/landuse/<new_man>.man` via `_join(self.wd, "landuse", ...)` and persists `man_dir = WD/landuse` inside summaries. (Producer, mixed-state-sensitive, **serialized-path hazard**)
- `wepppy/nodb/mods/omni/omni.py`: clones/copies/removes `WD/landuse/` and rewrites `WD/landuse/landuse.parquet` for contrasts/scenarios. (Producer, mixed-state-sensitive)
- `wepppy/tools/migrations/landuse.py`, `wepppy/tools/migrations/migrate_landuse_parquet.py`: read/write `WD/landuse/landuse.parquet` and update catalog entries. (Producer, mixed-state-sensitive)

### Consumers (reads/globs/walks)
- `wepppy/nodb/core/wepp.py`: uses `Landuse.lc_dir` as `ManagementDir` when generating `.man` for `wepp/runs`; consumes `.man` templates and landuse mapping summaries. (Consumer, mixed-state-sensitive)
- `wepppy/nodb/duckdb_agents.py`: reads `WD/landuse/landuse.parquet` by filesystem path (`_join(wd, "landuse/landuse.parquet")`). (Consumer, mixed-state-sensitive)
- `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py`, `wepppy/wepp/reports/*`: read `WD/landuse/landuse.parquet` by filesystem path. (Consumer, mixed-state-sensitive, FS-boundary for tools that require real files)
- `wepppy/query_engine/*`: catalogs and queries assume discoverable filesystem assets; see **Cross-Cutting**. (Consumer, mixed-state-sensitive)
- UI strings: `wepppy/weppcloud/templates/*`, `wepppy/weppcloud/static/js/*` refer to logical paths like `landuse/landuse.parquet` (these SHOULD remain stable; still a touchpoint for query-engine + download plumbing). (Consumer)

## Root: `soils` (`WD/soils/` or `WD/soils.nodir`)

### Producers (writes/mutates)
- `wepppy/nodb/core/soils.py`: owns `Soils.soils_dir` (`WD/soils`); `clean()` does `rmtree + mkdir`; `symlink_soils_map()` creates/updates `ssurgo.(tif|vrt)` (+ optional `.prj`) and may create symlinks; generates many `*.sol`; writes `soils/soils.parquet` + calls `update_catalog_entry(wd, "soils/soils.parquet")`. (Producer, mixed-state-sensitive)
- `wepppy/nodb/mods/*`: multiple mods create/copy/modify soils artifacts (not exhaustive): `wepppy/nodb/mods/disturbed/disturbed.py`, `wepppy/nodb/mods/baer/baer.py`, `wepppy/nodb/mods/rred/rred.py`, `wepppy/nodb/mods/treatments/treatments.py`, `wepppy/nodb/mods/omni/omni.py`. (Producer, mixed-state-sensitive)
- `wepppy/tools/migrations/soils.py`, `wepppy/tools/migrations/migrate_soils_parquet.py`: read/write `WD/soils/soils.parquet` and update catalog entries. (Producer, mixed-state-sensitive)
- Region builders (called by `Soils`): `wepppy/locales/earth/soils/isric/__init__.py`, `wepppy/eu/soils/*`, `wepppy/au/soils/*`, `wepppy/soils/ssurgo/*` write many files under a passed `soils_dir` (often `WD/soils`). (Producer, FS-boundary)

### Consumers (reads/globs/walks)
- `wepppy/nodb/core/wepp.py`: consumes `WD/soils/*.sol` and writes derived soils to `wepp/runs/*.sol` (including MOFE variants). (Consumer, mixed-state-sensitive)
- `wepppy/nodb/duckdb_agents.py`: reads `WD/soils/soils.parquet` by filesystem path. (Consumer, mixed-state-sensitive)
- `wepppy/export/export.py`: `shutil.copytree(soils.soils_dir, ...)` for WinWEPP export. (Consumer, FS-boundary)
- `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py`, `wepppy/wepp/reports/*`: read `WD/soils/soils.parquet`. (Consumer, mixed-state-sensitive)
- NoDb payload hazard example: `wepppy/_tests/feverish-lamp/soils.nodb` contains serialized `soils_dir: ".../soils"` inside `SoilSummary` objects; any runtime use of that field must not assume a real directory when archived. (Mixed-state-sensitive, **serialized-path hazard**)

## Root: `climate` (`WD/climate/` or `WD/climate.nodir`)

### Producers (writes/mutates)
- `wepppy/nodb/base.py`: `NoDbBase.cli_dir = WD/climate` is the canonical directory path used across controllers. (Mixed-state-sensitive)
- `wepppy/nodb/core/climate.py`: ensures `cli_dir` exists; builds/writes `.cli`, `.par`, `.prn`, multiple `*.parquet` caches, plus CSV report artifacts under `WD/climate/*`; some modes clear/rebuild per-hillslope climates. (Producer, mixed-state-sensitive)
- `wepppy/microservices/rq_engine/upload_climate_routes.py`: saves uploaded `.cli` to `Path(climate.cli_dir)` then enqueues validation. (Producer, mixed-state-sensitive)
- `wepppy/climates/cligen/cligen.py`: produces/consumes `cli_dir` content during CLIGEN workflows. (Producer/consumer, mixed-state-sensitive)

### Consumers (reads/globs/walks)
- `wepppy/nodb/core/wepp.py`: `_prep_climates()` copies `WD/climate/<cli_fn>` to `wepp/runs/*.cli`; SS batch copies a shared template `.cli`. (Consumer, mixed-state-sensitive)
- `wepppy/weppcloud/routes/nodb_api/climate_bp.py`: reads report CSVs under `cli_dir` (e.g., `atlas14_intensity_pds_mean_metric.csv`, `wepp_cli_pds_mean_metric.csv`). (Consumer, mixed-state-sensitive)
- `wepppy/wepp/interchange/_utils.py`, `wepppy/wepp/interchange/_rust_interchange.py`: ensure/read `wepp_cli.parquet` under `cli_dir` via `Path(cli_dir).glob("*.cli")`. (Consumer, FS-boundary)
- `wepppy/export/export.py`: `shutil.copytree(ron.cli_dir, ...)` for WinWEPP export. (Consumer, FS-boundary)

## Root: `watershed` (`WD/watershed/` or `WD/watershed.nodir`)

### Producers (writes/mutates)
- `wepppy/nodb/base.py`: `NoDbBase.wat_dir = WD/watershed`. (Mixed-state-sensitive)
- `wepppy/nodb/core/watershed.py`: primary producer of watershed artifacts (parquets + slope files + structure/network metadata); uses `os.mkdir/os.makedirs/open()` heavily under `wat_dir`. (Producer, mixed-state-sensitive, FS-boundary for many sub-tools)
- `wepppy/topo/peridot/peridot_runner.py`: reads/writes `WD/watershed/{hillslopes,channels,flowpaths}.{csv,parquet}`; removes CSVs; calls `update_catalog_entry(wd, "watershed")`. (Producer, mixed-state-sensitive)
- `wepppy/topo/watershed_abstraction/watershed_abstraction.py`: reads/writes `wat_dir` artifacts as part of abstraction/migration flows. (Producer/consumer, mixed-state-sensitive)
- `wepppy/tools/migrations/watershed.py`: migrates/writes watershed parquets (`hillslopes.parquet`, `channels.parquet`, `flowpaths.parquet`) and related files. (Producer, mixed-state-sensitive)

### Consumers (reads/globs/walks)
- `wepppy/nodb/core/wepp.py`: consumes slope files and network/structure metadata:
  - peridot: reads `WD/watershed/slope_files/hillslopes/*.slp` and `.../channels.slp`
  - legacy: reads `WD/watershed/hill_<id>.slp` and `WD/watershed/channels.slp`
  - flowpaths: globs `WD/watershed/slope_files/flowpaths/*.slps` (Consumer, mixed-state-sensitive)
- `wepppy/nodb/duckdb_agents.py`: reads `WD/watershed/{hillslopes,channels}.parquet` by filesystem path. (Consumer, mixed-state-sensitive)
- `wepppy/export/prep_details.py`, `wepppy/export/gpkg_export.py`, `wepppy/wepp/reports/*`: read `WD/watershed/{hillslopes,channels}.parquet` by filesystem path. (Consumer, mixed-state-sensitive, FS-boundary)
- Mods: `wepppy/nodb/mods/swat/swat.py` consumes watershed parquets via `_join(self.wd, "watershed", ...)`; `wepppy/nodb/mods/salvage_logging/flowpaths.py` globs `WD/watershed/flowpaths/*.npy`. (Consumer, mixed-state-sensitive)

## Cross-Cutting Touchpoints (all four roots)

### Browse / Files / Download microservice
- `wepppy/microservices/browse/listing.py`: builds a manifest and/or snapshots directory entries via `os.scandir`; it currently sorts `*.nodir` with directories but does not list archive contents. (Consumer, mixed-state-sensitive)
- `wepppy/microservices/browse/files_api.py`: resolves `wd + rel_path` to real paths and stats via filesystem; cannot address archive-inner paths without NoDir-aware path resolution. (Consumer)
- `wepppy/microservices/browse/_download.py`: downloads by `os.path.exists(wd/subpath)`; cannot stream `*.nodir/<inner>` without archive-aware open. Also generates `aria2c.spec` from filesystem walk. (Consumer, mixed-state-sensitive)
- `wepppy/microservices/browse/dtale.py`: requires `os.path.isfile(target)` and forwards `path` to the D-Tale service; archive-inner paths require materialization. (FS-boundary)
- `wepppy/microservices/_gdalinfo.py`: shells out `gdalinfo -json <path>`; archive-inner rasters require materialization. (FS-boundary)
- `wepppy/weppcloud/routes/diff/diff.py`: opens real files on disk; archive-inner paths require materialization or explicit “unsupported” errors. (FS-boundary)

### Query engine + catalogs
- `wepppy/query_engine/activate.py`: builds catalog by filesystem walk (`os.scandir` + symlink allowlist) and cannot discover assets inside `.nodir` without an archive-aware iterator (or materialize-on-activate). (Consumer, mixed-state-sensitive)
- Many modules reference logical dataset paths that are currently realized as filesystem paths under `WD/<root>/...`:
  - `wepppy/nodb/duckdb_agents.py`
  - `wepppy/export/prep_details.py`
  - `wepppy/export/gpkg_export.py`
  - `wepppy/query_engine/app/*` (presets reference e.g. `landuse/landuse.parquet`, `soils/soils.parquet`, `watershed/hillslopes.parquet`)

### Mixed state hot spots (directory + `.nodir` both present)
- Any code that does direct filesystem operations against `WD/<root>/...` will silently “choose” the directory form if it exists (even if `.nodir` also exists). This includes most controllers + exports + migrations listed above. (Mixed-state-sensitive)

## Repro / Update Commands (local)
- `rg -l '\\blc_dir\\b' wepppy`
- `rg -l '\\bsoils_dir\\b' wepppy`
- `rg -l '\\bcli_dir\\b' wepppy`
- `rg -l '\\bwat_dir\\b' wepppy`
- `rg -n \"_join\\([^\\n]*'(landuse|soils|climate|watershed)'\" wepppy`
- `rg -n \"'landuse/|soils/|climate/|watershed/\" wepppy`

