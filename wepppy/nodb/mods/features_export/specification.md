# Features Export Specification

Status: Implementation In Progress  
Owner: WEPPpy NoDb export subsystem  
Primary module: `wepppy/nodb/mods/features_export`  
Replaces: `wepppy/export/gpkg_export.py`
Document posture: Living working specification; mutate when implementation evidence shows a better contract or exposes gaps.

## 1. Summary
Create a NoDb `features_export` mod for user-configurable spatial and spatial-temporal exports across WEPP, Omni, Ash/WATAR, WEPP interchange, SWAT interchange, and AgFields datasets.
This is an immediate replacement for legacy gpkg/gdb export behavior, but implemented with NoDb controller patterns, canonical RQ polling contracts, and dependency-aware cache reuse.
AgFields support is parity+ (spatial + WEPP interchange metrics), including automatic on-demand AgFields interchange generation when required for requested export layers.

## 2. Supported Formats
- `geojson` (single-layer format)
- `geoparquet` (single-layer format)
- `kmz` (single-layer format)
- `geopackage` (multi-layer container format)
- `geodatabase` (multi-layer FileGDB container via `f_esri`)

Format token contract:
- Canonical request token is `geodatabase`.
- Backward-compatible alias `f_esri` is accepted and normalized to `geodatabase`.
- FileGDB download artifact filename extension is `.gdb.zip`.

Packaging rules:
- Single-layer formats produce one file per resolved layer and return a zip bundle.
- Multi-layer formats produce one container artifact per request.
- KMZ is single-layer only; multi-layer requests produce multiple `.kmz` files in the zip.

## 3. Layer Catalog And Discoverability
The backend owns an authoritative, versioned export layer catalog.
GL Dashboard taxonomy and discoverability are used as a blueprint, but export contracts are backend-defined and independent of frontend module internals.

Catalog source of truth:
- Machine-readable catalog file: `wepppy/nodb/mods/features_export/layer_catalog.yaml`.
- Catalog header block lives under `metadata` and includes versioning/compatibility fields.
- Runtime layer discovery for export/UI must read from `layer_catalog.yaml`, not hardcoded layer maps.

Catalog contract:
- Top-level keys:
- `metadata`: catalog metadata/version header block.
- `layers`: array of layer definitions.
- `metadata` minimum fields:
- `catalog_version`
- `schema_version`
- `updated_at_utc`
- `owner`
- `status` (`draft|active|deprecated`)
- `resolver_contract` (allowed locator kinds and template-variable contract)
- Layer definition minimum fields:
- `layer_id`
- `family`
- `scope_class` (`scope_aware|scope_invariant`)
- `geometry` contract (`type`, locator, feature-id metadata; geometry locator participates in readiness and dependency fingerprinting)
- `join` contract (`primary_key`, optional `fallback_keys`, optional `source_key_map`)
- `sources` datapaths (direct data sources used to build the layer)
- `dependencies` (additional files that must participate in readiness/fingerprint checks)
- `temporal` options (`supported_modes`, `grain`, `time_columns`, `mode_rules`)
- `measures.required` and `measures.optional`
- SWAT table-profile contract for `swat.interchange.*` layers (`table_profiles`, profile-level geometry/join rules, non-spatial behavior)
- Optional measure availability rules (`requires_any_column`, `requires_all_columns`, version gates, selector constraints)
- Version-gate semantics: `min_source_version` is a semantic version string compared against the resolved dependency manifest `version` field (for example `interchange_version.json.version`).
- Missing optional measure behavior (`warn` with `measure_unavailable`)

Locator contract (strict):
- Every `geometry.locator`, `sources[*].locator`, and `dependencies[*].locator` uses exactly:
- `kind`: one of `nodb_ref|relpath|path_template`
- `value`: locator value string
- Locator aliases such as `path`, `path_ref`, `path_template`, or `source_ref` are not allowed.
- `path_template` expansion variables are defined in `metadata.resolver_contract.path_template_vars`.

