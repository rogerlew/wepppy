# Rock fragment representation contract

Status: development contract, implementation conformance pending. Governs dimensional preparation and evidence; does not change native equations or validate surface proxies.

## Quantities and units

| Quantity | Denominator and units | Source/consumer |
| --- | --- | --- |
| Profile rock mass fraction w | dry fragment mass / total dry soil mass, fraction | WEPP RFG, mass-based SSURGO sieve preparation |
| Profile fragment volume v | fragment envelope volume / whole soil volume, fraction | SoilGrids cfvo; native CPM complement |
| Fine-earth bulk density rho_f | fine-earth dry mass / fine-earth bulk volume, g/cm3 | SoilGrids bdod normalized /100; conversion below |
| Fragment density rho_r | fragment dry mass / envelope volume, g/cm3 | mineral WEPP convention 2.65; not universal lithology truth |
| Surface rock S | plan-view rock area / total ground area, fraction | field observation; survey proxy with size/support caveats |
| Exposed surface rock E | rock area within bare classification / total ground area | requires co-location/overlap evidence |
| Fraction of bare r | exposed rock area / bare area | RUSLE rock_fraction_of_*_bare |

Percent values divide by100 to become fractions. SoilGrids cfvo stored cm3/dm3 divides by10 for volume percent (or1000 for fraction), independent of the maximum within a footprint. Both supported RUSLE raw and SoilGrids-aligned paths retain this stored scale. Resampling cannot convert units. A renamed file or grid resolution does not establish new data provenance.

## Profile conversion

For positive finite densities in the same units and fractions in [0,1]:

    v = (w / rho_r) / ((w / rho_r) + ((1-w) / rho_f))
    w = (v * rho_r) / ((v * rho_r) + ((1-v) * rho_f))

These represent additive fine-earth bulk and fragment envelope volumes; interfacial porosity and fragment water storage are not independently estimated. Use fine-earth bulk density, not whole-mixture density or fine-particle density. The conventional mineral fragment density 2.65 matches the existing native conversion; porous/organic fragments require a separately justified model. Native caps and recomputed densities can prevent exact round-trip volume recovery and must be reported.

The SoilGrids WEPP builder must convert normalized cfvo volume percent to RFG mass percent using its normalized bdod fine-earth bulk density before serializing. It must not assign volume percent directly to a mass field. Zero fragments remain zero; invalid/nonfinite fractions or nonpositive density fail explicitly rather than silently selecting a new default. Do not alter SSURGO's independently mass-derived RFG or uploaded soils. Existing artifacts are not migrated; correction applies on rebuild. No keys/columns/native format are renamed.

## Water and native interpretation

A nonporous-fragment approximation gives whole-soil water content (1-v)*theta_f. Porous-fragment storage, interface pores and changed fine-earth packing can violate that approximation. Do not multiply every native porosity consumer by (1-v): some already apply CPM. Dry-reference offsets cancel between capacity and stock at fixed absolute water. Any native limit correction must preserve stock/flux accounting, ordered retention limits and freeze/thaw semantics. The existing 85 percent native mass cap is retained, not a measurement or physical surface-cover bound.

## Surface support and overlap

S, E and r are different variables. With bare fraction B and total-area rock S, E is bounded by max(0,B+S-1) and min(B,S) absent co-location data. Independence would give E=B*S; all rock exposed would give E=min(B,S). Neither assumption follows solely from mass or volume fragments. E/B defines r only where B>0.

Retain current RUSLE scalar proxy/priority/fallback policy for the units repair; no claim that the proxy meets the exposed-rock definition. Field measurements must specify particle-size threshold, lithology/wood exclusion, exposed/covered status, date, role and spatial support. SSURGO component surface-fragment metadata is a proxy and must not be described as a measured Roads armor map. Missing data is unknown, distinct from measured zero; existing zero fallback remains a computational default only.

Native cropland generic residue cover is not automatically a permanent rock compartment. Preserve biomass, decomposition and overlap semantics. Do not switch landuse to expose rangeland rock fields or modify profile RFG as a surface-cover intervention. A new native surface mechanism requires separate scientific/implementation gates.

## Compatibility and validation

RUSLE C recognized SoilGrids raw/aligned inputs use fixed /10, preserve source order and explicit user overrides, and retain scale_divisor provenance. Added source-unit metadata is backward-compatible. K already uses /10 for those sources and must remain unchanged. Optional missing/all-nodata inputs retain existing fallback behavior.

Unit repairs require real input/output rasters and manifest readback for RAP and SBS, low/100/high values, nodata and both source paths. Generated-soil repair requires actual builder serialization, unchanged 200 mm boundary and downstream native input interpretation evidence. Tests alone do not establish field accuracy, deployed recovery or scientific acceptance of a changed native capacity/cover law.

## Authority and rationale

Operator requested investigation/development on 2026-10-31 Pacific. [ADR-0125](../adrs/ADR-0125-rock-fragment-unit-and-basis-repairs.md) records the bounded changes. Existing RUSLE [specification](../../wepppy/nodb/mods/rusle/specification.md) and [soil boundary contract](soil-horizon-boundary-contract.md) remain applicable. Separate basis variables prevent hidden mass/volume/area substitutions while preserving supported workflows.
