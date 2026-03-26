# Official RUSLE2 Climate and Erosivity Data

> Vendored normalization of the canonical official RUSLE2 climate-database
> distribution and its companion polygon bundle.

> **See also:** [../../specification.md](../../specification.md) for the R-mode
> contracts that distinguish official RUSLE2 planning datasets from
> `cligen_static` WEPP-aligned runtime erosivity.

## Overview

This directory vendors the official RUSLE2 climate-database release published
through the NRCS or Purdue-hosted RUSLE2 data site, converted into repository-
native Parquet or GeoParquet artifacts for inspection, provenance, and future
runtime or validation work.

The official distribution is not packaged as modern analytics formats. It is
published as:

- state or territory ZIP files containing legacy `.gdb` climate databases
- an official polygon shapefile bundle for climate zones

For local use in this repo, those sources were normalized into:

- one Parquet of official source-file inventory
- one Parquet of all extracted climate records
- one GeoParquet of the official polygon bundle with deterministic joins to the
  extracted climate records where an official or defensible `REC_LINK` exists

## Files

| File | Purpose |
|------|---------|
| [rusle2_official_source_files.parquet](rusle2_official_source_files.parquet) | Inventory of the 54 official climate ZIP files used for extraction |
| [rusle2_official_climate_records.parquet](rusle2_official_climate_records.parquet) | Normalized climate-record table extracted from the official `.gdb` files |
| [rusle2_official_climate_zones.geoparquet](rusle2_official_climate_zones.geoparquet) | Official polygon bundle converted to GeoParquet and joined to selected climate records |

## Source Attribution

- **Official RUSLE2 climate landing page**:
  https://www.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2
- **Official climate database index**:
  https://fargo.nserl.purdue.edu/rusle2_dataweb/NRCS_Climate_Database.htm
- **Official climate ZIP directory**:
  https://fargo.nserl.purdue.edu/RUSLE2_ftp/Climate_data/
- **Official polygon bundle**:
  https://fargo.nserl.purdue.edu/RUSLE2_ftp/Climate_data/Climate%20Data%20Shp%20Files/climate%20data%20shp%20files.zip

The vendored Parquet or GeoParquet artifacts in this directory are derivative
convenience products created for local runtime, inspection, and reproducible
repository access.

## Metadata

### Source Inventory Parquet

- Rows: `54`
- Coverage: official state or territory climate ZIP files present in the public
  RUSLE2 climate directory at extraction time
- Key columns:
  - `zip_name`, `zip_url`
  - `gdb_name`
  - `record_count`
  - `status`

### Climate Records Parquet

- Rows: `10,319`
- Unique non-null `official_rec_link`: `9,091`
- Rows without polygon join: `41`
- Coverage:
  - official climate records from the public RUSLE2 climate databases
  - includes CONUS, Alaska, Hawaii, Puerto Rico, Pacific Basin, and Virgin
    Islands table records where present in the official databases
- Key columns:
  - record identity: `state_name`, `local_area`, `record_name`,
    `record_name_decoded`
  - join diagnostics: `official_rec_link`, `official_rec_link_method`,
    `in_official_polygon_bundle`
  - erosivity values: `r_factor_english`, `r_equiv_english`,
    `r_monthly_jan` through `r_monthly_dec`, `r_monthly_sum`
  - supporting climate fields: `eros_density_*`, `precip_mm_*`, `temp_c_*`
  - official metadata: `climate_ei_choice`, `runoff_rainfall_choice`,
    `science_version`

### Climate Zones GeoParquet

- Rows: `32,932`
- Unique polygon `official_rec_link`: `8,970`
- Polygon rows with a matched climate record: `32,645`
- Unique polygon `official_rec_link` values with a matched climate record:
  `8,803`
- CRS: inherited from the official polygon shapefile (`EPSG:4326`)
- Key columns:
  - official polygon fields: `OBJECTID`, `RUSLE_REQ`, `REC_LINK`,
    `Shape_Leng`, `Shape_Area`
  - deterministic selected climate record:
    `selected_record_name`, `selected_record_variant`,
    `selected_official_rec_link_method`, `r_factor_english`,
    `r_monthly_*`, `r_monthly_sum`
  - duplicate diagnostics:
    `matched_record_count`, `matched_record_variants`,
    `matched_record_names`

## Transformation Notes

The vendored artifacts apply these local normalization steps:

- extracted the official `.gdb` tables from the public ZIP distribution
- excluded one non-data placeholder row named `default`
- normalized text fields with HTML unescaping, accent folding, and a small
  alias map for known legacy or misspelled county names
- parsed both `R` and `Req` region labels into official polygon `REC_LINK`
  forms such as `10-11` or `16-18`
- retained official `R_MONTHLY` when present
- derived monthly erosivity as `PRECIP * EROS_DENSITY` when `R_MONTHLY` was
  absent but the official monthly precipitation and erosivity-density fields
  were present
- converted the official polygon shapefile to GeoParquet
- joined one deterministic selected climate record per polygon `REC_LINK` with
  this preference order:
  - monthly data present
  - non-`Req` record preferred over `Req`
  - `CLIMATE_EI_CHOICE_R_RATIO` preferred over `R_AND_EI_PTR`
  - explicit region-labeled record preferred over plain county fallback

The GeoParquet also preserves duplicate diagnostics so the selected record is
auditable when multiple official climate rows share the same `REC_LINK`.

## Limitations

- `41` official climate-table rows remain table-only in the vendored Parquet:
  - `30` Montana `YellowstonePark County` rows
  - `10` Virgin Islands station rows
  - `1` Virginia `City of Clifton Forge` row
- The official polygon bundle is not a complete geometry companion for every
  climate record in the official tables.
- The climate-record Parquet therefore has broader official coverage than the
  polygon GeoParquet.
- The `.gdb` files in the official distribution are legacy SQLite 2.x
  databases, so reproducible regeneration requires compatible extraction
  tooling.

## Developer Notes

- Use the repository `.venv` to read these artifacts with `pandas`,
  `pyarrow`, and `geopandas`.
- Prefer the climate-record Parquet when you need the full official table
  inventory, including table-only rows and non-CONUS records.
- Prefer the GeoParquet when you need the official polygon geometry plus one
  deterministic joined climate record per zone.
- Do not assume `selected_record_name` is the only official climate row for a
  polygon. Check `matched_record_count` and `matched_record_names` when join
  multiplicity matters.