Initial layer families:
- Watershed: subcatchments, channels.
- Landuse: dominant class and coverage attributes.
- Soils: dominant class and physical properties.
- Ash/WATAR: hillslope ash transport outputs.
- AgFields spatial: field boundaries and sub-field polygons.
- AgFields WEPP metrics: sub-field/field metrics sourced from `wepp/ag_fields/output/interchange/*`.
- WEPP summary: runoff, subrunoff, baseflow, soil loss, sediment yields.
- WEPP temporal: yearly and event layers.
- Omni scenarios: `_pups/omni/scenarios/*`.
- Omni contrasts: `_pups/omni/contrasts/*`.
- WEPP interchange: interchange-backed export layers/tables.
- WEPP interchange includes hillslope element exports (`H.element.parquet`) with optional runoff-partition measures `QRain` and `QSnow`.
- SWAT interchange: `swat/outputs/run_*/interchange/*`.

## 4. Output Scope Contract Alignment
`output_scopes` is an array selector with values `baseline|roads`.
Default is `["baseline"]`.

Scope resolution must follow the canonical output-scope contract:
- Only datasets rooted at `wepp/output` are scope-rewritten for `roads`.
- Paths outside `wepp/output` remain unchanged for both scopes.
- Scope values are normalized case-insensitively to canonical lowercase.
- Duplicate scopes are deduplicated before execution and cache-key hashing.
- Invalid scope values fail with 400; silent fallback is forbidden.
- Catalog `scope_root` token mapping is fixed to `baseline=output` and `roads=roads/output`.

Layer scope classes:
- Scope-aware layers: WEPP summary, WEPP temporal, WEPP interchange layers rooted at `wepp/output`.
- Scope-invariant layers: watershed, landuse, soils, ash/watar, AgFields, Omni, SWAT interchange, and any layer not rooted at `wepp/output`.

Export behavior:
- Scope-aware layers are emitted separately per requested scope using `{scope}__{layer_id}`.
- Scope-invariant layers are emitted once using `shared__{layer_id}` even when both scopes are requested.
- If one requested scope is missing for a scope-aware layer, export available scopes and emit warning code `scope_missing_layer`.
- If a requested scope is not applicable to a scope-invariant layer, emit warning code `scope_not_applicable`.
- If no layer resolves after scope processing, return 404.

## 5. API Contract (rq-engine)
### 5.1 Submit Export Job
`POST /api/runs/{runid}/{config}/export/features`

Auth contract:
- Submit and download endpoints require `rq:export` plus run-access authorization.
- Polling auth follows canonical `/rq-engine/api/jobstatus` and `/rq-engine/api/jobinfo` route policy; `features_export` does not introduce route-specific polling auth overrides.

Transport contract:
- Request body is `application/json` only.
- Unsupported content type (including `multipart/form-data`) is rejected with 415.
- Missing JSON body, empty JSON body, or query-only submissions are rejected with 400 validation errors.
- This avoids `FormData` list-collapsing ambiguity in shared payload parsing.

Request schema:
- `format`: required enum from Section 2.
- `units`: required enum `si|english|project`.
- `crs`: optional enum `wgs|utm`, default `wgs`.
- `layers`: required non-empty array of layer IDs.
- `output_scopes`: optional non-empty array of `baseline|roads`.
- `scenario`: optional Omni scenario selector.
- `contrast_id`: optional Omni contrast selector.
- `swat_run_id`: optional SWAT run selector, default `latest`.
- `swat_tables`: optional object with one of `include` or `exclude`, each an array of table names.
- `temporal`: optional object.
- `temporal.mode`: optional enum `annual_average|yearly|event`.
- `temporal.year_selection`: optional enum `all|exclude_first|exclude_first_two|exclude_first_five|custom`.
- `temporal.exclude_yr_indxs`: optional array of zero-based integer indices.
- `temporal.event`: required when `temporal.mode=event`.
- `temporal.event.selector`: enum `date|return_period`.
- `temporal.event.dates`: required for `selector=date`; array of `YYYY-MM-DD`.
- `temporal.event.return_periods`: required for `selector=return_period`; numeric array in years.

Request example:
```json
{
  "format": "geoparquet",
  "units": "project",
  "crs": "wgs",
  "layers": ["wepp.summary.hillslopes", "watershed.subcatchments"],
  "output_scopes": ["baseline", "roads"],
  "swat_run_id": "latest",
  "temporal": {
    "mode": "annual_average",
    "year_selection": "exclude_first_two",
    "exclude_yr_indxs": [0, 1]
  }
}
```

