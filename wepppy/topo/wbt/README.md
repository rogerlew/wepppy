# Watershed Abstraction from Digital Elevation Maps (DEM)

> **See also:** [AGENTS.md](../../../AGENTS.md) for Watershed delineation (TOPAZ, Peridot/Rust, WhiteboxTools) and WhiteboxTools Integration sections.

The WEPP model requires an abstracted watershed model comprised of a channel or stream network and hillslopes or subcatchments flowing into the channel segments.

Watershed abstraction begins by acquiring a Digital Elevation Map or DEM.


## Watershed Abstraction General Workflow from Online Interface

1. Acquire a DEM (raster)
- can be from different sources depending on location
   - can be at various spatial resolutions
   - could be lidar

2. Delineate a channel with user defined parameters like critical source area and minimum channel length
   - requires DEM preprocessing to ensure cells are hydrologically connected (flow down hill)
   - then building a stream network based on flow accumulation

3. Identify an Outlet
   - User defines a point
   - We find the closed channel cell `TopazRunner.find_closest_channel2` (this is in python and should be re-implemented in wbt-weppcloud with routine that walks down to find channel, could utilized find outlet tool code)

4. Delineate watershed boundary
   - Find the basin by identying the cells that drain into the map
   - with TOPAZ the basin must be fully contained within the map extent
   - whitebox-tools is more forgiving and will clip basins if they extend past the map

5. Identify streams in the watershed
   - TOPAZ has a branching identifier scheme with channels ending with 4
   - Each channel can have 3 channels routing into them
   - The wbt-weppcloud `HillslopesTopaz` tool replicates TOPAZ's channel and subcatchments scheme

6. Identify Subcatchments
   - subcatchments are define in a subcatchments map the "subwta" map

7. Obtain channel network parameters
   - TOPAZ generates a channel report in the "netw.tab" file with information regarding starting and ending points, lengths, uparea, order, and so forth.
   - `HillslopesTopaz` in wbt-weppcloud has replicated functionality for generating the equivalent `netw` file

8. From here the workflow transitions to PERIDOT (Programmable Environmental Rust Interface for Drainage & Operational Topography, https://github.com/wepp-in-the-woods/peridot)
   - peridot is written in rust and generates slope files for WEPP
   - both channel and subcatchment slope files are determined by walking over their flowpaths
     - the hillslopes are "representative" of the terrain
     - they are always rectangular
     - the slope profiles are aggregated from flowpaths in the watershed
     - in wepppy we usually clip them to 300m in length and clip width to maintain area
   - peridot also generates tabular reports for channels and hillslopes (watershed/*.parquet files)

## WEPPcloud has two functional delineation backends

### TOPAZ
- FORTRAN90
- .ARC maps
- codebase available but not readily extensible, even with AI agents

### wbt-weppcloud(https:///github.com/rogerlew/whitebox-tools)
- rust lang, MIT license
- fork of whitebox-tools
- no gdal, but geotiff support
- performant
- tools are written in a straightforward encapsulated procedural style and relatively easy to extend
- `HillslopesTopaz` in wbt-weppcloud and `WhiteboxToolsTopazEmulator` in wepppy provide `NoDb.Watershed` a substantially similar interface to TOPAZ resources

## Flow Vector Outputs (WBT only)

- `flovec.tif` is the WhiteboxTools D8 pointer raster (`64 128 1 / 32 0 2 / 16 8 4`).
- Pointer mapping uses the WhiteboxTools default (not ESRI): 1=NE, 2=E, 4=SE, 8=S, 16=SW, 32=W, 64=NW, 128=N.
- `flovec.wgs.tif` is a WGS84 warp of `flovec.tif` (EPSG:4326, nearest-neighbor, same data type).
- `flovec.wgs.tif` includes metadata `WEPP_CELL_SIZE_M` so UI overlays can size arrows in meters.
- The gl-dashboard D8 Direction overlay loads `dem/wbt/flovec.wgs.tif` via the browse download routes; re-delineate WBT runs to generate it.
