# Frontend Integration & Smoke Automation

**Status**: Open (2025-02-24)

## Overview
The controller modernization and StatusStream cleanup landed, but the last stretch of the UI upgrade requires coordinated work: finish the remaining Pure-template migrations, rewrite the run-page bootstrap script, and ship a repeatable smoke validation flow. This work package tracks that integration push.

## Objectives
- Deliver a Pure-first runs0 page with modernized controllers (map/delineation + treatments conversions outstanding).
- Replace legacy `run_page_bootstrap.js.j2` wiring with helper-driven initialization that works for the Pure shell.

## Scope
- Update remaining templates/controllers (map, delineation, treatments) to Pure + StatusStream patterns.
- Refactor bootstrap initialization to use controller emitters/helpers instead of direct DOM manipulation.
- Align docs (`control-ui-styling`, `AGENTS.md`) with the new bootstrap implementation.

## Out of Scope
- Deep UX redesign of map/delineation controls beyond necessary modernization.
- Non-controller front-end improvements (e.g., command bar redesign, htmx adoption).
- Full end-to-end Playwright suite (planning only unless time permits).

## Stakeholders
- Frontend controllers team (implementation)
- QA/ops (smoke testing tooling)
- Docs maintainers

## Success Criteria
- Map/delineation and treatments controls run on Pure templates with consistent StatusStream telemetry.
- `run_page_bootstrap.js.j2` supports modern controllers without legacy shim calls.
- Documentation refreshed to match the new entry points and validation steps.

## Remaining 2 % Checklist
- [x] **Map / delineation bundle** – Pure templates verified (map, channel delineation, subcatchments) with StatusStream wiring; control inventory updated.
- [x] **Treatments control** – Pure template + controller confirmed; no legacy fallback required and documentation refreshed.
- [x] **Bootstrap overhaul** – Controller bootstrap contract in place (`run_page_bootstrap.js.j2` + `WCControllerBootstrap`).
- [x] **Map initialization guard** – Fixed race condition where `buildViewportPayload()` was called before map center/zoom set; added Leaflet container reinitialization protection (2025-10-23).
- [x] **Docs & guidance (non-smoke)** – Finalize front-end documentation updates tied to bootstrap changes.
- ⏩ Smoke automation (profiles, CLI, extended flows) tracked under [20251023_smoke_tests](../20251023_smoke_tests/package.md).

## Known Issues & Fixes

## 2025-01-23: Fixes

### Map Bootstrap Fix (Complete)
**Issue**: Map bootstrap logic had three conditional branches, but only one called `setView(center, zoom)` properly. The other two either called `setZoom()` alone or relied on `fitBounds()`, leaving the map without a defined center.

**Fix** (`wepppy/weppcloud/controllers_js/map.js`):
- Refactored `bootstrap()` to ensure ALL branches call `this.map.setView(center, zoom)` with valid coordinates
- Added fallback defaults: `center = center || [0, 0]` and `zoom = zoom || 2`
- Now guarantees map center is always initialized before any controller attempts to read it

**Result**: Eliminates "Set map center and zoom first" errors during page load.

---

### Preflight Script Compatibility Fix (Complete)
**Issue**: `wepppy/weppcloud/static/js/preflight.js` referenced undefined `readonly` variable

**Fix**:
- Exposed `window.readonly` in `run_page_bootstrap.js.j2` template
- Added fallback check in preflight.js: `readonly = window.readonly !== undefined ? window.readonly : false;`

**Result**: Preflight checklist renders without console errors.

---

### URL Construction Fix for Climate/Team Endpoints (Complete)
**Issue**: Climate and team controllers used relative URLs like `"view/closest_stations/"` which resulted in 404 errors because they were missing the config segment in the path (going to `/weppcloud/runs/{runid}/view/...` instead of `/weppcloud/runs/{runid}/{config}/view/...`).

**Root Cause**: The `url_for_run()` utility function only added the `?pup=` parameter but didn't construct the full run-scoped path. When combined with the HTTP helper's `applySitePrefix()`, URLs were incorrectly formed.

**Fix** (utils.js):
- Updated `url_for_run()` to build the complete run-scoped path: `/runs/{runid}/{config}/{url}`
- Uses `window.runId` and `window.runConfig` (available from bootstrap template)
- Properly URL-encodes path segments
- Still adds `?pup=` parameter when needed for pup runs

