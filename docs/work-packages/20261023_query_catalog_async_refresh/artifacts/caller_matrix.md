# Catalog caller and consumer disposition

Analysis baseline: `fc3234efc6da58ff1da896dfab5b2dd5875988c2`, 2026-10-23 UTC. Three read-only agents inspected direct calls, aliases, transitive wrappers, readers and queue precedent. This is migration evidence, not runtime conformance.

## Producer inventory

79 direct/aliased invocations across 41 production Python files: 63 update calls, 13 activations, three finalizer helper calls. Six additional transitive `_refresh_catalog` calls are listed separately. Paths below are relative to `wepppy/`. Line references describe this baseline, not permanent API identifiers.

A: async-preferred candidate after artifact publication, with downstream barrier retained. B: synchronous freshness/completion barrier. C: offline/compatibility, synchronous by default. A/C means choose explicitly at the managed orchestration boundary; reusable scientific code must not gain an implicit Redis requirement.

| File:function | Baseline call lines | Class and disposition |
| --- | --- | --- |
| `nodb/core/soils.py`: symlink_soils_map, build_chile, _build_spatial_api, _build_gridded, dump_soils_parquet | 708, 761, 1113, 2036, 2341 | A; incident priority. Direct model inputs remain synchronous artifacts. |
| `nodb/core/landuse.py`: symlink_landuse_map, _build_NLCD, _build_spatial_api, _build_fractionals, dump_landuse_parquet | 1091, 1161, 1227, 1436, 2459 | A; direct management preparation retained. |
| `nodb/core/ron.py`: fetch_dem, symlink_dem | 584, 893 | A; DEM discovery notification. |
| `nodb/core/ron.py`: __init__ | 294 | B/C; activation precedes ON_INIT_FINISH; constructor supports offline use. |
| `nodb/core/watershed.py`: _peridot_post_abstract_watershed | 1325 | A; consumer barriers retained. |
| `topo/peridot/peridot_runner.py`: post_abstract_watershed, post_abstract_sub_fields | 521–524, 619 | A; coalesce overlapping watershed paths. |
| `topo/peridot/peridot_runner.py`: migrate_watershed_outputs | 827–832 | C; no worker requirement for migration. |
| `nodb/core/climate_observed_build.py`: run_prism_revision_build | 256 | A; finalized climate artifacts first. |
| `nodb/core/climate_build_helpers.py`: run_prism_revision | 1170 | A; preserve staged publication. |
| `nodb/mods/rap/rap.py`: acquire_rasters | 190 | A. |
| `nodb/mods/rap/rap_ts_build.py`: acquire, analyze | 136, 183 | A; module-bound alias. |
| `nodb/mods/treecanopy/treecanopy.py`: acquire_raster | 121 | A. |
| `nodb/mods/shrubland/shrubland.py`: acquire_rasters | 213 | A. |
| `nodb/mods/polaris/polaris.py`: acquire_and_align | 489 | A. |
| `nodb/mods/openet/openet_ts.py`: analyze | 549 | A; report readiness separate. |
| `nodb/mods/swat/swat.py`: run_swat_interchange | 795 | A; task readiness separate. |
| `nodb/mods/ash_transport/ashpost.py`: run_post | 305 | A; task readiness separate. |
| `nodb/mods/ag_fields/ag_fields.py`: validate_field_boundary_geojson | 307 | A; audit existing best-effort wrapper. |
| `nodb/mods/skid_trails/skid_trails.py`: walk_skid_trails | 360 | A; audit existing best-effort wrapper. |
| `nodb/mods/path_ce/path_cost_effective.py`: _refresh_catalog | 679 | A; transitive call at 653. |
| `nodb/mods/omni/omni.py`: _refresh_catalog | 861 | A; exact child scope, not parent runid. |
| `nodb/mods/rusle/rusle.py`: _resolve_observed_rap, build | 664, 952, 963, 972, 1004, 1017, 1030, 1082 | A; direct raster/manifest consumers. |
| `nodb/mods/rusle/k_integration.py`: _resolve_optional_cfvo_layer_paths, run_rusle_k_factors | 552–553, 849, 898–899 | A/C; managed build opt-in. |
| `nodb/mods/rusle/c_integration.py`: run_rusle_c_factor | 661, 695, 800, 851 | A/C; standalone retained. |
| `wepp/interchange/hill_interchange.py`: run_wepp_hillslope_interchange | 250 | A/C; shared finalizer barrier. |
| `wepp/interchange/watershed_interchange.py`: run_wepp_watershed_interchange | 174 | A/C; shared finalizer barrier. |
| `wepp/reports/return_periods.py`: refresh_return_period_events trailing entries | 660, 665; fallback 662, 667 | A candidate for these notifications only; ReturnPeriodDataset reads staged files via PyArrow. |
| `wepp/reports/return_periods.py`: refresh_return_period_events initial activation | 475 | B; immediately resolves catalog context at 476. |
| `wepp/reports/helpers.py`: ReportQueryContext.ensure_datasets | 74, 87 | B; reloads and checks membership immediately. |
| `nodb/mods/geneva/collaborators/hru_event_measure_service.py`: query_rows | 253 | B; membership check and query follow immediately. |
| `query_engine/context.py`: resolve_run_context | 126 | B; loads catalog immediately. |
| `query_engine/app/server.py`: activate_run | 945 | B; returns actual filtered catalog. |
| `query_engine/app/mcp/router.py`: activate_run_endpoint | 1028 | B; activation_job response actually says completed. |
| `weppcloud/routes/weppcloudr.py`: _ensure_interchange | 401 | B; run_interchange=True prepares scientific outputs before rendering. |
| `rq/wepp_rq_stage_post.py`: _post_watershed_interchange_rq | 362 | B; ACTIVATED and COMPLETED follow refresh. |
| `nodb/wepp_nodb_post_utils.py`: activate_query_engine_for_run | 173 | B/C; shared finalizer. |
| `nodb/batch_runner.py`: run_batch_watershed | 812 | B/C; shared finalizer caller. |
| `rq/culvert_rq.py`: _process_culvert_run | 1540 | B; completed metadata requires readiness. |
| `nodb/mods/roads/roads.py`: _regenerate_roads_report_resources | 3785 | B; Roads currentness and report resources. |
| `tools/migrations/soils.py`: migrate_soils_parquet | 145 | C. |
| `tools/migrations/landuse.py`: migrate_landuse_parquet | 141 | C. |
| `tools/migrations/unroll_root_resources_batch.py`: _refresh_query_catalog_entry | 469 | C. |
| `tools/migrations/interchange.py`: refresh_query_catalog | 201 | C; query_catalog step after interchange, before redis_cache. |
| `query_engine/activate.py`: update_catalog_entry absent-catalog branch | 282 | Internal delegation; preserve synchronous primitive. |

