# RUSLE Momm 2025 R-Mode Integration

This ExecPlan is a living document. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a RUSLE run will be able to choose a second rainfall
erosivity mode based on the public Momm et al. (2025) county or `REGION`
monthly isoerodent dataset for the continental US, while preserving the
current `cligen_static` path for users who want the best approximation of the
erosivity used by WEPP in the run's own climate record. The locked v1 contract
keeps `momm2025` on the existing scalar-`R` controller path and selects the
county by watershed centroid. Users should be able to see the chosen source
clearly in `rusle/manifest.json`, and reviewers should be able to trace the
Momm-derived output back to a vendored Parquet row or rows and county geometry
in the repository.

This plan intentionally separates two scientific purposes:

- `cligen_static` approximates the erosivity used by WEPP for the run.
- `momm2025` approximates a published RUSLE2 planning climatology for CONUS.

The public supplement is materially useful but incomplete for one key need:
some counties have multiple `REGION` rows and the public files do not include
sub-county `REGION` polygons. The locked v1 contract now answers three of the
four initial questions:

- output stays scalar rather than spatial `r.tif`
- multi-county AOIs use watershed centroid county selection
- provenance wording must explicitly distinguish WEPP-derived versus county
  climatology `R`

The remaining checkpoint is how to handle counties where centroid lookup still
lands on multiple public `REGION` rows.

## Progress

- [x] (2026-03-25 00:00Z) Reviewed current `R` runtime behavior in
  `wepppy/nodb/mods/rusle/rusle.py` and the scientific contract in
  `wepppy/nodb/mods/rusle/specification.md`.
- [x] (2026-03-25 00:00Z) Normalized the public Momm 2025 CSV into
  `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`.
- [x] (2026-03-25 00:00Z) Vendored matching county geometry as
  `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`.
- [x] (2026-03-25 00:00Z) Updated package docs and the RUSLE specification to
  frame `momm2025` as a planned additional `R` mode.
- [x] Lock the v1 `momm2025` scalar output contract and record it in this
  ExecPlan.
- [x] Lock watershed-centroid county selection for multi-county AOIs.
- [x] Lock provenance wording that distinguishes WEPP-aligned
  `cligen_static` from Momm county climatology.
- [ ] Resolve the split-county `REGION` spatialization contract before code
  implementation begins.
- [ ] Implement the `momm2025` runtime path in the `Rusle` controller.
- [ ] Add manifest, UI, and regression coverage for the new `R` mode.
- [ ] Run final validation and close the package.

## Surprises & Discoveries

- Observation: The public dataset contains 8,247 county or `REGION` rows but
  only 3,107 unique county FIPS, so many counties are single-row while 410
  counties are split into multiple `REGION` rows.
  Evidence: Parquet inspection of
  `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`.

- Observation: The dataset still uses legacy FIPS values `46113` (Shannon
  County, SD) and `51515` (Bedford city, VA), which break joins against newer
  county boundary vintages.
  Evidence: Comparison against local 2017 county boundaries and successful
  rejoin against the 2010 Census 500k county layer.

- Observation: The public supplement exposes `REGION` labels but not the
  geometry needed to assign them spatially inside counties.
  Evidence: Public CSV rows contain only county fields, state fields, and a
  `REGION` label; no polygon or coordinate product accompanies the supplement.

## Decision Log

- Decision: Keep `cligen_static` as the default and present Momm 2025 as an
  additional mode, not a replacement.
  Rationale: `cligen_static` is tied to the run's WEPP climate record and is
  the better approximation of what WEPP itself used for the run.
  Date/Author: 2026-03-25 / Codex.

- Decision: Vendor the county companion as GeoParquet built from the 2010
  Census 500k county boundaries.
  Rationale: This is the cleanest geometry vintage that still preserves the
  legacy FIPS used by the public dataset.
  Date/Author: 2026-03-25 / Codex.

- Decision: Do not fake sub-county `REGION` geometry.
  Rationale: The public supplement does not provide polygons, so pretending
  otherwise would make the science and provenance less trustworthy.
  Date/Author: 2026-03-25 / Codex.

- Decision: `momm2025` v1 remains on the scalar-`R` contract and writes a
  constant `rusle/r.tif` from the selected annual `R`.
  Rationale: The public release is county or `REGION` climatology, not a
  gridded erosivity raster product.
  Date/Author: 2026-03-25 / User + Codex.

