# Outlet UI Controller Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-06
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if a production repair changes the authenticated
route, queue, or worker; current audit scope is tests and documentation only

## Purpose

Audit outlet selection from rendered cursor/manual controls through the
authenticated request, RQ worker mutation, and reload display. A user must be
able to choose either mode, submit valid coordinates, receive a job, and see
the persisted outlet after completion.

## Scope

The audit covers `set_outlet_pure.htm`, `outlet_gl.js`, the RQ-engine
`set-outlet` route, `set_outlet_rq`, and existing outlet query/display behavior.
It verifies field identities/default state, cursor and manual-entry payloads,
route validation/enqueue, worker mutation, and reload.

Outlet geometry algorithms, channel rebuilding, authorization policy, CSRF
policy, queue wiring, and map orchestration are excluded unless a focused test
proves a production mismatch.

## Acceptance

- Actual-render evidence proves mode field identities, defaults, action hooks,
  status/stacktrace/job-hint targets, and manual-entry field semantics.
- Focused controller and route/RQ tests prove canonical coordinates reach the
  existing worker and persisted reload path.
- Any production repair is minimal, backward-compatible, and receives
  correctness/security review proportional to its changed boundary.

## Decision

The operator authorized DOM-06 on 2026-07-28. Direct tests are sufficient;
this package introduces no registry, manifest, helper, or new enforcement tool.

## Outcome

The audit added actual-render mode/lifecycle evidence and an exact manual-entry
payload regression. Existing cursor, route validation/enqueue, worker mutation,
and reload coverage conformed. No production source changed.
