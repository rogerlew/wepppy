# Culvert Modeling

Culvert modeling in the current WEPPcloud ecosystem is a hydro-enforcement and batch-analysis workflow for engineered crossings. Use it when roads block or redirect drainage and you need the terrain-conditioning step to represent flow passing through known crossing locations instead of treating the road prism as an uninterrupted barrier.

## What This Is For

This workflow is for questions such as:

- Does a crossing change where flow leaves the road corridor?
- Does hydro-enforcement materially change watershed boundaries or outlet locations near engineered crossings?
- Which culvert catchments should move forward into WEPPcloud batch analysis?

It is not a culvert-sizing tool, a hydraulic-capacity calculator, or a structural safety certification workflow.

## The Current User-Facing Surface

The culvert workflow spans two user-facing surfaces:

1. the watershed delineation and hydro-enforcement form from the Culvert web app, where the user chooses hydro-conditioning behavior and prepares the batch inputs;
2. the WEPPcloud culvert batch API, where the prepared payload is submitted, retried, finalized, browsed, and downloaded.

The hydro-enforcement documentation available in this repo exposes the active form fields and defaults even though the original `ws_deln.html` template is not vendored here. The documented user-facing fields are:

| Documented form field | Purpose | Current default |
| --- | --- | --- |
| `hydroEnforcementSelect` | Turns hydro-enforcement on or off for the delineation branch | user choice required |
| `flowAccumThreshold` or `flowAccumThreshold_nohydro` | Stream extraction threshold | `100` |
| `pourPointSnapDistanceM` or `pourPointSnapDistanceM_nohydro` | Snap distance from pour point to road or intersection | `20` m |
| `filterWatershedMinAreaHa` or `filterWatershedMinAreaHa_nohydro` | Minimum watershed area retained | `2` ha |
| `flagWatershedAreaOutsideBoundaryHa` or `_nohydro` | Flag threshold for outside-boundary drainage area | `0.5` ha |
| `roadFillDemByM` | Amount added to the DEM along roads | `5` m |
| `roadFillDemBufferM` | Buffer width used for road fill | `2` m |
| `breaklineOffsetM` | Breakline length/offset at crossings | `10` m |
| `breaklineBurnDemByM` | Amount burned into the DEM along breaklines | `10` m |
| `breaklineBurnDemBufferM` | Buffer width used for breakline burn | `1` m |

For traceability, the workflow also branches on the documented pour-point selection field `pourPointDataSelect`, with distinct logic for:

- `both` or `culvert`
- `pour_pt_NA`
- `gauging`

## What Hydro-Enforcement Actually Assumes

The core modeling assumption is that roads can block drainage unless the workflow creates a deliberate crossing path through or across the road barrier.

When hydro-enforcement is enabled in the `both` or `culvert` branch, the workflow does this:

1. snaps pour points to nearby roads,
2. creates breaklines from those snapped crossing locations,
3. raises the DEM along roads using `roadFillDemByM` and `roadFillDemBufferM`,
4. burns the DEM along breaklines using `breaklineBurnDemByM` and `breaklineBurnDemBufferM`,
5. breaches or fills remaining depressions,
6. recomputes D8 flow direction, flow accumulation, and streams,
7. snaps final pour points to road-stream intersections and delineates nested watersheds.

This means the conditioned DEM is not intended to reproduce the exact physical culvert barrel. It is building a routing surrogate:

- roads are treated as raised barriers,
- breaklines are treated as intentional openings or passage corridors,
- the final stream and watershed products depend on that edited terrain.

When hydro-enforcement is not enabled, those road-fill and breakline edits are skipped and the workflow conditions the clipped DEM directly. That usually preserves a more natural DEM-derived drainage pattern, but it can miss crossings the user knows should convey flow beneath the road.

## Conditioning Choices That Matter Most

### `hydroEnforcementSelect`

This is the most important choice in the workflow.

Use hydro-enforcement when:

- the road clearly interrupts drainage in the DEM,
- known culverts or engineered crossings should pass flow,
- watershed boundaries are sensitive to crossing placement.

Leave hydro-enforcement off when:

- the DEM already represents drainage credibly near the crossing,
- you are screening broad areas and do not want the extra assumptions introduced by road fill and breakline burn,
- you do not trust the crossing locations enough to modify the terrain.

### `flowAccumThreshold`

This threshold controls how much contributing area is needed before the workflow extracts a stream.

Higher thresholds usually produce fewer mapped channels. Lower thresholds usually produce denser stream networks. That choice affects:

- where road-stream intersections exist,
- which pour points can be snapped to those intersections,
- how many watersheds are eventually delineated.

### `pourPointSnapDistanceM`

This controls how far the workflow will move a pour point to connect it to the nearest road or road-stream intersection.

If the snap distance is too small, valid crossings may fail to connect. If it is too large, the workflow may connect a point to the wrong road or stream crossing.

### `filterWatershedMinAreaHa` and `flagWatershedAreaOutsideBoundaryHa`

These are screening controls, not hydro-conditioning controls.

Use them to:

- drop very small catchments that are likely noise or artifacts,
- flag watersheds whose drainage extends materially outside the analysis boundary.

