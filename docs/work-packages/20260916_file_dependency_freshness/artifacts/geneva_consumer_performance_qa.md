# C05/C06 representative consumer cost discovery

Disposition: **measured provisional budgets supported; implementation and
runtime acceptance pending**. This is the actual Geneva geometry query and
auto-burn materializer on a copied maintained run, with additional identity
observations composed around them. It is not an implemented provenance or
publication guarantee.

Retained [script](benchmark_geneva_consumers.py),
[JSON](geneva_consumer_performance_baseline.json) and
[log](geneva_consumer_performance_baseline.log). Large inputs, source-module
snapshots, outputs and previous artifacts remain browsable beneath
`/wc1/batch/qa-geneva-consumers-d03fded2e37c/`; `benchmark-manifest.json`
describes the run. Source-module hashes remained unchanged during measurement.
The composed observer is the then-loaded `raster_freshness.py`, SHA-256
`c0b0a079b11574ef7d46b2d852afa6cae908d18a84279627633b8163aa2ad6f2`;
final security revisions require new acceptance measurements.

## Actual inputs and safety boundary

Six existing files from `/wc1/runs/in/incomparable-gracefulness` were copied
through ordinary file reads before any native raster inspection. Companion
candidates were enumerated/copied without native-opening the named originals.
Before/after hashes and device/inode/size/mtime/ctime prove all six named inputs
unchanged. The unique disposable basename has no named-run notification
identity. The services use a `wd`/real `GenevaArtifactIO` owner seam only: no
NoDb controller, named status channel, HTTP/RQ operation or Geneva kernel ran.
The container identity is UID 1000/GID 993; rasterio is 1.3.10.

| Input/output | Representative size and shape |
| --- | --- |
| HRU raster | 156,939 bytes; 192 × 195; int32 GTiff; 30-meter EPSG:32611 grid |
| HRU legend | 49,149 bytes |
| Existing geometry | 1,122,670 bytes; 990 features |
| Preferred SBS source | 46,216 bytes; 933 × 789; uint8 GTiff; 20-meter EPSG:26911 grid |
| Canonical bound | 151,730 bytes; 192 × 195; int32 GTiff; 30-meter EPSG:32611 grid |
| Existing aligned burn | 15,208 bytes |

The selected SBS path is the existing preferred `Disturbed.sbs_4class_path`.
The source-selection owner lookup is traced, not timed. Native rasterio lists
only the copied primary files for this plain-TIFF representative case. This
does not establish closure for masks/PAM/VRT or other supported layouts.

## Measurements

All times are milliseconds, on copied filesystem-warm NFS data. Means use
20–30 hit/identity repetitions and three misses. Helper-cold clears the existing
ordinary digest caches, without dropping OS caches. Force-miss operations
retain the previous disposable output by renaming it before actual generation;
that small setup cost is included in the miss time.

| Boundary | Existing actual consumer | Composed source checks + actual consumer |
| --- | ---: | ---: |
| C05 complete cached geometry query | 16.15 | 24.03 settled; 25.60 helper-cold |
| C05 complete native geometry query miss | 884.35 | 940.27 settled |
| C06 cached auto-burn materializer | 0.91 | 14.19 settled; 14.32 helper-cold |
| C06 native auto-burn materializer miss | 29.35 | 34.19 settled |

C05 native work includes masked rasterio reading, vectorization, WGS84
reprojection, legend properties, bounds, real artifact serialization and the
final query read/envelope. Identity adds the actual raster observer and legend
SHA with source-version guards, before and after the query. A single identity
costs 3.94 ms settled; its first helper-cold call costs 27.85 ms, including
first-use observer overhead. Complete cold reuse hashes 412,176 bytes, twice
the raster-plus-legend set.

C06 native work is the unchanged nearest-neighbor `raster_stacker`, including
color-table propagation. Identity observes the selected source raster and
opens the bound with **actual `rasterio.open(...).profile`**, with local version
guards. Profile-only cost is 3.21 ms; combined source/profile identity is
7.39 ms settled and 8.47 ms first helper-cold. Bound pixels/masks are not read
or hashed as scientific dependencies. Complete cold reuse hashes 92,432 source
bytes, twice the SBS source size. The probe captures the full profile for cost
discovery; final compatible field selection belongs to the checkpoint.

Both composed settled hit paths perform **zero full digest payload reads**.
Counters do not classify native GDAL/rasterio metadata or pixel reads as digest
payload reads. The 990 generated geometry features exactly equal the original
GeoJSON; generated burn pixels and complete rasterio profile equal the original.

## Proposed checkpoint budgets

Ratify these representative **service/component** targets only after the
provenance/publication checkpoint is explicit:

| Complete boundary | Proposed mean target | Measured basis |
| --- | --- | --- |
| C05 unchanged query, settled | ≤40 ms | Composed 24.03 ms, including the 16.15-ms existing JSON/envelope cost. |
| C05 unchanged query, cold/admission/evicted | ≤75 ms | Complete helper-cold 25.60 ms; first single observer 27.85 ms; headroom includes first-use and final evidence checks. |
| C05 miss, added overhead | ≤100 ms above paired native baseline | Composed added 55.93 ms; includes pre/post identity, with final atomic publication/evidence still to measure. |
| C06 unchanged materializer, settled | ≤25 ms | Composed 14.19 ms; actual profile reading is retained. |
| C06 unchanged materializer, cold/admission/evicted | ≤40 ms | Composed helper-cold 14.32 ms; first identity 8.47 ms. |
| C06 miss, added overhead | ≤35 ms above paired native baseline | Composed added 4.84 ms; native itself 29.35 ms; allows required provenance/publication work. |

These are measured proposals with explicit headroom, not passed final gates.
Actual 512-entry eviction was not run in this short discovery. Final timing
must include all source eligibility, persisted evidence, target validation,
coherence and atomic publication checks; retain failures rather than subtracting
required work. Use paired controls because native geometry timing varies.
Larger HRU fragmentation can increase geometry/JSON cost independently of TIFF
size; this small real watershed is not a universal scalability guarantee.

The [retained correctness baseline](c03_c05_c06_freshness_review.md) still
requires actual changed-pixel/legend/mask/source/grid outputs, same-byte reuse,
legacy regeneration, denied/unverified/native compatibility and previous-output
preservation. Do not equate this composition with publication safety. Full
Geneva owner, HTTP/RQ, browser and package acceptance remain open. No production
or test files changed.
