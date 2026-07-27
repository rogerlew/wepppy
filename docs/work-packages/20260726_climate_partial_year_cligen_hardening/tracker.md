# Tracker - Partial-Year Climate and CLIGEN NAS Hardening

> Living incident tracker for partial-year restoration and station-copy
> synchronization.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27 03:20 UTC
**Current phase**: Closed
**Last updated**: 2026-07-27
**Next milestone**: Production deployment and 30-day observation
**Security impact**: `low`
**Dedicated security review**: `no`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Captured both wepp1 incident signatures and production artifacts
  (2026-07-27 03:20 UTC).
- [x] Ratified full-year restoration behavior with the maintainer and drafted
  ADR-0026 (2026-07-27 03:20 UTC).
- [x] Scaffolded package, tracker, compatibility plan, active ExecPlan, and root
  tracker entry (2026-07-27 03:20 UTC).
- [x] Implemented and documented partial-year restoration and atomic station
  staging for Daymet and GridMET multiple paths (2026-07-27).
- [x] Passed focused and NoDb validation; dispositioned one unrelated full-suite
  usersum baseline failure (2026-07-27).
- [x] Completed clean independent code and QA re-reviews after fixing all
  findings (2026-07-27).
- [x] Archived the ExecPlan and closed the package (2026-07-27).

## Timeline

- **2026-07-27 01:49 UTC** - Job `a4b65525-3f23-4cc5-a5da-6690df28ab37`
  failed on the first future `tdew` NaN.
- **2026-07-27 02:50 UTC** - Job `7e97f4f5-dec8-4fc1-83a9-86c7486e37cd`
  failed when CLIGEN read a partial shared station file.
- **2026-07-27 03:20 UTC** - Maintainer clarified that WEPP requires the full
  year and authorized CLIGEN restoration of unpublished future values.

## Decisions Log

### 2026-07-27: Preserve generated future values per variable

**Context**: Current-year products publish variables on different schedules.
Using a common cutoff would discard later valid temperature observations.

**Decision**: CLIGEN produces the full year. Each supplemental variable overlays
only its finite contiguous observed prefix. A trailing missing suffix is allowed;
an internal hole fails explicitly.

**Impact**: WEPP receives a complete year while every available observation is
retained independently.

### 2026-07-27: Stage the station file before pool creation

**Context**: Seven parallel CLIGEN processes observed EOF while workers raced to
copy the same NAS destination.

**Decision**: The parent atomically copies, flushes, finalizes, and validates the
station file before Daymet or GridMET worker pools are created. Worker
concurrency is not the synchronization mechanism.

**Impact**: Lower concurrency may mitigate NAS load, but correctness does not
depend on worker count.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Generated data overwrites an observation | High | Low | Per-variable finite-prefix tests | Closed |
| Internal source hole is mistaken for publication lag | High | Medium | Contiguous-prefix validator | Closed |
| Atomic rename durability differs on NAS | Medium | Low | Same-directory temp file, file fsync, size validation | Monitor |
| Excess CLIGEN parallelism saturates NAS | Medium | Medium | Measure and expose a bounded worker control only if needed | Monitor |

## Hardening Signal Log

- **Baseline**: 161 trailing `tdew` NaNs in topaz 12032; seven of 58 CLIGEN logs
  showed station-file EOF during the retry.
- **Post-change**: 53 focused tests and 1513 NoDb tests passed; production
  observation remains pending deployment.
- **Danger signals observed**: Existing zero preallocation hides publication
  lag for radiation and wind as well as dewpoint.
- **Temporary callus register**: None.

## Verification Checklist

- [x] Focused climate helper/service tests pass.
- [x] Full `tests/nodb` gate passes.
- [x] Full repository test gate passes or unrelated baseline is dispositioned.
- [x] Broad-exception changed-file gate passes.
- [x] Documentation lint passes.
- [x] Code review has no unresolved findings.
- [x] QA review has no unresolved findings.

## Handoffs

- No production deployment or retry is included in this package execution.
