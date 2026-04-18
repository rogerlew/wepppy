# Features Export Specification

Status: Implemented (Living Spec)  
Owner: WEPPpy NoDb export subsystem  
Primary module: `wepppy/nodb/mods/features_export`  
Replaces legacy export modules: `wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py`, and associated route/task wiring
Document posture: Living working specification; mutate when implementation evidence shows a better contract or exposes gaps.

## 1. Summary
Create a NoDb `features_export` mod for user-configurable spatial and spatial-temporal exports across WEPP, Omni, Ash/WATAR, WEPP interchange, SWAT interchange, and AgFields datasets.
This is an immediate replacement for legacy gpkg/gdb export behavior, but implemented with NoDb controller patterns, canonical RQ polling contracts, and dependency-aware cache reuse.
AgFields support is parity+ (spatial + WEPP interchange metrics), including automatic on-demand AgFields interchange generation when required for requested export layers.
Data extraction and merge orchestration for export payload assembly is DuckDB-first (SQL joins/projections/filters) for performance and deterministic schema control; pandas merge loops are non-compliant for production payload assembly paths.
The normative materialization architecture is key-first and geometry-last: build one attribute table per carrier/context/scope keyed by canonical ids, then attach geometry exactly once from canonical carrier geometry.
This architecture is the default implementation contract (no temporary feature-flagged parallel path).
User-facing dataset labels and output layer names must prioritize established WEPP output vocabulary over internal family or implementation tokens.

## 2. Supported Formats
- `geojson` (single-layer format)
- `geoparquet` (single-layer format)
- `parquet` (single-layer geometryless tabular format)
- `csv` (single-layer geometryless tabular format)
- `kmz` (single-layer format)
- `geopackage` (multi-layer container format)
- `geodatabase` (multi-layer FileGDB container via `f_esri`)

Format token contract:
- Canonical request token is `geodatabase`.
- Backward-compatible alias `f_esri` is accepted and normalized to `geodatabase`.
- FileGDB payload member extension remains `.gdb.zip` inside the final download bundle.

Packaging rules:
- All format downloads are `.zip` artifacts.
- Single-layer formats produce one file per resolved layer inside the zip bundle.
- Multi-layer formats produce one container payload member inside the zip bundle.
- KMZ is single-layer only; multi-layer requests produce multiple `.kmz` files in the zip.
- Geometryless formats (`parquet`, `csv`) always emit tabular outputs without geometry columns/encodings.
- For geometryless formats, required identity/join fields remain included even when geometry is removed.
- Geometryless formats support optional `tabular` controls:
  - `concatenate_tables=true` concatenates hillslope carrier tables into one `hillslopes` file and channel carrier tables into one `channels` file.
  - `temporal_layout=wide|long` controls temporal measure shaping for `event`/`yearly` layers (`wide` default).
- Geometryless writer path is table-native end-to-end: tabular exports consume DataFrame payloads directly and must not serialize/parse FeatureCollection JSON in the writer path.
- Geometryless carrier materialization is independent of geometry files: tabular outputs are produced from attribute sources only and do not enrich identity columns from carrier geometry datasets.
- Every zip artifact must include:
  - export payload members (data files/container members),
  - `manifest.json`,
  - generated `README.md` (artifact metadata summary).
- Artifact bundles must not include `profile.yml` or built-in profile files; profile discovery/replay is route-level (`profile/resolve`) and publication-level (`published/index.json`) metadata.
- Identity normalization contract for all output formats (geometry and tabular):
  - Emit canonical identity columns `topaz_id`, `wepp_id` as the first two output columns.
  - Coalesce identity aliases (`TopazID`/`topaz_id`, `WeppID`/`wepp_id`) into canonical columns.
  - Remove redundant alias columns after coalescing.

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
- `columns` contract for UI-visible field selection:
  - `column_id` (canonical source/output field key)
  - `label` (human-readable field name)
  - `unit` metadata (`display_unit`, `unit_class`, `is_unitized`)
  - `default_selected` (boolean)
  - optional availability/selector guards
  - When a layer omits an explicit `columns` block, runtime schema discovery (from resolved source datasets) is the fallback source of truth for UI column selectors and unit labels.
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
- Resolved locator paths must stay inside allowed dependency roots:
  - default allowed root is the active working directory (`wd`);
  - for canonical Omni child runs (`_pups/omni/scenarios/*` and `_pups/omni/contrasts/*`), the parent run root (path segment before `_pups`) is also allowed.
- Canonical dependency `relpath` values are recorded relative to `wd`; parent-run references are therefore expected to include `../` segments for Omni child runs.

Initial layer families:
- Watershed: subcatchments, channels.
- Landuse: dominant class and coverage attributes.
- Soils: dominant class and physical properties.
- Ash/WATAR: hillslope ash transport outputs.
- AgFields spatial: field boundaries and sub-field polygons.
- AgFields WEPP metrics: sub-field/field metrics sourced from `wepp/ag_fields/output/interchange/*`.
- WEPP: canonical output datasets labeled with familiar file names (for example `H.element.parquet`, `H.wat.parquet`, `H.pass.parquet`, `H.loss.parquet`, `H.soil.parquet`, `return_period_events.parquet`, `chan.out.parquet`, `chanwb.parquet`).
- SWAT interchange: `swat/outputs/run_*/interchange/*`.
- Omni scenarios: `_pups/omni/scenarios/*`.
- Omni contrasts: `_pups/omni/contrasts/*`.

Discoverability requirements:
- Internal ids like `wepp.temporal.events` are backend-only tokens and must never be shown as the primary UI label.
- Primary dataset labels are catalog-owned via per-layer `label` in `layer_catalog.yaml`; route/controller code must not maintain a parallel hardcoded label map.
- Group rendering is discovery-driven: hide groups with zero currently available datasets for the active run/config.
- Group order keeps Omni families at the bottom of the catalog list.

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
- WEPP and Omni output datasets are consolidated by geometry carrier per context to keep layer counts legible:
  - Up to one `sbs_map-subcatchments` layer per scope.
  - Up to one `chan_map-channels` layer per scope.
- Base WEPP context emits at most two consolidated layers per requested scope (`subcatchments` and/or `channels`) depending on selected outputs.
- Each selected Omni scenario/contrast emits its own consolidated `subcatchments` and/or `channels` layer set per requested scope.
- Scope-invariant families remain single-emission artifacts and are not duplicated per scope unless explicitly scope-aware in catalog metadata.
- Consolidated layer names must use descriptive run/context naming:
  - Baseline base context: `{runid}-sbs_map-subcatchments`, `{runid}-chan_map-channels`.
  - Roads scope: `{runid}-roads-sbs_map-subcatchments`, `{runid}-roads-chan_map-channels`.
  - Scenario context: `{runid}-scenario-{scenario_id}-{carrier}`.
  - Contrast context: `{runid}-contrast-{contrast_id}-{carrier}`.
