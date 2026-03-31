# Disturbed Panel Modal and Landsoil Lookup UX Contract

**Status**: Complete (2026-03-30)

## Overview
This package introduces a dedicated Disturbed modal in the run-page More menu and removes disturbed lookup controls from the Power User panel. The goal is to make base versus extended landsoil table workflows explicit, reversible, and safer for users managing disturbed calibration parameters.

## Objectives
- Add a Disturbed modal entry in More-menu navigation, with the same modal footprint and visual treatment used by Power User.
- Move disturbed lookup actions out of `poweruser_panel.htm` into the new Disturbed modal.
- Add explicit lookup lifecycle controls: reset base table, load extended table, and delete extended table.
- Add explicit table-target controls for editing: modify base table, modify extended table, and sync base to extended.
- Define and implement a reusable Jinja utility for usersum documentation links with a prefixed documentation affordance glyph.
- Publish a developer-facing UI and route contract document for the Disturbed modal and keep it discoverable from package docs and root tracker.

## Scope
This package covers WEPPcloud run-page UI, disturbed route/controller behaviors, and usersum-link helper affordances tied to disturbed controls.

### Included
- New Disturbed modal template/trigger wiring from the More menu.
- Removal of disturbed action buttons and links from Power User panel.
- Disturbed modal sections and controls requested in tasking:
  - Landsoil lookup parameter table actions.
  - Lookup table resource selection.
  - Modify table actions.
  - Help section with usersum documentation link.
- Disturbed API additions required for UI actions (delete extended and base-to-extended sync).
- Edit-table route/link wiring for explicit `lookup=base` and `lookup=extended` entry points.
- Jinja utility for usersum links with a prefixed documentation glyph.
- Developer contract documentation and tests for route/UI behavior.

### Explicitly Out of Scope
- Reworking non-disturbed sections of the Power User panel.
- Broad visual redesign beyond introducing the new Disturbed modal and relocating disturbed controls.
- Changing disturbed lookup CSV schema semantics.
- Adding new disturbed scientific parameters unrelated to UI/control flow.

## Stakeholders
- **Primary**: WEPPcloud run-page users managing disturbed workflows.
- **Reviewers**: WEPPcloud routes/templates/controllers maintainers.
- **Informed**: Usersum/documentation maintainers and QA maintainers for run-page smoke coverage.

## Success Criteria
- [x] More menu exposes a dedicated Disturbed modal entry.
- [x] Power User panel no longer contains disturbed lookup actions or links.
- [x] Disturbed modal includes reset/load/delete lifecycle controls with status feedback.
- [x] Disturbed modal includes explicit base and extended modify actions and base-to-extended sync action.
- [x] Extended table can be deleted, and default editor selection falls back to base when extended is absent.
- [x] Usersum documentation link uses the new Jinja helper and renders with prefixed documentation affordance glyph.
- [x] Developer UI/route contract doc is published and linked from package docs.
- [x] Targeted test suites for disturbed routes and run-page UI wiring pass.

## Dependencies

### Prerequisites
- Existing disturbed lookup routing and variant resolution behavior in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`.
- Existing disturbed run-page control wiring in `wepppy/weppcloud/controllers_js/disturbed.js`.
- Existing usersum blueprint endpoints in `wepppy/weppcloud/routes/usersum/usersum.py`.

### Blocks
- Follow-on UX cleanup for additional mod-specific panels in the More menu.
- Future generalized documentation-link helper adoption across other control panels.

## Related Packages
- **Depends on**: [20260325_disturbed_lookup_hardening](../20260325_disturbed_lookup_hardening/package.md)
- **Related**: [20251023_frontend_integration](../20251023_frontend_integration/package.md)
- **Follow-up**: Potential package for generalized mod-panel architecture in More-menu controls.

## Timeline Estimate
- **Expected duration**: 2-5 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm` - current disturbed controls to remove.
- `wepppy/weppcloud/controllers_js/disturbed.js` - current disturbed action wiring and status feedback events.
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` - lookup variant resolution and disturbed task routes.
- `wepppy/weppcloud/templates/controls/edit_csv.htm` - lookup table editor entry contract.
- `tests/weppcloud/routes/test_disturbed_bp.py` - disturbed route behavior coverage.
- `docs/work-packages/20260330_disturbed_panel_modal/notes/disturbed_panel_ui_contract.md` - package-local UI contract draft.
- `docs/ui-docs/disturbed-panel-ui-contract.md` - canonical developer contract doc.

## Deliverables
- Completed ExecPlan under `prompts/completed/` with implementation milestones, validation gates, and closeout notes.
- New/updated run-page templates/controllers/routes implementing Disturbed modal behavior.
- New usersum-link Jinja utility and usage in disturbed controls.
- Updated route/UI tests.
- Final developer contract doc path confirmed and linked.

## Follow-up Work
- Evaluate extracting modal-section button stacks into reusable template partials once disturbed panel behavior stabilizes.
- Evaluate applying usersum-link helper to other control surfaces currently hardcoding external docs URLs.
