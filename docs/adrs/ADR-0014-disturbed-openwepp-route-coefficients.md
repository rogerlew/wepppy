# ADR-0014: Disturbed openWEPP Route Coefficients

Status: Accepted  
Date: 2026-07-07

## Context

openWEPP Lane-D active routing requires five static route coefficients in
native `ow-lanuse-1` management files. The preceding openWEPP D16 route
coefficient bridge held because selected Disturbed-produced management files
were legacy `98.4` files and carried no authoritative
`routing_coefficients` extension.

WEPPpy Disturbed owns the disturbed class, burn severity, soil texture, and
management-file parameterization harness for the affected workflows. It is
therefore the producer boundary for class-specific native openWEPP routing
inputs.

## Decision

Add explicit openWEPP Lane-D route coefficient defaults to the Disturbed
extended lookup table and use the management-file API to produce native
`ow-lanuse-1` files only when the caller explicitly selects native openWEPP
routing output.

The values are operator-calibrated, texture-invariant class defaults. They are
not inferred from legacy WEPP row spacing, ridge spacing, random roughness,
residue, cover, or other legacy cropland fields.

## Decision Provenance

Decision Venue: Codex work-package execution chat, 2026-07-07, America/Los_Angeles  
Participants Present: WEPPcloud/openWEPP operator, Codex  
Decision Owner(s): WEPPcloud/openWEPP operator  
Implementer(s): Codex

## Change Summary

Old behavior:

- Disturbed extended lookup rows carried soil, PMET, initial-condition, and
  plant fields, but no static openWEPP route coefficient fields.
- Disturbed management outputs remained legacy WEPP management files by default.

New additive behavior:

- The extended lookup table carries five route coefficient columns and four
  provenance columns:
  - `route_skin_friction_coefficient_ko`
  - `route_form_drag_coefficient`
  - `route_roughness_element_height_m`
  - `route_roughness_concentration`
  - `route_vegetation_drag_coefficient`
  - `route_coeff_source_ref`
  - `route_coeff_authority_class`
  - `route_coeff_confidence`
  - `route_coeff_notes`
- `route_coeff_authority_class` is `operator_calibration`.
- `route_coeff_confidence` is `bounded_class_calibration`.
- `route_coeff_notes` records `texture_invariant` and the effective route
  class.
- Native output uses `Management.as_openwepp_native_cropland(...)`, which emits
  `ow-lanuse-1`, `landuse=4` native cropland records, and a
  `routing_coefficients` block after each plant record.
- Legacy output is unchanged unless native output is explicitly selected.

Active class values are ordered as `k_o`, form `C_d`, `D_r` in meters,
`lambda`, vegetation `C_d`.

| Disturbed class | Values |
| --- | --- |
| agriculture crops | `480.0, 0.25, 0.010, 0.050, 0.12` |
| bare | `540.0, 0.00, 0.000, 0.000, 0.00` |
| deciduous forest | `420.0, 0.90, 0.050, 0.180, 0.65` |
| forest | `410.0, 0.95, 0.060, 0.200, 0.75` |
| forest high sev fire | `530.0, 0.18, 0.006, 0.018, 0.08` |
| forest low sev fire | `465.0, 0.58, 0.026, 0.085, 0.34` |
| forest moderate sev fire | `490.0, 0.40, 0.016, 0.050, 0.20` |
| forest prescribed fire | `450.0, 0.70, 0.035, 0.110, 0.45` |
| grass high sev fire | `530.0, 0.08, 0.003, 0.010, 0.04` |
| grass low sev fire | `475.0, 0.27, 0.010, 0.045, 0.15` |
| grass moderate sev fire | `500.0, 0.18, 0.007, 0.026, 0.09` |
| grass prescribed fire | `465.0, 0.32, 0.012, 0.055, 0.18` |
| high use skid | `575.0, 0.03, 0.000, 0.000, 0.00` |
| low or treated skid | `545.0, 0.12, 0.006, 0.020, 0.03` |
| mixed forest | `415.0, 0.92, 0.055, 0.190, 0.70` |
| mulch | `420.0, 0.85, 0.040, 0.180, 0.20` |
| short grass | `460.0, 0.34, 0.014, 0.070, 0.24` |
| shrub | `430.0, 0.72, 0.035, 0.120, 0.45` |
| shrub high sev fire | `525.0, 0.14, 0.004, 0.014, 0.06` |
| shrub low sev fire | `465.0, 0.44, 0.020, 0.065, 0.24` |
| shrub moderate sev fire | `490.0, 0.30, 0.012, 0.038, 0.14` |
| shrub prescribed fire | `450.0, 0.55, 0.026, 0.090, 0.32` |
| skid | `560.0, 0.05, 0.000, 0.000, 0.00` |
| tall grass | `440.0, 0.48, 0.020, 0.100, 0.35` |
| thinning | `435.0, 0.90, 0.045, 0.160, 0.50` |
| young forest | `430.0, 0.85, 0.045, 0.160, 0.60` |

