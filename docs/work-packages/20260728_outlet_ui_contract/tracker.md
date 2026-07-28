# Tracker - Outlet UI Controller Contract

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 UTC
**Current phase**: Closed
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for current test/documentation scope; re-triage any
production route, queue, or worker change

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Registered DOM-06 as the next watershed controller audit.
- [x] Added actual-render mode/lifecycle and manual-entry payload evidence.
- [x] Confirmed cursor, route validation/enqueue, worker mutation, and reload
  behavior conforms; no production patch was needed.
- [x] Passed focused Python, frontend lint, focused Outlet Jest, full frontend
  tests, and documentation lint.

## Decisions Log

### 2026-07-28 UTC: Cover both selection modes without changing queue behavior

**Decision**: Test template state plus cursor and manual coordinate submission,
then reuse the existing authenticated route and RQ mutation tests.

**Impact**: The audit proves both user inputs cross the established boundary
without duplicating queue or algorithm implementation work.

### 2026-07-28 UTC: Close without a production repair

**Decision**: Retain the direct regressions and make no production change.

**Impact**: The scoped controller/route/worker contract conforms. Generated
controller freshness, RQ graph validation, and correctness/security review are
not applicable because production source and queue wiring did not change.

## Verification Checklist

- [x] Actual-render mode, manual-entry, and lifecycle targets pass.
- [x] Cursor and manual-entry controller payload tests pass.
- [x] Existing authenticated route validation/enqueue and worker mutation tests pass.
- [x] Frontend lint and full frontend suite pass.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] RQ graph validation is N/A: no queue wiring changed.
- [x] Production and security reviews are N/A: no production patch was made.
