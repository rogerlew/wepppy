# AgFields Runs-Page UI Control Layout

Status: Implemented and accepted 2026-07-10; internal beta as of 2026-07-11
Audience: template, controller, route, and test implementers for `wepppy/nodb/mods/ag_fields`

## Grounding

- This is a canonical runs-page control: `ui.control_shell(...)` from `controls/_pure_macros.html`, singleton controller in `controllers_js/ag_fields.js`, `controlBase.attach_status_stream`, `set_rq_job_id`, `WCControllerBootstrap.resolveJobId`, delegated events only.
- The feature registry entry supplies `section_template: controls/ag_fields_pure.htm`; the runs page dynamically loads the registered section and controller when the `ag_fields` mod is enabled. The registry is the rendering and navigation source of truth.
- Maturity and access come from `weppcloud/feature_registry/feature_registry.yaml`, not the template. AgFields is an internal beta with `maturity: internal`, `internal_reason: beta`, and `min_role: dev`. Dev-role users receive the real control for initial and dynamic rendering; ordinary users do not receive its navigation or control section. The shell renders the Internal label from the resolved feature id (§6).
- Borrow the Batch Runner's staged-intake patterns (`routes/batch_runner/templates/batch_runner_pure.htm`): ordered section cards inside one shell, per-section empty-state chips, hidden-until-populated panes (`data-role` + `hidden`), upload → inspect → validate → act progression, status chips that collapse when empty.
- Borrow the Disturbed modal pattern (`controls/disturbed_modal.htm`) for the rotation mapping modal: a self-contained top-level `wc-modal` with `data-modal`/`data-modal-dismiss` that self-gates on `'ag_fields' in ron.mods` and is included unconditionally from the runs page. The opener button (`data-modal-open`) lives in the stage 3 panel, not in the modal file.
- Use `ui.collapsible_card(expanded=False)` for every advanced or rarely-touched control (the Climate control's "Advanced options" card is the precedent).
- No new widget frameworks, no client-side routing, no wizard library. Stages are visually ordered panels with gating, not a paged carousel.

## Design Mandate: Do Not Mirror the API

The backend exposes more operations than the user needs to reason about. The UI must NOT mirror that call graph. It presents five stages:

1. Provide field boundaries and confirm how the file is interpreted.
2. Build and review sub-fields.
3. Map crop names to managements, with optional plant-file uploads.
4. Run WEPP on the sub-fields.
5. Integrate the current sub-field results into an isolated watershed rerun.

`rasterize_field_boundaries_geojson`, `periodot_abstract_sub_fields`, and `polygonize_sub_fields` are mechanical consequences of decisions already made — they run as one chained job behind a single button. `set_field_id_key` and `set_rotation_accessor` are pickers populated from the uploaded file's own attribute table — the user must never type a column name from memory. Any layout that surfaces a backend method name as a button label is wrong.

## 1. Control Goals

- Make the staged workflow legible: four labeled, numbered stages, each answering "what do I do next" with one primary action.
- Every stage states its own prerequisites when blocked, in plain language, via a status chip — never a disabled button with no explanation.
- Auto-detect everything detectable: default the field ID column, propose the crop-year pattern from the column names, validate against the observed climate years before the user commits.
- Surface the sub-field abstraction results (counts + map overlay) so users review geometry before spending compute on WEPP runs.
- Keep the visible surface small. Delineation thresholds, executable selection, and cleanup actions live in collapsed `collapsible_card`s. Worker sizing is automatic and is not exposed in the browser.
- Preserve WEPPcloud async expectations: status panel with live log, stacktrace panel, job hint, poll fallback, stable DOM hooks.

## 2. Layout Overview

### 2.1 Desktop ASCII Wireframe

```text
+--------------------------------------------------------------------------------------------------+
| Agricultural Fields                                                [Experimental] [collapse]      |
| Model per-field WEPP runs driven by crop rotation schedules. Work top to bottom.                  |
+--------------------------------------------------------------------------------------------------+
| 1. Field Boundaries                                                                               |
|    Upload a GeoJSON of field polygons with a field_id column and one crop column per year.        |
|    Project header: [EPSG:32611] (shown after the project map is assigned)                         |
|    [GeoJSON file......] [Upload Field Boundaries]                                                 |
|    Current field boundary file: CSB_2008_2024_Hangman_EPSG32611.geojson                          |
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
|    (summary when built: "2,177 fields → 6,626 sub-fields")                                  |
|    Sub-fields load on the map automatically; the map layer control hides/shows them.             |
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
|    > Run options (collapsed: WEPP Exec, compact clear previous runs/outputs action)               |
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
- Projection feedback: `RonViewModel` exposes the assigned map's optional `srid`; once present, every run-header title row shows it as a pill labeled `EPSG:<srid>` (for example, `EPSG:32611`). Stage 1 upload help points users to that pill: matching it is preferred; WGS84 remains accepted; any other projected CRS requires correct CRS metadata. Hide the pill before the project map/SRID exists rather than displaying an unknown placeholder.
- Field ID column: a labeled select populated from the returned column list, defaulting to `field_id`. Most users never touch it.
- Crop-year pattern: the controller JS proposes the pattern by scanning column names for trailing 4-digit years within the observed climate range and grouping by the surrounding template (e.g. `Crop2008…Crop2015` → `Crop{}`). Three outcomes:
  - Exactly one candidate covering every observed year: render as read-only text ("Crop{} — resolves Crop2008…Crop2015") with the collapsible available to override.
  - Multiple candidates: render a select of candidates.
  - No candidate: expand the "Schema options" collapsible automatically, showing a text input and a per-year resolution table (year → resolved column → found/missing) driven by client-side checking, with server-side validation as the source of truth on confirm.
- "Confirm Schema" posts both values in one call. The two backend setters are independent, so the route owns atomicity: validate both values first, persist only if both pass (§9). Server errors (per-year missing columns from `set_rotation_accessor`) render in the schema status chip and expand the collapsible.
- Blocked state: observed-climate readiness is a derived boolean in the state snapshot (climate_mode is an observed mode AND both observed year bounds parse as integers) — `set_rotation_accessor` itself gives no friendly error for missing bounds, so the route/UI must gate before calling it. When not ready, the stage renders a warning chip explaining AgFields requires an observed climate; upload stays enabled, schema confirm is disabled.
- Complete when: `geojson_is_valid` and `field_id_key` and `rotation_accessor` are all set (hydrated from NoDb state).
- Re-upload invalidates downstream stages in the backend: boundary replacement clears the schema selections, refreshes boundary metadata/signatures, and causes server-computed sub-field/run staleness to block later stages. The controller renders those snapshot flags; it does not infer staleness from client-side hashes.

### Stage 2 — Sub-field Delineation

Purpose: run the mechanical chain (rasterize → Peridot abstraction → polygonize) as one job and let the user inspect the result.

- Primary button "Build Sub-fields" enqueues one RQ job that chains `rasterize_field_boundaries_geojson`, `periodot_abstract_sub_fields`, `polygonize_sub_fields`. The words "rasterize", "abstract", and "polygonize" appear only in the status log, never as controls.
- "Delineation options" collapsible: `ui.numeric_field` for minimum sub-field area (m², default 0 = keep everything, help text: "Sub-fields smaller than this are dropped."). A note that rebuilding replaces prior sub-fields and invalidates prior runs.
- Blocked chips: stage 1 incomplete → "Confirm the field boundary schema above first." Watershed abstraction missing (`dem/wbt/flovec.tif` absent) → "Build the watershed subcatchments first." (Peridot asserts both `flovec.tif` and `field_boundaries.tif`, but the latter is produced by this job's own first step, so only `flovec.tif` is a UI gate. The readiness check belongs in the state snapshot — do not rely on Peridot's Python `assert` as the user-facing error.)
- Failure modes that surface here, not at upload: un-inferable/ambiguous CRS and field geometry not overlapping the DEM extent. Both render the server message in the stage status chip. The CRS error must include the project DEM CRS and project/upload bounds and instruct the user to export in that project CRS for best precision or supply correct metadata for another projected CRS.
- Summary on completion (hydrated from `field_n` and `sub_field_n`): "N fields → M sub-fields". There is no separate "Show on Map" action.
- When a successful build reaches its terminal event, the controller re-hydrates state, registers the authenticated `sub_fields.WGS.geojson` resource as the named `AgFields Sub-fields` GL overlay, makes it visible, and refreshes an existing registration with the rebuilt geometry. Hydration also registers and displays an existing current overlay after a page reload.
- After registration, visibility belongs to the shared map layer control. Unchecking `AgFields Sub-fields` removes it only from the visible Deck layer set; it remains in the overlay registry and in the layer control. Checking it again constructs a fresh Deck layer descriptor from the cached GeoJSON, replaces the retained registry reference, and displays it without another HTTP request. Ordinary later state hydration respects that hidden choice; a newly completed rebuild makes the updated overlay visible again for review.
- Instruction copy must tell the user to review before running: sub-field splitting is the point of the tool, and geometry mistakes here poison everything downstream.
- Complete when: `sub_field_n > 0` and `sub_fields.WGS.geojson` exists.

### Stage 3 — Crop Managements

Purpose: produce a complete, valid `rotation_lookup.tsv` without the user ever hand-editing a TSV.

- Headline chip: "N of M crops mapped" — success state when N == M and all rows validate, warning otherwise. M comes from `get_unique_crops()` (available once stage 1 is complete).
- Primary button "Map Crops to Managements" opens the modal (§5). Disabled with an explanatory chip until stage 1 completes (crop enumeration needs the confirmed crop-year pattern and observed climate years; it does not use the field ID column).
- "Plant file database" collapsible, auto-expanded when plant files exist or any mapping row references `plant_file_db`:
  - One-sentence instruction: zip of `.man` files from the USDA rotation builder; extension matching is case-insensitive, 2017.1 files are converted to 98.4 automatically, and filenames are normalized (spaces → underscores).
  - Upload accepts a ZIP up to 100 MB. Archive ingestion rejects unsafe member paths and allows at most 200 members / 600 MB uncompressed before processing.
  - Jim-interface residue-only plant placeholders with nonpositive `hmax` are normalized to `0.00001 m` and recorded in inventory provenance. Active crop scenarios are never normalized by this rule.
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
- The AgFields executable is independent of the parent watershed WEPP executable and is persisted in `ag_fields.nodb`. New projects created from `ag-fields.cfg` default to the capacity-32 `wepp_260714` executable; historical projects retain their persisted executable until a user makes an AgFields selection. The selected executable is submitted with the run request and is the value propagated to every sub-field hillslope process.
- Progress streams to the status panel (the backend already logs "(k/N) sub_field_id=… completed"). No separate progress widget in v1.
- On success: success chip with run count and links — browse `wepp/ag_fields/output/`, and a pointer to Features Export for `AgFields Spatial` / `AgFields Metrics` layers.
- A single sub-field failure aborts the run (backend cancels pending sub-fields; already-running ones finish): the stacktrace panel shows the failing sub-field; the status chip must name the failed `sub_field_id` and its parent `field_id`.

### Stage 5 — Integrate the Watershed

Purpose: run one or all of the field-aware, direct-injection, and connectivity-aware
routing schemes without changing baseline or Stage 4 artifacts.

- The required select uses the exact machine values `concept_1`, `concept_2`,
  `hybrid`, and `all`. Its visible labels are, respectively, "Field-aware hillslope
  routing (routes fields through downstream OFEs)", "Direct sub-field outlet
  injection (preserves independent sub-field results; no buffer routing)",
  "Connectivity-aware mixed routing (injects channel-connected fields; routes
  other fields through OFEs)", and "Run all routing schemes (writes three separate
  results for comparison)". Direct injection is selected initially.
- The primary button posts `agfields/run-watershed` with the exact selection.
  One scheme queues one job; `all` returns and tracks a three-entry `job_ids`
  mapping in Concept 1, Concept 2, hybrid order. The scheme-specific keys are
  `agfields_run_watershed_concept_1`, `agfields_run_watershed_concept_2`, and
  `agfields_run_watershed_hybrid`; all use completion event
  `AGFIELDS_RUN_WATERSHED_TASK_COMPLETED`. The historical
  `agfields_run_watershed` key remains a Concept 2 compatibility alias.
- The stage is blocked until Stage 4 is complete and current, the observed climate
  is supported, and every parent prepared input exists. It shares the AgFields
  single-flight guard with Stages 2–4.
- Each current scheme renders independent running, completed, failed, and stale
  state, its limitation, and its fixed browse path under
  `wepp/ag_fields/watershed/{concept-1,concept-2,hybrid}/`.
- Clear requires a second click and calls `agfields/clear-watershed` with the exact
  selected identifier. Selecting `all` clears the three current scheme roots and
  states only; it preserves the legacy unscoped Concept 2 tree.

## 4. Stage Gating and Staleness

Gating is advisory-but-honest: downstream primary buttons are disabled with an explanatory chip, never silently disabled.

The backend owns invalidation and computes explicit staleness from boundary, schema, sub-field, mapping, and run source signatures. The state snapshot carries those flags; the controller renders what the snapshot says and never diffs hashes itself.

| Event | Effect |
|---|---|
| GeoJSON re-uploaded | Stages 2–5 revert to blocked; prior sub-field summary shows a "stale — rebuild required" warning chip; schema selections reset to auto-detected defaults from the new column list |
| Schema re-confirmed (changed values) | Same as re-upload for stages 2–4; crop list in stage 3 refreshes |
| Sub-fields rebuilt | Stages 4–5 revert to not-run/stale; previous outputs remain on disk until cleared or overwritten; summary chips note prior outputs are stale |
| Stage 4 rerun or parent inputs changed | Stage 5 is stale until the isolated integration is rerun |
| Mapping saved incomplete | Stage 3 chip shows remaining count; stage 4 stays blocked |
| Plant file deleted while referenced | Stage 3 chip gains error state ("mapping references a deleted plant file"); stage 4 blocked |

Hydration: the server-rendered control contains static structure and installed WEPP executable options. All workflow state derives from `GET api/agfields/state`, fetched on bootstrap, after mutations, and after job terminal events. The controller re-hydrates idempotently; a refresh mid-job resolves the active job id, reattaches to its stream, and reconstructs the chips from the snapshot.

## 5. Rotation Mapping Modal

- Top-level `wc-modal` (id `agfields_rotation_modal`, `data-modal`, dialog ~90vw like the Disturbed modal), included from the runs page, opened via `data-modal-open`.
- On open, controller fetches `GET api/agfields/rotation-mapping`: unique crops, current lookup rows, valid plant files, and weppcloud management options (id + description, from the run's landuse mapping).
- One row per unique crop, alphabetized. Columns: crop name (read-only), source (radio pair: WEPPcloud / Plant file), management (dependent select — weppcloud managements or valid plant files; disabled with placeholder until a source is chosen), row status (ok / unmapped / error).
- Rows referencing missing plant files (orphans) render in error state with the missing filename shown; the select offers current valid files to re-map.
- Crops present in the saved lookup but absent from the current schedule are shown in a collapsed "Unused mappings" group at the bottom (kept on save, harmless).
- Footer: Cancel (discard, `data-modal-dismiss`) and "Save Mapping" (posts all rows). Server validates every mapped row (`CropRotationManager` semantics); on a canonical HTTP 400 response containing only renderable `invalid_mapping` row errors, the modal stays open and matching rows show server messages. Expected row-validation feedback remains modal-local and does not overwrite the shared background-job Details panel; malformed, mixed, network, and server failures still populate shared Details. On success the modal closes, unrelated failure details remain intact, the controller re-hydrates state, and the stage 3 chip refreshes.
- Partial mappings are savable — save never blocks on unmapped rows (users map incrementally); only stage 4 gating requires completeness.
- No pagination; the table scrolls within the modal body. Crop counts are typically tens, not thousands.

## 6. Template Structure and DOM Contract

- Template: `templates/controls/ag_fields_pure.htm`. Modal in the same file, outside the shell call, following the Disturbed modal include pattern.
- Shell: `form_id="ag_fields_form"`, title "Agricultural Fields", `feature_id="ag_fields"`, collapsible shell (default open), and compact status/summary/stacktrace panels. The label text is registry-derived (see Grounding).
- Controller: `controllers_js/ag_fields.js`, built into the bundle via `build_controllers_js.py`. Singleton bootstrap, delegated events on the control root and the modal root only (`data-action` attributes), no per-row listeners.
- All JS-addressable nodes use `data-role` attributes scoped under the control root, mirroring Batch Runner naming (kebab-case). Required hooks:

| Region | Hooks |
|---|---|
| Stage 1 | `geojson-input`, `upload-button`, `upload-status`, `boundary-file-display`, `boundary-filename`, `boundary-summary`, `duplicate-warning`, `field-id-select`, `accessor-display`, `accessor-candidates`, `accessor-input`, `accessor-resolution-body`, `confirm-schema-button`, `schema-status` |
| Stage 2 | `build-subfields-button`, `subfields-status`, `subfields-summary`, `min-area-input` |
| Stage 3 | `mapping-chip`, `open-mapping-button`, `plantdb-input`, `plantdb-upload-button`, `plantdb-status`, `plantfile-table-body` |
| Stage 4 | `run-button`, `run-status`, `wepp-bin-select`, `clear-runs-button`, `results-links` |
| Stage 5 | `integration-run-button`, `integration-status`, `integration-clear-button`, `integration-results`, `integration-limitation` |
| Modal | `mapping-table-body`, `mapping-status`, `mapping-save-button`, `unused-mappings`, `unused-mappings-body` |

- Empty status chips collapse via the `:empty { display: none }` pattern.
- Stage panels get stable ids (`agfields_stage_boundaries`, `agfields_stage_subfields`, `agfields_stage_managements`, `agfields_stage_run`) for tests and deep links.
- The shared runs-page and report header title rows expose an assigned map as a `data-project-projection="EPSG:<srid>"` pill. The element is omitted when the `RonViewModel` has no SRID.

## 7. Controller Lifecycle and Event Contract

- Bootstrap re-queries the dynamically inserted DOM, resolves job ids for the three long-running job families via `WCControllerBootstrap.resolveJobId`, attaches status streams/poll fallback, and hydrates gating from the state snapshot. `resolveJobId` matches exact keys only — the job key names are contractual: `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`.
- All mutations go through the route contract (§9); the controller never computes workflow state locally except for the crop-year pattern *suggestion*, which is client-side UX sugar with server confirmation.
- Job completion (via status stream terminal events or poll fallback) triggers one `GET api/agfields/state` re-hydration; no optimistic gating flips.
- Current sub-fields auto-register on initial hydration. A successful build terminal event forces the registered overlay visible and refreshes it; a user-hidden overlay otherwise stays hidden across later hydration.
- Uploads use the shared upload helpers (`forms.js`/`http.js` conventions) with multipart posts; no drag-drop in v1.
- Clear uses an inline two-click confirmation: the second click must occur within eight seconds. No modal is opened because only regenerable artifacts are removed.
- Structured request/job failures are rendered in the stage chip and shared stacktrace panel. `EXCEPTION_JSON` supplies the offending plant filename or WEPP `sub_field_id`/`field_id` when available.
- Preflight checklist key `ag_fields` maps to `TaskEnum.run_ag_fields` and the `#ag-fields` TOC entry. Its emoji is 🌽. AgFields mutations and job submissions clear the timestamp; only successful Stage 4 completion stamps it.

## 8. Copy Guidelines

- Stage instruction = one sentence, imperative, no backend vocabulary. "Rasterize", "polygonize", "abstract", "NoDb", "parquet" never appear in labels or instructions (status log lines may use them).
- Help text under a control is at most one sentence.
- Blocked chips name the unmet prerequisite and where to fix it ("Run the watershed WEPP hillslopes first"), never "prerequisites not met".
- Error chips carry the server message verbatim after a short plain-language lead-in.
- The control description (shell header) links to the AgFields user guide page (`usersum` agricultural-fields ENDUSER doc).

## 9. Implemented Route and Job Contract

All routes are run-scoped under rq-engine and follow the Treatments/Disturbed precedents. Mutations require `rq:enqueue`, reads require `rq:status`, and every route calls `authorize_run_access`. Paths below are relative to the rq-engine `/api` prefix.

| Action | Method and path | Contract |
|---|---|---|
| Upload field boundaries | `POST /runs/{runid}/{config}/agfields/boundaries` (`field_boundaries`) | Accepts `.geojson`/`.json` up to 10 MB, validates before replacing canonical artifacts, and returns field count, columns, timestamp, and duplicates |
| Confirm schema | `POST /runs/{runid}/{config}/agfields/schema` | JSON/form `field_id_key` + `rotation_accessor`; validates and persists both atomically |
| Build sub-fields | `POST /runs/{runid}/{config}/agfields/build-subfields` | Enqueues rasterize → abstract → polygonize with optional `sub_field_min_area_threshold_m2` |
| Upload plant file zip | `POST /runs/{runid}/{config}/agfields/plant-database` (`plant_database`) | Accepts ZIPs up to 100 MB; validates the 200-member/600-MB-uncompressed quotas and member paths, stages a unique archive, and enqueues plant processing |
| Plant file inventory | `GET /runs/{runid}/{config}/agfields/plant-files` | Returns valid files, invalid reasons, downgrade provenance, and replacement flags |
| Delete plant file | `DELETE /runs/{runid}/{config}/agfields/plant-files/{filename}` | Deletes a `.man` basename and returns refreshed inventory plus mapping validation |
| Rotation mapping (read/save) | `GET/POST /runs/{runid}/{config}/agfields/rotation-mapping` | Reads modal data or saves JSON `rows` to canonical `rotation_lookup.tsv` and returns per-row validation |
| Management options | `GET /runs/{runid}/{config}/agfields/management-options` | Returns management id + description pairs from the run's landuse mapping |
| Run WEPP sub-fields | `POST /runs/{runid}/{config}/agfields/run-wepp` | Enforces sub-field, mapping, and parent-WEPP readiness, validates required `wepp_bin`, then enqueues with automatic worker sizing; the worker persists the selected executable before it starts the sub-field runs, and legacy callers may continue to send optional `max_workers` |
| Clear runs/outputs | `POST /runs/{runid}/{config}/agfields/clear` | Clears both regenerable AgFields WEPP directories and recorded run provenance |
| Sub-fields overlay resource | `GET /runs/{runid}/{config}/agfields/sub-fields.geojson` | Serves `sub_fields.WGS.geojson` as `application/geo+json` |
| State snapshot | `GET /runs/{runid}/{config}/agfields/state` | Returns all stage hydration state described below |

The state snapshot has top-level objects `boundary`, `schema`, `subfields`, `mapping`, `plant_files`, `wepp`, `watershed_integration`, `watershed_integrations`, `staleness`, and `readiness`. `boundary.filename` is the persisted source basename shown after reload, with the canonical boundary filename as the compatibility fallback for historical projects. `plant_files` carries valid/invalid counts; the inventory endpoint supplies the detailed rows. `wepp` carries `run_count`, `output_count`, `complete`, and the AgFields-owned `wepp_bin` used to hydrate Stage 4. The singular `watershed_integration` remains the backward-compatible Concept 2 view. `watershed_integrations` carries independent `concept_1`, `concept_2`, and `hybrid` status, staleness, terminal summary/error, job id, fixed browse path, and limitation text. The snapshot also exposes `job_ids` and `active_job_ids` under the Stage 2-4 keys, the three current watershed keys, and the historical Concept 2 alias. Staleness keys are `subfields` and `wepp_runs`; readiness includes observed-climate/year-bound validity, watershed abstraction, parent WEPP readiness, and missing parent WEPP ids.

RQ tasks return their terminal payload through the RQ job result and publish the same payload as `RESULT_JSON` before their completion trigger. Plant processing publishes the valid/invalid inventory; sub-field building publishes field/sub-field counts; WEPP publishes `run_count`. Failures publish `EXCEPTION_JSON`; plant failures include `filename`, and WEPP failures include both `sub_field_id` and parent `field_id`. Completion triggers are `AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED`, `AGFIELDS_PLANTDB_TASK_COMPLETED`, and `AGFIELDS_RUN_WEPP_TASK_COMPLETED`.

The Stage 4 worker clears `TaskEnum.run_ag_fields` when it starts and stamps it only after all sub-field WEPP runs succeed. `preflight2` considers the timestamp fresh only when it is newer than the latest parent WEPP timestamp and the current watershed abstraction, landuse, soils, and climate timestamps. The canonical cross-component contract is `docs/ui-docs/control-ui-styling/preflight_behavior.md#agfields-preflight-integration`.

Async submissions are single-flight per run across all four job families. A concurrent submission, boundary/schema/mapping mutation, plant-file delete, or artifact clear receives HTTP 409 with `error.code="agfields_job_active"` while a job is active; the UI must keep the current stream attached rather than replacing its job id.

## 10. Implemented Backend Behavior

The backend-readiness and acceptance follow-up packages established the behavior the UI relies on. This list is implementation rationale and regression scope, not pending work.

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
12. **Boundary CRS handling:** exact project-UTM coordinates, WGS84, and correctly declared projected CRSs are accepted; ambiguous projected coordinates are rejected with project EPSG/bounds diagnostics.
13. **Management synthesis:** `ManagementRotationSynth(..., mode="stack-and-merge")` preserves the crop timeline and existing setup-year/spring-fall composition while reusing structurally identical definitions and remapping references. It fails before writing when more than WEPP's 20 referenced plant scenarios remain.
14. **Residue placeholder normalization:** archive ingestion applies the ADR-0016 `0.00001 m` floor only to proven residue-only plants with `hmax <= 0`, preserves archived 2017.1 sources, leaves active crops unchanged, and records additive provenance.
15. **AgFields-owned executable:** `[ag_fields] bin` initializes new-project state independently of parent WEPP; `ag-fields.cfg` sets `wepp_dcc52a6`, while historical NoDb payloads without the field retain the parent-WEPP fallback until an AgFields run selection is submitted.
16. **Preflight freshness:** additive Redis timestamp `run_ag_fields` is invalidated by input/artifact mutations and job starts, stamped only on successful Stage 4 completion, and exposed as checklist key `ag_fields` with the 🌽 TOC emoji.

## 11. Accessibility

- Status chips that change from job flow use `role="status"` / `aria-live="polite"` (Batch Runner precedent).
- The modal follows the shared modal semantics: `role="dialog"`, `aria-modal`, labeled title, focus trap and Escape via the shared modal helper.
- Collapsibles are native `details`/`summary` (from `collapsible_card`) — keyboard-operable for free.
- Dependent selects in the modal must be labeled per row (visually-hidden labels including the crop name, e.g. "Management for Corn").
- Disabled primary buttons always have an adjacent visible chip explaining why (gating is never conveyed by disabled state alone).

## 12. Regression Coverage and Acceptance

### Automated coverage

- `controllers_js/__tests__/ag_fields.test.js` contains 10 focused Jest cases covering dynamic bootstrap, snapshot hydration, crop-year detection, stage gating, uploads, modal mapping, active-job conflicts, automatic authenticated sub-field overlay loading/refresh, executable hydration/submission, and the compact clear action.
- `controllers_js/__tests__/map_gl.test.js` proves the layer-control checkbox hides `AgFields Sub-fields` without unregistering it, then rebuilds a visible Deck descriptor from the cached non-empty feature collection without another load.
- `tests/microservices/test_rq_engine_ag_fields_routes.py` covers authorization, payload/error contracts, state hydration, atomic schema confirmation, single-flight behavior, executable validation, and run enqueue behavior.
- `tests/nodb/mods/test_ag_fields_backend_contract.py`, `test_ag_fields_rasterize_crs.py`, and `test_ag_fields_wepp_runner.py` cover NoDb persistence/staleness, archive inventory and normalization, CRS handling, management preparation, and executable propagation.
- `tests/rq/test_ag_fields_rq.py` covers the three job wrappers and structured terminal payloads.
- `tests/wepp/management/test_rotation_stack.py` plus the run-derived `ag_fields_rotation_synth` fixtures cover setup-year merging, structural reuse/reference remapping, the 20-plant preflight, residue-only `hmax` normalization, and representative WEPP replays.
- `tests/weppcloud/routes/test_feature_registry_runtime.py`, `test_pure_controls_render.py`, and `tests/nodb/test_ron_map.py` cover registry loading, template/DOM contracts, current-file display, WEPP options, and conditional projection pills.

### Manual acceptance

The 2026-07-10 walkthrough on `sacral-self-discipline` exercised all four stages with corrected `EPSG:32611` boundaries. It produced 2,177 fields → 6,626 sub-fields, 6,626 run files, and 46,382 output files. Output version evidence matched the job-pinned `wepp_dcc52a6`, and the maintainer accepted the interface. This closes the fresh-project acceptance requirement; evidence is recorded in `docs/work-packages/20260709_ag_fields_runs_page_ui/tracker.md`.

## 13. Known Limitations and Deferred Decisions

1. **Duplicate `field_id` values remain non-blocking.** They are reported as a data-quality warning. Promote them to a blocking upload error only with evidence that real joins require that stricter contract.
2. **Historical executable fallback is intentionally additive.** An AgFields NoDb created before `_wepp_bin` was introduced displays the parent WEPP executable until the user submits an AgFields run selection; new `ag-fields.cfg` projects start with `wepp_dcc52a6`.
3. **Worker tuning is API-only compatibility.** The browser uses automatic sizing and sends no `max_workers`; API callers may provide 1-16. Larger or non-positive values are rejected instead of clamped.
4. **Controller splitting is deferred.** The single controller shares one snapshot, modal, and job lifecycle. Reassess its module boundary only if observed maintenance friction justifies the churn.
