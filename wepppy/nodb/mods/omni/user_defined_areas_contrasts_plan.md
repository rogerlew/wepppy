# Omni User-Defined Areas Contrasts Plan

> Reference plan for implementing the GeoJSON-driven contrast selection mode in Omni.
> Scope: backend validation, Omni selection logic, UI support, reporting, and tests.

## Goal

Enable `user_defined_areas` contrast selection so a GeoJSON upload can define contrast
groups by polygon, with stable labeling and deterministic ordering.

## Required Behavior

- Accept `omni_contrast_selection_mode = user_defined_areas` in rq-engine.
- `omni_contrast_geojson_name_key` is optional; missing values fall back to the
  `contrast_id` (feature index) for display.
- Contrast IDs follow GeoJSON feature order. Features with no hillslopes are skipped
  and leave gaps so later contrasts keep their original feature index.
- Hillslope inclusion rule: polygon must cover **>= 50%** of the hillslope area.
- Overlapping polygons are allowed; a hillslope can appear in multiple contrasts
  when it meets the >= 50% rule for multiple features.
- Ignore cumulative objective threshold, hillslope limit, and advanced filters in this
  mode (log if provided).
- Contrast names stay parseable: `<control_scenario>,<contrast_id>__to__<contrast_scenario>`.
- Summary rows show the feature label (name key) or fallback to `contrast_id`.

## Inputs and Outputs

- Inputs:
  - `omni_contrast_geojson` upload (or `omni_contrast_geojson_path`)
  - Optional `omni_contrast_geojson_name_key`
  - Control/contrast scenario selections
- Outputs:
  - Sidecar TSVs: `omni/contrasts/contrast_<id>.tsv`
  - Audit trail: `_pups/omni/contrasts/build_report.ndjson`
  - Summary: `contrasts.out.parquet` and HTML summary table

## Data Sources

- Hillslope polygons: `Watershed.subwta_utm_shp` (project CRS).
- Project CRS: `Ron.srid`.
- Control/contrast WEPP outputs:
  - Base scenario: `wepp/output/H<wepp_id>`
  - Scenario clones: `_pups/omni/scenarios/<scenario>/wepp/output/H<wepp_id>`

## Implementation Steps

### 1) rq-engine validation + payload

- File: `wepppy/microservices/rq_engine/omni_routes.py`
- Allow `user_defined_areas` in `_run_omni_contrasts()`.
- Require a GeoJSON upload or path when selection mode is user-defined.
- Keep `omni_contrast_geojson_name_key` optional; pass through to `Omni.parse_inputs`.
- Store upload under `_pups/omni/contrasts/_uploads/<uuid>/`.
- Status: complete (2026-01-18).

### 2) Omni selection logic

- File: `wepppy/nodb/mods/omni/omni.py`
- Branch inside `_build_contrasts()` for `user_defined_areas`:
  - Load `Watershed.subwta_utm_shp` (hillslope polygons) and user GeoJSON.
  - Reproject uploaded GeoJSON to `Ron.srid` using its CRS; if missing CRS, assume WGS
    and reproject to the project CRS (log when assumptions are made).
  - Use geopandas/shapely intersection with spatial index to find candidate overlaps.
  - Compute `intersection_area / hillslope_area` and include if >= 0.5.
  - Skip channels (Topaz IDs ending in `4`) and unknown Topaz IDs.
  - Build contrast mapping for each feature in order (contrast_id = feature index):
    - In-feature hillslopes use **contrast** scenario outputs.
    - All other hillslopes use **control** scenario outputs.
  - Contrast name uses `<control_scenario>,<contrast_id>__to__<contrast_scenario>`;
    keep feature labels separate for display.
  - Store contrast names/mappings in a way that preserves feature-index gaps
    (skip missing sidecars in `run_omni_contrasts()` and `contrasts_report()`).
  - Write sidecar TSVs and build report entries (include `selection_mode`,
    `feature_index`, `area_label`, `n_hillslopes`, and `topaz_ids`) while preserving
    existing fields for compatibility (use nulls where not applicable).
  - If a feature has zero hillslopes, log + write a build report entry with
    `status: "skipped"`, no sidecar, no contrast run (leave contrast_id gap).
- Status: complete (2026-01-18).

### 3) Reporting

- File: `wepppy/nodb/mods/omni/omni.py`
  - Keep `contrasts_report()` parsing stable and ensure the summary table uses the
    GeoJSON label when provided, else `contrast_id`.
- File: `wepppy/weppcloud/routes/nodb_api/omni_bp.py`
  - Confirm summary uses the label/`contrast_id` display value for user-defined mode.
- Status: complete (2026-01-18).

### 4) Frontend

- File: `wepppy/weppcloud/controllers_js/omni.js`
  - Remove the hard reject for non-cumulative modes.
  - For `user_defined_areas`, require GeoJSON file and show a clear error if missing.
- File: `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm`
  - Ensure help text notes optional name key and ordering behavior.
- Status: complete (2026-01-18).

### 5) Tests

- File: `tests/nodb/mods/test_omni.py`
  - GeoJSON feature order -> contrast IDs, labels, and gap handling.
  - >=50% overlap rule with synthetic polygons and hillslopes.
  - Optional name key fallback to `contrast_id`.
  - Overlapping polygons -> hillslopes can appear in multiple contrasts.
- File: `tests/microservices/test_rq_engine_omni_routes.py`
  - Reject missing GeoJSON in user-defined mode.
  - Ensure upload path is passed to Omni inputs.
- Status: complete (2026-01-18). Tests run: `wctl run-pytest tests/nodb/mods/test_omni.py tests/microservices/test_rq_engine_omni_routes.py`

## Acceptance Criteria

- User-defined contrasts run via UI and rq-engine without switching to cumulative.
- Contrast IDs follow GeoJSON feature order.
- Hillslopes assigned only when polygon covers >= 50% of area.
- Feature label (or `contrast_id` fallback) appears in `contrasts_report()` and the contrast summary.
- Tests cover overlap rule, ordering, and rq-engine validation.

## References

- Omni core and docs:
  - `wepppy/nodb/mods/omni/README.md`
  - `wepppy/nodb/mods/omni/omni.py`
  - `wepppy/nodb/mods/omni/omni.pyi`
- RQ engine:
  - `wepppy/microservices/rq_engine/omni_routes.py`
  - `wepppy/rq/omni_rq.py`
  - `docs/mini-work-packages/completed/20260112_rq_api_migration.md`
- UI docs:
  - `docs/ui-docs/control-ui-styling/control-inventory.md`
  - `wepppy/weppcloud/templates/controls/omni_contrasts_pure.htm`
  - `wepppy/weppcloud/controllers_js/README.md`
