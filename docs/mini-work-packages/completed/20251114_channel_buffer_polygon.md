# Mini Work Package: Channel Buffer Polygon Stamp for HEC-RAS Mesh Prep

**Status:** Completed  
**Last Updated:** 2025-11-15  
**Primary Areas:** `wepppy/rq/wepp_rq.py`, `wepppy/wepp/interchange/hec_ras_boundary.py`, `watershed/channels.parquet`, `Watershed.subwta`, `export/dss/*`

---

## Objective
Automate the creation of a floodplain/flow-area polygon that HEC-RAS can ingest directly when building a 2D mesh. The polygon should safely envelop each selected WEPP channel, respect stream order so trunk channels receive wider buffers, and export purely as GML (HEC-RAS-native) accompanied by a debug raster.

## Background
- `_write_dss_channel_geojson` already knows which channel Topo IDs are participating in the DSS export and invokes `build_boundary_condition_features` to emit orthogonal cut lines.
- Field guidance (see colleague write-up) expects users to sketch or buffer channels in QGIS before running WEPPcloud. We can spare them this manual GIS step by rasterizing a buffered floodplain inside the DSS export pipeline.
- Inputs we already have per run:
  - `Watershed.subwta` (Topaz ID raster) and `Watershed.relief` (smoothed DEM) from the watershed build.
  - `watershed/channels.parquet` containing per-channel attributes keyed by `topaz_id` (use `topaz_id` for lookups; `chn_enum` is just a per-run WEPP index and not stream order).
  - Channel polylines (`wat/geojson/channels.geojson` aka `channels_shp`) used for DSS channel GeoJSON.

## Functional Targets
- Provide a dedicated `_write_hec_buffer_gml(watershed, channel_ids, boundary_width_m)` helper that can be invoked from `_write_dss_channel_geojson` but also reused elsewhere.
- Generate an in-memory raster the same shape, geotransform, and CRS as `relief.tif` / `RELIEF.ARC`.
- For every channel ID targeted by the DSS export (or all channels when no filter is applied), walk the ordered list of pixels along the channel network and stamp an oriented elliptical kernel (dense stamping—every pixel) whose diameter scales with stream order.
- Accumulate all kernels into a single-valued raster mask, apply a dilation-led smoothing flow to avoid jagged pixel edges, and convert the final mask into:
  - `export/dss/ras/channel_buffer_raster.tif` (debug + provenance, 8-bit mask where 0 = dry, 255 = buffered).
  - `export/dss/channel_buffer.gml` (single polygon feature expressed in EPSG:4326; we skip GeoJSON/SHP completely because HEC-RAS already consumes GML).
- Embed the GML reference into DSS metadata (`metadata["floodplain_polygon"]="export/dss/channel_buffer.gml"`) so the UI can surface a download link.
- Ensure artifacts are regenerated whenever `_write_dss_channel_geojson` (or any future caller) runs so buffers stay in sync with the selected channel set.
- Surface a `width_multiplier` (or similar) keyword argument on `_write_hec_buffer_gml` so advanced callers can tweak the kernel widths without editing global constants.

## Proposed Workflow

### 1. Inputs & Pre-flight
1. Resolve `Watershed.getInstance(wd)` inside `_write_dss_channel_geojson`.
2. Assert `subwta`, `relief`, and `watershed/channels.parquet` exist. Bail gracefully (log + skip polygon) if any inputs are unavailable.
3. Load `subwta` as `np.int32`, `relief` as `np.float64`, and capture the GDAL transform + projection from `relief` (ensures the raster blank we create matches the mesh terrain).
4. Read `watershed/channels.parquet` via `pyarrow`/`pandas` extracting at least `topaz_id`, `wepp_id`, and whatever stream-order column we store (e.g., `stream_order` or `order`). Use `topaz_id` as the lookup key; never rely on `chn_enum` because it simply enumerates WEPP channels starting at 1.

