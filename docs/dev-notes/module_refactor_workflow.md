# Module Refactor Workflow
> End-to-end checklist for modernizing WEPPcloud controllers and paired routes.

## When to Use
- Migrating a `controllers_js` module from jQuery to the new helper APIs.
- Updating the corresponding Flask routes to support JSON/vanilla payloads.
- Refreshing module documentation after behavioral or API changes.
- Coordinating validation (Jest + Python tests) before handing off to downstream agents.

## Prerequisites
- Review the helper specs captured in `docs/dev-notes/controllers_js_jquery_retro.md`.
- Skim `wepppy/weppcloud/controllers_js/AGENTS.md` for the current controllers_js agent expectations.
- Skim the existing controller’s template(s) under `wepppy/weppcloud/templates/controls/`.
- Identify backend routes (`wepppy/weppcloud/routes/...`) handling the controller’s requests.
- Familiarise yourself with the architectural guide in `docs/dev-notes/controller_foundations.md`—it explains the shared UI primitives, payload schemas, and controlBase patterns we expect refactors to reinforce.
- Confirm the JavaScript toolchain is wired up for the workspace:
  - `wctl run-npm lint` (ESLint + Prettier) — lints staged controller changes.
  - `wctl run-npm test` — runs the Jest suite for controllers/helpers.
- Ensure the controller bundle builds: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

## Workflow Overview
1. **Assess & Scope**
   - Inventory jQuery touchpoints: DOM selectors, event handlers, AJAX calls, `$.Deferred`, etc.
   - Map outbound requests to Flask endpoints; note expected payload shapes.
   - Check existing documentation (README, dev notes) for outdated instructions.
   - Capture findings in your working notes; highlight risky couplings (e.g., templates with inline `$`).

2. **Plan the Refactor**
   - Choose the helper utilities you need (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`).
   - Decide on payload format (JSON vs `application/x-www-form-urlencoded`) and confirm the route can accept it.
   - Outline unit tests you’ll create or update (Jest for helpers/controllers, pytest for routes if applicable).
   - If multiple controllers share patterns, note follow-up tasks for future agents.

3. **Implement Changes**
   - Update the controller:
     - Replace jQuery selectors/events with `WCDom` equivalents (`qs`, `delegate`, etc.).
     - Swap `$.ajax`/`$.post` with `WCHttp.request`/`getJson`/`postJson`.
     - Use `WCForms.serializeForm` for form payloads; prefer JSON bodies when practical.
     - Replace `$.Deferred` with native Promises/async/await.
     - Remove global `$` dependencies from templates (use `addEventListener`, data attributes).
   - Adapt the Flask route in the same change:
     - Ingest payloads via the shared parser (`parse_request_payload`) from `wepppy.weppcloud.routes._common`.
     - Normalize booleans, arrays, and defaults previously inferred from jQuery’s serialization.
     - Maintain existing permission checks (`authorize`, etc.) and error semantics.
     - Add meaningful error messages for invalid payloads; ensure `exception_factory` integration remains intact.
     - Update associated NoDb singletons (`parse_inputs`, `set_*` helpers) to accept native Python values instead of `"on"`/`"True"` strings so both legacy form posts and JSON bodies behave the same way.

4. **Validate**
   - **Frontend**
     - `wctl run-npm lint` (ESLint/Prettier formatting checks for controllers/helpers)
     - `wctl run-npm test` (Jest regression tests)
     - `python wepppy/weppcloud/controllers_js/build_controllers_js.py` (or run from repo root) to rebuild the bundle and verify no syntax errors.
   - **Backend**
     - Run targeted pytest suites via `wctl run-pytest tests/weppcloud/...` so the code executes inside the Docker image with the same environment variables as production.
     - For broader changes, finish with `wctl run-pytest tests --maxfail=1` before handoff; no refactor is complete without a green pytest run.
     - For serialization changes, consider integration tests that POST sample payloads.
   - **Manual sanity**
     - Smoke test the updated UI in the dev environment if accessible (controller loads, actions perform as expected).
     - Check browser console for WebSocket and fetch errors.

5. **Document & Communicate**
   - Update or create README/AGENTS/dev notes describing the new APIs or flows.
   - If templates changed, note required markup expectations (data attributes, IDs).
   - Mention the Jest workflow in `controllers_js/AGENTS.md`  when adding new suites.
   - Call out the shared test factories (`tests/factories/`) in any route/controller notes you touch so future work leans on `rq_environment` and `singleton_factory` instead of bespoke mocks.
   - Log any deferred follow-ups (e.g., next controller to migrate) in the relevant dev note or task tracker.

6. **Handoff Checklist**
   - ✅ Controller uses helper modules exclusively (no residual `$`/`jQuery`).
   - ✅ Paired Flask route parses the new payload and preserves legacy behavior.
   - ✅ All automated tests (Jest + pytest) pass; bundle builds cleanly.
   - ✅ Documentation reflects the refactor (controller README, helper specs if extended).
   - ✅ Agent prompt updated if future work is expected (cite this workflow for reuse).

## Tips & Best Practices
- Keep changes cohesive: controller + route + docs + tests in one commit when possible.
- Preserve telemetry hooks (`controlBase`, `controlBase.attach_status_stream`/`StatusStream`) so status panels stay functional.
- Prefer explicit booleans in JSON payloads—avoid `"on"`/`"off"` strings to reduce backend ambiguity.
- For large controllers, refactor in logical sections (e.g., setup, event wiring, async workflow) with intermediate validations.

Use this document as both a checklist and a handoff artifact—link to it in future agent prompts so everyone follows the same playbook. Let’s keep refining it as we learn from subsequent migrations.
