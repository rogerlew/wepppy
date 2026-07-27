# Tracker - WEPP SOIL OFE Overflow and 260726 Release

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27
**Current phase**: Complete
**Last updated**: 2026-07-27
**Next milestone**: Production deployment

## Task Board

### Ready / Backlog

- [x] Commit and push all three repositories.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Confirmed `I2` overflow and 238 ordered OFEs in the incident file.
- [x] Scaffolded package, compatibility plan, tracker, and active ExecPlan.
- [x] Widened daily and hourly WEPP SOIL OFE fields to `I5`.
- [x] Added strict historical overflow reconstruction in WEPPpyo3.
- [x] Built and validated WEPP `wepp_260726` and Python 3.12 native releases.
- [x] Replayed 587 hillslopes and the six-year incident watershed from a copy.
- [x] Converted all 521,696 historical incident rows with exact OFEs 1-238.
- [x] Vendored byte-identical WEPP artifacts and passed WEPPpy consumer gates.

## Decisions

- **2026-07-27** - Widen WEPP output for future correctness and retain a strict
  parser recovery path because existing model output cannot be regenerated
  cheaply and has deterministic ordering.
- **2026-07-27** - Name the dated release `wepp_260726` as requested.

## Risks

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Reconstructed ID is wrong | High | Per-day contiguous invariant and incident boundary assertions | Closed |
| Fixed-width change shifts measurements | High | Generated-output token/value regression | Closed |
| Binary uses nonportable loader | High | Required ELF provenance gate | Closed |
| Three repositories diverge | High | Commit/hash matrix and remote verification | Closed |

## Verification Checklist

- [x] WEPP build and applicable repository gates pass.
- [x] Generated output contains numeric OFEs above 99.
- [x] WEPPpyo3 Rust and release tests pass.
- [x] Synced incident run converts successfully.
- [x] WEPPpy binary provenance and consumer gates pass.
- [x] Work-package documentation lint passes.
- [x] All repositories are pushed and clean.
