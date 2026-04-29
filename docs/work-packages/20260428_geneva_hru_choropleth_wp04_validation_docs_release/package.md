# Geneva HRU Choropleth WP04 - Validation, Docs Closure, and Release Notes

**Status**: Open (2026-04-28)
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
- [ ] Required tests/lint/docs checks pass or blockers are explicitly documented.
- [ ] Spec/docs and runtime behavior are consistent.
- [ ] Series board and trackers reflect final status and evidence.
- [ ] Follow-up items are clearly scoped and linked.

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
