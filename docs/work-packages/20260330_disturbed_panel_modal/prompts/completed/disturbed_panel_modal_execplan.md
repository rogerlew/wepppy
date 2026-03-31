# Disturbed Modal and Landsoil Lookup Workflow Refactor

> Outcome: Completed on 2026-03-30 with subagent review remediation for medium findings (POST-only mutators, lookup radio persistence, and modal lifecycle alignment).

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users currently find disturbed lookup actions inside the Power User panel, and extended-table preference is implicit once the extended CSV exists. This package will make disturbed workflows explicit through a dedicated Disturbed modal, clear base versus extended controls, and a documented route/UI contract so future contributors can maintain the behavior safely.

## Progress

- [x] (2026-03-30 00:00Z) Reviewed current disturbed lookup routing, editor, and Power User control surfaces.
- [x] (2026-03-30 00:00Z) Created package scaffold and baseline docs (`package.md`, `tracker.md`, this active ExecPlan, UI contract note).
- [x] Implement Disturbed modal entry and shell in run-page/report More menus, sized/styled consistently with Power User modal.
- [x] Move disturbed controls from Power User modal into Disturbed modal sections.
- [x] Add route(s) and controller wiring for deleting extended table and syncing base to extended.
- [x] Add explicit base/extended modify links and table-resource selection controls.
- [x] Add usersum-link Jinja helper that prefixes link text with documentation affordance glyph.
- [x] Publish canonical developer contract doc and cross-link from package/tracker/docs.
- [x] Update/extend tests for disturbed routes, run-page templates/controllers, and usersum-link helper.
- [x] Run validation gates and close package.
- [x] Resolve post-review medium findings (POST-only mutating disturbed routes, persisted lookup-radio selection, report modal wiring via `data-modal-open`, legacy page disturbed modal include).

## Surprises & Discoveries

- Observation: Disturbed route selection already honors explicit `lookup=base|extended` and defaults to extended only when no explicit query is provided and extended CSV exists.
  Evidence: `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py::_resolve_lookup_target` and tests in `tests/weppcloud/routes/test_disturbed_bp.py`.

- Observation: Resetting disturbed parameters only rewrites base lookup and does not remove extended lookup, which leaves implicit preference on extended when file exists.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py::reset_land_soil_lookup` and resolver behavior in disturbed blueprint.

- Observation: No general Jinja helper exists today for usersum documentation links with prefixed icon affordance.
  Evidence: Existing templates use direct `url_for('usersum.view_markdown', ...)` calls or hardcoded external docs URLs.

- Observation: Disturbed lookup radio state was local-only and would drift back to resolver defaults after metadata refreshes.
  Evidence: Prior `disturbed.js::refreshLookupVariantSelection` always requested `api/disturbed/lookup_meta` without explicit lookup query and overwrote selected state.

## Decision Log

- Decision: Keep the existing `lookup=base|extended` query contract as the canonical table-target selector rather than introducing a new query parameter family.
  Rationale: Existing routes and tests already enforce this contract; using it minimizes migration risk.
  Date/Author: 2026-03-30 / Codex.

- Decision: Relocate disturbed controls from Power User to a dedicated Disturbed modal rather than adding more Power User rows.
  Rationale: Disturbed actions now have enough lifecycle and resource-management complexity to justify a dedicated modal surface.
  Date/Author: 2026-03-30 / Codex.

- Decision: Persist lookup table radio preference per run/config in Disturbed NoDb (`disturbed.nodb`) and expose a dedicated setter route.
  Rationale: Server-authoritative, run-scoped disk persistence avoids client-local drift and makes active lookup selection available to downstream NoDb build paths.
  Date/Author: 2026-03-31 / Codex.

## Outcomes & Retrospective

- Disturbed workflow controls are now isolated in a dedicated Disturbed modal and removed from PowerUser.
- Disturbed lookup lifecycle now has explicit delete/sync operations in both API and controller wiring.
- Base vs extended table visibility is explicit in UI through selector radios and explicit modify links.
- Disturbed lookup mutating routes are POST-only (`reset`, `load`, `delete`, `sync`) and reject GET with 405.
- Lookup radio selection now persists per run/config in Disturbed NoDb and metadata refresh requests read server-authoritative state.
- Report-page Disturbed/PowerUser/Unitizer buttons now use `data-modal-open` modal hooks (no legacy manual toggle path).
- Usersum documentation links can now be generated consistently in templates via `usersum_doc_link(...)`.
- Canonical contract doc published at `docs/ui-docs/disturbed-panel-ui-contract.md` and linked from `docs/ui-docs/README.md`.
- Validation gates passed:
  - `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
  - `wctl run-npm test -- disturbed`

