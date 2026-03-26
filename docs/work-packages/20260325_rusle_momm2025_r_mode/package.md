# RUSLE Planning-Climatology R Modes

**Status**: Complete (2026-03-26)

## Overview
This work package adds external planning-climatology rainfall-erosivity (`R`)
estimation paths for the RUSLE NoDb mod. The initial scoped mode is based on
the public Momm et al. (2025) continental-US RUSLE2 isoerodent dataset, and
the package also includes `canonical_rusle2` mode based on the
vendored official RUSLE2 climate-database release. The package keeps
`cligen_static` as the WEPP-aligned default when the goal is to approximate
the erosivity used by the run's WEPP climate, while defining separate planning
climatology modes for users who want published RUSLE2 references.

The package delivered dataset vendoring, contract decisions, runtime
implementation, manifest or UI exposure, and targeted validation for the new
`R` modes without misrepresenting public-data limitations.

## Objectives
- Vendor the public Momm et al. (2025) county or region monthly erosivity data
  in repo-native Parquet form with attribution and reproducible metadata.
- Vendor the official RUSLE2 climate-database release in repo-native Parquet
  or GeoParquet form with attribution and reproducible metadata.
- Vendor matching geometry layers and document why the 2010 county vintage is
  required for Momm FIPS compatibility and why the official RUSLE2 polygon
  bundle is only partially complete for table coverage.
- Update the RUSLE specification so `cligen_static` is framed as the
  WEPP-aligned approximation path, `momm2025_county_region` is framed as an
  updated CONUS planning-climatology path, and `canonical_rusle2` is framed as
  the vendored official planning-climatology baseline.
- Define the implementation contracts for `momm2025_county_region` and
  `canonical_rusle2` `r_mode` values, including provenance, centroid-based
  selection, and unsupported-area behavior.
- Implement the new modes with targeted tests and explicit unsupported-case
  failures.

## Scope
This package covers dataset vendoring, documentation, implementation planning,
and runtime integration of external planning-climatology `R` modes for Momm
2025 and the official canonical RUSLE2 dataset.

### Included
- Vendored `momm2025` monthly erosivity table in Parquet format.
- Vendored matching county geometry as GeoParquet.
- Vendored official RUSLE2 climate records as Parquet.
- Vendored official RUSLE2 climate zones as GeoParquet.
- Attribution and metadata documentation under
  `wepppy/nodb/mods/rusle/data/momm2025/README.md` and
  `wepppy/nodb/mods/rusle/data/rusle2/README.md`.
- Specification updates in `wepppy/nodb/mods/rusle/specification.md`.
- Work-package tracker and active ExecPlan.
- Controller/config/manifest/test work for additional `R` modes.

### Explicitly Out of Scope
- Replacing `cligen_static` as the default `R` mode before validation.
- Pretending the public supplement includes sub-county `REGION` polygons when
  it does not.
- Alaska, Hawaii, or other non-CONUS support not present in the published
  dataset.
- A new national rainfall-zone polygon product unless that becomes an explicit
  approved follow-up decision.

## Stakeholders
- **Primary**: RUSLE NoDb maintainers and WEPP or RUSLE science maintainers.
- **Reviewers**: Maintainers of `wepppy/nodb/mods/rusle`,
  `wepppy/climates/cligen`, and manifest or provenance contracts.
- **Informed**: UI maintainers for run-header mods and GL-dashboard raster
  consumers.

## Success Criteria
- [x] Public Momm 2025 dataset vendored as Parquet under
  `wepppy/nodb/mods/rusle/data/momm2025/`.
- [x] Matching county geometry vendored as GeoParquet under the same
  directory.
- [x] Official RUSLE2 climate records vendored under
  `wepppy/nodb/mods/rusle/data/rusle2/`.
- [x] Official RUSLE2 climate zones vendored as GeoParquet under the same
  directory.
- [x] Dataset attribution, provenance, and limitations documented in a local
  `README.md` for both vendored datasets.
- [x] RUSLE specification updated with academic highlights, mode boundaries,
  and implementation decisions still required.
