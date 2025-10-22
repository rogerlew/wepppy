# Outlet Controller Modernization Plan
> Working note capturing scope, decisions, and follow-ups while migrating the outlet control to the helper-first architecture.

## Current State (Pre-Refactor)
- `wepppy/weppcloud/controllers_js/outlet.js` is still jQuery-driven:
  - Direct `$()` selectors for every element and `.on()` bindings for radio group, cursor button, and entry button.
  - `$.get`/`$.post` calls handle outlet queries and job submission; payloads arrive as form-encoded strings (`longitude`/`latitude`).
  - Cursor toggling mutates text content manually and flips `.css("cursor", …)` on the Leaflet container.
- Template markup (`templates/controls/set_outlet_pure.htm`) keeps legacy IDs but lacks helper-friendly `data-*` hooks, so `WCDom.delegate` is unused.
- RQ route (`routes/rq/api/api.py::api_set_outlet`) still reads `request.form` and casts to float; no shared payload parser yet.
- No Jest coverage exists for outlet behavior; pytest suites do not exercise the endpoint with the normalized payload.

## Refactor Goals
1. Rewrite the controller on top of helper modules:
   - Use `WCDom`, `WCEvents`, `WCHttp`, and `controlBase` lifecycle helpers.
   - Emit scoped events such as `outlet:set:start/success/error`.
   - Replace polling hacks with `job:started/completed/error` events from `controlBase`.
   - Provide cursor vs entry mode handling via data attributes instead of jQuery show/hide.
2. Align templates with helper expectations:
   - Introduce `data-outlet-*` hooks for delegated listeners.
   - Document any new attributes/ARIA adjustments in README + this note.
3. Normalize backend payload handling:
   - Adopt `parse_request_payload` for `api_set_outlet`.
   - Ensure downstream calls (`set_outlet_rq`, NoDb) receive native floats.
4. Add testing + docs:
   - Jest tests for mode switching, event emission, and job submission flows.
   - Pytest coverage for the updated endpoint (happy path + validation failure).
   - Update `controllers_js/README.md`, `controllers_js/AGENTS.md`, and this note with emitted events + payload schema.

## Modernization Notes (In Progress)
- **Data hooks**: templates expose `data-outlet-root`, `data-outlet-mode-section`, `data-outlet-entry-field`, and `data-outlet-action` attributes so the controller can rely on `WCDom.delegate` and helper-friendly selectors. Entry controls default to `hidden` rather than inline styles.
- **Controller helpers**: the refactor replaces all `$` usage with `WCDom`, `WCHttp`, and `WCEvents`. `controlBase` lifecycle hooks (`job:started`, `job:completed`, `job:error`) now wrap the RQ job instead of manual status polling.
- **Event surface**: Outlet emits `outlet:mode:change`, `outlet:cursor:toggle`, `outlet:set:start`, `outlet:set:queued`, `outlet:set:success`, `outlet:set:error`, and `outlet:display:refresh`. Capture subscribers in README/AGENTS once tests land.
- **Payload schema**: `POST rq/api/set_outlet` accepts JSON or form data with `latitude`/`longitude` (floats). Optional envelope `{ "coordinates": { "lat": ..., "lng": ... } }` is also supported; the route normalises both.
- **Map behaviour**: cursor toggling now runs through a dedicated helper that updates button labels, ARIA state, hint text, and Leaflet cursor styling via `WCDom`.

## Open Questions / Follow-Ups
- Confirm whether other controllers consume outlet status events; document any new event names so subscribers can adjust.
- Evaluate whether cursor hint messaging should move into a shared Leaflet helper (out of scope for this refactor but worth tracking).
- Consider backfilling an integration test that exercises the Redis prep timestamp removal to guard against regressions.
