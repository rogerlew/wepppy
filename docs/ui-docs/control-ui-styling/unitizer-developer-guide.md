# Unitizer System Developer Guide

**Last updated: 2025-10-20**

## Overview

The Unitizer system provides dynamic unit conversion and preference management across WEPPcloud. Users can choose between SI and English unit systems globally, with per-category overrides (e.g., "SI everywhere except use acres for area"). The system handles real-time conversion of display values, form inputs, and report data.

**Complexity rating: 6.5/10** - Moderately complex but justified by scientific requirements.

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│ User Interface                                          │
│ ├─ unitizer_modal.htm (Pure CSS modal)                  │
│ │  ├─ Global SI/English radio buttons                   │
│ │  └─ Per-category unit preference radios               │
│ └─ Embedded in reports/forms via Jinja helpers          │
└─────────────────────────────────────────────────────────┘
                         ↓ ↑
┌─────────────────────────────────────────────────────────┐
│ JavaScript Client Layer                                  │
│ ├─ unitizer_client.js (conversion engine)               │
│ │  ├─ Module loading (unitizer_map.js)                  │
│ │  ├─ Preference state (Map<category, unit>)            │
│ │  ├─ Conversion functions                              │
│ │  └─ DOM synchronization                               │
│ ├─ project.js (event orchestration)                     │
│ │  ├─ handleGlobalUnitPreference()                      │
│ │  ├─ handleUnitPreferenceChange()                      │
│ │  └─ unitChangeEvent()                                 │
│ └─ modal.js (modal management)                          │
│    └─ Focus trapping & event handling                   │
└─────────────────────────────────────────────────────────┘
                         ↓ ↑
┌─────────────────────────────────────────────────────────┐
│ Backend (Python)                                         │
│ ├─ Unitizer (NoDb) - state persistence                  │
│ │  ├─ preferences dict (category → unit key)            │
│ │  ├─ is_english property                               │
│ │  └─ Jinja template helpers                            │
│ ├─ unitizer_map.js generation                           │
│ │  └─ Build-time export of conversion tables            │
│ └─ API endpoints                                         │
│    └─ /tasks/set_unit_preferences/ (POST)               │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Page load**: Jinja renders radios with server-side preferences
2. **User interaction**: Radio change → template handler → project.js
3. **State update**: JavaScript updates preference Map, applies to DOM
4. **Persistence**: POST to backend, updates NoDb instance
5. **DOM sync**: All `.unitizer-wrapper` elements re-render with new units

## Key Files

| Path | Purpose |
|------|---------|
| `wepppy/nodb/unitizer.py` | Backend state, conversion definitions, Jinja helpers |
| `wepppy/weppcloud/static/js/unitizer_map.js` | Generated conversion tables (build artifact) |
| `wepppy/weppcloud/controllers_js/unitizer_client.js` | JavaScript conversion engine & DOM sync |
| `wepppy/weppcloud/controllers_js/project.js` | Event handlers & backend communication |
| `wepppy/weppcloud/controllers_js/modal.js` | Modal system (focus trap, dismiss handlers) |
| `wepppy/weppcloud/templates/controls/unitizer.htm` | Main preference UI |
| `wepppy/weppcloud/templates/controls/unitizer_modal.htm` | Modal wrapper |
| `wepppy/weppcloud/routes/nodb_api/unitizer_bp.py` | Preference persistence endpoint |

## Common Patterns

### 1. Rendering Values with Unit Conversion

**Template (Jinja)**:
```jinja
{{ unitizer(value, 'mm', parentheses=True) }}
{# Renders multiple unit divs, shows/hides based on preference #}
```

**JavaScript**:
```javascript
UnitizerClient.ready().then(function(client) {
  var html = client.renderValue(123.45, 'mm', {
    includeUnits: true,
    parentheses: false
  });
  element.innerHTML = html;
});
```

### 2. Handling Numeric Inputs

Inputs with `data-unitizer-canonical-unit` automatically convert on preference change:

```html
<input type="number" 
       value="100"
       data-unitizer-canonical-unit="mm"
       data-unitizer-canonical-value="100">
```

When user changes from SI to English:
- Canonical value (100 mm) stays constant
- Display value converts to inches
- Form submission includes current unit

### 3. Listening to Preference Changes

```javascript
document.addEventListener('unitizer:preferences-changed', function(event) {
  var prefs = event.detail.preferences;    // {area: 'ha', distance: 'km', ...}
  var tokens = event.detail.tokens;        // {area: 'ha', distance: 'km', ...}
  // Re-render custom UI
});
```

### 4. Currency per Area Inputs

Mulch, seeding, and other treatment costs now use the `currency-area` category to
toggle between `$/ha` and `$/acre` automatically. When building inputs:

```html
<input type="number"
       name="mulch_costs[mulch_30_sbs_map]"
       data-unitizer-category="currency-area"
       data-unitizer-unit="$/ha"
       data-pathce-cost="mulch_30_sbs_map">
<span data-unitizer-label
      data-unitizer-category="currency-area"
      data-unitizer-unit="$/ha">$/ha</span>
```

