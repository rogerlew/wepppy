# Tracker - Channel Delineation Controller Contract

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 UTC
**Current phase**: Closed
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for current test/documentation scope; re-triage any
production patch

## Task Board

### Ready / Backlog

- [x] Complete the concise field matrix.
- [x] Add actual-render and focused downstream evidence where missing.
- [x] Confirm no newly observed production mismatch requires a repair.
- [x] Run applicable frontend/backend gates and close.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Registered DOM-05 as the next one-controller audit after DOM-01
  (2026-07-28 UTC).
- [x] Closed DOM-05 with direct actual-template, legacy/GL payload, and RQ
  persistence-order evidence; no production source changed (2026-07-28 UTC).

## Decisions Log

### 2026-07-28 UTC: Reuse REM-05 evidence without reopening it

**Decision**: Treat the completed depression-smoothing remediation as one
covered DOM-05 field and test the remaining channel fields directly.

**Impact**: DOM-05 avoids duplicate repair work while preserving the regression
that exposed the production incident.

### 2026-07-28 UTC: Close without a production repair

**Decision**: Retain the expanded regression tests and make no production
change.

**Impact**: The observed template, both controller payloads, and existing RQ
mutation path conform for the scoped Channel fields. Generated-controller build,
RQ graph validation, and production review are not applicable.

## Verification Checklist

- [x] Actual-render identity and reload state evidence passes.
- [x] Legacy and GL request payload tests pass.
- [x] Applicable Watershed/RQ tests pass.
- [x] Frontend lint and tests pass after JavaScript test changes.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] Production patch reviews are N/A: no production patch was made.
