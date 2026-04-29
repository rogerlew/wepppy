# Geneva HRU Choropleth WP01 - Spec and Contract Updates

**Status**: Closed (2026-04-29)
**Timezone**: UTC

## Overview
WP01 defines the authoritative Geneva contract for adding HRU-level event-map measures while preserving watershed-level `peak_discharge`. This package updates specifications first so downstream data/UI work builds on a stable, documented contract.

## Objectives
- Define a measure-scope matrix separating watershed-only metrics from HRU-mapable metrics.
- Keep `peak_discharge` explicitly watershed-level.
- Define per-event HRU measure artifact/query/report contract additions.
- Document backward compatibility and stale-artifact handling requirements.

## Scope

### Included
- `wepppy/nodb/mods/geneva/specification.md` updates for HRU map contract.
- Any required query/report contract doc updates under Geneva docs.
- Canonical identifiers/units for HRU map measures and event identifiers.
- Explicit join-key contract between HRU measure rows and vector geometry.

### Explicitly Out of Scope
- Runtime implementation of new artifacts.
- Query-engine route/execution coding.
- Deck.gl UI implementation.

## Stakeholders
- **Primary**: Geneva maintainers.
- **Reviewers**: Geneva query/report maintainers, query-engine maintainers.
- **Security Reviewer**: Not required for documentation-only contract package.
- **Informed**: WP02/WP03 implementers.

## Success Criteria
- [x] Spec clearly defines watershed-only vs HRU-map measure scope.
- [x] `peak_discharge` is documented as watershed-only with rationale.
- [x] HRU event-measure schema fields/units/keys are fully specified.
- [x] Backward-compatibility policy is documented for older runs lacking HRU measure artifacts.
- [x] WP02/WP03 can implement without unresolved contract ambiguity.

## Dependencies

### Prerequisites
- None.

### Blocks
- WP02 query-engine package.
- WP03 deck.gl UI package.
- WP04 validation closure package.

## Related Packages
- **Depends on**: None.
- **Related**: [Series package](../20260428_geneva_hru_choropleth_series/package.md)
- **Follow-up**: [WP02 Query Engine](../20260428_geneva_hru_choropleth_wp02_query_engine_hru_data_api/package.md)

## Timeline Estimate
- **Expected duration**: 1 focused session.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Documentation/contract-only scope.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/mods/geneva/specification.md`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
- `wepppy/nodb/mods/geneva/schemas/query_schema.py`

## Deliverables
- Geneva specification section `12.4` defining HRU choropleth measure scope, keys/joins, additive artifact schema, and legacy compatibility behavior.
- Geneva artifact catalog section updated with the WP02 additive artifact reference.
- WP01 tracker and series orchestration tracker/board synchronized to completed state.

## Closure Notes

**Closed**: 2026-04-29

**Summary**: WP01 was completed as documentation/contracts-only work. The Geneva specification now separates watershed summary measures from HRU-mapable measures, explicitly keeps `peak_discharge` watershed-only, defines canonical `storm_id`/`hru_id`/`hru_value` join behavior, and establishes the additive `hru_event_measure_rows.parquet` contract for WP02.

**Lessons Learned**: Capturing legacy-run compatibility (`legacy_hru_event_measures_missing`) and explicit scope-validation behavior (`unsupported_measure_scope`) at the spec stage removed key ambiguities that would otherwise have leaked into WP02/WP03 implementation.
