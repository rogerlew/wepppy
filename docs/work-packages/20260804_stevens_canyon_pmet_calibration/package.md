# Stevens Canyon PMET Fire-Severity Calibration

**Status:** Closed 2026-08-04
**Started:** 2026-08-04
**Security impact:** none

## Purpose

Determine whether physically plausible Penman-Monteith basal crop coefficient
(`kcb`) and readily available water fraction (`rawp`) values can approach the
post-fire annual soil-evaporation fraction and evapotranspiration magnitude
targets for low-, moderate-, and high-severity forest fire.

## Scope

Run a hillslope-only, 100-year grid calibration using the committed Stevens
Canyon fixtures and `wepp_260803_hill`. Score `Es/ET`, total ET relative to the
paired undisturbed hillslopes, and absolute annual `Es`, `Ep`, and ET. Exclude
runoff from candidate ranking. Do not modify WEPP source, production projects,
or production parameter defaults.

## Outcome

The 924-run grid found no interior `kcb`/`rawp` solution that jointly meets the
severity-specific annual ET and `Es/ET` targets. Low severity was marginally
close at `kcb=0.35`, `rawp=0.80`; moderate and high severity remained outside
the joint envelopes. `rawp` was weakly identifiable, and every best candidate
hit the lowest `kcb` boundary. PMET coefficients alone are insufficient; the
next calibration package must introduce and justify a control on the `Ep`/`Es`
partition. No production parameterization changed.

Key results are in
[pmet-calibration-results.md](../../investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/pmet-calibration-results.md).