They matter because culvert inventories often include many very small or awkwardly placed catchments that are not equally useful for WEPP-style follow-on analysis.

### `roadFill...` and `breakline...` controls

These fields are only relevant when hydro-enforcement is enabled.

They control the terrain edits directly:

- the `roadFill...` settings make the road more of a barrier,
- the `breakline...` settings define where that barrier is cut or burned open.

Use conservative values unless you have a reason not to. Large fill or burn adjustments can force routing behavior that looks precise but is really being driven by aggressive conditioning choices rather than source data quality.

## Important Branch Differences

The workflow does not use the same conditioning sequence in every branch.

### `both` or `culvert`

This is the most complete engineered-crossing workflow in the current documentation.

With hydro-enforcement enabled, it includes both:

- road fill,
- breakline burn.

This is the best fit when the crossing is explicitly tied to a road and culvert-style passage is the point of the analysis.

### `pour_pt_NA`

This branch runs a baseline flow stack first and, if hydro-enforcement is required, applies road fill and breakline burn afterward and recomputes the flow products.

Use this mental model: the workflow first learns the untreated drainage structure, then edits it around road-stream intersections.

### `gauging`

This branch is different in an important way: the documented implementation burns breaklines but does not include the road-fill step used in the `both` or `culvert` branch.

That means the conditioned terrain assumption is not the same as the main culvert branch. If you compare results across branches, do not assume the only difference is the point type.

## Workflow Assumptions Near Engineered Crossings

The current workflow assumes:

- crossing locations are accurate enough to snap to roads and intersections,
- the DEM and road network align spatially,
- road width is known from uploaded `road_width`, inferred from OSM road class, or allowed to fall back to `10.0`,
- a crossing can be represented adequately by raised-road and burned-breakline terrain edits,
- nested watersheds are the correct conceptual output for WEPPcloud batch analysis.

It does not automatically know:

- whether the culvert is blocked,
- whether inlet or outlet conditions are damaged,
- whether hydraulic capacity is sufficient for a design storm,
- whether the road prism or channel geometry has changed since the source data were created.

## The WEPPcloud Batch Actions You Trigger

After the watershed delineation and conditioning step produces the required files, the WEPPcloud-facing actions are API-backed and explicit.

### Submit a batch

`POST /rq-engine/api/culverts-wepp-batch/`

This upload expects a `payload.zip` containing:

- `topo/breached_filled_DEM_UTM.tif`
- `topo/streams.tif`
- `culverts/culvert_points.geojson`
- `culverts/watersheds.geojson`
- `metadata.json`
- `model-parameters.json`

The response returns:

- `job_id`
- `culvert_batch_uuid`
- `status_url`
- `browse_token`
- `browse_token_expires_at`

That is the handoff from terrain-conditioned culvert prep into WEPPcloud batch processing.

### Retry one point

`POST /rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}`

Use this when one culvert needs to be rerun without resubmitting the entire batch.

### Finalize the batch

`POST /rq-engine/api/culverts-wepp-batch/{batch_uuid}/finalize`

Use this to rebuild the batch-level rollup artifacts after retry or repair work.

### Browse and download

Use the returned `browse_token` to access:

- `/weppcloud/culverts/{batch_uuid}/browse/*`
- `/weppcloud/culverts/{batch_uuid}/download/{subpath}`

This is how users inspect the generated run skeletons and other batch artifacts after submission.

## Data Contracts That Matter To End Users

The most important culvert payload rules are:

- all payload layers must use the same projected UTM CRS,
- both `culvert_points.geojson` and `watersheds.geojson` must carry `Point_ID`,
- `Point_ID` values must be non-empty, valid, and consistent across both files,
- the payload must include nested watershed polygons that correspond to the prepared culvert points.

If these contracts are wrong, the batch fails early or specific culvert runs are skipped.

## Interpreting Results

The first question is not "did the model finish?" It is "did hydro-enforcement create a more defensible drainage path near the crossing?"

Start by checking whether the conditioned outputs show:

- plausible road-stream intersections,
- pour points snapped where you expect,
- watershed polygons that make sense relative to the crossing,
- no obvious over-conditioning caused by aggressive fill or burn values.

Then interpret the WEPPcloud batch results as crossing-centered watershed scenarios. Those results are only as meaningful as the conditioned watershed geometry that produced them.

## Assumptions And Limits

- Hydro-enforcement is a terrain-conditioning approximation, not a direct culvert hydraulics model.
- Results are sensitive to crossing location, road geometry, DEM quality, and the conditioning parameters.
- The `gauging` branch does not currently use the same road-fill logic as the main `both` or `culvert` branch.
- If no road layer is uploaded, the workflow may use OSM roads instead, which can be good enough for screening but weak for site-specific decisions.
- Nested watershed and `Point_ID` consistency are required for reliable WEPPcloud batch processing.
- Conditioned drainage paths should still be checked against site knowledge before using them for design, permitting, or safety-critical decisions.

## Related Docs

- [Roads](../roads/ENDUSER.md)
- [WEPP](../wepp/ENDUSER.md)
- [Culvert Web App Hydroenforcement](../../../vendor/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md)