**Usage** (climate.js, team.js):
- Controllers now use: `url_for_run("view/closest_stations/")`
- Which produces: `/runs/{runid}/{config}/view/closest_stations/`
- HTTP helper then prepends site prefix: `/weppcloud/runs/{runid}/{config}/view/closest_stations/`

**Result**: All run-scoped endpoints now resolve to correct paths with both runid and config segments.

---

## Outstanding Issues (runs0_pure.htm and Related Files)

### 1. Legend Visual Styling
**Location**: `wepppy/weppcloud/templates/controls/map_pure.htm` (lines ~84-87)  
**Current State**: Legends for subcatchment layers (`#sub_legend`, `#sbs_legend`) render as plain divs with minimal formatting  
**Required Fix**: Implement 2-column layout with:
- Small color swatch column (fixed width) using `.wc-baer-classify__swatch` pattern from BAER classify control
- Larger description column (flexible width)
- Example reference: `wepppy/weppcloud/templates/mods/baer/classify.htm` lines 110-114 show proper swatch sizing and structure
- CSS classes should follow existing `.wc-map-legend` conventions but add grid layout
- Each legend item should have: `<div class="wc-legend-item"><span class="wc-legend-item__swatch" style="--legend-color: rgb(...)"></span><span class="wc-legend-item__label">Description</span></div>`

**Technical Details**:
- The `#sub_legend` div (line 87) receives HTML content via `MapController` drilldown helpers
- The `#sbs_legend` div (line 86) is populated by SBS (Soil Burn Severity) layer switching logic
- Both are `aria-live="polite"` regions, so DOM updates should preserve accessibility
- Reference existing CSS: `.wc-baer-classify__swatch` uses `--wc-baer-swatch` CSS custom property for inline color assignment

**Files to Modify**:
- `wepppy/weppcloud/templates/controls/map_pure.htm` (legend container structure)
- `wepppy/weppcloud/static/css/weppcloud.css` or control-specific stylesheet (add `.wc-legend-item` grid layout)
- `wepppy/weppcloud/controllers_js/map.js` or related JS that populates legend HTML (update markup generation)

---

### 2. Report Table Visual Styling
**Location**: Various report templates included in controls  
**Current State**: Report tables lack consistent styling and proper responsive wrappers  
**Required Fix**: Standardize report table presentation using:
- Wrapper: `<div class="wc-table-wrapper">` for horizontal scroll on narrow viewports
- Table classes: `class="wc-table"` (base) with optional modifiers:
  - `wc-table--dense` for compact row spacing
  - `wc-table--compact` for narrower overall width
  - `wc-table--striped` for alternating row backgrounds
- Example reference: `wepppy/weppcloud/templates/reports/wepp/summary.htm` line 77-78 shows proper wrapper + table structure

**Affected Templates** (partial list):
- `wepppy/weppcloud/templates/controls/map/wepp_hillslope_visualizations.htm`
- `wepppy/weppcloud/templates/controls/map/rhem_hillslope_visualizations.htm`
- `wepppy/weppcloud/templates/reports/landuse.htm` (line 4 already uses `.wc-table`)
- Any report template with `<table>` elements missing wrapper divs

**Technical Details**:
- The `.wc-table-wrapper` provides `overflow-x: auto` for horizontal scroll
- Use `.wc-table-wrapper--compact` when table should remain narrow (e.g., single-metric summaries)
- All `<th>` elements should have `scope="col"` or `scope="row"` for accessibility
- Consider adding `.wc-table-actions` div above tables for export/download buttons (see `summary.htm` line 102)

**Files to Review**:
```bash
grep -r "<table" wepppy/weppcloud/templates/controls/ | grep -v "wc-table"
grep -r "<table" wepppy/weppcloud/templates/reports/ | grep -v "wc-table"
```

---

### 3. Restore Preflight TOC Indicator
**Location**: `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` TOC section (lines 56-92)  
**Current State**: TOC `<ol>` has navigation links but no preflight completion indicators  
**Required Fix**: Add `data-toc-emoji` infrastructure to TOC anchors so `preflight.js` can inject completion checkmarks

**Implementation Pattern**:
```html
<li><a href="#map" data-toc-emoji-value="✅">Map &amp; Analysis</a></li>
<li><a href="#channel-delineation" data-toc-emoji-value="✅">Channel Delineation</a></li>
```

