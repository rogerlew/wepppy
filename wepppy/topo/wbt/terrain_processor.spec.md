# TerrainProcessor Spec

> High-level design for a configurable terrain processing DAG that extends
> `WhiteboxToolsTopazEmulator` to handle LiDAR/10m DEMs, road embankment
> synthesis, culvert enforcement, bounded breach, and multi-watershed
> delineation.

## Problem Statement

The current emulator hardcodes a single linear pipeline:
`relief → d8 → accum → streams → junctions → outlet → subcatchments`.
Real-world terrain processing requires conditional branches depending on
DEM resolution, available ancillary data, and user intent:

- **LiDAR DEMs** capture road embankments but need smoothing and may not
  resolve culverts.
- **10m DEMs** lack road signatures entirely; embankments must be
  synthesized from road vectors.
- **Breach depressions** can carve through ridgelines into adjacent basins.
  Users need a fill-first-then-breach-within-boundary option.
- **Culvert locations** may be known (uploaded) or unknown (rely on breach
  or BurnStreamsAtRoads).
- **Multiple outlets** require UnnestBasins and per-basin subcatchment
  delineation.

`adjust_dem_along_polyline` (Culvert_web_app) applies a uniform constant
offset within a fixed-width buffer. This is inadequate because it ignores
local terrain context, creates abrupt elevation discontinuities at buffer
edges, doesn't vary width with road class, and can double-stamp embankments
on LiDAR DEMs that already contain road signatures.

## Design Principles

1. **Standalone tool, not embedded in the run pipeline.** TerrainProcessor
   is its own interface. Users build a processing pipeline, configure each
   step, execute it, and visually inspect results at each stage (hillshade
   with slope colormap, stream network overlay, watershed boundaries, road
   vectors). Once satisfied, they launch a WEPPcloud run or batch from
   the pipeline's output artifacts.
2. **Extend, don't replace.** TerrainProcessor composes
   WhiteboxToolsTopazEmulator; the emulator's `@build_step` methods,
   artifact properties, and hook system remain the execution substrate.
3. **Configuration over code paths.** A single `TerrainConfig` dataclass
   declares *what* the pipeline should do. The processor translates config
   into the correct step sequence.
4. **File artifacts are the DAG edges.** Each step consumes named files and
   produces named files. The "current DEM" is a mutable pointer that
   successive preparation steps update in place.
5. **Two-pass is explicit.** When culvert burning requires re-deriving the
   flow stack, that's a second call to `_derive_flow_stack`, not hidden
   retry logic.
6. **Visualize before committing.** Every phase produces artifacts that
   the UI can render for inspection. Users don't proceed blind — they see
   what smoothing did, where roads were stamped, how breach changed flow
   paths, where outlets snapped to, and what the resulting basins look
   like before any WEPP run begins.

## TerrainConfig

```
@dataclass
class TerrainConfig:
    # ── DEM Preprocessing ──────────────────────────────────────────
    smooth: bool = False
    smooth_filter_size: int = 11          # kernel for FeaturePreservingSmoothing
    smooth_max_diff: float = 0.5          # max elevation change threshold (m)

    # ── Road Embankment Synthesis ──────────────────────────────────
    roads_source: str | None = None       # "upload", "osm", None
    roads_path: str | None = None         # uploaded road vector path
    osm_highway_filter: tuple[str,...] = (
        "motorway","trunk","primary","secondary",
        "tertiary","unclassified","residential","track",
    )

    # Road fill strategy (see Road Embankment Synthesis section)
    road_fill_strategy: str = "profile_relative"
        # "constant"          – legacy: uniform +dy everywhere
        # "profile_relative"  – raise to local ridgeline + margin
        # "cross_section"     – stamp a parametric cross-section
    road_fill_dy: float = 5.0            # meters (constant strategy)
    road_fill_margin: float = 2.0        # meters above local max (profile_relative)
    road_buffer_width: float | None = None  # None → read from road attributes

    # ── Hydrologic Conditioning ────────────────────────────────────
    conditioning: str = "breach"
        # "fill"               – fill only (conservative boundaries)
        # "breach"             – breach only (aggressive, can cross basins)
        # "breach_least_cost"  – breach with search distance limit
        # "bounded_breach"     – fill → boundary → breach within boundary
    blc_dist: int | None = None          # search distance for breach_least_cost

    # ── Culvert Enforcement ────────────────────────────────────────
    culvert_source: str | None = None    # "upload", "auto_intersect", None
    culvert_path: str | None = None      # uploaded culvert point/line vector
    culvert_method: str = "burn_streams_at_roads"
        # "burn_streams_at_roads" – WBT BurnStreamsAtRoads (Lindsay 2016)
        # "breakline"            – legacy perpendicular breakline burn
    culvert_road_width: float = 10.0     # BurnStreamsAtRoads width param (m)
    breakline_burn_dy: float = 10.0      # breakline burn depth (m)
    breakline_offset: float = 10.0       # breakline extension beyond road (m)
    breakline_buffer: float = 1.0        # breakline rasterization buffer (m)

    # ── Channel Extraction ─────────────────────────────────────────
    csa: float = 5.0                     # channel source area (ha)
    mcl: float = 60.0                    # minimum channel length (m)

    # ── Outlet / Watershed Mode ────────────────────────────────────
    outlet_mode: str = "single"
        # "single"    – one outlet, one watershed (existing behavior)
        # "multiple"  – list of outlets → UnnestBasins
        # "auto"      – FindOutlet with no requested location
    outlets: list[tuple[float,float]] | None = None  # (lng, lat) pairs
    snap_distance: float = 20.0          # outlet snap to stream (m)
```

