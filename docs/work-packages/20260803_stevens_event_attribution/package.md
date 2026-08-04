# Stevens Canyon Focal-Event Attribution

**Status:** Closed (2026-08-04 UTC)
**Timezone:** UTC

## Overview

Attribute the exceptional year-34, Julian-day-203 Stevens Canyon inversion to
antecedent ET partitioning, surface-water availability, and event runoff
generation. The study uses paired burned/undisturbed hillslope replays and an
opt-in diagnostic binary built in a disposable `wepp-forest` worktree.

## Objectives

- Record the PMET demand, LAI partition, water-stress, residue-exposure, and
  realized-flux terms for the 30-day antecedent window.
- Quantify component-swap counterfactuals without changing production inputs.
- Relate antecedent fluxes and shallow storage to day-203 hillslope runoff.
- Cleanly remove the source worktree after retaining its patch and binary hash.

## Scope

Included are H49-H61 hillslope-only burned and undisturbed replays,
instrumentation gated by `wepp_observe.on`, and offline counterfactual
calculations. Watershed reruns, production parameter changes, and calibration
are excluded.

## Success Criteria

- [x] Diagnostic build has output parity when observation is disabled.
- [x] All paired hillslopes complete with required sidecars and finite traces.
- [x] The focal-event mechanism is attributed with explicit uncertainty.
- [x] Figures have Markdown sidecars and package docs lint cleanly.
- [x] Baseline source remains clean and the disposable worktree is removed.

## Parameterization ADR Gate

- **Parameterization change present:** no
- **ADR required:** no
- **Decision provenance captured:** yes

## Security Impact and Review Gate

- **Security impact triage:** none
- **Dedicated security review required:** no
- **Triage rationale:** Local diagnostic model execution; no application or
  external interface changes.

## Deliverables

- Reproducible runner, source patch, hashes, compact CSV results, figures, and
  findings integrated into the Stevens investigation.

## Closure Notes

The study attributes a material share of the focal inversion to antecedent
burned soil evaporation: 25.89 mm of excess 30-day `Es` closely matches the
23.0 mm shallow-layer deficit. Reference demand and precipitation are equal;
LAI partition and residue exposure carry the modeled contrast. See
[`artifacts/results.md`](artifacts/results.md).
