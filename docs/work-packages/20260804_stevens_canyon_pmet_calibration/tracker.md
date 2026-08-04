# Tracker - Stevens Canyon PMET Fire-Severity Calibration

**Started:** 2026-08-04
**Current phase:** Complete
**Security impact:** none

## In Progress

- [x] Built an isolated, reproducible `kcb`/`rawp` calibration runner.
- [x] Executed low-, moderate-, and high-severity grids over 100 climate years.
- [x] Ranked candidates against joint `Es/ET`, ET-ratio, and magnitude targets.
- [x] Produced figures with Markdown sidecars and documented identifiability.
- [x] Preserved production inputs and verified the WEPP source tree remains clean.

## Decisions

- **2026-08-04** - Calibrate only PMET `kcb` and `rawp`; keep management, soil,
  climate, and model source fixed. Runoff is excluded from the objective.
- **2026-08-04** - Treat inability to reach the joint targets as a valid
  negative result establishing that PMET coefficients alone are insufficient.

## Outcome

- Low severity is marginal at `kcb=0.35`, `rawp=0.80`, with only 4% of years
  jointly passing.
- Moderate and high severity have no defensible joint solution in the grid.
- `rawp` is weakly identifiable from annual ET components; all best candidates
  lie on the lower `kcb` boundary.
- No production defaults changed. A partition-control study is the required
  successor.
