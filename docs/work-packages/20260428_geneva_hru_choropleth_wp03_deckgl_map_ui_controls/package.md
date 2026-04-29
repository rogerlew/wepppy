# Geneva HRU Choropleth WP03 - Deck.gl Map UI and Themed Controls

**Status**: Done (2026-04-29 08:09 UTC)
**Timezone**: UTC

## Overview
WP03 adds the Geneva Interactive Summary map panel that renders event-selected HRU measures as a deck.gl vector choropleth. UI controls and styling should match gl-dashboard map semantics closely, including theme support and water-measure colormap behavior.

## Objectives
- Render HRU choropleth with deck.gl vector layers in Geneva summary report.
- Provide measure/event controls that support theming and match gl-dashboard look-and-feel.
- Use query-engine-style API calls for map data loading.
- Apply gl-dashboard water-measure colormap policy (`winter`).

## Scope

### Included
- Geneva summary template/controller updates for map container and controls.
- Deck.gl layer integration for HRU vector features and measure coloring.
- Theme-aware control styling aligned with gl-dashboard conventions.
- UI tests for event selection, measure switching, legend updates, and error states.

### Explicitly Out of Scope
- New map frameworks or global map-shell redesign.
- Replacing existing Geneva charts/tables unrelated to map mode.
- HRU mapping for `peak_discharge`.

## Stakeholders
- **Primary**: Geneva summary report users and maintainers.
- **Reviewers**: WEPPcloud controllers/templates maintainers, gl-dashboard maintainers.
- **Security Reviewer**: Not required unless new token/auth surface is introduced.
- **Informed**: WP04 validation and release docs owners.

## Success Criteria
- [x] Deck.gl vector choropleth renders selected event HRU measure data.
- [x] Controls support theming and visually align with gl-dashboard conventions.
- [x] Water/runoff measures use `winter` colormap policy.
- [x] API calls follow query-engine pattern compatible with existing map data utilities.
- [x] JS tests cover selection flow and map rendering state transitions.

## Dependencies

### Prerequisites
- [WP01 Spec + Contracts](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md)
- [WP02 Query Engine Data API](../20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md)

### Blocks
- [WP04 Validation + Release Docs](../20260428_geneva_hru_choropleth_wp04_validation_docs_release/package.md)

## Related Packages
- **Depends on**: [WP01](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md), [WP02](../20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md)
- **Related**: [Series package](../20260428_geneva_hru_choropleth_series/package.md)
- **Follow-up**: WP04 closure package

## Timeline Estimate
- **Expected duration**: 2-3 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: UI/report rendering work on existing run-scoped data surfaces.
- **Security review artifact**: `N/A`

## References
- `wepppy/weppcloud/templates/reports/geneva/summary.htm`
- `wepppy/weppcloud/controllers_js/geneva_summary_report.js`
- `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`
- `wepppy/weppcloud/static/js/gl-dashboard/colors.js`
- `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`
