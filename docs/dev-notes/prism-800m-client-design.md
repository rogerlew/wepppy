# PRISM 800 m historical client design

Status: accepted scope and cell-identity requirements; proposed freshness and
validation design. Bulk feasibility evaluated on 2026-10-08; production client,
cache, climate catalog, and WEPP integration are not implemented by this study.
Evidence: [bulk extraction investigation](../investigations/20261008_prism_800m_bulk/findings.md).

## Accepted scope and cell identity

The operator selected bulk extraction before considering daily full-CONUS grid
downloads. Every production bulk request must use the nearest native PRISM cell
center with interpolation disabled (`spares=800m`, `interp=0`). Cache identity
must use integer native row/column and a grid-geometry identifier, not arbitrary
hillslope coordinates, rounded user coordinates, or the CSV's four-decimal
coordinate display. Retain original coordinates and the mapping to cells.
Rationale: all requests for one cell can reuse one series, and native daily
precipitation values and wet/dry occurrence remain intact. Adjacent-cell
interpolation and nearest-*valid*-land-cell substitution are not authorized.

A downloaded 800 m grid establishes EPSG:4269 (NAD83), 7025 columns, 3105 rows,
approximately 1/120-degree spacing, and upper-left outer corner
(-125.02083333333351, 49.9374999999995). The full affine transform is retained in
the investigation. Resolve incoming coordinates into the native grid coordinate
system before indexing; specify and test the coordinate transformation and
boundary tie rule. Compute cell centers from the affine transform, not an
assumption that 800 m is a constant geographic distance. Extent inclusion does
not establish data coverage; masked cells must produce an explicit coverage
failure. The study's controlled coordinates used native geographic axes and
did not evaluate datum transformations near cell boundaries.

## Acquisition and cache proposal

Use the Explorer multi-point flow: POST `pp/daily_timeseries_mp`, retain its
ticket, poll `pp/checkup`, and download the returned CSV. Submit no more than
500 unique cells or 12 months of daily data per batch. Start with serialized
batches; the measured workload does not justify a new service or national
archive. Implement bounded timeouts, polling, response validation, and resumable
attempt records. The website RPC is operationally demonstrated but is not a
versioned public API contract; provider workload policy and long-run reliability
remain integration gates.

Recommended logical key: provider, region, grid-geometry ID, native row/column,
variable, date partition, units, sampling method, and parser/schema version.
Year partitions permit shared retrieval and reuse across watersheds. Keep the
source revision manifest as a version of that key. Preserve exact source CSV
bytes, source units, acquisition metadata, and a checksum alongside normalized
values. Use a semantic value checksum when comparing independent extractions:
CSV generation timestamps can change while all climate values remain equal.
Do not replace immutable run provenance when a shared cache is refreshed.

The planned variables are `ppt`, `tmin`, `tmax`, `tdmean`, and `soltotal` in SI
units. Wind sourcing, PRISM's 12:00 UTC day boundary, radiation conversion, and
CLIGEN disaggregation remain separate integration decisions. Existing daily
PRISM and Daymet/GridMET methods must retain their current identities and
behavior; `ClimateMode.ObservedPRISM` currently routes to Daymet.

## Freshness proposal

Use the documented range endpoint once per variable/date partition:

    https://services.nacse.org/prism/data/get/releaseDate/us/800m/ppt/20200101/20201231?json=true

It returns data date, release date, variable, update count, and grid URL. Retain
a normalized, complete manifest for every variable/day in the cached series.
Do not use a watershed-specific manifest: revisions apply to source grids and
can invalidate many cached cells together. Compare release dates as well as
counts; count 8 means the routine update sequence is complete, not immutable
historical data. Compare for inequality, not just increasing dates/counts.

Capture manifests before and after a fresh bulk extraction. If they change,
retain the attempt but do not publish it as verified current; repeat within a
bounded attempt policy. On reuse, a changed manifest makes the affected
partition stale. Missing records, malformed responses, API failures, or unknown
versions mean freshness is unknown, not current. In particular, HTTP 200 may
contain a plain-text error instead of JSON. A refresh cadence for stable history
versus provisional data still requires an explicit operational decision.

