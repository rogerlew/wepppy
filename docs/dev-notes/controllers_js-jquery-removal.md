# controllers_js jQuery Removal
> Inventory and roadmap for migrating WEPPcloud run controllers away from jQuery.

## Snapshot
- The `controllers_js/` bundle still depends heavily on global jQuery for DOM selection, event delegation, form serialization, and AJAX calls. Core infrastructure (`control_base.js`, `status_stream.js`, most controllers) expose jQuery-aware adapters to one another, although new controllers default to native DOM helpers.
- Newer utilities (`status_stream.js`, `modal.js`, `unitizer_client.js`) already use modern browser APIs, proving a path to full removal.
- Eliminating jQuery requires a coordinated rewrite of `control_base`, shared helpers, and 20+ controllers that currently assume `$` is available. The largest blockers are job-status management, form serialization, and delegated events on controller forms.
- We can phase the migration by first introducing vanilla helpers (fetch wrapper, DOM utilities, event bus) and then refactoring controllers in families while keeping build output stable.

## Current Footprint

### Bundling and Infrastructure
- `build_controllers_js.py` renders `templates/controllers.js.j2`, concatenating all `.js` files in dependency order. `control_base.js`, `utils.js`, and `status_stream.js` land first; controller modules follow alphabetically.
- Most controller modules initialize via `var Foo = function () { … return { getInstance } }();`. Inside `createInstance()` they call `controlBase()` to inherit common behavior, cache jQuery selections (`that.form = $('#control_form')`), and wire up delegated `form.on('event', selector, handler)` listeners.
- HTML templates under `wepppy/weppcloud/templates/controls/` expose IDs/classes that the controllers expect. `_pure_macros.html` and `_base.htm` define the shared regions `#status`, `#stacktrace`, `#rq_job`, etc.

### jQuery Usage Overview
The table below captures the jQuery AJAX helpers detected in each controller (via `$.method` calls). All but a handful rely on jQuery’s XHR wrapper:

| File | AJAX helpers |
| --- | --- |
| ash.js | `$.get`, `$.post` |
| baer.js | `$.get`, `$.post` |
| channel_delineation.js | `$.get`, `$.post`, `$.getJSON`, `$.inArray` |
| climate.js | `$.get`, `$.post` |
| control_base.js | `$.ajax` (job status polling) |
| debris_flow.js | `$.post` |
| disturbed.js | `$.ajax`, `$.get` |
| dss_export.js | `$.post` |
| landuse.js | `$.get`, `$.post` |
| landuse_modify.js | `$.get`, `$.post` |
| map.js | `$.ajax`, `$.get` |
| observed.js | `$.get`, `$.post` |
| omni.js | `$.get`, `$.post` |
| outlet.js | `$.get`, `$.post` |
| path_ce.js | `$.ajax`, `$.get`, `$.post` |
| project.js | `$.get`, `$.post`, `$.Deferred` |
| rangeland_cover.js | `$.get`, `$.post` |
| rangeland_cover_modify.js | `$.get`, `$.post` |
| rap_ts.js | `$.post` |
| rhem.js | `$.get`, `$.post` |
| soil.js | `$.get`, `$.post` |
| subcatchment_delineation.js | `$.get`, `$.post`, `$.ajax`, `$.Deferred`, `$.when` |
| team.js | `$.get`, `$.post` |
| treatments.js | `$.get`, `$.post` |
| wepp.js | `$.get`, `$.post` |

DOM-heavy patterns include:
- Cached jQuery objects (e.g., `that.stacktrace = $("#stacktrace")`, `that.centerInput = $("#input_centerloc")`) shared across methods.
- Event delegation via `form.on('event.namespace', selector, handler)` and `$(document).on(...)`. Almost every controller registers multiple handlers this way.
- Form helpers (`form.serialize()`, `.serializeArray()`, `.val()`, `.prop()`, `.data()`, `.trigger()`), show/hide toggling (`.show()`, `.hide()`, `.toggleClass()`), and DOM writes (`.text()`, `.html()`, `.append()`, `.empty()`).
- Promise bridges using `$.Deferred()`/`$.when()` (Project controller name/scenario updates, subcatchment workflows).