Always record canonical values (in `$/ha`) via `data-unitizer-canonical-value`
or by dispatching an `input` event after setting the field programmatically so
the Unitizer client can keep the stored value in sync with the user-facing unit.

## Modal System Integration

### How the Modal Works

The modal uses attribute-based triggers:

```html
<!-- Trigger button -->
<button data-modal-open="unitizerModal">Open Unitizer</button>

<!-- Modal container -->
<div class="wc-modal" id="unitizerModal" data-modal hidden>
  <!-- When opened, modal.js adds data-modal-open="true" -->
  <div class="wc-modal__overlay" data-modal-dismiss></div>
  <div class="wc-modal__dialog">
    <!-- Content here -->
  </div>
</div>
```

### Critical Bug & Fix (Oct 2025)

**Problem**: Radio buttons inside the modal weren't responding to clicks.

**Root cause**: `modal.js` uses `data-modal-open` for two purposes:
1. **Trigger attribute**: `<button data-modal-open="modalId">` 
2. **State marker**: Modal gets `data-modal-open="true"` when open

The `handleOpenClick` function used `closest('[data-modal-open]')` which matched the modal itself (with value "true"), causing `preventDefault()` to fire on all clicks inside the modal, blocking radio button default behavior.

**Fix**: Check if the attribute value is "true" (state) vs a modal ID (trigger):

```javascript
function handleOpenClick(event) {
    var trigger = event.target.closest("[data-modal-open]");
    if (!trigger) {
        return;
    }
    var targetId = trigger.getAttribute("data-modal-open");
    // Only handle if the value is a modal ID (string), not "true" (open state marker)
    if (!targetId || targetId === "true") {
        return;
    }
    event.preventDefault();
    openModal(targetId);
}
```

**Lesson**: Attribute-based selectors can match unintended ancestors. Always validate attribute values when using `closest()`.

## Debugging Guide

### Diagnostic Approach (Human vs AI)

When debugging the unitizer modal radio bug, **Codex spent 2+ hours making guesses** (trying event handlers, propagation, inline handlers) while **the human developer used systematic diagnostics** that identified the issue in minutes.

#### ❌ Guessing approach (Codex GPT 5):
- Remove inline handlers → still broken
- Remove stopPropagation → still broken
- Add different event phases → still broken
- Rename radio buttons → still broken
- Add undefined guards → still broken
- Never arrived at solution

#### ✅ Diagnostic approach (Claude Sonnet 4.5):
1. **Check if events fire**: Console log showed click events registered
2. **Check defaultPrevented**: Console showed `defaultPrevented: true`
3. **Identify the blocker**: Something calling preventDefault between capture and bubble
4. **Find the culprit**: Searched for modal event handlers
5. **Verify the theory**: Added `hasModalOpen: target.closest('[data-modal-open]')` diagnostic
6. **Fix precisely**: Modified only the offending logic

### Debugging Checklist

When unitizer controls don't work:

#### 1. **Is the JavaScript loaded?**
```javascript
// Console
typeof UnitizerClient  // Should be 'object'
UnitizerClient.getClientSync()  // Should return client instance or null
```

#### 2. **Are preferences being set?**
```javascript
UnitizerClient.ready().then(function(client) {
  console.log(client.getPreferencePayload());
  // Should show: {area: 'ha', distance: 'km', ...}
});
```

#### 3. **Are radio buttons bound?**
```javascript
// Check if change handlers are registered
document.querySelectorAll('input[name="unit_main_selector"]').forEach(radio => {
  console.log('Radio:', radio.value, 'checked:', radio.checked);
});
```

#### 4. **Are events firing?**
Add temporary diagnostics to `unitizer.htm`:
```javascript
document.addEventListener('change', function(event) {
  if (event.target.name === 'unit_main_selector') {
    console.log('[DEBUG] Change event:', {
      value: event.target.value,
      checked: event.target.checked,
      defaultPrevented: event.defaultPrevented,
      phase: event.eventPhase  // 1=CAPTURE, 2=TARGET, 3=BUBBLE
    });
  }
}, true);  // Use capture phase to see events before bubble handlers
```

#### 5. **Is preventDefault being called?**
```javascript
document.addEventListener('click', function(event) {
  var target = event.target;
  if (target && target.type === 'radio') {
    console.log('[DEBUG] Click:', {
      name: target.name,
      value: target.value,
      defaultPrevented: event.defaultPrevented
    });
  }
}, true);  // Capture phase
```

If `defaultPrevented: true`, something is blocking the default action.

#### 6. **Are there attribute conflicts?**
```javascript
// Check for unintended attribute matches
var target = document.querySelector('input[name="unit_main_selector"]');
console.log('Closest modal-open:', target.closest('[data-modal-open]'));
// Should be null for radios outside modals
```

