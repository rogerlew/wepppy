# DOM-13A AgFields Boundary/Schema UI Contract

**Status**: Closed 2026-07-28 UTC  
**Timezone**: UTC  
**Package ID**: DOM-13A  
**Parent**: `20260716_pure_ui_contract_standardization_c`  
**Security impact**: High in principle because the controller accepts geospatial
uploads; this package changes tests and documentation only.

## Purpose

Audit field-boundary upload, schema confirmation, and sub-field delineation
from the rendered AgFields control through browser requests, RQ-engine parsing,
persisted state, enqueue, and hydration.

## Outcome

The rendered control exposes the exact multipart field, schema keys, minimum
area input, actions, and lifecycle targets consumed by `ag_fields.js`. Existing
route tests prove extension/size rejection, atomic schema failure, preflight
invalidation, and the `agfields_build_subfields` enqueue key. No mismatch or
production patch was required.