**Technical Details**:
- `wepppy/weppcloud/static/js/preflight.js` function `setTocEmojiState(selector, isComplete)` (line 183) expects:
  - Anchor elements with `data-toc-emoji-value` attribute (stores the emoji character)
  - `data-toc-emoji` attribute gets populated when `isComplete = true`
- The preflight WebSocket handler (lines 60-71) calls `updateUI(payload.checklist)` which triggers TOC updates
- Each control section should have a TOC anchor with matching `href="#section-id"`
- Emoji values can be set inline or via `window.tocTaskEmojis` object (line 212 fallback)

**Preflight Checklist Mapping** (from `preflight.js` updateUI function):
- `#map` → always visible, no preflight dependency
- `#disturbed-sbs` → depends on `checklist.sbs_map` (line 153)
- `#channel-delineation` → depends on `checklist.channels`
- `#set-outlet` → depends on `checklist.channels`
- `#subcatchments-delineation` → depends on `checklist.channels`
- `#landuse` → depends on `checklist.landuse`
- `#climate` → depends on `checklist.landuse`
- `#soils` → depends on `checklist.soils`
- `#wepp` → depends on `checklist.wepp`

**Files to Modify**:
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` (add `data-toc-emoji-value` to anchors)
- Verify `preflight.js` selector targets match the TOC structure (currently targets `#toc a[href^="#"]`)

---

### 4. Reorder Soils Control Below Landuse
**Location**: `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`  
**Current Issue**: Soils section appears before landuse in some mod configurations  
**Required Fix**: Ensure consistent ordering in both TOC (lines 56-92) and content sections (lines 77-178)

**Standard Order** (from AGENTS.md workflow):
1. Map & Analysis
2. Soil Burn Severity (if baer/disturbed mod)
3. Channel Delineation
4. Outlet
5. Subcatchments Delineation
6. Rangeland Cover (if mod enabled)
7. **Landuse** ← must come before soils
8. Climate
9. RAP Time Series (if mod enabled)
10. **Soils** ← must come after landuse
11. Treatments (if mod enabled)
12. WEPP
13. Ash / RHEM / Omni (mod-specific)

**Current Structure** (lines 106-119):
```html
<section id="landuse" class="wc-stack">
  {% include 'controls/landuse_pure.htm' %}
</section>

<section id="climate" class="wc-stack">
  {% include 'controls/climate_pure.htm' %}
</section>

<!-- rap_ts if enabled -->

<section id="soils" class="wc-stack">
  {% include 'controls/soil_pure.htm' %}
</section>
```
This is correct, but verify TOC `<li>` order matches (lines 75-83).

**Verification**:
```bash
# Check TOC order
grep -A 1 'href="#landuse"' wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm
grep -A 1 'href="#soils"' wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm

# Check section order
grep 'id="landuse"\|id="soils"' wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm
```

---

### 5. Enable Map Layer Radios Based on Preflight State
**Location**: `wepppy/weppcloud/templates/controls/map_pure.htm` (lines 14-44)  
**Current State**: Three subcatchment color map radios are initially `disabled: True`:
- `sub_cmap_radio_slp_asp` (Slope/Aspect)
- `sub_cmap_radio_dom_lc` (Dominant Landcover)
- `sub_cmap_radio_dom_soil` (Dominant Soil)

**Status**: ✅ **FIXED 2025-10-27**

**Bug Discovered**: The `updateLayerAvailability()` function was implemented but the preflight event listener was registered outside the instance at module load time (when `instance` was null). The event listener never fired because the controller instance didn't exist yet.

**Fix Applied**:
1. Moved preflight event listener from module scope into `bootstrap()` method
2. Added `preflightListenerAttached` flag to `bootstrapState` to prevent duplicate listeners
3. Event listener now correctly calls `sub.updateLayerAvailability()` when preflight updates

**Fixed Code** (`subcatchment_delineation.js` lines 1560-1572):
```javascript
// Update layer availability based on preflight state
if (typeof sub.updateLayerAvailability === "function") {
    sub.updateLayerAvailability();
}

// Set up preflight listener (only once)
if (!bootstrapState.preflightListenerAttached && typeof document !== "undefined") {
    document.addEventListener("preflight:update", function() {
        if (typeof sub.updateLayerAvailability === "function") {
            sub.updateLayerAvailability();
        }
    });
    bootstrapState.preflightListenerAttached = true;
}
```