### 2. Raster Staging
1. Allocate a zeroed `np.int32` raster (`buffer_accum`) matching `relief.shape`; each kernel write just adds `1` to the covered pixels.
2. Keep kernel sizing in pixel units: convert each stream-order diameter from meters → pixels once using `width_px = width_m / cellsize` and store that value (no repeated conversions).
3. Precompute the mapping from stream order to kernel width in meters (still defaulting to 30/60/90/120 m) then convert to pixels while building kernels.
4. For each unique width, build a normalized elliptical kernel mask whose:
   - Major axis = requested width in pixels (full diameter), applied perpendicular to the flow direction.
   - Minor axis = `max(1 px, 0.4 * major_axis)` to keep longer ellipses from becoming lines.
   - Resolution = ceil(width_px) so the kernel spans at least one pixel beyond the target width.
   Cache these kernels so stamping becomes a fast `buffer_accum[row0:row1, col0:col1] += kernel`.

### 3. Channel Traversal & Kernel Stamping
1. Expand the channel list to include every downstream Topo ID until the watershed outlet so buffers stay contiguous even when the user picks a subset.
2. For each channel Topo ID (sorted, honoring filters + downstream expansion):
   - Reuse `_build_boundary_line` helpers from `wepppy/wepp/interchange/hec_ras_boundary.py` (or extract shared utilities) to obtain the ordered list of unique raster pixels from downstream to upstream. Make it explicit that stamping starts at the **third-lowest pixel** (same anchor used for boundary lines) and proceeds upstream, because that pixel approximates the boundary-condition target point.
   - Determine a local tangent vector at each pixel by differencing adjacent ordered pixels. Degenerate vectors fall back to the channel polyline direction from `channels_shp` (sample the segment nearest to the pixel centroid).
   - Retrieve that channel’s stream order via the `topaz_id` lookup to choose the kernel size (fallback to default width when the column is missing).
2. Walk the ordered pixels and **stamp densely** (no skipping) so narrow reaches still receive coverage.
   - Align the kernel orientation so the ellipse’s major axis is perpendicular to the tangent vector (same orientation we use for boundary lines). The tangent unit vector `v=(dx, dy)` yields the perpendicular `n=(-v_y, v_x)`. Construct a 2×2 rotation matrix to rotate the cached axis-aligned kernel into world space.
3. Clip stamps to raster bounds and add them into `buffer_accum`. Because the array is `int32`, we simply increment counts and postpone any clamping/thresholding until stamping finishes.

### 4. Anti-Jagging & Vectorization
To avoid single-cell stair-steps around bends while keeping the flow simple:
1. After all channels stamp, threshold once: `buffer_mask = buffer_accum > 0`.
2. Apply a morphological **dilation** pass to `buffer_mask` using a circular structuring element sized to one cell radius; optionally follow with a single erosion to trim spikes if needed. This keeps the implementation simple and still smooths seams between kernels.
3. Convert the resulting binary mask to vector polygons using `rasterio.features.shapes`, but feed a **center-shifted transform** (`center_transform = transform * Affine.translation(0.5, 0.5)`) so the coordinates represent pixel centers instead of pixel edges.
4. Dissolve all parts into a single polygon, transform coordinates to EPSG:4326 via `GeoTransformer`, and emit them straight into a `channel_buffer.gml`.
5. Because we only target GML, we can skip the extra generalization buffer passes for now; add them later only if QA flags jagged artifacts.

### 5. Outputs & Metadata
1. Persist `channel_buffer_raster.tif` as an 8-bit mask: take the dilated boolean, cast to `uint8`, multiply by 255, and store metadata such as runid, creation timestamp, kernel mapping (in pixels), and the downstream-expansion flag.
2. Write `channel_buffer.gml` (single `Polygon`/`MultiPolygon` feature) with properties:
  - `selected_topaz_ids`, `downstream_topaz_ids`, `stream_order_counts`, `kernel_width_rules`, `generated_at`.
   - `source_crs` so consumers know the raster CRS before transformation.
3. Update `_write_dss_channel_geojson` to reference the new GML path and publish a `StatusMessenger` update (`"building hec-ras floodplain buffer…"`) while `_write_hec_buffer_gml` runs.

## Kernel Width Reference (initial mapping)
| Stream Order (`chn_enum`) | Width (full diameter) | Notes |
| --- | --- | --- |
| 1 | 30 m | Small headwater buffers, roughly 15 m beyond each bank. |
| 2 | 60 m | Captures moderate tributaries and debris fans. |
| 3 | 90 m | Medium channels, default for most mid-watershed reaches. |
| ≥4 | 120 m | Main stem, ensures high flows stay inside the polygon. |

