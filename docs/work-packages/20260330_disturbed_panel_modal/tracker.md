# Tracker - Disturbed Panel Modal and Landsoil Lookup UX Contract

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-30  
**Current phase**: Complete  
**Last updated**: 2026-03-31 (lookup persistence follow-up)  
**Next milestone**: Archived handoff.

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Scoped package and created scaffold (`package.md`, `tracker.md`, `prompts/active`, `notes`) (2026-03-30).
- [x] Documented current disturbed lookup preference behavior and base/extended override semantics (2026-03-30).
- [x] Drafted package-local Disturbed panel UI contract note for implementation alignment (2026-03-30).
- [x] Captured frozen requested layout block in UI contract note to avoid memory drift during implementation (2026-03-30).
- [x] Added dedicated Disturbed modal and More-menu wiring in run/report templates (2026-03-30).
- [x] Removed disturbed lookup actions/docs link from PowerUser panel (2026-03-30).
- [x] Added disturbed routes for deleting extended lookup and syncing base to extended (2026-03-30).
- [x] Added `usersum_doc_link` Jinja helper and adopted it in Disturbed Help section (2026-03-30).
- [x] Published canonical UI contract doc at `docs/ui-docs/disturbed-panel-ui-contract.md` and linked it from `docs/ui-docs/README.md` (2026-03-30).
- [x] Added/updated controller, route, and template tests; full pytest and npm test gates passed (2026-03-30).
- [x] Completed subagent code+QA review remediation for medium findings: POST-only mutating routes, run-scoped lookup radio persistence, `ModalManager` alignment in report header, and disturbed modal inclusion in legacy page container (2026-03-30).
- [x] Migrated lookup radio persistence from browser localStorage to Disturbed NoDb disk state via `tasks/set_lookup_variant` and updated route/controller/docs contract (2026-03-31).

## Timeline

- **2026-03-30** - Package created and initial scope captured.
- **2026-03-30** - Active ExecPlan drafted and package-local UI contract note authored.
- **2026-03-31** - Follow-up patch moved lookup variant persistence to Disturbed NoDb and updated UI contract docs/tests.

## Decisions Log

### 2026-03-30: Treat dedicated Disturbed modal as a first-class run-page control
**Context**: Disturbed lookup actions currently live inside Power User and are not grouped around explicit base/extended workflow state.

**Options considered**:
1. Keep disturbed controls in Power User and only add additional buttons.
2. Add a dedicated Disturbed modal and relocate all disturbed lookup controls.
3. Keep controls split between Power User and a small helper modal.

**Decision**: Choose option 2 and relocate disturbed lookup actions to a dedicated Disturbed modal.

**Impact**: Disturbed workflows become discoverable and isolated; Power User panel remains focused on general-purpose actions.

---

### 2026-03-30: Preserve explicit base/extended selection via route query contract
**Context**: Disturbed lookup already supports `lookup=base|extended` but defaults to extended when extended CSV exists.

**Options considered**:
1. Preserve implicit extended preference and expose no explicit selector.
2. Add explicit selector and explicit modify buttons for both tables.
3. Flip default globally to base regardless of extended file presence.

**Decision**: Choose option 2 while preserving existing backend query contract and adding UI controls that make selection explicit.

**Impact**: Users can choose table target deterministically without changing existing route contract assumptions.

---

### 2026-03-31: Persist active lookup variant in Disturbed NoDb (not localStorage)
**Context**: Local browser storage did not provide run-scoped disk persistence or server-authoritative continuity across clients/sessions.

**Options considered**:
1. Keep localStorage as authoritative state.
2. Persist lookup choice in Disturbed NoDb and expose explicit setter route.
3. Persist only in query strings per request with no stored state.

**Decision**: Choose option 2.

