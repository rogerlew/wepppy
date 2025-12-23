# SBS Controls Behavior Documentation

**Date**: October 25, 2025  
**Context**: BAER/Disturbed SBS upload and uniform generation controls

## Overview

The SBS (Soil Burn Severity) controls coordinate the Disturbed, Baer, and Map controllers so users can upload a custom raster or generate a uniform severity map while keeping the Leaflet overlay and summary panel in sync.

## Mode System

### Two Modes (Persisted)
1. **Upload Mode** (`sbs_mode = 0`): Upload custom `.tif` or `.img` raster
2. **Uniform Mode** (`sbs_mode = 1`): Generate uniform low/moderate/high severity raster (`uniform_severity` stores the chosen level)

## File Structure

### Frontend
- **Controller**: `wepppy/weppcloud/controllers_js/disturbed.js`
  - Handles upload, uniform generation, removal
  - Syncs with `baer.js` controller for map display
  - Manages "Current SBS map" filename display

- **Template**: `wepppy/weppcloud/templates/controls/disturbed_sbs_pure.htm`
  - Two control sections: `#sbs_mode0_controls` (upload), `#sbs_mode1_controls` (uniform)
  - Radio buttons to switch modes (persisted via `sbs_mode`)
  - Summary panel (`#info`) is filled by the BAER controller via `load_modify_class()`

- **Summary Template**: `wepppy/weppcloud/templates/mods/baer/classify.htm`
  - Rendered by `view/modify_burn_class`
  - Injected into the SBS summary panel after uploads or uniform builds
  - Shows the active uniform severity when `sbs_mode` is 1

- **Map Controller**: `wepppy/weppcloud/controllers_js/map.js`
  - Provides `MapController.getInstance()` which Disturbed/Baer use to add or remove the "Burn Severity Map" overlay
  - Keeps the Leaflet control (`map.ctrls`) in sync to avoid duplicate or orphaned legend entries

### Backend
- **Routes**: `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
  - `task_upload_sbs`: Upload and validate raster
  - `task_build_uniform_sbs`: Generate uniform severity raster
  - `task_remove_sbs`: Remove SBS raster
  - Upload/uniform responses include `{'disturbed_fn': ...}` (no HTML payload today)
  - `view/modify_burn_class`: Returns HTML summary used in the SBS panel

- **NoDb**: `wepppy/nodb/mods/baer/baer.py` and `wepppy/nodb/mods/disturbed/disturbed.py`
  - Stores: `baer_fn` (filename), `has_map` (boolean), `sbs_mode`, `uniform_severity`

## Tested Behaviors

### ✅ Upload Mode
1. **Initial state**: No SBS, Upload mode selected by default
2. **File selection triggers auto-upload**: No separate "Upload" button
3. **Success**: 
   - Map appears on Leaflet with "Burn Severity Map" layer
   - "Current SBS map" display shows filename
4. **Remove button**: Removes map layer and legend; filename display currently remains populated

### ✅ Uniform Mode
1. **Switch to Uniform mode**: Radio button hides upload controls, shows 4 buttons
2. **Four buttons** (all same 240px width):
   - Use Uniform Low SBS
   - Use Uniform Moderate SBS
   - Use Uniform High SBS
   - Remove SBS
3. **Success**:
   - Map appears on Leaflet with "Burn Severity Map" layer
   - BAER summary panel calls out the selected uniform severity
4. **Remove button**: Same behavior as upload mode (map + legend cleared, filename display persists)

### ✅ Re-upload / Regenerate
1. **Multiple uploads**: Old layer removed before new one added (no accumulation)
2. **Multiple uniform generations**: Same behavior, replaces existing
3. **Switch modes**: Can upload, then generate uniform, or vice versa - last one wins

### ✅ Reload Behavior
1. **After upload**: Page reloads → Upload mode selected with filename restored
2. **After uniform**: Page reloads → Uniform mode selected with BAER summary showing the stored severity
3. **Bootstrap**: `disturbed.bootstrap()` calls `baer.bootstrap()` which calls `baer.show_sbs()` to render map

### Bootstrap & State Restoration
1. Run bootstrap JSON injects `controllers.disturbed`/`controllers.baer` with `mode` and `uniformSeverity` (`run_page_bootstrap.js.j2`).
2. `Disturbed.bootstrap(ctx)` seeds the cached `has_sbs` flag, applies the controller context (radio buttons + cached severity), and replays `Baer.bootstrap(ctx)` when an SBS exists.
3. `Baer.bootstrap` binds event listeners and issues an initial `show_sbs()` / `load_modify_class()` so map overlays and summary content match the persisted state.

### Summary Refresh Flow
1. Upload/uniform build responses trigger `disturbed:uniform:completed` / `SBS_UPLOAD_TASK_COMPLETE`.
2. Disturbed schedules `baer.show_sbs()` + `baer.load_modify_class()` to redraw the map overlay and re-render `mods/baer/classify.htm`.
3. The template highlights the active uniform severity (when `sbs_mode == 1`), keeping the info panel aligned with backend state.

## Event Flow

### Upload Flow
```
1. User selects file → auto-upload triggered
2. disturbed.uploadSbs()
   - Clear hints
   - POST /tasks/upload_sbs with FormData (use /upload prefix via `url_for_run(..., { prefix: "/upload" })`)
