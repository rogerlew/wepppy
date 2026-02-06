# RQ Job Dependencies Catalog
> Manual catalog of RQ entrypoints that enqueue child jobs and the dependency graph between them.
> This is derived from `Queue.enqueue_call` / `Queue.enqueue` usage, not from any single output file.

## Scope
- Modules: `wepppy/rq/*.py` (entrypoints that enqueue other jobs).
- rq-engine routes that build dependency chains directly: `wepppy/microservices/rq_engine/run_sync_routes.py`.

## Path Legend
| Token | Meaning |
| --- | --- |
| `wd` | Run working directory (e.g., `/wc1/runs/<prefix>/<runid>`). |
| `runs_dir` | `Wepp.runs_dir` (typically `wd/wepp/runs`). |
| `output_dir` | `Wepp.output_dir` (typically `wd/wepp/output`). |
| `plot_dir` | `Wepp.plot_dir` (typically `wd/wepp/plots`). |
| `export_dir` | `Wepp.export_dir` (typically `wd/export`). |
| `wat_dir` | `Watershed.wat_dir` (watershed workspace; varies by backend). |
| `cli_dir` | `Wepp.cli_dir` (climate .cli directory). |
| `soils_dir` | `Soils.soils_dir` (source soils). |
| `lc_dir` | `Landuse.lc_dir` (landuse/management templates). |
| `fp_runs_dir` | `Wepp.fp_runs_dir` (flowpath run staging). |
| `omni_dir` | `wd/omni` (OMNI_REL_DIR). |
| `swat_txtinout_dir` | `Swat.swat_txtinout_dir` (SWAT TxtInOut). |
| `dem_dir` | `Ron.dem_dir` (DEM staging). |

## Conventions
- Parent jobs record child ids in `job.meta["jobs:<order>,..."]` for `job_info.py` and `cancel_job.py`.
- `depends_on` uses a single job or a list; when the list is empty, it is passed as `None` (no dependency).
- Prereq files list explicit file/dir inputs referenced by the job or immediate controller calls. Optional inputs are marked.
- Paths are shown relative to `wd` unless noted; placeholders like `<topaz>` and `<wepp_id>` indicate per-hillslope files.

## Catalog

**`wepppy/rq/wepp_rq.py`**

**`run_wepp_rq(runid)`**

Graph (stage order is the `jobs:<n>` prefix):
```text
jobs:0 prep inputs
  -> _prep_remaining_rq
  -> _run_hillslopes_rq
  -> (_prep_watershed_rq if run_watershed)
  -> _build_hillslope_interchange_rq
  -> (_build_totalwatsed3_rq if not single storm)
  -> (_post_dss_export_rq if enabled)
  -> (_run_flowpaths_rq if enabled)
  -> (SWAT build/run if enabled)
  -> watershed runs (if run_watershed)
  -> post-run jobs (cleanup, prep details, watbal, loss grid, watershed interchange, return periods)
  -> export jobs (legacy arc, gpkg)
  -> _log_complete_rq
```

Child jobs, dependencies, and file prerequisites:

