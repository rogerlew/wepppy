# AgFields Runs-Page UI Control Layout

Status: Implemented through automated UI milestones 2026-07-09; fresh-project acceptance pending
Audience: template, controller, route, and test implementers for `wepppy/nodb/mods/ag_fields`

## Grounding

- This is a canonical runs-page control: `ui.control_shell(...)` from `controls/_pure_macros.html`, singleton controller in `controllers_js/ag_fields.js`, `controlBase.attach_status_stream`, `set_rq_job_id`, `WCControllerBootstrap.resolveJobId`, delegated events only.
- Include in `runs0_pure.htm` following its existing idiom: a `show_ag_fields` flag alongside the other `show_*` flags, a `data-mod-nav` nav item, and a `data-mod-section` panel include placed after the WEPP/observed region near roads/geneva. The feature registry alone does not render a section — all three pieces are explicit template work.
- Maturity label comes from the feature registry (`feature_registry/feature_registry.yaml`), not the template. AgFields is currently `maturity: internal`; bump it to a valid registry value (e.g. `experimental` — `alpha` is not in the schema) when the control ships, and the shell renders the label automatically once the feature id resolves (§6).
- Borrow the Batch Runner's staged-intake patterns (`routes/batch_runner/templates/batch_runner_pure.htm`): ordered section cards inside one shell, per-section empty-state chips, hidden-until-populated panes (`data-role` + `hidden`), upload → inspect → validate → act progression, status chips that collapse when empty.
- Borrow the Disturbed modal pattern (`controls/disturbed_modal.htm`) for the rotation mapping modal: a self-contained top-level `wc-modal` with `data-modal`/`data-modal-dismiss` that self-gates on `'ag_fields' in ron.mods` and is included unconditionally from the runs page. The opener button (`data-modal-open`) lives in the stage 3 panel, not in the modal file.
- Use `ui.collapsible_card(expanded=False)` for every advanced or rarely-touched control (the Climate control's "Advanced options" card is the precedent).
- No new widget frameworks, no client-side routing, no wizard library. Stages are visually ordered panels with gating, not a paged carousel.

## Design Mandate: Do Not Mirror the API

The AgFields controller exposes eight public workflow methods. The UI must NOT render eight buttons. The backend call graph is an implementation detail; the user makes four decisions:

1. Provide field boundaries (upload).
2. Confirm how the file is interpreted (ID column, crop-year pattern).
3. Map crop names to managements (plus optional plant file uploads).
4. Run.

`rasterize_field_boundaries_geojson`, `periodot_abstract_sub_fields`, and `polygonize_sub_fields` are mechanical consequences of decisions already made — they run as one chained job behind a single button. `set_field_id_key` and `set_rotation_accessor` are pickers populated from the uploaded file's own attribute table — the user must never type a column name from memory. Any layout that surfaces a backend method name as a button label is wrong.

## 1. Control Goals

- Make the staged workflow legible: four labeled, numbered stages, each answering "what do I do next" with one primary action.
- Every stage states its own prerequisites when blocked, in plain language, via a status chip — never a disabled button with no explanation.
- Auto-detect everything detectable: default the field ID column, propose the crop-year pattern from the column names, validate against the observed climate years before the user commits.
- Surface the sub-field abstraction results (counts + map overlay) so users review geometry before spending compute on WEPP runs.
- Keep the visible surface small. Thresholds, worker counts, and re-run/cleanup actions live in collapsed `collapsible_card`s.
- Preserve WEPPcloud async expectations: status panel with live log, stacktrace panel, job hint, poll fallback, stable DOM hooks.

## 2. Layout Overview

### 2.1 Desktop ASCII Wireframe

```text
+--------------------------------------------------------------------------------------------------+
| Agricultural Fields                                                       [alpha] [collapse]      |
| Model per-field WEPP runs driven by crop rotation schedules. Work top to bottom.                  |
+--------------------------------------------------------------------------------------------------+
| 1. Field Boundaries                                                                               |
|    Upload a GeoJSON of field polygons with a field_id column and one crop column per year.        |
|    [GeoJSON file......] [Upload Field Boundaries]                                                 |
|    (chip: "2,177 fields loaded · 41 columns · uploaded 2026-07-09")                               |
|    (chip, warning, only if present: "12 duplicate field_id values")                               |
|    Field ID column:  [field_id        v]                                                          |
|    Crop-year pattern: "Crop{}"  — resolves Crop2008…Crop2015 (matches observed climate years)     |
|    [Confirm Schema]                                                                               |
|    > Schema options (collapsed: manual pattern entry, per-year resolution table)                  |
+--------------------------------------------------------------------------------------------------+
| 2. Sub-field Delineation                                                                          |
|    Fields are split where they cross hillslope boundaries. Review the result before running WEPP. |
|    [Build Sub-fields]                                                                             |
|    (chip when blocked: "Confirm the field boundary schema above first.")                          |
|    (summary when built: "2,177 fields → 8,109 sub-fields · median 0.9 ha")  [Show on Map]         |
|    > Delineation options (collapsed: minimum sub-field area m², rebuild note)                     |
+--------------------------------------------------------------------------------------------------+
| 3. Crop Managements                                                                               |
|    Map every crop name in the rotation schedule to a WEPP management.                             |
|    (chip: "14 of 17 crops mapped" | warning state until complete)                                 |
|    [Map Crops to Managements]   <- opens modal                                                    |
|    > Plant file database (collapsed unless files exist or mapping references plant_file_db)       |
|      Upload a management zip from the USDA rotation builder. Files are converted automatically.   |
|      [Zip file......] [Upload Plant Files]                                                        |
|      table: filename | format | status | [delete]                                                 |
+--------------------------------------------------------------------------------------------------+
| 4. Run WEPP on Sub-fields                                                                         |
|    Runs one WEPP hillslope simulation per sub-field using its parent hillslope soil and climate.  |
|    [Run WEPP on Sub-fields]                                                                       |
|    (chip when blocked: "Run the watershed WEPP hillslopes first — sub-fields reuse their          |
|     soil and climate files.")                                                                     |
|    > Run options (collapsed: max workers, clear previous runs/outputs)                            |
|    (on success: links — browse outputs, export via Features Export)                               |
+--------------------------------------------------------------------------------------------------+
| Status Panel (compact, live log)                                                                  |
| Stacktrace Panel (hidden until exception)                                                         |
| Job hint                                                                                          |
+--------------------------------------------------------------------------------------------------+
```

Stages stack vertically at all breakpoints; there is no side column. Detail tables get `wc-table-wrapper` horizontal scroll on narrow viewports.

### 2.2 Rotation Mapping Modal ASCII Wireframe

```text
+------------------------------------------------------------------------------+
| Map Crops to Managements                                              [x]    |
| Every crop below appears in the rotation schedule. Choose a management       |
| source and file for each. Unmapped crops block the WEPP run.                 |
+------------------------------------------------------------------------------+
| Crop         | Source                  | Management                 | Status |
|--------------|-------------------------|----------------------------|--------|
| Alfalfa      | (o) WEPPcloud ( ) Plant | [Alfalfa (id 42)       v]  |  ok    |
| Corn         | ( ) WEPPcloud (o) Plant | [corn_spring_NT.man    v]  |  ok    |
| Spring Wheat | ( ) WEPPcloud ( ) Plant | [choose a source first...] | unmapped |
| Barley       | ( ) WEPPcloud (o) Plant | [barley_MT.man  (missing)] | error  |
+------------------------------------------------------------------------------+
| (chip: "1 crop unmapped · 1 mapping references a deleted plant file")        |
|                                              [Cancel]  [Save Mapping]        |
+------------------------------------------------------------------------------+
```

## 3. Stage Definitions

Every stage is a `wc-panel` section inside the shell with a numbered `wc-panel__title`, a one-sentence instruction in `wc-text-muted`, one primary action, a status/summary region, and at most one collapsed `collapsible_card`.

### Stage 1 — Field Boundaries

Purpose: get a valid boundary file and freeze its interpretation.

- Upload: `ui.file_upload` accepting `.geojson,.json`, primary button "Upload Field Boundaries". Upload is synchronous (route runs `validate_field_boundary_geojson`); button shows busy state while in flight.
- Current file: after hydration, render the persisted source basename in its own `ui.text_display` control below the upload input. Historical projects without source-name metadata fall back to the canonical boundary filename. Hide the control when no boundary file exists; a reload must not make the accepted upload appear lost merely because browsers cannot repopulate file inputs.
- On success the route returns feature count, column list, and `field_id_duplicates`. Note: the controller method returns only the duplicates — the route assembles count/columns/timestamp from the NoDb properties it just populated. Render a success chip with count/columns/timestamp; render a separate warning chip for duplicates (non-blocking — duplicates are a data-quality warning, per backend behavior).
- Validation failures (missing `field_id` column, unreadable file) render in the upload status chip with the server message. The backend hard-requires a literal `field_id` column; say so in the instruction copy before the user uploads. CRS problems do NOT surface here — upload validation reads attributes only; CRS resolution and extent validation occur during rasterization in stage 2.
- Boundary CRS contract: for maximum overlay and rasterization precision, the preferred input is a GeoJSON whose coordinates are already in the exact projected UTM CRS used by the project DEM. AgFields recognizes unlabeled coordinates that match the project UTM coordinate domain/bounds even though GeoJSON readers commonly default unlabeled files to `EPSG:4326`. Longitude/latitude WGS84 remains supported and is reprojected to the DEM CRS. A different projected CRS is supported only when the file carries CRS metadata that GDAL can resolve; AgFields must not guess an arbitrary projection from ambiguous numeric coordinates.
- Field ID column: `ui.select_field` populated from the returned column list, defaulting to `field_id`. Most users never touch it.
- Crop-year pattern: the controller JS proposes the pattern by scanning column names for trailing 4-digit years within the observed climate range and grouping by the surrounding template (e.g. `Crop2008…Crop2015` → `Crop{}`). Three outcomes:
  - Exactly one candidate covering every observed year: render as read-only text ("Crop{} — resolves Crop2008…Crop2015") with the collapsible available to override.
  - Multiple candidates: render a select of candidates.
  - No candidate: expand the "Schema options" collapsible automatically, showing a text input and a per-year resolution table (year → resolved column → found/missing) driven by client-side checking, with server-side validation as the source of truth on confirm.
- "Confirm Schema" posts both values in one call. The two backend setters are independent, so the route owns atomicity: validate both values first, persist only if both pass (§9). Server errors (per-year missing columns from `set_rotation_accessor`) render in the schema status chip and expand the collapsible.
- Blocked state: observed-climate readiness is a derived boolean in the state snapshot (climate_mode is an observed mode AND both observed year bounds parse as integers) — `set_rotation_accessor` itself gives no friendly error for missing bounds, so the route/UI must gate before calling it. When not ready, the stage renders a warning chip explaining AgFields requires an observed climate; upload stays enabled, schema confirm is disabled.
- Complete when: `geojson_is_valid` and `field_id_key` and `rotation_accessor` are all set (hydrated from NoDb state).
- Re-upload must invalidate downstream stages. The backend does not do this today — upload only refreshes count/hash/timestamp/columns and leaves `field_id_key`, `rotation_accessor`, and sub-field state untouched — so staleness is a backend prerequisite (§10), signaled through the state snapshot, not inferred client-side.

### Stage 2 — Sub-field Delineation

Purpose: run the mechanical chain (rasterize → Peridot abstraction → polygonize) as one job and let the user inspect the result.

- Primary button "Build Sub-fields" enqueues one RQ job that chains `rasterize_field_boundaries_geojson`, `periodot_abstract_sub_fields`, `polygonize_sub_fields`. The words "rasterize", "abstract", and "polygonize" appear only in the status log, never as controls.
- "Delineation options" collapsible: `ui.numeric_field` for minimum sub-field area (m², default 0 = keep everything, help text: "Sub-fields smaller than this are dropped."). A note that rebuilding replaces prior sub-fields and invalidates prior runs.
- Blocked chips: stage 1 incomplete → "Confirm the field boundary schema above first." Watershed abstraction missing (`dem/wbt/flovec.tif` absent) → "Build the watershed subcatchments first." (Peridot asserts both `flovec.tif` and `field_boundaries.tif`, but the latter is produced by this job's own first step, so only `flovec.tif` is a UI gate. The readiness check belongs in the state snapshot — do not rely on Peridot's Python `assert` as the user-facing error.)
- Failure modes that surface here, not at upload: un-inferable/ambiguous CRS and field geometry not overlapping the DEM extent. Both render the server message in the stage status chip. The CRS error must include the project DEM CRS and project/upload bounds and instruct the user to export in that project CRS for best precision or supply correct metadata for another projected CRS.
- Summary on completion (hydrated from `field_n`, `sub_field_n`, `sub_field_fp_n`): "N fields → M sub-fields". Include "Show on Map": follow the Roads precedent — a run-scoped resource endpoint serves `sub_fields.WGS.geojson` (as `roads_bp.py` serves `resources/roads.json`) and the controller registers a named overlay via the GL map's `addGeoJsonOverlay`, refreshing it after rebuilds.
- Instruction copy must tell the user to review before running: sub-field splitting is the point of the tool, and geometry mistakes here poison everything downstream.
- Complete when: `sub_field_n > 0` and `sub_fields.WGS.geojson` exists.

### Stage 3 — Crop Managements

Purpose: produce a complete, valid `rotation_lookup.tsv` without the user ever hand-editing a TSV.

- Headline chip: "N of M crops mapped" — success state when N == M and all rows validate, warning otherwise. M comes from `get_unique_crops()` (available once stage 1 is complete).
- Primary button "Map Crops to Managements" opens the modal (§5). Disabled with an explanatory chip until stage 1 completes (crop enumeration needs the confirmed crop-year pattern and observed climate years; it does not use the field ID column).
- "Plant file database" collapsible, auto-expanded when plant files exist or any mapping row references `plant_file_db`:
  - One-sentence instruction: zip of `.man` files from the USDA rotation builder; 2017.1 files are converted to 98.4 automatically; filenames are normalized (spaces → underscores). Only lowercase `.man` extensions are processed today — uppercase `.MAN` entries are silently ignored (backend prerequisite §10).
  - A single unreadable 2017.1 file aborts the whole processing job (backend raises); the terminal event must name the offending file so the user can fix the zip.
  - Zip upload → RQ job (extract/downgrade/validate streams to the status panel).
  - Inventory table: final filename, format badge ("2017.1 → 98.4" for downgraded files), validation status, delete button per row. Files that failed validation appear with their parse error and no delete ambiguity — the user must be able to see exactly which names are usable in the mapping.
  - Uploading a file whose normalized name already exists replaces it (backend prerequisite §10.3); the table notes replacement in its status column after upload.
- Complete when: every unique crop has a mapping row that validates server-side (weppcloud IDs resolve, plant file paths exist).

### Stage 4 — Run WEPP on Sub-fields

Purpose: run and monitor the per-sub-field simulations.

- Primary button "Run WEPP on Sub-fields" enqueues the RQ job wrapping `run_wepp_ag_fields`.
- Blocked chips, checked in order: stage 2 incomplete → "Build sub-fields first." Stage 3 incomplete → "Map all crops to managements first (N unmapped)." Parent WEPP hillslope artifacts missing (`wepp/runs/p*.sol`/`.cli`) → "Run the watershed WEPP hillslopes first — sub-fields reuse their soil and climate files."
- "Run options" collapsible: a "WEPP Exec" select populated from the same installed-binary list as the main WEPP control, and a content-width "Clear previous runs and outputs" button wrapping `clear_ag_field_wepp_runs`/`clear_ag_field_wepp_outputs` (confirmation via status chip, not a modal — it only deletes regenerable artifacts). Do not expose the executor worker count in this UI.
- The AgFields executable is independent of the parent watershed WEPP executable and is persisted in `ag_fields.nodb`. New projects created from `ag-fields.cfg` default to `wepp_dcc52a6`; historical projects that predate the setting retain their parent WEPP executable until a user makes an AgFields selection. The selected executable is submitted with the run request and is the value propagated to every sub-field hillslope process.
- Progress streams to the status panel (the backend already logs "(k/N) sub_field_id=… completed"). No separate progress widget in v1.
- On success: success chip with run count and links — browse `wepp/ag_fields/output/`, and a pointer to Features Export for `AgFields Spatial` / `AgFields Metrics` layers.
- A single sub-field failure aborts the run (backend cancels pending sub-fields; already-running ones finish): the stacktrace panel shows the failing sub-field; the status chip must name the failed `sub_field_id` and its parent `field_id`.

## 4. Stage Gating and Staleness

Gating is advisory-but-honest: downstream primary buttons are disabled with an explanatory chip, never silently disabled.

The staleness signals below are not free: the backend keeps `geojson_hash`/`geojson_timestamp` but never invalidates downstream state on re-upload, so the state snapshot must carry explicit staleness flags computed server-side (§10). The controller renders what the snapshot says; it does not diff hashes itself.

| Event | Effect |
|---|---|
| GeoJSON re-uploaded | Stages 2–4 revert to blocked; prior sub-field summary shows a "stale — rebuild required" warning chip; schema selections reset to auto-detected defaults from the new column list |
| Schema re-confirmed (changed values) | Same as re-upload for stages 2–4; crop list in stage 3 refreshes |
| Sub-fields rebuilt | Stage 4 reverts to not-run; previous outputs remain on disk until cleared or overwritten; summary chip notes prior outputs are stale |
| Mapping saved incomplete | Stage 3 chip shows remaining count; stage 4 stays blocked |
| Plant file deleted while referenced | Stage 3 chip gains error state ("mapping references a deleted plant file"); stage 4 blocked |

Hydration: all gating state derives from one snapshot (template context at render + `GET api/agfields/state` after job completion events). The controller re-hydrates idempotently — refresh mid-job must reattach to the stream and reconstruct chips (Batch Runner's runstate hydration is the pattern).

## 5. Rotation Mapping Modal

- Top-level `wc-modal` (id `agfields_rotation_modal`, `data-modal`, dialog ~90vw like the Disturbed modal), included from the runs page, opened via `data-modal-open`.
- On open, controller fetches `GET api/agfields/rotation-mapping`: unique crops, current lookup rows, valid plant files, and weppcloud management options (id + description, from the run's landuse mapping).
- One row per unique crop, alphabetized. Columns: crop name (read-only), source (radio pair: WEPPcloud / Plant file), management (dependent select — weppcloud managements or valid plant files; disabled with placeholder until a source is chosen), row status (ok / unmapped / error).
- Rows referencing missing plant files (orphans) render in error state with the missing filename shown; the select offers current valid files to re-map.
- Crops present in the saved lookup but absent from the current schedule are shown in a collapsed "Unused mappings" group at the bottom (kept on save, harmless).
- Footer: Cancel (discard, `data-modal-dismiss`) and "Save Mapping" (posts all rows). Server validates every row (`CropRotationManager` semantics); on any error the modal stays open, failing rows show server messages, valid rows persist state client-side. On success the modal closes and the stage 3 chip refreshes.
- Partial mappings are savable — save never blocks on unmapped rows (users map incrementally); only stage 4 gating requires completeness.
- No pagination; the table scrolls within the modal body. Crop counts are typically tens, not thousands.

## 6. Template Structure and DOM Contract

- Template: `templates/controls/ag_fields_pure.htm`. Modal in the same file, outside the shell call, following the Disturbed modal include pattern.
- Shell: `form_id="ag_fields_form"`, title "Agricultural Fields", collapsible shell (default open), status/summary/stacktrace panel options like Batch Runner's compact variant. For the maturity label either add `ag_fields_form` to the shell's `_feature_form_map` or pass `feature_id="ag_fields"` explicitly — the label text itself is registry-derived (see Grounding).
- Controller: `controllers_js/ag_fields.js`, built into the bundle via `build_controllers_js.py`. Singleton bootstrap, delegated events on the control root and the modal root only (`data-action` attributes), no per-row listeners.
- All JS-addressable nodes use `data-role` attributes scoped under the control root, mirroring Batch Runner naming (kebab-case). Required hooks:

| Region | Hooks |
|---|---|
| Stage 1 | `geojson-input`, `upload-button`, `upload-status`, `boundary-file-display`, `boundary-filename`, `boundary-summary`, `duplicate-warning`, `field-id-select`, `accessor-display`, `accessor-input`, `accessor-resolution-body`, `confirm-schema-button`, `schema-status` |
| Stage 2 | `build-subfields-button`, `subfields-status`, `subfields-summary`, `show-on-map-button`, `min-area-input` |
| Stage 3 | `mapping-chip`, `open-mapping-button`, `plantdb-input`, `plantdb-upload-button`, `plantdb-status`, `plantfile-table-body` |
| Stage 4 | `run-button`, `run-status`, `wepp-bin-select`, `clear-runs-button`, `results-links` |
| Modal | `mapping-table-body`, `mapping-status`, `mapping-save-button`, `unused-mappings` |

- Empty status chips collapse via the `:empty { display: none }` pattern.
- Stage panels get stable ids (`agfields_stage_boundaries`, `agfields_stage_subfields`, `agfields_stage_managements`, `agfields_stage_run`) for tests and deep links.

## 7. Controller Lifecycle and Event Contract

- Bootstrap resolves job ids for the three long-running job families via `WCControllerBootstrap.resolveJobId`, reattaches status streams, then hydrates gating from the state snapshot. `resolveJobId` matches exact keys only — the job key names are contractual: `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`.
- All mutations go through the route contract (§9); the controller never computes workflow state locally except for the crop-year pattern *suggestion*, which is client-side UX sugar with server confirmation.
- Job completion (via status stream terminal events or poll fallback) triggers one `GET api/agfields/state` re-hydration; no optimistic gating flips.
- Uploads use the shared upload helpers (`forms.js`/`http.js` conventions) with multipart posts; no drag-drop in v1.

## 8. Copy Guidelines

- Stage instruction = one sentence, imperative, no backend vocabulary. "Rasterize", "polygonize", "abstract", "NoDb", "parquet" never appear in labels or instructions (status log lines may use them).
- Help text under a control is at most one sentence.
- Blocked chips name the unmet prerequisite and where to fix it ("Run the watershed WEPP hillslopes first"), never "prerequisites not met".
- Error chips carry the server message verbatim after a short plain-language lead-in.
- The control description (shell header) links to the AgFields user guide page (`usersum` agricultural-fields ENDUSER doc).

## 9. Route and Job Contract (new backend surface)

All routes are run-scoped under rq-engine and follow the Treatments/Disturbed precedents. Mutations require `rq:enqueue`, reads require `rq:status`, and every route calls `authorize_run_access`. Paths below are relative to the rq-engine `/api` prefix.

| Action | Method and path | Contract |
|---|---|---|
| Upload field boundaries | `POST /runs/{runid}/{config}/agfields/boundaries` (`field_boundaries`) | Accepts `.geojson`/`.json` up to 10 MB, validates before replacing canonical artifacts, and returns field count, columns, timestamp, and duplicates |
| Confirm schema | `POST /runs/{runid}/{config}/agfields/schema` | JSON/form `field_id_key` + `rotation_accessor`; validates and persists both atomically |
| Build sub-fields | `POST /runs/{runid}/{config}/agfields/build-subfields` | Enqueues rasterize → abstract → polygonize with optional `sub_field_min_area_threshold_m2` |
| Upload plant file zip | `POST /runs/{runid}/{config}/agfields/plant-database` (`plant_database`) | Validates ZIP quotas/member paths, stages a unique archive, and enqueues plant processing |
| Plant file inventory | `GET /runs/{runid}/{config}/agfields/plant-files` | Returns valid files, invalid reasons, downgrade provenance, and replacement flags |
| Delete plant file | `DELETE /runs/{runid}/{config}/agfields/plant-files/{filename}` | Deletes a `.man` basename and returns refreshed inventory plus mapping validation |
| Rotation mapping (read/save) | `GET/POST /runs/{runid}/{config}/agfields/rotation-mapping` | Reads modal data or saves JSON `rows` to canonical `rotation_lookup.tsv` and returns per-row validation |
| Management options | `GET /runs/{runid}/{config}/agfields/management-options` | Returns management id + description pairs from the run's landuse mapping |
| Run WEPP sub-fields | `POST /runs/{runid}/{config}/agfields/run-wepp` | Enforces sub-field, mapping, and parent-WEPP readiness, validates and persists required `wepp_bin`, then enqueues with automatic worker sizing; legacy callers may continue to send optional `max_workers` |
| Clear runs/outputs | `POST /runs/{runid}/{config}/agfields/clear` | Clears both regenerable AgFields WEPP directories and recorded run provenance |
| Sub-fields overlay resource | `GET /runs/{runid}/{config}/agfields/sub-fields.geojson` | Serves `sub_fields.WGS.geojson` as `application/geo+json` |
| State snapshot | `GET /runs/{runid}/{config}/agfields/state` | Returns all stage hydration state described below |

The state snapshot has top-level objects `boundary`, `schema`, `subfields`, `mapping`, `plant_files`, `wepp`, `staleness`, and `readiness`. `boundary.filename` is the persisted source basename shown after reload, with the canonical boundary filename as the compatibility fallback for historical projects. `wepp.wepp_bin` is the current AgFields executable and hydrates the Stage 4 selector. The snapshot also exposes `job_ids` (last known ids) and `active_job_ids` (only queued/started/deferred/scheduled ids) under the contractual keys `agfields_build_subfields`, `agfields_plantdb`, and `agfields_run_wepp`. Staleness keys are `subfields` and `wepp_runs`; readiness keys are `observed_climate`, `watershed_abstraction`, `parent_wepp`, observed year bounds, and missing parent WEPP ids.

RQ tasks return their terminal payload through the RQ job result and publish the same payload as `RESULT_JSON` before their completion trigger. Plant processing publishes the valid/invalid inventory; sub-field building publishes field/sub-field counts; WEPP publishes `run_count`. Failures publish `EXCEPTION_JSON`; plant failures include `filename`, and WEPP failures include both `sub_field_id` and parent `field_id`. Completion triggers are `AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED`, `AGFIELDS_PLANTDB_TASK_COMPLETED`, and `AGFIELDS_RUN_WEPP_TASK_COMPLETED`.

Async submissions are single-flight per run across all three job families. A concurrent submission, boundary/schema/mapping mutation, plant-file delete, or artifact clear receives HTTP 409 with `error.code="agfields_job_active"` while a job is active; the UI must keep the current stream attached rather than replacing its job id.

## 10. Backend Prerequisites (implemented 2026-07-09)

The backend-readiness package `docs/work-packages/20260709_ag_fields_backend_readiness/` completed these prerequisites. The list remains as implementation rationale and regression scope for the successor UI package.

1. **`run_wepp_subfield` binary propagation:** `wepp_bin` is explicit and is read from the AgFields NoDb before executor submission; historical AgFields NoDb payloads without that additive key fall back to the parent Wepp NoDb value.
2. **RQ task wrappers:** `wepppy/rq/ag_fields_rq.py` provides build-subfields, plant-db, and run-wepp jobs with the §7 keys and status events.
3. **Re-upload staleness:** boundary replacement clears schema selections; build/run source signatures drive server-side `subfields` and `wepp_runs` staleness.
4. **Structured lookup validation:** `validate_rotation_lookup()` returns per-crop `ok`/`unmapped`/`error` results and does not print.
5. **Plant replace/delete semantics:** re-upload replaces same-named files; archive-local flatten collisions suffix deterministically; `delete_plant_file()` removes a basename.
6. **Invalid and uppercase plant files:** invalid reasons persist in NoDb inventory and `.man` matching is case-insensitive.
7. **Rotation mapping writer:** `write_rotation_lookup()` atomically writes the existing three-column TSV after validating mapped rows.
8. **weppcloud management options:** the mapping response and dedicated endpoint return id + description pairs from the run mapping.
9. **Readiness checks:** the snapshot reports observed climate, `dem/wbt/flovec.tif`, and required parent `.sol`/`.cli` pairs.
10. **2017.1 truncation:** `first_year_only=False` remains fixed and is not exposed in v1.
11. **Logging:** duplicate-field warnings use `logger.warning`.

## 11. Accessibility

- Status chips that change from job flow use `role="status"` / `aria-live="polite"` (Batch Runner precedent).
- The modal follows the shared modal semantics: `role="dialog"`, `aria-modal`, labeled title, focus trap and Escape via the shared modal helper.
- Collapsibles are native `details`/`summary` (from `collapsible_card`) — keyboard-operable for free.
- Dependent selects in the modal must be labeled per row (visually-hidden labels including the crop name, e.g. "Management for Corn").
- Disabled primary buttons always have an adjacent visible chip explaining why (gating is never conveyed by disabled state alone).

## 12. Test Checklist

### Jest (`controllers_js/__tests__/ag_fields.test.js`)
- Singleton bootstrap + idempotent re-hydration from a state snapshot fixture.
- Crop-year pattern detection: single candidate, multiple candidates, no candidate (collapsible auto-expand), partial year coverage.
- Gating matrix transitions from §4 (re-upload resets downstream, mapping incomplete blocks run, orphaned plant file flips stage 3 to error).
- Modal: dependent select enable/disable, per-row error rendering from a save-failure fixture, unused-mappings grouping.
- Upload flows set busy state and render server errors in the correct chip.

### Playwright
- Full staged walk-through against a seeded run with fixture GeoJSON and plant zip: upload → auto-detected schema → build sub-fields → map crops in modal → run blocked on parent WEPP → (with parent WEPP fixture) run enabled.
- Refresh mid-job reattaches the status stream and preserves stage states.

### pytest
- Route contract: each §9 route (auth, payload validation, error shapes); schema-confirm atomicity (bad accessor leaves field_id_key unchanged); mapping save round-trips through `CropRotationManager`.
- RQ tasks: build-subfields chain ordering; run-wepp failure surfaces sub_field_id in the failure payload.

## 13. Open Decisions (flagged for review)

1. **Plant file collapsible default state** — spec says auto-expand when files exist or are referenced; if that proves jumpy, demote to always-collapsed with a count in the summary line.
2. **Duplicate `field_id` values** are non-blocking (matches backend). If real usage shows duplicates producing garbage joins, promote to a blocking error at upload.
3. **Registry maturity value** — AgFields sits at `internal` in the feature registry; the ship decision is which valid value to move it to (`experimental` suggested).
