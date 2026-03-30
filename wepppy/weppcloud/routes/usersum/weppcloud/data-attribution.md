# WEPPcloud Data Attribution

> Consolidated from `/workdir/ui-weppcloud.github.io/earth-data.md`, `/workdir/ui-weppcloud.github.io/us-data.md`, `/workdir/ui-weppcloud.github.io/eu-data.md`, and `/workdir/ui-weppcloud.github.io/au-data.md` on 2026-03-30.

WEPPcloud uses different upstream data stacks by locale and interface. This page documents those sources with a clear distinction between active implementation paths and legacy references that remain relevant for older runs.

## Global and Earth Workflows

| Category | Source | WEPPcloud use | Reference |
| --- | --- | --- | --- |
| Terrain | Copernicus DEM 30 m | Active primary Earth DEM source (`dem_db = "copernicus://dem_cop_30"`). | <https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM> |
| Terrain | SRTM GL1 via OpenTopography | Legacy or fallback Earth DEM source referenced by older Earth notes and fallback paths. | <https://portal.opentopography.org/apidocs/#/Public/getGlobalDem> |
| Soils | ISRIC SoilGrids | Active Earth soil source (`ssurgo_db = "isric"`; ISRIC builder path). | <https://maps.isric.org/> |
| Soils | Global Soil, Regolith, and Sediment Grids | Historical Earth reference from legacy docs; not the primary active Earth soil build path. | <https://www.earthdata.nasa.gov/data/catalog/ornl-cloud-global-soil-regolith-sediment-1304-1> |
| Land cover | Copernicus Climate Change Service (C3S) land cover | Active Earth land-cover family (`locales/earth/C3Slandcover/{year}`; mapping `c3s-disturbed`). | <https://cds.climate.copernicus.eu/datasets/satellite-land-cover?tab=overview> |
| Land cover | ArcGIS-hosted global land-cover item | Legacy Earth reference retained for historical context. | <https://www.arcgis.com/home/item.html?id=1453082255024699af55c960bc3dc1fe> |
| Climate | CLIGEN with GHCN station catalog | Active Earth climate station base (`cligen_db = "ghcn_stations.db"`). | <https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily> |
| Climate | CHIRPS or CHIRTS | Legacy Earth note item, historically described as in-development context. | <https://www.chc.ucsb.edu/data> |

## United States

| Category | Source | WEPPcloud use | Reference |
| --- | --- | --- | --- |
| Terrain | USGS 3DEP via The National Map (legacy NED naming) | Primary U.S. elevation source family in current and historical runs. | <https://www.usgs.gov/programs/national-geospatial-program/national-map> |
| Soils | USDA SSURGO | Primary detailed U.S. soil source. | <https://www.nrcs.usda.gov/resources/data-and-reports/soil-survey-geographic-database-ssurgo> |
| Soils | USDA STATSGO2 | Coarser U.S. soil source used alongside SSURGO in gridded U.S. workflows. | <https://www.nrcs.usda.gov/resources/data-and-reports/description-of-statsgo2-database> |
| Soils | Disturbed WEPP soils library | Secondary parameter library used in disturbed and fire-severity parameterization paths. | `Disturbed WEPP soils library (internal)` |
| Soils | Rapid Response Erosion Database (RRED) | External disturbed workflow dependency used in specific BAER or RRED paths. | <https://rred.mtri.org/rred/> |
| Climate | Updated CLIGEN climate station files | Active stochastic climate station base for many U.S. runs. | <https://doi.org/10.2489/jswc.74.4.334> |
| Climate | PRISM climate normals | Active climate localization input in multiple modes. | <https://prism.oregonstate.edu/> |
| Climate | DAYMET | Active observed gridded climate source. | <https://daymet.ornl.gov/> |
| Climate | GRIDMET | Active observed gridded climate source. | <https://www.climatologylab.org/gridmet.html> |
| Climate | DEP NEXRAD breakpoint data | Supported observed climate mode for breakpoint-style runs. | <https://www.ncei.noaa.gov/products/radar/next-generation-weather-radar> |
| Climate | Future CMIP5 scenarios | Supported future climate mode for U.S. impact analysis workflows. | <https://pcmdi.llnl.gov/mips/cmip5/> |
| Climate | Northwest Knowledge future-climate downloads | Legacy future-climate reference retained from earlier docs. | <https://climate.northwestknowledge.net/RangelandForecast/download/Models.php> |
| Land cover | Annual National Land Cover Database (NLCD) | Primary U.S. land-cover family; annual vintages are used in modern workflows. | <https://www.usgs.gov/centers/eros/science/national-land-cover-database?qt-science_center_objects=0#qt-science_center_objects> |
| Land cover | Rangeland Analysis Platform (RAP) | Active land-cover and cover-change source for revegetation and rangeland workflows. | <https://rangelands.app/products> |
| Land cover | MRLC shrubland products | Fractional cover data used by shrubland or RHEM-oriented workflows. | <https://www.mrlc.gov/data> |
| Land cover | University of Idaho Ever Forest annual NLCD derivative | Legacy auxiliary land-cover dataset retained from historical U.S. notes. | <https://github.com/rogerlew/us-conus-nlcd-ever-forest/> |

