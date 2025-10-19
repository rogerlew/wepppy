## Agent Brief: Unitizer Modal + Unit Map Export

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

_Last updated: 2025-10-19_

**Mission**: deliver the Pure-styled Unitizer experience and ship a static unit conversion map that the controllers bundle can import without runtime Python calls.

### Primary Targets
- Template refactor: `wepppy/weppcloud/templates/controls/unitizer_modal.htm`
- Source of truth: `wepppy/nodb/unitizer.py`
- Build hook: `wepppy/weppcloud/controllers_js/templates/controllers.js.j2` (and the `build_controllers_js.py` pipeline)
- Tokens: `wepppy/weppcloud/static/css/ui-foundation.css` (no inline styling)

### Deliverables
1. **Modal restyle**
   - Rebuild the modal markup with the Pure control shell primitives (`wc-field`, `.wc-choice--checkbox`, `.wc-choice-group`) and align spacing with `ui-foundation.css`.
   - Replace Bootstrap classes and legacy `<div class="form-group">` scaffolding with documented Pure tokens; ensure accessibility (focus trap preserved, labelled controls, `aria-describedby` tied to helper copy).
   - Surface the modal contents in `/ui/components/` so reviewers can test the redesign independent of the `run_0.runs0` route. Add an entry in the gallery that mirrors the production layout.

2. **Static conversion library**
   - Extract the unit maps, precision hints, and category metadata from `Unitizer` into a deterministic JSON/ES module generated during the controllers build.
   - Extend `build_controllers_js.py` (or a companion script) to output `wepppy/weppcloud/static/js/unitizer_map.js` (ES module exporting conversion tables + metadata). Keep it idempotent and consider hashes for cache busting.
   - Update the controllers bundle (and any helper that drives unit syncing) to import the generated map instead of performing AJAX calls or in-template serialization.

3. **Integration plumbing**
   - Ensure macros (`numeric_field`, future unit-aware controls) can read the static map by adding predictable `data-unit-key` attributes or a shared `UnitizerClient` helper inside `controllers.js`.
   - Confirm the modal writes preference changes back via existing endpoints while also updating the imported map consumer in real time.
   - Document the contract in `control_components.md` (inputs exposed, events fired) and drop a short usage note in `control-inventory.md` under the Unitizer section.

### Acceptance Checklist
- [ ] `/ui/components/` showcases the refreshed modal with Pure tokens and accessible markup.
- [ ] `unitizer_modal.htm` contains zero Bootstrap classes or inline style attributes.
- [ ] Controllers build emits `static/js/unitizer_map.js` (or equivalent) and the bundle consumes it without eval hacks.
- [ ] `numeric_field` + other unit-aware macros can toggle units using the static map without hitting Python endpoints.
- [ ] Tests or scripts validate the generated map against `Unitizer` definitions (checksum or structural diff).
- [ ] Docs updated (`control_components.md`, `control-inventory.md`) to reflect new attributes/events.