Validation:
- `scenario` and `contrast_id` are mutually exclusive.
- Omni scenario and Omni contrast layer families cannot be mixed in one request.
- Omni scenario layers require `scenario`.
- Omni contrast layers require `contrast_id`.
- SWAT layers require a resolved `swat_run_id`; `latest` is resolved to a concrete run ID before execution and persisted in manifest/cache key.
- Unknown layer IDs return 400.
- Unsupported `crs` value returns 400.
- Unsupported temporal mode returns 400.
- Daily timeseries mode is not supported and returns 400.
- `swat_tables.include` and `swat_tables.exclude` are mutually exclusive.
- `crs=utm` requires a resolvable run UTM CRS; unresolved UTM CRS returns 409.
- AgFields WEPP metric layers require AgFields output/interchange assets; exporter performs on-demand preparation as defined in Section 6.3.
- Temporal mode support is evaluated per resolved layer from catalog `temporal.supported_modes`.
- If some layers are incompatible with requested temporal settings and at least one layer remains exportable, incompatible layers are dropped with `layer_unavailable` warnings.
- If no requested layers support the requested temporal settings, return 400.
- If `year_selection` or `exclude_yr_indxs` is provided for a layer whose catalog rule sets `year_selection_supported=false`, ignore those selectors for that layer and emit `selector_defaulted`.
- Missing required datasets return 404 only when nothing exportable remains.
- If at least one requested export target resolves, unresolved requested layers/tables are emitted as warnings and do not fail the job.
- Unsupported format dependency returns 409.

CRS behavior:
- `crs=wgs` exports spatial layers in EPSG:4326.
- `crs=utm` exports spatial layers in the run-resolved UTM CRS (single resolved EPSG per job).
- Non-spatial layers are unaffected by CRS selection.

Submission response:
- Always HTTP 202 with canonical async payload.
- Required key: `job_id`.
- Required `status_url` points to `/rq-engine/api/jobstatus/{job_id}`.
- Optional `download_url` may be present but is only valid once the job is `finished`.
- Cache hits still return 202 with a new `job_id` (fast-path job), never sync 200.

### 5.2 Polling And Result Contract
Polling is canonical RQ polling:
- `GET /rq-engine/api/jobstatus/{job_id}`
- `GET /rq-engine/api/jobinfo/{job_id}`

Status semantics:
- Success terminal state is `finished`.
- Failure terminal states from job payload are `failed|stopped|canceled`.
- Job/status lookup misses are HTTP 404 error responses with `error.code="not_found"`.
- Feature export does not define alternate terminal names like `completed`.

Warnings and summaries:
- `jobstatus` keeps canonical fields (`job_id`, `runid`, `status`, `started_at`, `ended_at`).
- Export warnings and manifest summary are carried in `jobinfo.result`.
- `jobinfo.result` minimum fields:
- `artifact_id`
- `download_url`
- `cache_hit` (boolean)
- `source_job_id` (present on cache hit)
- `manifest_relpath`
- `warnings` (array of warning objects)

### 5.3 Download
`GET /api/runs/{runid}/{config}/export/features/{job_id}/download`

Behavior:
- Resolves `job_id` to an `artifact_id` mapping.
- Returns file response when `jobstatus.status == "finished"`.
- Returns 409 if job is not yet terminal success.
- Returns canonical 404 if job or artifact mapping does not exist.

## 6. Dependency Tracking And Options-Aware Caching
### 6.1 Execution Tracking Versus Cache Index
RedisPrep and cache index have separate responsibilities:
- RedisPrep + TaskEnum track transient workflow state and latest RQ job IDs.
- Persistent cache index tracks reusable artifacts by request+dependency fingerprint.

Required RedisPrep changes:
- Add `TaskEnum.run_features_export = "run_features_export"` with label `Export Features` and emoji `📦`.
- Use `RedisPrep.timestamp(TaskEnum.run_features_export)` for lifecycle milestones.
- Persist latest export job ID under `RedisPrep.set_rq_job_id("features_export", job_id)`.

Persistent cache index:
- Store under run workspace at `export/features/cache/index.json`.
- Index key is `request_hash + dependency_fingerprint`.
- Index value includes `artifact_id`, artifact paths, source `job_id`, and manifest metadata.