- If one requested scope is missing for a scope-aware layer, export available scopes and emit warning code `scope_missing_layer`.
- If a requested scope is not applicable to a scope-invariant layer, emit warning code `scope_not_applicable`.
- If no layer resolves after scope processing, return 404.
- When `format=csv|parquet` and `tabular.concatenate_tables=true`, carrier-concatenated rows include provenance columns:
  - `output_scope`
  - `omni_scenario` (scenario-context rows only; null otherwise)
  - `omni_contrast_id` (contrast-context rows only; null otherwise)
- `tabular.temporal_layout` behavior for `event`/`yearly` temporal modes:
  - `wide` (default): one row per feature key with temporal selector tokens appended to measure column names.
  - `long`: one temporal selector column (`date`, `return_period`, or `year`) with measure columns across multiple rows.

Carrier materialization contract (normative):
- Consolidated carriers are built in two phases:
  - Phase A (`DuckDB attribute core`): materialize one table per `{context, selector_id, scope, carrier}` from discovered datasets using canonical join keys.
  - Phase B (`geometry attach`): join Phase A output to a canonical carrier geometry table exactly once.
- Canonical key precedence:
  - Subcatchments carrier: `topaz_id` preferred, `wepp_id` fallback.
  - Channels carrier: `chn_id` preferred, `topaz_id` fallback.
  - Catalog `join.source_key_map` overrides remain authoritative for source-specific key resolution.
- Contract clarification:
  - `wepp.summary.channels` must materialize its internal metrics-plus-attributes join on `wepp_id` because `loss_pw0.chn.parquet` is keyed by WEPP channel id while the canonical channel geometry carrier remains topaz-facing.
- Each source dataset must be reduced to one row per effective carrier key before joining into Phase A output (via deterministic temporal filtering, deterministic projection, and deterministic dedupe/aggregation rules when needed).
- Unresolved many-to-many key joins on a carrier hot path are contract violations and must fail explicitly with `materialization_error`; silent Cartesian growth is forbidden.
- Legacy non-carrier source merges must resolve identity keys from explicit join contract candidates (`join.primary_key`, `join.fallback_keys`, `geometry.feature_id_keys`). If no candidate resolves, fail with `materialization_error`; arbitrary first-column fallback is non-compliant.
- Canonical carrier geometry tables must contain one geometry row per effective carrier key. When raw geometry sources contain repeated key rows, geometry must be canonicalized (for example, deterministic dissolve/aggregation) before Phase B.
- For spatial carriers, the canonical geometry keyset is the authoritative export row domain. Phase A keys not present in canonical geometry are excluded before final attachment, and final row/feature counts must match canonical carrier entity counts.
- Repeated geometry-attached frame merges (geometry-first per-dataset pipelines) are non-compliant for production export paths.

## 5. API Contract (rq-engine)
### 5.1 Submit Export Job
`POST /api/runs/{runid}/{config}/export/features`

Auth contract:
- Submit/profile-resolve endpoints require `rq:export` plus run-access authorization.
- Download endpoints (`job/{job_id}/download`, `published/{profile}/download`) allow anonymous access for public runs; non-public runs require `rq:export` plus run-access authorization.
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
- `scenarios`: optional non-empty array of Omni scenario IDs.
- `contrast_ids`: optional non-empty array of Omni contrast IDs.
- Backward-compatible aliases `scenario` and `contrast_id` are accepted and normalized into single-entry arrays.
- `swat_run_id`: optional SWAT run selector, default `latest`.
- `swat_tables`: optional object with one of `include` or `exclude`, each an array of table names.
- `column_selection`: optional object keyed by `layer_id` with one of:
  - `include`: non-empty array of `column_id` values to export.
  - `exclude`: array of `column_id` values to drop from export.
  - `include` and `exclude` are mutually exclusive per layer.
- `temporal`: optional object.
- `temporal.mode`: optional default enum `annual_average|yearly|event` used when a temporal-capable layer does not provide an override.
- `temporal.layer_modes`: optional object keyed by `layer_id`; value enum `annual_average|yearly|event`.
- `temporal.year_selection`: optional global enum `all|exclude_first|exclude_first_two|exclude_first_five|custom`.
- `temporal.exclude_yr_indxs`: optional global array of zero-based integer indices.
- `temporal.event`: required when any effective temporal mode is `event`.
- `temporal.event.selector`: enum `date|return_period`.
- `temporal.event.dates`: required for `selector=date`; array of `YYYY-MM-DD`.
- `temporal.event.return_periods`: required for `selector=return_period`; numeric array in years.
- `tabular`: optional object, valid only for `format=csv|parquet`.
- `tabular.concatenate_tables`: optional boolean, default `false`.
- `tabular.temporal_layout`: optional enum `wide|long`, default `wide`.

Request example:
```json
{
  "format": "geoparquet",
  "units": "project",
  "crs": "wgs",
  "layers": ["wepp.H.element.parquet", "wepp.chan.out.parquet"],
  "output_scopes": ["baseline", "roads"],
  "scenarios": ["thinned", "control"],
  "swat_run_id": "latest",
  "temporal": {
    "mode": "yearly",
    "layer_modes": {
      "wepp.H.element.parquet": "yearly",
      "wepp.chan.out.parquet": "annual_average"
    },
    "year_selection": "exclude_first_two",
    "exclude_yr_indxs": [0, 1]
  }
}
```

Validation:
- `scenarios` and `contrast_ids` are mutually exclusive.
- Omni scenario and Omni contrast layer families cannot be mixed in one request.
- Omni scenario layers require `scenarios`.
- Omni contrast layers require `contrast_ids`.
- SWAT layers require a resolved `swat_run_id`; `latest` is resolved to a concrete run ID before execution and persisted in manifest/cache key.
- Unknown layer IDs return 400.
- Unsupported `crs` value returns 400.
- Unsupported temporal mode returns 400.
- Daily timeseries mode is not supported and returns 400.
- `swat_tables.include` and `swat_tables.exclude` are mutually exclusive.
- `format=parquet|csv` is valid for both spatial and non-spatial datasets and strips geometry from output rows instead of failing on spatial inputs.
- `tabular` is only valid when `format=parquet|csv`.
- `tabular.concatenate_tables` must be boolean when provided.
- `tabular.temporal_layout` must be `wide|long` when provided.
- `tabular.temporal_layout=long` rejects mixed effective `event` and `yearly` layer modes in one request.
- `column_selection[layer_id].include` and `column_selection[layer_id].exclude` are mutually exclusive.
- Unknown layer ids in `column_selection` return 400 with structured validation errors.
- Unknown column ids return 400 when the target layer has an explicit `columns` contract in catalog metadata; for discovery-driven layers without explicit `columns`, dynamic source-schema column ids are accepted.
- If `column_selection[layer_id].include` is provided, exported fields for that layer are limited to the selected set plus required identity/join geometry fields.
- If `column_selection[layer_id].exclude` removes all optional fields, export still retains required identity/join geometry fields.
- `crs=utm` requires a resolvable run UTM CRS; unresolved UTM CRS returns 409.
- AgFields WEPP metric layers require AgFields output/interchange assets; exporter performs on-demand preparation as defined in Section 6.3.
- Temporal mode support is evaluated per resolved layer from catalog `temporal.supported_modes`.
- Every selected temporal-capable layer must resolve an effective temporal mode from `temporal.layer_modes[layer_id]` or fallback `temporal.mode`.
- If `temporal.mode=yearly` (or a layer-level effective mode is `yearly`) and `temporal.year_selection` is omitted, default to `year_selection=all`.
- `year_selection` and `exclude_yr_indxs` apply globally across all layers whose effective mode supports year filtering.
- If some layers are incompatible with requested temporal settings and at least one layer remains exportable, incompatible layers are dropped with `layer_unavailable` warnings.
- If no requested layers support the requested temporal settings, return 400.
- If `year_selection` or `exclude_yr_indxs` is provided for a layer whose catalog rule sets `year_selection_supported=false`, ignore those selectors for that layer and emit `selector_defaulted`.
- Missing required source dependencies for a resolved layer (missing required source locator, missing required source file, unsupported required source kind, unresolved required join key) fail the job with `materialization_error`; silent downgrade to warnings is forbidden.
- Optional missing datasets may emit warnings and still succeed when at least one export target resolves.
- Unsupported format dependency returns 409.

