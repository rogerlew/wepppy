# Tracker - Stevens Canyon Hillslope Water-Balance Attribution

**Started:** 2026-08-03
**Current phase:** Existing-output visualization
**Security impact:** none

## In Progress

- [x] Produced and visually validated paired water-flux figures for H49-H61.
- [ ] Synthesize cross-hillslope mechanism patterns from the existing outputs.
- [x] Traced the active Penman-Monteith soil-evaporation dynamics and management
  parameter pathway.
- [x] Specified joint annual `Es`, `Ep`, and total-ET diagnostic calibration
  targets by burn severity.
- [x] Run and integrate the additive canonical high-severity forest scenario for
  H50-H56 and H58-H61, retaining H49/H57 as unchanged controls.

## To Do

- [ ] Quantify focal-event and antecedent-period component differences.
- [ ] Classify flashier-undisturbed events across the 100-year record.
- [ ] Relate hillslope mechanisms to reaches 169, 172, 173, and the outlet.
- [ ] Decide whether any additional hillslope-only runs are warranted.

## Decisions

- **2026-08-03** - Prioritize LAI/residue/soil-water instrumentation over broad
  parameter mutation. The source trace shows a structural dual-coefficient
  transfer from transpiration to soil evaporation as LAI declines.
- **2026-08-03** - Calibrate total-ET ratio and `Es/ET` jointly, deriving `Ep`
  by closure. A simple burned-to-undisturbed `Es` multiplier is unsafe while
  the undisturbed partition remains unvalidated.
- **2026-08-04** - Retain canonical `ksflag=0`, `ksatadj=1`, `ksatfac=100`, and
  `ksatrec=0.3`. The `wepp-forest` forest-specific conductivity calculation is
  activated by `ksatadj=1`; no study-local `ksflag` override is needed.
