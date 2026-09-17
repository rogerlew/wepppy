# M1 independent correctness inventory

Reviewer: `freshness_correctness`; baseline revision
`adb4f9b004459fc578460a95f30ac01ae1421f36`. Scope: the non-postfire seed consumers,
their callers, producers, existing tests and current domain contracts. This is
an independent contribution to the repository-wide inventory, not a claim that
all maintained code has been audited. No production implementation was changed.

## Evidence and severity

Replay:

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/m1_correctness_probe.py > docs/work-packages/20260916_file_dependency_freshness/artifacts/m1_correctness_probe.json
```

The retained script uses real files on the repository bind mount, production
Python functions, GDAL writes and the installed native SBS summarizer. Container
identity was UID 1000, GID 993, supplementary GID 993. All mutations were in a
disposable directory. D-Tale is explicitly a predicate-only AST extraction:
its route and separate service were not exercised. No named project was changed.
The small SBS fixture has no projection; its class-count cache result still
demonstrates stale reuse, but acceptance must also exercise valid projected maps.
Representative-size, NFS, concurrent-reader and restart/UI acceptance remain open.

P1 below means stale scientific data or mixed-generation publication is possible;
P2 means stale presentation or redundant work. “Confirmed mechanism” means a
real helper/cache reproduction, not an end-to-end claim about an ordinary writer.

## Findings and consumer dispositions

| ID | Consumer and actual callers | Mechanism, impact and disposition | Writers / current owner / regression anchors |
| --- | --- | --- | --- |
| C01, P1 | `wepppy/nodb/_derived_build.py:file_signature`; `climate_observed_build._spatial_inputs/_check_inputs/run_prism_revision_build`; `mods/rap/rap_ts_build._inputs/_check_inputs/analyze` | `(resolved path, mtime_ns, size)` captures scientific input identity outside a lock, then compares inside finalization. Equal-size in-place rewrites with restored mtime leave identity unchanged (probe confirmed), permitting stale/mixed collected state. A metadata-only touch instead rejects equivalent input. **Open confirmed mechanism.** Signature is transaction-local, not persisted schema. | Climate builders and RAP raster acquisition; subwta/MOFE producers in Watershed. Owner: NoDb persistence contract, derived-builder finalization section. `tests/nodb/test_batch_climate_rap_contention.py` tests changed content with deliberately advanced mtime, missing source and rollback, but not restored-time mutation. |
| C02, P1/P2 | `mods/features_export/dependency_tracker.py:build_dependency_snapshot/_build_entry_for_relpath/dependency_fingerprint`; `service.prepare_export_submission` | Service always uses default `content_hash_mode="none"`. Persisted dependency entry equality is relpath/existence/size/mtime, so restored-time changes collide. Configurable SHA-256 sees byte changes, but mtime remains in fingerprint: unchanged bytes plus touch produces another cache key (both reproduced). Hash loop lacks before/after coherence checks. **Open confirmed mechanism; concurrency risk inspected, not reproduced.** | Source parquet/geometry/NoDb producers; unitizer preferences. Owner: `mods/features_export/specification.md`, “Dependency fingerprint” and WP-2 contracts. `tests/nodb/mods/test_features_export_dependency_tracker.py`, `test_features_export_service.py`, `test_features_export_cache_key.py`. Any fix changes persisted export cache/manifest identity; decide old-reader/new-writer behavior first. |
| C03, P1 | `core/landuse.py:_mofe_pair_count_file_signature/_build_mofe_pair_count_signature/build_managements` | Cached native pair counts are reused on two raster metadata signatures plus a semantic digest of MOFE key structure. Changed pixels with restored mtime preserve signatures (reproduced); management area/coverage can therefore use old pair counts. `_mofe_pair_count_cache_signature` and cached counts are object fields that may serialize in `landuse.nodb`. **Open confirmed mechanism.** | Watershed subwta/MOFE builders; explicit invalidation paths in Landuse. NoDb persistence/domain Landuse documentation own compatibility. `tests/nodb/test_landuse_coverage_area_source.py:test_build_managements_multi_ofe_pair_count_cache_miss_on_signature_drift` mocks the signature; it does not cover real preserved-time writes. |
| C04, P1 | `mods/baer/sbs_map.py:_summary_cache_key/_summarize_sbs_raster_cached/_summarize_sbs_raster`; `SoilBurnSeverityMap` | Eight-entry process LRU uses pathname/mtime/size. Real 152-byte GeoTIFF changed from six class-1 cells to six class-2 cells, preserving mtime/size; cached native summary remained class 1, direct native summary returned class 2. **Open confirmed stale-data defect.** Include external `.msk`/`.aux.xml` when native reader consumes them; that closure is not currently present and requires separate proof. | GDAL writes/upload/BAER and disturbed preparation. Owners: BAER/disturbed module docs and SBS native/display contracts. `tests/nodb/mods/baer/test_sbs_native_required.py`, `test_sbs_coverage_mask.py`, `tests/sbs_map/test_sbs_map.py`. Existing tests preserve source masks/export failure behavior, not cache freshness. |
| C05, P1 | `mods/geneva/collaborators/hru_map_geometry_service.py:_is_cache_stale/_ensure_feature_collection_artifact/query_feature_collection` | GeoJSON is reused when both raster and legend mtimes precede output. Restored-time content changes remain accepted (predicate reproduced). Main raster and legend are correctly named dependencies; native raster mask/georeferencing sidecars need closure review. **Open confirmed mechanism.** | Geneva HRU preparation writes map/legend; geometry service writes GeoJSON. Owner: `mods/geneva/specification.md` HRU map features. `tests/nodb/mods/geneva/test_geneva_hru_map_geometry_service.py` covers cache availability/materialization but no byte-identity regression. |
| C06, P1 | `mods/geneva/collaborators/hsg_assignment_service.py:_is_current_auto_burn_artifact/_materialize_auto_burn_severity` | Reuses aligned burn raster based only on target newer than burn source and bound raster. Equal-size/restored-time source changes accepted (predicate reproduced). Source pathname can also change to an older different raster without invalidation because provenance is not recorded. **Open confirmed mechanism.** | `raster_stacker` produces aligned artifact; disturbed chooses `sbs_4class_path` or cropped SBS. Owner: Geneva specification HSG/input binding. Need service regression for source-path changes, boundary masks and same-byte replacement. |
| C07, P1 | `mods/omni/omni_contrast_build_service.py:_is_stale/_stream_order_needs_prune` and downstream generated-path checks | Compares generated file mtime to RedisPrep `build_subcatchments` completion time. This is a **completion-order approximation used as dependency freshness**, not intrinsically safe scientific identity. Direct source changes without completion updates remain unobserved (predicate confirms comparison has no source input). An ordinary subcatchment rerun advances the marker and rebuilds. **Open risk; must trace supported writers before claiming ordinary workflow defect.** | WBT pruning source set includes flovec/netful/relief/chnjnt/bound/subwta/outlet, with TIF or VRT selection. Owner: Omni README stream-order pruning and orchestration contracts. `tests/nodb/mods/test_omni_contrast_build_service.py`. Preserve build-completion sequencing; file hash must not replace orchestration state. |
| C08, P1 | `wepp/reports/hillslope_watbal.py:_source_is_newer_than_cache/__init__/_write_native_summary` | Source-newer comparison misses restored-time H.wat changes (predicate reproduced). Version-only sidecar lacks source identity. Report also uses Watershed translator and optional Roads manifest, neither currently in freshness key. **Open confirmed mechanism; dependency omission needs full report demonstration.** | Native H.wat interchange and compact summary producers; watershed mappings; roads manifest. Owner: `docs/schemas/output-scope-contract.md#hillslope-water-balance-summary-cache`. `tests/wepp/reports/test_hillslope_watbal.py`. Preserve nullable schema, baseline/Roads isolation, native producer and mapping semantics. |
| C09, P1 | `wepp/reports/average_annuals_by_landuse.py:AverageAnnualsByLanduseReport.__init__`; `helpers.ReportCacheManager` | Cache hit uses version and exact columns only; no identity for loss, hillslopes or landuse parquet. A schema-compatible cache can outlive any source update. Repository search found reports-cache removal only in `rq/project_rq_fork.py:_clear_reports_cache`, not ordinary source writers. **Open confirmed code-level omission; native end-to-end baseline still required.** | Interchange loss, Watershed and Landuse parquet producers. Owner: reports README “Average Annuals by Landuse” (its stated cache location is also stale), output-scope contract when applicable. `tests/wepp/reports/test_average_annuals_by_landuse.py` tests building and reuse, not input updates. |
| C10, P2 | `weppcloud/utils/assets.py:resolve_controllers_gl_build_id` | Header extraction result cached by pathname/mtime/size. A same-length next-day build-date rewrite with restored mtime returns the old ID (real callable reproduced), masking stale-client detection. **Open confirmed stale-cache defect under restore/deploy metadata preservation.** | `controllers_js/build_controllers_js.py` generates the build header. Owner: controller build/version UX documentation. `tests/weppcloud/utils/test_assets_controllers_gl_build_id.py` covers extraction/absence only. Header-only read cost differs substantially from large-file hashing. |
| C11, P1/P2 | `webservices/dtale/dtale.py:_fingerprint`, `_register_geojson`, `/internal/load` | Dataset and GeoJSON fingerprints are `mtime_ns:size`; restored-time changes collide (production predicate extracted/reproduced). Eager frame retains old rows; lazy parquet may retain old schema/count metadata while later reads see current file. **Open confirmed predicate defect; actual D-Tale service route proof required.** | User/run parquet/CSV/Feather/pickle and geospatial producers. Owner: `webservices/dtale/AGENTS.md`, lazy-parquet contract and README. `tests/microservices/test_browse_dtale.py` primarily covers integration/auth redirect surface. Preserve internal token, path containment, limits and bounded lazy reads. |

