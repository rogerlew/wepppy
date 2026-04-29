# Geneva HRU Choropleth WP02 - Query Engine HRU Data API

**Status**: Completed (2026-04-29)
**Timezone**: UTC

## Overview
WP02 implements the data-access layer for Geneva HRU choropleth rendering using query-engine-style calls. It adds the event+measure-filtered HRU dataset contract needed by the map UI, including join-key integrity for vector geometry rendering.

## Objectives
- Persist or materialize HRU event-measure rows for mapable Geneva measures.
- Provide query-engine-compatible request/response patterns for Geneva map queries.
- Ensure join-key compatibility between HRU measure rows and vector polygons.
- Add targeted contract tests for event/measure query behavior.

## Scope

### Included
- Geneva artifact generation updates needed to expose HRU event-measure data.
- Query-engine dataset/activation/path contract updates for Geneva HRU map data.
- Query payload conventions matching gl-dashboard query-engine usage patterns.
- Backend tests for schema, filtering, and missing-data behavior.

### Explicitly Out of Scope
- UI deck.gl rendering and controls.
- Broader query-engine refactors unrelated to Geneva map queries.
- Adding HRU-level `peak_discharge`.

## Stakeholders
- **Primary**: Geneva backend maintainers.
- **Reviewers**: query-engine maintainers, Geneva route/query maintainers.
- **Security Reviewer**: likely not required unless new auth surface is added.
- **Informed**: WP03 UI implementers.

## Success Criteria
- [x] HRU event-measure dataset contract is implemented and queryable.
- [x] Query-engine request pattern for Geneva map mode is documented and tested.
- [x] Join-key mapping between metric rows and vector features is validated.
- [x] Mapable measure set excludes `peak_discharge`.
- [x] Tests cover happy path, missing event, missing measure, and legacy-no-artifact behavior.

## Dependencies

### Prerequisites
- [WP01 Spec + Contracts](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md)

### Blocks
- [WP03 Deck.gl UI + Controls](../20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls/package.md)
- [WP04 Validation + Release Docs](../20260428_geneva_hru_choropleth_wp04_validation_docs_release/package.md)

## Related Packages
- **Depends on**: [WP01](../20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates/package.md)
- **Related**: [Series package](../20260428_geneva_hru_choropleth_series/package.md)
- **Follow-up**: [WP03](../20260428_geneva_hru_choropleth_wp03_deckgl_map_ui_controls/package.md)

## Timeline Estimate
- **Expected duration**: 2-3 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no` (re-triage to `high` if auth surface changes)
- **Triage rationale**: Read-path data/query contract work inside existing run-scoped boundaries.
- **Security review artifact**: `N/A`

## References
- `wepppy/query_engine/README.md`
- `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