### Shared Dependencies and Touchpoints
- **`control_base.js`**: Manages RQ job IDs, polling intervals, button enable/disable, stacktrace rendering, and WebSocket integration. It relies on jQuery objects for buttons, status areas, and event emission (`form.trigger`). Every control that calls `controlBase()` inherits these expectations.
- **StatusStream helper**: `controlBase.attach_status_stream` is now the single integration point for job telemetry. It fabricates hidden panels when legacy templates lack Pure status markup, so no additional shim is required.
- **Form templates**: Many macros (e.g., `controls/_pure_macros.html`, `runs0_pure.htm`) include script blocks that assume `$` exists when initializing controllers.
- **`UnitizerClient` bridge**: Controllers like `project.js` and `landuse.js` call into `UnitizerClient.ready()` then manipulate jQuery-wrapped DOM to update units. The bridge itself is vanilla but expects callers to pass native elements or jQuery objects with `.html()`/`.val()`.
- **Leaflet + jQuery**: Map interactions mix Leaflet APIs with jQuery for DOM controls (search inputs, legend toggles) and rely on the `leaflet-ajax` plugin (`L.geoJson.ajax`).
- **Templates referencing jQuery UI idioms**: Some controllers toggle classes defined by Pure CSS but still expect jQuery’s animation-less `.show()` / `.hide()` semantics (display block/none).

### Already Vanilla Modules
- `status_stream.js`, `modal.js`, `unitizer_client.js`, `utils.js` (partial), and the newly refactored tab/command helpers avoid jQuery entirely. They provide working examples for event wiring, DOM updates, and fetch-based network calls.

## Pain Points
- **Implicit global dependency**: Controllers never import jQuery—templates ensure `$` is global. Any per-controller rewrite must either polyfill or refactor all call sites in one go.
- **ControlBase contract**: Buttons, stacktraces, and job cards are all manipulated through jQuery methods on cached instances. Replacing those with vanilla APIs requires updating every controller that reads/writes `that.stacktrace`, `that.form`, or `that.command_btn_id`.
- **Delegated events**: `form.on('event', selector, handler)` is concise and covers future dynamic rows (e.g., Path CE treatments). The vanilla equivalent needs helper utilities to maintain clarity (`delegate(form, 'click', selector, handler)`).
- **Form submission helpers**: Controllers rely on `form.serialize()` to post JSON-like payloads. Vanilla replacements must reproduce the exact encoding (URL-encoded by default) and observed casing.
- **Async chaining**: `$.Deferred` & `$.when` provide `resolve()/reject()` semantics without native Promises. Rewrites must translate to `Promise`/`async` patterns without altering behavior.
- **Leaflet plugin coupling**: Some map layers (`L.geoJson.ajax`) automatically use jQuery for XHR unless replaced with Fetch-backed loaders.
- **Testing coverage**: No automated tests currently exercise the controllers. Migration will require either Cypress/Playwright smoke tests or targeted Jest/dom tests to reduce regression risk.

## Migration Strategy

### Phase 0 — Foundations
1. **Introduce vanilla helpers** under `controllers_js/`:
   - `dom.js`: `qs`, `qsa`, `delegate`, `toggle`, `setText`, etc.
   - `http.js`: Fetch wrapper with consistent headers (`Accept`, CSRF token), JSON helpers, error normalization.
   - `forms.js`: Serialize `<form>` elements to URLSearchParams/JSON, mirror `form.serialize()` semantics, and expose utility to sync checkboxes/selects.
   - `events.js`: Tiny pub/sub for emitting controller events (replacing `form.trigger`).
2. **Document the new helpers** in `controllers_js/README.md` and update bundler ordering so helpers precede controllers that import them.
3. **Server-side payload compatibility**: rely on the shared Flask helper `parse_request_payload(request, …)` from `wepppy.weppcloud.routes._common` to:
   - Attempts `request.get_json(silent=True)` to accept explicit JSON bodies from the rewritten controllers.
   - Falls back to `request.form.to_dict(flat=False)` for legacy `application/x-www-form-urlencoded` posts.
   - Normalizes checkbox-style inputs into booleans (`"on"`, `"true"`, `"1"` → `True`) and preserves arrays from multi-selects.
   - Ensures backwards compatibility by leaving untouched keys that legacy routes already inspect (`mode`, `landuse_single_selection`, etc.).
   This lets routes accept both the old jQuery serialization and the new vanilla payloads during the migration window.

### Phase 1 — Core Infrastructure Rewrite
1. **Refactor `control_base.js`** to operate purely on native elements:
   - Accept selectors or elements and wrap them in lightweight adapters.
   - Replace `$.ajax` polling with `fetch` (`GET` status endpoint, `signal` for abort).
   - Swap `stacktrace.show()/text()/append()` with templated DOM writes (consider using `<details>` for persistent stack traces).
