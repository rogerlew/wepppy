# TerrainProcessor Concept

> Concept document for a configurable terrain processing DAG that is
> independent of `WhiteboxToolsTopazEmulator` while reusing the same
> working WhiteboxTools primitives (DEM parsing, flow stack derivation,
> outlet snapping, polygonization utilities). It handles LiDAR/10m DEMs,
> road embankment synthesis (implemented via `RaiseRoads` in
> `weppcloud-wbt`), culvert enforcement, bounded breach, and
> multi-watershed delineation. This document captures design intent and
> recommended approaches — not a binding implementation specification.

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

## Comparison with Culvert_web_app Hydroenforcement

The Culvert_web_app's hydroenforcement pipeline (in
`subroutine_nested_watershed_delineation.py`) is the closest existing
implementation to what TerrainProcessor aims to replace. Understanding its
limitations motivates the design decisions below.

### What Culvert_web_app does

Hydroenforcement is a single binary toggle ("Required" / "Not Required").
When enabled, it runs a monolithic 4-step sequence gated by the same
`hydro_enforcement_select == 'hydroenf_required'` conditional:

1. **Create breaklines** — perpendicular segments at road-stream
   intersections, extended by a fixed offset (default 10m).
2. **Fill roads** — `adjust_dem_along_polyline` raises the DEM by a
   uniform +5m within a 2m buffer around all road centerlines.
3. **Burn breaklines** — `adjust_dem_along_polyline` lowers the DEM by
   -10m within a 1m buffer along all breaklines.
4. **Breach depressions** — unconstrained `wbt.breach_depressions` with
   `max_depth=None, max_length=None, fill_pits=True`.

When disabled, the pipeline still runs `breach_depressions` on the raw
DEM — so it is not "no conditioning" vs "conditioning" but rather
"breach only" vs "road fill + breakline burn + breach."

### Shortcomings TerrainProcessor addresses

**No granularity.** The toggle is all-or-nothing. Users cannot enable
road embankment synthesis without breakline burning, or vice versa.
There is no way to choose breach strategy (fill, bounded breach,
least-cost breach) or to skip road filling on LiDAR DEMs where roads
are already represented. TerrainProcessor decomposes these into
independent, composable pipeline phases with separate configuration
for road synthesis (Phase 1), conditioning strategy (Phase 2), and
culvert enforcement (Phase 3).

**Uniform, terrain-unaware modification.** `adjust_dem_along_polyline`
applies the same +5m offset everywhere regardless of local terrain
context, road class, or whether the DEM already captures embankments.
Lindsay (2015) demonstrated that minimizing DEM modification is
critical — every modified cell corrupts slope, curvature, and
morphometric attributes. TerrainProcessor's `"profile_relative"`
strategy adapts to local terrain, only raises where needed, and tapers
to avoid the abrupt cliff edges that `adjust_dem_along_polyline` creates.

