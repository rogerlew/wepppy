# Agent Prompt – Controller Bootstrap Migration

## Mission
Refactor controller initialization so every panel boots through a shared helper instead of bespoke wiring in `run_page_bootstrap.js.j2`. Define a clear bootstrap contract, update controllers to implement it, and modernize the run-page script to consume the contract. Finish with documentation and targeted tests so future agents can rely on the new flow.

## Background
- The Pure layout is now the production default; legacy `_base.htm` and `0.htm` are archival only.
- StatusStream is the single telemetry pipeline; controllers expose helpers such as `attach_status_stream`, `setMode`, `events`, etc.
- `run_page_bootstrap.js.j2` still contains legacy DOM pokes (`set_rq_job_id`, `triggerEvent`, jQuery-esque selectors). We need a structured initialization path that hands controllers the run context (job IDs, flags) without duplicating controller logic.
- Work package: `docs/work-packages/20251023_frontend_integration/` (see `package.md` + `tracker.md`).

## Goals / Deliverables
1. **Bootstrap Contract**
   - Design a `Controller.bootstrap(context)` (or equivalent) API implemented by each controller that requires run-scoped initialization.
   - Context should minimally include: `jobIds`, `sitePrefix`, `runId`, `config`, and controller-specific flags (e.g., `hasSubcatchments`, `hasChannels`, `initialHasSbs`).
   - Document the contract in controller docs (`controllers_js/README.md`, work-package tracker, and `control-ui-styling/AGENTS.md`).

2. **Controller Updates**
   - Update relevant controllers (`map.js`, `channel_delineation.js`, `subcatchment_delineation.js`, `outlet.js`, `landuse.js`, `rangeland_cover.js`, `treatments.js`, `baer.js`, `disturbed.js`, etc.) to expose the new bootstrap entry point.
   - Move existing initialization logic (job id wiring, mode setup, event listeners) inside the bootstrap implementation.
   - Ensure controllers fall back gracefully if bootstrap is called multiple times (idempotent setup).

3. **run_page_bootstrap.js.j2 Refactor**
   - Detect Pure layout (legacy path can be ignored/removed).
   - Replace manual DOM operations with calls to `Controller.bootstrap(context)`.
   - Collect run-scope context once (jobs, mods, toggles) and pass to controllers.
   - Remove direct references to jQuery-only APIs.

4. **Tests / Validation**
   - Update Jest controller tests to cover the bootstrap contract (mock context, ensure helpers called).
   - Add a small unit/smoke test for the bootstrap script (if feasible) or document manual verification steps.
   - Execute `wctl run-npm lint` and relevant controller test suites (map, landuse, climate, treatments, etc.). Document results.

5. **Documentation**
   - Update `docs/ui-docs/control-ui-styling/control-inventory.md` footnotes if bootstrap behaviours change.
   - Note the new contract in `docs/ui-docs/control-ui-styling/AGENTS.md` and `docs/work-packages/20251023_frontend_integration/tracker.md`.
   - Provide a short implementation summary in the work-package tracker with follow-ups (if any).

## Reference Files
- `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- Controllers under `wepppy/weppcloud/controllers_js/`
- Work package docs: `docs/work-packages/20251023_frontend_integration/`
- UI docs: `docs/ui-docs/control-ui-styling/`

## Success Criteria
- All controllers initialize through the shared bootstrap contract.
- `run_page_bootstrap.js.j2` no longer manually mutates DOM/state per controller.
- Tests/lint succeed; smoke plan (from bootstrap checklist) is updated with any new steps.
- Documentation reflects the new bootstrap workflow; no dangling references to the legacy init flow.

Hand off with a concise summary (changes, tests run, remaining risks) in the package tracker.
