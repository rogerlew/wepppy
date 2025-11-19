# Controller Contract

> **See also:** [`controllers_js/README.md`](../../wepppy/weppcloud/controllers_js/README.md) for bundling and architecture details.

## Overview

WEPPcloud controllers are singleton JavaScript modules that manage run workflow UI (Climate, Landuse, Soils, WEPP, etc.). This document defines the explicit contract every controller must follow to ensure consistent behavior, especially during dynamic loading scenarios.

## Core Contract

### Singleton Pattern

**Every controller MUST:**
- Export a single global instance via `getInstance()`
- Never allow direct construction via `new`
- Return the same instance across multiple calls

**Why:** Prevents duplicate DOM wiring, WebSocket connections, and event handlers.

### Bootstrap Method

**Every controller MUST implement:**
```javascript
controller.bootstrap = function(context) {
    // Re-query DOM elements if needed
    // Wire event handlers
    // Initialize state from context
};
```

**Context object contains:**
- `run`, `user`, `mods`, `flags` - Run metadata
- `jobIds` - RQ job name → ID mapping
- `data` - Domain flags (hasChannels, hasRun, etc.)
- `controllers[name]` - Controller-specific overrides

**Bootstrap is called:**
- On initial page load
- After dynamic mod enablement via Mods dialog
- May be called multiple times (must be idempotent)

### Dynamic Loading Contract

**The Problem:** When mods are dynamically enabled, the controller singleton may be created **before** DOM elements exist, resulting in null references that persist even after HTML insertion.

**Required Patterns:**

1. **Re-query elements in bootstrap():**
```javascript
controller.bootstrap = function(context) {
    if (!controller.form) {
        controller.form = dom.qs("#my-form");
    }
    // Now safe to use controller.form
};
```

2. **Defensive element access:**
```javascript
controller.doSomething = function() {
    if (!controller.form) {
        console.warn("Form not available");
        return;
    }
    // Safe to proceed
};
```

3. **Re-attach event delegates in bootstrap():**
```javascript
controller.bootstrap = function(context) {
    var needsDelegates = false;
    
    if (!controller.form) {
        controller.form = dom.qs("#my-form");
        needsDelegates = true;
    }
    
    if (needsDelegates) {
        controller._delegates.push(
            dom.delegate(controller.form, "click", "[data-action='submit']", handleSubmit)
        );
    }
};
```

**Why this matters:** Without re-query + delegate setup, dynamically loaded mods show UI but buttons don't respond to clicks.

**Full guidance:** See [`dynamic-mod-loading-patterns.md`](../dev-notes/dynamic-mod-loading-patterns.md) for comprehensive patterns, alternatives, and testing strategies.

## DOM Contract

### Required Elements

Controllers expect standardized DOM structure from Pure templates:

```html
<form id="controller-form" data-controller-form>
  <fieldset>
    <!-- Form controls -->
  </fieldset>
  
  <!-- Status panel for WebSocket logs -->
  <div id="controller-status" data-status-panel>
    <div data-status-log></div>
  </div>
  
  <!-- Stacktrace panel (optional) -->
  <div id="controller-stacktrace" data-stacktrace-panel hidden>
    <div data-stacktrace-body></div>
  </div>
</form>
```

### Data Attributes

**Action hooks:**
```html
<button data-action="submit">Build</button>
<input data-field="mode" name="mode">
<select data-role="dataset-picker"></select>
```

**Use delegated event listeners on data attributes, not inline handlers.**

### Status Streaming

**Required for long-running tasks:**
```javascript
controlBase.attach_status_stream('controller-status', {
    channel: 'controller-channel',
    runId: window.runId
});
```

**Status panel must have unique ID for WebSocket attachment.**

## Transport Contract

### HTTP Helpers

**All controller network requests MUST use `WCHttp`:**
```javascript
const { postJson, getJson, postForm } = WCHttp;

// JSON payload
postJson(url_for_run("rq/api/build_climate"), payload);

// Form data
postForm(url_for_run("tasks/set_mode"), formElement);
```

**Why:** Enables global interceptors, audit logging, recorder tooling, and consistent error handling.

### URL Construction

**Run-scoped endpoints MUST use `url_for_run()`:**
```javascript
// ✅ Correct
http.postJson(url_for_run("rq/api/build_climate"), payload);
http.get(url_for_run("resources/subcatchments.json"));

// ❌ Wrong - missing run context
http.postJson("rq/api/build_climate", payload);
```

**Applies to:** `rq/api/*`, `tasks/*`, `query/*`, `resources/*`

**See:** [`controllers_js/README.md`](../../wepppy/weppcloud/controllers_js/README.md) for full URL construction guidance.

## Event Contract

### Scoped Events

