# Wallow 2011 final-severity fixtures

Preferred real burn-severity examples for postfire debris-flow development,
selected by the repository owner on 2026-09-09 instead of the pseudo-BARC256
examples. Source: USDA Forest Service RSAC, distributed by USGS in
[Wallow_FinalSoilBurnSeverity.zip](https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/MTBS_Fire/data/baer/Wallow_FinalSoilBurnSeverity.zip).
The archived README identifies `FinalSoilBurnSeverity` as the field-validated
collection. Source metadata permits use with proper source acknowledgment.
Original metadata and README are retained alongside `manifest.json`.

## Products and compatibility

All three GeoTIFFs come from the archive's `FinalSoilBurnSeverity` directory,
not its separate July 1 preliminary BARC collection:

- `wallow_20110623_barc4_alb.tif`: distributed final four-class severity raster;
  1 unchanged/very low, 2 low, 3 moderate, 4 high. Value 0 is unclassified/background,
  not an additional documented severity class.
- `wallow_20110623_barc256_alb.tif`: source continuous BARC256 product, values 0–255.
- `wallow_dnbr.tif`: continuous Float32 dNBR, scaled by 1000 according to source
  metadata; normalization uses scale 0.001. This file's archive name differs
  from the descriptive metadata's dated dNBR filename.

Grid: 2609 rows × 2380 columns, 30 m, NAD83 / Conus Albers (EPSG:5070).
Source pre/post image dates: 2011-05-30 and 2011-06-23. No cropping, warping,
reclassification, threshold changes or recalculation from dNBR is performed.
The field-validation claim applies to the distributed final severity collection,
not to treating continuous dNBR or BARC256 as measured soil properties.

Compatibility plan: add new fixtures only; existing source fixtures, producer
formulas and saved runs remain unchanged. Convert HFA to losslessly compressed
GeoTIFF, preserving dtype, every sample, grid and effective raster masks. Preserve
palette RGB entries; GeoTIFF palettes do not store HFA alpha entries. The source
rasters declare no numeric NoData, so these copies also declare none. Do not
silently reinterpret dNBR -2000 or BARC256 zero as missing. For normalized SBS,
explicitly map only codes 1–4 to 0–3 and treat unclassified zero as unavailable
under the caller's preparation contract; no normalized SBS derivative is made here.

These Albers rasters require explicit alignment before use with the M1 builder's
UTM DEM grid. They do not overlap the earlier Sky Island fixtures or establish
complete watershed DEM/K/Soils inputs. The pseudo fixtures remain labeled history.

## Reproduction and checks

Download the linked archive to a local path, then run:

    wctl exec weppcloud python tests/nodb/mods/fixtures/postfire_debris_flow_wallow/import_archive.py /workdir/path/to/Wallow_FinalSoilBurnSeverity.zip

The importer verifies the pinned archive hash, reads only named members and
compares all output samples, masks, grids and palette RGB with the original HFA.
Existing output rasters are validated rather than overwritten. Source member and
output SHA-256 hashes, class counts and valid ranges are in `manifest.json`.
The 130 MiB archive, Landsat reflectance bands, pyramids and duplicate preliminary
products are not stored in Git.

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_wallow_fixtures.py --maxfail=1

## Related Wallow project

The owner identified forest project `woolen-refusal/disturbed9002_wbt`.
Its earlier SBS used the archive's July 1 original BARC256. The owner subsequently
uploaded the final polygon TIFF below and rebuilt landuse, WEPP and gridded RUSLE.
Current read-only validation uses matching June 23 dNBR; see [Wallow evidence](../../../../../docs/work-packages/20260909_staley_m1_predictors/artifacts/validation.md#rebuilt-wallow-final-assessment).
Keep assessment dates explicit when comparing these fixtures with that project.

## Final polygon raster

Owner-requested conversion (2026-09-09): `wallow_finalsoilburnseverity.tif`
rasterizes the archive's `wallow_finalsoilburnseverity.shp` using `GRIDCODE`.
This is an additive fixture; the previously imported rasters remain unchanged.
It uses the same 30 m EPSG:5070 grid and extent, preserving severity codes 1–4
with 0 as background/NoData. GDAL's default pixel-center rule applies; no
all-touched expansion, reprojection or severity thresholds are introduced.
Source component hashes, class counts and output identity are recorded in
`wallow_finalsoilburnseverity.manifest.json`. Reproduce with a fresh output path
(the script refuses to overwrite the existing TIFF):

    wctl exec weppcloud python tests/nodb/mods/fixtures/postfire_debris_flow_wallow/rasterize_final_severity.py /workdir/path/to/Wallow_FinalSoilBurnSeverity.zip
