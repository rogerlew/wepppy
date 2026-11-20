# Incident readback and replay inputs

## Read-only evidence

Collected 2026-11-20 UTC on production host `wepp1` and analyzed on `forest`. The original run files and jobs were read without production mutations.

A private archive on forest at `/var/tmp/wepppy-eu-run-recovery-baseline/runs.tar` holds 30 files from the two runs. Its SHA-256 is `52b4632a176664388ce84778d2e336104ba9617fc567124646cdd05525af648c`. The archive contains effective configurations and manifests, selected NoDb state and logs, both submitted climates, the failed E-OBS artifacts, the ESDAC quality report, and the final CORINE raster. It is outside Git. Both runs have the same saved map extent and 5 m cell size. Recover the exact delineation operation and settings from the retained state and available recordings before replay. The upload named `LandCover25m.tif` was absent from the current working directory. The saved `landuse/nlcd.tif` is from the later gridded build and cannot establish original upload parity.

| Retained fixture | SHA-256 |
| --- | --- |
| `autosomal-vetch/climate/FLOOD4.cli` | `684e0fe20875c3d997e2d2523c9535a13f9ba561c6a1d4e451132de8edc29463` |
| `autosomal-vetch/climate/ESFANGAR.cli` | `1b6329e1509b6f6527e4ce00016c4d48492c7373ff5a542fd3e0f6ca455732b2` |
| `studded-stranglehold/landuse/nlcd.tif` | `7c7c4ee919553e19cbfc8412a88989ebf2bab4d77051f97f7a448f2830a7a8e6` |

The matching prepared DEM (`MDT5m.tif`) has SHA-256 `f4ed3d5e181e5e3ae89fe766bd6caf1014947b99dc92a1221b7b9444b1cbc3fd` in both runs. The saved source is `eu/eu-dem-v1.1`, with a map extent of west/south/east/north 2.9802277/39.8070076/3.0049379/39.8371029, a critical source area setting of 5, a minimum channel length setting of 100, and outlet requested at 2.98514914 E, 39.81271779 N. Both saved snapped outlets are at 2.9850804545 E, 39.8127342915 N. No burn-severity coverage is recorded. The separate private `delineation.tar` contains the available DEM files and original channel/hillslope Parquet references. Its SHA-256 is `b4974d1a066676301bbf7d23be4831bdc0abe3d55f1c89f1133c0cf6b312369a`.

RQ records show TOPAZ channel mode `ifolp`, followed by outlet selection, subcatchment construction and abstraction with Bieger 2015 widths enabled. The retained final DEM, matching outlet and delineation parameters anchor the spatial replay. The land-use timeline for `studded-stranglehold` records successful CORINE 2018 and uploaded-raster attempts using the CORINE mapping before several ESDAC upload failures and the final CORINE-plus-ESDAC failure.

A forest preflight found both E-OBS and ESDAC mounts in the existing RQ worker and the E-OBS mount in metquery. These are baseline observations. The candidate has yet to be deployed.

## E-OBS coastal interpolation

The installed E-OBS v19.0e monthly rainfall GeoTIFFs contain daily means in mm, as metquery describes. At the incident point (2.9905174 E, 39.8190863 N), the January raster pixel is 1.269 mm/day. The live API reports 60.118 mm/day with cubic and 1.269 mm/day with bilinear. July cubic reports 58.986 mm/day and bilinear reports 0.132 mm/day. The same effect contaminates both temperature series. For January, cubic minimum/maximum are 11.742/21.472 °C and the bilinear values are 4.405/12.946 °C. The conversion from mm/day to inches/month then magnifies the bad rainfall input without introducing the underlying discrepancy.

The January coastal sampling window contains approximately -999.9 for rainfall and -99.99 for temperature. The TIFF and VRT NoData metadata say -9999. The preprocessing code scales the source sentinel with the data, and passes the unscaled sentinel as output metadata. The cubic interpolator reads raw samples without masking. This explains both the high positive cubic results and why just trusting the declared NoData value is insufficient. The nearest API returned HTTP 500 at the incident location during the probe. Nearest and bilinear still require a coverage and coordinate audit before selecting production behavior.

A diagnostic build in an isolated directory on forest used the real production metquery API in bilinear mode, the original station `SPE00119882`, original centroid, 30-year duration, and the existing CLIGEN binary. It generated all 10,957 daily records with finite monthly precipitation and wet days in every month. This gives a working comparison for contract and regression design. It does not establish bilinear as the production policy or prove output parity at other locations. The cubic interpolator has consumers beyond metquery, including European soil and climate-adjacent paths. Scope any shared change using consumer-specific evidence.

## ESDAC subsoil raster sampling

Compared original `.rst` and runtime GeoTIFF values for subsoil bulk density, clay, sand and silt at all 58 original hillslopes. The values matched for each queried pixel. The diagnostic used GDAL to transform run coordinates into the EPSG:3035 grid and compared the containing pixel with the current corner-relative rounding in `RasterDatasetInterpolator`.

| Production outcome | Current rounding, all four values zero | Containing pixel, all four values zero | Containing pixel, populated |
| --- | ---: | ---: | ---: |
| Rejected (37) | 37 | 31 | 6 |
| Accepted (21) | 0 | 5 | 16 |

For example, hillslope 221 has all four fields zero under both pixel choices. Hillslope 81 uses a populated adjacent pixel at runtime but the containing pixel has all four values zero. The six populated pixels are recovery candidates that still require full physical profile validation. This experiment establishes a pixel-selection discrepancy and source coverage gaps. It does not establish a suitable substitute profile, or a net recovery from switching methods. Compare categorical attributes and continuous layers under the same declared spatial rule and test any proposed change across both recovered and previously accepted locations.
