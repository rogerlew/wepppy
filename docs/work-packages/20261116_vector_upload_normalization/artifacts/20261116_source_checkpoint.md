# M0 source checkpoint

Status: source review complete; execution/acceptance evidence pending.
Reviewer: independent `source_review` agent, 2026-11-16.
Source: `05e3450fa7d3b24572e65161100670ae542a6ea8` plus transferred planning docs.

Compared bytes of all shape-converter source files (excluding build/cache files)
and the receiving routes/controllers listed below with `/home/workdir/wepppy`.
They are identical. The task worktree contains the latest contract/package drafts;
shared uncommitted work has not been imported or modified by this review.

## Receiving boundary matrix

| Consumer | Browser and receiving boundary | Auth, scope, CSRF | Existing byte/extension policy |
| --- | --- | --- | --- |
| Roads | `templates/controls/roads_pure.htm:53`; `controllers_js/roads.js:1134`; Flask `routes/nodb_api/roads_bp.py:335` | `authorize_and_handle_with_exception_factory`; run context active root; request lifecycle Redis fence; global Flask CSRF; XHR supplies `X-CSRFToken` | Multipart `file`; `.geojson` only; 10 MiB; controller also enforces configured `max_upload_mb` (default 50) |
| AgFields | `templates/controls/ag_fields_pure.htm:135`; `controllers_js/ag_fields.js:1417`; `rq_engine/ag_fields_routes.py:606` | JWT `rq:enqueue`, `authorize_run_access(..., operation="act")`, `ag_fields` feature; active-job conflict guard; browser session-token bridge | Multipart `field_boundaries`; `.geojson`/`.json`; 10 MiB |
| Omni | `templates/controls/omni_contrasts_pure.htm:212`; `controllers_js/omni.js:2608,2731`; `rq_engine/omni_routes.py:1183,1224` | JWT `rq:enqueue`, run access, `omni_contrasts` feature; session-token bridge; common preparation for run and dry-run | Multipart `omni_contrast_geojson`; `.geojson`/`.json`; 100 MiB; optional when saved path supplied |
| Batch Runner | `routes/batch_runner/templates/batch_runner_pure.htm:179`; `controllers_js/batch_runner.js:1598`; `rq_engine/upload_batch_runner_routes.py:139` | JWT `rq:enqueue`, `batch_runner` feature and feature flag; bearer header; batch resolved by name | Multipart `geojson_file` or `file`; `.geojson`/`.json`; 30 MiB default and existing `BATCH_GEOJSON_MAX_MB` override |

Paths above are relative to `wepppy/weppcloud/` or `wepppy/microservices/` as
indicated. Server handlers do not establish format identity from MIME. Batch
retains the MIME string only as resource metadata. The browser accepts are hints.
Bearer rq-engine mutations do not require CSRF; CSRF belongs to the cookie-backed
session-token bridge. Roads remains under Flask CSRF. No auth change is needed.

## Validation, publication, reload and artifacts

| Consumer | Existing semantic behavior | Publication and reload | Next actual consumed/generated artifact |
| --- | --- | --- | --- |
| Roads | `Roads._validate_uploaded_geojson` (`roads.py:1080`) requires a nonempty FeatureCollection and LineString/MultiLineString types; validates/infer CRS in `set_uploaded_geojson` | Lifecycle mutation wrapper; copies to `roads/roads.uploaded.geojson`; locked NoDb path/hash/catalog/params update. Summary reload drives controller/map | `prepare_segments` reads staged canonical source and emits `wepp/roads/segments/roads.inslope.monotonic.geojson` and low points; actual paths are controller properties at `roads.py:594,598` |
| AgFields | `ag_fields.py:221` stages source, uses `gpd.read_file(..., ignore_geometry=True)`, requires literal `field_id`, reports duplicates without rejecting; **does not check polygon geometry** | Stages GeoJSON and attributes Parquet; locked replacements of `ag_fields/fields.WGS.geojson`, `rotation_schedule.parquet`, then NoDb fields; original basename retained. `/agfields/state` rehydrates browser | `rotation_schedule.parquet` attribute readback; `rasterize_field_boundaries_geojson` consumes canonical GeoJSON and emits DEM-aligned `field_boundaries.tif`; later `sub_fields/sub_fields.WGS.geojson` |
| Omni | `_prepare_omni_contrasts:658` stages in unique `_pups/omni/contrasts/_uploads/<uuid>/`; `_load_user_defined_gdf:1139` rejects empty, fills missing CRS with EPSG:4326 and transforms; **does not reject nonpolygons** | Both routes call `omni.parse_inputs` before building/reporting; saved path/name reload through template and NoDb collaborator. Run builds synchronously before enqueue; dry-run computes report without run enqueue | `contrasts/build_report.ndjson` records ordered feature index/label and selected Topaz IDs; subsequent contrast run inputs derive from this selection |
| Batch Runner | `WatershedCollection._load_geojson:344` verifies nonempty FeatureCollection; analysis computes bbox/property schema/checksum; `WatershedFeature.is_valid:121` checks structure, not polygon type | `save_upload_file` validates temporary sibling before replacement; then `register_geojson:1120` locks `_geojson_state` update and invalidates template validation. `get_watershed_collection:1155` reloads exact resource path | `BatchRunner` saves per-watershed `dem/target_watershed.geojson` (`batch_runner.py:612`), including `runid`/`index`, before downstream delineation |

