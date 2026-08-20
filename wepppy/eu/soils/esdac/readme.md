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
