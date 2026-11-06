# ESDAC Soils

https://esdac.jrc.ec.europa.eu/resource-type/european-soil-database-soil-properties
https://esdac.jrc.ec.europa.eu/content/topsoil-physical-properties-europe-based-lucas-topsoil-data
https://esdac.jrc.ec.europa.eu/content/european-soil-database-derived-data

## Runtime quality boundary

ESDAC builds persist an additive `soil_quality.json` report beside generated
base soils. EU disturbed-soil generation uses that per-location result for
both single-OFE and MOFE transformations: `valid` and `degraded` profiles are
transformed, while rejected profiles fail with location-specific diagnostics.
Each generated artifact is written to a temporary `.sol`, reparsed with the
canonical WEPP soil parser, and atomically published only after the downstream
contract passes. Non-EU and non-ESDAC disturbed workflows are outside this
runtime gate.

When a batch is rejected, `soil_quality.json` remains the complete diagnostic
record. The raised error, application log, and run status channel also report
a bounded summary containing representative TopoAZ IDs, grouped reason codes,
fields, counts, raw values, and the report filename. This summary is intended
for immediate operator diagnosis; consult the report for every affected
location and all source evidence.

The run interface obtains the failed job's traceback from `jobinfo`. Its soil
control displays the terminal ESDAC batch diagnostic in Summary and retains
the traceback in Details, so users do not need filesystem access to learn why
the source locations were rejected.

## Incomplete source data

Builds accept missing FAO names and descriptive groundwater/rooting classes
with warnings when the physical profile is usable. Missing landuse uses the
existing unknown/non-forest parameter branch and records that decision.
`soil_quality.json` retains raw missing-data evidence; generated soil comments
identify warnings. Required depth, CEC, texture, density and conductivity
checks still apply. See the [field-by-field source contract](../../../../docs/schemas/esdac-soil-source-contract.md)
and [ADR-0139](../../../../docs/adrs/ADR-0139-esdac-missing-metadata.md).
A successful build with `degraded` quality is usable, with the listed source
limitations; retrying a rejected build without changing its missing physical
evidence will not repair it.

Equivalent rebuilds reuse existing soil files. Distinct physical profiles that
share a rounded legacy key receive deterministic content suffixes, so each
hillslope retains its own soil rather than failing the batch or overwriting a
neighbor's profile. Current quality warnings remain in `soil_quality.json` even
when a historical file is reused without rewriting its comments.

For shallow profiles, the existing mapped impermeable depth limits the top
material. If the mapped texture transition lies at or below that boundary,
there is no subsoil interval: subsoil data are not required and the report
records `source.profile.single_horizon`. The 200 mm subdivision still preserves
the material properties. Required data for every emitted material remain
validated; the builder does not fabricate deeper soil where data are missing.