### 6.2 Canonical Cache Key Rules
Cache key must use normalized payload and resolved dependencies:
- Normalize and sort arrays: `layers`, `output_scopes`, table lists.
- Resolve defaults before hashing (`crs`, `output_scopes`, `swat_run_id`, temporal defaults).
- Resolve `swat_run_id="latest"` to concrete run id before hashing.
- Include Unitizer settings fingerprint when `units=project` is used.
- Include version markers: layer catalog version, unit conversion version, export code version.
- Include dependency fingerprint from the export dependency resolver (not RedisPrep/Preflight task status).

Dependency resolver contract:
- Resolve final dataset relpaths after all selectors are applied (`output_scopes`, scenario/contrast, SWAT run/table filters, temporal mode).
- Build dependency entries from actual resolved `geometry.locator`, `sources`, and `dependencies` in `layer_catalog.yaml`, including `unitizer.nodb` when `units=project`.
- Include `layer_catalog.yaml` metadata/version signature in dependency resolution.
- Fingerprint each dependency entry from canonical relpath plus file metadata (`size`, `mtime_ns`) and optional content hash when configured.
- Build the final dependency fingerprint from ordered dependency entries serialized in canonical JSON.

### 6.3 AgFields Interchange Auto-Preparation (Parity+)
Trigger:
- Any requested layer in the AgFields WEPP metrics family.
- No backward-compatibility hooks are required for AgFields layer IDs or selectors; enforce the current parity+ contract directly.

Behavior:
- If required AgFields interchange assets are missing or version-incompatible, run on-demand interchange preparation for `wepp_output_subpath="ag_fields"` using the shared interchange workflow.
- Required assets are catalog-driven from AgFields metrics layers (`ag_fields.metrics.subfields`, `ag_fields.metrics.fields`) across `geometry.locator`, `sources`, and `dependencies`; no hardcoded file list outside the catalog contract.
- If preparation succeeds, continue export in the same job with prepared assets included in dependency fingerprinting.
- If preparation fails and no requested layers remain exportable, return 404 or 409 according to root cause classification.
- If preparation fails for some AgFields layers but other requested layers are still exportable, complete export with `layer_unavailable` warnings.

### 6.4 Cache Hit Behavior
Cache hit flow:
- Submit endpoint still enqueues a lightweight export-finalize RQ job and returns 202.
- Lightweight job writes a new job-scoped manifest that points to existing `artifact_id`.
- `jobinfo.result.cache_hit=true` and `source_job_id=<original producer job>`.
- Download route serves the cached artifact via `artifact_id` mapping.

Artifact layout:
- Job metadata: `export/features/jobs/{job_id}/`.
- Reusable artifacts: `export/features/artifacts/{artifact_id}/`.
- Manifest exists in both locations.
- Job manifest includes `cache_hit` and `source_job_id`.

### 6.5 WP-2 Milestone Status (Completed 2026-03-26)

ExecPlan completion:
- `docs/mini-work-packages/20260326_features_export_wp2_execplan.md` status is `done`.

Implemented files:
- `wepppy/nodb/mods/features_export/dependency_tracker.py`
- `wepppy/nodb/mods/features_export/cache_key.py`
- `wepppy/nodb/mods/features_export/__init__.py`
- `tests/nodb/mods/test_features_export_dependency_tracker.py`
- `tests/nodb/mods/test_features_export_cache_key.py`

Contract clarifications from implementation:
- `nodb_ref` locator paths are resolved through an explicit resolver callback contract in WP-2 helpers; no implicit controller fallback behavior is used.
- `path_template` locators that include `{table_name}` require pre-resolved table names (for example SWAT table discovery output) before dependency fingerprinting.
- Dependency fingerprints include a stable catalog metadata signature (`catalog_version`, `schema_version`, `updated_at_utc`, `owner`, `status`) plus ordered canonical dependency entries.
- Dependency entry snapshots include `relpath`, `exists`, `size`, `mtime_ns`, and optional `content_hash_marker`/`content_hash_value` (`sha256` mode).
- Cache request hashing requires a concrete `swat_run_id` (no unresolved `latest`) and requires Unitizer preferences fingerprint input when `units=project`.
- WP-2 cache index helper persists deterministic JSON at `export/features/cache/index.json` with load/get/upsert semantics and `schema_version=1`.