CRS behavior:
- `crs=wgs` exports spatial layers in EPSG:4326.
- `crs=utm` exports spatial layers in the run-resolved UTM CRS (single resolved EPSG per job).
- Non-spatial layers are unaffected by CRS selection.
- Geometryless formats (`parquet`, `csv`) are unaffected by CRS selection because geometry is not exported.

Submission response:
- Always HTTP 202 with canonical async payload.
- Required key: `job_id`.
- Required `status_url` points to `/rq-engine/api/jobstatus/{job_id}`.
- Required `download_url` points to `/rq-engine/api/runs/{runid}/{config}/export/features/job/{job_id}/download` and is only valid once the job is `finished`.
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
- `download_url` (canonical job route URL)
- `cache_hit` (boolean)
- `source_job_id` (present on cache hit)
- `manifest_relpath`
- `warnings` (array of warning objects)

### 5.3 Download
`GET /api/runs/{runid}/{config}/export/features/job/{job_id}/download`  
`GET /api/runs/{runid}/{config}/export/features/published/{profile}/download`

Behavior:
- Job endpoint resolves `job_id` to an `artifact_id` mapping.
- Job endpoint returns file response when `jobstatus.status == "finished"`.
- Job endpoint returns 409 if job is not yet terminal success.
- Job endpoint returns canonical 404 if job or artifact mapping does not exist.
- Published endpoint resolves `{profile}` through `export/features/published/index.json` (source of truth).
- Published endpoint profile tokens are canonical kebab-case profile IDs (for cutover: `prep-wepp`, `prep-wepp-geodatabase`, `prep-details`); no `latest` path segment is used.
- Published endpoint returns 404 when the profile has no published entry.
- Published endpoint returns 409 `stale_publication` when the registry entry no longer matches resolvable current dependency/request fingerprints for the published request.
- Published endpoint sets `Content-Disposition` filename as `<runid>.<canonical-profile>.<format>.zip` (for example `run-1.prep-wepp.geopackage.zip`).

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
- Resolve final dataset relpaths after all selectors are applied (`output_scopes`, scenarios/contrast_ids, SWAT run/table filters, temporal mode).
- Build dependency entries from actual resolved `geometry.locator`, `sources`, and `dependencies` in `layer_catalog.yaml`, including `unitizer.nodb` when `units=project`.
- Include `layer_catalog.yaml` metadata/version signature in dependency resolution.
- Fingerprint each dependency entry from canonical relpath plus file metadata (`size`, `mtime_ns`) and optional content hash when configured.
- Parent-run dependencies for canonical Omni child runs are valid cache dependencies when the resolved path stays within the inferred parent run root.
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
- Job download endpoint serves the cached artifact via `artifact_id` mapping.

Artifact layout:
- Job metadata: `export/features/jobs/{job_id}/`.
- Reusable artifacts: `export/features/artifacts/{artifact_id}/`.
- Manifest exists in both locations.
- Job manifest includes `cache_hit` and `source_job_id`.

### 6.5 Published Profile Registry
Publication-level downloads use one run-scoped registry document:
- Path: `export/features/published/index.json`.
- This file is the source of truth for `GET /api/runs/{runid}/{config}/export/features/published/{profile}/download`.
- The registry is a lightweight JSON index; it must not be modeled as a dedicated NoDb controller class.

Registry contract:
- Top-level:
  - `schema_version` (integer),
  - `updated_at_utc` (ISO 8601 UTC timestamp),
  - `profiles` (object map keyed by canonical profile ID).
- Canonical profile IDs for legacy-cutover publication are `prep-wepp`, `prep-wepp-geodatabase`, and `prep-details`.
- `prep-wepp-gpkg-gdb` is an execution-only virtual orchestration profile and is not persisted as a registry key; it co-publishes `prep-wepp` and `prep-wepp-geodatabase`.
- Each `profiles.{profile}` entry includes:
  - `profile` (string, matches key),
  - `job_id`,
  - `artifact_id`,
  - `artifact_relpath`,
  - `manifest_relpath`,
  - `format`,
  - `request_hash`,
  - `dependency_fingerprint`,
  - `cache_key`,
  - `published_at_utc`.
- Registry writes are atomic and idempotent per profile key.
- Published download resolution must verify that the registry entry still maps to an existing artifact and that its cache/dependency fingerprint remains valid for the resolved published request contract.

### 6.6 WP-2 Milestone Status (Completed 2026-03-26)

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

Column naming contract:
- Unit-applicable output columns must include a normalized unit token suffix in the exported column name (for example `runoff_mm`, `hillslope_area_ha`, `runoff_volume_m3`, `sediment_yield_kg_m2`).
- Columns without an applicable unit mapping keep their canonical source name and are recorded as pass-through in manifest unit metadata.
- Manifest must include a per-column unit mapping table so UI/download consumers can recover source field, target field, and resolved unit metadata deterministically.

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
- For `event` and `yearly` exports, materialize temporal measures in wide form at carrier geometry grain (one spatial feature row per canonical key).

Supported modes:
- `annual_average`
- `yearly`
- `event`

Global temporal control model:
- Temporal mode is resolved per selected temporal-capable dataset from `temporal.layer_modes[layer_id]` with fallback to `temporal.mode`.
- Global year selection controls (`year_selection`, `exclude_yr_indxs`) apply across all datasets whose effective temporal mode supports year filtering.
- UI control order must place global year selection immediately after CRS selection.
- Per-dataset column selection is independent from temporal controls and applies after temporal filtering.

`annual_average` rules:
- Uses return-period year-selection behavior.
- `exclude_yr_indxs` uses zero-based year index semantics consistent with return-period processing.
- `year_selection=custom` requires explicit `exclude_yr_indxs`.

`yearly` rules:
- If `year_selection` is omitted, default to `all`.
- Export includes every available year after global year filters are applied.
- `yearly` wide materialization pivots selected measures to year-suffixed columns (for example `runoff_yr2015_mm`).
- When multiple rows exist for one `{key, year}` slice, numeric measures are explicitly reduced by summation before pivoting; conflicting non-numeric slices fail with `materialization_error`.
- If year filtering excludes all years for a layer, that layer is dropped with `layer_unavailable` (or 400 if no layers remain).

