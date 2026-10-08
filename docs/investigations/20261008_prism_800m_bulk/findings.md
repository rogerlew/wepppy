# PRISM 800 m bulk extraction feasibility

Date: 2026-10-08. Status: live acquisition and sampled artifact parity validated;
production client/cache and WEPP integration not implemented. Durable design and
the operator's native-cell requirement are recorded in
[PRISM 800 m client design](../../dev-notes/prism-800m-client-design.md).

## Result

Bulk extraction is viable for the tested workload. A single 500-cell, full-leap-year,
five-variable request returned 183,000 complete daily rows in 17.27 seconds,
including polling and download. The existing services suffice for an initial
client; these measurements do not justify an archive or new service. No sustained
load, concurrent-user performance, provider service guarantee, or multi-decade
end-to-end build was tested.

The important observed hazards are silently omitted masked cells, coarse bulk
version metadata, and HTTP-200 error bodies. Existing dewpoint preprocessing
materially changes source values, but the operator clarified that Anurag
specified that behavior for WEPP use; it is not classified as a defect. See the
[source audit and correction](dewpoint-source-audit.md). Full-year point/bulk
comparisons and sampled independent COG comparisons passed.

## Workload and timings

All requests used 800 m, interpolation off, SI units, and `ppt tmin tmax tdmean
soltotal`. Batches were serialized; polling interval was five seconds. Times
include that polling quantization, downloading, and lossless gzip retention.
Source CSV sizes below are uncompressed decimal MB.

| Batch | Requested / returned locations | Daily rows | Time (s) | CSV MB |
| --- | --- | --- | --- | --- |
| 1981 full year | 52 / 50 | 18,250 | 5.65 | 1.219 |
| 2020 full year | 52 / 50 | 18,300 | 5.61 | 1.224 |
| 2025 full year | 52 / 50 | 18,250 | 5.61 | 1.221 |
| 2026-10-01 through 2026-10-07 | 52 / 50 | 350 | 5.41 | 0.024 |
| 2020, 100 adjacent Oklahoma cells | 100 / 100 | 36,600 | 5.77 | 2.333 |
| 2020, 500 adjacent Oklahoma cells | 500 / 500 | 183,000 | 17.27 | 11.755 |

The 52 requests cover 12 regional anchors: Palouse, Olympic Peninsula, Sierra
Nevada, Death Valley, Rockies, Tucson, Oklahoma, Houston, Asheville, Miami,
Maine, and Duluth. Four anchors have 3-by-3 native-cell neighborhoods. Four
water/coast/island probes and four same-cell aliases complete the sample.
There are 48 distinct native cells, 46 of which returned data. This is a
deliberately varied diagnostic sample, not a representative national survey or
validation against weather stations. Exact coordinates and rows/columns are in
[locations.json](evidence/locations.json).

## Data quality and spatial checks

Across 274,750 primary daily rows, every returned location had exactly the
requested calendar, with no duplicate dates, missing/nonfinite fields, -9999
values, negative precipitation/radiation, or minimum temperatures above maxima.
The two omitted identifiers (`coast`, `pacific`) were absent from every sample
CSV despite `Locations: 52` and `errors: false`. Independent grids contain
-9999 at those cells. Lake Superior and Key West probes returned data. A client
must compare returned IDs against the request, not just inspect returned values.

Mean dewpoint was below daily minimum temperature on 12,227 of 18,300 returned
2020 rows (66.8%, including aliases). This is physically permissible: the daily
mean dewpoint is not bounded below by the daily minimum air temperature. The
existing `np.clip(tdmean, tmin, None)` would change these source values. Preserve
raw observations while retaining the established adjustment for model inputs
pending resolution of Anurag's rationale; the initial recommendation to remove
it is withdrawn. No sampled
mean dewpoint exceeded daily maximum temperature. Largest sampled daily rainfall
was 247.53 mm and temperature maximum was 53.1 C; neither is classified as an
error from magnitude alone. Station-based accuracy and solar physical-bound
validation remain untested.

Same-cell off-center requests (`pal_sw`, `pal_ne`) matched the center for all
five variables, all historical years, and the recent window. Original-coordinate
aliases also matched. The first 100 cells were exactly identical in the 100- and
500-location batches. Three full-year point requests (Palouse, Death Valley,
Miami) matched their bulk counterparts for all 366 dates and five variables.

The four 3-by-3 neighborhoods showed spatial wet/dry differences in 2020:

| Neighborhood | Days with both wet and dry cells | Maximum same-day cell range (mm) |
| --- | --- | --- |
| Sierra | 3 | 2.65 |
| Tucson | 7 | 4.19 |
| Oklahoma | 10 | 7.46 |
| Asheville | 15 | 11.47 |

These are native daily precipitation patterns that smoothing would change;
they do not establish observed subdaily storm timing or improved WEPP results.

## Independent grid parity