- [x] Work-package brief, tracker, and active ExecPlan authored.
- [x] Scientific and product decisions for split-county Momm selection and
  polygon-backed canonical selection are resolved and recorded.
- [x] `Rusle` controller supports additional `momm2025_county_region` and
  `canonical_rusle2` `r_mode` values without regressing `cligen_static`.
- [x] Manifest and UI surfaces distinguish WEPP-aligned `cligen_static` from
  planning-climatology `momm2025` and `canonical_rusle2`.
- [x] Targeted tests and validation evidence cover centroid selection,
  provenance, and AOI behavior for the new modes.

## Dependencies

### Prerequisites
- `docs/work-packages/20260320_rusle_r_static_hyetograph_api/` for the current
  shipped `cligen_static` contract.
- `wepppy/nodb/mods/rusle/specification.md` as the scientific source of truth.
- Vendored dataset assets under `wepppy/nodb/mods/rusle/data/momm2025/`.
- Vendored dataset assets under `wepppy/nodb/mods/rusle/data/rusle2/`.

### Blocks
- None. Follow-up work is optional and documented under "Follow-up Work".

## Related Packages
- **Depends on**:
  [20260320_rusle_r_static_hyetograph_api](../20260320_rusle_r_static_hyetograph_api/package.md)
- **Related**:
  [20260320_rusle_ls_factor_wbt](../20260320_rusle_ls_factor_wbt/package.md)
- **Related**:
  [20260321_rusle_k_polaris_implementation](../20260321_rusle_k_polaris_implementation/package.md)
- **Related**:
  [20260321_rusle_nodb_ui](../20260321_rusle_nodb_ui/package.md)

## Timeline Estimate
- **Actual duration**: 2 focused sessions after contract lock.
- **Complexity**: Medium-high.
- **Risk level**: High scientific-contract risk; medium implementation risk.

## References
- `wepppy/nodb/mods/rusle/specification.md` - Canonical RUSLE factor and mode
  contracts.
- `wepppy/nodb/mods/rusle/rusle.py` - Current controller path that only
  consumes scalar static `R`.
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`
  - Vendored monthly erosivity table derived from the public supplement.
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`
  - County geometry companion selected to preserve dataset FIPS compatibility.
- `wepppy/nodb/mods/rusle/data/momm2025/README.md` - Attribution, metadata,
  and transformation notes.
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_records.parquet`
  - Vendored official RUSLE2 climate-record table.
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_zones.geoparquet`
  - Vendored official RUSLE2 climate-zone polygons with deterministic selected
    record joins.
- `wepppy/nodb/mods/rusle/data/rusle2/README.md` - Attribution, metadata, and
  join-caveat notes for the canonical official dataset.
- Momm, H. G., et al., 2025. *Isoerodent surfaces of the continental US for
  conservation planning with the RUSLE2 water erosion model*. *Catena*, 249,
  108879. https://doi.org/10.1016/j.catena.2025.108879
- USDA ARS Agricultural Data Commons. *Data from: Isoerodent surfaces of the
  continental US for conservation planning with the RUSLE2 water erosion
  model*. https://doi.org/10.15482/USDA.ADC/28821569.v1
- Official RUSLE2 climate database index.
  https://fargo.nserl.purdue.edu/rusle2_dataweb/NRCS_Climate_Database.htm
- Official RUSLE2 climate ZIP directory.
  https://fargo.nserl.purdue.edu/RUSLE2_ftp/Climate_data/

## Deliverables
- Vendored `momm2025` and official `rusle2` data assets in Parquet and
  GeoParquet form.
- Local dataset `README.md` files with attribution and metadata.
- Package brief, tracker, and active ExecPlan.
- Updated RUSLE specification for `cligen_static`, `momm2025_county_region`,
  and `canonical_rusle2` support.
- Runtime code, tests, and manifest or UI updates for the new `R` modes.

## Follow-up Work
- If maintainers require true sub-county `REGION` spatialization, scope a
  dedicated rainfall-zone polygon derivation package.
- If `canonical_rusle2` needs to support the official climate-table rows that
  do not have polygon-backed joins, scope a follow-up contract for table-only
  locales before public rollout.