Legacy U.S. metadata references for SSURGO:

- [SSURGO Metadata: Table Column Descriptions](https://github.com/rogerlew/wepppy/files/3741446/SSURGO_Metadata_-_Table_Column_Descriptions.pdf)
- [SSURGO Metadata: Tables and Columns](https://github.com/rogerlew/wepppy/files/3741447/SSURGO_Metadata_-_Tables_and_Columns.pdf)

## Europe

| Category | Source | WEPPcloud use | Reference |
| --- | --- | --- | --- |
| Terrain | EU-DEM v1.1 | Primary EU DEM family in standard EU configs (`dem_db = "eu/eu-dem-v1.1"`). | <https://land.copernicus.eu/en/products/products-that-are-no-longer-disseminated-on-the-clms-website> |
| Terrain | IDEAragon MDT | Regional DEM override in specific EU locale configurations (for example Aragon). | <https://idearagon.aragon.es/portal/en/wcs.jsp> |
| Soils | ESDAC soil properties | Active EU soil source family in ESDAC-based builds. | <https://esdac.jrc.ec.europa.eu/resource-type/european-soil-database-soil-properties> |
| Soils | EU-SoilHydroGrids | Active interpolated EU soil-property source in current EU workflows. | <https://esdac.jrc.ec.europa.eu/projects/eusoilhydrogrids> |
| Land cover | Copernicus CORINE Land Cover | Primary EU land-cover family in disturbed EU workflows (`1990`, `2000`, `2006`, `2012`, `2018`). | <https://land.copernicus.eu/en/products/corine-land-cover> |
| Land cover | ESDAC land-use classifications | Legacy or supporting EU classification context retained from older docs. | <https://esdac.jrc.ec.europa.eu/> |
| Climate | E-OBS daily gridded climate data | Active EU climate localization source in E-OBS-modified modes. | <https://surfobs.climate.copernicus.eu/dataaccess/access_eobs.php> |
| Climate | CLIGEN with GHCN station catalog | Active station base used with EU climate localization workflows (`cligen_db = "ghcn_stations.db"`). | <https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily> |

## Australia

| Category | Source | WEPPcloud use | Reference |
| --- | --- | --- | --- |
| Terrain | SRTM-derived 1 Second DEM (DEM-H) | Primary historical Australian DEM source in legacy AU notes and configs. | <https://ecat.ga.gov.au/geonetwork/srv/eng/catalog.search#/metadata/72759> |
| Land cover | ABARES Land Use of Australia 2010-11 | Active Australian land-use classification source in AU workflows. | <https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11> |
| Soils | ASRIS 2001 and ASRIS National Soil Grid | Active AU soil build source family (`build_asris_soils`). | <https://www.asris.csiro.au/> |
| Soils | Disturbed WEPP fire-parameter library | Secondary source for AU severity-adjusted soil parameter variants. | `Disturbed WEPP soil fire parameters (internal)` |
| Soils | TERN AusCover or Landscapes references | Historical attribution context from legacy docs; not the primary active AU soil API path. | <https://ternaus.atlassian.net/wiki/spaces/TERNSup/pages/676298869/TERN%2BLandscapes%2B-%2BRemote%2BSensing> |
| Climate | AGDC monthly dataset wiring (legacy BAWAP-derived path) | Active AU runtime wiring in current code (`catalog_id = "agdc"`, `monthly_dataset = "agdc"`). | <https://ternaus.atlassian.net/wiki/spaces/TERNSup/pages/2130706474/Gridded%2BClimate%2BData%2Bfor%2BAustralia> |
| Climate | CLIGEN with GHCN station catalog | Active station base used for AU localization workflows. | <https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily> |
| Climate | BOM AGCD | Current national public gridded climate reference; included as successor context where legacy AGDC wiring still exists. | <https://www.bom.gov.au/climate/austmaps/about-agcd-maps.shtml> |

## Notes

- WEPPcloud integrates these datasets with internal preprocessing, lookup tables, and model-parameter transformations. Public attribution does not imply one-to-one raw input usage for every run step.
- Dataset availability, product names, and provider URLs can change over time. This page should be reviewed periodically against both implementation configs and provider documentation.
