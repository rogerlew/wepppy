# DOM-08A Landuse Build UI Controller Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-08A
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if a production repair changes authenticated upload,
route, queue, or worker behavior; current audit scope is tests and documentation
only

## Purpose

Audit Landuse build controls from rendered mode, mapping, upload, and disturbance
fields through multipart controller submission, RQ-engine parsing, persisted
Landuse/Disturbed updates, build RQ, and completion reload.

## Scope

The audit covers `landuse_pure.htm`, `landuse.js`, the RQ-engine build/mode
routes, `Landuse`, `Disturbed`, and `build_landuse_rq`. It verifies upload-mode
identities, multipart serialization, MOFE and disturbance normalization, queue
submission, worker mutation, and report reload.

Landuse catalog/editor/map behavior belongs to DOM-08B. Landuse modification,
authorization/CSRF policy, mapping algorithms, and queue wiring are excluded
unless a focused test proves a production mismatch.

## Acceptance

- Actual rendering proves risk-bearing mode-4 upload/mapping/disturbance field
  identities and build lifecycle targets.
- Controller, route, persistence, worker, and reload tests prove the existing
  build contract across multipart transport.
- A repair, if needed, is minimal and reviewed at the changed risk boundary.

## Outcome

The audit added actual upload-mode rendering, exact browser multipart payload,
and multipart route-normalization regressions. Existing mode validation, upload
validation, grouped update, worker cache/timestamp, and completion reload tests
conformed. No production source changed.