3. Backend validates, saves to baer_dir
4. Response: {Success: true, Content: {disturbed_fn: "..."}}
5. Frontend:
   - Updates "Current SBS map" display
   - Triggers SBS_UPLOAD_TASK_COMPLETE event
   - Calls baer.show_sbs() to render map
   - Calls baer.load_modify_class() to refresh the summary/classification panel
```

### Uniform Flow
```
1. User clicks "Use Uniform [Low|Moderate|High] SBS"
2. disturbed.buildUniformSbs(severity)
   - Clear hints
   - POST /tasks/build_uniform_sbs with {value: severity}
3. Backend generates uniform raster
4. Response: {Success: true, Content: {disturbed_fn: "..."}}
5. Frontend: (same as upload flow with BAER summary reflecting uniform severity)
```

### Remove Flow
```
1. User clicks "Remove SBS" (in either mode)
2. disturbed.removeSbs()
   - POST /tasks/remove_sbs
3. Backend deletes raster file
4. Response: {Success: true}
5. Frontend:
   - Removes map layer directly via MapController
   - Removes layer from control
   - Clears SBS legend
   - Clears the SBS summary panel (`infoAdapter.html("")`)
   - Leaves "Current SBS map" display populated (needs follow-up if we want clearing)
   - Mode selection remains unchanged
   - Updates has_sbs flag
```

## Cross-Controller Communication

### Disturbed ↔ Baer
- **Two separate forms**: `#sbs_upload_form` (Disturbed) and `#baer_form` (Baer)
- **Event bridge**: Disturbed emits `SBS_UPLOAD_TASK_COMPLETE` / `SBS_REMOVE_TASK_COMPLETE`; Baer listens and re-renders the summary panel via `load_modify_class()`.
- **Direct calls**: Disturbed invokes `baer.show_sbs()`/`load_modify_class()` to refresh the overlay and classification UI after uploads or uniform builds.
- **Timing guard**: A 100 ms `setTimeout` ensures the Baer form has mounted before dispatching map refresh calls.

### Map Controller Integration
- **Overlay lifecycle**: Disturbed and Baer both call `MapController.getInstance()`; when unavailable the code guards with try/catch so backend state still updates.
- **Legend hygiene**: `baer.show_sbs()` clears existing "Burn Severity Map" entries from both the map and control before adding the new overlay to prevent duplicates.
- **Removal path**: Disturbed explicitly removes the overlay and legend during `remove_sbs` so the UI immediately reflects the cleared state.