This is conservative invalidation, not proof that the bulk backend served the
advertised grid revision. Bulk CSVs expose no per-variable/day revision IDs, and
release dates have day-level precision. Keep representative point/grid parity
checks for backend consistency; the current study establishes sampled parity,
not atomic version pinning or future reanalysis behavior.

For grid caches, preserve the same manifest plus available GeoTIFF/info tags,
archive checksum, and HTTP validators. Old COGs lack tags present in recent
COGs. Static ZIP `ETag`/`Last-Modified` identify the downloadable object; they
can supplement refresh detection but do not substitute for climate revision
metadata. The grid API response tested had neither validator. Bulk CSV
validators identify an extraction artifact and cannot validate source freshness.
Download time and the CSV's generic `Dataset: AN91d` line are insufficient.

## Required validation before publishing a cache entry

Validate the actual CSV against the submitted cell/date/variable inventory,
including the exact set of location identifiers, duplicate rows, date order,
leap days, units, finite values, and provider missing-data sentinels. Reject
missing locations even when the CSV header claims the requested location count
and the job reports `errors: false`. Never fill an omitted location with zero,
silently select another land cell, or convert internal missing dates into
synthetic weather.

Preserve raw dewpoint in acquisition/cache artifacts. The operator clarified on
2026-10-08 that Anurag specified `dewpoint >= tmin` as necessary for WEPP use.
Retain this established preprocessing rule for model inputs; do not remove it
based on atmospheric plausibility alone. Record raw and adjusted values and
the adjustment in derived-artifact provenance. Daily mean dewpoint below daily
minimum temperature is common in the samples; this is not by itself a source
data defect. The [WEPP source audit](../investigations/20261008_prism_800m_bulk/dewpoint-source-audit.md)
found no hard lower-bound requirement in the inspected engine, but found
effects on evapotranspiration and snowmelt. Anurag's original rationale remains
unresolved; changing the preprocessing rule requires explicit approval and
model-level evidence. This supersedes the initial recommendation to omit it.
The [nine-hillslope OpenET study](../work-packages/20261008_dewpoint_openet/artifacts/results.md)
supports retaining the current default: clipped GridMET forcing gave lower
monthly ET MAE/RMSE in all 36 site–product comparisons. This is bounded evidence
for the existing parameterization, not a PRISM-specific validation. Defer a
general disable switch pending broader evidence. The study also found that
spatial temperature adjustment after source clipping can leave final hillslope
Td below local Tmin and occasional temperature-ordering exceptions; preserve
stage-specific provenance and validate derived forcing as well as source data.
The separate [stochastic station study](../work-packages/20261008_stochastic_dewpoint/artifacts/results.md)
ran 180 paired cases: adding a floor modestly improved seasonal agreement, but
station precipitation mismatch and CLIGEN quality diagnostics limit inference.
Preserve native stochastic behavior; a universal floor across observed and
stochastic methods is not established. Keep the experimental treatment in
research unless subsequent evaluation supports a stronger choice.
The [PRISM-localized stochastic experiment](../work-packages/20261008_prism_stochastic_dewpoint/artifacts/results.md)
used nearest-cell 800 m monthly normals at the same nine hillslopes. Forest
precipitation improved from 22–37% to 90–102% of the prior GridMET assessment
mean. Clipping improved seasonal RMSE in 36/36 comparisons but annual ET bias
in only 6/36. Preserve native stochastic behavior; a general stochastic clipping
switch is not established by these results. The existing localization changes
P/T means and wet-day frequency but retains station humidity and other parameters.
Any future PRISM dewpoint-normal treatment must be a separately declared change;
cache raw normals and record both localization and clipping provenance. Generator
quality diagnostics and satellite ET uncertainty remain material limitations.
Check negative precipitation/radiation and
minimum temperature above maximum temperature; investigate suspect extremes
without automatic clipping. Treat CSV rounding as part of source precision
(precipitation/solar: 0.01; temperatures: 0.1 in the observed CSVs).

Before production wiring, add an active ExecPlan, the relevant climate/UI
contracts and parameterization ADR, cache/concurrency validation, and artifact
readback through PRN, CLI, and generated WEPP inputs. This investigation changes
no run schemas, defaults, numeric formulas, or production behavior.
