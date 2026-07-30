# Channel Delineation
> Build a channel network from a DEM so WEPP can route flow and sediment.

## Overview
Channel delineation extracts channels from a DEM using either TOPAZ or Weppcloud-WBT. You choose an extent mode to define the working area, set the routing parameters, and run **Build Channels**. The resulting channel network is required before subcatchments and most downstream steps.

## Quick Start
1. Pick an **Extent mode**.
2. Confirm **Minimum channel length (MCL)** and **Critical source area (CSA)**.
3. For Weppcloud-WBT, choose the **depression smoothing** option and (if needed) **breach distance**.
4. Click **Build Channels** and wait for completion.

## Extent Modes
| Mode | When to use | Required inputs | Notes |
| --- | --- | --- | --- |
| Use map extent | Most runs | Current map view | Uses the visible map bounds. Build may be disabled until you zoom in. |
| Specify extent | You know the exact bounds | Manual bounds entry | Enter **south, west, north, east** in decimal degrees (WGS84). |
| Set Map Object | Reuse an exact grid | Map object JSON | Paste the `_map` JSON from `ron.nodb` to reuse the exact grid, cellsize, and UTM metadata. |
| Upload DEM | You already have a DEM | GeoTIFF upload | Validates and installs the uploaded DEM, then uses its extent for delineation. |

## Upload DEM Requirements
Your DEM must meet all of the following:
- GeoTIFF (`.tif`) with a valid spatial reference.
- Floating point data (`Float32` or `Float64`).
- No larger than **2560 x 2560** pixels.
- North-up with **no rotation**.
- **Square pixels** (equal x and y resolution).

UTM handling:
- If the DEM is already in UTM, it is used as-is (square pixels required).
- If the DEM is not UTM, it is warped to UTM based on the **top-left** corner.

If any requirement fails, the upload is rejected with a specific error message.

## Parameters
### Minimum Channel Length (MCL)
- Units: meters.
- Controls the minimum length for a channel segment to be retained.
- Lower values produce more channels; higher values produce fewer channels.

### Critical Source Area (CSA)
- Units: hectares.
- Minimum contributing area needed to initiate a channel.
- Lower values produce more channels; higher values produce fewer channels.

Calibration guidance: WEPP in WEPPcloud has been calibrated with CSA < 10 ha and MCL < 100 m. Avoid grossly exceeding these values unless you have a specific justification and understand the impacts on channel density and routing.
### Weppcloud-WBT Options

See the [WBT Channel Delineation guide](../wbt-channel-delineation.md) for
end-user guidance on all WBT inputs and choices.

- **Depression smoothing**
  - Fill: fills sinks before routing.
  - Breach: removes barriers by breaching.
  - Breach (Least Cost): uses a bounded cost-based breach and stops with
    guidance when the selected distance leaves depressions unresolved.
  - Topaz Conditioning Algorithm: reproduces TOPAZ FILDEP/RELIEF depression
    filling, narrow-obstruction adjustment, and flat resolution before the
    normal Weppcloud-WBT flow and channel steps.
  - A successful **Build Channels** saves the selected algorithm; reloading the
    run shows the algorithm used for the build.
- **Breach distance**
  - Only used with Breach (Least Cost).
  - Units: meters.
  - If the search cannot resolve every depression, channel building fails
    without filling the unresolved areas. The summary recommends increasing
    the distance, adjusting the DEM extent, inspecting DEM/NoData boundaries,
    or deliberately selecting another conditioning method.

TOPAZ uses only **MCL** and **CSA**.

New projects created with the `disturbed9002_wbt` configuration select
**Topaz Conditioning Algorithm** by default. Existing projects retain their
saved selection, and other configurations keep their configured defaults.

### Watershed reaches the DEM boundary

After WBT delineates subcatchments, WEPPcloud checks all four raster edges for
positive hillslope identifiers. The project configuration can either warn and
continue or stop with an error. Signed-in users can choose an account default
on the [User Preferences](../user-preferences.md) page. That choice follows
the authenticated user who submits delineation; it is not selected from the
run owner and does not become another user's preference. Auto uses the project
configuration.

When **Stop with an error** is active, WEPPcloud removes the clipped
subcatchment raster and does not run watershed abstraction. Select a different
outlet or enlarge the project extent, rebuild channels, and delineate again.
The error lists the edge hillslope identifiers to help diagnose which part of
the watershed reached the boundary.

## Set Map Object Mode
Use this when you want the **exact** grid from another run.

Where to find it:
- Open the source run’s `ron.nodb` and copy the `_map` JSON block.

What it contains:
- Extent, center, zoom, cellsize.
- UTM metadata and grid dimensions.

Example (truncated):
```json
{
  "py/object": "wepppy.nodb.ron.Map",
  "extent": [-117.8, 46.7, -117.2, 47.1],
  "center": [-117.5, 46.9],
  "zoom": 11,
  "cellsize": 30.0,
  "utm": {"py/tuple": [395201.31, 5673135.24, 32, "U"]},
  "_num_cols": 800,
  "_num_rows": 650
}
```

## Outputs
Successful delineation produces channel outputs in the run directory, typically under:
- `topaz/` (TOPAZ artifacts) or `watershed/wbt/` (Weppcloud-WBT artifacts)
- `watershed/` summary files and channel resources

These outputs drive subcatchments, hillslopes, and later WEPP steps.

## Troubleshooting
- **Build button disabled**
  - Use map extent: zoom in further.
  - Upload DEM: upload a valid DEM first.
- **Upload rejected: missing spatial reference**
  - Re-export the DEM with a valid CRS.
- **Upload rejected: non-float data**
  - Re-export as Float32 or Float64.
- **Upload rejected: non-square pixels or rotation**
  - Reproject or resample to square pixels with north-up orientation.
- **Channels fail after upload**
  - Confirm the DEM is Float32/Float64 and UTM-compatible.
  - Verify the DEM is <= 2560 x 2560 pixels.
- **Watershed reaches the DEM boundary**
  - Enlarge the map extent or choose an outlet farther inside the DEM.
  - Rebuild channels before delineating subcatchments again.

## Tips
- For repeatable runs, **Set Map Object** ensures identical grid geometry.
- For custom DEMs, **Upload DEM** gives you full control but must meet strict requirements.
- If your channels look too dense or sparse, adjust **CSA** and **MCL** in small steps.
