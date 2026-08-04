# Tracker - Stevens Canyon Legacy-ET Burn Matrix

**Started:** 2026-08-04
**Current phase:** Complete
**Security impact:** none

## In Progress

- [x] Fixed the paired legacy-ET experiment and target contract.
- [x] Executed 33 isolated 100-year hillslope simulations.
- [x] Aggregated and compared annual ET components against the burn matrix.
- [x] Produced a figure with a same-stem Markdown sidecar.
- [x] Documented the result and verified cleanup.

## Decisions

- **2026-08-04** - Remove `pmetpara.txt` from both the burned treatment and
  undisturbed reference lanes so the severity ratios do not mix ET methods.
- **2026-08-04** - Preserve `wepp_ui.txt` and all other required sidecars; the
  experiment changes only ET model selection.
- **2026-08-04** - Exclude runoff from scoring. This package asks whether the
  legacy routine improves annual `Es`, `Ep`, and total ET behavior.

## Outcome

- No severity had a year inside both target envelopes.
- Median ET ratios were 0.990, 0.997, and 0.862 for low, moderate, and high
  severity; total ET therefore remained too high.
- Undisturbed legacy ET was entirely `Ep`, with zero `Es` and `Er`, while fire
  primarily redistributed the same demand among components.
- Disabling PMET is rejected as a production workaround. Temporary run lanes
  were removed and the WEPP source checkout remained clean.
