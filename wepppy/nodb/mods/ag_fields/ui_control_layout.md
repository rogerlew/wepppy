# AgFields Runs-Page UI Control Layout

Status: Spec-only
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
- On success the route returns feature count, column list, and `field_id_duplicates`. Note: the controller method returns only the duplicates — the route assembles count/columns/timestamp from the NoDb properties it just populated. Render a success chip with count/columns/timestamp; render a separate warning chip for duplicates (non-blocking — duplicates are a data-quality warning, per backend behavior).
- Validation failures (missing `field_id` column, unreadable file) render in the upload status chip with the server message. The backend hard-requires a literal `field_id` column; say so in the instruction copy before the user uploads. CRS problems do NOT surface here — upload validation reads attributes only; a missing CRS is inferred (or fails on non-overlap) during rasterization in stage 2.
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
- Failure modes that surface here, not at upload: un-inferable CRS and field geometry not overlapping the DEM extent. Both render the server message in the stage status chip.
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
- "Run options" collapsible: max workers numeric (blank = auto, help: "Auto uses one worker per CPU core, at most one per sub-field."), and "Clear previous runs and outputs" button wrapping `clear_ag_field_wepp_runs`/`clear_ag_field_wepp_outputs` (confirmation via status chip, not a modal — it only deletes regenerable artifacts).
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
- Partial mappings are saveable — save never blocks on unmapped rows (users map incrementally); only stage 4 gating requires completeness.
- No pagination; the table scrolls within the modal body. Crop counts are typically tens, not thousands.

## 6. Template Structure and DOM Contract

- Template: `templates/controls/ag_fields_pure.htm`. Modal in the same file, outside the shell call, following the Disturbed modal include pattern.
- Shell: `form_id="ag_fields_form"`, title "Agricultural Fields", collapsible shell (default open), status/summary/stacktrace panel options like Batch Runner's compact variant. For the maturity label either add `ag_fields_form` to the shell's `_feature_form_map` or pass `feature_id="ag_fields"` explicitly — the label text itself is registry-derived (see Grounding).
- Controller: `controllers_js/ag_fields.js`, built into the bundle via `build_controllers_js.py`. Singleton bootstrap, delegated events on the control root and the modal root only (`data-action` attributes), no per-row listeners.
- All JS-addressable nodes use `data-role` attributes scoped under the control root, mirroring Batch Runner naming (kebab-case). Required hooks:

| Region | Hooks |
|---|---|
| Stage 1 | `geojson-input`, `upload-button`, `upload-status`, `boundary-summary`, `duplicate-warning`, `field-id-select`, `accessor-display`, `accessor-input`, `accessor-resolution-body`, `confirm-schema-button`, `schema-status` |
| Stage 2 | `build-subfields-button`, `subfields-status`, `subfields-summary`, `show-on-map-button`, `min-area-input` |
| Stage 3 | `mapping-chip`, `open-mapping-button`, `plantdb-input`, `plantdb-upload-button`, `plantdb-status`, `plantfile-table-body` |
| Stage 4 | `run-button`, `run-status`, `max-workers-input`, `clear-runs-button`, `results-links` |
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

All routes are run-scoped and follow existing runs-page conventions. Precedents: Treatments (`rq_engine/treatments_routes.py`) is the closest match for multipart upload + enqueue; the Disturbed SBS upload (`rq_engine/upload_disturbed_routes.py`) is the sync rq-engine upload precedent; Roads is a mixed legacy/new example (Flask `roads_bp.py` plus rq-engine duplicates) — follow Treatments/Disturbed, not the Roads split. All rq-engine routes call `authorize_run_access`. Names below are contractual for hooks/tests; align URL style with those precedents at implementation time.

