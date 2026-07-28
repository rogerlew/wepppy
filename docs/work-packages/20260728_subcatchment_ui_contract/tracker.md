# Tracker - DOM-07 Subcatchment UI Controller Contract

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 UTC
**Current phase**: Closed
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for test/documentation scope; re-triage any
production route, queue, or worker change.

## Done

- [x] Registered and traced DOM-07 from rendered options to the worker chain.
- [x] Added WBT/MOFE actual-render, exact controller payload, and ordered
  build/abstraction child-job evidence.
- [x] Confirmed route coercion/update-before-enqueue and existing reload
  behavior conform; no production patch was needed.
- [x] Passed focused Python, frontend lint, focused Subcatchment Jest, full
  frontend tests, and documentation lint.

## Decisions Log

### 2026-07-28 UTC: Keep the contract at the direct seams

**Decision**: Test actual template names, the serialized controller payload,
route coercion, and the worker dependency edge without adding a shared registry
or a controller helper.

**Impact**: The regression covers the user-facing data path while preserving
the established controller, route, and queue implementations.

### 2026-07-28 UTC: Close without a production repair

**Decision**: Retain the direct regressions and make no production change.

**Impact**: Generated controller freshness, RQ graph validation, and
correctness/security review are N/A because production source and queue wiring
did not change.

## Verification Checklist

- [x] Actual-render WBT/MOFE identities and lifecycle targets pass.
- [x] Controller payload, route coercion/update, and worker ordering pass.
- [x] Frontend lint and full frontend suite pass.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] RQ graph validation is N/A: no queue wiring changed.
- [x] Production and security reviews are N/A: no production patch was made.