## Rationale

This creates an explicit source-authorized input surface for openWEPP Lane-D
routing without depending on a hidden or mechanical mapping from unrelated
legacy management fields. The class ordering follows Disturbed semantics:
undisturbed vegetated classes carry stronger roughness and vegetation terms,
high-severity burned classes carry reduced vegetation and roughness protection,
and bare/skid classes carry no vegetation drag.

The initial values are texture-invariant because no source in this work package
authorizes texture-specific gradients for these surface-routing coefficients.
Soil texture remains available in the row key for future measured or
literature-backed refinement.

## Alternatives Considered

1. Infer values from legacy WEPP row/ridge/random roughness/cover fields -
   rejected because openWEPP authority explicitly disallows a hidden bridge.
2. Use the H2637 timing recipe `500.0 0.0 0.0 0.0 0.0` for every lane -
   rejected because it is a timing harness value, not a Disturbed cohort
   production policy.
3. Hold for measured per-site values - rejected for this source-acquisition
   increment because the operator accepted an explicit bounded calibration
   table, and the schema records provenance/confidence for later replacement.

## Consequences

Disturbed can now be the canonical producer of native `ow-lanuse-1` management
files for the active Disturbed class table at the current mesh. The values are
reviewable and replaceable because they live in a single module and table with
provenance columns.

The main limitation is that these are class defaults, not measured site data.
Future packages may replace any class with measured or literature-range values
without changing the management-file API.

## Evidence

- Work package:
  `/home/workdir/openWEPP/docs/work-packages/20260707-laned-router-d16-hybrid-disturbed-route-coeff-source-acquisition-001/`
- Implementation:
  `wepppy/nodb/mods/disturbed/route_coefficients.py`
- Static table:
  `wepppy/nodb/mods/disturbed/data/extended_land_soil_lookup.csv`
- Focused tests:
  `tests/disturbed/test_route_coefficients.py`
  `tests/test_managements_module.py`

## Risk and Rollback Notes

Risks:

- Class defaults may need recalibration after D16 cohort sensitivity evidence.
- Native forest `landuse=3` is not implemented in WEPPpy management parsing;
  current Disturbed native production uses native cropland `landuse=4` over the
  existing cropland-grammar templates.

Rollback:

- Revert the route coefficient module, static CSV columns, and Disturbed
  extended-table enrichment.
- Native output is opt-in, so legacy WEPP management generation can continue
  without runtime migration if the new producer is disabled.

## Implementation Notes

`managements.py` is the canonical native management parser/writer surface.
Disturbed supplies lookup-row coefficients and calls
`Management.as_openwepp_native_cropland(...)` when native openWEPP output is
requested. WEPP prep honors the opt-in
`disturbed.openwepp_native_managements_enabled` flag and writes native
`pN.man` files only when that flag is true.