The mapping should be centralized (e.g., `HEC_RAS_ORDER_WIDTH = {1: 30.0, 2: 60.0, 3: 90.0, "default": 120.0}`) and surfaced via `wepppy/config/hec_ras.py` later so operators can tune it per basin if needed.

## “Nice Boundary” Strategies
1. **Dilation-only baseline (MVP).** Single dilation step provides acceptable smoothing with minimal complexity—aligned with the “keep it simple” direction; if we ever outgrow it we can revisit more advanced smoothing or port the raster stamping to Rust.
2. **Raster-first smoothing (upgrade).** If dilation proves insufficient, layer on a Gaussian blur + threshold but only after sizing benchmarks confirm the performance hit is manageable.
3. **Vector buffer refinement (future).** Optional buffer-in/buffer-out trick if QA still spots jagged edges once dilation is deployed.

## Integration Points
- Extend `_write_dss_channel_geojson` with a helper (`_write_hec_buffer_gml(...)`) that receives the same `watershed`, `channel_ids`, and `boundary_width_m`. This keeps export orchestration in one place and ensures we only read `subwta`/`relief` once per RQ job.
    - Consider housing the heavy lifting inside `wepppy/wepp/interchange/hec_ras_buffer.py` so both the RQ path and future CLI utilities can reuse it.
    - Add the GML + debug raster to the DSS zip bundle (inside `archive_dss_export_zip`) so users downloading the export automatically receive the buffer artifacts.
- Document the new artifact in `docs/mini-work-packages/completed/20251113_hec_ras_boundary_gml.md` once implemented so boundary lines + buffer polygon share the same spec lineage.

## Open Questions & Concerns
- **Stream order lookup:** validate which column in `watershed/channels.parquet` actually stores stream order per `topaz_id`. If absent, fall back to drainage area bins. `chn_enum` must not be used.
- **Performance:** dense stamping might add seconds on massive basins; if the Python path becomes a bottleneck we can port the kernel walker to Rust without redesigning the algorithm.
- **Overlapping buffers:** the int32 accumulator avoids clamping per stamp; we just increment and threshold once after stamping, which keeps the implementation trivial even for braided reaches.
- **User configurability:** accept a `width_multiplier` (or similar) kwarg on `_write_hec_buffer_gml` so callers can experiment. Full UI controls can land later.
- **QA hooks:** no special preview artifacts today—the browse service will eventually gain generalized GML preview support if hydrologists need a richer visualization.

Delivering this spec clears the path to implement the raster stamping helper and wire it into the DSS export flow without blocking on UI changes.

## Outcome
- `_write_hec_buffer_gml` now generates `export/dss/channel_buffer.gml` plus `export/dss/ras/channel_buffer_raster.tif` automatically during `_write_dss_channel_geojson`. Boundary channels stamp downstream-only while downstream traces fill the rest of the network.
- The raster pipeline stamps dense elliptical kernels, performs a 3-pixel dilation, fills 4-neighbor holes, and then converts the mask to smooth polygons via `skimage.measure.find_contours`. This produces sub-pixel boundary curves without post-buffering artifacts.
- Buffer metadata (selected IDs, downstream IDs, width rules, multiplier, raster cell size) is embedded in `dss_channels.geojson["metadata"]["channel_buffer"]` along with a `floodplain_polygon` pointer for UI download links.
- The new contour step relies on `scikit-image==0.24.0`, now baked into the Docker image via `docker/requirements-uv.txt`.

## Verification
Ran the DSS export helper for the reference run to ensure the raster + GML emit correctly and look smooth in GIS previews:

```bash
./wctl/wctl.sh run-python <<'PY'
from wepppy.rq.wepp_rq import _write_dss_channel_geojson
_write_dss_channel_geojson('/wc1/runs/si/sizzling-hap', None)
PY
```

This regenerated `export/dss/channel_buffer.gml` + `ras/channel_buffer_raster.tif` for `sizzling-hap`, confirming the contour-based workflow behaves in a real run directory.

## Follow-ups
- Surface the buffer download link and preview inside the WEPPcloud UI once the browse service can render arbitrary GML.
- Monitor runtime on large basins; porting the stamping loop to Rust remains the primary option if DSS exports become noticeably slower. 
