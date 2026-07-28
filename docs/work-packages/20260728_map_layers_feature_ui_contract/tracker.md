# Tracker - Map Layers and Feature UI Contract

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 UTC
**Current phase**: Closed
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for current scope; re-triage any production route or
remote-resource change

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Registered DOM-04B as a bounded follow-up to closed DOM-04A.
- [x] Added actual-render layer-default and legend-host evidence.
- [x] Confirmed existing layer, SBS, scale, and feature-modal coverage conforms;
  no production patch was needed.
- [x] Passed focused Python, frontend lint, focused Map Jest, full frontend
  tests, and documentation lint.

## Decisions Log

### 2026-07-28 UTC: Test rendered layer state, not remote resources

**Decision**: Lock the actual template control identities/default state and
reuse focused helper tests for interactive presentation.

**Impact**: The package covers the user-visible Map helper contract without
expanding into public routes, external data, or a shared test framework.

### 2026-07-28 UTC: Close without a production repair

**Decision**: Retain the actual-render regression and make no production change.

**Impact**: Controller generation, RQ graph validation, and production/security
review are not applicable. The full Python suite was not rerun because DOM-04A
already recorded the unrelated GridMET fake-units failure; DOM-04B's focused
Python test passes.

## Verification Checklist

- [x] Actual-render layer defaults and legend hosts pass.
- [x] Layer ordering, SBS presentation, scale, and feature-modal Jest tests pass.
- [x] Frontend lint and full frontend suite pass.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] RQ graph validation is N/A: no queue wiring changed.
- [x] Production and security reviews are N/A: no production patch was made.
