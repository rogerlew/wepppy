# Tracker – GridMET Download Client Hardening

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-31
**Current phase**: Closed
**Last updated**: 2026-08-31 18:43 UTC
**Next milestone**: stateless recurrence response only
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-08-31_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Captured production failure evidence and scoped package (2026-08-31).
- [x] Recorded retry/concurrency decision in ADR-0028 (2026-08-31).
- [x] Implemented shared acquisition, validation, and atomic publication
  contracts (2026-08-31).
- [x] Added hermetic client and fan-out regressions; 37 focused tests pass
  (2026-08-31).
- [x] Correctness, QA, and security reviews passed with no open Critical, High,
  or Medium findings (2026-08-31).
- [x] Forest1 live current-prefix grid gate passed (2026-08-31).
- [x] Full repository suite passed: 7,306 passed, 63 skipped (2026-08-31).

## Decisions Log

### 2026-08-31: Validate before publication

**Context**: HTTP success and byte arrival do not establish that a response is
the requested GridMET product.

**Decision**: Validate single-location JSON schema and gridded NetCDF structure.
Write grids to a same-directory temporary file and use `os.replace` only after
validation.

**Impact**: Failed attempts cannot create or overwrite a final `.nc` artifact.

### 2026-08-31: Keep acquisition strategies separate

**Context**: Single-location requests use an aggregated JSON service; watershed
builds already request spatial grids from THREDDS NCSS.

**Decision**: Harden both existing strategies without replacing either or
adding a cache/aggregated-grid redesign.

**Impact**: Scientific output and caller APIs remain compatible; architecture
research remains a separate package.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Retry amplifies upstream load | High | Medium | bounded attempts, backoff, concurrency ceiling | Mitigated |
| Existing good grid overwritten | High | Medium | validate temporary file before atomic replace | Closed |
| Error logging leaks upstream content | Medium | Low | status/type summaries only | Closed |
| Scientific output changes | High | Low | preserve variables/units/interpolation and assert valid-path parity | Closed |
| Slow-trickle response occupies worker | Low | Low | byte, attempt, concurrency, and idle-timeout bounds | Accepted |

## Hardening Signal Log

- **Baseline**: 36/376 final files were HTML; two retries failed on different
  artifacts.
- **Post-change**: 37 focused tests pass; a local live point request returned the
  exact requested three-day axis; Forest1 received HTTP 200 classic NetCDF3
  with shape `(241, 4, 4)` for the current-year prefix.
- **Danger signals**: malformed final `.nc`, point date gaps/duplicates, repeated
  retry exhaustion, or materially increased GridMET build duration.
- **Recurrence trigger**: any HTML/non-NetCDF final artifact or matching unknown
  format failure opens a new incident/package citing this work.

## Verification Checklist

- [x] Focused client tests pass (25 tests).
- [x] NoDb GridMET service tests pass (12 tests).
- [x] Full repository suite passes (7,306 passed, 63 skipped).
- [x] Broad-exception check passes.
- [x] Documentation lint passes.
- [x] Correctness, QA, and security review gates pass.
- [x] Forest1 valid-response integration gate passes.

## Progress Notes

### 2026-08-31: Package scaffolded

**Agent/Contributor**: Codex

**Work completed**: captured production evidence, froze scope, and recorded the
client and parameterization contracts.

**Next steps**: implement tests and clients, then execute validation and review.

### 2026-08-31: Implementation and independent gates complete

**Agent/Contributor**: Codex with independent correctness, QA, and security
reviewers

**Work completed**: hardened both clients, reduced gridded concurrency to four,
closed realistic tail-truncation and partial-date findings, passed 37 focused
tests, and validated live point and Forest1 grid responses.

**Next steps**: finish the full repository suite and record closeout.

### 2026-08-31: Package closed

**Agent/Contributor**: Codex

**Work completed**: full repository gate passed (7,306 passed, 63 skipped in
12m54s); all package criteria and independent gates are satisfied.

**Next steps**: no scheduled follow-up. A matching danger signal opens a new
incident/package citing this immutable record.
