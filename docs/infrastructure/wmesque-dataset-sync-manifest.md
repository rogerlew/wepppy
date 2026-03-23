# WMesque Dataset Sync Manifest
> Required dataset identifiers for synchronizing production geodata to the test production WMesque environment.

## Purpose
- Provide a canonical, code-derived list of dataset IDs that `wepppy` requests through `wmesque_retrieve(...)`.
- Support repeatable production-to-test-production geodata sync planning.

## How WMesque Resolves a Dataset ID
- `wmesque2` resolves a request path `dataset` to `/geodata/<dataset>/.vrt`.
- Sync operations should preserve the full dataset directory tree and adjacent metadata files used by each VRT.

## Baseline Required Datasets
These are the default datasets used by standard NoDb defaults and common runtime paths.

| Area | Dataset ID |
| --- | --- |
| DEM | `ned1/2024` |
| Landuse | `nlcd/2019` |
| Soils | `ssurgo/gNATSGSO/2025` |
| Climate revision tiles | `prism/ppt` |
| Climate revision tiles | `prism/tmin` |
| Climate revision tiles | `prism/tmax` |

## Additional Config-Driven Datasets
These appear in committed NoDb configs and route through `wmesque_retrieve(...)` when those configs are used.

### DEM (`dem_db`) dataset IDs
- `au/srtm-1s-dem-h`
- `ca/ftp.maps.canada.ca/pub/nrcan_rncan/elevation/cdem_mnec`
- `eu/eu-dem-v1.1`
- `idearagon://mdt`
- `locales/ChileCayumanque/DEM`
- `locales/hubbar_brook/dem`
- `ned1/2024`
- `ned13/2016`
- `ned13/2022`
- `tenerife/136_MDT25_TF`
- `tenerife/MDT05_Tenerife`

### Landuse (`nlcd_db`) dataset IDs
- `alaska/nlcd/2016`
- `ca/canadalandcover2020`
- `eu/CORINE_LandCover/2000`
- `eu/CORINE_LandCover/2018`
- `hawaii/nlcd/wepp_31131a7`
- `locales/ChileCayumanque/landuse`
- `locales/earth/C3Slandcover/2020`
- `locales/virgin_islands/landcover/2023`
- `nlcd/2016`
- `nlcd/2019`
- `portland/nlcd`

### Fractional landuse layers (`landuse.fractionals`)
- `nlcd/2001`
- `nlcd/2004`
- `nlcd/2006`
- `nlcd/2008`
- `nlcd/2011`
- `nlcd/2013`
- `nlcd/2016`
- `nlcd/2019`
- `nlcd/2021`

### Soils dataset IDs used with WMesque
- `alaska/gsmsoil`
- `chile`
- `hawaii/ssurgo`
- `locales/ChileCayumanque/soils`
- `locales/virgin_islands/soils`
- `portland/soils`
- `ssurgo/gNATSGSO/2025`

## Mod-Specific Hardcoded Dataset IDs
- `nlcd_treecanopy/2016`
- `nlcd_shrubland/2016/annual_herb`
- `nlcd_shrubland/2016/bare_ground`
- `nlcd_shrubland/2016/big_sagebrush`
- `nlcd_shrubland/2016/sagebrush`
- `nlcd_shrubland/2016/herbaceous`
- `nlcd_shrubland/2016/sagebrush_height`
- `nlcd_shrubland/2016/litter`
- `nlcd_shrubland/2016/shrub`
- `nlcd_shrubland/2016/shrub_height`

## Dynamic/Override Inputs
- Culvert batch processing can request `nlcd_db_override` at runtime, so additional `nlcd/*`-style datasets may be needed beyond this manifest.

## Explicit Non-WMesque Backends
These identifiers are present in configs but are not served by WMesque when used in their designated code paths.

- `copernicus://...` (`dem_db`) routes to Copernicus retrieval code.
- `opentopo://...` (`dem_db`) routes to OpenTopography retrieval code.
- `isric` (`ssurgo_db`) routes to ISRIC soils build logic.
- `None` (`ssurgo_db`) indicates no WMesque SSURGO retrieval for that config path.

## Maintenance Notes
- Update this manifest when adding or changing:
  - `wmesque_retrieve(...)` callsites in `wepppy/*`
  - config dataset IDs in `wepppy/nodb/configs/*`
- Validation entry points:
  - `rg -n 'wmesque_retrieve\\(' wepppy`
  - `rg -n '^(dem_db|nlcd_db|ssurgo_db|soils_map|fractionals)\\s*=' wepppy/nodb/configs`