## Cross-Controller Communication

### Disturbed ↔ Baer
- **Two separate forms**: `#sbs_upload_form` (disturbed) and `#baer_form` (baer)
- **Communication**: Via events and direct method calls
  - `disturbed.triggerEvent('SBS_UPLOAD_TASK_COMPLETE', data)`
  - Direct calls: `baer.show_sbs()`, `baer.load_modify_class()`
- **Timing**: 100ms setTimeout to ensure baer form is ready

### Map Layer Management
- **Layer name**: "Burn Severity Map"
- **Cleanup**: Must remove both from map (`map.removeLayer`) and control (`map.ctrls.removeLayer`)
- **Orphaned layers**: `baer.showSbs()` checks for existing layer and removes before adding new
- **Legend**: Separate element `#sbs_legend`, must be cleared on remove

## CSS Styling

### Button Widths
```css
#sbs_mode1_controls .wc-button-row {
  margin-bottom: var(--wc-space-md);
}

#sbs_mode1_controls .wc-button-row .pure-button {
  min-width: 240px;  /* Ensures all 4 buttons same width */
  justify-content: center;
}
```

### Table Formatting (Classification UI)
```css
.wc-baer-classify__table--breaks {
  max-width: 600px;
}

.wc-text-right {
  text-align: right;
}

.wc-text-bold {
  font-weight: bold;
}
```

## Testing Checklist

### Upload Mode
- [ ] File selection auto-triggers upload
- [ ] Success: Map appears with correct bounds
- [ ] Success: "Current SBS map" displays filename
- [ ] Summary panel renders BAER classification content
- [ ] Error: Error message shown in Status panel
- [ ] Re-upload: Old layer removed, new one appears
- [ ] Remove: Map and legend disappear; filename display stays populated

### Uniform Mode
- [ ] All 4 buttons same width (240px)
- [ ] Low/Moderate/High generate different files
- [ ] Success: Map appears with correct bounds
- [ ] Multiple generations: No layer accumulation
- [ ] Summary panel updates to reflect uniform severity controls
- [ ] Remove: Map disappears, legend clears, mode/filename remain

### Reload Scenarios
- [ ] After upload: Map reappears via bootstrap
- [ ] After uniform: Map reappears via bootstrap
- [ ] Mode selector reflects persisted `sbs_mode`
- [ ] Summary content matches persisted state

### Cross-Browser
- [ ] Safari (macOS)
- [ ] Chrome
- [ ] Firefox

## Related Files

### Frontend
- `wepppy/weppcloud/controllers_js/disturbed.js`
- `wepppy/weppcloud/controllers_js/baer.js`
- `wepppy/weppcloud/templates/controls/disturbed_sbs_pure.htm`
- `wepppy/weppcloud/templates/mods/baer/classify.htm`
- `wepppy/weppcloud/static/css/ui-foundation.css`

### Backend
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- `wepppy/nodb/mods/baer/baer.py`
- `wepppy/nodb/mods/disturbed/disturbed.py`
- `wepppy/nodb/mods/baer/baer.pyi`

### Documentation
- `wepppy/weppcloud/controllers_js/README.md`
- `wepppy/AGENTS.md`
- `docs/dev-notes/sbs_controls_behavior.md` (this file)

## Changelog

### October 25, 2025
- ✅ Fixed duplicate "Burn Severity Map" entries on reload
- ✅ Fixed form value capture bug (read before startTask clears)
- ✅ Removed Upload SBS button, added auto-upload on file select
- ✅ Fixed layer accumulation on re-upload
- ✅ Fixed filename display update after upload
- ✅ Fixed remove functionality (map + legend)
- ✅ Made uniform buttons consistent width (240px)
- ✅ Persists both the `sbs_mode` and `uniform_severity` for reload
- ✅ classify.htm is `sbs_mode` aware
