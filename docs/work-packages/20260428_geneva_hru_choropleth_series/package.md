# Geneva HRU Choropleth Series

**Status**: Closed (2026-04-29 17:32 UTC)
**Timezone**: UTC

## Overview
This series delivers an HRU-level choropleth map in the Geneva Interactive Summary when a user selects an event. The implementation uses deck.gl vector rendering and themed map controls aligned to gl-dashboard styling, while preserving watershed-only `peak_discharge` behavior.

Current Geneva runtime writes storm-level summaries and hydrograph artifacts, but does not persist per-event HRU measure tables for report queries. The series adds the missing data contract, query-engine access pattern, and report UI integration as separate work packages.

## Objectives
- Add a durable per-event HRU measure contract for Geneva mapable measures.
- Keep `peak_discharge` watershed-level only and explicitly out of the HRU choropleth measure set.
- Serve HRU map data through query-engine-compatible payloads and API call patterns.
- Implement a deck.gl vector map panel + controls in Geneva summary with gl-dashboard-like theming.
- Update Geneva specification and related contract docs in the same series.

## Scope

### Included
- Orchestrated multi-package plan for data contract, query-engine access, UI integration, and validation.
- Specification updates in `wepppy/nodb/mods/geneva/specification.md` and any impacted query/report contract docs.
- Query-engine-centered data retrieval for event/measure-specific HRU values.
- Deck.gl vector choropleth rendering and themeable controls in Geneva summary report UI.

### Explicitly Out of Scope
- Changing the scientific definition or computation of watershed-level `peak_discharge`.
- Replacing Geneva results/report architecture outside the HRU map feature scope.
- Non-Geneva map framework rewrites.

## Stakeholders
- **Primary**: Geneva feature maintainers and Geneva report users.
- **Reviewers**: NoDb Geneva maintainers, WEPPcloud report/controller maintainers, query-engine maintainers.
- **Security Reviewer**: Not required unless scope expands to new auth/token/file-upload surfaces.
- **Informed**: gl-dashboard/map maintainers and operators supporting Geneva runs.

## Success Criteria
- [x] Work-package orchestration board tracks all scoped packages with status and dependency flow.
- [x] Spec/contract package lands first and defines HRU measure scope + watershed-only `peak_discharge` policy.
- [x] Query-engine package exposes/validates HRU event-measure retrieval contract used by UI.
- [x] UI package ships deck.gl choropleth map + controls with gl-dashboard-like theme support.
- [x] Validation package closes tests/docs/review gates and publishes rollout notes.

## Dependencies

### Prerequisites
- Geneva summary report baseline package: [20260418_geneva_interactive_summary_report](../20260418_geneva_interactive_summary_report/package.md).
- Geneva storm-shape package contract context: [20260428_geneva_storm_shape_control](../20260428_geneva_storm_shape_control/package.md).

### Blocks
- This series blocks the HRU map enhancement request in Geneva Interactive Summary.

## Related Packages
- **Related**: [20260418_geneva_interactive_summary_report](../20260418_geneva_interactive_summary_report/package.md)
- **Related**: [20260428_geneva_storm_shape_control](../20260428_geneva_storm_shape_control/package.md)
- **Follow-up**: Optional post-release UX tuning package if user feedback requires control/layout adjustments.

## Timeline Estimate
- **Expected duration**: 4-7 focused sessions across four child packages.
- **Complexity**: High.
- **Risk level**: Medium-High (crosses data contracts, query surfaces, and report UI rendering).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Scope is read-oriented run data contracts and report visualization. No new privileged mutation surfaces are planned.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/mods/geneva/specification.md`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
- `wepppy/query_engine/README.md`
- `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`
- `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`
- `wepppy/weppcloud/static/js/gl-dashboard/colors.js`
- `wepppy/weppcloud/templates/reports/geneva/summary.htm`
- `wepppy/weppcloud/controllers_js/geneva_summary_report.js`

## Deliverables
- Series package docs: `package.md`, `tracker.md`, `orchestration_board.md`.
- Four child work-package directories with package/tracker scaffolding and execution prompts.
- `PROJECT_TRACKER.md` Done entry for the closed series.

## Follow-up Work
- Decide whether additional HRU measures beyond runoff-focused metrics should be included in map mode.
- Evaluate whether Geneva should reuse additional gl-dashboard legend components directly after first release.