Downloaded three native grid ZIPs: precipitation for 2020-01-01 and 2026-10-01,
and solar radiation for 2020-01-01. Parsed the GeoTIFFs and compared all 52
requested positions against the actual downloaded bulk CSVs. All 50 returned
positions matched within 0.00501 in source units, consistent with CSV rounding
to 0.01; both omitted positions were nodata in every grid. Maximum differences
were 0.00200 mm, 0.0049411 mm, and 0.00499996 MJ/m2/day, respectively.

Grid geometry is EPSG:4269, 7025 by 3105, 30 arc seconds; see
[grid_geometry.json](evidence/grid_geometry.json). Controlled test coordinates
used these native axes; datum transformation and exact boundary tie handling
are still production validation requirements. Full ZIPs are cached in `/tmp`
and not committed. Their URLs, hashes, metadata, transforms, and all sampled
values are retained under `evidence/grid_*`; the ZIPs can be reacquired subject
to PRISM's download limits. Bulk CSV bytes are retained losslessly as `.csv.gz`.

## Can we identify stale bulk data and grids?

Yes for conservative local-cache invalidation; no bulk API response proves
atomic correspondence to a particular upstream grid revision.

The `releaseDate` range API returned complete 366-day manifests for all five
variables for 2020, each in approximately 0.13-0.14 seconds. It also returned
records for 1981 and for solar radiation, despite older PDF limitations. In the
sample, 2020 precipitation/temperature/dewpoint release dates were 2024-12-17;
solar release dates were 2026-03-10. All had update count 8. Recent records had
counts 1 or 2 and release dates through 2026-10-08. Recent manifests captured
before and after independent parity checks were unchanged. We did not observe
an actual provider revision transition during this study.

Use release date plus update count for each variable/day as a cached manifest;
a difference makes dependent cached series stale even if their age or count
suggests stability. The date-only API metadata cannot rule out same-day changes
or bulk-backend lag. The CSV exposes a generation date and generic `AN91d`
label, not per-grid versions. In fact, the 2020 precipitation grid identifies
`an81/r1812`, D2, while the multi-variable CSV says AN91d. Do not interpret that
CSV label as precise provenance for every variable and date.

Recent GeoTIFFs include release number and source creation tags that the 2020
precipitation grid lacks. That grid's internal creation date is July 2020,
releaseDate is December 2024, and static ZIP Last-Modified is January 2025:
these timestamps identify different processing/distribution events. The static
ZIP supports ETag/Last-Modified; the grid API response tested did not. Bulk CSV
ETag/Last-Modified refer only to that extraction file. None establishes that a
retained CSV still reflects current source data.

Requests beyond the published date exposed another boundary: the point service
returned `GridAccessError/InvalidGridKeys`; releaseDate returned HTTP 200 with a
plain-text invalid-date error despite `?json=true`. Validate response bodies and
requested date coverage. A recent bulk request with client `stability=stable`
was correctly returned with an `early` filename; the server did not accept the
client label as evidence of stability.

## Reproduction and acceptance

The standalone [check.py](check.py) uses already available requests, pandas,
NumPy, and rasterio. No production modules were changed. Offline reproduction:

    python docs/investigations/20261008_prism_800m_bulk/check.py analyze
    python docs/investigations/20261008_prism_800m_bulk/check.py verify

The verification passes expected masked-cell omissions, exact returned calendars,
basic physical checks, same-cell identity, batch-size invariance, point/grid
parity, and unchanged recent manifests. The deliberate coverage omissions remain
failures a production client must reject, not missing rows to approve silently.

For a new live study, copy `check.py` into a separate study directory to preserve
this dated evidence, and run `grid`, `freshness`, `sample`, `scale`, `parity`,
`extras`, `analyze`, `verify` in order. Dates are fixed to this study; revise the
recent/unpublished-date probes for a later study. Already-retained bulk CSVs are
reused for experiment resumption only; this is not production cache freshness
logic. All live phases are explicit; analysis and verification make no requests.

Raw request/response metadata, downloaded CSV hashes, summaries, comparisons,
and the pass result are in [evidence](evidence/). Small initial releaseDate,
gridCount, and static ZIP HEAD probes are retained there as supplementary
evidence. No PRN/CLI/model outputs were generated, so this is not a WEPP
integration acceptance result. Broad production tests are not applicable;
validation directly parsed the acquired artifacts and exercised the experiment.

## Sources

- [PRISM bulk Explorer](https://prism.oregonstate.edu/explorer/bulk.php): 500 locations and 12 months per daily request.
- [Web services specification](https://prism.oregonstate.edu/documents/PRISM_downloads_web_service.pdf): releaseDate, gridCount, downloads, and limits; live responses exceed some older documented coverage limits.
- [PRISM datasets](https://prism.oregonstate.edu/documents/PRISM_datasets.pdf): variables, daily boundaries, and scientific background.
- [Explorer JavaScript](https://prism.oregonstate.edu/explorer/dataexplorer/js/explorer.js): live multi-point submit/poll protocol.

Data attribution: PRISM Group, Oregon State University,
https://prism.oregonstate.edu, accessed 2026-10-08. Data are reproduced according
to [PRISM's terms](https://prism.oregonstate.edu/terms/).