#### 7. **Is the backend syncing?**
```javascript
// Network tab → Filter by "set_unit_preferences"
// Should see POST requests after radio changes
// Check response: {Success: true, ...}
```

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Radios don't check | Controller not initialised | Ensure `Project.getInstance()` loads (check console) and that markup includes `data-project-unitizer` attributes |
| Values don't convert | unitizer_map.js not loaded | Check network tab, ensure build ran |
| Wrong units displayed | Preference state out of sync | Call `client.syncPreferencesFromDom()` |
| POST fails | Backend error or lock | Check server logs, clear NoDb locks |
| Modal won't open | Modal.js not loaded | Check controllers-gl.js bundle includes modal.js |
| Clicks do nothing | preventDefault interference | Check `defaultPrevented` in event logs |

### Testing Interactive Forms in Modals

The modal system is relatively new (2025). When adding complex forms:

1. **Start simple**: Test with static text and buttons first
2. **Add controls incrementally**: Links → Buttons → Checkboxes → Radios → Selects
3. **Test keyboard navigation**: Tab, Shift+Tab, Escape all working?
4. **Check preventDefault**: Any events being blocked?
5. **Verify focus trap**: Does Tab stay inside the modal?
6. **Test form submission**: Do change/submit events fire?

**Red flags**:
- `defaultPrevented: true` when clicking form controls
- `closest()` matches returning unexpected ancestors
- Event handlers attached to `document` with broad selectors

## Performance Considerations

### Module Loading Strategy

`unitizer_client.js` uses a fallback chain:
1. Try to import `unitizer_map.js` as ES module
2. Fall back to inline `window.__unitizerMap`
3. Gracefully degrade with error messages

This ensures robustness but adds branching complexity.

### DOM Update Efficiency

When preferences change, the system:
1. Updates internal Map (O(1) per category)
2. Queries all `.unitizer-wrapper` elements (O(n))
3. Shows/hides child divs based on preference (O(n × units per category))

For large reports (1000+ values), this can cause layout thrashing. Consider:
- Batching updates with `requestAnimationFrame`
- Using CSS classes instead of inline style toggles
- Virtualizing long lists

## Future Improvements

### Complexity Reduction Opportunities

1. **Template logic now centralized**: Global preference wiring lives in the Project controller; future tweaks should extend `Project.handleGlobalUnitPreference` instead of reintroducing inline scripts.
2. **Simplify radio state management**: The triple-pass (uncheck → check → verify) is defensive but verbose
3. **Consolidate sync functions**: `syncPreferencesFromDom`, `applyPreferenceRadios`, `applyGlobalRadio` overlap
4. **Consider reactive framework**: If refactoring, React/Vue would handle state → DOM updates more elegantly

### Modal System Maturity

Current state: Works but needs validation with simpler use cases before broader adoption.

Recommendations:
- Use for confirmation dialogs (low risk)
- Avoid for complex multi-step forms (high risk)
- Document all attribute-based interactions
- Add integration tests for interactive form elements

## Contributing

### Making Changes

1. **Backend (Python)**: Update `wepppy/nodb/unitizer.py`
   - Add new unit categories to `converters` and `precisions` dicts
   - Rebuild `unitizer_map.js`: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`

2. **Frontend (JavaScript)**: Update `unitizer_client.js`
   - Test with `UnitizerClient.ready().then(...)` in console
   - Rebuild controllers bundle: restart weppcloud (auto-rebuilds on start)

3. **UI (Templates)**: Update `unitizer.htm` or `unitizer_modal.htm`
   - Maintain Pure CSS patterns (no Bootstrap)
   - Keep accessibility (ARIA labels, keyboard nav)

### Testing Changes

```bash
# Restart to rebuild controllers-gl.js
wctl restart weppcloud

# Test in browser
1. Open modal
2. Toggle radios
3. Check console for errors
4. Verify POST to /tasks/set_unit_preferences/
5. Refresh page, verify persistence
```

### Code Review Checklist

- [ ] No inline styles in templates
- [ ] All form controls have labels
- [ ] Change events fire correctly
- [ ] Keyboard navigation works (Tab, Escape)
- [ ] No console errors
- [ ] Backend preferences persist
- [ ] Works on mobile/narrow viewports
- [ ] No modal event handler conflicts

## References

- [Control Components Spec](./control-components.md)
- [UI Style Guide](../ui-style-guide.md) - Modal patterns
- [AGENTS.md](./AGENTS.md) - Original task brief
- Backend NoDb pattern: `wepppy/nodb/base.py`

## Changelog

- **2025-10-20**: Initial guide created after radio button preventDefault bug resolution
- **2025-10-19**: Modal system implemented, unitizer migrated to Pure CSS

---

**Pro tip**: When debugging interactive controls in modals, always check `event.defaultPrevented` early in the diagnostic process. It's a reliable signal that something upstream is blocking the browser's default behavior.