Indirect inventory: `query_engine/__init__.py` forwards return values; `rq/wepp_rq.py:470` injects stage-post activation; climate calls `helpers.update_catalog_entry`, RAP TS calls `module.update_catalog_entry`. `_update_catalog_entry` aliases occur in Peridot, AgFields, skid trails, PathCE, Omni and interchange. Omni calls `_refresh_catalog` from `omni_state_contrast_mixin.py:163` and `omni_artifact_export_service.py:485,608,666,708`; PathCE calls it at 653. No non-test Python matches outside `wepppy` were found in the baseline search.

## Reader and lifecycle inventory

| Surface | Evidence | Disposition / required acceptance |
| --- | --- | --- |
| Core catalog loading | `query_engine/catalog.py:DatasetCatalog.load`, `load_catalog`; `context.py:resolve_run_context` | Retain fresh context/barrier; absent/corrupt auto-activation cannot silently become false missing-run. |
| SQL planning | `core.py:build_query_plan`, `_dataset_source_sql`, `_apply_identifier_aliases`, `_spatial_geometry_alias` | Validate selected fs_path, schema and aliases; stale catalog can alter executed results. |
| HTTP query | `app/server.py:run_query_endpoint` | Preserve dataset/route authorization and Roads admission before query/refresh. |
| HTTP listing/schema | `server.py:run_info`, `run_schema`, `make_query_endpoint` | Future async reader candidates only after additive pending/stale UX contract and tests. |
| MCP reads/validation | `app/mcp/router.py:_load_catalog_data`, `_load_catalog_metadata`, `get_catalog`, `_prepare_query_request` | Preserve 404 catalog_missing, 500 catalog_invalid, 422 dataset_missing distinctions until explicitly amended; pending cannot masquerade as missing. |
| Report context | `wepp/reports/helpers.py:ReportQueryContext.activate`, `ensure_datasets`, `_context` | Explicit barrier and reload; disk publication does not refresh memoized object. |
| Landuse report cache | `average_annuals_by_landuse.py:_observe_inputs`, `_normalize_report_context` | Preserve dependency identity, fresh selection check and historical archived report availability. |
| Return-period preparation | `return_periods.py:refresh_return_period_events`, ReturnPeriodDataset | Initial barrier retained; trailing updates candidate only; actual direct-read evidence controls over broad module classification. |
| Completed Omni choices | `weppcloud/routes/nodb_api/return_period_scenarios.py:completed_return_period_scenarios` | Read-only discovery must not schedule preparation; finalizer must provide readable catalog. |
| GL flow duration | `weppcloud/routes/gl_dashboard_flow_duration.py:_source_status` | Preserve exact root/unique path checks and reload-required stale session behavior. |
| Storm event analyzer | `query_engine/storm_event_analyzer.py` dataset/field/column helpers | Query barrier; no stale alias/column substitution. |
| WEPPcloudR / model finalizers | B rows above | Existing completion and interchange generation retained; never wait for a child queued behind sole occupied batch worker. |
| Combined viewer preparation | `weppcloud/combined_viewer_preparation.py:prepare`, `rollback` | Direct catalog writer via staging/os.link and manifest-owned deletion; exclude generic async conversion. Preserve explicit READONLY offline exception and hash-owned rollback. |
| Fork cache deletion | `rq/project_rq_fork.py:_clear_query_engine_catalog_cache`; facade `project_rq.py` | Missing destination catalog is expected. Invalidate copied incarnation; schedule only after destination publication. |
| Archive / restore | `rq/project_rq_archive.py:archive_rq`, `restore_archive_rq` | Catalog is archived; coordinate publication with tree replacement, preserve diagnostics and fence old jobs. |
| Delete / recreate / READONLY | Existing lifecycle admission and `activate.py:_raise_if_readonly` | Old worker cannot recreate or replace scope; recheck authority at publication under shared lifecycle exclusion. |
| Nested scopes | `context.py:_resolve_scenario_dir`, `activate.py:_find_parent_run_root`, `_canonicalize_nodir_parquets` | Separate exact scenario/batch/pup owners, preserve authorized parent fallback. |

