# Geneva Interactive Summary Report (Retroactive)

**Status**: Closed (2026-04-18)
**Timezone**: UTC

## Overview
This retroactive package records the completed Geneva summary report implementation that moved `/query/geneva/summary` and `/report/geneva/summary` from scaffold output to a fully interactive, contract-driven report. The change aligned Geneva with canonical Pure report-shell patterns and the single-storm analyzer interaction model.

## Objectives
- Ship a non-scaffold Geneva summary query/report payload contract with filter options, chart series metadata, row-level event status, and selected-storm synchronization.
- Deliver a report UI that is interactive end-to-end (filter-driven query refresh, marker-to-row selection/focus linkage) and themed with canonical Pure classes/tokens.
- Add or update regression tests for payload shape, report embedding contract, Pure control render expectations, and client interaction semantics.
- Close code/QA/security review findings found during implementation.

## Scope
This package covers the completed Geneva interactive summary report flow and immediate hardening fixes.

### Included
- Query payload contract implementation for `/query/geneva/summary`.
- Report rendering contract for `/report/geneva/summary` including single embedded JSON payload node.
- Geneva report client/controller implementation and style assets.
- Marker-click/keyboard interaction linking chart and event table selection/focus.
- Event table presentation contract: unavailable events are hidden, status is omitted from the table, numeric/report-value columns are sortable, and marker selection centers the focused row in view.
- Route/template shell-context hardening for `_base_report.htm` dependencies (`ron`, `current_ron`, `unitizer_nodb`, `precisions`).
- Security/QA hardening items: no-store headers, message sanitization, stale-summary suppression.
- Regression test updates in Geneva route/unit and JS suites.

### Explicitly Out of Scope
- New Geneva runoff model behavior beyond summary-report query/report contracts.
- Broader report-shell refactors outside Geneva routes.
- Environment/bootstrap dependency fixes (for example, local `rosetta` availability or compose service lifecycle).

## Stakeholders
- **Primary**: Geneva feature maintainers and WEPPcloud route/template maintainers.
- **Reviewers**: Route/UI maintainers, QA reviewers, security reviewer.
- **Security Reviewer**: Completed via subagent security review + disposition.
- **Informed**: Operators working with Geneva run outputs and report consumers.

## Success Criteria
- [x] `/query/geneva/summary` returns interactive payload content (not scaffold-only) with `schema_version`, `filters`, `filter_options`, chart metadata, selected storm, and event rows.
- [x] `/report/geneva/summary` embeds exactly one `geneva-summary-payload` JSON node and renders report controls/layout via Pure patterns.
- [x] Report JS supports datasource/ARI/measure filtering and marker→table selection/focus synchronization.
- [x] Event table hides unavailable events, omits the Status column, supports sortable headers, and keeps selected rows visibly centered after chart-marker selection.
- [x] Review findings are dispositioned with code/test updates or explicit rationale.
- [x] Required JS gates run cleanly (`wctl run-npm lint`, `wctl run-npm test`, controller bundle rebuild).
- [ ] Full requested Python `wctl run-pytest` gates executed in compose container (blocked: `weppcloud` service not running in this environment).

## Dependencies

### Prerequisites
- Geneva specification contract sections in `wepppy/nodb/mods/geneva/specification.md`.
- UI style conventions in `docs/ui-docs/control-ui-styling/ui-style-guide.md` and `docs/ui-docs/report-ui-conventions.md`.
- Existing report-shell contract in `wepppy/weppcloud/templates/reports/_base_report.htm`.

### Blocks
- None.

## Related Packages
- **Related**: [20260323_roads_wepp_reports_regen](../20260323_roads_wepp_reports_regen/package.md) (Pure report patterns and report contract cleanup context).
- **Follow-up**: Optional operational package if full compose-backed Geneva test gates need environment stabilization automation.

## Timeline Estimate
- **Expected duration**: Retroactively documented as complete in a single implementation cycle.
- **Complexity**: Medium-High.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: No new auth surface or secret handling; changes were run-scoped report/query payload and UI behavior. Security-relevant hardening (message sanitization + no-store headers) was completed.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/mods/geneva/specification.md`
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
- `wepppy/weppcloud/templates/reports/geneva/summary.htm`
- `wepppy/weppcloud/controllers_js/geneva_summary_report.js`
- `wepppy/weppcloud/templates/reports/_base_report.htm`
- `docs/ui-docs/report-ui-conventions.md`
- `docs/dev-notes/weppcloud-base-report-shell.md`

## Deliverables
- Backend payload implementation/hardening:
  - `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
  - `wepppy/nodb/mods/geneva/collaborators/results_service.py`
  - `wepppy/nodb/mods/geneva/geneva.py`
- Route/template/report-shell updates:
  - `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
  - `wepppy/weppcloud/templates/reports/geneva/summary.htm`
  - `wepppy/weppcloud/static/css/geneva-summary-report.css`
  - `wepppy/weppcloud/controllers_js/geneva_summary_report.js`
- Tests:
  - `tests/nodb/mods/geneva/test_geneva_report_payload_service.py`
  - `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py`
  - `tests/weppcloud/routes/test_geneva_bp.py`
  - `tests/weppcloud/routes/test_geneva_wp08_routes.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
  - `wepppy/weppcloud/controllers_js/__tests__/geneva_summary_report.test.js`

## Follow-up Work
- Run full compose-backed Python Geneva route/test gates once the local `weppcloud` container is available.
- Evaluate adding targeted smoke coverage for report-shell context dependencies to catch missing `ron/unitizer` context earlier.

## Closure Notes
**Closed**: 2026-04-18

**Summary**: The Geneva summary experience is now an interactive report instead of scaffold output, with canonical Pure controls, chart/table linkage, contract-consistent query/report payloads, and hardened run-scoped rendering behavior. Retroactive defects surfaced during rollout (`ron`/`unitizer_nodb` missing report-shell context) were fixed and regression assertions were added.

**Lessons Learned**:
- `_base_report.htm` usage requires explicit route context discipline; missing shell dependencies fail late in template includes.
- Review-driven hardening improved correctness and safety (stale artifact suppression, payload sanitization, no-store headers) beyond the initial feature acceptance path.

**Archive Status**: Package closed on creation (retroactive completion record).