`event` rules:
- `selector=date`: explicit date set.
- `selector=return_period`: explicit requested recurrence intervals (years), never raw rank values.
- Mixed date and return-period selectors in one request are invalid.
- Event selector filtering is applied to discovered source frames before key-first uniqueness checks.
- Required sources missing selector-compatible columns must fail with `materialization_error`.
- Required sources with selector-compatible columns but zero matched rows remain materialized as empty event cores; export succeeds with canonical geometry rows and null event metrics.
- Optional sources that cannot satisfy the active event selector are skipped.
- Return-period filtering uses nearest available Weibull `T` where `T >= requested_interval` (one available interval may satisfy at most one requested interval).
- Rank-only lookup sources derive `T` using the canonical WEPP return-period defaults (`method=cta`, Gringorten correction enabled) before applying interval matching.
- Event materialization pivots selected measures to selector-token-suffixed columns (for example `q_2015_01_16_mm` or `runoff_rp2_mm`) so output geometry remains normalized to canonical carrier feature counts.
- If event slices contain duplicate OFE rows, the terminal OFE (`max(ofe_id)`) is selected as the deterministic per-slice representative before pivoting.
- Remaining conflicting duplicates for the same `{key, event_token, measure}` slice are contract failures (`materialization_error`).

Mixed-layer temporal compatibility:
- Temporal compatibility is layer-specific and driven by each layer's catalog `temporal.supported_modes` and `temporal.mode_rules`.
- Layers with `temporal.supported_modes=[]` are explicitly atemporal and remain exportable regardless of request temporal mode.
- Layers incompatible with request temporal selectors are excluded with `layer_unavailable` when at least one other layer remains exportable.
- If every requested layer is excluded by temporal compatibility checks, return 400.
- `year_selection` and `exclude_yr_indxs` are only applied where catalog rules allow `year_selection_supported=true`; otherwise emit `selector_defaulted`.

## 9. Selector Rules For Omni And SWAT
Omni:
- Scenario layers require `scenarios`.
- Contrast layers require `contrast_ids`.
- Scenario and contrast families cannot be requested together in one job.
- Omni contexts inherit the selected base WEPP datasets; users do not pick separate Omni dataset lists.
- Omni selectors are multi-select and support bulk controls (`Select All`, `Unselect All`) for discovered options (required for contrasts).

SWAT:
- Default is all discovered interchange tables for resolved `swat_run_id`.
- `swat_tables.include` exports only listed tables.
- `swat_tables.exclude` exports all discovered minus listed tables.
- Include/exclude values are deduplicated and lexicographically sorted for cache canonicalization.
- SWAT table resolution is profile-driven from catalog `table_profiles` (for example, `subbasin`, `channel`, `hru`, `non_spatial`).
- Each resolved table maps to profile-defined geometry strategy and join contract before export.
- Non-spatial SWAT tables are exportable for `geoparquet`, `parquet`, `csv`, `geopackage`, and `geodatabase`; they are skipped with `table_unavailable` warnings for `geojson` and `kmz`.

## 10. NoDb Mod And Runs-Page UI Contract
Module placement:
- Implement at `wepppy/nodb/mods/features_export`.
- Follow NoDb facade/collaborator pattern.

Runs page integration:
- Add `Export` to the Mods list.
- Implement a NoDb controller UI using established async pattern.
- Add top-of-control profile actions:
  - `Load Export Profile` quick actions are populated from built-in profile files discovered via `load_builtin_profiles()` plus virtual orchestration presets (current built-ins: `Prep details`, `Post Wepp`, `Temporal yearly`; virtual: `Post Wepp (GPKG + GDB)` / `prep_wepp_gpkg_gdb`).
  - `Specify Export from Profile` text area + `Load profile` action.
  - `Clear selection` remains available as a separate action.
- `Post Wepp` is the default quick profile and replaces the legacy `Load Defaults` button behavior.
- Virtual profile discoverability contract:
  - `prep_wepp_gpkg_gdb` is emitted in runs-page bootstrap `profiles`/`profile_buttons` even though it has no dedicated `.yml` file.
  - Its base request is resolved via `resolve_published_profile_request("prep-wepp-gpkg-gdb")`.
  - Runtime enrichment applies before exposing it to the UI:
    - add `roads` to `output_scopes` when roads scope is available for the active run/config;
    - add `omni.scenarios.hillslopes` and discovered scenario IDs (`scenarios`) when Omni scenarios are available.
- Profile text loading accepts pasted YAML/JSON request-profile content and applies the profile without auto-submit.
- Run settings visual order is fixed: `format` -> `units` -> `crs` -> global `year_selection`.
- Catalog UI is hierarchy-first and must not include a layer search box, filter chips, or "select visible" behavior.
- Family labels are user-facing domain labels and must use one consolidated `WEPP` family with familiar output names (not split `WEPP Summary`, `WEPP Temporal`, `WEPP Interchange` headings).
- Layer rows must present clear hierarchy/indentation under family headers rather than a flat left-aligned list.
- Each dataset row must include an expandable/collapsible "Columns" section showing:
  - Column checkbox (selected/unselected)
  - Column label / `column_id`
  - Source-backed description text when available
  - Resolved unit display (or explicit non-unitized marker)
  - Required-field indicator for non-removable identity/join columns
- The collapsed row remains scannable; detailed column picking is opt-in through expansion.
- Column metadata source order is: parquet field metadata (`label`, `description`, `units`) -> interchange `README.md` docs for the resolved source file -> deterministic fallback label/unit inference.
- Required identity/join locks are canonicalized by column token so alias-equivalent keys (for example `topaz_id` vs `TopazID`) do not render as duplicate mandatory selectors.
- Every temporal-capable dataset row includes a temporal mode control (dataset-scoped mode); global year selection remains single and shared.
- Omni Scenarios and Omni Contrasts families render at the bottom of the catalog.
- Output scope controls are discovery-aware: disable `roads` with an explanatory hint when roads outputs are unavailable for the active run/config.
- Family discovery is dynamic: hide groups with no available datasets (for example AgFields when missing inputs).
- Availability/scope readiness updates should stream through websocket status updates so users do not need a manual dataset-detection action.
- Use the dedicated subagent role pack at `wepppy/nodb/mods/features_export/SUBAGENT_ROLES.md` for UI design/development specification and implementation planning.
- Use `wepppy/nodb/mods/features_export/ui_control_layout.md` as the canonical detailed control layout and ASCII wireframe reference.
- Controller posts JSON payload, stores returned `job_id`, and polls canonical `/rq-engine/api/jobstatus/{job_id}` via `set_rq_job_id`.
- Completion details and warnings are read from `/rq-engine/api/jobinfo/{job_id}`.
- Download is enabled when job state is `finished`.
- Controller must attach `attach_status_stream` with stacktrace hooks and keep poll fallback enabled.
- Controller must hydrate prior `job_id` on bootstrap using existing controller-contract guidance.
- Template must include required status panel, stacktrace panel, and job-hint DOM hooks with `aria-live="polite"` status behavior.
- Built-in profile source-of-truth files live in:
  - `wepppy/nodb/mods/features_export/profiles/post-wepp.yml`
  - `wepppy/nodb/mods/features_export/profiles/prep-details.yml`
  - `wepppy/nodb/mods/features_export/profiles/temporal-yearly.yml`