## Pipeline Phases

### Phase 0: Validate and Prepare

- Assert DEM exists and is projected (UTM).
- If `roads_source == "osm"`, assert boundary polygon available for bbox query.
- If `culvert_source == "upload"`, assert file exists and contains point geometries.
- If `conditioning == "bounded_breach"`, ensure outlet info is available (need a
  preliminary boundary to constrain the breach).

### Phase 1: DEM Preparation

Produces the "prepared DEM" that all downstream steps operate on.

```
raw DEM
  │
  ├─ [if smooth] ──→ _smooth_dem() ──→ dem_smoothed.tif
  │                                       │
  ├─ [if roads_source] ──→ _acquire_roads() ──→ roads_utm.{geojson,shp}
  │                              │
  │                    _synthesize_road_embankments() ──→ dem_roads.tif
  │
  └─ self._dem = latest prepared DEM artifact
```

Steps update `self._dem` so subsequent phases see the prepared version.
A `dem_provenance: list[str]` tracks what was applied (for reproducibility
metadata in NoDb).

### Phase 2: Hydrologic Conditioning + Flow Stack

The flow stack subgraph (reusable, called once or twice):

```
_derive_flow_stack():
    _create_relief()           → relief.tif
    _create_flow_vector()      → flovec.tif
    _create_flow_accumulation()→ floaccum.tif
    _extract_streams()         → netful.tif
    _identify_stream_junctions()→ chnjnt.tif
    polygonize_netful()        → netful.geojson
```

#### Conditioning strategies:

**`"fill"`** – `wbt.fill_depressions()`. Conservative. Won't carve through
ridgelines. Use when basin boundaries matter more than realistic drainage
paths.

**`"breach"`** – `wbt.breach_depressions(fill_pits=True)`. Aggressive.
Produces more realistic flow paths but can breach into adjacent basins on
high-relief terrain.

**`"breach_least_cost"`** – `wbt.breach_depressions_least_cost(dist=blc_dist)`.
Middle ground. The search distance limits how far the breach can reach, but
the limit is spatial, not topographic — it doesn't know about basin
boundaries.

**`"bounded_breach"`** – Two-pass approach:
1. Fill depressions to get a conservative DEM.
2. Derive a preliminary flow stack from the filled DEM.
3. Determine the watershed boundary (using outlet or auto-detect).
4. Create a basin mask from the boundary.
5. Breach depressions on the *original* (pre-fill) prepared DEM.
6. Composite: use breached values inside the mask, filled values outside.
7. Re-derive the final flow stack from the composite.

This gives realistic internal drainage without breaching into neighboring
basins. The fill acts as a topographic fence.

### Phase 3: Culvert Enforcement (conditional, two-pass)

Only executes when `culvert_source is not None`.

```
[if culvert_source == "auto_intersect"]
    _find_road_stream_intersections() → culvert_points.geojson
    (requires roads from Phase 1 and streams from Phase 2)

[if culvert_method == "burn_streams_at_roads"]
    wbt.burn_streams_at_roads(
        dem=relief, streams=netful_vector,
        roads=culvert_vector, width=culvert_road_width
    ) → relief_burned.tif

[if culvert_method == "breakline"]
    _create_breaklines()        → breaklines.geojson
    _burn_dem_along_breaklines() → relief_burned.tif

# Re-derive flow stack from burned relief
_derive_flow_stack()
```