## Legitimate metadata and compatibility boundaries

1. `_derived_build._identity` is rollback ownership/race protection, including
   device/inode identity. Do not replace it with byte-equivalence equality:
   rollback must not overwrite a concurrently replaced artifact merely because
   the bytes match. Missing ctime creates a separate potential restored-time
   in-place race blind spot; preserve or strengthen this guard independently.
2. `runtime_paths/fs.py` stat/list entries expose transport/display metadata.
   `resolve` now returns directory form with `archive_fp=None`; archive-backed
   runtime access raises `NODIR_ARCHIVE_RETIRED`. These are **nondependency**
   consumers. Preserve path containment and symlink checks; stale archive docs
   cannot justify adding a new runtime extraction/cache mechanism here.
3. `config_builder/registry.py:_executable_sha256` already keys cached hashes by
   resolved path/inode/size/mtime/ctime, then returns SHA-256 as identity.
   Metadata churn triggers recomputation rather than false scientific staleness.
   **Verified safe for sequential POSIX metadata operations by inspection**;
   before/after hash race validation and device identity are residual gaps.
   Keep execute/read access validation ahead of cache reuse. Owner:
   `docs/schemas/project-owned-config-contract.md` binary identity.
4. NoDb `_nodb_mtime/_nodb_size` serve disk-authority cache refresh **and stale
   write rejection**, not ordinary scientific content signatures. Canonical
   writers guarantee atomic replace and monotonic mtime for same-size changes.
   That makes their metadata key justified under their explicit writer contract;
   out-of-band restored-time replacement is a separate reconciliation question.
   Do not remove stale-write gates or silently bless a hash-matching unauthorized
   writer. Owner: NoDb persistence/concurrency contract §§ Cache Refresh,
   Persistence, Monotonic Signature Enforcement.
