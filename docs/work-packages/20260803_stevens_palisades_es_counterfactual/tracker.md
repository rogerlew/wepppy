# Tracker – Stevens–Palisades Peak Soil-Evaporation Counterfactual

## Quick Status

**Timezone:** UTC
**Started:** 2026-08-04 02:40 UTC
**Current phase:** Complete
**Last updated:** 2026-08-04 02:49 UTC
**Next milestone:** None; package closed
**Security impact:** none
**Dedicated security review:** no

## Task Board

### Done

- [x] Scoped a hillslope-only, no-production-mutation experiment (2026-08-04 02:40 UTC).
- [x] Confirmed the canonical binary and `wepp_ui.txt` sidecar path (2026-08-04 02:40 UTC).
- [x] Replayed 278 Palisades and parsed 13 Stevens hillslopes (2026-08-04 02:45 UTC).
- [x] Generated and interpreted exact synchronization bounds (2026-08-04 02:47 UTC).
- [x] Documented the negative eightfold reproduction result (2026-08-04 02:49 UTC).

## Decisions Log

### 2026-08-04 02:40 UTC: Separate measured bounds from causal inference

**Decision:** Report the synchronization counterfactual exactly from individual
hillslope series, but label climate/water and vegetation contrasts as empirical
counterfactual evidence unless controlled swaps identify them uniquely.

**Impact:** The package will not overstate observational conditioning as a
mechanistic intervention.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| Cross-site calendars differ | Medium | Certain | Compare distributions and normalized seasonal coordinates, not dates | Open |
| LAI and residue covary in management | Medium | High | Report their joint exposure effect unless independently intervened | Open |

## Verification Checklist

- [x] Smoke and full execution produced stable compact artifacts.
- [x] All WEPP rows are finite and calendar-complete.
- [x] Required sidecars match their source files.
- [x] Figure sidecars and package Markdown pass scoped lint.

## Progress Notes

### 2026-08-04 02:40 UTC: Package started

**Work completed:** Reviewed both prior studies and selected a non-mutating
hillslope design using the existing binary and fixtures.

**Next steps:** Implement, smoke-test, execute, interpret, and close.

### 2026-08-04 02:49 UTC: Execution complete

**Work completed:** Replayed all Palisades burned-PMET hillslopes, parsed all
Stevens burned hillslopes, computed exact synchronization bounds, generated a
visually inspected figure and sidecar, and linked the corrected magnitude into
both investigations.

**Test results:** Smoke passed; 278/278 Palisades and 13/13 Stevens outputs were
finite and calendar-complete. Observed peak ratio 1.2836; p99 ratio 1.0909.