**Implementation Details**:
1. Subscribe to preflight WebSocket updates in `subcatchment_delineation.js`
2. Check `window.lastPreflightChecklist` (populated by `preflight.js` line 66-67)
3. Enable radios when conditions met:
   - **Slope/Aspect**: Enable after `checklist.channels === true` (channel delineation complete)
   - **Dominant Landcover**: Enable after `checklist.landuse === true` (landuse acquisition complete)
   - **Dominant Soil**: Enable after `checklist.soils === true` (soil building complete)

**Reference Code** (from `subcatchment_delineation.js` line 978-980):
```javascript
case "slp_asp":
    disableRadio("sub_cmap_radio_slp_asp", false);  // false = enable
    break;
```
This pattern exists but isn't wired to preflight state.

**Preflight Checklist Structure** (from `preflight.js` updateUI):
```javascript
{
  channels: boolean,          // Channel delineation complete
  landuse: boolean,           // Landuse built
  soils: boolean,             // Soils built
  wepp: boolean,              // WEPP run complete
  watershed: boolean,         // Watershed abstraction complete
  sbs_map: boolean,           // SBS classification complete (baer/disturbed only)
  climate: boolean,           // Climate data acquired
  // ... other flags
}
```

**Files to Modify**:
1. `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`:
   - Add `updateLayerAvailability()` function that reads `window.lastPreflightChecklist`
   - Call from controller initialization and whenever preflight updates broadcast
   - Use existing `disableRadio(id, shouldDisable)` helper (line 979)

2. `wepppy/weppcloud/static/js/preflight.js`:
   - Consider emitting custom event when checklist updates: `document.dispatchEvent(new CustomEvent('preflight:update', { detail: checklist }))`
   - Controllers can then listen: `document.addEventListener('preflight:update', handler)`

**Implementation Sketch**:
```javascript
// In subcatchment_delineation.js
function updateLayerAvailability() {
    var checklist = window.lastPreflightChecklist;
    if (!checklist) return;
    
    // Enable Slope/Aspect after channel delineation
    if (checklist.channels) {
        disableRadio("sub_cmap_radio_slp_asp", false);
    }
    
    // Enable Dominant Landcover after landuse acquisition
    if (checklist.landuse) {
        disableRadio("sub_cmap_radio_dom_lc", false);
    }
    
    // Enable Dominant Soil after soil building
    if (checklist.soils) {
        disableRadio("sub_cmap_radio_dom_soil", false);
    }
}

// Call on init and preflight updates
document.addEventListener('preflight:update', updateLayerAvailability);
updateLayerAvailability(); // Initial check
```

---

### 6. Revise Help Icon Fields to Use Inline Component Macro
**Location**: Multiple control templates  
**Current Pattern** (example from `channel_delineation_pure.htm` lines 56-68):
```html
<div class="wc-field">
  <label class="wc-field__label" for="input_mcl">
    Minimum channel length (m)
    <a data-toggle="tooltip" data-placement="top" title="Recommended to use default value.">
      <img src="{{ url_for('static', filename='images/61692-200-24.png') }}" alt="Help">
    </a>
  </label>
  <input id="input_mcl" name="mcl" class="wc-field__control disable-readonly" type="text" value="...">
</div>
```

**Problem**:
- Inline help icons inside `<label>` violate accessibility best practices (nested interactive elements)
- Tooltip plugin dependency (`data-toggle="tooltip"`) couples markup to Bootstrap/jQuery
- No consistent visual styling or keyboard interaction pattern
- `alt="Help"` on decorative icon image is redundant when title already provides context

**Required Fix**: Refactor to use Pure macro `help` parameter