5. Landuse file-size stabilization loops near `_wait_for_*` are readiness/read
   coordination, not durable dependency equality. Their limitation is producer
   completion/coherent-read evidence, not hard-link ctime false staleness.
6. Hillslope water-balance missing source does **not** automatically justify
   rejecting legacy cache: `test_hillslope_watbal_uses_cache` explicitly supplies
   only the legacy cache. The current output-scope contract retains baseline
   legacy reads. Ratify compatibility before changing this established workflow.
7. Features-export catalog identity includes metadata/version, not the entire
   catalog. Layer-definition changes without version advancement are a separate
   release-governance question; do not assume hashing only files closes it.

## Required implementation constraints and follow-up acceptance

- Do not make every status read hash every large raster. Separate digest cache
  invalidation hints from persisted accepted-content equality; measure actual
  working-set size as well as one-file warm performance.
- Include dependency closure: raster masks/auxiliary georeferencing, VRT source
  members, shapefile sidecars, translator and Roads mappings, source path and
  selected configuration where consumed. Same bytes at a different authorized
  source are not automatically equivalent provenance.
- Before persisted changes, specify old signatures, absent/empty optional files,
  schema/version bumps, cache misses, rollback, and generated-artifact effects.
- A digest comparison does not ensure a coherent read/publication snapshot.
  Capture metadata/identity before and after reads and retain the existing
  locks/rechecks at publication. Cross-file dependency snapshots need explicit
  consistency limits; unbounded retries are not an acceptable hidden fallback.
- Baselines above justify further bounded tests, not closure. Reproduce actual
  callable scientific results for C01/C02/C03/C05/C06/C08/C09/C11 before fixing
  them; demonstrate ordinary and restored-time producer paths and archive/restore
  on isolated copies. C04 already has a native scientific-summary reproduction.
- Main discovery must include completion timestamps, cache existence/schema-only
  hits, content-hash caches, and sidecars; timestamp grep alone misses C09.
