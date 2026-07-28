# Tracker - WATAR/Ash Controller Contract Tests

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-28 06:50 UTC
**Current phase**: Planned
**Last updated**: 2026-07-28 UTC
**Next milestone**: Start actual-render and field-contract tests after GOV-00A
publishes the concise test convention.
**Security impact**: `none` for current test/documentation scope
**Dedicated security review**: `no`; re-triage any production patch
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Freeze the concise intended field matrix.
- [ ] Render the actual WATAR template and add field identity/state assertions.
- [ ] Add focused serialization, parser, persistence, and reload tests.
- [ ] Reproduce the historical mismatch.
- [ ] Patch only confirmed mismatches.
- [ ] Run focused and existing broad gates.
- [ ] Record helper value, runtime, mismatches, and false tooling failures.

### In Progress

- None. Planning does not start controller execution.

### Blocked

- [ ] Waiting only for GOV-00A's concise test convention; no shared package or
  enforcement gate blocks the controller.

### Done

- [x] Replaced the platform-first pilot with the one-controller test loop
  (2026-07-28 UTC).

## Decisions Log

### 2026-07-28 UTC: Tests and repairs are the product

**Decision**: Begin with direct actual-render and downstream assertions. Extract
test tooling only from repeated assertions. Do not build registry/enforcement
machinery before controller tests demonstrate a need.

**Impact**: DOM-01 can execute immediately after the concise GOV-00A convention
and cannot be delayed by six shared audits.

## Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Hand-authored DOM repeats the expected bug | High | Render the actual Jinja template |
| Broad patch changes unrelated behavior | High | One mismatch and minimal patch per test |
| Helper obscures what is asserted | Medium | Direct assertions first; extract after repetition |
| Test-only work inherits hypothetical security burden | Medium | Re-triage only an actual production patch |

## Verification Checklist

- [ ] Focused actual-render and JavaScript tests pass.
- [ ] Focused route/NoDb/RQ tests pass where applicable.
- [ ] `wctl run-npm lint` and `wctl run-npm test` pass after JavaScript changes.
- [ ] Applicable Python suites pass after backend changes.
- [ ] Generated controller freshness passes after source changes.
- [ ] One independent correctness review closes any production patch.