**Proposed Macro Enhancement** (for `_pure_macros.html`):
```jinja
{% macro text_field(field_id, label, value='', help=None, inline_help=None, type='text', placeholder=None, attrs=None, error=None, extra_control_class=None) -%}
{# ... existing code ... #}
<div class="{{ ' '.join(field_classes) }}" style="max-width: 650px;">
  <label class="wc-field__label" for="{{ field_id }}">
    {{ label }}
    {% if inline_help %}
    <button type="button"
            class="wc-field__help-trigger"
            aria-label="Help: {{ inline_help }}"
            data-help-tooltip="{{ inline_help }}"
            tabindex="0">
      <svg class="wc-icon wc-icon--help" aria-hidden="true" width="16" height="16">
        <use href="#icon-help-circle"></use>
      </svg>
    </button>
    {% endif %}
  </label>
  <input class="{{ ' '.join(control_classes) }}"
         id="{{ field_id }}"
         name="{{ field_id }}"
         type="{{ type }}"
         value="{{ value }}"
         {% if placeholder %}placeholder="{{ placeholder }}"{% endif %}
         {% if error %}aria-invalid="true"{% endif %}
         {% if describedby %}aria-describedby="{{ ' '.join(describedby) }}"{% endif %}
         {% for attr_key, attr_val in attrs.items() %}
           {{ attr_key }}="{{ attr_val }}"
         {% endfor %}>
  {% if help %}
  <p id="{{ help_id }}" class="wc-field__help">{{ help }}</p>
  {% endif %}
  {% if error %}
  <p id="{{ error_id }}" class="wc-field__message wc-field__message--error" role="alert">{{ error }}</p>
  {% endif %}
</div>
{%- endmacro %}
```

**Migration Example**:
```jinja
{# BEFORE #}
<div class="wc-field">
  <label class="wc-field__label" for="input_mcl">
    Minimum channel length (m)
    <a data-toggle="tooltip" data-placement="top" title="Recommended to use default value.">
      <img src="{{ url_for('static', filename='images/61692-200-24.png') }}" alt="Help">
    </a>
  </label>
  <input id="input_mcl" name="mcl" class="wc-field__control disable-readonly" type="text" value="100">
</div>

{# AFTER #}
{{ ui.text_field(
     "input_mcl",
     "Minimum channel length (m)",
     value="100",
     inline_help="Recommended to use default value.",
     extra_control_class="disable-readonly"
   ) }}
```

**Affected Templates** (from grep results):
- `wepppy/weppcloud/templates/controls/climate.htm` (12 instances, lines 36, 39, 140, 144, 148, 151, 154, 157, 169, 172, 176, 179)
- `wepppy/weppcloud/templates/controls/channel_delineation_pure.htm` (4 instances)
- Any other control using `data-toggle="tooltip"` with help icons

**Implementation Steps**:
1. **Add `inline_help` parameter to macros** in `_pure_macros.html`:
   - `text_field`
   - `select_field`
   - `checkbox_field`
   - `radio_group` (apply to individual option labels)

2. **Create CSS for `.wc-field__help-trigger`**:
   ```css
   .wc-field__help-trigger {
     display: inline-flex;
     align-items: center;
     justify-content: center;
     width: 1.25rem;
     height: 1.25rem;
     padding: 0;
     margin-left: 0.25rem;
     border: none;
     background: transparent;
     color: var(--color-text-muted);
     cursor: help;
     vertical-align: middle;
   }
   
   .wc-field__help-trigger:hover,
   .wc-field__help-trigger:focus {
     color: var(--color-primary);
     outline: 2px solid var(--color-focus);
     outline-offset: 2px;
   }
   ```

3. **Add JavaScript tooltip handler** (lightweight, no Bootstrap dependency):
   ```javascript
   // In wepppy/weppcloud/static/js/field-help-tooltips.js
   (function initFieldHelpTooltips() {
     document.addEventListener('click', function(event) {
       var trigger = event.target.closest('[data-help-tooltip]');
       if (!trigger) return;
       
       var helpText = trigger.getAttribute('data-help-tooltip');
       if (!helpText) return;
       
       event.preventDefault();
       // Show tooltip using existing modal/popover system or create minimal implementation
       alert(helpText); // Placeholder - replace with proper tooltip UI
     });
   })();
   ```

4. **Migrate control templates**:
   - Start with `channel_delineation_pure.htm` (already Pure-based)
   - Then tackle `climate_pure.htm` when it exists
   - Update legacy controls during next Pure migration wave

**Accessibility Benefits**:
- Help trigger is a proper `<button>` with `aria-label`
- Keyboard accessible via `Tab` and `Enter`/`Space`
- Screen readers announce help text via `aria-label`
- No nested interactive elements (label wraps text only, button is sibling)