**Impact**: Active lookup selection now survives process/page/client boundaries as run-scoped NoDb state while preserving explicit `lookup=` query overrides.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Modal wiring regressions in run-page controls | Medium | Medium | Added focused template assertions for modal-open hooks and disturbed modal inclusion in legacy page container | Mitigated |
| Deleting extended table breaks legacy links/workflows | Medium | Medium | Keep route behavior deterministic and fallback to base via existing resolver tests | Open |
| Usersum helper contract drifts from existing URL patterns | Low | Medium | Reuse `url_for('usersum.view_markdown', ...)` patterns and add template wiring tests | Mitigated |
| Ambiguity over selector label (`Extended` vs `Disturbed`) | Low | Medium | Locked terminology in canonical UI contract doc and modal copy (`Extended`) | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud --maxfail=1`
- [x] `wctl run-npm lint`
- [x] `wctl run-npm test`

### Documentation
- [x] Disturbed panel contract doc updated and linked from package references.
- [x] `PROJECT_TRACKER.md` updated for package visibility.
- [x] `wctl doc-lint --path docs/work-packages/20260330_disturbed_panel_modal`

### Testing
- [x] Route tests for delete/sync and lookup variant behavior pass.
- [x] Template/controller tests verify control relocation from Power User to Disturbed modal.
- [x] Automated run-page coverage in full `tests --maxfail=1` gate passed after changes.
- [x] Route tests confirm GET requests are rejected for disturbed lookup mutation endpoints (405).
- [x] Controller tests confirm lookup radio preference persists per run/config and refresh queries include selected lookup variant.
- [x] Report template tests confirm Disturbed/PowerUser/Unitizer buttons use `data-modal-open` hooks and no legacy toggle helper.

## Progress Notes

### 2026-03-30: Package creation and contract capture
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold and initial package/tracker docs.
- Captured current disturbed lookup behavior baseline (extended preferred when file exists unless `lookup=base` requested).
- Drafted Disturbed panel UI contract note for implementation alignment.
- Added a literal "Requested Layout Snapshot (Frozen)" section with exact requested menu/modal/button/link layout text.
- Updated root `PROJECT_TRACKER.md` backlog with package entry.

**Blockers encountered**:
- No external blockers during package creation.

**Next steps**:
- Archive package as completed after docs lint and handoff.

**Test results**: Not run for package scaffolding-only session.

### 2026-03-30: Implementation and validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Implemented Disturbed modal (`controls/disturbed_modal.htm`) and menu wiring from run/report More menus.
- Removed Disturbed lookup lifecycle/actions and external docs link from PowerUser panel.
- Added disturbed endpoints for delete-extended and sync-base-to-extended lookup operations.
- Extended disturbed controller with delete/sync actions and lookup-variant selector synchronization via `lookup_meta`.
- Added Jinja helper `usersum_doc_link(...)` with `📄` prefix and used it in Disturbed modal Help.
- Published canonical contract doc at `docs/ui-docs/disturbed-panel-ui-contract.md` and linked in `docs/ui-docs/README.md`.
- Updated/added tests:
  - `tests/weppcloud/routes/test_disturbed_bp.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
  - `tests/weppcloud/test_jinja_filters.py`
  - `wepppy/weppcloud/controllers_js/__tests__/disturbed.test.js`

**Validation results**:
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass, 71 suites)
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/test_jinja_filters.py --maxfail=1` (pass, 65 tests)
- `wctl run-pytest tests --maxfail=1` (pass, 2858 passed / 35 skipped)
- `wctl doc-lint --path docs/work-packages/20260330_disturbed_panel_modal` (pass)
- `wctl doc-lint --path docs/ui-docs/disturbed-panel-ui-contract.md` (pass)
- `wctl doc-lint --path docs/ui-docs/README.md` (pass)
- `wctl doc-lint --path PROJECT_TRACKER.md` (pass)

### 2026-03-30: Review remediation and final closeout
**Agent/Contributor**: Codex + reviewer subagents

**Work completed**:
- Ran dedicated `reviewer` and `qa_reviewer` subagent passes and triaged medium findings.
- Restricted disturbed lookup mutators (`reset/load/delete/sync`) to `POST` only.
- Added lookup radio persistence in `disturbed.js` using per-run local storage and `lookup_meta?lookup=` reconciliation.
- Replaced legacy report modal toggle wiring with `data-modal-open` hooks and included Disturbed modal in legacy `_page_container.htm`.
- Extended route/controller/template tests to cover remediated findings.

**Validation results**:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (pass)
- `wctl run-npm test -- disturbed` (pass)

### 2026-03-31: NoDb lookup persistence follow-up
**Agent/Contributor**: Codex

**Work completed**:
- Added Disturbed NoDb `active_lookup_variant` persistence and `active_lookup_fn` resolver usage in disturbed lookup propagation path.
- Added disturbed route `POST /tasks/set_lookup_variant` and wired resolver defaults to Disturbed NoDb active selection.
- Updated disturbed controller JS to persist lookup radio changes via `tasks/set_lookup_variant` instead of localStorage.
- Updated route and controller tests for the new persistence contract.
- Updated canonical and package-local disturbed panel contract docs.

**Validation results**:
- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1` (pass)
- `wctl run-npm test -- disturbed -- disturbed lookup variant persistence` (pass)
- `wctl doc-lint --path docs/work-packages/20260330_disturbed_panel_modal` (pass)
- `wctl doc-lint --path docs/ui-docs/disturbed-panel-ui-contract.md` (pass)

## Communication Log

### 2026-03-30: Disturbed modal scoping request
**Participants**: User, Codex  
**Question/Topic**: Create a dedicated Disturbed modal package, relocate controls from Power User, define explicit base/extended workflows, and define usersum-link utility direction.  
**Outcome**: New work package created with active ExecPlan and implementation-ready UI contract draft.
