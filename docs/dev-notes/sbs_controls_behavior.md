# SBS Controls Behavior Documentation

**Date**: October 25, 2025  
**Context**: BAER/Disturbed SBS upload and uniform generation controls

## Overview

The SBS (Soil Burn Severity) controls allow users to either upload a custom raster or generate a uniform severity map. The interface now persists both the active mode (`sbs_mode`) and the uniform severity (`uniform_severity`) alongside the raster metadata so reloads restore the previous selection automatically.

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
  - Radio buttons to switch modes (not persisted)
  - Summary panel (`#info`) is filled by the BAER controller via `load_modify_class()`

- **Summary Template**: `wepppy/weppcloud/templates/mods/baer/classify.htm`
  - Rendered by `view/modify_burn_class`
  - Injected into the SBS summary panel after uploads or uniform builds

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
   - "Current SBS map" display shows filename (only visible in Upload mode section)
4. **Remove button**: Same behavior as upload mode (map + legend cleared, filename display persists)

### ✅ Re-upload / Regenerate
1. **Multiple uploads**: Old layer removed before new one added (no accumulation)
2. **Multiple uniform generations**: Same behavior, replaces existing
3. **Switch modes**: Can upload, then generate uniform, or vice versa - last one wins

### ✅ Reload Behavior
1. **After upload**: Page reloads → Upload mode selected with filename restored
2. **After uniform**: Page reloads → Uniform mode selected with severity banner restored
3. **Bootstrap**: `disturbed.bootstrap()` calls `baer.bootstrap()` which calls `baer.show_sbs()` to render map

### ⚠️ Known Issues

#### Issue 1: Filename Display Placement
**Observation**: The "Current SBS map" field still sits inside the upload panel. When users toggle to uniform mode the filename is hidden even though the raster remains active.

**Improvement Options**:
- Duplicate the filename field in the uniform panel.
- Move the filename display into a shared summary strip above both panels.

#### Issue 2: Uniform Label After Removal
**Observation**: Removing the SBS raster clears the summary panel and map overlays, but the uniform banner keeps the last selected severity so users can recreate it quickly.

**Decision Point**:
- Leave the label in place (current behavior) for faster re-generation.
- Clear the label and require users to pick a severity again if a fully reset experience is preferred.

#### Issue 3: Summary Panel State on Reload
~~**Problem**: Summary panel is empty on page load, even if SBS exists.~~

**Status**: Works fine - the BAER controller injects `mods/baer/classify.htm` after upload/uniform actions.

## Event Flow

### Upload Flow
```
1. User selects file → auto-upload triggered
2. disturbed.uploadSbs()
   - Clear hints
   - POST /tasks/upload_sbs with FormData
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
5. Frontend: (same as upload flow)
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

## Future Improvements

### Option 1: Add Mode to NoDb (Recommended)
**Pros**: 
- Proper state persistence
- Can pre-select correct mode on reload
- Can show mode-specific UI correctly

**Cons**:
- Requires NoDb schema change
- Migration needed for existing runs

**Implementation**:
```python
# In baer.py or disturbed.py
@property
def sbs_mode(self):
    return self._sbs_mode if hasattr(self, '_sbs_mode') else 0

@sbs_mode.setter
@nodb_setter
def sbs_mode(self, value):
    self._sbs_mode = int(value)