Direct production catalog access outside `activate.py`: readers `catalog.py`, MCP router, GL flow-duration route; readability probes landuse report and return-period scenario route; writer/deleter combined-viewer preparation; deleter fork helper. Archive/restore copies catalog as ordinary project payload. No persistent global query-result cache found; held RunContext/report contexts require freshness handling.

## Migration waves and acceptance

1. Infrastructure prerequisite: durable intent/admission/recovery, atomic coordinated publishers, stable external lifecycle guard, status inspection and targeted receipt/source-aware synchronous barriers (existing missing-entry checks alone are insufficient). Include recurring source reconciliation for receipt-free crash gaps and native GIL release for retained web scans. Prove actual NFS locking and no deadlocks before any producer conversion.
2. Incident wave: soils/landuse/DEM/watershed managed producers. Core scientific/offline execution retains explicit sync mode; verify each UI task and immediate reports, model inputs and finalizer.
3. Managed climate/modules/interchange and nested Omni: family-specific artifact/readback tests, directory deletion, child scope and finalizer coverage. A classification is permission to evaluate migration, not proof that runtime workflow passes.
4. Optional external reader/API changes (internal freshness checks are prerequisite wave 1): separately ratified pending/ready transport and UX. No broad reader conversion in initial implementation scope.

Public API tests preserve dict/None/full-catalog returns and immediate on-disk readback (`tests/query_engine/test_activate.py`, server/MCP tests). Geneva, WEPP stage-post, batch/culvert/Roads tests preserve readiness order. Existing mocked update calls must be replaced with meaningful artifact/ordering checks, not merely renamed mocks. Real Redis, filesystem and production-equivalent workflow evidence are mandatory for changed boundaries.

## Reconciled analysis findings

Reader analysis initially grouped all return-period refresh work as a barrier. Writer inspection distinguished the initial activation from trailing metadata notifications; the table preserves this distinction. Queue review confirmed WATCH conflict is not durable acceptance, and Redis-only dirty state cannot guarantee recovery after loss. The canonical draft uses durable receipt-set acknowledgment and recoverable discovery instead of blindly copying WMesque's boolean admission result.
