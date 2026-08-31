# WP12C Locale and Dataset Matrix

This closed matrix is the implementation and Forest acceptance population.
Profile-owned lists are authoritative; catalog-wide support flags cannot add a
Builder choice.

| Stable profile | Runtime token | DEM | Soil | Land cover | Climate | Station DB | Defaults |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `continental-us` | `us` | `usgs-ned1-2024`, `usgs-ned13-2022` | `ssurgo-gnatsgso-2025` | `nlcd-2019` | `vanilla_cligen`, `prism_stochastic`, `observed_daymet`, `observed_gridmet` | `cligen-stations-legacy`, `cligen-stations-2015`, `cligen-stations-ghcn` | NED1 2024, SSURGO/gNATSGO 2025, NLCD 2019, Vanilla CLIGEN, 2015 |
| `europe` | `eu` | `europe-eudem-v1-1` | `esdac-europe` | `corine-1990`, `corine-2000`, `corine-2006`, `corine-2012`, `corine-2018` | `vanilla_cligen`, `eobs_modified` | `cligen-stations-ghcn` | EUDEM v1.1, ESDAC, CORINE 2018, Vanilla CLIGEN, GHCN |
| `canada` | `canada` | `copernicus-dem-30` | `isric-global` | `c3s-landcover-1992` through `c3s-landcover-2020` | `vanilla_cligen`, `observed_daymet` | `cligen-stations-ghcn` | Copernicus 30 m, ISRIC, C3S 2020, Vanilla CLIGEN, GHCN |
| `australia` | `au` | `australia-srtm-1s` | `asris-australia` | `australia-landuse-2010-2011` | `vanilla_cligen`, `agdc` | `cligen-stations-ghcn` | SRTM 1 second, ASRIS, Australia 2010-2011, Vanilla CLIGEN, GHCN |
| `global-earth` | `earth` | `copernicus-dem-30` | `isric-global` | `c3s-landcover-1992` through `c3s-landcover-2020` | `vanilla_cligen` | `cligen-stations-ghcn` | Copernicus 30 m, ISRIC, C3S 2020, Vanilla CLIGEN, GHCN |

Every profile allows `topaz` and `wbt` with Single OFE and the complete runtime
WEPP binary provider list. The only Multiple OFE tuple is
`wbt|multiple-ofe|wepp_260803`; all other binaries remain Single-OFE-only.
Every generated config is Preview and sets
`landuse.enable_landuse_change = true`.

WP12C graphs use capability schema v3 because Climate Station Database is a
new mandatory stored authority axis. Historical schema-v2 graphs remain valid
without that axis.