- Virtual quick profiles (for example `prep_wepp_gpkg_gdb`) are discoverable through bootstrap payload composition and intentionally do not require a dedicated file under `profiles/`.
- Published download profile IDs are canonical kebab-case tokens (`prep-wepp`, `prep-wepp-geodatabase`, `prep-details`) and may map to built-in profile aliases during cutover (`post_wepp` -> `prep-wepp`, `prep_details` -> `prep-details`).
- `prep-details.yml` is the canonical replacement profile for legacy `prep_details` export behavior and defaults to `format=csv`.
- `temporal-yearly.yml` is the canonical built-in preset that exercises yearly temporal measures (`wepp.interchange.loss_all_years_hill`).

## 11. Manifest And Warning Contract
Every artifact includes:
- `manifest.json` (canonical machine-readable metadata/provenance contract).
- generated `README.md` (human-readable metadata summary derived from resolved export metadata).

### 11.1 Geospatial Metadata Standards Baseline For Artifact README
The generated `README.md` must align with established geospatial metadata guidance and format standards:
- FGDC CSDGM v2 (`FGDC-STD-001-1998`) and FGDC CSDGM Essential Metadata Elements for minimum discovery, contact, extent, quality, and lineage coverage.
  - References:
    - https://www.fgdc.gov/metadata/csdgm-standard
    - https://www.fgdc.gov/metadata/documents/CSDGMEssentialMeta_20080514.pdf
- FGDC-endorsed ISO 191** metadata suite baseline with ISO 19115-1 Fundamentals as the core model.
  - Reference: https://www.fgdc.gov/metadata/iso-suite-of-geospatial-metadata-standards
- USGS metadata best practices for practical quality guardrails (descriptive title, abstract/purpose, update dates, DOI-as-URL when present, and packaging metadata with data).
  - Reference: https://www.usgs.gov/data-management/metadata-creation
- GeoParquet v1.1.0 metadata requirements for geometry encoding and CRS semantics in parquet payloads.
  - Reference: https://geoparquet.org/releases/v1.1.0/
- OGC GeoPackage metadata extension model (`gpkg_metadata`, `gpkg_metadata_reference`) for standards-compatible metadata carriage in GPKG ecosystems.
  - Reference: https://docs.ogc.org/is/12-128r19/12-128r19.html
- GeoJSON RFC 7946 CRS and bbox semantics for GeoJSON payload interpretation.
  - Reference: https://www.rfc-editor.org/rfc/rfc7946

### 11.2 Available Metadata Inputs For README Generation (Current Implementation)
Metadata already available today (no new science/data-source contracts required):
- Manifest/request context:
  - `request.resolved` (`format`, `units`, `crs`, `output_scopes`, temporal selectors, scenario/contrast selectors, SWAT selectors, column selection, tabular options)
  - `generated_at_utc`, `cache_hit`, `source_job_id`, `artifact_id`
- Artifact and packaging context:
  - `artifact.format`, `artifact.artifact_relpath`, `artifact.packaged_member_relpaths`
- Layer-level context:
  - `layer_id`, `output_layer_id`, `family`, `scope_class`, `scope`, `context`, `selector_id`, `carrier_layer`, `temporal_mode`
  - `row_count`, `feature_count`, `artifact_relpath`
  - output column metadata (`source_layer_ids`, `selected_columns`, `unit_mapping`, materialization strategy metadata)
- CRS/projection context:
  - `crs.requested_crs`, `crs.resolved_crs`, `crs.resolved_epsg` (when available)
- Dependency and lineage context:
  - `dependency_snapshot.catalog_signature`, `dependency_snapshot.fingerprint`
  - per dependency entry: `relpath`, `exists`, `size`, `mtime_ns`, `content_hash_*`, `dependency_role`, `dependency_id`
- QA/status context:
  - `warnings` with canonical warning codes and optional `layer_id`/`scope`

Known metadata gaps to track separately (do not block initial README rollout):
- Persistent identifiers (DOI/PID) for exported artifacts.
- Explicit distribution license/use constraints and access constraints per export artifact.
- Canonical contact/organization fields for artifact-level metadata ownership.
- Spatial extent (`bbox`) and temporal extent summaries precomputed across all exported layers.
- Formal data-quality measure blocks (beyond warning summaries and source dependency fingerprinting).

### 11.3 Dynamic Artifact README Contract
README generation behavior:
- `README.md` is generated dynamically for each cache-miss artifact publication and packaged into the artifact zip root.
- Cache-hit jobs reuse the cached artifact `README.md`; cache-hit job manifests remain job-scoped and can differ only in `cache_hit`/`source_job_id` context.
- `README.md` is deterministic for the same artifact payload/manifest inputs (stable ordering and section structure).

README minimum sections:
- Export summary:
  - generated timestamp, run/config context, format, units mode, CRS mode.
- Standards and interpretation notes:
  - concise format-specific CRS/metadata interpretation notes (for example GeoJSON RFC 7946 WGS84 semantics, GeoParquet CRS notes).
- Resolved request profile:
  - normalized selectors (`layers`, `output_scopes`, temporal selectors, scenario/contrast selectors, SWAT selectors, tabular layout controls).
- Layer inventory table:
  - output layer id, source layer id(s), context/scope, row count, feature count, artifact member path.
- Column and unit summary:
  - selected columns and resolved unit mapping per output layer.
- Dependency lineage summary:
  - dependency fingerprint, catalog signature, and grouped dependency entries by role.
- Warning summary:
  - warning code/message table with layer/scope attachments when present.
- Machine-readable contract pointer:
  - explicit pointer that `manifest.json` is the canonical machine-readable provenance payload.

README authoring rules:
- Do not include absolute host filesystem paths.
- Do not include secrets/tokens/auth headers.
- Avoid profile replay payload embedding (`profile.yml` is not bundled).
- Prefer concise tables and stable ordering to keep diffs/cache artifacts deterministic.

Manifest minimum fields:
- Resolved request payload and selector defaults.
- CRS metadata (`requested_crs`, `resolved_crs`, `resolved_epsg`).
- Resolved dependency entries with path, existence, timestamp, and fingerprint components.
- Per-layer scope metadata (`baseline|roads|shared`).
- Layer context metadata (`base|scenario|contrast`), selected selector id when applicable, and consolidated geometry carrier (`sbs_map-subcatchments|chan_map-channels`).
- SWAT table profile resolution and per-table spatiality classification.
- Temporal compatibility decisions (selectors applied, selectors defaulted, and layer/table exclusions).
- Conversion summary and unit pass-through fields.
- Unitized column-name mapping (`source_column`, `export_column`, `resolved_unit`, `pass_through_reason`).
- Column-selection decisions by layer (`include`, `exclude`, and required columns auto-retained).
- Row and feature counts per layer.
- Generation timestamps and tool/catalog versions.
- `cache_hit`, `source_job_id`, `artifact_id`.
- Dependency-preparation records (including AgFields interchange auto-prep attempts and outcomes).
- `warnings` array.
- Optional publication metadata when a job is promoted to published profile status:
  - `published_profile`,
  - `published_at_utc`.

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
- `roads_scope_unavailable`
- `legacy_flags_ignored`

