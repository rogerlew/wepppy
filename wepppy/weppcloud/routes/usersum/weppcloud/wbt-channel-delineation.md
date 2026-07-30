# WBT Channel Delineation

Use the **Channel Delineation** control to define the terrain grid and build a
modeled channel network with the Weppcloud-WBT delineation backend. The extent,
critical source area, minimum channel length, pruning method, and depression
conditioning choice all affect where channels begin and which tributaries
remain in the network.

## What This Is For

Channel delineation converts a digital elevation model (DEM) into the drainage
network that WEPPcloud uses for outlet selection, subcatchment delineation, and
channel routing. The resulting channels are modeled features derived from
terrain; they are not surveyed or observed stream locations.

This page explains the inputs and options shown when a project uses the
Weppcloud-WBT backend. Projects configured for legacy TOPAZ delineation show
fewer options.

## When to Use It

Build channels after creating a project and before selecting an outlet or
delineating subcatchments. Return to this control when you need to:

- enlarge, reduce, or exactly reproduce the terrain grid;
- use a local GeoTIFF DEM;
- make the channel network denser or sparser;
- change how short headwater tributaries are removed; or
- test a different way of filling or breaching depressions in the DEM.

Rebuilding channels can change channel identifiers, flow paths, and the
available outlet locations. Repeat downstream delineation steps after a
rebuild.

## Before You Begin

Have the following ready:

- a project configured to use the Weppcloud-WBT delineation backend;
- an area of interest visible on the map, exact geographic bounds, a map object
  from another run, or an uploadable DEM; and
- a general expectation for channel density based on mapped hydrography,
  aerial imagery, or field knowledge.

The displayed defaults are the best starting point for most projects. Record
any nondefault settings when comparing runs.

## Choose the Terrain Extent

**Extent mode** determines the area and grid used to obtain or install the DEM.

| Extent mode | What to provide | When to use it | Important details |
| --- | --- | --- | --- |
| **Use map extent** | The current map view | Normal interactive setup | Pan and zoom until the area of interest is framed and **Build Channels** is enabled. |
| **Specify extent** | South, west, north, east bounds | You know the exact geographic limits | Enter four comma-separated decimal-degree coordinates in that order. |
| **Set Map Object** | `_map` JSON from another run's `ron.nodb` | You need the same grid as an earlier run | Reuses extent, center, zoom, Universal Transverse Mercator (UTM) zone, cell size, rows, and columns. |
| **Upload DEM** | A local GeoTIFF | You need to use your own elevation data | The upload establishes the extent, projection, cell size, and grid dimensions. |

### Manual extent

Enter bounds as:

```text
south, west, north, east
```

For example:

```text
44.16, -122.52, 44.23, -122.41
```

The values are latitude and longitude in decimal degrees. South must be less
than north, and west must be less than east.

### Set Map Object

Paste the complete `_map` JSON object from the source run's `ron.nodb`. This is
the preferred way to reproduce an existing grid exactly. Reusing the map
object does not copy the source run's channel thresholds or conditioning
choices; review the other settings before building.

### Upload DEM

The uploaded DEM must be:

- a GeoTIFF with a `.tif` extension;
- Float32 or Float64 elevation data;
- 2,560 by 2,560 pixels or smaller;
- tagged with a valid coordinate reference system;
- north-up, with no rotated grid axes; and
- made of square pixels with equal horizontal and vertical resolution.

A DEM already in UTM is used in its UTM grid. A DEM in another coordinate
reference system is reprojected to an appropriate UTM zone automatically.
Reprojection uses bilinear resampling and can slightly change elevation values.

Wait for the upload-success message and the current DEM filename before
clicking **Build Channels**.

## Set Channel Initiation and Length

The unit preference controls whether the form displays metric or US customary
units. WEPPcloud converts between the paired fields.

| Setting | Units | What it controls | Effect of increasing it |
| --- | --- | --- | --- |
| **Critical source area (CSA)** | hectares or acres | Minimum contributing area used to qualify a flow path as a channel | Channels generally begin farther downslope, producing fewer and shorter headwater branches. |
| **Minimum channel length (MCL)** | meters or feet | Minimum source-channel or branch length used during pruning | More short headwater tributaries are generally removed. |

Lower CSA and MCL values usually create a denser network. Higher values usually
create a sparser network. These parameters interact: changing one may alter
which branches are available for the other to retain or remove.

Do not assume that a visually detailed network is more accurate. Compare the
result with known drainage patterns and keep the DEM resolution in mind.

