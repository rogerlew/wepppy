# Map Orchestration Controller Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-04A
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `none` for the current test/documentation scope; re-triage
if a production patch changes a public query route

## Purpose

Audit the Map controller's orchestration path from the rendered search and map
host controls through coordinate navigation, ID lookup, elevation requests, and
drilldown display. A user must be able to navigate to a coordinate, search a
TOPAZ or WEPP identifier, see the resulting drilldown, and inspect elevation
without a template/controller/request mismatch.

## Scope

The audit covers `map_pure_gl.htm`, the map host in `runs0_pure.htm`,
`map_gl.js`, the elevation microservice contract, and existing report drilldown
routes. It covers actual rendered action identities, coordinate input, exact
run-scoped elevation payloads, and search/drilldown URLs.

Map layer controls, scales, legends, remote layer resources, and feature modal
presentation are DOM-04B. This package does not change defaults, map state
persistence, authorization, public routes, RQ wiring, or shared helpers unless
a focused regression proves a conformance mismatch.

## Acceptance

- Actual-render evidence proves the map host, search input, action hooks,
  drilldown target, and elevation status target.
- Focused controller evidence proves coordinate navigation, TOPAZ/WEPP search,
  run-scoped elevation request payload, and report drilldown URLs.
- Existing elevation-service and report-route tests cover the applicable
  downstream response boundaries.
- Any production repair is minimal, backward-compatible, and re-triaged for
  route security before it is made.

## Decision

The operator authorized DOM-04A on 2026-07-28. The package uses direct tests
and a concise field matrix; it creates no registry, manifest, shared helper, or
new enforcement mechanism.

## Preliminary outcome

The audit added one actual-render regression for the production map actions and
one exact elevation request assertion. Existing coordinate, ID search,
drilldown, elevation-service, and report-route coverage already conformed. No
production source changed; DOM-04B remains the owner of layer and feature UI.
The full Python suite reached an unrelated GridMET fake-units failure after
2,451 passes. Its exact result is recorded in the tracker; it does not alter
the scoped Map evidence.