## 12. Migration And Cutover
Cutover is immediate with explicit legacy cleanup:
- Remove direct `gpkg_export` route/task usage from rq-engine export routes.
- Remove direct `prep_details` route/task usage from rq-engine export routes.
- Move export ownership from legacy modules (`wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py`) to NoDb `features_export`.
- Rewire run-completion hooks to `features_export` profile execution/publication.
- Keep `/export/geopackage`, `/export/geodatabase`, and `/export/prep_details` as compatibility facades that execute `features_export` profiles.
- Standardize job downloads on `/export/features/job/{job_id}/download` (replace `/export/features/{job_id}/download`).
- Add profile-aware published downloads on `/export/features/published/{profile}/download` backed by `export/features/published/index.json`.
- Keep run-completion toggles functional while routing generation through `features_export` internals.
- Keep artifact bundles profile-file-free (`profile.yml`, built-in profile files are excluded) while including generated artifact `README.md` plus `manifest.json`.
- AgFields parity+ support ships without legacy compatibility shims (single-project assumption).

Back-compat behavior for existing saved configs:
- Persisted run-completion export flags remain active but now drive `features_export` profile execution:
  - `prep_details_on_run_completion` -> published `prep-details`.
  - `arc_export_on_run_completion` -> published orchestration profile `prep-wepp-gpkg-gdb` (co-publishes `prep-wepp` + `prep-wepp-geodatabase`).
- Legacy module imports/writers are removed; flags do not call `wepppy/export/gpkg_export.py` or `wepppy/export/prep_details.py`.
- Legacy module deletion (`gpkg_export.py`, `prep_details.py`) must occur only after explicit human approval based on parity validation evidence (see work-package gate requirements).

## 13. Acceptance Criteria
- All seven formats export successfully on representative runs.
- Dataset merge/materialization path is DuckDB-first for production export payload assembly (no pandas merge loops on the hot path).
- Materialization is key-first/geometry-last: exactly one DuckDB carrier core table per `{context, selector_id, scope, carrier}` plus one final geometry attach.
- Export row counts are bounded by carrier key cardinality; multiplicative row growth from repeated many-to-many joins is a contract failure.
- Single-layer formats produce zipped files with one file per resolved layer.
- Multi-layer formats produce one container artifact per request.
- Base WEPP context exports at most two consolidated spatial layers per requested scope (`sbs_map-subcatchments` and/or `chan_map-channels`).
- Each selected Omni scenario/contrast exports its own consolidated `subcatchments` and/or `channels` layers per requested scope.
- Consolidated layer names follow descriptive run/context naming (for example `{runid}-roads-sbs_map-subcatchments`).
- Partial-scope exports emit warnings and still succeed when at least one scoped layer resolves.
- Non-scope missing requested layers/tables emit `layer_unavailable` or `table_unavailable` warnings and still succeed when at least one export target resolves.
- Geometryless formats (`parquet`, `csv`) export tabular outputs with geometry removed while preserving required identity/join columns.
- Geometryless formats expose `tabular.concatenate_tables` and `tabular.temporal_layout` controls with deterministic writer behavior.
- Parity+ AgFields support is present: boundaries/sub-fields plus AgFields WEPP metric layers sourced from `wepp/ag_fields/output/interchange/*`.
- Requesting AgFields WEPP metric layers triggers on-demand AgFields interchange preparation when needed and proceeds without manual pre-run migration.
- Submit endpoint rejects non-JSON payloads with 415 and validates selector rules with 400/404/409 per contract.
- CRS selection works with `wgs|utm`, defaults to `wgs`, and exports include CRS metadata in manifest.
- UI places global year selection directly after CRS selection.
- Temporal-capable datasets expose per-dataset temporal mode controls.
- Dataset rows expose expandable column-selection panels with visible units.
- Users can include/exclude columns per selected dataset; required identity/join columns remain enforced.
- `yearly` mode exports every available year by default (`year_selection=all`) unless globally filtered.
- Global year selection applies consistently across all applicable selected datasets.
- `event` and `yearly` exports default to `wide` temporal layout with temporal selector tokens appended to measure columns.
- `tabular.temporal_layout=long` emits one temporal selector column (`date`, `return_period`, or `year`) and rejects mixed `event` + `yearly` requests.
- Polling and terminal status behavior align with canonical RQ contract (`finished` success).
- Warnings are present in both `jobinfo.result.warnings` and `manifest.json`.
- Cache hits return 202 with a new lightweight job ID, `cache_hit=true`, and reusable artifact delivery.
- Cache key includes Unitizer settings fingerprint for `units=project` and invalidates on Unitizer preference changes.
- Dependency fingerprint is computed from resolved geometry/sources/dependencies, not task timestamps/preflight status.
- `output_scopes` is case-normalized, deduplicated, and invalid values fail with 400.
- `layer_catalog.yaml` is present, machine-readable, and drives layer discovery/validation.
- UI catalog shows one consolidated `WEPP` family with familiar output names (for example `H.element.parquet`) and does not surface internal labels such as `wepp.temporal.events`.
- Omni Scenarios and Omni Contrasts render at the bottom of the catalog.
- Omni selectors support multi-select and bulk selection controls (`Select All`, `Unselect All`).
- Layer search/filter strip is removed from the control.
- Discovery hides unavailable families and disables unavailable `roads` scope without requiring manual detection refresh.
- `layer_catalog.yaml` schema validation enforces locator vocabulary, temporal mode rules, and join-key precedence.
- Optional measure availability (for example `tsmf`, phosphorus, `QRain`, `QSnow`) follows catalog rules and emits `measure_unavailable` warnings when absent.
- Baseline default export for run `clogging-starch/disturbed9002-wbt-mofe` is a regression anchor with exactly two spatial layers and carrier-aligned feature counts (`66` subcatchments, `27` channels).
- RedisPrep/TaskEnum timestamps and `rq:features_export` tracking are wired.
- `units=si|english|project` all work with manifest conversion metadata.
- Unit-applicable exported columns include unit tokens in column names and are documented in manifest column mapping metadata.
- Applied per-layer column-selection decisions are recorded in manifest metadata.
- Unitizer numeric API foundation (`convert_scalar|convert_sequence|convert_table`, `resolve_target_unit`, `preferences_fingerprint`) is complete and available for `features_export` integration.
- `annual_average`, `yearly`, and `event` modes work; daily is rejected.
- Mixed temporal requests have deterministic partial-export behavior and warning semantics.
- SWAT default all-table export and include/exclude overrides work with profile-based geometry/non-spatial handling.
- Export mod appears on Runs page and follows existing NoDb async controller interaction.
- Run-page control exposes profile quick buttons (current set: built-ins `Prep details`, `Post Wepp`, `Temporal yearly`, plus virtual `Post Wepp (GPKG + GDB)`) and a profile-text load path for pasted profile content.
- All artifact downloads are zip bundles and include export payload members plus `manifest.json` and generated `README.md`.
- Generated `README.md` includes standards-aligned metadata sections (summary, layer inventory, CRS/units, dependency lineage, warnings, and manifest pointer).
- Download routes are standardized to `/export/features/job/{job_id}/download` and `/export/features/published/{profile}/download`.
- `export/features/published/index.json` is authoritative for published profile download resolution (`prep-wepp`, `prep-wepp-geodatabase`, `prep-details`).
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
  column_selection.py         # selected-column resolution and unit inference helpers
  cache_rehydration.py        # cache-entry artifact/layer-output rehydration helpers
  discovery.py                # source discovery and strict required-source handling
  join_planner.py             # join-key normalization and cardinality contracts
  duckdb_materializer.py      # key-first DuckDB attribute materialization
  geometry_carriers.py        # canonical geometry carrier build + final attach
  manifest_builder.py         # manifest-facing per-layer column metadata assembly
  legacy_source_materializer.py   # legacy geometry-first source merge collaborator
  carrier_layer_materializer.py   # carrier-source materialization collaborator
  exporters/
    __init__.py
    base.py                   # common writer contract
    geojson.py
    geoparquet.py
    parquet.py
    csv.py
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

