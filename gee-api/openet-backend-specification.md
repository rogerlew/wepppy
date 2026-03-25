# OpenET GEE Backend Specification
> Design specification for a Google Earth Engine backed OpenET raster acquisition pipeline that minimizes remote API calls, avoids Google Drive, caches deterministic tiles, and performs merge/crop/zonal work locally.

## Status
- Draft for design review.
- Authored on 2026-03-24.
- Scope is backend architecture and API strategy, not implementation code.

## Problem Statement
The current WEPPpy OpenET path is not durable because it performs per-polygon remote queries through Climate Engine. That pattern scales with `polygons x datasets x runs`, which is exactly the wrong cost shape under quota enforcement.

The replacement design should:
- use the OpenET public Earth Engine catalog directly
- avoid Google Drive entirely
- minimize Earth Engine task and request count
- cache reusable raster tiles in a deterministic fixed grid
- do merge, crop, and zonal statistics locally
- preserve the ability to generate the existing downstream WEPPpy OpenET summaries

## Current Repository Context
- The active OpenET path is [openet_ts.py](/workdir/wepppy/wepppy/nodb/mods/openet/openet_ts.py#L35), which calls Climate Engine per hillslope polygon.
- WEPPpy already has an older direct OpenET API helper in [openet_client.py](/workdir/wepppy/wepppy/locales/conus/openet/openet_client.py#L20), but it is not wired into the NoDb mod and is still polygon-request oriented.
- There is a small legacy Earth Engine webservice in [geeapi](/workdir/wepppy/wepppy/webservices/geeapi/__init__.py#L1), so using Earth Engine in-repo is not alien to the codebase.
- The gl-dashboard consumes `openet/openet_ts.parquet`, so the preferred backend keeps downstream contracts stable and changes the acquisition layer only.

## Goals
- Acquire monthly OpenET rasters from Earth Engine without Google Drive.
- Make Earth Engine calls scale with `months x datasets x tile-cache misses`, not with polygon count.
- Ensure duplicate raster requests are deduplicated by a stable tile key.
- Keep polygon clipping and zonal aggregation off Earth Engine.
- Support both lazy cache fill and optional bulk backfill.
- Make cost and quota control explicit with workload tagging and project-level EECU limits.

## Non-Goals
- No attempt to preserve Climate Engine as a primary path.
- No dependence on OpenET API quotas or OpenET Drive exports.
- No Earth Engine-side zonal stats for arbitrary user polygons in the normal path.
- No BigQuery requirement in the first version.

## Authoritative API Review
### OpenET data source
- OpenET explicitly recommends the Google Earth Engine public data catalog for very large extractions that exceed OpenET API quota limits.
- OpenET monthly datasets are available in the public catalog for Ensemble, eeMETRIC, SIMS, PT-JPL, SSEBop, DisALEXI, and geeSEBAL.
- The public Earth Engine path avoids OpenET API monthly query quotas entirely.

### Earth Engine processing modes
- Earth Engine has two relevant execution realms:
  - interactive: synchronous, quick responses, limited to small outputs and short runtime
  - batch: asynchronous exports to Cloud Storage or assets, intended for large workloads
- The high-volume interactive endpoint is for many simple automated requests, but Google documents that it has less intermediate caching and can consume more EECU for complex requests.
- Batch tasks can run for up to ten days and are the preferred path for large raster exports.

### Earth Engine extraction methods relevant here
- `Export.image.toCloudStorage()` is the primary batch mechanism for writing GeoTIFF or TFRecord output to GCS.
- `getPixels` fetches pixel blocks from an existing image asset.
- `computePixels` fetches pixel blocks from a computed image expression.
- Manual extraction with `getPixels` or `computePixels` can write to Cloud Storage or to a local directory via the client, but each request is capped.

### Earth Engine limits that directly affect design
- Default project limits currently include:
  - 40 concurrent standard interactive requests
  - 40 concurrent high-volume interactive requests
  - 100 requests per second
  - average 2 concurrent batch tasks by default, though commercial plans can increase this
  - 250 GB Earth Engine asset storage and 10,000 assets
- `getPixels` and `computePixels` requests are limited to:
  - 48 MB uncompressed response size
  - 32K pixels in either dimension
  - 1024 bands
- Large image exports are automatically split into multiple output files, with filenames suffixed as `baseFilename-yMin-xMin`.
- `Export.image.toCloudStorage()` supports:
  - `crs` and `crsTransform`
  - `shardSize`
  - `fileDimensions`
  - `skipEmptyTiles`
  - GeoTIFF `cloudOptimized`
  - GeoTIFF `noData`
  - task `priority`

### Earth Engine cost controls relevant here
- Earth Engine lets projects set a custom `earthengine.googleapis.com/daily_eecu_usage_time` quota to cap daily compute usage.
- Cloud Monitoring can alert on `workload_tag`, and Earth Engine tasks can be canceled programmatically based on EECU usage.

### Google Cloud Storage considerations
- Cloud Storage is the supported non-Drive export destination for Earth Engine batch raster export.
- Earth Engine documentation recommends US-CENTRAL bucket locations when optimizing for low-latency compute access to COG-backed assets.

## Core Design Decision
Use a hybrid Earth Engine backend:

1. **Primary acquisition path**
   - Batch export monthly OpenET raster images to Google Cloud Storage using deterministic fixed-grid tiling.

2. **Cache model**
   - Treat each output tile as a reusable artifact addressed by a stable tile key.

3. **Fallback path**
   - When a tile is missing and immediate retrieval is needed, fetch it directly with `computePixels` or `getPixels`, then store it under the same cache key.

4. **Local analytics**
   - Merge only the required cached tiles, crop locally, and run zonal statistics locally.

This keeps Earth Engine focused on raster extraction, not polygon analytics.

## Why This Shape Is More Durable
- Request count is tied to tile cache misses instead of polygon count.
- The same raster tile can serve many different watershed polygons, scenarios, or reruns.
- Large backfills can use batch exports, while rare misses can use direct extraction.
- Local merge/crop/zonal work is fully under WEPPpy control and can use the repo's preferred performance-oriented raster stack.

## Dataset Selection
### Initial datasets
- `OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0`
- `OpenET/EEMETRIC/CONUS/GRIDMET/MONTHLY/v2_0`

### Initial band selection
- Export ET band only.
- Do not export the `count` band in the first version.

Rationale:
- Current WEPPpy downstream use is ET, not observation-count diagnostics.
- Single-band export maximizes cache density and keeps interactive miss retrieval under the 48 MB ceiling for larger tiles.

## Grid Strategy
### Design principle
The tile grid must be:
- deterministic
- independent of run polygons
- aligned to a single raster projection and affine transform
- chosen once and versioned in metadata

### Projection choice
Preferred rule:
- Use the dataset's native projection and affine transform if it is stable across the collection.

Fallback:
- If native projection stability is not acceptable or operational tooling strongly prefers a common CONUS grid, use EPSG:5070 with an explicitly versioned affine transform.

Rationale:
- Using the native projection avoids Earth Engine reprojection work and avoids introducing resampling artifacts.
- A stable transform is more important than a human-friendly CRS label.

### Fixed tile size
Recommended initial tile size:
- `3328 x 3328` pixels

Rationale:
- Earth Engine interactive extraction is capped at 48 MB uncompressed.
- For one float32 band, the largest safe multiple of 256 below 48 MB is `3328` pixels:
  - `3328 * 3328 * 4 bytes = 44,302,336 bytes`
- This keeps the same logical grid usable by both:
  - batch exports via `fileDimensions`
  - interactive miss retrieval via `computePixels` or `getPixels`
- At 30 m resolution, each tile spans about `99.84 km x 99.84 km`.

### Tile origin
- Define a single affine transform and origin for the entire cache namespace.
- Never derive tile origin from an individual AOI.
- The tile grid spec is part of the cache key.

### Grid versioning
Every cache artifact must include a grid version string, for example:
- `openet-conus-v2_0-nativegrid-3328px-v1`

Changing CRS, transform, band set, nodata handling, or tile size creates a new grid version.

## Cache Key Design
### Tile key fields
- dataset key: `ensemble`, `eemetric`
- Earth Engine collection id
- dataset version: `v2_0`
- year
- month
- band id
- grid version
- tile column
- tile row
- file format
- nodata policy

### Suggested path layout
```text
gee-api/
  cache/
    openet/
      ensemble/
        v2_0/
          et_ensemble_mad/
            grid=openet-conus-v2_0-nativegrid-3328px-v1/
              year=2024/
                month=07/
                  tile_x=0012/
                    tile_y=0007.tif
      eemetric/
        v2_0/
          et/
            grid=openet-conus-v2_0-nativegrid-3328px-v1/
              year=2024/
                month=07/
                  tile_x=0012/
                    tile_y=0007.tif
```

### Manifest files
Maintain a manifest alongside tiles:
- `tile_manifest.parquet` or `tile_manifest.jsonl`

Each record should include:
- tile key
- GCS object path
- local cache path
- file size
- checksum
- source task id or request id
- Earth Engine workload tag
- export/create timestamp
- image date range metadata
- nodata value
- CRS and affine transform

## Acquisition Modes
### Mode A: Bulk monthly export to GCS
Use when:
- backfilling new months
- refreshing a whole AOI cache
- prewarming a known region

Mechanism:
- Select the monthly Earth Engine image.
- Export to GCS with `Export.image.toCloudStorage()`.
- Set:
  - `fileFormat='GeoTIFF'`
  - `formatOptions.cloudOptimized=true`
  - `fileDimensions=3328`
  - `shardSize=256`
  - `skipEmptyTiles=true`
  - explicit `crs` and `crsTransform`
  - explicit `maxPixels`
  - `priority` based on workload class

Important design choice:
- Prefer one export task per `(dataset, year, month, superregion)` rather than one task per tile.
- Let Earth Engine split the output into files internally.

Why:
- Far fewer API calls and task objects.
- Lower client orchestration overhead.
- Deterministic output filenames can still be mapped back to tile identities.

### Mode B: On-demand miss fill with `computePixels` or `getPixels`
Use when:
- a small number of tiles is missing
- immediate retrieval is preferable to queuing a batch export

Mechanism:
- Request exactly one deterministic tile extent matching the cache grid.
- Write returned bytes directly to local storage.
- Register the tile in the manifest.

Selection rule:
- Prefer `getPixels` if you already have a stable image asset reference.
- Prefer `computePixels` when selection logic depends on collection filtering or simple band selection from a computed expression.

Endpoint rule:
- Use standard endpoint for complex expressions.
- Use high-volume endpoint only for simple tile fetches that do not depend on expensive aggregations.

## Recommended Export Workflow
### Image selection
For each `(dataset, year, month)`:
- select the public OpenET image from the monthly collection
- select the ET band only
- cast output explicitly if needed so file size and nodata behavior are controlled

### Region selection
Two supported strategies:

1. **Lazy regional growth**
   - Compute the minimal set of grid cells intersecting requested polygons.
   - Expand to the aligned tile envelope.
   - Export only that superregion.

2. **Programmatic prewarming**
   - Export predefined large regions such as state packs, hydrologic regions, or a full CONUS envelope.

Default recommendation:
- start with lazy regional growth
- add prewarming only for known high-demand regions

### Nodata policy
- Unmask outside-image gaps to a fixed numeric nodata such as `-9999`
- set `formatOptions.noData`
- keep nodata policy versioned in the cache key

This makes local merge/crop/zonal logic predictable.

## Local Processing Contract
Once tiles are cached locally:
- merging is local only
- cropping is local only
- zonal statistics are local only

### Suggested local flow
1. Determine intersecting tile keys for the polygon set.
2. Materialize or verify local copies of those tiles.
3. Build a local VRT or equivalent lightweight mosaic index.
4. Crop to AOI bounding box or mask as needed.
5. Run zonal statistics using the local raster stack.
6. Persist summarized monthly ET outputs in the existing WEPPpy tabular contract.

### Why local zonal stats
- avoids repeated Earth Engine aggregation cost
- avoids Earth Engine concurrent aggregation limits
- lets one raster cache support arbitrary future polygon definitions
- improves reproducibility and debuggability

## API Efficiency Rules
### Required rules
- Never do per-polygon remote zonal stats in the steady-state pipeline.
- Never export ET and diagnostic bands together unless the diagnostics are actively used.
- Always use a deterministic grid and tile key.
- Always set `workloadTag` on direct extraction and batch jobs.
- Always set a project daily EECU limit.
- Always cache tile existence and checksum metadata.

### Preferred rules
- Prefer batch export for bulk month ingestion.
- Prefer direct pixel extraction only for sparse misses.
- Prefer dataset-native projection over reprojection.
- Prefer superregion export over per-tile export tasks.
- Prefer lazy cache growth over nationwide prefill unless demand justifies prewarming.

### Anti-patterns to avoid
- Per-run per-polygon Earth Engine reductions.
- Recomputing the same month tile because local metadata is missing.
- Using the high-volume endpoint for complex expressions or heavy aggregation.
- Letting output CRS drift per request.
- Using Google Drive as an intermediate transport.

## Monitoring, Cost, and Quota Controls
### Earth Engine controls
- Set `earthengine.googleapis.com/daily_eecu_usage_time` to a real ceiling.
- Use `workloadTag` values such as:
  - `openet-backfill`
  - `openet-cache-miss`
  - `openet-refresh`
- Use Cloud Monitoring alerts filtered by `workload_tag`.
- Add a watchdog that can cancel long-running expensive export operations.

### Operational metrics to collect
- cache hit rate by tile request
- batch export task success rate
- average EECU per exported month
- average EECU per cache miss
- GCS bytes written per month
- local cache bytes reused vs newly fetched
- number of polygons served per cached tile

## Proposed Backend Layout
```text
gee-api/
  openet-backend-specification.md
  cache/
  manifests/
  tmp/
  notebooks/
```

Future code modules can mirror this separation:
- catalog selection
- grid math
- task submission
- GCS sync
- local raster materialization
- zonal summarization

## Suggested Implementation Phases
### Phase 0: Validation spike
- authenticate with the billed project
- inspect native projection of representative monthly OpenET images
- confirm ET band names for Ensemble and eeMETRIC
- run one `computePixels` tile pull into a local file
- run one `Export.image.toCloudStorage()` monthly export with `fileDimensions=3328`
- confirm output naming, nodata, and COG readability

### Phase 1: Cache skeleton
- implement tile key generation
- implement manifest schema
- implement local and GCS existence checks
- implement lazy tile miss fill

### Phase 2: Batch export path
- implement month export submission
- implement task polling and reconciliation
- ingest exported GCS objects into the manifest

### Phase 3: Local analytics bridge
- merge needed tiles locally
- crop locally
- compute monthly polygon zonal values locally
- emit the existing WEPPpy monthly OpenET parquet contract

### Phase 4: Refresh and operations
- monthly refresh jobs
- provisional/final data refresh policy
- alerts and cost guardrails

## Open Questions
- Does the public OpenET collection use a single stable native projection and transform across all months and both datasets?
- Should the first implementation store only local tiles, or treat GCS as the durable source of truth and local disk as a read-through cache?
- Do we want a single shared tile cache for all runs, or run-scoped copies plus a shared immutable backing store?
- Is there any downstream need for the `count` band that would justify a second cache namespace?
- Should the first version support only `ensemble` and `eemetric`, or all OpenET monthly collections from day one?

## Recommended Initial Answers
- Use GCS as the durable remote cache and local disk as a read-through execution cache.
- Use a shared immutable tile cache, not run-scoped copies.
- Start with `ensemble` and `eemetric`.
- Export ET band only.
- Use lazy cache growth first.

## Sources Reviewed
- OpenET Earth Engine guidance: https://openet.gitbook.io/docs/additional-resources/earth-engine
- OpenET data availability: https://openet.gitbook.io/docs/additional-resources/data-availability
- OpenET quota page: https://openet.gitbook.io/docs/additional-resources/quota
- Earth Engine processing environments: https://developers.google.com/earth-engine/guides/processing_environments
- Earth Engine image data extraction: https://developers.google.com/earth-engine/guides/data_extraction
- Earth Engine quotas: https://developers.google.com/earth-engine/guides/usage
- Earth Engine cost controls: https://developers.google.com/earth-engine/guides/cost_controls
- Earth Engine image export guide: https://developers.google.com/earth-engine/guides/exporting_images
- `Export.image.toCloudStorage()` reference: https://developers.google.com/earth-engine/apidocs/export-image-tocloudstorage
- `projects.assets.getPixels` reference: https://developers.google.com/earth-engine/reference/rest/v1/projects.assets/getPixels
- `projects.image.computePixels` reference: https://developers.google.com/earth-engine/reference/rest/v1alpha/projects.image/computePixels
- Earth Engine pricing: https://cloud.google.com/earth-engine/pricing
- Earth Engine FAQ bucket-location guidance: https://developers.google.com/earth-engine/faq
- OpenET Ensemble monthly catalog page: https://developers.google.com/earth-engine/datasets/catalog/OpenET_ENSEMBLE_CONUS_GRIDMET_MONTHLY_v2_0
- OpenET eeMETRIC monthly catalog page: https://developers.google.com/earth-engine/datasets/catalog/OpenET_EEMETRIC_CONUS_GRIDMET_MONTHLY_v2_0
