# Stevens Canyon Contributor-Indexed `htcs` Ensemble

**Status:** Complete
**Started:** 2026-08-03
**Security impact:** none

## Purpose

Test whether physically derived, hillslope-specific lateral-flow times of
concentration can explain the undisturbed peak-flow inversion at simulation
year 34, Julian day 203, and whether that sensitivity is consistent across
comparable events.

## Scope

The study will relink the legacy text-pass-compatible watershed executable in
an isolated ablation directory, activate `htcs` using the actual contributing
hillslope index, and run deterministic low-, medium-, and high-variation
ensembles. Production projects and `/workdir/wepp-forest_260430_baseline` stay
read-only. Results will cover WEPP_IDs 169, 172, 173, and 193, include routed
volume checks, and be presented as figures with Markdown sidecars.

## Exit Criteria

The package closes only after an unmodified relink has baseline parity, the
experimental binary reads the staged text pass shards, the ensemble completes
with recorded seeds and parameters, selected channel volumes remain within the
documented tolerance, figures and sidecars are generated, and cleanup verifies
the baseline checkout is unchanged.

## Outcome

The paired 100-year experiment and 300-realization ensemble completed. Spatial
`htcs` variation changes upstream peaks but does not remove the inversion; the
outlet response is small. Sidecars document compact-fixture and rebuilt-control
limitations. Fortran review and scientific QA approved the accepted evidence,
and cleanup verified the baseline checkout.