## Choose a Stream Pruning Method

The pruning method is applied after flow accumulation identifies potential
stream cells.

### Iterative First-Order Link Prune (IFOLP)

**Iterative First-Order Link Prune (IFOLP)** is the default WBT method. It uses
CSA to qualify channel cells and repeatedly evaluates first-order headwater
links against MCL. Iteration matters because removing one short tributary can
change the order and status of the remaining links.

Use IFOLP for new delineations and repeatable WBT workflows unless you need to
reproduce a run made with the legacy method.

### Remove Short Streams (Legacy)

**Remove Short Streams (Legacy)** first extracts a network from CSA and then
removes stream branches shorter than MCL. It is retained for compatibility
with earlier WEPPcloud-WBT results.

Use the legacy method when reproducing or comparing with an earlier run that
used it. Switching pruning methods can change headwater density and channel
identifiers even when CSA and MCL are unchanged.

## Choose a Depression Smoothing Algorithm

Real DEMs commonly contain pits, flats, road embankments, and other barriers
that interrupt modeled flow. The **Depression smoothing algorithm** conditions
the DEM before WEPPcloud calculates flow direction and extracts channels.

| Option | How it changes the DEM | When it is useful |
| --- | --- | --- |
| **Fill** | Raises every depression to its lowest recognized spill elevation and adds a small gradient across resulting flats | Cases where depressions are known artifacts and the required fill depths are acceptable |
| **Breach** | Uses Whitebox's legacy hybrid breach-first, fill-second method; cuts drainage paths with effectively unrestricted depth and length unless the caller supplies limits | Reproducing earlier WBT runs or testing whether an unrestricted breach can connect a large depression to lower terrain |
| **Breach (Least Cost)** | Searches within the configured distance for a path that minimizes excavation; WEPPcloud stops instead of filling depressions the bounded search cannot resolve | Useful for road embankments and other narrow barriers when unresolved depressions should require review |
| **Topaz Conditioning Algorithm** | Applies TOPAZ-compatible FILDEP filling and one- or two-cell obstruction adjustment, followed by RELIEF flat resolution | WEPP/TOPAZ-compatible workflows and projects calibrated around TOPAZ drainage behavior |

No conditioning method is universally best. Compare the resulting channels
with known drainage and inspect areas containing roads, reservoirs, quarries,
large flats, or DEM gaps. A conditioning choice can reroute flow even when CSA
and MCL remain unchanged.