## Context and Orientation

Relevant runtime surfaces and current behavior:

- Disturbed route logic: `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
  - `load_extended_land_soil_lookup` builds extended CSV.
  - `modify_disturbed`, `lookup_meta`, `lookup_snapshot`, and `task_modify_disturbed` all resolve base/extended target through query args.
- Disturbed NoDb lookup files: `wepppy/nodb/mods/disturbed/disturbed.py`
  - Base: `disturbed_land_soil_lookup.csv`
  - Extended: `disturbed_land_soil_lookup_extended.csv`
- Current controls in Power User modal: `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
- Disturbed front-end action handlers: `wepppy/weppcloud/controllers_js/disturbed.js`
- Disturbed lookup editor template: `wepppy/weppcloud/templates/controls/edit_csv.htm`
- Existing disturbed route tests: `tests/weppcloud/routes/test_disturbed_bp.py`
- Usersum route and template contract: `wepppy/weppcloud/routes/usersum/usersum.py`, `wepppy/weppcloud/routes/usersum/AGENTS.md`

Target contract includes:

- More menu entry for Disturbed modal.
- Disturbed modal sections with requested actions.
- Explicit base and extended modify actions.
- Explicit delete-extended action to return implicit default selection to base.
- Usersum documentation link helper with prefixed documentation glyph.

## Plan of Work

Milestone 1 establishes the Disturbed modal skeleton and relocates existing disturbed controls out of Power User. The run page should still render with no broken control wiring, and existing reset/load actions should work from the new location.

Milestone 2 adds lifecycle operations that are currently missing from the API surface: deleting extended lookup and syncing base lookup to extended lookup. This milestone includes route-level tests to verify locking, lookup-target behavior, and fallback to base after delete.

Milestone 3 adds explicit table-target UX controls and links so users can open and edit base and extended tables without relying on implicit preference rules.

Milestone 4 introduces a reusable usersum-link helper in Jinja and applies it to the Disturbed modal help section. This milestone also removes the hardcoded external disturbed-doc link from Power User.

Milestone 5 publishes a canonical developer contract document (target path `docs/ui-docs/disturbed-panel-ui-contract.md`) and updates discoverability pointers from package docs and root tracker.

Milestone 6 closes with validation gates and package closeout updates.

## Concrete Steps

From repository root `/workdir/wepppy`:

1. Implement modal/template/controller/route changes.
2. Run targeted disturbed route tests:

    wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1

3. Run broader WEPPcloud route/template/controller tests:

    wctl run-pytest tests/weppcloud --maxfail=1

4. Run frontend checks for controller/template integration:

    wctl run-npm lint
    wctl run-npm test

5. Validate docs touched by this package:

    wctl doc-lint --path docs/work-packages/20260330_disturbed_panel_modal
    wctl doc-lint --path docs/ui-docs/disturbed-panel-ui-contract.md

6. Run pre-handoff sanity gate:

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance is complete when all of the following are true:

- More menu exposes Disturbed as its own modal action.
- Power User panel no longer renders disturbed lookup action controls.
- Disturbed modal includes requested sections and control actions.
- Users can open base and extended editors intentionally (`lookup=base` and `lookup=extended`).
- Delete-extended action removes extended CSV and subsequent default editor target resolves to base.
- Sync-base-to-extended action regenerates/updates extended from current base state.
- Help section uses usersum-link helper and renders prefixed documentation affordance glyph.
- Disturbed route tests and WEPPcloud targeted tests pass.

## Idempotence and Recovery

- Template/controller updates are additive and can be reapplied without data migration.
- Delete-extended is recoverable via existing load-extended action.
- Sync-base-to-extended is rerunnable; latest sync should overwrite extended deterministically.
- If a milestone fails validation, keep package/tracker progress entries synchronized and proceed with scoped rollback by file-level revert for the failed milestone only.

## Artifacts and Notes

- Active package tracker: `docs/work-packages/20260330_disturbed_panel_modal/tracker.md`
- UI contract draft note: `docs/work-packages/20260330_disturbed_panel_modal/notes/disturbed_panel_ui_contract.md`
- Planned canonical contract doc: `docs/ui-docs/disturbed-panel-ui-contract.md`

---
Revision Note (2026-03-30, Codex): Initial active ExecPlan authored during package creation.
Revision Note (2026-03-30, Codex): Updated after subagent code+QA review remediation and final closeout.
