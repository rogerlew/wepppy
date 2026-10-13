# EDDE v2 experimental client and daily replay contract

## Status and scope

This additive research interface is not wired into WEPPcloud. It supports reproducible feasibility experiments, not a claim of unbiased or complete future weather. The [feasibility package](../work-packages/20261013_edde_v2_feasibility/package.md) owns study evidence; this document owns the durable interface. Scientific transformations and limitations are recorded in [ADR-0091](../adrs/ADR-0091-edde-v2-experimental-daily-replay.md).

## Acquisition and eligibility

`wepppy.climates.edde.EddeClient` accesses only the public `epa-edde-v2` S3 bucket over HTTPS, without credentials or arbitrary endpoint overrides. The session disables environment-derived authentication, proxies, and CA overrides (`trust_env=False`); direct HTTPS uses Requests' default CA trust. Discover actual objects for model/scenario/year/month/variable; a registry label or directory period is not an availability guarantee. Reject missing combinations and partial requested date coverage. Requested dates are inclusive Gregorian calendar days; no gap filling, leap-day duplication, bias correction, or spatial interpolation occurs.

Each `Point` has a unique safe name and finite WGS84 longitude/latitude. Eligibility transforms the point into the source's projected grid, checks cell-face bounds, and selects a native cell. Require valid land mask exactly equal to one; do not clamp outside points or relocate ocean-cell points to nearby land. Report source cell center, row/column, projected distance, and cells to the grid edge. Geographic coverage and valid weather records are separate checks. Future locale gating cannot replace project and required-location eligibility.

The caller supplies a download budget (default 4 billion bytes per query). Preflight checks the full source footprint conservatively even for warm queries; actual download accounting also enforces the limit. Read all requested points from each fetched monthly object. The caller owns disk capacity and cache retention; there is no unbounded background ingestion or automatic eviction. One writer per cache object is required; separate cache roots can isolate independent jobs.

## Source integrity and errors

Cache names are SHA-256 hashes of complete validated object keys. Reuse requires matching source listing metadata, exact size, and a freshly verified file SHA-256. Downloads use `If-Match`, verify response ETag and exact byte count, and promote a completed file from a `.partial` path. Do not follow redirects. Explicit HTTP timeouts apply. Missing dependencies or upstream failures propagate; there is no silent fallback to another model, scenario, cell, variable, or date.

`EligibilityError` means outside-domain or nonland cell. `AvailabilityError` means absent/ambiguous source selection. `DataQualityError` means invalid metadata, geometry, times, or values. All inherit `ValueError`. Transport exceptions retain the requests error contract. Before downloading, record an attempt manifest; partial files and their source identity remain inspectable after failure. A failed study/CLI generation is never marked complete.

## Query result and provenance

`query(points, model, scenario, start, end, variables)` returns a DataFrame with `point`, `date`, and one source-valued column per requested variable, plus a JSON-serializable manifest. Every point/date/variable must exist exactly once and contain finite unmasked values. Source grids must match static projected axes and CRS. Daily timestamps must be consecutive midnight values. Preserve source variable name, units, calendar, timestamps, object key, size, ETag, SHA-256, model/scenario, cell selection, and transfer/cache metrics. An ETag is an identity token, not necessarily an MD5.

The command `python -m wepppy.climates.edde` offers `inventory` and `query`. Output directories must be new; intentional reruns use new directories. A query writes `manifest.json` with incomplete status before work and completes it only after writing/hash-reading `daily.csv`. Existing outputs are not evidence of a new attempt.

## CLIGEN generation

`wepppy.climates.edde.cligen.build_climate` requires a single point, complete consecutive daily years, complete matching query manifests, an explicit station, a seed, and a new output directory. Source metadata must identify `prday/PRECIP/kg m-2`, `tsmax/T2MAX/K`, and `tsmin/T2MIN/K`. Convert precipitation to numerical mm and temperature to Celsius; reject invalid physical ordering and negative precipitation. Preserve a raw table and normalized table before writing PRN and invoking the existing CLIGEN 5.3.2 daily replay interface.

Keep the existing PRN rounding and validate exact CLI dates and precipitation/temperature within format bounds from ADR-0091. No MX .5 P adjustment, source-value restoration, or quality-guard bypass occurs. Storm duration/shape/intensity, radiation, wind, and dewpoint remain station-generated. The CLI header retains that station's location and normals; source point/cell and daily EDDE attribution are in the manifest. Consumers must not infer that header normals or auxiliary fields are future projections. Full future-weather production adoption remains gated on addressing these limitations.

## Multiple PRISM

`revise_prism(source, output, reference, target)` implements existing precipitation-ratio and temperature-offset arithmetic using explicit retained 12-month normals. Require matching reference/target periods, precipitation in mm/month, temperatures in Celsius, source hash, finite values, positive reference precipitation, and valid temperature ordering. Output and its companion provenance file must both be new and separate from source. Source and readback must have continuous ordered dates, finite fields, nonnegative precipitation, valid temperature ordering, and meaningful wet-day storm duration/intensity; revision arithmetic must remain finite. Reject any daily inversion of minimum/maximum temperature; never clamp or silently switch methods. A PRISM-covered point is not sufficient to guarantee that a particular climate/normal pair is valid.

Historical and future experiments use identical normal pairs. Validate resulting values within the CLI's 0.1-unit rounding and measure seasonal future-signal preservation. Multiple Interpolated is not supported initially: useful finer-scale variation has not been established for the 12 km source.

## Artifact layout and operational recovery

Query output contains `daily.csv` and `manifest.json`. Each new generation directory contains `source-daily.csv`, `normalized-daily.csv`, `daily.prn`, the station `.par`, `cligen_wepp.log`, `wepp.cli` when successful, and `manifest.json`. PRISM output has a companion `.prism.json`. Manifests identify binaries, seeds, hashes, generated fields, source objects, and limitations. Preserve failed attempt directories; retry in a new directory. Query cache is reconstructible; generated study records and provenance are not disposable cache.

These are standalone research directories, following existing climate-module artifact naming. No project/browser/archive route or NoDb schema is changed. The integration package must place these records under visible project climate directories and prove normal browser/download/archive behavior before application adoption. This document does not waive that gate.
