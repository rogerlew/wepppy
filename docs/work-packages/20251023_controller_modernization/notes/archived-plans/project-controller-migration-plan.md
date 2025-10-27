## Project Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Reference contract for the modernized Project run control. Keep this doc in sync with `controllers_js/project.js`, the paired Flask routes, and associated templates.

### Why this matters
- Project state is the first touch point for every WEPPcloud run. Aligning it with the controller foundations establishes the pattern other modules should follow: helpers over jQuery, declarative data hooks, scoped events, and typed payloads from browser → Flask → NoDb.
- The controller now acts as the single integration point for Unitizer preferences, run visibility, and command-bar messaging. Documenting the contract here keeps downstream work (command bar shortcuts, dev tools, docs) consistent.

### Markup contract
- **Name/Scenario inputs**: `data-project-field="name"` and `data-project-field="scenario"` (any element that emits `input` + `focusout` works).
- **Toggles**: `data-project-toggle="readonly"` and `data-project-toggle="public"`. Mark interactive elements with `disable-readonly` or `hide-readonly` so `Project.set_readonly_controls` can toggle access.
- **Actions**: buttons/links use `data-project-action="clear-locks" | "migrate-omni" | "enable-path-ce"` (extend with new verbs as needed).
- **Unitizer radios**: `data-project-unitizer="global"` (global preference) and `data-project-unitizer="category"` (per-category radios). Categories may add `data-unitizer-category="{{ unitclass }}"` for clarity.

### Event surface
`Project.getInstance().events` is a `WCEvents.useEventMap` instance exposing:
- `project:name:updated` / `project:name:update:failed`
- `project:scenario:updated` / `project:scenario:update:failed`
- `project:readonly:changed` / `project:readonly:update:failed`
- `project:public:changed` / `project:public:update:failed`
- `project:unitizer:sync:started` / `project:unitizer:preferences` / `project:unitizer:sync:completed` / `project:unitizer:sync:failed`

> Subscribe via `Project.getInstance().events.on(eventName, handler)`; avoid reading internal fields (`_currentName`, `_unitPreferenceInflight`, etc.) so the implementation can evolve without breaking dependents.

### Backend payloads
All routes parse bodies through `parse_request_payload`. Expected schema:

| Endpoint | Method | Payload shape | Notes |
| --- | --- | --- | --- |
| `/tasks/setname/` | `POST` | `{ "name": "<string>" }` | Server trims and defaults to `"Untitled"` when blank. Response: `{"Success": true, "Content": {"name": "<final>"}}`. |
| `/tasks/setscenario/` | `POST` | `{ "scenario": "<string>" }` | Trimmed server-side; empty string allowed. Response mirrors input. |
| `/tasks/set_public` | `POST` | `{ "public": <boolean> }` | Accepts form or JSON booleans. Response: `{"Success": true, "Content": {"public": <bool>}}`. |
| `/tasks/set_readonly` | `POST` | `{ "readonly": <boolean> }` | Enqueues background job and returns `{"Success": true, "Content": {"readonly": <bool>, "job_id": "<rq id>"}}`. |
| `/tasks/set_unit_preferences/` | `POST` | `{ "<category_key>": "<preferred_unit>" }` | Works with JSON or form bodies. Response: `{"Success": true, "Content": {"preferences": {...}}}`. |

Corresponding NoDb setters (`Ron.name`, `Ron.scenario`, and `Unitizer.set_preferences`) coerce incoming values to native types, so controllers can post JSON without `"on"`/`"off"` shims.

### Global helpers & integration points
- `window.setGlobalUnitizerPreference(pref)` now simply calls `Project.getInstance().handleGlobalUnitPreference(pref)`, keeping command-bar shortcuts and legacy scripts alive.
- Command bar notifications flow through `initializeCommandBar()` via `project.notifyCommandBar(message, { duration })`.

### Validation checklist
1. `wctl run-npm lint`
2. `wctl run-npm test`
3. `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
4. `wctl run-pytest tests/weppcloud/routes/test_project_bp.py`
5. `wctl run-pytest tests/weppcloud/routes/test_unitizer_bp.py`

Jest coverage lives in `controllers_js/__tests__/project.test.js`; extend it whenever you touch events, data hooks, or error flows.

### Related docs
- [controllers_js/README.md](../../../../../wepppy/weppcloud/controllers_js/README.md)
- [controllers_js/AGENTS.md](../../../../../wepppy/weppcloud/controllers_js/AGENTS.md)
- [docs/dev-notes/controller_foundations.md](../../../../dev-notes/controller_foundations.md)
