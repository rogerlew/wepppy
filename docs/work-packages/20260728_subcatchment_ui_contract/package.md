# DOM-07 Subcatchment UI Controller Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-07
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if a production repair changes the authenticated
route, queue, or worker; current audit scope is tests and documentation only

## Purpose

Audit Subcatchment build options from their rendered identities through the GL
payload, authenticated route parsing, build/abstraction queue chain, and
subcatchment reload.

## Scope

The audit covers `subcatchments_pure.htm`, `subcatchments_gl.js`, the RQ-engine
build route, and `build_subcatchments_and_abstract_watershed_rq`. It verifies
WBT sentinels, MOFE option identities, serialized payload preservation, route
coercion/update-before-enqueue, and ordered worker children.

Hydrology algorithms, map/layer behavior, authorization, CSRF policy, and queue
wiring are excluded unless a focused test proves a production mismatch.

## Acceptance

- Actual rendering proves WBT/MOFE field names and build lifecycle targets.
- Controller, route, and worker tests prove values reach the existing ordered
  build/abstraction chain.
- A repair, if needed, is minimal and reviewed at the changed risk boundary.

## Outcome

The audit added direct template, exact payload, and ordered-worker-chain
regressions. Existing route coercion/update and subcatchment reload coverage
conformed. No production source changed.