**Controllers SHOULD emit domain events:**
```javascript
controller.events = WCEvents.useEventMap([
    'climate:build:started',
    'climate:build:completed',
    'climate:build:error'
]);

// Emit
controller.events.emit('climate:build:started', { jobId });

// Subscribe
controller.events.on('climate:build:completed', handleCompletion);
```

**Benefits:** Decouples controllers, enables telemetry, supports testing.

### Legacy DOM Events

**May still dispatch CustomEvents for backward compatibility:**
```javascript
controlBase.triggerEvent('CLIMATE_BUILD_COMPLETED', { status: 'success' });
```

**New code should prefer scoped event emitters.**

## Testing Contract

### Dynamic Loading Tests

**Every controller MUST test:**

1. Initial page load (mod in template)
2. Dynamic enable via Mods checkbox
3. Dynamic disable → re-enable
4. Event handlers work after dynamic load
5. UI interactions identical in both scenarios

### Test Suite Locations

- **Jest:** `controllers_js/__tests__/<controller>.test.js`
- **Playwright:** `static-src/tests/smoke/controller-regression.spec.js`
- **Backend:** `tests/weppcloud/routes/test_<domain>_bp.py`

### Running Tests

**JavaScript unit tests:**
```bash
wctl run-npm test                    # Full suite
wctl run-npm test -- <controller>    # Single controller
```

**Playwright controller regression:**
```bash
wctl run-playwright --suite controllers --workers 1
```

**Backend integration:**
```bash
wctl run-pytest tests/weppcloud/routes/test_<domain>_bp.py
```

## Documentation Contract

### Controller README

**Each controller should document:**
- DOM contract (required elements, data attributes)
- Event surface (emitted events, expected subscribers)
- Transport endpoints (routes, payload schemas)
- Dynamic loading behavior (if applicable)
- Testing coverage

### Controller Reference Examples

See these controllers for reference implementations:
- **Climate:** Helper-first, scoped events, WebSocket streaming
- **Map:** Tab management, elevation probes, overlay refresh
- **Subcatchments:** Form serialization, delegated actions, map integration
- **Project:** Header controls, readonly toggles, unitizer sync

## Accessibility Requirements

**Every controller MUST:**
- Use semantic HTML (`<button>`, `<label>`, `<fieldset>`)
- Include `aria-label` on icon-only buttons
- Link inputs to labels via `for` attribute
- Use `aria-describedby` for help text and errors
- Mark error containers with `role="alert"`
- Ensure focus outlines remain visible
- Support keyboard navigation

**Status panels MUST use `aria-live="polite"` for screen reader announcements.**

## Migration Checklist

When modernizing a controller:

- [ ] Replace jQuery with `WCDom`, `WCHttp`, `WCForms`
- [ ] Use delegated events on data attributes
- [ ] Implement re-query pattern in `bootstrap()`
- [ ] Test dynamic loading scenario
- [ ] Add Jest unit tests
- [ ] Add Playwright regression test
- [ ] Document DOM contract in controller README
- [ ] Update `controllers_js/README.md` reference section

## Anti-Patterns

### ❌ Don't

**Query DOM only in createInstance():**
```javascript
function createInstance() {
    var form = dom.qs("#form"); // May be null!
    return { form: form };
}
```

**Use inline event handlers:**
```html
<button onclick="controller.submit()">Submit</button>
```

**Make multiple XMLHttpRequest without WCHttp:**
```javascript
var xhr = new XMLHttpRequest();
xhr.open('POST', '/tasks/something');
```

**Skip bootstrap re-query:**
```javascript
controller.bootstrap = function(context) {
    // Assumes elements exist - fails for dynamic loading!
    controller.form.addEventListener(...);
};
```

### ✅ Do

**Query lazily or re-query in bootstrap:**
```javascript
controller.bootstrap = function(context) {
    if (!controller.form) {
        controller.form = dom.qs("#form");
    }
};
```

**Use delegated events:**
```javascript
dom.delegate(container, "click", "[data-action='submit']", handleSubmit);
```

**Route through WCHttp:**
```javascript
WCHttp.postJson(url_for_run("tasks/something"), payload);
```

**Always check element existence:**
```javascript
if (controller.form) {
    controller.form.reset();
}
```

## Further Reading

- [`controllers_js/README.md`](../../wepppy/weppcloud/controllers_js/README.md) - Architecture and bundling
- [`dynamic-mod-loading-patterns.md`](../dev-notes/dynamic-mod-loading-patterns.md) - Deep dive on dynamic loading
- [`ui-style-guide.md`](ui-style-guide.md) - UI patterns and templates
- [AGENTS.md](../../AGENTS.md#front-end-development) - Front-end development section
