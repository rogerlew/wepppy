# RUSLE Momm 2025 R-Mode Integration

**Status**: Open (2026-03-25)

## Overview
This work package adds a second rainfall-erosivity (`R`) estimation path for
the RUSLE NoDb mod based on the public Momm et al. (2025) continental-US
RUSLE2 isoerodent dataset. The package keeps `cligen_static` as the
WEPP-aligned default when the goal is to approximate the erosivity used by the
run's WEPP climate, while defining a separate `momm2025` mode for users who
want a county or rainfall-zone planning climatology tied more closely to the
published RUSLE2 surfaces.

The package begins with dataset vendoring and specification updates, then
proceeds to the remaining design and implementation work needed to expose the
new `R` mode in the controller, manifests, and UI without misrepresenting what
the public supplement can and cannot support.

## Objectives
- Vendor the public Momm et al. (2025) county or region monthly erosivity data
  in repo-native Parquet form with attribution and reproducible metadata.
- Vendor a matching county geometry layer as GeoParquet and document why the
  2010 county vintage is required for FIPS compatibility.
- Update the RUSLE specification so `cligen_static` is framed as the
  WEPP-aligned approximation path and Momm 2025 is framed as a separate,
  RUSLE2-oriented climatology path.
- Define the implementation contract for a future `momm2025` `r_mode`,
  including provenance, AOI-to-county selection, and split-county `REGION`
  behavior.
- Implement the new mode with targeted tests after the remaining scientific
  and product decisions are resolved.

## Scope
This package covers dataset vendoring, documentation, implementation planning,
and the eventual runtime integration of a new Momm 2025-based `R` mode.

### Included
- Vendored `momm2025` monthly erosivity table in Parquet format.
- Vendored matching county geometry as GeoParquet.
- Attribution and metadata documentation under
  `wepppy/nodb/mods/rusle/data/momm2025/README.md`.
- Specification updates in `wepppy/nodb/mods/rusle/specification.md`.
- Work-package tracker and active ExecPlan.
- Future controller/config/manifest/test work for the additional `R` mode.

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
- [x] Dataset attribution, provenance, and limitations documented in a local
  `README.md`.
- [x] RUSLE specification updated with academic highlights, mode boundaries,
  and implementation decisions still required.
- [x] Work-package brief, tracker, and active ExecPlan authored.
- [ ] Scientific and product decisions for county or `REGION` spatialization
  are resolved and recorded.
- [ ] `Rusle` controller supports an additional `momm2025`-based `r_mode`
  without regressing `cligen_static`.
- [ ] Manifest and UI surfaces distinguish WEPP-aligned `cligen_static` from
  planning-climatology `momm2025`.
- [ ] Targeted tests and validation evidence cover county selection,
  provenance, and AOI behavior for the new mode.

## Dependencies

### Prerequisites
- `docs/work-packages/20260320_rusle_r_static_hyetograph_api/` for the current
  shipped `cligen_static` contract.
- `wepppy/nodb/mods/rusle/specification.md` as the scientific source of truth.
- Vendored dataset assets under `wepppy/nodb/mods/rusle/data/momm2025/`.

### Blocks
- Runtime implementation of a public `momm2025` `r_mode`.
- UI or manifest exposure of a second `R` source in the RUSLE mod.

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
- **Expected duration**: 1-2 weeks after the remaining `R`-mode decisions are
  locked.
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
- Momm, H. G., et al., 2025. *Isoerodent surfaces of the continental US for
  conservation planning with the RUSLE2 water erosion model*. *Catena*, 249,
  108879. https://doi.org/10.1016/j.catena.2025.108879
- USDA ARS Agricultural Data Commons. *Data from: Isoerodent surfaces of the
  continental US for conservation planning with the RUSLE2 water erosion
  model*. https://doi.org/10.15482/USDA.ADC/28821569.v1

## Deliverables
- Vendored `momm2025` data assets in Parquet and GeoParquet form.
- Local dataset `README.md` with attribution and metadata.
- Package brief, tracker, and active ExecPlan.
- Updated RUSLE specification for `cligen_static` guidance and planned
  `momm2025` support.
- Future runtime code, tests, and manifest or UI updates for the new `R` mode.

## Follow-up Work
- If maintainers require true sub-county `REGION` spatialization, scope a
  dedicated rainfall-zone polygon derivation package.
- If county-only aggregation is approved for v1, follow with validation
  against published county or region examples before making it the default.

