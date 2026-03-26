# RUSLE Planning-Climatology R Modes

This ExecPlan is a living document. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a RUSLE run will be able to choose additional planning
climatology rainfall-erosivity modes based on the public Momm et al. (2025)
county or `REGION` monthly isoerodent dataset and on the vendored official
RUSLE2 climate-database release, while preserving the current `cligen_static`
path for users who want the best approximation of the erosivity used by WEPP
in the run's own climate record. The locked v1 contract keeps the external
modes on the existing scalar-`R` controller path. Users should be able to see
the chosen source clearly in `rusle/manifest.json`, and reviewers should be
able to trace the external-mode output back to vendored Parquet or GeoParquet
artifacts in the repository.

This plan intentionally separates two scientific purposes:

- `cligen_static` approximates the erosivity used by WEPP for the run.
- `momm2025` approximates a published RUSLE2 planning climatology for CONUS.
- `canonical_rusle2` approximates the vendored official RUSLE2 planning
  climatology release.

The public supplement is materially useful but incomplete for one key need:
some counties have multiple `REGION` rows and the public files do not include
sub-county `REGION` polygons. The locked v1 contract now answers three of the
four initial questions:

- output stays scalar rather than spatial `r.tif`
- multi-county AOIs use watershed centroid county selection
- provenance wording must explicitly distinguish WEPP-derived versus county
  climatology `R`

Resolved checkpoint outcomes (2026-03-26):

- counties where centroid lookup lands on multiple public `REGION` rows are
  rejected explicitly in v1 (`momm2025_county_region` does not guess).
- `canonical_rusle2` is explicitly limited to polygon-backed official links;
  unsupported/table-only selections fail with clear errors.

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
- [x] Vendor the official RUSLE2 climate tables and climate-zone polygons as
  Parquet or GeoParquet artifacts under `wepppy/nodb/mods/rusle/data/rusle2/`.
- [x] Expand the package and specification scope so `canonical_rusle2` is a
  planned sibling `R` mode.
- [x] (2026-03-26 00:00Z) Resolve the split-county `REGION` spatialization
  contract (`momm2025_county_region` rejects split-county selections in v1).
- [x] (2026-03-26 00:00Z) Resolve the supported-area contract for
  `canonical_rusle2` (polygon-backed official links only in v1).
- [x] (2026-03-26 00:00Z) Implement the external runtime paths in the `Rusle`
  controller.
- [x] (2026-03-26 00:00Z) Add manifest, UI, and regression coverage for the
  new `R` modes.
- [x] (2026-03-26 00:00Z) Run focused validation and close the package.

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

- Observation: The vendored official RUSLE2 climate release is broader than
  the official polygon bundle.
  Evidence: `rusle2_official_climate_records.parquet` contains 10,319 rows and
  9,091 non-null `official_rec_link` values, while
  `rusle2_official_climate_zones.geoparquet` contains 8,970 unique polygon
  `REC_LINK` values and leaves 41 climate rows table-only.

- Observation: The normalized official `r_monthly_*` fields are entirely null
  in the vendored official dataset, so v1 canonical runtime selection must use
  annual `r_factor_english` conversion to SI.
  Evidence: Inspection of
  `rusle2_official_climate_records.parquet` and
  `rusle2_official_climate_zones.geoparquet` shows zero non-null
  `r_monthly_sum` rows.

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

- Decision: Add the vendored official dataset as planned `canonical_rusle2`
  mode rather than leaving it as reference-only data.
  Rationale: The repo already carries cleaned official RUSLE2 tables and
  polygons, so they should be first-class planning-climatology inputs beside
  the Momm update.
  Date/Author: 2026-03-25 / User + Codex.

- Decision: `momm2025_county_region` rejects split-county centroid selections
  (multiple public `REGION` rows) in v1.
  Rationale: The public supplement does not ship sub-county `REGION` polygons,
  so selecting one silently would fabricate unsupported spatial precision.
  Date/Author: 2026-03-26 / User + Codex.

- Decision: `canonical_rusle2` v1 is polygon-backed only and rejects
  unsupported/table-only selections explicitly.
  Rationale: The official climate table includes rows with no polygon-backed
  join, and silent fallback would blur provenance and selection semantics.
  Date/Author: 2026-03-26 / User + Codex.

## Outcomes & Retrospective

Runtime and closeout are complete. The package now has:

- implemented `r_mode` support for `momm2025_county_region` and
  `canonical_rusle2` in `Rusle`
- explicit v1 failure contracts for split-county Momm selections and
  unsupported/table-only canonical selections