The re-derivation is the reason this is two-pass: the first flow stack
identifies where streams cross roads; the burn modifies the DEM at those
crossings; the second flow stack reflects the enforced drainage.

### Phase 4: Outlet Resolution

```
[if outlet_mode == "single"]
    set_outlet(lng, lat)  → outlet.geojson  (existing method)

[if outlet_mode == "auto"]
    set_outlet() with no requested coords → FindOutlet auto-detect

[if outlet_mode == "multiple"]
    _snap_outlets_to_streams()  → outlets_snapped.geojson
    _unnest_basins()            → unnested.tif + hierarchy.csv
    return basin_list           (caller handles fan-out)
```

### Phase 5: Review and Launch

The pipeline does NOT automatically proceed into subcatchment delineation
or WEPP runs. After Phase 4, the user has a fully processed terrain with
conditioned DEM, flow stack, stream network, and delineated basin(s). The
UI presents these for visual inspection.

The user then decides:
- Adjust parameters and re-run from an earlier phase.
- Accept results and launch a run or batch from the pipeline outputs.

Subcatchment delineation (`HillslopesTopaz`) happens as part of the
downstream WEPPcloud run, not inside the TerrainProcessor itself. The
processor's job ends at basin boundaries and stream networks.

## Road Embankment Synthesis Strategies

### Why `adjust_dem_along_polyline` Is Inadequate

1. **Uniform constant offset.** Adding +5m everywhere ignores that some
   road segments sit in valleys (where +5m is reasonable) and others sit
   on ridges (where +5m creates an unrealistic spike).
2. **Fixed buffer width.** All roads get the same buffer regardless of
   road class. A forest track and a highway get identical treatment.
3. **Abrupt edges.** The buffer boundary creates a vertical cliff in the
   DEM. Water routes along the cliff face rather than flowing naturally
   over or around the road.
4. **No awareness of existing road signature.** On LiDAR DEMs, roads
   already appear as embankments. The constant fill doubles the effect.
5. **No cross-section shape.** Real roads have crowns, shoulders, ditches.
   A flat +5m slab doesn't approximate this.

### Proposed Strategies

**`"constant"` (legacy compatibility)**
Uniform `+dy` within `buffer_width` of road centerline. Equivalent to
`adjust_dem_along_polyline(burn=False)`. Retain for backward compatibility
and simple cases.

**`"profile_relative"`**
1. Sample DEM elevations along the road centerline at regular intervals.
2. For each sample point, query the local terrain maximum within a
   search radius (e.g., 2x road width).
3. Set the road surface elevation to `local_max + margin` (default 2m).
4. Interpolate between sample points along the road.
5. Taper the elevation adjustment over the buffer width using a cosine
   roll-off so there's no abrupt cliff at the buffer edge.
6. Only raise, never lower — if the DEM already exceeds the target
   (LiDAR captured embankment), leave it alone.

This adapts to local terrain: roads in valleys get raised more, roads on
ridges get raised less. The taper prevents artificial flow channels along
buffer edges.

**`"cross_section"`**
1. Define a parametric road cross-section: crown width, shoulder width,
   shoulder slope, ditch depth, ditch width, backslope angle.
2. At each point along the road centerline, orient the cross-section
   perpendicular to the road direction.
3. Sample the existing DEM along the cross-section line.
4. Compute the target profile: road surface at `local_grade + crown_height`,
   shoulders tapering down, ditches at `surface - ditch_depth`, backslope
   reconnecting to natural terrain.
5. Stamp the target profile onto the DEM, taking the max of target and
   existing DEM (never excavate below existing grade, only build up).
6. Blend transitions between successive cross-sections.

Most physically realistic but requires more parameters. Appropriate when
road geometry data includes width, surface type, and ditch presence (e.g.,
forest road inventories).

### Road Width Resolution

When `road_buffer_width is None`, the processor attempts to read width
from road vector attributes in this priority order:
1. `road_width` or `width` attribute (meters)
2. OSM `highway` tag → lookup table (motorway: 12m, trunk: 10m, primary: 8m,
   secondary: 7m, tertiary: 6m, residential: 5m, track: 3m, unclassified: 4m)
3. Fall back to 5m default

## Bounded Breach Detail

The breach-into-adjacent-basins problem is particularly acute with LiDAR
DEMs on steep terrain where narrow ridgelines separate basins. Standard
breach will find the lowest-cost path through a ridgeline and carve a
channel into the neighboring basin, corrupting both the watershed boundary
and the flow accumulation.