**Files to Create/Modify**:
- `wepppy/weppcloud/templates/controls/_pure_macros.html` (add `inline_help` parameter to field macros)
- `wepppy/weppcloud/static/css/weppcloud.css` (add `.wc-field__help-trigger` styles)
- `wepppy/weppcloud/static/js/field-help-tooltips.js` (new lightweight tooltip handler)
- `wepppy/weppcloud/templates/base_pure.htm` (include new JS file in head_extras)
- `wepppy/weppcloud/templates/controls/channel_delineation_pure.htm` (migrate 4 help icon instances)

---

### 7. Controller Hint Elements - Deduplicate Status Messages and Show Job Dashboard Link
**Location**: `wepppy/weppcloud/controllers_js/control_base.js` lines 690-710  
**Current State**: Controller hint elements (e.g., `#hint_build_soil`) duplicate status log messages and show raw RQ job IDs with trigger events  
**Current Behavior Example**:
```html
<!-- Status panel shows: -->
<div data-status-log>
  <div>Building soils database...</div>
  <div>rq:f19c2fde-711a-4d38-8e82-a3e947af0916 TRIGGER soils SOILS_BUILD_TASK_COMPLETED</div>
</div>

<!-- Hint element duplicates same content: -->
<p id="hint_build_soil" class="wc-text-muted" aria-live="polite">
  rq:f19c2fde-711a-4d38-8e82-a3e947af0916 TRIGGER soils SOILS_BUILD_TASK_COMPLETED
</p>
```

**Problem**:
1. **Duplication**: Hint elements show the same message as the status log, creating redundant information
2. **Poor UX**: Raw RQ job ID strings like `rq:f19c2fde-711a-4d38-8e82-a3e947af0916` are not user-friendly
3. **Missing Link**: Users cannot easily navigate to job dashboard for details
4. **Status card clutter**: Job dashboard link appears in status card `render_job_status()` output, not needed if hint has it

**Required Fix**: Update hint to show **job dashboard link only**, remove job link from status card

**Desired Behavior**:
```html
<!-- Status panel shows task messages only (no job link): -->
<div data-status-log>
  <div>Building soils database...</div>
  <div>TRIGGER soils SOILS_BUILD_TASK_COMPLETED</div>
</div>

<!-- Status card shows status without link: -->
<div id="rq_job">
  <div>job_id: f19c2fde-711a-4d38-8e82-a3e947af0916</div>
  <div class="small text-muted">Status: Finished</div>
</div>

<!-- Hint element shows job dashboard link: -->
<p id="hint_build_soil" class="wc-text-muted" aria-live="polite">
  job_id: <a href="https://wc.bearhive.duckdns.org/weppcloud/rq/job-dashboard/f19c2fde-711a-4d38-8e82-a3e947af0916" target="_blank">f19c2fde-711a-4d38-8e82-a3e947af0916</a>
</p>
```

**Technical Implementation**:

**1. Modify `control_base.js` `attach_status_stream` onAppend callback** (lines 693-710):

Current code:
```javascript
onAppend: function (detail) {
    advanceSpinner();

    const rawMessage = detail && detail.raw !== undefined ? detail.raw : detail ? detail.message : "";
    const summary = extractSummaryText(rawMessage, summaryMaxLength);

    if (summarySetter) {
        summarySetter(summary);
    }
    if (hintSetter) {
        hintSetter(summary);  // ← Currently duplicates summary
    }
    // ... rest of callback
}
```

Proposed change:
```javascript
onAppend: function (detail) {
    advanceSpinner();

    const rawMessage = detail && detail.raw !== undefined ? detail.raw : detail ? detail.message : "";
    const summary = extractSummaryText(rawMessage, summaryMaxLength);

    if (summarySetter) {
        summarySetter(summary);
    }
    
    // Update hint with job dashboard link instead of summary
    if (hintSetter && self.rq_job_id) {
        const jobLink = `job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a>`;
        hintSetter(jobLink);
    }
    
    // ... rest of callback
}
```

**2. Modify `control_base.js` `render_job_status` function** (lines 483-525):

Current code (lines 497-499):
```javascript
parts.push(
    `<div>job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a></div>`
);
```

Proposed change:
```javascript
// Remove link, show plain job_id (link will be in hint element)
parts.push(
    `<div>job_id: ${escapeHtml(self.rq_job_id)}</div>`
);
```

**3. Update `makeTextSetter` to handle HTML content for hints**:

The `hintSetter` is created via `makeTextSetter` which might need to support HTML content. Check implementation around lines 170-200 and ensure it uses `.html()` or `.innerHTML` when setting content with HTML tags.