WP-3: Format writers, packaging, and manifest generation (completed 2026-03-26)
- Status: done via `docs/mini-work-packages/20260326_features_export_wp3_execplan.md`.
- Implemented files:
  - `wepppy/nodb/mods/features_export/exporters/__init__.py`
  - `wepppy/nodb/mods/features_export/exporters/base.py`
  - `wepppy/nodb/mods/features_export/exporters/geojson.py`
  - `wepppy/nodb/mods/features_export/exporters/geoparquet.py`
  - `wepppy/nodb/mods/features_export/exporters/kmz.py`
  - `wepppy/nodb/mods/features_export/exporters/geopackage.py`
  - `wepppy/nodb/mods/features_export/exporters/geodatabase.py`
  - `wepppy/nodb/mods/features_export/exporters/packaging.py`
  - `wepppy/nodb/mods/features_export/manifest.py`
  - `tests/nodb/mods/test_features_export_exporters.py`
  - `tests/nodb/mods/test_features_export_manifest.py`
- Contract clarification: writer inputs are explicitly pre-resolved and payload-driven (`ResolvedExportPlan` + per-layer `PreparedLayerPayload` mapping keyed by `output_layer_id`); WP-3 does not resolve or extract source datasets.
- Contract clarification: single-layer formats (`geojson|geoparquet|kmz`) write deterministic one-file-per-layer outputs and return one deterministic zip bundle; multi-layer formats return one container artifact per request.
- Contract clarification: geodatabase writer uses the canonical `f_esri` gpkg conversion boundary and fails explicitly when backend capability is unavailable.
- Contract clarification: geopackage artifacts must be valid SQLite/GPKG containers (not synthesized JSON payload bytes); geodatabase staging gpkg input must use the same container contract.
- Contract clarification: geopackage writer output must be GDAL/OGR-readable for downstream conversion boundaries; implementation uses the GDAL `GPKG` driver and supports both spatial feature payloads and aspatial fallback payloads for interoperability.
- Contract clarification: feature-layer field synthesis must retain null-only properties as nullable columns while preserving numeric field typing for non-null numeric properties.
- Contract clarification: manifest assembly is pure (`build_export_manifest`) and serialization/write (`serialize_export_manifest`, `write_export_manifest`) is a separate step.
- Deliverable: deterministic artifact metadata and manifest generation from pre-resolved plan inputs.

WP-4: Service orchestration and RQ wiring
- Add `service.py` orchestration and thin rq-engine route/task adapters.
- Implement canonical async submit/jobinfo/download behavior.
- Deliverable: end-to-end export job execution for API callers with warning contract.