- Decision: Multi-county AOIs select the county containing the watershed
  centroid.
  Rationale: Centroid semantics are deterministic and easy to trace in
  provenance.
  Date/Author: 2026-03-25 / User + Codex.

- Decision: User-facing provenance wording must label `cligen_static` as
  `WEPP Climate-Derived R` and `momm2025` as `Momm 2025 County Climatology`.
  Rationale: The two modes serve different scientific purposes and need clear
  naming.
  Date/Author: 2026-03-25 / User + Codex.

## Outcomes & Retrospective

Scoping and data vendoring are complete. The package now has the primary data
assets, a county geometry companion, an attribution README, and a specification
update that distinguishes WEPP-aligned versus planning-climatology `R`
purposes. The scalar-output, centroid-selection, and provenance-label
contracts are now fixed. Runtime implementation remains open because split-
county `REGION` handling is still unresolved.

## Context and Orientation

The current `Rusle` controller lives in `wepppy/nodb/mods/rusle/rusle.py`. It
expects a scalar `R` value from `cli_calculate_static_r` and writes a constant
`rusle/r.tif` for the run. That means the current controller contract is
"single scalar `R` first, rasterized later," not "gridded erosivity surface."

The new data assets live in:

- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`
- `wepppy/nodb/mods/rusle/data/momm2025/README.md`

The main Parquet contains monthly erosivity values (`jan` through `dec`) plus
`annual_r` for county or `REGION` rows. The GeoParquet contains one county
geometry per dataset FIPS plus diagnostic columns such as `dataset_row_count`,
`has_split_regions`, and `region_labels`.

The public Momm paper is important because it updates RUSLE2 operational
isoerodent generation for the continental US. The published highlights relevant
to this repo are:

- It is designed for RUSLE2 conservation-planning climatology, not for WEPP
  replay of a specific run's climate file.
- It produces monthly values because RUSLE2 stores and consumes monthly
  erosivity distributions.
- It uses a reproducible interpolation workflow rather than relying on older
  hand-built surfaces.
- The paper emphasizes smoother spatial and temporal behavior while keeping
  absolute values broadly aligned with official RUSLE2 practice.

The key limitation is equally important: the public supplement gives county or
`REGION` tables, but not the sub-county polygons needed to spatialize the
split-county rows directly.

## Plan of Work

Milestone 1 is now partially resolved. Read the vendored dataset README, the
RUSLE specification, and the current `Rusle` controller. The remaining
decision work must answer one question:

1. How are counties with multiple `REGION` rows handled when public polygons do
   not exist?

Locked v1 decisions:

- Keep the existing scalar-`R` controller contract.
- Select the county using watershed centroid semantics.
- Do not expose generic or ambiguous provenance labels.

Recommended default if maintainers want the smallest truthful v1:

- Do not expose split-county `REGION` logic until an approved rule exists.
  Either:
  - collapse split counties to an explicit county-level aggregate with
    documented loss of within-county detail, or
  - scope a follow-up package to derive defensible `REGION` polygons before
    public rollout.

Milestone 2 implements the data-access layer. Add a small module under
`wepppy/nodb/mods/rusle/` for loading the vendored Parquet or GeoParquet,
finding the watershed centroid county, and returning a clear typed result that
includes selected county FIPS, selected `REGION` labels if any, monthly values,
and annual `R`.

Milestone 3 integrates the new mode into `wepppy/nodb/mods/rusle/rusle.py`.
The controller should accept a new `r_mode` value, branch explicitly between
`cligen_static` and `momm2025`, compute the chosen scalar or raster contract,
write `rusle/r.tif`, and record provenance in `rusle/manifest.json`.

Milestone 4 exposes the mode in configuration and UI surfaces. Update the
spec-driven config docs, controller config parsing, and any user-visible method
summary rows so the source of `R` is clear without requiring users to inspect
the raw manifest JSON.

Milestone 5 adds regression coverage and closeout evidence. Tests should cover
single-county AOIs, multi-county AOIs, unsupported or unresolved split-county
cases, manifest provenance, and backward compatibility for `cligen_static`.

## File-Level Edit Map

Primary runtime files expected to change in `/workdir/wepppy`:

- `wepppy/nodb/mods/rusle/rusle.py`
- `wepppy/nodb/mods/rusle/specification.md`
- `wepppy/nodb/mods/rusle/README.md` if a user-facing mode summary is needed
- `wepppy/nodb/mods/rusle/data/momm2025/README.md`
- tests under `tests/nodb/mods/` and any RUSLE-specific route or manifest test
  modules that already cover `r_mode` behavior

Recommended new helper module paths:

- `wepppy/nodb/mods/rusle/r_momm2025.py`
- `wepppy/nodb/mods/rusle/r_momm2025_manifest.py` if provenance logic grows
  beyond a small helper

## Concrete Steps

Run commands from `/workdir/wepppy` unless noted.

1. Reconfirm vendored data readability:

    /workdir/wepppy/.venv/bin/python - <<'PY'
    import pandas as pd
    import geopandas as gpd
    base = "wepppy/nodb/mods/rusle/data/momm2025"
    df = pd.read_parquet(f"{base}/momm2025_county_region_monthly_r.parquet")
    gdf = gpd.read_parquet(f"{base}/momm2025_counties_conus_2010_500k.geoparquet")
    print(len(df), df["fips"].nunique(), len(gdf))
    PY

2. Lock the Milestone 1 decision checkpoint in:

    docs/work-packages/20260325_rusle_momm2025_r_mode/tracker.md
    docs/work-packages/20260325_rusle_momm2025_r_mode/prompts/active/rusle_momm2025_r_mode_execplan.md

3. Implement the data-access helper and add focused tests:

    wctl run-pytest tests/nodb/mods -k rusle --maxfail=1

4. Integrate the mode into `Rusle` runtime and re-run focused tests:

    wctl run-pytest tests/nodb/mods -k rusle --maxfail=1

5. If UI or route behavior changes, run the smallest relevant route suite and
   document it in the tracker.

6. Re-lint docs when specification or package documents change:

    wctl doc-lint --path docs/work-packages/20260325_rusle_momm2025_r_mode/package.md
    wctl doc-lint --path docs/work-packages/20260325_rusle_momm2025_r_mode/tracker.md
    wctl doc-lint --path docs/work-packages/20260325_rusle_momm2025_r_mode/prompts/active/rusle_momm2025_r_mode_execplan.md
    wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md
    wctl doc-lint --path wepppy/nodb/mods/rusle/data/momm2025/README.md

7. Before closure, run at least:

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance is complete when:

- `Rusle` accepts a second `r_mode` for Momm 2025 without regressing
  `cligen_static`.
- The selected `R` source is explicit in `rusle/manifest.json`.
- The runtime either handles or explicitly rejects unresolved split-county
  `REGION` cases according to the locked contract, without silent fallback.
- Users and reviewers can trace the source data to the vendored Parquet or
  GeoParquet assets and the local attribution README.
- Focused tests pass, and the final package notes record the exact validation
  commands used.

## Idempotence and Recovery

- Re-running the Parquet or GeoParquet read checks is safe and should not
  change any files.
- Any future normalization scripts for Momm data should overwrite only the
  vendored `momm2025` files, not unrelated RUSLE assets.
- If a chosen split-county `REGION` strategy proves invalid, revert only the
  `momm2025` runtime path and leave `cligen_static` untouched.

## Artifacts and Notes

Package documents that must remain synchronized:

- `docs/work-packages/20260325_rusle_momm2025_r_mode/package.md`
- `docs/work-packages/20260325_rusle_momm2025_r_mode/tracker.md`
- `docs/work-packages/20260325_rusle_momm2025_r_mode/prompts/active/rusle_momm2025_r_mode_execplan.md`
- `wepppy/nodb/mods/rusle/specification.md`
- `wepppy/nodb/mods/rusle/data/momm2025/README.md`

Important data assets:

- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`

## Interfaces and Dependencies

The mode name should remain explicit and stable. Recommended config name:
`momm2025_county_region`.

Any helper introduced for the new mode should make these outputs explicit:

- selected county from watershed centroid lookup
- selected `REGION` labels, if the approved contract ever uses them
- monthly erosivity values
- annual `R`
- provenance fields needed by `rusle/manifest.json`

The implementation must not add a silent fallback from `momm2025` to
`cligen_static`. If the chosen county or `REGION` rule cannot be applied, the
runtime should fail with a clear, contract-compliant error.
