# DOM-09 Landuse Modifier UI Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-09
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if a production repair changes run authorization,
map selection, or Landuse mutation behavior; current scope is tests and
documentation only

## Purpose

Audit the map adjunct that selects subcatchments and assigns a replacement
landuse code from rendered fields through the browser request and persisted
Landuse mutation.

## Scope

The audit covers `modify_landuse.htm`, `landuse_modify_gl.js`, selection helper
interactions, and the RQ-engine `modify-landuse` route. Catalog/map editing is
DOM-08B; report-inline mapping edits are outside this subcatchment-selection
surface.

## Acceptance

Actual rendering proves selection, Topaz ID, landuse-code, submit, and lifecycle
identities. Browser tests prove map and exact native payload behavior. Route
tests prove authorization, strict input validation, and mutation.

## Outcome

The audit added actual-render coverage and confirmed the existing exact-payload,
map-selection, authorization, validation, and mutation tests. No mismatch or
production patch was found.