2. **Lock status streaming on the helper**:
   - Ensure every controller calls `controlBase.attach_status_stream({ channel })`; legacy `WSClient` constructors should not reappear.
   - Let the helper build fallback status/stacktrace panels on legacy templates so controllers never branch on markup presence.
   - (Completed) Delete the legacy `ws_client.js` compatibility shim now that every template relies on `controlBase.attach_status_stream`.

### Phase 2 — Controller Families
Proceed controller-by-controller in logical groups so shared templates can be updated together:
1. **Foundational forms**: `project.js`, `wepp.js`, `landuse.js`, `soil.js`, `climate.js` (heavily used). Rewrite event wiring and AJAX calls using the new helper modules. Replace `form.serialize()` with `serializeForm(form)`.
2. **Map and delineation**: `map.js`, `channel_delineation.js`, `subcatchment_delineation.js`, `outlet.js`. Coordinate with Leaflet integration—consider replacing `L.geoJson.ajax` (jQuery) with `fetch` + `L.geoJSON`.
3. **Specialty modules**: `path_ce.js`, `disturbed.js`, `omni.js`, `rhem.js`, `ash.js`, `treatments.js`, etc. Many share `controlBase` patterns, so once Phase 1 lands these conversions are mostly mechanical.
4. **Legacy holdouts**: Clean up `$.Deferred` usage by converting to native `Promise` flows, update `Project` controller debouncing, and ensure command bar notifications work without jQuery.
5. **Route adaptations (same change)**: When converting a controller, update its paired Flask route in the same change-set to consume the normalized payload helper instead of raw `request.form`. Remove assumptions about `"on"`/`"off"` sentinels and rely on booleans/arrays provided by the helper so controller and backend stay in lockstep.

Each batch should:
- Update the paired control template (Pure macros) to remove `$(document).ready` hooks.
- Replace inline `$` calls in templates with vanilla `addEventListener`.
- Run `build_controllers_js.py` and manual browser smoke tests.

### Phase 3 — Remove jQuery from bundle
1. Once all controllers are migrated, drop the `<script>` tag that loads jQuery in the base template.
2. Delete shim logic from Phase 1 (`if (element.jquery)`). Ensure tests confirm `$` is undefined.
3. Audit remaining static assets (e.g., `sorttable.js`, `select2` etc.) to confirm they do not silently depend on jQuery.

## Replacement Cookbook

| jQuery usage | Vanilla replacement |
| --- | --- |
| `$.ajax({ url, method, data, dataType })` | `fetch(url, { method, headers, body })` with helper that auto-serializes payloads and returns JSON/text. |
| `$.get`, `$.post` | `fetchJson(url, { method: 'GET'/'POST', body })` convenience wrappers. |
| `form.serialize()` | `serializeForm(form)` returning `URLSearchParams` (for legacy endpoints) or `FormData`/JSON where applicable. |
| `$(selector)` | `document.querySelector(selector)` (single) or `querySelectorAll` (loop). Provide helper to accept either string or element. |
| `el.on(event, selector, handler)` | `delegate(root, event, selector, handler)` helper using `addEventListener` + `event.target.closest`. |
| `el.trigger('custom', data)` | `root.dispatchEvent(new CustomEvent('custom', { detail: data }))`. |
| `el.show()` / `el.hide()` | `element.hidden = false/true` or toggle CSS classes (`classList.add/remove`). |
| `el.val()` | `element.value` (for inputs/selects). |
| `el.prop('disabled', true)` | `element.disabled = true`. |
| `el.data('key')` | `element.dataset.key`. |
| `$.Deferred` / `$.when` | Native `Promise`, `Promise.resolve()`, `Promise.all([...])`. |

## Helper Module Specifications

Detailed targets for the foundational helper modules so parallel agents can implement them consistently:

### `dom.js`
- `qs(target, context = document)` → `HTMLElement | null`: accepts a selector string or element; returns the element untouched if already passed. Throws a descriptive error when provided an invalid type.
- `qsa(target, context = document)` → `HTMLElement[]`: wraps `querySelectorAll`, always returns an array copy.
- `delegate(root, eventName, selector, handler, options)`:
  - Uses `addEventListener` with a single listener per `(root,event,selector,handler)`.
  - Calls `handler(event, matchedElement)` when `event.target.closest(selector)` matches inside `root`.
  - Supports optional `options` (e.g., `{ passive: true }`) forwarded to `addEventListener`.
- `setText(element, text)` / `setHTML(element, html)`: coerce input via `qs`; gracefully handle `null` by no-op.
- `show(element)` / `hide(element)` / `toggle(element, force)`:
  - Use `hidden` attribute by default; accept optional `{ display: 'flex' }` override when needed.