- manifest provenance fields that distinguish WEPP-derived versus
  planning-climatology `R` sources
- rq-engine payload filtering and run-page UI controls for the new `r_mode`
  options
- focused regression coverage across selector logic, controller runtime,
  microservice routes, and controller JS behavior

Validation evidence:

- `wctl run-pytest tests/nodb/mods -k rusle --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k rusle --maxfail=1`
- `wctl run-npm test -- rusle`
- `wctl run-npm lint`
- `wctl run-pytest tests --maxfail=1`

## Context and Orientation

The current `Rusle` controller lives in `wepppy/nodb/mods/rusle/rusle.py`. It
expects a scalar `R` value from `cli_calculate_static_r` and writes a constant
`rusle/r.tif` for the run. That means the current controller contract is
"single scalar `R` first, rasterized later," not "gridded erosivity surface."

The new data assets live in:

- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet`
- `wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet`
- `wepppy/nodb/mods/rusle/data/momm2025/README.md`
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_records.parquet`
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_zones.geoparquet`
- `wepppy/nodb/mods/rusle/data/rusle2/README.md`

The main Parquet contains monthly erosivity values (`jan` through `dec`) plus
`annual_r` for county or `REGION` rows. The GeoParquet contains one county
geometry per dataset FIPS plus diagnostic columns such as `dataset_row_count`,
`has_split_regions`, and `region_labels`.

The official RUSLE2 Parquet contains normalized climate records from the public
state or territory climate databases. The official GeoParquet contains the
public polygon bundle plus one deterministic selected climate record per
official `REC_LINK`, along with duplicate diagnostics so the selection is
auditable.

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

The key limitation of the official dataset is different: the official climate
record table is broader than the official polygon bundle, so some climate rows
remain table-only and cannot be reached by polygon centroid lookup without an
additional contract.

## Plan of Work

Execution summary:

1. Resolved contract checkpoints:
   - `momm2025_county_region` split-county selections are explicit errors.
   - `canonical_rusle2` is polygon-backed only with explicit unsupported-case
     errors.
2. Implemented data-access selectors in
   `wepppy/nodb/mods/rusle/r_modes.py`.
3. Integrated `r_mode` branching into
   `wepppy/nodb/mods/rusle/rusle.py`, including manifest provenance and README
   source labeling.
4. Exposed `r_mode` in rq-engine payload filtering and run-page controls.
5. Added focused regression coverage and validation evidence.

## File-Level Edit Map

Primary runtime files expected to change in `/workdir/wepppy`:

- `wepppy/nodb/mods/rusle/rusle.py`
- `wepppy/nodb/mods/rusle/specification.md`
- `wepppy/nodb/mods/rusle/README.md` if a user-facing mode summary is needed
- `wepppy/nodb/mods/rusle/data/momm2025/README.md`
- `wepppy/nodb/mods/rusle/data/rusle2/README.md`
- tests under `tests/nodb/mods/` and any RUSLE-specific route or manifest test
  modules that already cover `r_mode` behavior

Recommended new helper module paths:

- `wepppy/nodb/mods/rusle/r_modes.py`

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
    wctl doc-lint --path wepppy/nodb/mods/rusle/data/rusle2/README.md

7. Before closure, run at least:

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance is complete when:

- `Rusle` accepts external `r_mode` values for Momm 2025 and Canonical RUSLE2
  without regressing `cligen_static`.
- The selected `R` source is explicit in `rusle/manifest.json`.
- The runtime either handles or explicitly rejects unresolved split-county
  `REGION` cases according to the locked contract, without silent fallback.
- The runtime either handles or explicitly rejects unsupported table-only
  canonical official rows according to the locked contract, without silent
  fallback.
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
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_records.parquet`
- `wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_zones.geoparquet`

## Interfaces and Dependencies

The mode name should remain explicit and stable. Recommended config name:
`momm2025_county_region`.

Recommended sibling config name:
`canonical_rusle2`.

Any helper introduced for the new mode should make these outputs explicit:

- selected county from watershed centroid lookup
- selected official `REC_LINK` when `canonical_rusle2` is used
- selected `REGION` labels, if the approved contract ever uses them
- monthly erosivity values
- annual `R`
- provenance fields needed by `rusle/manifest.json`

The implementation must not add a silent fallback from `momm2025` or
`canonical_rusle2` to `cligen_static`. If the chosen county, polygon, or
`REGION` rule cannot be applied, the runtime should fail with a clear,
contract-compliant error.
