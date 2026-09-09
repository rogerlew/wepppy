# Implement dNBR backend contract and normalization


This living plan follows `docs/prompt_templates/codex_exec_plans.md`. Update
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.

## Purpose


Accept explicitly encoded local dNBR rasters, normalize onto an authoritative
project DEM grid, and expose catchment means and observed support for M1.
Deliver a Python interface with real western US fixtures. No UI, endpoint,
NoDb state, queue, or live replacement publication is implemented here.

## Progress


- [x] Source and repository research; two real Arizona fixtures acquired.
- [x] Contract/ADR finalized before runtime edits.
- [x] Backend implementation and 45 synthetic/real integration tests.
- [x] Independent reviews approved, full suite 7,822 passed / 72 skipped, docs and evidence.

## Surprises & Discoveries


USGS source metadata describes an 8-bit output, but actual files are Float32
with x1000 values. Metadata processing code explicitly multiplies dNBR by 1000.
Nonfinite values occur inside declared masks; treat them as invalid support.
Independent review also found that detached decoding could silently discard
external masks and that compressed blocks/XML could exceed logical input
limits. Recognized sidecars now fail explicitly; decoded block and preparse
XML bounds have real regression cases and independent closure evidence.

## Decision Log


2026-09-09: backend first assumption stated while optional UI scope question
remains unanswered. User authorized dNBR contract and WEPPpy implementation.
Use existing rasterio/GDAL compiled warp precedent, not Python raster traversal.
Choose nearest source-cell sampling to preserve values and holes without
inventing observations. Record candidate comparison evidence in tests.

## Context and Orientation


Read root/nested AGENTS and `wepppy/nodb/mods/postfire_debris_flow/specification.md`.
Its dNBR draft covers .tif/.tiff/.img/.vrt, 100 MiB, explicit encoding, WBT grid,
negative/zero preservation, and partial catchments. Existing RUSLE integrations
use rasterio.warp.reproject through compiled GDAL. Tests belong under
`tests/nodb/mods`, real source fixtures in `fixtures/postfire_debris_flow_dnbr`.
Raw dNBR is dimensionless; normalized catchment mean supplies M1 F directly.
Never divide it by 1000 twice, substitute SBS categories, or affect M3.

## Plan of Work


Milestone 1 freezes a backend contract in the module dNBR document and ADR-0054:
function names, explicit factor/offset, allowed real numeric bands, safe local
VRT subset, exact target grid, nearest valid sampling, output manifest and
coverage summaries. Offline output directories must be new and published only
after validation. Preserve all existing outputs; caller selects/publishes later.
Backend-only changes do not invoke a UI/NoDb/RQ ancestor checkpoint. Any scope
expansion to those boundaries requires the separate standard checkpoint.

Milestone 2 implements `dnbr.py` with `normalize_dnbr` and `summarize_dnbr`.
Validate numeric encoding, dates, local references and finite grid/values;
retain source masks before scaling. Work in staging, write normalized Float32
GeoTIFF, and install a new completed directory only after a success manifest.
Use compiled GDAL warp, no live data acquisition. Return stable error codes.
Test invalid/empty inputs, shifts, differing CRS/resolution/extents, sentinels,
equivalent scales, negative/zero values, partial catchments and failures.

Milestone 3 compares candidate kernels on synthetic shifted/holey grids and
runs actual western US fixtures through an explicit 10 m target. Compare
summary results against independently calculated array expectations and hashes.
Obtain independent correctness and security reviews as required by package
guidance; permitted delegation is limited to these bounded reviews. Fix
medium/high findings and collect generated-output evidence, full tests, docs.

## Concrete Steps


From `/workdir/wepppy`, use `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_dnbr.py`
for focused checks and `wctl run-pytest tests --maxfail=1` for substantive
handoff. Run `wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow` and
the package path. Record exact counts and review dispositions in artifacts.
Do not require network access in tests. Any regression unrelated to this
change must be evidenced and reported separately, not silently ignored.

## Validation and Acceptance


Read actual raster outputs: CRS/affine/dimensions match the DEM exactly,
Float32/NaN is canonical, partial means divide by observed target support,
and no-data catchments are unavailable. Hostile VRT paths/functions fail
before GDAL opens them; accepted local single-source VRT and self-contained
IMG exercise real readers. Existing output directories and source hashes
survive failed normalization. Source metadata and full-precision factor/offset
are recorded. Independent reviews must have no unresolved medium/high findings.

## Idempotence and Recovery


Use new output directories and immutable inputs; staging is removed on failure.
No writes to project state, cached source rasters, or existing outputs. Preserve
unrelated edits. Do not deploy or send messages/emails to acquire fixtures.

## Interfaces and Dependencies


The backend uses NumPy and existing rasterio/GDAL, standard-library XML/path
validation, JSON provenance, and local files only. No new GIS dependency.
Caller supplies the authoritative grid, binary watershed mask and encoding.
Browser transport and active-artifact pointer publication remain separate.

## Outcomes & Retrospective


Backend and 45 focused tests implemented; independent reviews approved after
external-mask and XML/decoded-block resource findings were closed. Real 10 m
outputs are recorded in artifacts. Full suite passed: 7,822 tests, 72 skipped. Backend scope complete; browser,
NoDb and RQ publication remain deferred. No live changes or deployment.

Revision note: Completed locally 2026-09-09 UTC; gates and independent
review dispositions recorded, prompts archived, durable contract promoted.