Validation evidence:
- `wctl run-pytest tests/nodb/mods/test_features_export_dependency_tracker.py --maxfail=1` -> pass (3 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_cache_key.py --maxfail=1` -> pass (4 passed)
- `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=1` -> pass (2 passed)

## 7. Units Strategy And Unitizer Requirements
Units modes:
- `si`: SI export output.
- `english`: English export output.
- `project`: project Unitizer settings, including mixed per-variable preferences.

`features_export` must use Unitizer numeric conversion primitives.

### 7.1 Unitizer Milestone Status (Completed 2026-03-25)

ExecPlan completion:
- `docs/mini-work-packages/20260325_unitizer_features_export_execplan.md` status is `done`.

Implemented files:
- `wepppy/nodb/unitizer.py`
- `wepppy/nodb/unitizer.pyi`
- `tests/nodb/test_unitizer_numeric_apis.py`
- `docs/mini-work-packages/20260325_unitizer_features_export_execplan.md`

New public Unitizer API contract:
- Numeric conversion APIs: `convert_scalar`, `convert_sequence`, `convert_table`.
- Target resolution API: `resolve_target_unit` with `si|english|project` semantics.
- Stable cache fingerprint API: `preferences_fingerprint`.
- Public metadata/result types: `UnitTargetResolution`, `UnitConversionMetadata`, `UnitizedScalar`, `UnitizedSequence`, `UnitizedTable`.
- Public helper: `get_unit_class`.
- Explicit pass-through/no-mapping signaling via `pass_through_reason`.
- Ambiguity handling for shared labels (for example `ppm`) and identity-path type preservation (no int-to-float coercion when no conversion applies).
- Existing `context_processor_package()` behavior remains compatible (`unitizer`, `unitizer_units`, `unitizer_with_units`).

Validation evidence from handoff:
- `wctl run-pytest tests/nodb/test_unitizer_preferences.py --maxfail=1` -> pass (4 passed)
- `wctl run-pytest tests/weppcloud/routes/test_unitizer_bp.py --maxfail=1` -> pass (2 passed)
- `wctl run-pytest tests/nodb/test_unitizer_numeric_apis.py --maxfail=1` -> pass (29 passed)
- `wctl run-stubtest wepppy.nodb.unitizer` -> pass
- `wctl check-test-stubs` -> pass
- `wctl run-pytest tests --maxfail=1` -> pass (2582 passed, 34 skipped)

Reviewer status:
- High/medium findings reported during review were resolved (ambiguity handling and identity conversion type preservation).
- QA reviewer reported no remaining high/medium findings.

Residual risk:
- Low-risk untested defensive branch remains (`target_unit_not_supported`), requiring registry mutation to exercise.
- No blocking risks identified.

## 8. Temporal Semantics
Temporal schema policy:
- Preserve native source schemas and temporal grain.
- Do not force long-table normalization.

Supported modes:
- `annual_average`
- `yearly`
- `event`

`annual_average` rules:
- Uses return-period year-selection behavior.
- `exclude_yr_indxs` uses zero-based year index semantics consistent with return-period processing.
- `year_selection=custom` requires explicit `exclude_yr_indxs`.

`event` rules:
- `selector=date`: explicit date set.
- `selector=return_period`: explicit return-period intervals.
- Mixed date and return-period selectors in one request are invalid.

Mixed-layer temporal compatibility:
- Temporal compatibility is layer-specific and driven by each layer's catalog `temporal.supported_modes` and `temporal.mode_rules`.
- Layers incompatible with request temporal selectors are excluded with `layer_unavailable` when at least one other layer remains exportable.
- If every requested layer is excluded by temporal compatibility checks, return 400.
- `year_selection` and `exclude_yr_indxs` are only applied where catalog rules allow `year_selection_supported=true`; otherwise emit `selector_defaulted`.

## 9. Selector Rules For Omni And SWAT
Omni:
- Scenario layers require `scenario`.
- Contrast layers require `contrast_id`.
- Scenario and contrast families cannot be requested together in one job.

SWAT:
- Default is all discovered interchange tables for resolved `swat_run_id`.
- `swat_tables.include` exports only listed tables.
- `swat_tables.exclude` exports all discovered minus listed tables.
- Include/exclude values are deduplicated and lexicographically sorted for cache canonicalization.
- SWAT table resolution is profile-driven from catalog `table_profiles` (for example, `subbasin`, `channel`, `hru`, `non_spatial`).
- Each resolved table maps to profile-defined geometry strategy and join contract before export.
- Non-spatial SWAT tables are exportable for `geoparquet`, `geopackage`, and `geodatabase`; they are skipped with `table_unavailable` warnings for `geojson` and `kmz`.

## 10. NoDb Mod And Runs-Page UI Contract
Module placement:
- Implement at `wepppy/nodb/mods/features_export`.
- Follow NoDb facade/collaborator pattern.

Runs page integration:
- Add `Export` to the Mods list.
- Implement a NoDb controller UI using established async pattern.
- Add a top-of-control secondary `Load Defaults` action that applies a gpkg-adjacent profile without auto-submit.
- `Load Defaults` profile defaults: `format=geopackage`, `units=project`, `crs=wgs`, `output_scopes=["baseline"]`, cleared temporal/Omni selectors, and a curated baseline layer set aligned with legacy gpkg outcomes.
- Use the dedicated subagent role pack at `wepppy/nodb/mods/features_export/SUBAGENT_ROLES.md` for UI design/development specification and implementation planning.
- Use `wepppy/nodb/mods/features_export/ui_control_layout.md` as the canonical detailed control layout and ASCII wireframe reference.
- Controller posts JSON payload, stores returned `job_id`, and polls canonical `/rq-engine/api/jobstatus/{job_id}` via `set_rq_job_id`.
- Completion details and warnings are read from `/rq-engine/api/jobinfo/{job_id}`.
- Download is enabled when job state is `finished`.
- Controller must attach `attach_status_stream` with stacktrace hooks and keep poll fallback enabled.
- Controller must hydrate prior `job_id` on bootstrap using existing controller-contract guidance.
- Template must include required status panel, stacktrace panel, and job-hint DOM hooks with `aria-live="polite"` status behavior.

## 11. Manifest And Warning Contract
Every artifact includes `manifest.json`.

Manifest minimum fields:
- Resolved request payload and selector defaults.
- CRS metadata (`requested_crs`, `resolved_crs`, `resolved_epsg`).
- Resolved dependency entries with path, existence, timestamp, and fingerprint components.
- Per-layer scope metadata (`baseline|roads|shared`).
- SWAT table profile resolution and per-table spatiality classification.
- Temporal compatibility decisions (selectors applied, selectors defaulted, and layer/table exclusions).
- Conversion summary and unit pass-through fields.
- Row and feature counts per layer.
- Generation timestamps and tool/catalog versions.
- `cache_hit`, `source_job_id`, `artifact_id`.
- Dependency-preparation records (including AgFields interchange auto-prep attempts and outcomes).
- `warnings` array.

Warning object shape:
- `code`: machine-readable warning code.
- `message`: human-readable description.
- `layer_id`: optional associated layer.
- `scope`: optional associated scope.

Reserved warning codes:
- `scope_missing_layer`
- `scope_not_applicable`
- `layer_unavailable`
- `table_unavailable`
- `measure_unavailable`
- `unit_pass_through`
- `selector_defaulted`
- `legacy_flags_ignored`

## 12. Migration And Cutover
Cutover is immediate with explicit legacy cleanup:
- Remove direct `gpkg_export` route/task usage from rq-engine export routes.
- Move export ownership from `wepppy/export/gpkg_export.py` to NoDb `features_export`.
- Remove run-completion hooks that auto-generate gpkg/gdb artifacts.
- Retire `/export/geopackage` and `/export/geodatabase` in favor of `/export/features`.
- Remove legacy prep UI toggles for gpkg/gdb auto-export.
- AgFields parity+ support ships without legacy compatibility shims (single-project assumption).

Back-compat behavior for existing saved configs:
- Persisted legacy export flags (`create_gpkg`, `create_gdb`, `arc_export_on_run_completion`) are ignored.
- Default config for new runs sets `arc_export_on_run_completion=false` (or removes the setting entirely) as part of the same cutover.
- Existing runs with `arc_export_on_run_completion=true` no longer auto-generate gpkg/gdb; on first export interaction emit `legacy_flags_ignored` warning in manifest and `jobinfo.result.warnings`.

## 13. Acceptance Criteria
- All five formats export successfully on representative runs.
- Single-layer formats produce zipped files with one file per resolved layer.
- Multi-layer formats produce one container artifact per request.
- Scope-aware layers export per requested scope; scope-invariant layers export once as `shared__*`.
- Partial-scope exports emit warnings and still succeed when at least one scoped layer resolves.
- Non-scope missing requested layers/tables emit `layer_unavailable` or `table_unavailable` warnings and still succeed when at least one export target resolves.
- Parity+ AgFields support is present: boundaries/sub-fields plus AgFields WEPP metric layers sourced from `wepp/ag_fields/output/interchange/*`.
- Requesting AgFields WEPP metric layers triggers on-demand AgFields interchange preparation when needed and proceeds without manual pre-run migration.
- Submit endpoint rejects non-JSON payloads with 415 and validates selector rules with 400/404/409 per contract.
- CRS selection works with `wgs|utm`, defaults to `wgs`, and exports include CRS metadata in manifest.
- Polling and terminal status behavior align with canonical RQ contract (`finished` success).
- Warnings are present in both `jobinfo.result.warnings` and `manifest.json`.
- Cache hits return 202 with a new lightweight job ID, `cache_hit=true`, and reusable artifact delivery.
- Cache key includes Unitizer settings fingerprint for `units=project` and invalidates on Unitizer preference changes.
- Dependency fingerprint is computed from resolved geometry/sources/dependencies, not task timestamps/preflight status.
- `output_scopes` is case-normalized, deduplicated, and invalid values fail with 400.
- `layer_catalog.yaml` is present, machine-readable, and drives layer discovery/validation.
- `layer_catalog.yaml` schema validation enforces locator vocabulary, temporal mode rules, and join-key precedence.
- Optional measure availability (for example `tsmf`, phosphorus, `QRain`, `QSnow`) follows catalog rules and emits `measure_unavailable` warnings when absent.
- RedisPrep/TaskEnum timestamps and `rq:features_export` tracking are wired.
- `units=si|english|project` all work with manifest conversion metadata.
- Unitizer numeric API foundation (`convert_scalar|convert_sequence|convert_table`, `resolve_target_unit`, `preferences_fingerprint`) is complete and available for `features_export` integration.
- `annual_average`, `yearly`, and `event` modes work; daily is rejected.
- Mixed temporal requests have deterministic partial-export behavior and warning semantics.
- SWAT default all-table export and include/exclude overrides work with profile-based geometry/non-spatial handling.
- Export mod appears on Runs page and follows existing NoDb async controller interaction.
- `Load Defaults` is available as a secondary action near the top of the control, applies gpkg-adjacent defaults, emits a defaults-loaded event, and never auto-submits.
- Regression tests cover payload shape, selector validation, scope behavior, cache hit flow, and legacy cutover.

## 14. Implementation Skeleton And Work-Package Breakdown
This feature should be implemented as multiple small, ordered work-packages with stable boundaries and explicit handoff contracts.

Code organization target:

```text
wepppy/nodb/mods/features_export/
  __init__.py
  specification.md
  ui_control_layout.md
  layer_catalog.yaml
  contracts.py                # request/result/warning dataclasses and enums
  facade.py                   # NoDb facade entrypoint for control/bootstrap data
  catalog_loader.py           # catalog read + schema validation + index build
  planner.py                  # selectors -> resolved layer export plan
  dependency_tracker.py       # RedisPrep/TaskEnum preflight/dependency checks
  cache_key.py                # options-aware canonical cache key/fingerprint
  unit_conversion.py          # Unitizer numeric conversion integration adapter
  exporters/
    __init__.py
    base.py                   # common writer contract
    geojson.py
    geoparquet.py
    kmz.py
    geopackage.py
    geodatabase.py
    packaging.py              # zip bundling for single-layer formats
  manifest.py                 # manifest/warning assembly
  service.py                  # orchestration: plan -> export -> manifest -> artifact
```

Related integration files (outside module) should be kept thin and delegate to `features_export.service`:
- rq-engine export route/controller.
- rq task enqueue + worker function.
- Runs-page controller bootstrap + template wiring.

### 14.1 Work-Package Sequence

WP-0: Unitizer numeric API foundation (completed)
- Status: done via `docs/mini-work-packages/20260325_unitizer_features_export_execplan.md`.
- Deliverable: public numeric conversion APIs + cache fingerprint support now available for `features_export`.

WP-1: Core contracts and planner skeleton (completed 2026-03-26)
- Status: done via `docs/mini-work-packages/20260326_features_export_wp1_execplan.md`.
- Implemented files: `contracts.py`, `catalog_loader.py`, `planner.py`, `__init__.py`, and focused tests under `tests/nodb/mods/test_features_export_*`.
- Contract clarification: planner validation failures are emitted through a canonical 400-style `validation_error` contract (`error + errors[]`) with structured `ValidationIssue` entries.
- Contract clarification: deterministic plan ordering is canonicalized by sorted unique `layers`, canonical `output_scopes` order (`baseline`, `roads`), and stable resolved layer ids (`{scope_or_shared}__{layer_id}`).
- Contract clarification: temporal incompatibility is handled per layer; incompatible layers emit `layer_unavailable`, and if all layers are excluded the planner raises `no_exportable_layers`.
- Deliverable: deterministic `ResolvedExportPlan` object and unit tests for selector rules.

WP-2: Dependency tracking and options-aware caching (completed 2026-03-26)
- Status: done via `docs/mini-work-packages/20260326_features_export_wp2_execplan.md`.
- Implemented files: `dependency_tracker.py`, `cache_key.py`, package export wiring, and focused tests under `tests/nodb/mods/test_features_export_dependency_tracker.py` and `test_features_export_cache_key.py`.
- Contract clarification: dependency locators enforce strict `kind`/`value` structure at resolution time; `nodb_ref` requires explicit resolver input and `path_template` entries requiring `{table_name}` require pre-resolved table names.
- Contract clarification: request hash requires concrete `swat_run_id` and includes Unitizer preferences fingerprint for `units=project`, plus catalog/conversion/export version markers.
- Deliverable: deterministic dependency snapshot/fingerprint and deterministic cache-key/index foundation (`export/features/cache/index.json`).

WP-3: Format writers and packaging
- Add `exporters/*` plus `manifest.py`.
- Implement all five format writers behind one writer interface.
- Implement single-layer zip packaging behavior for `geojson|geoparquet|kmz`.
- Deliverable: artifact + manifest generated from a pre-resolved plan.

WP-4: Service orchestration and RQ wiring
- Add `service.py` orchestration and thin rq-engine route/task adapters.
- Implement canonical async submit/jobinfo/download behavior.
- Deliverable: end-to-end export job execution for API callers with warning contract.

WP-5: Runs-page UI control integration
- Implement template + JS controller using `ui_control_layout.md`.
- Include top-level `Load Defaults`, progressive disclosure cards, and status/stacktrace/job-hint contract.
- Deliverable: fully wired Runs-page control with Jest/Playwright coverage.

WP-6: Cutover and legacy retirement
- Remove legacy gpkg/gdb routes and completion hooks.
- Finalize migration warnings for ignored legacy flags.
- Deliverable: feature flag/cutover complete with regression suite passing.

### 14.2 Dependency Order And Parallelism
- WP-1 depends on completed WP-0 Unitizer APIs.
- WP-2 depends on WP-1 outputs.
- WP-3 depends on WP-1; can proceed in parallel with late WP-2 testing once plan shape is stable.
- WP-4 depends on WP-2 and WP-3.
- WP-5 can begin after WP-1 contracts stabilize, then finalize against WP-4 endpoints.
- WP-6 is last.

### 14.3 Keep-It-Organized Rules
- Keep planner and validation logic pure and side-effect free.
- Keep file-system and geospatial I/O only inside exporter/service layers.
- Keep route/task files as adapters only; no business logic.
- Keep warning-code definitions centralized in `contracts.py`.
- Keep catalog/path resolution logic centralized in `catalog_loader.py`; no duplicated path construction in writers.
