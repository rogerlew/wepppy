# Agent Prompt: Implement controllers_js Helper Modules

## Mission
Build the foundational vanilla JS helper modules that will replace our jQuery dependency inside `wepppy/weppcloud/controllers_js/`. Your implementation should follow the contracts documented in `docs/dev-notes/controllers_js-jquery-removal.md` (see **Helper Module Specifications** section).

## Key References
- `docs/dev-notes/controllers_js-jquery-removal.md` — authoritative spec (targets: `dom.js`, `http.js`, `forms.js`, `events.js`).
- `wepppy/weppcloud/controllers_js/` — bundle sources and current build script (`build_controllers_js.py`).
- `wepppy/weppcloud/controllers_js/README.md` — update this file to describe the new helpers and bundling order.

## Deliverables
1. New helper modules:
   - `wepppy/weppcloud/controllers_js/dom.js`
   - `wepppy/weppcloud/controllers_js/http.js`
   - `wepppy/weppcloud/controllers_js/forms.js`
   - `wepppy/weppcloud/controllers_js/events.js`
   Implement as IIFEs that attach a namespaced API (e.g., `window.WCDom`, `window.WCHttp`, …) and match every function/capability called out in the spec.
2. Documentation updates:
   - Extend `controllers_js/README.md` with usage notes and ordering requirements.
   - If helper behavior differs slightly from the spec (e.g., additional utility functions), document the rationale.
3. Build integration:
   - Ensure `build_controllers_js.py` emits the helper modules before any controller that consumes them. Add automated ordering if necessary.
4. Quality gates:
   - Run `python wepppy/weppcloud/controllers_js/build_controllers_js.py` to confirm the bundle renders without errors.
   - Provide a brief validation summary (e.g., linting or manual bundle inspection) in your final response.

## Acceptance Criteria
- All functions described in the spec exist, handle both happy-path and defensive cases, and include inline JSDoc or concise comments where non-trivial.
- Helper APIs gracefully accept either selector strings or element references, with clear error messages on invalid usage.
- HTTP utilities handle prefixing with `site_prefix`, CSRF propagation, JSON/body normalization, and timeout support. Errors throw `HttpError` objects with rich metadata.
- Form serialization mirrors jQuery semantics for URL-encoded payloads and provides object/JSON conversions plus value application helpers.
- Events module exposes emitter utilities with `on/off/once/emit`, DOM bridge helpers, and optional piping.
- No dependencies on jQuery remain inside the new modules; they should be framework-agnostic.
- README documents how controllers should import/consume the new helpers.

## Notes
- Keep everything ES2018-compatible (no transpilation).
- Use existing logging patterns (`console.warn`, etc.) sparingly and consistently.
- If you uncover gaps in the spec, flag them in your status update and propose a resolution before coding.

## Follow-up
After completing the helper modules, write Jest unit tests under `wepppy/weppcloud/controllers_js/__tests__/` that cover key behaviors (selector resolution, delegation, serialization edge cases, HTTP error handling, emitter events) and update package scripts so `npm test` executes the suite.
