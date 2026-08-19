# EU Disturbed Soil Hardening Artifacts

This directory will hold reviewed evidence for the EU disturbed-soil
hardening package. Planned artifacts include captured source provenance,
fixture/replay results, correctness review, QA review, any required
parameterization ADR link or decision record, and final observation results.

Do not place secrets, credentials, or complete external raster datasets here.

The Phase 2 contract is documented in
[quality-taxonomy.md](quality-taxonomy.md). Its parameterization decisions are
ratified in [ADR-0043](../../../adrs/ADR-0043-eu-esdac-soil-quality-contract.md)
for Phase 3 implementation.

Phase 5 evidence is summarized in
[phase5-downstream-validation.md](phase5-downstream-validation.md). The
downstream validator reparses generated 9002 files with the canonical
`WeppSoilUtil` parser and preserves degraded or rejected base diagnostics.