### Algorithm

```
Input: prepared_dem, outlet (or auto-detect)

Step 1 – Conservative boundary via fill:
    filled_dem = fill_depressions(prepared_dem)
    d8_fill = d8_pointer(filled_dem)
    accum_fill = d8_flow_accumulation(d8_fill)
    streams_fill = extract_streams(accum_fill, threshold=csa)
    if outlet known:
        boundary_mask = watershed(d8_fill, outlet)
    else:
        outlet = find_outlet(d8_fill, streams_fill)
        boundary_mask = watershed(d8_fill, outlet)

Step 2 – Breach within boundary:
    # Mask the prepared DEM to the basin interior + a collar.
    # The collar (e.g., 10 pixels) prevents edge artifacts from
    # breach trying to route flow off the masked edge.
    collar_mask = dilate(boundary_mask, pixels=10)
    masked_dem = where(collar_mask, prepared_dem, nodata)

    breached_interior = breach_depressions(masked_dem)

Step 3 – Composite:
    # Inside the boundary: use breached values.
    # Outside: use filled values (preserves ridgeline integrity).
    composite_dem = where(boundary_mask, breached_interior, filled_dem)

Step 4 – Final flow stack from composite:
    _derive_flow_stack(composite_dem)
```

The collar prevents the breach algorithm from hitting the artificial nodata
boundary and creating false sinks. The composite preserves the fill-derived
ridgeline while allowing natural internal drainage.

### When to Use Bounded Breach

- LiDAR on steep terrain with narrow ridgelines
- When the user needs accurate basin boundaries AND realistic internal
  flow paths
- When `breach_least_cost` with a distance limit is insufficient (the
  ridgeline is close in XY but far in Z)

### When Not Needed

- Flat terrain (breach rarely crosses basin divides)
- 10m DEMs with synthesized road embankments (the embankments themselves
  act as topographic fences)
- Single-basin analysis where adjacent basin corruption doesn't matter

## Multi-Watershed Mode

Multi-watershed is always a precursor to batch or to starting a single
run from one of the delineated basins. It is not an inline feature of
the existing run pipeline — it lives in the TerrainProcessor interface.

When `outlet_mode == "multiple"`:

1. TerrainProcessor runs Phases 0–3 once (shared DEM prep, flow stack,
   optional culvert enforcement).
2. Snap each outlet to the stream network.
3. Call `wbt.unnest_basins()` → produces `unnested.tif` + `hierarchy.csv`.
4. Parse hierarchy CSV into a list of `Basin` objects, each with:
   - outlet pixel coords and snapped lng/lat
   - parent basin ID (for nesting)
   - boundary mask (extracted from unnested.tif)
   - area, stream order at outlet
5. Render all basins on the map for the user to inspect.

From here the user can:
- **Start a batch** — all basins (or a selected subset) become batch
  entries. Each basin's boundary, outlet, and the shared flow stack
  artifacts are the starting resources for the batch run.
- **Start a single run** — pick one basin from the map, launch a
  WEPPcloud run using that basin's boundary and outlet.
- **Adjust and re-run** — modify outlets, add/remove basins, change
  CSA/MCL, and re-execute from the appropriate phase.

The shared flow stack (DEM prep, relief, d8, accumulation, streams,
junctions) is computed once and reused across all basins. Only the
per-basin subcatchment delineation (`HillslopesTopaz`) runs per basin.

## Visualization Artifacts

Each phase produces artifacts the UI can render for step-by-step
inspection. The user sees what each processing step did before proceeding.

### Phase 1 outputs (DEM Preparation)

| Artifact | Visualization |
|----------|---------------|
| `dem_smoothed.tif` | Hillshade + slope colormap; diff overlay showing what smoothing changed |
| `roads_utm.geojson` | Road vectors colored by highway class, overlaid on hillshade |
| `dem_roads.tif` | Hillshade showing synthesized embankments; diff from pre-road DEM |

### Phase 2 outputs (Flow Stack)

| Artifact | Visualization |
|----------|---------------|
| `relief.tif` | Hillshade of conditioned DEM; diff from prepared DEM showing where breach/fill modified terrain |
| `flovec.tif` | Flow direction arrows (sampled at display resolution) |
| `floaccum.tif` | Log-scaled accumulation heatmap |
| `netful.geojson` | Stream network lines colored by Strahler order, overlaid on hillshade |
| `chnjnt.tif` | Junction points highlighted on stream network |