WP-5: Runs-page UI control integration
- Status: completed 2026-03-26 via `docs/mini-work-packages/20260326_features_export_wp5_execplan.md`.
- Implemented files:
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py`
  - `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
  - `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
  - `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
  - `wepppy/weppcloud/controllers_js/project.js`
  - `wepppy/weppcloud/templates/controls/features_export_pure.htm`
  - `wepppy/weppcloud/controllers_js/features_export.js`
  - `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`
  - `wepppy/weppcloud/static-src/tests/smoke/controller-cases.js`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
  - `tests/weppcloud/routes/test_project_bp.py`
  - `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
- Contract clarification: Runs-page dynamic mod behavior requires both server-side mod metadata (`MOD_UI_DEFINITIONS` + `view/mod/<mod_name>`) and client-side bootstrap registration (`project.js` `MOD_BOOTSTRAP_MAP`) for runtime mod insertion parity with initial page render.
- Contract clarification: the features-export submit route is `rq:export` scoped and explicitly documents/requires `415` for non-JSON payloads; frozen checklist/rules artifacts were aligned accordingly.
- Contract clarification: smoke-case execution requires a pre-submit layer selection for `features_export` because the form submit action is validation-gated until minimum payload requirements are met.
- Contract clarification: service orchestration must always pass a `nodb_ref_resolver` into dependency snapshot construction so catalog `nodb_ref` locators (for example `nodb:watershed.subwta_shp`) resolve deterministically during submit-time cache/dependency planning.
- Contract clarification: features-export status UI must use canonical `control_shell` status-panel plumbing (`status_panel_options`) so `wc-status-panel` theming and shared status-log behavior remain consistent with other controllers.
- Contract clarification: controller submit/bootstrap paths must resolve job IDs from canonical variants (`job_id`, wrapped `Content.job_id`, and keyed `job_ids` maps including `run_features_export`/`run_features_export_rq`) before treating submit as failed.
- Contract clarification: completed features-export result payloads should provide dedicated rq-engine download links (`/api/runs/{runid}/{config}/export/features/job/{job_id}/download`) instead of browse-service relpath URLs.
- Contract clarification: cache-hit reuse must validate geopackage artifact signature; legacy non-SQLite `.gpkg` cache entries are treated as invalid and regenerated through cache-miss execution.
- Contract clarification: rq-engine enqueue selection for cache-hit worker must use validated cache eligibility (artifact format/path integrity), not cache-index presence alone, so invalid legacy entries route to standard execution.
- Contract clarification: submit-time service payload preparation must materialize catalog/dependency-resolved source data into per-layer feature collections (geometry + joined attributes) for default exports; payload-metadata-only `.gpkg` rows are non-compliant for the Runs-page experience.
- Deliverable: fully wired Runs-page control with Jest coverage and updated smoke/route-template invariants.

WP-6: Cutover and legacy retirement
- Status: complete via `docs/work-packages/20260329_features_export_legacy_exports_cutover/` (including GO-approved Phase 8 legacy module deletion).
- Active planning package: `docs/work-packages/20260329_features_export_legacy_exports_cutover/`.
- Replace legacy geopackage/prep-details routes and completion hooks with `features_export` profile-backed execution.
- Add publication-aware download path and registry (`/export/features/published/{profile}/download`, `export/features/published/index.json`) with canonical published profiles `prep-wepp`, `prep-wepp-geodatabase`, and `prep-details`.
- Remove compatibility `/export/features/{job_id}/download` route in favor of `/export/features/job/{job_id}/download`.
- Contract clarification (2026-03-29): rq-engine legacy endpoints `/export/geopackage`, `/export/geodatabase`, and `/export/prep_details` execute through `resolve_published_profile_request` + `execute_features_export`; `geopackage` and `prep_details` publish to `export/features/published/index.json`.
- Contract clarification (2026-03-29): geodatabase cutover path prefers published `prep-wepp-geodatabase` artifact resolution and only triggers on-demand execution when absent/stale.
- Contract clarification (2026-03-29): post-WEPP completion hooks `_post_gpkg_export_rq` and `_post_prep_details_rq` execute profile-backed features-export flows; `_post_gpkg_export_rq` runs orchestration profile `prep-wepp-gpkg-gdb` that executes `prep-wepp` once, co-creates `.gdb`, and publishes both `prep-wepp` and `prep-wepp-geodatabase`.
- `legacy_flags_ignored` warning code remains reserved for explicit legacy-flag migration messaging but is not required for normal profile-routed run-completion execution.
- Require explicit human approval gate after parity and e2e validation evidence before deleting legacy modules (`wepppy/export/gpkg_export.py`, `wepppy/export/prep_details.py`).
- Deliverable: legacy replacement shipped with parity evidence, human approval record, and legacy modules removed.

WP-7: Reconciliation pass for WEPP naming, temporal controls, and consolidated layer outputs (planned 2026-03-27)
- Status: complete via `docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md`; architecture correction landed in WP-8.
- Scope: reconcile taxonomy/UI/selector behavior with operator expectations, replace merge hot path with DuckDB-oriented consolidation for WEPP/Omni contexts, and land deterministic naming/temporal contracts.
- Contract clarification: WEPP outputs are presented as one family with familiar output names; internal labels (for example `wepp.temporal.events`) are hidden.
- Contract clarification: yearly mode must export all years by default and year-selection controls are global while temporal mode selection is dataset-scoped.
- Contract clarification: Omni scenario/contrast selection is multi-select, inherits base WEPP output selection, and supports `Select All`/`Unselect All`.
- Contract clarification: base and Omni WEPP outputs are consolidated to up to two geometry-carrier layers per scope with descriptive run/context layer naming.
- Contract clarification: control layout is hierarchy-first, removes search/filter strip, hides unavailable families, and receives websocket-driven discovery updates.
- Contract clarification: geometryless format tokens `parquet` and `csv` are added as first-class single-layer tabular exports that drop geometry while keeping required identity/join columns.
- Contract clarification: profile-based defaults are first-class (`post-wepp.yml`, `prep-details.yml`, `temporal-yearly.yml`) and replace the legacy defaults/prep-details split behavior.
- Deliverable: reconciled backend/UI contract with regression and performance validation coverage.

WP-8: Key-first carrier materialization rewrite and module maintainability refactor (planned 2026-03-27)
- Status: complete via `docs/mini-work-packages/20260327_features_export_key_first_materialization_execplan.md` (validated 2026-03-28 with `66/27` baseline carrier counts on `clogging-starch/disturbed9002-wbt-mofe`).
- Scope: replace geometry-first dataset materialization with key-first DuckDB carrier-core assembly, enforce one-row-per-key join contracts, canonicalize carrier geometry, and split service orchestration into maintainable collaborators (`discovery`, `join_planner`, `duckdb_materializer`, `geometry_carriers`, `manifest_builder`).
- Contract clarification: no temporary feature flag is allowed; the rewritten key-first path becomes the default implementation.
- Contract clarification: discovery-driven schema extraction (column labels/descriptions/units) is required input to both UI payloads and column-selection validation for layers without explicit catalog `columns`.
- Contract clarification: baseline default exports must materialize only `subcatchments` and `channels` carrier layers with carrier-grain row counts.
- Contract clarification: temporal `event`/`yearly` exports must remain carrier-grain spatially and encode temporal selectors in wide measure column names (no long-format feature duplication).
- Deliverable: maintainable and performant default export path with deterministic cardinality, deterministic naming, and verified small-watershed runtime targets.

WP-9: Service quality compliance closure and strictness coverage completion (planned 2026-03-28)
- Status: complete via `docs/work-packages/20260328_features_export_service_compliance_refactor/`.
- Scope: close QA \"conditionally compliant\" findings by extracting remaining service collaborators, removing dead wrappers, and adding missing strict-required branch coverage.
- Contract clarification: strict required-source behavior is shared across carrier and legacy paths through `discover_layer_sources` policy reuse; required source dependency/file/kind and unresolved required join key all fail explicitly with `materialization_error`.
- Contract clarification: refactor does not change external submit/jobinfo/download contracts; service API behavior remains stable while orchestration internals are decomposed.
- Deliverable: reduced service orchestration complexity, closed medium QA findings, and preserved baseline run-path parity (`66/27` on `clogging-starch/disturbed9002-wbt-mofe`).

WP-10: Standards-aligned artifact `README.md` generation and zip plumbing (planned 2026-03-29)
- Status: planned via `docs/work-packages/20260329_features_export_artifact_readme_metadata/`.
- Scope: generate deterministic, standards-aligned artifact `README.md` from resolved manifest/catalog/request metadata and package it into every features-export zip artifact.
- Contract clarification: `manifest.json` remains canonical for machine-readable consumers; `README.md` is a human-readable derivative and must not diverge from manifest values.
- Contract clarification: artifact bundles exclude profile files (`profile.yml`, built-in profile files) while including generated `README.md` and `manifest.json`.
- Contract clarification: README generation must be deterministic and safe (no absolute paths/secrets), and cache-hit behavior must reuse the cached artifact README.
- Deliverable: end-to-end README generation helper + service packaging integration + regression coverage + documentation/work-package closure artifacts.

### 14.2 Dependency Order And Parallelism
- WP-1 depends on completed WP-0 Unitizer APIs.
- WP-2 depends on WP-1 outputs.
- WP-3 depends on WP-1; can proceed in parallel with late WP-2 testing once plan shape is stable.
- WP-4 depends on WP-2 and WP-3.
- WP-5 can begin after WP-1 contracts stabilize, then finalize against WP-4 endpoints.
- WP-7 depends on WP-4/WP-5 behavior and may revise portions of both.
- WP-8 depends on WP-7 outputs and supersedes WP-7 merge-path assumptions.
- WP-9 depends on WP-8 internals and closes remaining service-quality and strictness-coverage gaps.
- WP-10 depends on WP-9 baseline service contracts and updates artifact packaging/docs contracts.
- WP-6 final cutover validation follows WP-10.

### 14.3 Keep-It-Organized Rules
- Keep planner and validation logic pure and side-effect free.
- Keep file-system and geospatial I/O only inside exporter/service layers.
- Keep route/task files as adapters only; no business logic.
- Keep warning-code definitions centralized in `contracts.py`.
- Keep catalog/path resolution logic centralized in `catalog_loader.py`; no duplicated path construction in writers.
- Keep data-shaping joins/projections in DuckDB SQL paths; avoid pandas merge pipelines in export hot paths.
