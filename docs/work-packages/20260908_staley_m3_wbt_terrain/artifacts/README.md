# Evidence Catalog

Status: planned artifacts; none of the numerical evaluations has run.

Execution should produce `terrain_contract.md`, `study_protocol.md`,
`catchments.csv`, `reference_parity.md`, `resolution_comparison.csv`,
`resolution_decision.md`, and `validation.md`, plus dated independent
correctness and security review reports. Include portable plots where useful.

Record source URLs or authorized local paths, input hashes, geographic outlets,
CRS, vertical units, pixel dimensions, conditioning parameters, pointer encoding,
tool and reference revisions, built-binary hash, commands, and runtime environment.
Store large DEMs and generated rasters outside git in an isolated study directory;
record their locations and reproduction steps here. Do not commit the Staley PDF
or copied GPL implementation/tests. Missing evidence must remain explicit.

The primary input fixtures are committed in the sibling WBT repository at
`test_fixtures/staley_m3_resolution/`; its README and manifest identify all six
runs and source URLs. This deliberately versions the selected input rasters
through LFS, while generated study rasters remain external. Boundary TIFFs and
projected/WGS84 GeoJSONs are included. No new site acquisition is needed to
begin the paired workflow comparison.
