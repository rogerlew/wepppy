# Evidence Catalog

The registered owned terrain command and evaluation are implemented. The
[decision report](resolution_decision.md) recommends genuine 10 m for initial
M3 support; production wiring/availability enforcement is outside scope.

- [Terrain contract](terrain_contract.md), [predeclared study protocol](study_protocol.md).
- [Initial fixture inventory](catchments.csv), [requested-coordinate audit](requested_coordinate_audit.csv).
- [Reference findings](reference_parity.md), [rebuilt comparison](reference_built_comparison.json).
- [24 resolution comparisons](resolution_comparison.csv), [864 M3 scenarios](m3_sensitivity.csv), [plot](resolution_sensitivity.png).
- [Runtime measurements](runtime.csv), [environment/binary hash](environment.json), [commands](commands.json), [unavailable cases](unavailable.json).
- [Source hashes](source_hashes.json), [built source delta](wbt_source.patch), [validation](validation.md).
- [Correctness review](20260908_correctness_review.md), [security review](20260908_security_review.md).

`reference_probe.py`/`reference_probe.jsonl` preserve initial independently
authored diagnostic inputs and observed external-reference values.
`inventory.py` reproduces the initial fixture grid/outlet inventory. The final
runnable study and reference-comparison harnesses live in WBT `tools/` and
are included in the source delta. No GPL source/tests were copied or translated.

The six-run fixture bundle remains in sibling WBT
`test_fixtures/staley_m3_resolution/` with its original 66 files and hashes.
Final generated rasters are external in `/tmp/staley-m3-terrain-study/study-v4/`
and `reference-built-v4/`; validation records reproduction commands. No
publisher PDF, generated raster, production binary or live run is added here.
