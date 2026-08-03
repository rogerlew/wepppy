# Stevens Canyon Hillslope Water-Balance Attribution

**Status:** Complete
**Started:** 2026-08-03
**Security impact:** none

## Purpose

Identify which hillslope-scale hydrologic fluxes carry the broad tendency for
the undisturbed scenario to be flashier than the burned scenario. The first
milestone uses existing outputs only and produces a paired burned/undisturbed
water-flux figure for each contributing hillslope H49-H61.

## Scope

Analyze the existing 100-year daily `H*.wat.dat` outputs. Compare surface
runoff, lateral subsurface flow, deep percolation, plant transpiration, soil
evaporation, and residue evaporation. Do not rerun WEPP or modify production
projects. Figures use common axes within each hillslope and include Markdown
sidecars with event and antecedent-period totals.

## Outcome

The focal inversion is carried by surface runoff rather than antecedent lateral
flow. Undisturbed runoff excess is rare over the 100-year record and coincides
with lower soil evaporation and wetter shallow layers. Total ET remains nearly
conserved between burned and undisturbed because the model transfers ET from
plant-side flux to soil evaporation. A canonical high-severity extension fails
the provisional annual ET and `Es/ET` targets in all 100 paired years. The next
study should instrument `evappm` and runoff-generation thresholds rather than
apply another broad parameter ensemble.