| Stage | Child job | `depends_on` | File prerequisites (relative to `wd`) |
| --- | --- | --- | --- |
| jobs:0 | `_prep_multi_ofe_rq` | none | `wat_dir/slope_files/hillslopes/hill_<topaz>.mofe.slp`; `soils_dir/hill_<topaz>.mofe.sol`; `lc_dir/*.man`; optional `wepp.kslast_map` raster |
| jobs:0 | `_prep_slopes_rq` | none | `wat_dir/hill_<topaz>.slp` or `wat_dir/slope_files/hillslopes/hill_<topaz>.slp` |
| jobs:0 | `_prep_managements_rq` | none | `landuse/landuse.parquet`; `lc_dir/*.man`; `soils/soils.parquet`; optional `disturbed.nodb` + disturbed maps; optional `rap/rap_ts.parquet` |
| jobs:0 | `_prep_soils_rq` | none | `soils_dir/*.sol`; optional `wepp.kslast_map` raster; `soils/soils.parquet` for soil metadata |
| jobs:0 | `_prep_climates_rq` | none | `cli_dir/<cli_fn>`; for SS batch writes `runs_dir/p<wepp_id>.<ss_batch_id>.cli` and `runs_dir/pw0.<ss_batch_id>.cli` |
| jobs:0 | `_prep_remaining_rq` | `jobs0_hillslopes_prep` list | `runs_dir/p*.slp`; `runs_dir/p*.sol`; `runs_dir/p*.man`; `runs_dir/p*.cli` |
| jobs:1 | `_run_hillslopes_rq` | `_prep_remaining_rq` | `runs_dir/*.run`; `runs_dir/p*.slp`; `runs_dir/p*.sol`; `runs_dir/p*.man`; `runs_dir/p*.cli` |
| jobs:2 | `_prep_watershed_rq` | `_run_hillslopes_rq` | `wat_dir/structure.json` or `wat_dir/network.txt`; `wat_dir/channels.parquet`; `wat_dir/hillslopes.parquet`; `wat_dir/slope_files/channels.slp` or `wat_dir/channels.slp`; `soils/soils.parquet`; `cli_dir/<cli_fn>` |
| jobs:2 | `_build_hillslope_interchange_rq` | `_run_hillslopes_rq` | `output_dir/H*.pass.dat`; `output_dir/H*.ebe.dat`; `output_dir/H*.element.dat`; `output_dir/H*.loss.dat`; `output_dir/H*.soil.dat`; `output_dir/H*.wat.dat` |
| jobs:2 | `_build_totalwatsed3_rq` | `_build_hillslope_interchange_rq` | `output_dir/interchange/H.pass.parquet`; `output_dir/interchange/H.wat.parquet`; optional `ash/H<wepp_id>_ash.parquet` or `ash/H<wepp_id>.parquet`; optional `ash.nodb`; `wat_dir/hillslopes.parquet` (area lookup when ash is present) |
| jobs:2 | `post_dss_export_rq` | `_build_hillslope_interchange_rq` | `output_dir/interchange/H.pass.parquet`; `output_dir/interchange/H.wat.parquet`; optional `ash/*.parquet`; `output_dir/interchange/chan.out.parquet`; `watershed.channels_shp` (GeoJSON); `wat_dir/network.txt` (downstream mapping); `export/dss` dir (created) |
| jobs:2 | `_run_flowpaths_rq` | `_prep_remaining_rq` | `wat_dir/slope_files/flowpaths/*.slps`; `fp_runs_dir` (created/cleaned by controller) |
| jobs:2 | `_build_swat_inputs_rq` | `_build_hillslope_interchange_rq` (+ `_prep_watershed_rq` if present) | `wepp/output/*` (hillslope outputs); `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; `swat_template_dir/*` (config `swat_template_dir`) |
| jobs:3 | `_run_swat_rq` | `_build_swat_inputs_rq` | `swat_txtinout_dir/*` |
| jobs:3 | `run_watershed_rq` / `run_ss_batch_watershed_rq` | `_prep_watershed_rq` | `runs_dir/pw0.str`; `runs_dir/pw0.slp`; `runs_dir/pw0.chn`; `runs_dir/pw0.sol`; `runs_dir/pw0.cli`; `runs_dir/pw0.man`; `runs_dir/chan.inp`; for SS batch `runs_dir/pw0.<ss_batch_id>.cli` |
| jobs:4 | `_post_run_cleanup_out_rq` | `jobs3_watersheds` or `_prep_watershed_rq` | `runs_dir/*.out`; optional `runs_dir/tc_out.txt` |
| jobs:4 | `_post_prep_details_rq` | `post_dependencies` | `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; `landuse/landuse.parquet`; `soils/soils.parquet` |
| jobs:4 | `_run_hillslope_watbal_rq` | `post_dependencies` | `output_dir/interchange/H.wat.parquet` |
| jobs:4 | `_post_make_loss_grid_rq` | `post_dependencies` | `watershed.subwta` (`wat_dir/SUBWTA.ARC` or `wbt_wd/subwta.tif`); `watershed.discha` (`wat_dir/DISCHA.ARC` or `wbt_wd/discha.tif`); `output_dir/H*` |
| jobs:4 | `_post_watershed_interchange_rq` | `post_dependencies` | `output_dir/pass_pw0.txt`; `output_dir/ebe_pw0.txt`; `output_dir/chan.out`; `output_dir/chanwb.out`; `output_dir/chnwb.txt`; `output_dir/soil_pw0.txt` or `output_dir/soil_pw0.txt.gz`; `output_dir/loss_pw0.txt` |
| jobs:4 | `_analyze_return_periods_rq` | `_post_watershed_interchange_rq` (+ `_build_totalwatsed3_rq` if present) | `output_dir/loss_pw0.txt`; optional cached `output_dir/return_periods*.json` |
| jobs:5 | `_post_legacy_arc_export_rq` | `jobs4_post` | `topaz_wd/*.ARC`; `topaz_wd/SUBCATCHMENTS.JSON`; `topaz_wd/CHANNELS.JSON`; `output_dir/loss_pw0.txt`; `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; optional `ash` metadata |
| jobs:5 | `_post_gpkg_export_rq` | `jobs4_post` | `watershed.subwta_shp` (SUBCATCHMENTS.WGS JSON); `watershed.channels_shp` (CHANNELS.WGS JSON); `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; `landuse/landuse.parquet`; `soils/soils.parquet`; `output_dir/loss_pw0.hill.parquet`; `output_dir/loss_pw0.chn.parquet` |
| jobs:6 | `_log_complete_rq` | `jobs4_post + jobs5_post` | `ron.nodb` |

Audit notes:
1. `_run_hillslope_watbal_rq` waits for `output_dir/interchange/H.wat.parquet` internally but is not explicitly dependent on `_build_hillslope_interchange_rq`.
2. `_run_flowpaths_rq` only depends on `_prep_remaining_rq`. It requires `wat_dir/slope_files/flowpaths/*.slps`; verify those are always ready before `_prep_remaining_rq` completes.
3. `post_dss_export_rq` depends on `_build_hillslope_interchange_rq` only. If DSS export needs `totalwatsed3` outputs from a prior step, add a dependency on `_build_totalwatsed3_rq`.
4. `_build_totalwatsed3_rq` depends on hillslope interchange. If watershed outputs are required, depend on `jobs3_watersheds` or `_post_watershed_interchange_rq`.

**`run_wepp_watershed_rq(runid)`**

| Stage | Child job | `depends_on` | File prerequisites (relative to `wd`) |
| --- | --- | --- | --- |
| jobs:2 | `_prep_watershed_rq` | none | `wat_dir/structure.json` or `wat_dir/network.txt`; `wat_dir/channels.parquet`; `wat_dir/hillslopes.parquet`; `wat_dir/slope_files/channels.slp` or `wat_dir/channels.slp`; `soils/soils.parquet`; `cli_dir/<cli_fn>` |
| jobs:3 | `run_watershed_rq` / `run_ss_batch_watershed_rq` | `_prep_watershed_rq` | `runs_dir/pw0.*` as above; SS batch `runs_dir/pw0.<ss_batch_id>.cli` |
| jobs:4 | `_post_run_cleanup_out_rq` | `jobs3_watersheds` or `_prep_watershed_rq` | `runs_dir/*.out`; optional `runs_dir/tc_out.txt` |
| jobs:4 | `_post_prep_details_rq` | `post_dependencies` | `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; `landuse/landuse.parquet`; `soils/soils.parquet` |
| jobs:4 | `_post_make_loss_grid_rq` | `post_dependencies` | `watershed.subwta`; `watershed.discha`; `output_dir/H*` |
| jobs:4 | `_post_watershed_interchange_rq` | `post_dependencies` | `output_dir/pass_pw0.txt`; `output_dir/ebe_pw0.txt`; `output_dir/chan.out`; `output_dir/chanwb.out`; `output_dir/chnwb.txt`; `output_dir/soil_pw0.txt` or `output_dir/soil_pw0.txt.gz`; `output_dir/loss_pw0.txt` |
| jobs:4 | `_analyze_return_periods_rq` | `_post_watershed_interchange_rq` | `output_dir/loss_pw0.txt`; optional cached `output_dir/return_periods*.json` |
| jobs:5 | `_post_legacy_arc_export_rq` | `jobs4_post` | `topaz_wd/*.ARC`; `topaz_wd/SUBCATCHMENTS.JSON`; `topaz_wd/CHANNELS.JSON`; `output_dir/loss_pw0.txt`; `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; optional `ash` metadata |
| jobs:6 | `_log_complete_rq` | `jobs4_post + jobs5_post` | `ron.nodb` |

Audit notes:
1. This entrypoint bypasses hillslope prep/run; ensure downstream jobs only require watershed outputs.

**`wepppy/rq/swat_rq.py`**

**`run_swat_rq(runid)`**

| Stage | Child job | `depends_on` | File prerequisites (relative to `wd`) |
| --- | --- | --- | --- |
| jobs:0 | `_build_swat_inputs_rq` | none | `wepp/output/*` (hillslope outputs); `wat_dir/hillslopes.parquet`; `wat_dir/channels.parquet`; `swat_template_dir/*` |
| jobs:1 | `_run_swat_rq` | `_build_swat_inputs_rq` | `swat_txtinout_dir/*` |

Audit notes:
1. This assumes WEPP outputs already exist. The caller is responsible for enqueueing only after WEPP hillslope/watershed outputs are ready.

**`wepppy/rq/batch_rq.py`**

**`run_batch_rq(batch_name)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| jobs:0 | `run_batch_watershed_rq` (per watershed feature) | none | Batch workspace `batch_root/<batch_name>`; `batch_runner.nodb`; uploaded watershed GeoJSON (stored in `batch_runner.nodb` state); base run directory for cloning |
| jobs:1 | `_final_batch_complete_rq` | all `jobs:0` | `batch_runner.nodb` (for status updates) |

Audit notes:
1. `run_batch_watershed_rq` calls `run_omni_scenarios_rq(runid)` inline. Those Omni jobs are not linked into the batch dependency tree, so batch completion does not wait for Omni completion. Confirm if this is intended.

**`wepppy/rq/culvert_rq.py`**

**`run_culvert_batch_rq(culvert_batch_uuid)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| jobs:0 | `run_culvert_run_rq` (per run_id) | none | `batch_root/metadata.json`; `batch_root/model-parameters.json`; `batch_root/topo/breached_filled_DEM_UTM.tif` (or payload override); `batch_root/topo/streams.tif` (or payload override); `batch_root/culverts/watersheds.geojson`; `batch_root/topo/flovec.tif`; `batch_root/topo/netful.tif`; `batch_root/topo/chnjnt.tif`; `batch_root/topo/chnjnt.streams.tif` |
| jobs:1 | `_final_culvert_batch_complete_rq` | all `jobs:0` | `batch_root/culverts/*.json` run metadata (written by child jobs) |

Audit notes:
1. Batch-level topo generation happens before enqueueing children. If that becomes async, ensure child jobs depend on it.

**`run_culvert_run_rq(runid, culvert_batch_uuid, run_id)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| (inline) | `_process_culvert_run` (internal) | none | `batch_root/metadata.json`; `batch_root/model-parameters.json`; `batch_root/culverts/watersheds.geojson`; `batch_root/culverts/culvert_points.geojson`; `batch_root/topo/breached_filled_DEM_UTM.tif`; `batch_root/topo/flovec.tif`; `batch_root/topo/netful.tif`; `batch_root/topo/chnjnt.tif`; per-run directory `batch_root/runs/<run_id>` |

**`wepppy/rq/omni_rq.py`**

**`run_omni_scenarios_rq(runid)`**

| Stage | Child job | `depends_on` | File prerequisites (relative to `wd`) |
| --- | --- | --- | --- |
| jobs:0 | `run_omni_scenario_rq` (stage 1 scenarios) | none | Base scenario inputs under `wepp/output/*`; dependency hash uses `wepp/output/loss_pw0.txt` |
| jobs:1 | `run_omni_scenario_rq` (stage 2 scenarios) | all stage 1 jobs | Stage 1 scenario outputs under `omni/scenarios/<scenario>/wepp/output/loss_pw0.txt` |
| jobs:2 | `_compile_hillslope_summaries_rq` | stage 2 jobs (or stage 1 if no stage 2) | `wepp/output/loss_pw0.txt`; `omni/scenarios/<scenario>/wepp/output/loss_pw0.txt` |
| jobs:3 | `_finalize_omni_scenarios_rq` | `_compile_hillslope_summaries_rq` | `omni.nodb` |

Audit notes:
1. Stage 2 depends on the full set of stage 1 jobs, not just the specific scenario’s dependency. This is conservative but can increase critical path length.

**`run_omni_contrasts_rq(runid)`**

| Stage | Child job | `depends_on` | File prerequisites (relative to `wd`) |
| --- | --- | --- | --- |
| jobs:contrast:* | `run_omni_contrast_rq` | previous batch (if any) | `omni/contrasts/contrast_<id>.tsv`; scenario outputs referenced by sidecar paths under `omni/contrasts/<id>/wepp/output/*` |
| jobs:finalize | `_finalize_omni_contrasts_rq` | last batch | `omni.nodb` |

Audit notes:
1. Batches are chained (`batch_depends`), so the final dependency on the last batch implies all prior batches.

**`wepppy/rq/project_rq.py`**

**`fetch_dem_and_build_channels_rq(...)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| jobs:0 | `fetch_dem_rq` | none | `ron.nodb`; writes `dem_dir/dem.tif` or `dem_dir/dem.vrt` |
| jobs:1 | `build_channels_rq` | `fetch_dem_rq` | `dem_dir/dem.tif` or `dem_dir/dem.vrt` |
| jobs:0 | `build_channels_rq` | none | (upload DEM mode) `dem_dir/dem.tif` or `dem_dir/dem.vrt` already present |

Audit notes:
1. No file-based waits here; ensure `fetch_dem_rq` fully writes `dem_dir/dem.tif` before returning.

**`build_subcatchments_and_abstract_watershed_rq(runid, updates)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| jobs:0 | `build_subcatchments_rq` | none | `dem_dir/dem.tif` or `dem_dir/dem.vrt`; channel outputs under `wat_dir/*` from `build_channels_rq` |
| jobs:1 | `abstract_watershed_rq` | `build_subcatchments_rq` | `watershed.subwta` (`wat_dir/SUBWTA.ARC` or `wbt_wd/subwta.tif`) and associated topo products under `wat_dir/*` |

Audit notes:
1. `abstract_watershed_rq` includes a short `time.sleep(0.05)` to avoid a known file write race (`SUBWTA.ARC`). If the race reappears, add a file existence wait instead of a fixed sleep.

**`fork_rq(..., undisturbify=True)`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| (inline) | `run_wepp_rq(new_runid)` | none | Forked run directory with `.nodb` files (`ron.nodb`, `wepp.nodb`, `landuse.nodb`, `soils.nodb`, `disturbed.nodb`) |
| (inline) | `_finish_fork_rq` | final job from `run_wepp_rq` | relies on `run_wepp_rq` completion metadata |

Audit notes:
1. `_finish_fork_rq` depends on the final `_log_complete_rq` job produced by `run_wepp_rq`, so it should run after all WEPP tasks finish.

**`wepppy/microservices/rq_engine/run_sync_routes.py`**

**`POST /rq-engine/run-sync`**

| Stage | Child job | `depends_on` | File prerequisites |
| --- | --- | --- | --- |
| root | `run_sync_rq` | none | Target root writable (default `/wc1/runs`); remote source reachable |
| root | `migrations_rq` | `run_sync_rq` | `target_root/<prefix>/<runid>` run directory with `.nodb` files and run outputs |

Audit notes:
1. `migrations_rq` depends on the sync job, ensuring that run files exist before migrations execute.

## Checklist For New Child Jobs
1. Add `depends_on` for any file or controller state produced by upstream jobs.
2. Record `job.meta["jobs:<order>,..."]` for every child job so `job_info.py` and `cancel_job.py` can traverse the tree.
3. If you rely on filesystem writes inside a single job, prefer explicit file waits over fixed sleeps.
4. Update this catalog when adding new enqueue sites or dependency edges.
