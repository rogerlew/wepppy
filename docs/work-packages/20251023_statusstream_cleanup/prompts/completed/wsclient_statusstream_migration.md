# WSClient → StatusStream Cleanup (Archived)

`WSClient` has been fully removed in favour of the unified StatusStream pipeline. Use this checklist when sanity-checking future controller or telemetry work: ensure everything still flows through `controlBase.attach_status_stream` and no one reintroduces the legacy shim.

## Grounding References
- `docs/dev-notes/controller_foundations.md` – shared controller vision, helper expectations, controlBase roadmap.
- `docs/dev-notes/controllers_js_jquery_retro.md` – modernization retrospective; keep it in sync with ongoing StatusStream maintenance work.
- `wepppy/weppcloud/controllers_js/README.md` & `AGENTS.md` – helper usage, controller contracts, current modernization status.
- Source tree for helpers/controllers/tests: `wepppy/weppcloud/controllers_js/`.
- Jest suites: `wepppy/weppcloud/controllers_js/__tests__/`.
- Relevant Flask routes for telemetry payloads: `wepppy/weppcloud/routes`.

## Working Set
Focus on:
- `wepppy/weppcloud/controllers_js/status_stream.js`
- `wepppy/weppcloud/controllers_js/control_base.js`
- `controlBase.attach_status_stream` helper (ensure all controllers route through it)
- Compatibility surface check: ensure no new references to `WSClient` appear (search for raw instantiations or global usages)
- Shared helper addition (new adapter or module under `controllers_js/`)
- Tests under `controllers_js/__tests__`
- Docs noted above

Expect to touch templates only if legacy jQuery bootstrap remains after the refactor (grep `rg '\$\(' wepppy/weppcloud/templates`).

## Deliverables
1. **StatusStream Verification**
   - Ensure the StatusStream adapter exposes all behaviours the shim forwards today:
     - Spinner tick updates (`#braille`)
     - Trigger event propagation (`TRIGGER` messages → `controlBase.triggerEvent`)
     - Stacktrace enrichment remains functional
   - Maintain the existing API surface for consumers (climate, rhem, treatments, team).

2. **Control Base Integration**
   - Keep `self.status_stream` plumbing centred on `controlBase.attach_status_stream`.
   - Guarantee `controlBase.triggerEvent` continues to fire DOM events for legacy listeners.
   - Ensure fallback panel creation still works when legacy templates lack Pure markup.

3. **Controller Migration**
   - Confirm every controller calls `controlBase.attach_status_stream` (no `new WSClient(...)` remaining).
   - Remove jQuery-specific code paths that only existed for the shim (spinner, status text writes, stacktrace fetch).
   - Keep controller-specific telemetry (e.g., `wepp.triggerEvent`) working.

4. **Testing**
   - Add Jest coverage for the new adapter/StatusStream hooks.
   - Keep controller tests focused on StatusStream interactions.
   - Ensure the bundle builds (`python wepppy/weppcloud/controllers_js/build_controllers_js.py`).
   - Run lint/tests: `wctl run-npm lint`, `wctl run-npm test -- <affected suites>`, plus targeted pytest for routes touched.

5. **Cleanup & Documentation**
   - Confirm docs (`controllers_js/README.md`, `AGENTS.md`, `docs/dev-notes/controllers_js_jquery_retro.md`) continue to describe the StatusStream-only flow.
   - Note telemetry changes or new helpers in `controller_foundations.md` if the contract expands.

## Validation Checklist
- `wctl run-npm lint`
- `wctl run-npm test -- <updated suites>` (include new adapter tests + impacted controllers)
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest` for any backend routes touched (list in handoff)

## Handoff Report
When finished, summarize:
- Key code changes (helpers, controlBase, controllers)
- Tests/commands executed with results
- Docs updated
- Known risks or follow-up tasks (e.g., templates still holding jQuery hooks)

Keep StatusStream as the single telemetry pipeline—no resurrections of the WSClient shim.
