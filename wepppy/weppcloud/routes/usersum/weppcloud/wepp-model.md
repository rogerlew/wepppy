# The WEPP Model

## Model Background

The WEPP model is a physically-based hydrology and erosion model (Flanagan and Nearing, 1995; Flanagan et al., 2007), initially developed to be applied at hillslope scales or in small agricultural catchments. The advantage of WEPP is its ability to estimate the spatial and temporal distribution of soil loss or deposition along a hillslope, as well as sediment yield at the bottom of a hillslope. WEPP is based on the fundamentals of hydrology, plant science, hydraulics, and erosion mechanics (Flanagan and Nearing, 1995). For detailed descriptions of model components and processes, refer to the WEPP User Summary (Flanagan and Livingston, 1995) and WEPP Technical Documentation (Flanagan and Nearing, 1995).

Developments such as the incorporation of baseflow algorithms and channel routing methods have extended the applicability of the model to larger watersheds. The model has been tested for several undisturbed watersheds and for forest management effects on water and sediment yield from watersheds in the Pacific Northwest (Brooks et al., 2016; Srivastava et al., 2020).

The following is a brief description of model components and processes.

### Watershed Delineation

Watershed delineation can be performed by TOPAZ or WEPPcloud-WBT.

#### TOPAZ

- Topographic Parameterization (TOPAZ) is used to derive topographic features (slope length, width, aspect, slopes) from the Digital Elevation Model (DEM).
- TOPAZ characterizes watersheds as representative hillslopes and channels, and links hillslopes to channel networks.
- A Python watershed abstraction routine (`wepppy.watershed_abstraction`) parameterizes representative hillslopes by walking the flowpaths for each subcatchment identified by TOPAZ.
- Output grids and tables from TOPAZ are included in archived project downloads. Descriptions of these products are available in the [TOPAZ Manual](https://www.ars.usda.gov/ARSUserFiles/30700510/TOPAZ_User-Manual2.pdf).

#### WEPPcloud-WBT

- [WEPPcloud-WBT](https://github.com/rogerlew/weppcloud-wbt) is a WEPPcloud-maintained fork of WhiteboxTools used operationally for watershed preprocessing and delineation.
- It provides modern DEM-based hydrologic preprocessing (for example D8 flow direction, flow accumulation, and stream extraction) and is designed for larger catchments and high-performance raster workflows.
- The `HillslopesTopaz` tool implements Garbrecht and Martz TOPAZ-style stream and hillslope identifiers for a single watershed and emits WEPPcloud-ready channel metadata tables (`netw.tsv`, `netw_props.tsv`) plus left/right/top hillslope rasters.
- The `FindOutlet` tool derives a stream outlet pour point by tracing D8 flow and supports requested start locations for interactive outlet selection.
- The `StreamJunctionIdentifier` and `PruneStrahlerStreamOrder` tools support confluence/junction analysis and stream-order pruning workflows used by WEPPcloud modules.

### Hydrology and Hydraulics

WEPP first executes hydrologic and erosion calculations for each hillslope and channel. The flow and sediment yield from each hillslope are fed into associated channels and routed through the channel network to the watershed outlet.

- WEPP simulates surface hydrology and hydraulics, subsurface hydrology, vegetation growth and residue decomposition, and sediment detachment and transport along each hillslope and channel segment using four major input files: climate, slope, soil, and vegetation.
- Climate: Requires precipitation amount and its characteristics (duration, peak intensity, and time-to-peak intensity). Other variables include maximum and minimum temperatures, dew point temperature, solar radiation, wind speed, and wind direction.
- Winter hydrology: Snow accumulation, snowmelt, frost, and thaw. These processes are performed internally by the model on an hourly basis.
- Surface hydrology: Calculates infiltration, rainfall excess, depression storage, and peak discharge. Rainfall excess is calculated at 1-minute intervals following the modified Green-Ampt-Mein-Larson equation.
- Hydraulics: Overland flow and peak discharge are computed using a modified kinematic wave equation.
- Percolation: Uses storage routing techniques to predict flow through soil layers.
- Plant growth: Follows EPIC’s model approach for vegetation growth. The model estimates biomass accumulation based on heat units and photosynthetically active radiation. Plant growth accounts for water and temperature stress. Variables include growing degree days, vegetative dry matter, canopy cover and height, root growth, and leaf area index.
- Evapotranspiration: Uses the Penman equation for potential evapotranspiration. Another available method is FAO 56 Penman-Monteith.
- Subsurface flow: Subsurface lateral flow from hillslopes is estimated using Darcy’s law.
- WEPP maintains a continuous daily water balance of surface runoff, subsurface lateral flow, soil evaporation, plant transpiration, residue evaporation, total soil water, deep percolation, snow accumulation and melt, and frost and thaw.

### Hillslope Erosion

- WEPP-simulated soil erosion on a hillslope profile is represented in two ways: 1) detachment and delivery of soil particles by raindrop impact and shallow sheet flow on interrill areas, and 2) soil particle detachment, transport, and deposition by concentrated flow in rill areas.
- Rill erosion is modeled as a function of the flow’s capacity to detach and transport soil versus the existing sediment load in the flow. WEPP uses a steady-state sediment continuity equation for erosion computations. Soil detachment in rills occurs when the flow hydraulic shear stress exceeds the critical shear stress of the soil, and when sediment load is less than sediment transport capacity.
- Deposition occurs when sediment load in rill flow is greater than flow sediment transport capacity. Sediment transport capacity is calculated using a modified Yalin equation.

### Channel Hydrology and Erosion

- Peak runoff rates are computed using: 1) modified EPIC, 2) CREAMS, 3) Kinematic Wave, 4) Muskingum-Cunge, and 5) Muskingum-Cunge (variable). The last three routing methods support simulations of perennial channels/streams.
- The channel erosion routine in WEPP is similar to rill erosion simulation on hillslopes, except that flow shear stress is calculated using regression equations that approximate spatially varied flow equations, and only entrainment, transport, and deposition by concentrated flow are considered.
- Detachment is assumed to occur from the channel bottom until the nonerodible layer is reached, after which the channel starts to widen and the erosion rate decreases with time until flow is too shallow to cause detachment.

### Recent Developments

- An improved algorithm for frost simulation based on energy balance (Dun et al., 2010).
- An enhanced algorithm for percolation and subsurface lateral flow, allowing saturation-excess runoff (Dun et al., 2009; Boll et al., 2015).
- A FAO 56 Penman-Monteith method for reference and actual evapotranspiration (ET) developed by Allen et al. (1998) (Wu and Dun, 2004).
- Implementation of more appropriate channel routing methods (for example kinematic wave and Muskingum-Cunge) for perennial streams (Wang et al., 2014).
- A linear reservoir groundwater baseflow contribution from hillslopes to channel streamflow (Srivastava et al., 2017).
