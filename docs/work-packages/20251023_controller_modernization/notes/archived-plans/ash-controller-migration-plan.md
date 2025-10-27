# Ash Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Helper-first modernization blueprint for WATAR control, routes, and NoDb.

## 1. Current State Snapshot
- **Controller**: `wepppy/weppcloud/controllers_js/ash.js` still depends on jQuery for selectors, event wiring, `$.post`/`$.get`, and global helpers (`window.updateAshModelForm`).
- **Templates**: `controls/ash.htm` and `controls/ash_pure.htm` expose IDs/classes but rely on implicit jQuery behaviours (show/hide, inline globals).
- **Backend**: `/rq/api/run_ash` parses `request.form` manually, infers booleans/floats, and writes stringified values into `Ash.parse_inputs`, which still anticipates `"on"` / string payloads.
- **Tests**: No Jest coverage for Ash controller behaviour; pytest lacks regression tests for the RQ endpoint or ash-specific payload parsing.

Risks include inconsistent depth mode validation between front-end/back-end, brittle model parameter caching, and stringly-typed values leaking into `Ash` state.

## 2. Target Architecture
- **Helpers**: Use `WCDom` for DOM lookups/show-hide, `WCForms` for form serialization/object merging, `WCHttp` for fetch wrappers, and `WCEvents.useEventMap` around a scoped `createEmitter`.
- **Event Contract**: Adopt the following events for downstream subscribers:
  - `ash:mode:changed` → payload `{ mode: number }`.
  - `ash:model:changed` → payload `{ model: string }`.
  - `ash:transport:mode` → payload `{ model: string, transportMode: string }`.
  - `ash:run:started` / `ash:run:completed` → payload includes `{ jobId }` when available.
  - `ash:model:values:capture` (optional) → emitted when Alex dynamic/static caches persist.
- **Control Base**: Continue leveraging `controlBase()` for status panes and RQ job wiring, but expose legacy adapters via `WCDom` to avoid regressions.

## 3. Front-End Refactor Outline
- Replace per-input listeners with delegated hooks tied to `data-ash-*` attributes (`data-ash-action`, `data-ash-depth-mode`, `data-ash-upload`).
- Maintain model parameter caching by persisting values via helper-managed maps; remove the global `window.updateAshModelForm`.
- Route async work through `WCHttp` (e.g., `postForm` for `/rq/api/run_ash`, `postJson` for `tasks/set_ash_wind_transport/`).
- Validate upload extensions/sizes via helper functions before submission; surface messages through `controlBase.showHint` helper.
- Emit lifecycle events when depth/mode/model/transport selections change and when run submissions start/finish.

## 4. Backend Alignment Tasks
- Swap `/rq/api/run_ash` to use `parse_request_payload(request)` to normalise primitives; extract `request.files` for raster uploads.
- Update `Ash.parse_inputs` (and getters) to accept native ints/floats/bools, avoiding `"on"` checks and guarding against `None`.
- Ensure spatial mode toggles (`AshSpatialMode.Gridded`) and file setters use typed values with consistent error handling via `exception_factory`.
- Maintain existing RedisPrep, telemetry, and Disturbed/Ash interactions.

## 5. Testing Strategy
- **Jest** (`controllers_js/__tests__/ash.test.js`):
  - Depth mode toggling shows/hides panels, caches values, and emits `ash:mode:changed`.
  - Model selector ensures Alex vs Anu panels flip, caches persisted numeric inputs, and transport mode updates emit `ash:transport:mode`.
  - Run submission posts via `WCHttp.postForm`, validates FormData contents, emits `ash:run:started/completed`, and handles errors.
  - Wind transport checkbox posts JSON payload and reports stacktrace on failures.
- **Pytest** (`tests/weppcloud/routes/test_rq_api_ash.py`):
  - Valid payloads enqueue RQ job with parsed floats/ints/bools.
  - Map uploads (mocked via `BytesIO`) respect extension/size checks and missing file errors return `exception_factory` payloads.
  - Depth mode conversions validate numeric parsing and zero-division protection.

Commands to run after implementation:
```bash
wctl run-npm lint
wctl run-npm test
python wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl run-pytest tests/weppcloud/routes/test_rq_api_ash.py
```

## 6. Template Updates
- Remove inline jQuery assumptions; rely on data attributes consumed by the refactored controller.
- Ensure collapsible/advanced panels remain accessible with semantic markup (`hidden` toggles instead of `.show()`/`.hide()`).
- Keep script tag `ash-model-params-data` as JSON source; controller will parse via DOM helpers.

## 7. Follow-Ups & Compatibility Notes
- Document the event contract and helper usage in `controllers_js/README.md` and `controllers_js/AGENTS.md`.
- Cross-link this plan from `controller_foundations.md` if new primitives emerge.
- After roll-out, audit other controllers sharing ash tasks (e.g., Disturbed overlays) for subscription opportunities.

