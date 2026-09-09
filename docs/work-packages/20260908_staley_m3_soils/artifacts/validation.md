# Validation evidence

## Scope and QA assessment

This is an offline implementation and scientific source experiment. No
production NoDb/UI/RQ path, live soil cache, generated WEPP profile or deployment
was changed. Initial Git status was clean. Acquisition and evaluation use new
isolated directories; frozen inputs are checksummed before/after evaluation.

Root QA assessment: the helper remains narrowly scoped to interval arithmetic,
read-only cache adaptation and offline artifacts. Existing owned WBT and
wepppyo3 Rust perform routing/intersection counting; NumPy performs compiled
array encoding and GDAL performs bounded raster warps. No new dependency,
Python raster traversal, catch-all recovery, or implicit acquisition was added.
Tests use actual SQLite and GeoTIFF boundaries, explicit fixture records and
synthetic arithmetic examples; no sys.modules stubs were introduced. Scientific
unknowns and partial outputs remain visible rather than being declared ready.
Correctness review closes arithmetic, key and material defects; security review
closes disguised-VRT reads. Final QA gates and reproducibility evidence are recorded below.

## Focused and boundary tests

From `/workdir/wepppy`:

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py
wctl run-pytest tests --maxfail=1
wctl run-stubtest wepppy.nodb.mods.postfire_debris_flow.soil_thickness
wctl check-test-stubs
```

Focused result: **35 passed**, including real public records, valid/empty/
malformed/absent caches, encoded SQLite paths, gaps/overlaps/duplicates, R/Cr,
percentages, unknown/substituted/zero keys, partial component raster propagation,
Float32 overflow, VRT disguise rejection, reference sentinel handling, and
M3 forward/inverse consistency within 1e-12. No source hash changed.

Full repository suite: **7,766 passed, 72 skipped**, 795.59 seconds. The broad
sweep began during implementation; the final **35-test** focused suite passed
after review fixes (9.71 seconds). Stubtest: **success, no issues in 1 module**;
`wctl check-test-stubs`: **all stubs complete**. Initial stubtest runs exposed
typing-class reexports and missing untyped-import annotations, corrected without
changing scientific behavior. Test logs remain under
`/tmp/staley-m3-soils-study/`.
Independent boundary probes and findings are in the dated review artifacts.

## Acquisition and frozen-input reproduction

```bash
.venv/bin/python docs/work-packages/20260908_staley_m3_soils/artifacts/acquire_sources.py \
  --terrain /workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution \
  --spatial-source /wc1/geodata/ssurgo/gNATSGSO/2025/.vrt \
  --output /tmp/staley-m3-soils-study/acquisition-reproduction
```

Passed. The promoted acquisition recipe reproduced all six CSV tables and all
six raster subsets byte-for-byte. Final fixture metadata records the repeated
requests, survey revisions, URLs, units, attribution and hashes. Original data
were obtained with the same endpoint queries and GDAL window methods in an
initial bounded probe; later SDA snapshots may legitimately differ. No network
fallback occurs during evaluation. The three named live projects still have
no soil directories; this acquisition does not establish project readiness.

## Full offline panel

```bash
.venv/bin/python docs/work-packages/20260908_staley_m3_soils/artifacts/run_study.py \
  --wbt /workdir/weppcloud-wbt/target/release/whitebox_tools \
  --output /tmp/staley-m3-soils-study/evaluation-final
```

The final invocation passed with **72 comparison rows and 924 diagnostic
scenarios**. Final source/comparison/component/map-unit tables are byte-identical
to evaluation-v4; all 30 thickness/support/reference/mask raster arrays match
exactly. Input hashes remain unchanged and final code hashes match the recorded
environment. See `reproducibility.json`. Prior evaluation-v2/v3 also produced **72 comparison
rows and 924 diagnostic scenarios**, with byte-identical paired numerical
results across review fixes. Every reconstructed upstream mask matched archived
cell counts. The harness verifies source snapshots and terrain DEM hashes and
records WBT commands, binary/helper/harness hashes and generated input hashes.
Each site/policy builds actual SQLite → component/map-unit audits → thickness
and support rasters → catchment S → diagnostic M3 outputs. Full-support results
remain unavailable at all 12 catchments; partial results remain diagnostics.

The first native-pointer reconstruction failed archived count parity and was
corrected to reproduce the controlled terrain commands. No soil comparison was
accepted from that failed run. Intermediate incomplete folders remain isolated.

## Documentation and final gates

```bash
wctl doc-lint --path docs/work-packages/20260908_staley_m3_soils
wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
wctl doc-lint --path docs/adrs/ADR-0053-staley-m3-offline-soil-thickness.md
wctl doc-lint --path tests/nodb/mods/fixtures/postfire_debris_flow_soils/README.md
```

All four scoped documentation commands passed with zero errors/warnings.
Spelling normalization preview covered 22 Markdown files with no differences.
Final archival links and publication hashes pass closeout checks.
No frontend/RQ gates apply because those paths are unchanged.

Code-quality observability completed in observe-only mode. Changed-file broad
exception enforcement passed but scanned zero Python files because the new
modules are not yet tracked; a direct AST audit of all three new implementation/
harness files confirms zero bare or broad exception handlers. No commit or
staging was performed just to change the scanner scope.


## Scientific and review provenance

Coefficient readback reuses the independent Table 4 verification recorded in
[terrain reference evidence](../../20260908_staley_m3_wbt_terrain/artifacts/reference_parity.md)
(lines describing the nine M3 coefficients and three intercepts). The current
correctness reviewer independently recalculated all 924 scenario results.
No GPL implementation/tests or publisher PDF is copied into this package.

[Correctness](20260909_correctness_review.md) and
[security](20260909_security_review.md) gates both pass with zero unresolved
medium/high findings. Final nonfunctional typing-import fixes were additionally
checked by stubtest and the 35-test focused suite. Their file hashes are in
`environment.json`; numerical tables and all 30 checked raster arrays remained
identical through final reproduction. Prompts are archived under `completed/`.