**Unconstrained breach.** The Culvert_web_app calls `breach_depressions`
with `max_depth=None, max_length=None` — no cost or distance limits.
Lindsay (2015) explicitly recommends cost-constrained breaching with
`BreachDepressionsLeastCost` and appropriate `dist` / `max_cost`
thresholds. On steep terrain, unconstrained breach carves through
ridgelines into adjacent basins. TerrainProcessor offers
`breach_least_cost` (Lindsay's recommended approach) and
`bounded_breach` (fill-first fence for basin boundary integrity).

**No resolution awareness.** The same pipeline runs on any DEM
resolution. LiDAR DEMs already contain road embankments and don't
need +5m fill (which doubles the embankment). 10m DEMs lack road
signatures entirely and need synthesis. 30m DEMs have scale mismatch
with vector hydrography that neither filling nor breakline burning
addresses — Lindsay (2016) showed `TopologicalBreachBurn` is needed at
that scale. TerrainProcessor selects resolution-appropriate defaults
and guides users toward the minimum-modification pipeline.

**Fixed burn depth.** Breakline burning uses a constant -10m regardless
of local stream bed elevation or road embankment height. Lindsay (2016)
recommends `BurnStreamsAtRoads`, which finds the local minimum elevation
in a corridor and lowers only the higher cells to match — no arbitrary
burn depth needed. This is the TerrainProcessor default for culvert
enforcement.

**Minimal user guidance.** The Culvert_web_app provides only three
sentences of guidance: "Required: Flat terrain where natural flow paths
are unclear / Not Required: Steep terrain with well-defined drainage
networks / Consider: Local topography and existing hydrologic
connectivity." There is no mention of DEM resolution, no quantitative
thresholds, and no reference to the tradeoffs between breach strategies.
TerrainProcessor's resolution-specific pipeline recommendations and
per-step visualization with diff overlays give users the information
they need to make informed decisions.

**No step-by-step visualization.** The Culvert_web_app runs the full
pipeline as a background job and shows only the final result.
TerrainProcessor produces visualization artifacts at every phase —
hillshade with slope colormap, diff overlays showing what each step
changed, detected embankment masks, stream networks before and after
culvert enforcement — so users can inspect intermediate results and
adjust parameters before proceeding.

## Design Intent

1. **Standalone tool, not embedded in the run pipeline.** TerrainProcessor
   is its own interface. Users build a processing pipeline, configure each
   step, execute it, and visually inspect results at each stage (hillshade
   with slope colormap, stream network overlay, watershed boundaries, road
   vectors). Once satisfied, they launch a WEPPcloud run or batch from
   the pipeline's output artifacts.
2. **Independent module, shared DNA.** TerrainProcessor is not a subclass
   of `WhiteboxToolsTopazEmulator` and is not framed as TOPAZ emulation.
   It reuses proven, low-level building blocks (WBT runner setup, DEM
   metadata parsing, common raster/vector utilities) through shared helper
   modules, not inheritance.
3. **Configuration over code paths.** A configuration object declares
   *what* the pipeline should do. The processor translates config into the
   correct step sequence.
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
7. **Config/runtime separation.** `TerrainConfig` stores user intent and
   reproducibility parameters; `TerrainProcessor` stores runtime state,
   resolved inputs, and generated artifacts.

## TerrainConfig (Exemplary)

The dataclass below is illustrative — it shows the configuration surface
the processor needs to expose, not a final API. Field names, groupings,
and defaults will evolve during implementation. The intent is to capture
the categories of decisions users need to make.

```
@dataclass
class TerrainConfig:
    # ── DEM Preprocessing ──────────────────────────────────────────
    smooth: bool = False
    smooth_algorithm: str = "feature_preserving"
        # "feature_preserving" – WBT FeaturePreservingSmoothing (default)
        # "gaussian"           – Gaussian smoothing
        # "mean"               – Mean/box filter smoothing
    smooth_filter_size: int = 11          # kernel for FeaturePreservingSmoothing
    smooth_max_diff: float = 0.5          # max elevation change threshold (m)

    # ── Road Embankment Synthesis ──────────────────────────────────
    roads_source: str | None = None       # "upload", "osm", None
    roads_path: str | None = None         # uploaded road vector path
    osm_highway_filter: tuple[str,...] = (  # passed to OSM roads module
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
    blc_dist_m: float | None = None      # max breach search distance (meters)
    blc_max_cost: float | None = None    # max cumulative breach cost (z-units)
    blc_fill: bool = True                # fill pits that exceed cost/distance limits
    bounded_breach_collar_m: float | None = None  # defaults to 10 * cellsize

    # ── Culvert Enforcement ────────────────────────────────────────
    enforce_culverts: bool = False       # LiDAR preset should set this True
    culvert_source: str = "auto_intersect"  # "auto_intersect", "upload_points"
    culvert_path: str | None = None      # uploaded culvert points (optional filter)
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

### TerrainConfig vs TerrainProcessor Attributes

`TerrainConfig` should contain only user-selected parameters that define
the intended processing behavior and must round-trip into NoDb for
reproducibility.

Examples that belong in `TerrainConfig`:
- Smoothing settings (`smooth`, `smooth_algorithm`, `smooth_filter_size`, `smooth_max_diff`)
- Road sourcing/synthesis settings (`roads_source`, `road_fill_strategy`, widths/margins)
- Conditioning settings (`conditioning`, `blc_dist_m`, `blc_max_cost`, `blc_fill`)
- Culvert enforcement settings (`enforce_culverts`, source/method, burn widths)
- Channel extraction and outlet-mode settings (`csa`, `mcl`, `outlet_mode`, `outlets`)

`TerrainProcessor` should own runtime/derived attributes that are not
part of user intent and may change during one run.

Examples that belong in `TerrainProcessor` state:
- Workspace/runtime handles (`wbt_wd`, logger, WBT runner instance)
- Derived DEM metadata (`cellsize`, `epsg`, transform, extents)
- Runtime pointers (`current_dem_path`, current phase, selected mask paths)
- Resolved inputs (`resolved_roads_path`, resolved culvert intersections)
- Artifact registry/index (`artifacts_by_phase`, created file paths)
- Execution telemetry (`provenance`, warnings, elapsed timings, diagnostics)
- Re-entry bookkeeping (which phases are invalidated by config deltas)

Rule of thumb: if changing a value should require re-running a phase and
must be persisted for audit/replay, it belongs in `TerrainConfig`; if the
value is discovered/produced while executing, it belongs in
`TerrainProcessor`.

## Pre-Implementation Helper Status (2026-03-05)

The helper-first pre-implementation package now ships reusable contracts in
`wepppy/topo/wbt/terrain_processor_helpers.py`:

- **Phase 1 (Flow-stack facade)**
  - `derive_flow_stack(...) -> FlowStackArtifacts`
  - Executes relief -> flow vector -> flow accumulation -> streams ->
    junctions -> stream polygonization, with explicit emulator contract
    validation and typed artifact-path return.
- **Phase 2 (Bounded breach)**
  - `resolve_bounded_breach_collar_pixels(...)`
  - `create_masked_dem(...)`
  - `run_bounded_breach_workflow(...) -> BoundedBreachArtifacts`
  - `create_bounded_breach_composite(...)`
  - Delivers collar sizing, interior-mask preparation, injected breach-run
    orchestration, and filled/breached compositing.
- **Phase 3 (Culvert prep + burn adapter)**
  - `extract_road_stream_intersections(...)`
  - `load_culvert_points(...)`
  - `snap_uploaded_culvert_points_to_crossings(...)`
  - `burn_streams_at_roads_adapter(...)`
  - Typed helper errors now provide machine-readable codes:
    `geometry_input_error`, `culvert_snap_error`,
    `burn_streams_at_roads_validation_error`.
- **Phase 4 (Multi-outlet + unnest parsing)**
  - `snap_outlets_to_streams(...)`
  - `build_outlet_feature_collection(...)`
  - `parse_unnest_basins_hierarchy_csv(...) -> list[BasinSummary]`
  - Parser accepts both conceptual and WBT-style hierarchy sidecars,
    including `outlet_id`/`parent_outlet_id` and `row`/`column`.
- **Phase 5 (Provenance + invalidation scaffolding)**
  - `ProvenanceEntry`
  - `TerrainArtifactRegistry`
  - `determine_invalidated_phases(...)`
  - Includes conservative unknown-key invalidation and explicit phase-order
    semantics.

## Runtime Implementation Status (2026-03-05)

The runtime package now ships in `wepppy/topo/wbt/terrain_processor.py`
with phase handlers aligned to this concept:

- `TerrainConfig` + strict config validation contracts.
- `TerrainProcessor.run()` + `rerun_with_config(...)` with config-delta
  invalidation and selective phase re-entry.
- Phase 1 orchestration for smoothing, roads-source resolution, and
  embankment synthesis (`RaiseRoads` seam).
- Phase 2 orchestration for fill/breach/breach-least-cost plus bounded
  breach composite flow.
- Breach-least-cost controls now pass through end-to-end:
  `blc_dist_m`, `blc_max_cost`, and `blc_fill` are validated and routed
  through helper/emulator contracts into WBT execution.
- Phase 3 culvert enforcement with mandatory second flow-stack pass.
- Phase 4 single/auto/multiple outlet resolution with hierarchy parsing.
- Phase 5 backend visualization artifact generation (hillshade, slope,
  phase diff rasters, benchmark report, and UI payload metadata contract),
  including raster-size guardrails for expensive workloads.
- Phase 6 invalidation report contract plus helper/runtime invalidation
  mapping evidence output.
- WEPPcloud watershed API surface now exposes terrain config/run/result
  routes and artifact URL serving for UI clients.

Targeted runtime validation now lives in
`tests/topo/test_terrain_processor_runtime.py`.

## Pipeline Phases (Conceptual)

### Phase 0: Validate and Prepare

- Assert DEM exists and is projected (UTM).
- If `roads_source == "osm"`, assert boundary polygon available for bbox query.
- If `roads_source == "upload"`, assert the roads vector has a defined CRS.
- If `enforce_culverts`, assert roads are available from Phase 1.
- If `culvert_source == "upload_points"`, assert file exists and contains point geometries.
- If `conditioning == "bounded_breach"` and `outlet_mode != "auto"`, ensure outlet
  info is available (auto mode can derive a preliminary outlet).
- If uploaded roads are not in DEM CRS (including WGS84 uploads), reproject
  roads to DEM CRS before synthesis (`RaiseRoads` path).

### Phase 1: DEM Preparation

Produces the "prepared DEM" that all downstream steps operate on.

```
raw DEM
  │
  ├─ [if smooth] ──→ _smooth_dem() ──→ dem_smoothed.tif
  │                                       │
  ├─ [if roads_source == "upload"] ──→ roads_utm.{geojson,shp}
  ├─ [if roads_source == "osm"]    ──→ osm_roads module (server-wide cache)
  │                                       ──→ roads_utm.{geojson,shp}
  │                              │
  │                    _synthesize_road_embankments() ──→ dem_roads.tif
  │
  └─ self._dem = latest prepared DEM artifact
```

Steps update `self._dem` so subsequent phases see the prepared version.
A `dem_provenance: list[dict[str, Any]]` tracks what was applied (for reproducibility
metadata in NoDb).

When `roads_source == "osm"`, road acquisition delegates to a separate
OSM roads module (not part of the TerrainProcessor itself). This module
maintains a server-wide persistent cache keyed by bbox + highway filter,
so repeated queries for the same area across different projects and users
hit the cache rather than Overpass. See "OSM Roads Module" below.

### Phase 2: Hydrologic Conditioning + Flow Stack

The flow stack subgraph (reusable, called once or twice):

```
_derive_flow_stack(dem_input, conditioning):
    _create_relief(dem_input)  → relief.tif
    _create_flow_vector()      → flovec.tif
    _create_flow_accumulation()→ floaccum.tif
    _extract_streams()         → netful.tif
    _identify_stream_junctions()→ chnjnt.tif
    polygonize_netful()        → netful.geojson
```

#### Conditioning strategies:

**`"fill"`** – `wbt.fill_depressions()`. Conservative. Won't carve through
ridgelines. Use when basin boundaries matter more than realistic drainage
paths. Lindsay (2015) notes that filling raises all cells within a
depression to the elevation of the outlet cell — on LiDAR DEMs with road
embankments, this floods entire valleys upstream of roads, losing all
surface drainage information within those areas.

**`"breach"`** – `wbt.breach_depressions(fill_pits=True)`. Aggressive.
Produces more realistic flow paths but can breach into adjacent basins on
high-relief terrain.

**`"breach_least_cost"`** – `wbt.breach_depressions_least_cost(dist=blc_dist_m)`.
Lindsay & Dhun (2015) least-cost path algorithm. The `dist` parameter
(`d_max` in the paper) controls maximum breach search distance. The paper's
examples are in grid cells (5, 50, 150, 750, 1500 cells); TerrainProcessor
stores `blc_dist_m` in meters for API consistency with existing WBT backend
contracts and converts internally as needed. Set `--max_cost` based on expected
maximum embankment height to prevent excessive trenching. Set `--fill true`
to resolve pits exceeding cost/distance thresholds.

On the Rondeau Bay 1m LiDAR dataset (940M cells), the least-cost breach
correctly resolved 87.7% of major embankment underpasses without any
ancillary culvert data (Lindsay 2015, Table 2). Minor culverts (ditch-
connecting) achieved 61.0%. The curved breach channels follow natural
stream courses, unlike straight-line trenching from other breach methods.

Key limitation: the search distance is spatial, not topographic — the
algorithm doesn't know about basin boundaries. On steep terrain where a
narrow ridgeline is closer (in grid cells) than the true outlet path,
breach can carve through into an adjacent basin.

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

Executes when `enforce_culverts` is true.

Lindsay (2016, p.667) recommends `BurnStreamsAtRoads` as the conservative
approach for LiDAR DEMs: burn only a short distance upstream/downstream of
road crossings, preserving the DEM's representation of drainage features
elsewhere. The tool finds the local minimum elevation in a corridor of
`width/2` cells upstream and downstream of each stream-road intersection,
then lowers all higher cells in that corridor to match — no arbitrary
burn depth needed.

The legacy breakline approach (Culvert_web_app) uses a constant burn
depth (-10m) along perpendicular breaklines. This is retained for cases
where `BurnStreamsAtRoads` produces undesirable results (e.g., when the
local minimum is itself an artifact), but `BurnStreamsAtRoads` should be
the default.

```
[if culvert_source == "auto_intersect"]
    _find_road_stream_intersections() → culvert_points.geojson
    (requires roads from Phase 1 and streams from Phase 2)

[if culvert_source == "upload_points"]
    _load_culvert_points() → culvert_points_upload.geojson
    _snap_culvert_points_to_stream_road_crossings() → culvert_points.geojson
    (uploaded points constrain which crossings are enforced)

[if culvert_method == "burn_streams_at_roads"]
    wbt.burn_streams_at_roads(
        dem=relief, streams=netful_vector,
        roads=roads_vector, width=culvert_road_width
    ) → relief_burned.tif

[if culvert_method == "breakline"]
    _create_breaklines()        → breaklines.geojson
    _burn_dem_along_breaklines() → relief_burned.tif

# Re-derive flow stack from burned relief
self._dem = relief_burned.tif
_derive_flow_stack(dem_input=self._dem, conditioning="breach_least_cost")
```

The re-derivation is the reason this is two-pass: the first flow stack
identifies where streams cross roads; the burn modifies the DEM at those
crossings; the second flow stack reflects the enforced drainage.

Following Lindsay (2015), the recommended post-burn conditioning is
`BreachDepressionsLeastCost` (not unconstrained `BreachDepressions`),
with `fill=true` to resolve remaining pits that exceed the cost/distance
thresholds.

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

### Guiding Principle: Minimize DEM Modification

Lindsay (2015) demonstrated that least-cost breaching modified 80% fewer
cells and produced 9x less volumetric DEM impact than depression filling
or stream burning on the Rondeau Bay 1m LiDAR dataset:

| Method | Cells modified | Volumetric impact |
|--------|---------------|-------------------|
| Least-cost breach | baseline | 6.2M m³ |
| Stream burn + fill | 81% more | 33.8M m³ |
| Depression fill | 86% more | 55.9M m³ |

Lindsay (2016, p.667) explicitly recommends a conservative approach for
LiDAR DEMs:

> "an alternative, conservative method, may be to only burn a LiDAR DEM
> for a short distance upstream/downstream of road crossings, with the
> intent of removing road embankments while preserving the DEM's
> representation of drainage features elsewhere."

Every cell modified by road embankment synthesis corrupts local slope,
curvature, and morphometric attributes used by downstream WEPP modeling.
The strategies below are ordered from least to most DEM modification.
Users should choose the minimum intervention that achieves hydrologic
connectivity.

### Recommended Pipelines by DEM Resolution

**LiDAR DEMs (1–3m): No road fill needed.**
Road embankments are already represented in the DEM. The problem is
missing culverts, not missing roads. Recommended pipeline:

1. (Optional) Smooth with `FeaturePreservingSmoothing` to reduce noise
   while retaining drainage features.
2. Enable culvert enforcement (`enforce_culverts=True`,
   `culvert_source="auto_intersect"` by default).
3. `BurnStreamsAtRoads(dem, streams, roads, width)` — localized,
   elevation-aware road-crossing enforcement using local minimum
   elevation. Only modifies cells at stream-road intersections.
4. `BreachDepressionsLeastCost(dem, dist, max_cost, fill=true)` —
   cost-constrained depression removal for remaining natural depressions.
   Lindsay (2015) recommends iterative runs with increasing `dist` in cells
   (e.g., 5, 50, 150, 750). TerrainProcessor stores `dist` in meters
   (`blc_dist_m`) and converts using cell size.

This replaces the Culvert_web_app's 4-step pipeline (create breaklines +
fill roads + burn breaklines + unconstrained breach) with two tool calls
that are spatially controlled and elevation-aware.

Use `EmbankmentMapping` (Van Nieuwenhuizen et al. 2021) in the
visualization layer to *detect* where the DEM already represents road
embankments — this helps users verify that the LiDAR captured the road
network before deciding whether additional modification is needed.

**10m DEMs: Road embankment synthesis required.**
Roads are below the grid resolution. Embankments must be synthesized
from road vectors (uploaded or fetched from OSM). Recommended pipeline:

1. Acquire road vectors (upload or OSM).
2. Synthesize embankments using `RaiseRoads --strategy=profile_relative`.
3. `BurnStreamsAtRoads` at known/detected culvert locations to maintain
   connectivity (`RaiseWalls --breach` remains a legacy fallback path).
4. `BreachDepressionsLeastCost` for remaining depressions.

**30m DEMs (future work): TopologicalBreachBurn.**
At coarser resolutions, scale mismatch between vector hydrography and
DEM becomes the dominant problem. Lindsay (2016) showed FillBurn Kappa
accuracy degraded from 0.953 (SRTM-1) to 0.490 (GTOPO-30), while
`TopologicalBreachBurn` maintained 0.952 to 0.921 across resolutions.
TopologicalBreachBurn uses Total Upstream Channel Length (TUCL) to prune
the vector network to match DEM resolution, then applies a modified
priority-flood that integrates flow direction assignment with
topology-preserving breach-burn. This is out of scope for initial
implementation but should be a follow-up for users working with
GMTED/SRTM-scale DEMs and mapped hydrography.

### Why `adjust_dem_along_polyline` Is Inadequate

The Culvert_web_app's `adjust_dem_along_polyline` applies a uniform
constant offset (+5m) within a fixed-width buffer (2m) around road
centerlines. This violates Lindsay's minimum-modification principle:

1. **Uniform constant offset.** Adding +5m everywhere ignores local
   terrain context. Roads in valleys need more raise than roads on
   ridges. A constant offset creates unrealistic spikes on ridgelines
   and insufficient barriers in valleys.
2. **Fixed buffer width.** All roads get the same buffer regardless of
   road class. A forest track and a highway get identical treatment.
3. **Abrupt edges.** The buffer boundary creates a vertical cliff in the
   DEM. Water routes along the cliff face rather than flowing naturally
   over or around the road.
4. **No awareness of existing road signature.** On LiDAR DEMs, roads
   already appear as embankments. The constant fill doubles the effect.
5. **No cross-section shape.** Real roads have crowns, shoulders, ditches.
   A flat +5m slab doesn't approximate this.
6. **Excessive modification.** Every cell under the buffer is altered by
   a fixed amount, destroying local slope and curvature attributes
   across the entire road network.

### Candidate Strategies

**`"constant"` (legacy compatibility)**
Uniform `+dy` within `buffer_width` of road centerline. Equivalent to
`adjust_dem_along_polyline(burn=False)`. Retain for backward compatibility
and simple cases. Highest DEM modification footprint.

**`"profile_relative"` (recommended for 10m DEMs)**
1. Rasterize road centerline (same vector-to-raster pattern as
   `RaiseWalls`).
2. Priority-flood expand outward to `road_width/2` (same pattern as
   `EmbankmentMapping`), tracking perpendicular distance from centerline.
3. At each cell, query local terrain maximum via `FixedRadiusSearch2D`
   within a search radius of 2x road width (infrastructure already
   exists in `EmbankmentMapping`).
4. Set the road surface elevation to `local_max + margin` (default 2m).
5. Taper the elevation adjustment over the buffer width using the
   distance field from the priority-flood. Cosine roll-off prevents
   the abrupt cliff that `adjust_dem_along_polyline` creates.
6. Only raise, never lower — if the DEM already exceeds the target
   (LiDAR captured embankment, or natural ridgeline), leave it alone.

This adapts to local terrain: roads in valleys get raised more, roads on
ridges get raised less. The taper prevents artificial flow channels along
buffer edges. Modifies fewer cells than `"constant"` because cells
already above the target are untouched.

Implemented status (`weppcloud-wbt`, `RaiseRoads`): this strategy now
exists as a shipped tool with:
- strategy selection (`constant`, `profile_relative`, `cross_section`)
- no-lowering guarantee (`output >= input` on valid cells)
- width/parameter fallback hierarchy and conservative unpaved-road defaults
- per-feature GeoJSON overrides for cross-section parameters
- CRS-aware road ingestion and auto-reprojection to DEM CRS

**`"cross_section"` (forest road inventories)**
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

Most physically realistic but requires parameters that are only available
from forest road inventories (ditch width/depth, surface type). Falls
back to `"profile_relative"` when cross-section attributes are absent.

For unpaved roads (for example `track`, `unclassified`, or roads tagged
`surface=gravel|dirt|unpaved`) the processor should use a reasonable
default cross-section template when full inventory attributes are missing
(shallow ditch, narrower crown/shoulders, conservative backslope), while
still allowing users to override parameters through uploaded road GeoJSON
attributes (for example `crown_width_m`, `ditch_depth_m`,
`shoulder_slope`, `backslope_angle_deg`).

`RaiseRoads` now implements this cross-section parameter override path and
unpaved-road conservative fallback.

### Road Width Resolution

When `road_buffer_width is None`, `RaiseRoads` resolves width from road
attributes in this priority order:
1. `road_width` or `width` attribute (meters)
2. OSM `highway` tag → lookup table (motorway: 12m, trunk: 10m, primary: 8m,
   secondary: 7m, tertiary: 6m, residential: 5m, track: 3m, unclassified: 4m)
3. Fall back to 5m default

### EmbankmentMapping for Visualization

The `EmbankmentMapping` tool (Van Nieuwenhuizen, Lindsay, DeVries 2021)
detects and maps existing road embankments in LiDAR DEMs using
morphometric region-growing from road centerlines. Parameters:
`min_road_width` (6m), `typical_width` (30m), `max_width` (60m),
`max_height` (2m), `spillout_slope` (4 deg).

In the TerrainProcessor this is a visualization-only tool, not a DEM
modifier. Run it on the input LiDAR DEM and overlay the detected
embankment mask on the hillshade. This lets users:
- Verify that the LiDAR captured road embankments before skipping
  road synthesis.
- Identify where embankments are partial or absent (e.g., recently
  graded roads, small forest tracks below detection threshold).
- Compare detected embankments against the road vector layer to spot
  missing roads.

## OSM Roads Module

Road acquisition from OpenStreetMap is a separate module from the
TerrainProcessor, shared across the WEPPcloud server. The
TerrainProcessor calls into it but does not own it. The implementation now
exists under `wepppy/topo/osm_roads/`, with the TerrainProcessor-facing seam
at `wepppy/topo/wbt/osm_roads_consumer.py::resolve_roads_source`.

**Server-wide hybrid persistent cache.** OSM Overpass queries are rate-limited
and slow for large extents. The module uses:

- PostgreSQL metadata + advisory-lock coordination (`osm_roads_cache` schema)
- `/wc1` file payloads (tile GeoParquet + request-level GeoJSON artifacts)

Requests are keyed deterministically using tile-cover hash + highway-filter
hash. For each request:

1. Read request/tile metadata from PostgreSQL.
2. On cache hit, reuse payloads and return clipped/reprojected output.
3. On miss/stale, acquire per-key advisory lock, fetch from Overpass, persist
   payload + metadata, and return.
4. On upstream failure, apply bounded stale/expired fallback policy when
   configured.

**Separation of concerns.** The module handles Overpass query construction,
retry/backoff, response normalization, cache policy, and artifact generation.
TerrainProcessor receives a road artifact path and does not care whether the
source was upload, cache hit, or fresh Overpass fetch.

**Deployment requirement (forest1 + production).** Before enabling
`roads_source="osm"` in terrain workflows, roll out PostgreSQL schema support
and runtime env config on both forest1 and production. Use:
`docs/work-packages/20260304_osm_roads_client_cache/artifacts/postgres_migration_setup.md`.
The key operational requirement is explicit `WEPPPY_OSM_ROADS_CACHE_DB_URL`
configuration and one-shot schema initialization (`PostgresMetadataStore.ensure_schema()`).

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
    # The collar defaults to 10 * cellsize unless overridden via
    # bounded_breach_collar_m.
    # It prevents edge artifacts from
    # breach trying to route flow off the masked edge.
    collar_px = round((bounded_breach_collar_m or (10 * cellsize)) / cellsize)
    collar_mask = dilate(boundary_mask, pixels=collar_px)
    masked_dem = where(collar_mask, prepared_dem, nodata)

    breached_interior = breach_depressions(masked_dem)

Step 3 – Composite:
    # Inside the boundary: use breached values.
    # Outside: use filled values (preserves ridgeline integrity).
    composite_dem = where(boundary_mask, breached_interior, filled_dem)

Step 4 – Final flow stack from composite:
    _derive_flow_stack(dem_input=composite_dem, conditioning="breach_least_cost")
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
| `embankment_mask.tif` | (LiDAR only) EmbankmentMapping detected embankments overlaid on hillshade; helps verify DEM already captures road network before deciding on synthesis |

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

All intermediate DEM TIFFs are retained (e.g., `dem_raw.tif`,
`dem_smoothed.tif`, `dem_roads.tif`, `relief.tif`, `relief_burned.tif`).
The backend also emits canonical phase-diff rasters for adjacent
DEM-modifying steps so UI consumers can render a stable, precomputed
diff contract without recomputing on the client. For DEM modification
steps (smooth, road fill, breach, culvert burn), the UI should offer a
toggle between:
- **Absolute view** — hillshade of the output DEM
- **Diff view** — color-ramped difference from the previous DEM
  (blue = lowered, red = raised, gray = unchanged)

Retaining intermediates also supports phase re-entry: when a user changes
a parameter and re-runs from an earlier phase, the processor can discard
only the artifacts downstream of that phase.

Phase re-entry should be dependency-driven: the processor tracks field-to-
phase dependencies and automatically computes the earliest invalidated
phase from config deltas (for example `csa`/`mcl` invalidates Phase 2+,
while road synthesis strategy changes invalidate Phase 1+).

This lets users immediately see if breach carved through a ridgeline,
if road fill created unrealistic spikes, or if smoothing removed a real
drainage feature.

## Provenance Tracking

TerrainProcessor maintains a `provenance: list[dict[str, Any]]` recording each
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

1. ~~**Smooth algorithm choice.**~~ Resolved: expose
   `smooth_algorithm` selections (`feature_preserving`, `gaussian`,
   `mean`) and default to `feature_preserving`
   (`FeaturePreservingSmoothing`).

2. ~~**OSM road fetch caching.**~~ Resolved: separate OSM roads module
   implemented at `wepppy/topo/osm_roads/` with PostgreSQL metadata/advisory
   locks + `/wc1` payload cache. Forest1/prod rollout requires the migration
   setup in `docs/work-packages/20260304_osm_roads_client_cache/artifacts/postgres_migration_setup.md`.

3. ~~**Bounded breach collar sizing.**~~ Resolved: expose
   `bounded_breach_collar_m` and default to `10 * cellsize` when unset.

4. ~~**Cross-section road profile parameters.**~~ Resolved: support
   GeoJSON road-attribute overrides for cross-section fields and use a
   reasonable unpaved-road default template when inventory attributes are
   incomplete; still fall back to `"profile_relative"` when cross-section
   mode is not feasible.

5. ~~**Phase re-entry granularity.**~~ Resolved: the processor tracks
   config-field dependencies and automatically determines the earliest
   re-entry phase from config deltas.

6. ~~**Diff raster generation.**~~ Resolved: keep all intermediate TIFFs
   and generate canonical adjacent-phase diff rasters in backend runtime.
   Intermediate DEM artifacts (`dem_raw.tif`, `dem_smoothed.tif`,
   `dem_roads.tif`, `relief.tif`, `relief_burned.tif`) are retained for
   re-entry semantics, while `phase*_diff.tif` outputs provide stable
   visualization contracts for UI consumers.

## References

Lindsay JB, Dhun K. 2015. Modelling surface drainage patterns in altered
landscapes using LiDAR. *International Journal of Geographical Information
Science* 29(3): 397–411. DOI: 10.1080/13658816.2014.975715

- Introduces the least-cost breaching algorithm (`BreachDepressionsLeastCost`).
- Key finding: breaching modified 80% fewer cells and produced 9x less
  volumetric impact than filling or stream burning.
- Recommended iterative `d_max` strategy (5, 50, 150, 750, 1500 cells).
- 87.7% accuracy on major embankment underpasses without culvert data.
- Basis for the `"breach_least_cost"` conditioning strategy and the
  guidance to prefer breach over fill for LiDAR DEMs.

Lindsay JB. 2016. The practice of DEM stream burning revisited. *Earth
Surface Processes and Landforms* 41(5): 658–668. DOI: 10.1002/esp.3888

- Introduces `TopologicalBreachBurn` for scale-insensitive stream enforcement.
- Introduces `BurnStreamsAtRoads` as a conservative LiDAR-specific alternative.
- Key finding: TopologicalBreachBurn maintained Kappa 0.952–0.921 across
  resolutions from SRTM-1 to GTOPO-30; FillBurn degraded from 0.953 to 0.490.
- Recommends burning LiDAR DEMs only at road crossings, preserving
  the DEM's representation of drainage features elsewhere.
- Basis for the `BurnStreamsAtRoads` default in Phase 3 and the
  `TopologicalBreachBurn` future work note for 30m DEMs.

Van Nieuwenhuizen N, Lindsay JB, DeVries B. 2021. Mapping and removing
road and railway embankments from fine-resolution LiDAR DEMs. *Remote
Sensing* 13(7): 1308.

- Introduces `EmbankmentMapping` — region-growing embankment detection
  from road centerlines using morphometric constraints.
- Parameters: `min_road_width` (6m), `typical_width` (30m), `max_width`
  (60m), `max_height` (2m), `spillout_slope` (4 deg).
- Uses `FixedRadiusSearch2D` for IDW interpolation of terrain beneath
  detected embankments.
- Basis for the visualization-layer embankment detection and for the
  building blocks (priority-flood expansion, spatial queries) reused
  in the `"profile_relative"` road synthesis strategy.
