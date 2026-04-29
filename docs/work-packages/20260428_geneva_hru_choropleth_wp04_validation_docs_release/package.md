# Geneva HRU Choropleth WP04 - Validation, Docs Closure, and Release Notes

**Status**: Done (2026-04-29 17:32 UTC)
**Timezone**: UTC

## Overview
WP04 closes the series by validating backend/query/UI behavior end-to-end, finalizing specification and package documentation, and recording release-readiness evidence and residual risks.

## Objectives
- Run and document required validation gates across touched modules.
- Confirm spec + implementation + report UI behavior alignment.
- Publish concise rollout and residual-risk notes.
- Close all package trackers and series orchestration board.

## Scope

### Included
- Targeted test execution and result capture.
- Documentation synchronization across spec and work-package artifacts.
- Final review of measure scope constraints (including watershed-only `peak_discharge`).
- Series closure notes and follow-up recommendations.

### Explicitly Out of Scope
- New feature implementation beyond defect fixes found during validation.
- Unrelated Geneva backlog items.

## Stakeholders
- **Primary**: Geneva maintainers and release operators.
- **Reviewers**: Backend/UI maintainers for Geneva and query-engine.
- **Security Reviewer**: Not required unless validation uncovers new attack surface.
- **Informed**: Series stakeholders and users relying on Geneva summary outputs.

## Success Criteria
- [x] Required tests/lint/docs checks pass or blockers are explicitly documented.
- [x] Spec/docs and runtime behavior are consistent.
- [x] Series board and trackers reflect final status and evidence.
- [x] Follow-up items are clearly scoped and linked.

## Closure Summary (2026-04-29 17:32 UTC)
- Executed the required WP04 validation suite and captured command evidence.
- Confirmed `peak_discharge` remains watershed-only and is rejected for HRU map rows (`unsupported_measure_scope`).
- Confirmed HRU map measure scope remains `runoff_depth|runoff_volume`.
- Confirmed HRU map availability/error contracts remain aligned with WP01-WP03 (`legacy_hru_event_measures_missing` and canonical unavailable envelopes).
- Dispositioned the known unrelated frontend lint baseline in `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js` as external to this series.

## Validation Evidence
- `wctl run-pytest tests/nodb/mods/geneva tests/query_engine tests/weppcloud/routes/test_geneva_bp.py --maxfail=1` -> pass (`202 passed`, `84 warnings`).
- `wctl run-npm lint` -> fail (external baseline): 4 pre-existing `jest/no-conditional-expect` errors in `landuse_map_inline.test.js`.
- `wctl run-npm test -- geneva_summary_report` -> pass (`1 passed`, `6 tests`).
- `wctl doc-lint --path docs/work-packages/20260428_geneva_hru_choropleth_series --path docs/work-packages/20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates --path docs/work-packages/20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api --path docs/work-packages/20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls --path docs/work-packages/20260428_geneva_hru_choropleth_wp04_validation_docs_release --path PROJECT_TRACKER.md` -> pass (`17 files validated, 0 errors, 0 warnings`).
- `git diff --check` -> pass.

## Preflight Notes
- WP01-WP03 dependencies are complete and WP04 is unblocked.
- Known baseline caveat before execution: `wctl run-npm lint` currently fails on unrelated pre-existing lint issues in `wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`; WP04 must either document this as an external blocker or close it in-scope.

## Dependencies

### Prerequisites
- [WP01](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md)
- [WP02](../20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md)
- [WP03](../20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls/package.md)

### Blocks
- Series closure.

## Related Packages
- **Depends on**: WP01, WP02, WP03
- **Related**: [Series package](../20260428_geneva_hru_choropleth_series/package.md)
- **Follow-up**: optional post-release tuning package if needed

## Timeline Estimate
- **Expected duration**: 1 focused session.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Validation/documentation closure package.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/20260428_geneva_hru_choropleth_series/orchestration_board.md`
- `wepppy/nodb/mods/geneva/specification.md`
- `PROJECT_TRACKER.md`
