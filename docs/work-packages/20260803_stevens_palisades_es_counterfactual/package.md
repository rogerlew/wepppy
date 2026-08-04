# Stevens–Palisades Peak Soil-Evaporation Counterfactual

**Status:** Closed (2026-08-04)
**Timezone:** UTC

## Overview

Determine why the Stevens Canyon burned fixture produces much larger peak
daily soil evaporation (`Es`) than the Palisades burned fixture. The package
uses paired production-derived hillslope inputs and decomposes the contrast
into site forcing and surface-water coincidence, vegetation exposure, and
spatial synchronization without changing production parameterization.

## Objectives

- Reproduce area-weighted and individual-hillslope daily `Es` for both sites.
- Quantify how much spatial synchronization changes each site's peak.
- Evaluate peak-day atmospheric-demand, shallow-water, LAI, and residue
  conditions and construct transparent counterfactual bounds.
- Produce figures with Markdown sidecars and a reproducible results narrative.

## Scope

Included are burned-PMET hillslope simulations with `wepp_260803_hill`, saved
Stevens outputs, reconstructed Palisades inputs from the completed four-cell
study, and analysis artifacts. Watershed/channel reruns, production changes,
and parameter calibration are excluded.

## Success Criteria

- [x] Input provenance and sidecar validation are retained.
- [x] Both sites have validated per-hillslope daily series.
- [x] The observed peak ratio and synchronization bounds are reproducible.
- [x] Driver attribution states what is measured, inferred, and unresolved.
- [x] Every figure has a Markdown sidecar and scoped docs lint passes.

## Parameterization ADR Gate

- **Parameterization change present:** no
- **ADR required:** no
- **Decision provenance captured:** yes

## Security Impact and Review Gate

- **Security impact triage:** none
- **Dedicated security review required:** no
- **Triage rationale:** Offline analysis of local, public-run-derived fixtures;
  no application, authentication, network, or execution interface changes.

## Dependencies

- `docs/work-packages/20260803_stevens_canyon_water_balance_attribution/`
- `docs/investigations/2026-08-03-palisades-fire-peak-flow-inversion/artifacts/four-cell-et/`
- `/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes/`

## Deliverables

- Active ExecPlan and completed outcome record.
- Reproducible runner and compact CSV results.
- Counterfactual figures with Markdown sidecars.
- Findings linked from the two investigation trees.

## Closure Notes

**Closed:** 2026-08-04

The full replay rejected the eightfold premise: the observed area-weighted
ratio is 1.28 and the p99 ratio is 1.09. Exact synchronization bounds are
negative as an explanation. Higher realized evaporative throughput coincident
with available surface water carries the remaining observed contrast; PMET's
soil fraction is actually larger at Palisades. Detailed evidence is in
[`artifacts/results.md`](artifacts/results.md).