Current `makeTextSetter` logic (approximate location line 170-180):
```javascript
function makeTextSetter(target) {
    // ...
    return function (value) {
        if (callAdapter(target, "text", [value])) {
            return;
        }
        const element = unwrapElement(target);
        if (element) {
            element.textContent = value;  // ← Uses textContent (escapes HTML)
        }
    };
}
```

Needs enhancement to support HTML for hints:
```javascript
function makeTextSetter(target, allowHtml) {
    // ...
    return function (value) {
        const adapterMethod = allowHtml ? "html" : "text";
        if (callAdapter(target, adapterMethod, [value])) {
            return;
        }
        const element = unwrapElement(target);
        if (element) {
            if (allowHtml) {
                element.innerHTML = value;
            } else {
                element.textContent = value;
            }
        }
    };
}
```

Then update hint setter creation (line ~634):
```javascript
const hintSetter = makeTextSetter(
    config.hint || config.hintTarget || self.hint || null,
    true  // Allow HTML for job dashboard links
);
```

**Alternative Approach** (simpler, no HTML injection risk):

Instead of injecting HTML into hints, populate hint elements only when job completes and use direct DOM manipulation:

```javascript
onAppend: function (detail) {
    advanceSpinner();
    const rawMessage = detail && detail.raw !== undefined ? detail.raw : detail ? detail.message : "";
    const summary = extractSummaryText(rawMessage, summaryMaxLength);

    if (summarySetter) {
        summarySetter(summary);
    }
    
    // Don't duplicate summary in hint - hints will be updated by onTrigger
    
    // ... rest of callback
},
onTrigger: function (detail) {
    if (detail && detail.event) {
        // ... existing trigger logic ...
        
        // Update hint with job link when task completes
        const normalized = String(detail.event).toUpperCase();
        if (
            normalized.includes("COMPLETE") ||
            normalized.includes("FINISH") ||
            normalized.includes("SUCCESS")
        ) {
            if (hintSetter && self.rq_job_id) {
                const hintElement = unwrapElement(config.hint || config.hintTarget || self.hint);
                if (hintElement) {
                    hintElement.innerHTML = `job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a>`;
                }
            }
            resetSpinner();
        }
    }
    // ... rest of trigger callback ...
}
```

**Affected Controllers** (all use hint elements):
- `soil.js` (line 113) - `#hint_build_soil`
- `channel_delineation.js` (line 246) - hint element
- `treatments.js` (lines 243, 284) - hint element
- `ash.js` (lines 477, 483) - hint element
- `observed.js` (line 293) - hint element
- `debris_flow.js` (line 153) - hint element
- `rhem.js` (line 189) - hint element
- `dss_export.js` (line 435) - hint element
- `rap_ts.js` (line 330) - hint element
- `path_ce.js` (line 227) - hint element
- `omni.js` (lines 681, 706, 731) - hint element

**Template Pattern** (all Pure control templates):
```html
<p id="hint_build_[controller]" class="wc-text-muted" aria-live="polite"></p>
```

**Benefits**:
1. **Reduced duplication**: Hints no longer echo status log content
2. **Better UX**: Clear, clickable link to job dashboard for debugging
3. **Cleaner status cards**: Job dashboard link removed from `#rq_job` element (which may not even be visible in Pure templates)
4. **Consistent pattern**: All controllers get job link in hint after task completion

**Accessibility Considerations**:
- Hint elements already have `aria-live="polite"` so screen readers will announce link when it appears
- Link should have `target="_blank"` for job dashboard (opens in new tab)
- Job ID should remain visible text content for screen readers

**Testing Checklist**:
- [ ] Verify hint shows job link after task completion
- [ ] Verify status log doesn't duplicate job ID in hint
- [ ] Verify `#rq_job` status card shows plain job_id (no link)
- [ ] Test with multiple controllers (soil, climate, wepp, etc.)
- [ ] Verify `aria-live` announces link to screen readers
- [ ] Test link opens job dashboard in new tab

**Files to Modify**:
- `wepppy/weppcloud/controllers_js/control_base.js` (onAppend callback, onTrigger callback, render_job_status function)
- Optional: Update hint element styles if link needs visual distinction

---

## Follow-up
- Smoke automation (profiles, CLI, extended Playwright flows) continues under [20251023_smoke_tests](../20251023_smoke_tests/package.md).
