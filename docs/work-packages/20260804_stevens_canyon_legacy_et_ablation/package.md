# Stevens Canyon Legacy-ET Burn Matrix

**Status:** Closed 2026-08-04
**Started:** 2026-08-04
**Security impact:** none

## Purpose

Test whether WEPP's legacy evapotranspiration routine produces a more credible
post-fire annual partition than the active Penman-Monteith implementation for
the Stevens Canyon low-, moderate-, and high-severity hillslopes.

## Scope

Run paired, hillslope-only, 100-year simulations with `pmetpara.txt` absent for
both burned and undisturbed inputs. Preserve the production-derived management,
soil, slope, climate, `wepp_ui.txt`, and other runtime sidecars. Score annual
`Es/ET`, total ET relative to paired undisturbed ET, and absolute `Ep`, `Es`,
`Er`, and ET. Runoff is explicitly outside the objective.

## Acceptance

The package closes when all 33 hillslope simulations produce finite 36,525-row
water-balance files, compact annual and summary artifacts are reproducible,
the burn matrix is compared with the existing target envelopes and PMET
baseline, every figure has a Markdown sidecar, temporary lanes are removed,
and the WEPP source checkout remains clean.

## Outcome

All 33 runs passed. No severity produced a paired year inside both target
envelopes. Legacy low- and moderate-severity total ET remained approximately
equal to undisturbed ET; high-severity ET remained too high. The routine also
assigned all undisturbed forest ET to `Ep`, with zero `Es` and `Er`. Disabling
PMET is therefore rejected as a production workaround. No source, production
input, or parameter default changed.
