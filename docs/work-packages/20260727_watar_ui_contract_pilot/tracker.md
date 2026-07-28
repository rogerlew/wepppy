# Tracker - WATAR/Ash Controller Contract Tests

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 06:50 UTC
**Current phase**: Closed
**Last updated**: 2026-07-28 UTC
**Next milestone**: Select the next single controller from the parent register.
**Security impact**: `none` for current test/documentation scope
**Dedicated security review**: `no`; re-triage any production patch
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [x] Freeze the concise intended field matrix.
- [x] Render the actual WATAR template and add field identity/state assertions.
- [x] Add focused serialization, parser, persistence, and reload tests.
- [x] Reproduce the historical selector mismatch through retained regression coverage.
- [x] Confirm no production mismatch requires a patch.
- [x] Run existing broad gates.
- [x] Record helper value, runtime, mismatches, and false tooling failures.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Replaced the platform-first pilot with the one-controller test loop
  (2026-07-28 UTC).
- [x] GOV-00A published and independently reviewed the concise convention;
  no shared package or enforcement gate blocks execution (2026-07-28 10:20 UTC).
- [x] Established field matrix and focused actual-render, controller, route,
  persistence, and RQ evidence without finding a production mismatch
  (2026-07-28 10:30 UTC).
- [x] Closed DOM-01 after 111 affected Python tests, frontend lint, and 88
  frontend suites / 662 tests passed; no source patch, helper, or false tooling
  failure was introduced (2026-07-28 10:45 UTC).
- [x] Dispositioned DOM-01 review findings: both wind boolean states and both
  rendered reload states are covered; this DOM-01 revision marks the ledger
  `verified` (2026-07-28 UTC).

## Decisions Log

### 2026-07-28 UTC: Tests and repairs are the product

**Decision**: Begin with direct actual-render and downstream assertions. Extract
test tooling only from repeated assertions. Do not build registry/enforcement
machinery before controller tests demonstrate a need.

**Impact**: DOM-01 can execute immediately after the concise GOV-00A convention
and cannot be delayed by six shared audits.

### 2026-07-28 UTC: No repair without a mismatch

**Decision**: Close DOM-01 with regression tests and no production patch.

**Impact**: The historical selector mismatch remains protected by actual-render
and downstream tests. No correctness/security review or generated-controller
build was required because no production/controller source changed.

## Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Hand-authored DOM repeats the expected bug | High | Render the actual Jinja template |
| Broad patch changes unrelated behavior | High | One mismatch and minimal patch per test |
| Helper obscures what is asserted | Medium | Direct assertions first; extract after repetition |
| Test-only work inherits hypothetical security burden | Medium | Re-triage only an actual production patch |

## Verification Checklist

- [x] Focused actual-render and JavaScript tests pass.
- [x] Focused route/NoDb/RQ tests pass where applicable.
- [x] `wctl run-npm lint` and `wctl run-npm test` pass after JavaScript changes.
- [x] Applicable Python suites pass after backend changes.
- [x] Generated controller freshness is N/A: no controller source changed.
- [x] Independent correctness review is N/A: no production patch was made.
