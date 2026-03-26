# Momm 2025 RUSLE2 Isoerodent Data

> Vendored Momm et al. (2025) continental-US monthly erosivity data and a
> matching county GeoParquet companion for planned `momm2025` RUSLE `R`-mode
> support.

> **See also:** [../../specification.md](../../specification.md) for the full
> R-factor contract and mode-boundary guidance.

## Overview

This directory vendors a normalized copy of the public dataset released with
Momm et al. (2025), "Isoerodent surfaces of the continental US for
conservation planning with the RUSLE2 water erosion model," together with a
county geometry layer selected to match the dataset's county FIPS coverage.

The goal here is reproducible local access for the RUSLE NoDb mod. The data is
not the shipped default runtime `R` source. It is an implemented optional
`r_mode` that complements the existing `cligen_static` path:

- `cligen_static` is the WEPP-aligned approximation path.
- `momm2025_county_region` is the implemented CONUS RUSLE2
  planning-climatology path.
- the locked v1 runtime intent is a scalar run-level `R` selected from the
  watershed centroid county, with monthly values preserved in provenance

## Files

| File | Purpose |
|------|---------|
| [momm2025_county_region_monthly_r.parquet](momm2025_county_region_monthly_r.parquet) | Main monthly erosivity table derived from the public supplement |
| [momm2025_counties_conus_2010_500k.geoparquet](momm2025_counties_conus_2010_500k.geoparquet) | Matching county geometry companion built from 2010 Census counties |

## Source Attribution

- **Paper**: Momm, H. G., McGehee, R. P., and coauthors, 2025.
  *Isoerodent surfaces of the continental US for conservation planning with the
  RUSLE2 water erosion model*. *Catena*, 249, 108879.
  https://doi.org/10.1016/j.catena.2025.108879
- **Dataset**: USDA ARS Agricultural Data Commons.
  *Data from: Isoerodent surfaces of the continental US for conservation
  planning with the RUSLE2 water erosion model*.
  https://doi.org/10.15482/USDA.ADC/28821569.v1
- **County boundaries source**: U.S. Census Bureau, 2010 cartographic boundary
  counties, 1:500,000.
  https://www2.census.gov/geo/tiger/GENZ2010/gz_2010_us_050_00_500k.zip

The USDA dataset is published for public access. The vendored Parquet and
GeoParquet files in this directory are derivative convenience artifacts created
for local runtime use and reproducible repository access.

## Metadata

### Main Parquet

- Rows: `8,247`
- Unique county FIPS: `3,107`
- Counties with one row: `2,697`
- Counties with multiple `REGION` rows: `410`
- Coverage: conterminous US plus DC; Alaska and Hawaii are not present
- Columns:
  - county identity: `fips`, `state`, `state_fips`, `county`, `county_fips`
  - public split label: `region`
  - monthly erosivity: `jan` through `dec`
  - derived convenience total: `annual_r`

### County GeoParquet

- Rows: `3,107`
- CRS: `EPSG:4269` (`NAD83`)
- Geometry vintage: 2010 Census county boundaries
- Key columns:
  - identifiers: `fips`, `geoid`, `statefp`, `countyfp`, `name`, `lsad`
  - dataset diagnostics: `dataset_row_count`, `has_split_regions`,
    `region_labels`, `annual_r_min`, `annual_r_max`
  - provenance: `source_vintage`, `source_url`

## Transformation Notes

The vendored Parquet and GeoParquet are normalized from the public source
files with these local adjustments:

- padded county FIPS fields to fixed-width strings
- normalized monthly column names to lowercase `jan` through `dec`
- added `annual_r` as the sum of monthly columns
- restricted county geometry to the exact FIPS set present in the public table
- added county-level diagnostic columns to the GeoParquet for join review and
  implementation planning

## Why 2010 Counties

The public supplement still uses county FIPS values that no longer join cleanly
against newer county-boundary vintages. Two observed examples are:

- `46113` - Shannon County, South Dakota
- `51515` - Bedford city, Virginia

Using the 2010 Census county layer preserves those FIPS values and gives an
exact county-level join for every row in the vendored main Parquet.

## Limitations

- The public supplement does **not** include polygon geometry for split-county
  `REGION` rows.
- A county with multiple `REGION` rows therefore cannot be spatialized exactly
  from the public files alone.
- The dataset is a RUSLE2 planning climatology, not a reconstruction of the
  WEPP storm record for a specific run.
- Coverage is limited to the continental US plus DC.

The lack of public `REGION` polygons is the main open implementation decision
for this dataset. Current runtime behavior therefore rejects split-county
multi-`REGION` selections explicitly rather than guessing a sub-county region.

## Academic Highlights

The published paper is valuable here because it updates the operational
RUSLE2 isoerodent workflow for the continental US in a reproducible way. The
high-signal points for this repository are:

- monthly erosivity surfaces are produced for RUSLE2 climate assignment
- the workflow includes small-event handling, spatially varying recurrence
  intervals, and weighted interpolation
- the authors emphasize smoother spatial and temporal behavior than older
  hand-built surfaces
- the dataset is better understood as a planning-climatology reference than as
  a substitute for WEPP run-specific erosivity

## Developer Notes

- Prefer reading these assets with the repository `.venv`, which already has
  `pyarrow` and `geopandas`.
- Do not infer sub-county `REGION` polygons from the label strings alone.
- The approved v1 selection contract is watershed centroid, not county-area
  weighting.
- The approved v1 output contract is scalar `R`, not a spatially varying
  erosivity raster.
- If a runtime mode is added, record the exact selected county, `REGION`
  labels if used, and any aggregation rule in `rusle/manifest.json`.