- `addClass(element, className)` / `removeClass(element, className)` / `toggleClass(element, className, force)` via `classList`.
- `ariaBusy(element, isBusy)` helper for common loading state toggles.
- Expose utility `ensureElement(element, message)` that throws when the element cannot be resolved (helps controllers fail fast).

### `http.js`
- Central `request(url, { method = 'GET', headers, params, body, json, signal, timeoutMs })` returning a promise that resolves with a `{ ok, status, statusText, headers, body }` object.
  - Automatically prefixes the URL with `site_prefix` if provided globally.
  - Appends `params` (object or `URLSearchParams`) to the URL query string.
  - If `json` is provided, sets `Content-Type: application/json` and stringifies; otherwise accepts `body` as `FormData`, `URLSearchParams`, or string.
  - Always includes `Accept: application/json, text/plain;q=0.9` unless overridden.
  - Injects CSRF token header `X-CSRFToken` when present on `<meta name="csrf-token">` or cookies (reuse existing `getCsrfToken` logic if available).
  - Timeout support using `AbortController`.
- Convenience wrappers:
  - `getJson(url, options)` → resolves with parsed JSON or rejects with descriptive `HttpError`.
  - `postJson(url, payload, options)` → sets `method: 'POST', json: payload`.
  - `postForm(url, formDataOrObject, options)` → serializes object to `application/x-www-form-urlencoded` using `forms.js`.
- Error handling:
  - Throw `HttpError` instances containing `status`, `statusText`, `detail` (parsed JSON error or text), and `response`.
  - Provide `isHttpError(err)` type guard.

### `forms.js`
- `serializeForm(form, { format = 'url', includeDisabled = false })`:
  - Accepts a `HTMLFormElement` or selector.
  - Output options:
    - `'url'` → `URLSearchParams` matching jQuery’s default (ignore disabled inputs, unchecked checkboxes/radios omitted, multi-selects repeated).
    - `'object'` → plain object with arrays for multi-values.
    - `'json'` → JSON-ready object (same as `'object'` but without `URLSearchParams` wrapping).
  - Normalizes checkboxes: returns `true/false` for `'object'`/`'json'`, string `'on'` for URL encoding.
- `serializeFields(fields, format)` to support ad-hoc payload construction (accepts array of `{ name, value }`).
- `formToJSON(form)` as shorthand for `serializeForm(form, { format: 'json' })`.
- `applyValues(form, values)`:
  - Sets field values from an object (handles arrays for multi-select/checklist).
  - Toggles checkboxes by boolean.
- Helpers for CSRF extraction (`findCsrfToken(form)`) if not in meta.

### `events.js`
- Lightweight emitter factory: `createEmitter()` returning `{ on, off, once, emit, listenerCount }`.
  - `on(event, handler)` → unsubscribe function.
  - `once(event, handler)` → auto-removes after first call.
  - `emit(event, payload)` returns boolean indicating if handlers ran.
- DOM bridge: `emitDom(element, eventName, detail, { bubbles = true, cancelable = true })`.
- `forward(emitter, sourceEvent, targetEmitter, targetEvent = sourceEvent)` convenience for piping events between controllers.
- Optional `useEventMap(target)` wrapper that lets controllers attach strongly-typed event maps (prevents typos by warning when unknown event emitted in development mode).

Each module should be written as an IIFE that attaches to the global bundle namespace (e.g., `window.WCDom = { … }`) so existing controller files can `const { qs } = WCDom;` once included.

## Risks and Mitigation
- **Behavioral regressions**: Without automated UI tests, regressions may slip in. Mitigate by adding smoke tests (Playwright) for key workflows during each phase.
- **Template drift**: Some templates may still invoke `$` inline. Track these via `rg '\\$\\(' templates/` before removing jQuery.
- **Third-party plugins**: Verify whether dependencies like `leaflet-ajax`, `sorttable`, or custom vendor scripts rely on jQuery. Replace or fork as needed.
- **Browser support**: Confirm target browsers support ES2018+ features used by vanilla helpers (e.g., `fetch`, `classList`, `CustomEvent`). Provide polyfills if older browsers must be supported.

## Outstanding Tasks
- Audit controller initialization scripts in templates to catalog remaining `$(...)` usage.
- Design the helper modules (`dom.js`, `http.js`, `forms.js`) and add unit tests to guard behavior.
- Capture current jQuery network headers to ensure fetch replacement preserves `Accept`, `X-Requested-With`, and CSRF semantics.
- Investigate Leaflet layers that rely on `L.geoJson.ajax` and plan a fetch-based alternative.
- Identify priority controller groups (run-critical vs. low-traffic) to schedule migration windows without disrupting users.