| Action | Kind | Contract |
|---|---|---|
| Upload field boundaries | sync POST, multipart | Saves into `ag_fields/`, runs `validate_field_boundary_geojson` (returns duplicates only); route assembles field count, column list, timestamp from NoDb state and applies the staleness contract (§10) |
| Confirm schema | sync POST | Validates both values, then sets `field_id_key` + `rotation_accessor`; the backend setters are independent so the route enforces atomicity (validate-then-persist, no partial commit); returns per-year resolution errors on failure |
| Build sub-fields | RQ job | Chains rasterize → abstract (with optional min-area param) → polygonize; publishes to the run status channel |
| Upload plant file zip | multipart POST → RQ job | Saves zip to `ag_fields/`, job runs `handle_plant_file_db_upload`; terminal event carries valid/invalid summary |
| Plant file inventory | sync GET | Valid files, invalid files with reasons, downgrade provenance |
| Delete plant file | sync POST/DELETE | Removes file, returns refreshed inventory + orphaned mapping rows |
| Rotation mapping (read) | sync GET | Unique crops, current lookup rows with validation status, valid plant files, weppcloud management options |
| Rotation mapping (save) | sync POST | JSON rows → server writes `rotation_lookup.tsv` and validates; returns per-row results |
| Run WEPP sub-fields | RQ job | Wraps `run_wepp_ag_fields(max_workers)`; failure payload names sub_field_id/field_id |
| Clear runs/outputs | sync POST | Wraps the two clear methods |
| Sub-fields overlay resource | sync GET | Serves `sub_fields.WGS.geojson` for the map overlay (Roads `resources/roads.json` precedent) |
| State snapshot | sync GET | Everything §4 hydrates from: schema state, counts, staleness flags, mapping completeness, plant file counts, observed-climate readiness, parent-WEPP readiness, active job ids |

## 10. Backend Prerequisites (blocking template/controller work)

1. **`run_wepp_subfield` is broken.** The module-level function references `self.wepp_instance.wepp_bin` (`ag_fields.py:1046`) — a `NameError` on every sub-field run. `wepp_bin` must become a parameter, read from the Wepp NoDb in `run_wepp_ag_fields` and passed through. Stage 4 cannot ship without this fix.
2. **RQ task wrappers do not exist.** `wepppy/rq` has no AgFields tasks; build-subfields chain, plant-db processing, and run-wepp jobs must be added with status-channel publishing and the §7 job keys.
3. **Re-upload staleness contract.** Uploading a new GeoJSON refreshes count/hash/timestamp/columns but leaves `field_id_key`, `rotation_accessor`, and sub-field state untouched. The upload route (or controller) must either clear dependent state or record enough (e.g. the geojson hash sub-fields were built from) for the state snapshot to emit the §4 staleness flags.
4. **`validate_rotation_lookup` returns nothing** — it pretty-prints to stdout (`ag_fields.py:664`). It must return structured per-crop results (and not print) for the mapping save/read routes.
5. **Plant file replace/delete semantics.** No delete method exists. Collision suffixing (`name_1.man`) applies on flatten/rename conflicts, while same-named root-level entries and downgrade outputs can silently overwrite — the semantics are accidental either way. For the fix-and-re-upload loop the upload must deterministically replace same-named files; add an explicit delete method. Suffixing should remain only for genuinely distinct files arriving in one zip.
6. **Invalid plant files are only logged.** Persist the reject list (filename + parse error) on the NoDb alongside `_valid_plant_files` so the inventory endpoint can report it. Also: only lowercase `.man` extensions are extracted — uppercase `.MAN` files are silently ignored; make the extension check case-insensitive.
7. **Rotation mapping writer.** Server-side construction of `rotation_lookup.tsv` from the modal's JSON payload (the TSV format and `CropRotationManager` validation already exist; only a debug dump to a different filename exists today).
8. **weppcloud management options endpoint** (or reuse): id + description list for the run's landuse mapping, for the modal's WEPPcloud source select.
9. **Readiness checks for the state snapshot**: parent-WEPP artifacts (`wepp/runs/p*.sol`/`.cli`), watershed abstraction (`dem/wbt/flovec.tif`), and observed-climate readiness derived from `climate_mode` + parseable observed year bounds (no `is_observed` helper exists).
10. `first_year_only` truncation on the 2017.1 downgrade stays hardcoded off in v1 — not exposed in the UI.
11. Minor: duplicate-field warning uses deprecated `logger.warn` (`ag_fields.py:187`); fix opportunistically.

## 11. Accessibility

- Status chips that change from job flow use `role="status"` / `aria-live="polite"` (Batch Runner precedent).
- The modal follows the shared modal semantics: `role="dialog"`, `aria-modal`, labelled title, focus trap and Escape via the shared modal helper.
- Collapsibles are native `details`/`summary` (from `collapsible_card`) — keyboard-operable for free.
- Dependent selects in the modal must be labelled per row (visually-hidden labels including the crop name, e.g. "Management for Corn").
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
