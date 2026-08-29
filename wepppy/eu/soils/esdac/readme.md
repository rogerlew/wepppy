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