All model paths above are relative to `wepppy/nodb/` and collection paths to
`wepppy/topo/watershed_collection/watershed_collection.py`. Upload helper ownership
is `wepppy/microservices/upload_boundary.py:319`; its callback receives a staged
sibling before destination replacement. Do not pass raw binary content to these
existing GeoJSON validators or unrestricted native readers.

## CRS and ordering implications

- Roads infers absent GeoJSON CRS using project/configured CRS. Explicit canonical
  CRS metadata or equivalent trusted input provenance must prevent reinterpreting
  converter-produced longitude/latitude using project units.
- AgFields' `fields.WGS.geojson` basename is historical: ingestion copies values,
  and rasterization infers CRS when the payload lacks explicit CRS
  (`ag_fields.py:413`). Preserve legacy GeoJSON behavior; normalized binary input
  must carry authoritative WGS84 context through this consumer.
- Omni uses source CRS when present, assumes WGS84 when absent, and reprojects to
  the hillslope dataset CRS. Feature order defines contrast index/labels; do not
  sort or explode multipart features during normalization.
- Batch `WatershedCollection._extract_epsg` reports explicit CRS or inferred
  EPSG:4326. `WatershedFeature.save_geojson` propagates CRS and feature properties;
  the generated `dem/target_watershed.geojson` must be reparsed to verify them.
- Shapefile equivalence fixtures must use DBF-representable property names/types;
  silently truncating arbitrary names is not an equivalent transformation.

## Confirmed implementation risks to resolve

1. **High — Omni failed replacement changes saved state before validation.** Both
   routes call `omni.parse_inputs` before `build_contrasts`/dry-run validation.
   Normalize and fully validate upload before this point. Failed conversion or
   receiving validation must leave the prior path/settings/artifact unchanged.
2. **Medium — claimed polygon validation does not exist in AgFields or Omni.**
   The package/user intent is polygonal inputs, but the retained source only
   validates attributes or loads a GeoDataFrame. Contract text must distinguish
   intended admission from current behavior and tests must exercise these checks.
3. **Medium — raw/staged content lifetime needs explicit treatment.** Roads
   retains `roads.upload.source.geojson` even on semantic failure; Omni stages
   before semantic validation. New raw binaries must remain private ephemeral
   request files; accepted canonical GeoJSON remains observable in workflow roots.
4. **Medium — preserve composite-operation boundaries.** AgFields performs two
   replacements before NoDb dump; Batch publishes before registration; Roads
   copies before its NoDb lock. Pre-validation failure safety is required, but do
   not claim transactional recovery for arbitrary later I/O failures without
   testing the NoDb composite-operation contract.
5. **Resolved decision, implementation pending — Batch polygons.** Apply the
   authorized Polygon/MultiPolygon gate to new upload admission before replacement.
   Do not tighten the shared collection constructor because saved-project reload
   also uses it. Current production call-site inventory finds direct constructor
   use in this upload route and `load_from_analysis_results`; tests/tools may also
   consume the public collection API.

## Evidence limits

This checkpoint records direct source/byte comparison, not browser or artifact
execution. Required hostile fixtures and format equivalence receipts remain in
M0–M5. The correctness matrix names those states without claiming they passed.