```

### Option 2: Infer Mode from Filename
**Pros**: No schema change needed

**Cons**: 
- Fragile (relies on naming convention)
- Breaks if user uploads file named "uniform_*.tif"

**Implementation**: Check if filename starts with "uniform_"

### Option 3: Accept Current Behavior
**Pros**: No changes needed

**Cons**: 
- Confusing UX
- Summary panel empty on reload

**Recommendation**: Document as known limitation

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
- ⚠️ Attempted to add Summary panel updates (partially implemented)


### Known Limitations
1. "Current SBS map" field still lives in the upload panel, so the filename remains hidden when the uniform panel is expanded.
2. Removing the SBS raster keeps the last uniform severity in the UI to ease re-generation; if we decide the label should clear, adjust `disturbed.remove_sbs()`/frontend to reset it.

## Next Steps: Add NoDb Serialization

### Task for GPT-5-Codex

Add the following properties to **both** `Disturbed` class (`wepppy/nodb/mods/disturbed/disturbed.py`) and `Baer` class (`wepppy/nodb/mods/baer/baer.py`):

#### 1. `sbs_mode` Property
- **Type**: `int` (0 = upload, 1 = uniform)
- **Default**: `0`
- **Purpose**: Remember which mode was used to create current SBS
- **Usage**: Pre-select correct radio button on page reload

#### 2. `uniform_severity` Property  
- **Type**: `Optional[int]` (1 = low, 2 = moderate, 3 = high, None = not uniform)
- **Default**: `None`
- **Purpose**: Remember which severity level was selected in uniform mode
- **Usage**: Display "Current: Uniform Moderate SBS" instead of just filename

### Implementation Requirements

1. **Add to `__init__`**:
   ```python
   self._sbs_mode = 0
   self._uniform_severity = None
   ```

2. **Add properties with `@nodb_setter` decorator**:
   ```python
   @property
   def sbs_mode(self) -> int:
       return getattr(self, '_sbs_mode', 0)
   
   @sbs_mode.setter
   @nodb_setter
   def sbs_mode(self, value: int) -> None:
       self._sbs_mode = int(value)
   
   @property
   def uniform_severity(self) -> Optional[int]:
       return getattr(self, '_uniform_severity', None)
   
   @uniform_severity.setter
   @nodb_setter
   def uniform_severity(self, value: Optional[int]) -> None:
       self._uniform_severity = int(value) if value is not None else None
   ```

3. **Update `build_uniform_sbs()` method** to set these values:
   ```python
   def build_uniform_sbs(self, value: int = 4) -> str:
       # ... existing code ...
       
       # Before return, set mode and severity
       self.sbs_mode = 1  # setter will acquire the lock
       self.uniform_severity = value
       
       return sbs_fn
   ```

4. **Update `validate()` method** (called after upload) to set mode:
   ```python
   def validate(self, disturbed_fn: str) -> None:
       # ... existing code ...
       
       # After validation succeeds, set mode (already inside self.locked())
       self._sbs_mode = 0
       self._uniform_severity = None
   ```
   Add a short comment explaining that `validate()` holds the lock, so private
   attributes should be assigned directly to avoid re-entrant locking by the
   `@nodb_setter` wrapper.

5. **Update type stubs** (`.pyi` files):
   - `wepppy/nodb/mods/baer/baer.pyi`
   - `stubs/wepppy/nodb/mods/baer/baer.pyi`
   If Disturbed exports are added to `__all__`, create matching stubs under
   `stubs/wepppy/nodb/mods/disturbed/`.

6. **Update template** (`disturbed_sbs_pure.htm`):
   - Pre-select correct mode based on `disturbed.sbs_mode`
   - Show "Current: Uniform [Low|Moderate|High] SBS" when mode is 1
   - Show "Current SBS map: filename" when mode is 0

7. **Update BAER summary UI**: Adjust `mods/baer/classify.htm` (and the
   corresponding view/controller wiring) so the injected summary reflects the
   new mode/severity fields.

8. **Update JavaScript** (`disturbed.js`):
   - Read initial mode from context/bootstrap
   - Update mode selection on page load
   - Keep `remove_sbs` neutral with respect to mode (per UX guidance)

### Why Both Classes?

- **Disturbed**: Used for standalone disturbed mod
- **Baer**: Subclass used for BAER workflows (will eventually be removed, but needed for now due to WEPP soil compatibility issues in desert climates)
- Both need same properties for consistent behavior

### Testing After Implementation

1. **Upload SBS** → reload → should show:
   - Upload mode selected
   - Summary panel shows upload metadata

2. **Generate Uniform Moderate SBS** → reload → should show:
   - Uniform mode selected
   - Summary panel shows uniform severity
   
3. **Upload after Uniform** → should show:
   - Switch to Upload mode
   - Summary panel shows upload metadata

4. **Uniform after Upload** → should show:
   - Switch to Uniform mode
   - Summary panel shows uniform severity
   
5. **Remove** → should show:
   - No raster on map, but mode stays on the last selection (per UX guidance)
   - Summary panel cleared via `infoAdapter.html("")`