### Phase 2b outputs (Bounded Breach, when used)

| Artifact | Visualization |
|----------|---------------|
| `filled_dem.tif` | Hillshade of fill-only DEM (preliminary) |
| `boundary_preliminary.geojson` | Preliminary basin boundary from fill pass |
| `composite_dem.tif` | Final composite; color-coded to show which cells are breach-derived vs fill-derived |

### Phase 3 outputs (Culvert Enforcement)

| Artifact | Visualization |
|----------|---------------|
| `culvert_points.geojson` | Culvert locations on stream/road intersection map |
| `relief_burned.tif` | Hillshade diff showing where culvert burns modified the DEM |
| `netful.geojson` (v2) | Updated stream network after re-derivation; highlight changes from pre-burn network |

### Phase 4 outputs (Outlet Resolution)

| Artifact | Visualization |
|----------|---------------|
| `outlet.geojson` | Snapped outlet point on stream network |
| `bound.geojson` | Watershed boundary polygon overlaid on hillshade |
| `unnested.tif` + `hierarchy.csv` | Multiple basins color-coded by ID; nesting relationships shown |
| `outlets_snapped.geojson` | All snapped outlet points with snap distance indicators |

### Diff overlays

For DEM modification steps (smooth, road fill, breach, culvert burn), the
UI should offer a toggle between:
- **Absolute view** — hillshade of the output DEM
- **Diff view** — color-ramped difference from the previous DEM
  (blue = lowered, red = raised, gray = unchanged)

This lets users immediately see if breach carved through a ridgeline,
if road fill created unrealistic spikes, or if smoothing removed a real
drainage feature.

## Provenance Tracking

TerrainProcessor maintains a `provenance: list[dict]` recording each
mutation applied to the DEM:

```
[
  {"step": "smooth", "filter_size": 11, "artifact": "dem_smoothed.tif"},
  {"step": "road_fill", "strategy": "profile_relative", "source": "osm",
   "road_count": 47, "artifact": "dem_roads.tif"},
  {"step": "bounded_breach", "collar_px": 10, "artifact": "relief.tif"},
  {"step": "burn_culverts", "method": "burn_streams_at_roads",
   "culvert_count": 12, "artifact": "relief_burned.tif"},
]
```

This serializes into NoDb alongside the config and is available for
audit, reproducibility, and debugging.

## Open Questions

1. **Smooth algorithm choice.** WBT offers `FeaturePreservingSmoothing`
   (edge-preserving, good for LiDAR) and various Gaussian/mean filters.
   Should the config expose the algorithm or default to
   FeaturePreservingSmoothing?

2. **OSM road fetch caching.** Overpass queries are rate-limited. Should
   the processor cache downloaded roads in the working directory and skip
   re-fetch if the file exists?

3. **Bounded breach collar sizing.** The 10-pixel collar is a heuristic.
   Should this be a config parameter, or derived from DEM resolution
   (e.g., `collar_m / cellsize`)?

4. **Cross-section road profile parameters.** For the `"cross_section"`
   strategy, how much parameterization is appropriate? Forest road
   inventories may have ditch width/depth; OSM roads won't. Should this
   fall back to `"profile_relative"` when cross-section attributes are
   absent?

5. **BurnStreamsAtRoads vs breakline approach.** BurnStreamsAtRoads
   (Lindsay 2016) uses local minimum elevation and is more physically
   grounded. The legacy breakline approach uses constant burn depth. Should
   breakline be deprecated or retained for cases where BurnStreamsAtRoads
   produces undesirable results?

6. **Phase re-entry granularity.** When a user adjusts CSA/MCL after
   inspecting the stream network, only the flow stack needs re-derivation
   (Phase 2 onward). When they change the road fill strategy, everything
   from Phase 1 onward must re-run. Should the processor track which
   config fields changed and automatically determine the earliest phase
   to re-enter, or should the user explicitly choose?

7. **Diff raster generation.** Should the processor always produce diff
   TIFFs between successive DEM versions (adds disk I/O and storage), or
   should the UI compute diffs on-the-fly from the before/after artifacts?

8. **Road embankment strategy as Rust tool.** The `"profile_relative"`
   and `"cross_section"` strategies involve per-pixel DEM sampling and
   local neighborhood queries. These could be Python (rasterio + numpy)
   or a new WBT Rust tool for performance on large LiDAR DEMs. Which
   is the right starting point?