**Fill** avoids excavating artificial channels, but it is not necessarily the
least disruptive option. A deep or extensive closed depression can be raised
to a distant saddle, producing a large flat or an implausibly deep fill. See
the WhiteboxTools manual entry for
[FillDepressions](https://jblindsay.github.io/wbt_book/available_tools/hydrological_analysis.html#filldepressions).

Despite its shorter name, **Breach** is not generally the faster or
lower-impact breaching option. Whitebox documents it as a legacy method that
often produces longer or deeper cuts and can be less efficient than
**Breach (Least Cost)**. Its unrestricted search may nevertheless find a
distant raster-edge outlet that a bounded least-cost search cannot reach. See
[BreachDepressions](https://jblindsay.github.io/wbt_book/available_tools/hydrological_analysis.html#breachdepressions)
and
[BreachDepressionsLeastCost](https://jblindsay.github.io/wbt_book/available_tools/hydrological_analysis.html#breachdepressionsleastcost).

**Topaz Conditioning Algorithm** is for numerical and workflow compatibility,
not a guarantee of the smallest terrain change. It can lower a qualifying
one- or two-cell obstruction, but wider obstructions and closed depressions are
filled. It also treats NoData next to valid terrain as an open lower boundary
and allows raster-edge cells to act as outlets. Consequently, changing the DEM
crop or NoData mask can turn a valley into an edge outlet—or enclose it—and can
substantially change the fill depth. Compare algorithms using the same aligned
DEM extent and NoData mask.

### Breach least cost distance

**Breach least cost distance** appears only for **Breach (Least Cost)**. It is
the maximum search distance, in meters, for finding a breach route. WEPPcloud
converts this distance to raster cells before calling WhiteboxTools.

- A larger distance allows the algorithm to search farther for a viable path,
  but can increase runtime and permit longer cuts.
- A smaller distance restricts the search near each depression, but may leave
  more depressions unresolved by breaching.
- WEPPcloud disables the tool's fill fallback and requires every depression to
  be resolved by the bounded search. If any remain unresolved, channel
  delineation stops before accepting the conditioned DEM.
- A larger search distance does not force drainage to the raster edge. The
  algorithm may select a nearer, lower-cost target instead.

Use the displayed default unless inspection shows that important barriers
cannot be resolved within that distance. If a plausible outlet lies farther
away, increase the distance and inspect the resulting breach. The value must
be greater than zero.

### If least-cost breaching cannot resolve a depression

The channel delineation summary reports the unresolved-depression count and
the selected search distance. WEPPcloud does not fill the remaining
depressions because a deep fill can substantially raise terrain and reroute
flow.

Retry only after choosing an appropriate correction:

- increase **Breach least cost distance** when the expected drainage target is
  farther away;
- enlarge or reposition the DEM extent so the expected outlet is represented;
- inspect the DEM crop and NoData mask for a closed or missing edge; or
- deliberately select another conditioning method when its terrain changes
  better match the modeling intent.

WEPPcloud does not choose one of these alternatives automatically.

## Build the Channels

1. Select an **Extent mode** and provide its required extent or DEM input.
2. Review **Critical source area** and **Minimum channel length**.
3. Select the **Stream Pruning Method**.
4. Select the **Depression smoothing algorithm**.
5. If using **Breach (Least Cost)**, review **Breach least cost distance**.
6. Click **Build Channels**.
7. Wait for the delineation job to complete and for the channel layer to
   appear on the map.
8. Inspect the network before selecting an outlet and delineating
   subcatchments.

Do not close the project based only on a submitted-job message. Wait for the
completion status and verify that the map contains the expected channel layer.

## Interpreting Results

Review the channel layer at both watershed and headwater scales.

- **Too many headwater channels** usually indicates that CSA or MCL is too low.
- **Missing headwater channels** usually indicates that CSA or MCL is too high.
- **Channels crossing ridges or bypassing visible valleys** can indicate DEM
  artifacts, an unsuitable conditioning choice, or incorrect uploaded-DEM
  georeferencing.
- **Large differences between pruning methods** are possible near confluences
  because IFOLP reevaluates the network after each pruning change.
- **Large differences between conditioning methods** indicate that pits,
  barriers, or flats materially control drainage in the selected DEM.

Channel density affects subcatchment size, channel routing length, and the
partitioning of hillslope and channel erosion. Treat threshold changes as
modeling decisions and document them when results support management or design
work.

## Assumptions and Limits

- Channels are derived from the DEM and parameter choices; they are not an
  observed stream inventory.
- DEM quality and resolution limit the precision of channel locations.
- CSA and MCL do not directly represent jurisdictional stream definitions,
  perennial-flow status, or field-mapped channel heads.
- Reprojecting an uploaded DEM can alter its grid and elevations slightly.
- Neither the extent nor conditioning options explicitly model culverts,
  subsurface drainage, or flow through bridges.
- Very small thresholds can create dense networks and longer processing times.
- The selected settings apply to the next build. Rebuilding may invalidate
  previously selected outlets and downstream delineation products.
- Field checks, mapped hydrography, or local expert review remain important for
  decision-critical applications.

## Troubleshooting

- **Build Channels is disabled** — for map extent, zoom in and establish a
  valid map view; for upload mode, wait for a successful DEM upload.
- **Manual extent is rejected** — enter exactly four numeric values in south,
  west, north, east order.
- **Map object is rejected** — copy the complete `_map` JSON object, including
  its extent, center, zoom, cell size, UTM information, rows, and columns.
- **DEM upload is rejected** — confirm the file is a georeferenced floating
  point GeoTIFF, no larger than 2,560 by 2,560 pixels, with a north-up square
  grid.
- **MCL or CSA is rejected** — enter numeric values in the units displayed by
  the form.
- **The network is too dense or sparse** — adjust one threshold at a time,
  rebuild, and compare the same locations.
- **Least-cost breaching is slow or produces long cuts** — return toward the
  displayed breach-distance default and inspect whether another conditioning
  option better matches the terrain.
- **Channels changed after rebuilding with the same thresholds** — verify that
  extent, map object or uploaded DEM, pruning method, and conditioning method
  also match the earlier run.

## Related Docs

- [General Channel Delineation guide](controls/channel-delineation.md)
- [Iterative First-Order Link Prune guide](../vendor/weppcloud-wbt/docs/iterative_first_order_link_prune.ENDUSER.md)
- [User preferences](user-preferences.md)
