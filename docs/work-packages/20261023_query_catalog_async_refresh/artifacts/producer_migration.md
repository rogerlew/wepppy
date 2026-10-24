# Producer migration disposition

Implementation evidence, 2026-10-23. The baseline inventory is [caller_matrix.md](caller_matrix.md). The producer changes use explicit `request_catalog_refresh` calls; they do not redefine or alias the synchronous compatibility API.

## Disposition by inventory row

| Baseline A or A/C row | Implemented disposition |
| --- | --- |
| Soils: symlink_soils_map, build_chile, _build_spatial_api, _build_gridded, dump_soils_parquet | Request after the existing artifact publication point. Atomic parquet publication, permissions and schema remain unchanged. |
| Landuse: symlink_landuse_map, _build_NLCD, _build_spatial_api, _build_fractionals, dump_landuse_parquet | Request after existing publication; direct model inputs remain available immediately. |
| Ron: fetch_dem, symlink_dem | Explicit requests; constructor activation remains synchronous. |
| Watershed: _peridot_post_abstract_watershed | Request; durable admission errors propagate. |
| Peridot: post_abstract_watershed, post_abstract_sub_fields | Request; four overlapping watershed notifications become one subtree notification. Offline migration remains synchronous. |
| Climate: run_prism_revision_build, run_prism_revision | Explicit requests after existing staged publication. |
| RAP acquire_rasters; RAP TS acquire/analyze | Explicit requests, including the module-bound collaborator calls. |
| Treecanopy acquire_raster; Shrubland acquire_rasters; Polaris acquire_and_align | Explicit requests. |
| OpenET analyze; SWAT run_swat_interchange; AshPost run_post | Explicit requests; readiness remains a separate finalizer/reader responsibility. |
| AgFields validate_field_boundary_geojson; skid trails walk_skid_trails | Required requests replace optional best-effort notification. |
| PathCE _refresh_catalog | Explicit request with a scope-relative directory; exceptions propagate. |
| Omni _refresh_catalog and all five artifact export / one state mixin transitive callers | Explicit request retaining `self.wd` and the existing relative artifact target; no parent-run substitution. |
| RUSLE _resolve_observed_rap, build | Supported assets request refresh. The README notification remains synchronous because Markdown is unsupported and the existing caller handles immediate rejection. A durable request for it would otherwise never succeed. |
| RUSLE K _resolve_optional_cfvo_layer_paths, run_rusle_k_factors; RUSLE C run_rusle_c_factor | Explicit requests; standalone mode remains synchronous through the public request API. |
| Hillslope and watershed interchange | Request after version-manifest publication; shared synchronous finalizers remain unchanged. |
| Return-period trailing entries | Retained synchronous pending family-specific integration proof, as agreed with the reader implementer. Initial activation remains a barrier. |

All B/C constructor, report, model-finalizer and migration calls outside these producer rows retain synchronous semantics. Asynchronous behavior remains disabled by default behind `QUERY_CATALOG_REFRESH_ENABLED`; managed roots and worker prerequisites must be configured before enabling it. Best-effort import/error wrappers were removed from converted paths so durable admission failure cannot be reported as success. Queue unavailability recovery belongs to the admission API.

## Artifact and regression evidence

- `tests/nodb/test_catalog_producer_refresh.py`: managed soils parquet readback and immutable receipt before enqueue; refresh publishes a discoverable catalog and acknowledges receipts; durable admission failure propagates after readable artifact publication; standalone soils remains synchronously discoverable.
- Existing soils provenance and permission tests now read the completed parquet inside the notification callback, proving publication order rather than only observing a renamed mock.
- Existing Peridot schema tests verify the single subtree request alongside generated parquet readback. Existing no-data AshPost, RUSLE, Polaris, climate staging and interchange tests retain their artifact assertions.
- First targeted run: 129 passed before a test-only obsolete optional callback (`None`) caused failure. Corrected it to an explicit callback. Remaining/new focused run: 33 passed. Together these cover all 162 selected tests.
- Additional RUSLE/Omni wrapper regression run: 32 passed.
- Ash transport README lint passed. Python compile checks and changed-file whitespace checks passed.

These tests are local container evidence. They do not replace NFS cross-host exclusion, production identity, native GIL responsiveness, or enabled full model workflow rollout gates. The default-disabled rollout preserves those requirements.
