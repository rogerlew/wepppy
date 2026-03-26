# Tracker - RUSLE Planning-Climatology R Modes

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Started**: 2026-03-25  
**Current phase**: Complete - runtime, UI, manifest, tests, and docs closed  
**Last updated**: 2026-03-26  
**Next milestone**: Optional follow-up packages only (no open blocker in this package)  
**Active ExecPlan**:
`prompts/active/rusle_momm2025_r_mode_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed the current `cligen_static` `R` contract in
  `wepppy/nodb/mods/rusle/specification.md` and `wepppy/nodb/mods/rusle/rusle.py`
  (2026-03-25).
- [x] Inspected the public Momm 2025 CSV structure and normalized it into
  `momm2025_county_region_monthly_r.parquet` (2026-03-25).
- [x] Verified that the public dataset covers 3,107 county FIPS in the
  conterminous US plus DC, with 410 counties carrying multiple `REGION` rows
  (2026-03-25).
- [x] Determined that 2010 Census counties are the best geometry match because
  the dataset still uses FIPS `46113` (Shannon County, SD) and `51515`
  (Bedford city, VA), which are absent from newer vintages (2026-03-25).
- [x] Vendored `momm2025_counties_conus_2010_500k.geoparquet` with matching
  FIPS coverage and source metadata (2026-03-25).
- [x] Authored the package brief, tracker, and active ExecPlan scaffold
  (2026-03-25).
- [x] Updated the RUSLE specification with Momm 2025 mode guidance, academic
  highlights, and explicit open implementation decisions (2026-03-25).
- [x] Added `wepppy/nodb/mods/rusle/data/momm2025/README.md` with attribution,
  metadata, and limitations (2026-03-25).
- [x] Normalized the official RUSLE2 climate-database release into
  `rusle2_official_climate_records.parquet`,
  `rusle2_official_climate_zones.geoparquet`, and a source inventory Parquet
  (2026-03-25).
- [x] Added `wepppy/nodb/mods/rusle/data/rusle2/README.md` with attribution,
  metadata, join policy, and table-only caveats (2026-03-25).
- [x] Locked `momm2025` v1 to a scalar run-level `R` that still writes a
  constant `rusle/r.tif`, not a spatially varying erosivity raster
  (2026-03-25).
- [x] Locked multi-county AOI selection to watershed-centroid county lookup
  for `momm2025` (2026-03-25).
- [x] Locked provenance or UI wording so `cligen_static` remains the
  WEPP-aligned `R` path and `momm2025` is labeled as county climatology
  (2026-03-25).
- [x] Added `canonical_rusle2` as a planned sibling `R` mode in the package
  and specification scope (2026-03-25).
- [x] Registered the package in `PROJECT_TRACKER.md` backlog and linted the
  changed Markdown files (2026-03-25).
- [x] Locked split-county handling contract for `momm2025_county_region`:
  reject counties with multiple public `REGION` rows explicitly (2026-03-26).
- [x] Locked `canonical_rusle2` supported-area contract: watershed-centroid
  polygon-backed official links only, explicit rejection for unsupported/table-
  only cases (2026-03-26).
- [x] Implemented runtime selectors in
  `wepppy/nodb/mods/rusle/r_modes.py` with deterministic centroid lookup and
  explicit failure behavior (2026-03-26).
- [x] Integrated `r_mode` branching into
  `wepppy/nodb/mods/rusle/rusle.py` with manifest provenance and README
  updates (2026-03-26).
- [x] Exposed `r_mode` through rq-engine (`rusle_routes.py`) and run-page UI
  controls (`rusle_pure.htm`, `controllers_js/rusle.js`) (2026-03-26).
- [x] Added regression coverage in
  `tests/nodb/mods/test_rusle_r_modes.py`,
  `tests/nodb/mods/test_rusle_controller.py`,
  `tests/microservices/test_rq_engine_rusle_routes.py`, and
  `controllers_js/__tests__/rusle.test.js` (2026-03-26).

## Timeline

- **2026-03-25** - Package created and scoped.
- **2026-03-25** - Public Momm 2025 data normalized and vendored as Parquet.
- **2026-03-25** - Matching county geometry vendored as GeoParquet after FIPS
  vintage review.
- **2026-03-25** - Official RUSLE2 climate tables and polygons normalized into
  vendored Parquet and GeoParquet assets.
- **2026-03-25** - Specification, tracker, and data README updated.
- **2026-03-25** - Scalar, centroid, and provenance decisions locked for the
  planned runtime contract.
- **2026-03-25** - `canonical_rusle2` added as a planned external `R` mode.
- **2026-03-26** - Split-county and canonical polygon-backed contracts
  resolved and documented.
- **2026-03-26** - `r_mode` runtime implementation shipped in `Rusle`,
  including `momm2025_county_region` and `canonical_rusle2`.
- **2026-03-26** - RQ/API payload filtering, run-page UI controls, manifest
  provenance, and regression coverage updated.
- **2026-03-26** - Focused validation gates passed; package closed.

## Decisions Log

### 2026-03-25: Keep `cligen_static` as the WEPP-aligned default
**Context**: The new dataset is valuable, but it is a planning climatology and
does not use the run's actual WEPP storm record.

**Options considered**:
1. Replace `cligen_static` with the Momm 2025 dataset.
2. Keep `cligen_static` as the default WEPP-aligned mode and add Momm 2025 as
   an additional `R` mode.

**Decision**: Option 2.

**Impact**: The product can distinguish between "approximate the erosivity used
by WEPP for this run" and "use a published RUSLE2 planning climatology."

---

### 2026-03-25: Vendor the county companion as GeoParquet from the 2010 Census county layer
**Context**: The public supplement uses legacy FIPS values not preserved in the
local 2017 county boundary dataset.

**Options considered**:
1. Use the existing 2017 county boundary layer and accept FIPS mismatches.
2. Use the 2010 Census county 500k boundaries that still contain the dataset's
   legacy FIPS values.

**Decision**: Option 2.

**Impact**: County joins are exact for the vendored dataset and for both legacy
FIPS examples observed during review.

---

### 2026-03-25: Treat split-county `REGION` geometry as an open scientific blocker
**Context**: The public supplement exposes `REGION` labels but does not ship
polygon geometry for those sub-county zones.

**Options considered**:
1. Pretend the labels imply a geometry and silently choose one.
2. Surface the missing geometry as a real design decision and keep the package
   honest about what the public data can support today.

**Decision**: Option 2.

**Impact**: The package can move forward on data vendoring and documentation
without locking an invalid spatialization contract.

---

### 2026-03-25: Keep `momm2025` on the existing scalar-`R` controller contract
**Context**: The public release is county or `REGION` climatology, not a
cell-scale erosivity surface.

**Options considered**:
1. Force the dataset into a spatially varying `r.tif`.
2. Preserve the current scalar-`R` contract and write a constant `r.tif` from
   the selected annual `R`.

**Decision**: Option 2.

**Impact**: The runtime does not imply within-county spatial detail that the
public files do not actually provide.

---

### 2026-03-25: Select counties by watershed centroid
**Context**: The runtime needs one deterministic county lookup rule when an
AOI spans more than one county.

**Options considered**:
1. Area-weight multiple counties.
2. Select the county containing the watershed centroid.

**Decision**: Option 2.

**Impact**: County selection is deterministic and easy to explain in
provenance, but split-county `REGION` handling still remains open when the
centroid lands in a county with multiple public rows.

---

### 2026-03-25: Use explicit provenance wording to separate WEPP-aligned and planning-climatology `R`
**Context**: Users need to distinguish the current WEPP-climate-derived path
from the planned Momm county climatology path.

**Options considered**:
1. Keep generic `R mode` wording.
2. Use explicit user-facing labels and help text for each mode.

**Decision**: Option 2.

**Impact**: The product can label:

- `cligen_static` as `WEPP Climate-Derived R`
- `momm2025` as `Momm 2025 County Climatology`

and can describe their different purposes without forcing users to inspect raw
manifest internals.

---

### 2026-03-25: Promote the vendored official dataset to planned `canonical_rusle2` mode
**Context**: The repo now vendors a cleaned official RUSLE2 climate-record and
polygon dataset, not just the Momm 2025 update.

**Options considered**:
1. Keep the official dataset as internal reference data only.
2. Add the official dataset as a planned sibling `R` mode with explicit
   provenance and runtime-scoping rules.

**Decision**: Option 2.

**Impact**: The package now covers two external planning-climatology modes:
the updated CONUS Momm dataset and the vendored canonical official RUSLE2
baseline.

---

### 2026-03-26: Reject split-county `REGION` cases for `momm2025_county_region` v1
**Context**: Public Momm files expose county or `REGION` labels but do not
ship sub-county geometry for split counties.

**Options considered**:
1. Guess a split-county `REGION` selection rule without polygons.
2. Aggregate split counties silently to one county-level value.
3. Reject split-county selections explicitly until defensible geometry/rule is
   approved.

**Decision**: Option 3.

**Impact**: Runtime stays scientifically honest; no silent fallback or
fabricated sub-county behavior is introduced.

---

### 2026-03-26: Limit `canonical_rusle2` v1 to polygon-backed official links
**Context**: Official climate tables contain rows not represented by the
official polygon bundle.

**Options considered**:
1. Attempt table-only fallback without polygon centroid contract.
2. Restrict v1 to polygon-backed records and reject unsupported selections.

**Decision**: Option 2.

**Impact**: Runtime behavior is explicit and deterministic, and provenance can
always trace to the vendored polygon-backed selection.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Split-county `REGION` rows cannot be spatialized defensibly from public files alone | High | High | v1 rejects split-county centroid selections explicitly and records why in runtime errors/provenance | Mitigated |
| The official RUSLE2 polygon bundle does not cover every climate-table row, so `canonical_rusle2` needs a clear supported-area contract | High | Medium | v1 is explicitly polygon-backed only; unsupported/table-only selections fail with contract-compliant errors | Mitigated |
| Users may confuse Momm 2025 planning climatology with WEPP-run erosivity | High | Medium | Keep `cligen_static` documented as WEPP-aligned default and make provenance explicit in manifests or UI | Mitigated |
| County FIPS mismatches against newer boundary vintages break joins | Medium | Medium | Vendor 2010 county GeoParquet with exact FIPS match and source metadata | Mitigated |
| Monthly climatology could be over-simplified into a single annual scalar without recording the loss of seasonality | Medium | Medium | Record mode semantics in spec and manifest; do not hide aggregation choices | Mitigated |

## Verification Checklist

### Data
- [x] Main Parquet reads successfully with repo `.venv` and contains the
  expected monthly plus `annual_r` columns.
- [x] County GeoParquet reads successfully with `geopandas`.
- [x] County GeoParquet FIPS set matches the main Parquet exactly.

### Documentation
- [x] Package brief, tracker, and active ExecPlan authored.
- [x] `PROJECT_TRACKER.md` backlog updated.
- [x] RUSLE specification updated for `cligen_static`,
  `momm2025_county_region`, and `canonical_rusle2` runtime contracts.
- [x] Local dataset `README.md` files added with attribution and metadata.

### Validation
- [x] `wctl doc-lint` passes for changed Markdown files.
- [x] Runtime validation for `momm2025_county_region` and `canonical_rusle2`
  selector and controller paths passed in focused test suites.

## Progress Notes

### 2026-03-25: Scoping, data vendoring, and specification update
**Agent/Contributor**: Codex

**Work completed**:
- Researched the Momm 2025 public supplement and normalized the public CSV into
  repo-native Parquet.
- Derived and vendored a matching county GeoParquet after confirming that the
  dataset still expects 2010-vintage county FIPS coverage.
- Normalized and vendored the official RUSLE2 climate-table and polygon
  release as Parquet and GeoParquet.
- Updated package docs and the RUSLE specification so the new external modes
  are framed as planned rather than silently shipped.
- Locked the scalar, watershed-centroid, and provenance decisions that do not
  depend on missing `REGION` geometry.
- Captured the remaining split-county and polygon-backed scientific or product
  decisions needed before runtime implementation starts.

**Blockers encountered**:
- The public supplement does not include sub-county `REGION` polygons, so
  split-county spatialization is the main open contract question.

**Next steps**:
1. Approve a split-county `REGION` strategy for counties where centroid lookup
   still lands on multiple public Momm rows.
2. Approve the supported-area contract for `canonical_rusle2`, especially for
   the table-only official climate rows.
3. Implement the runtime modes in `wepppy/nodb/mods/rusle/`.
4. Add manifest, UI, and regression coverage.

**Test results**:
- Data-read validation with `/workdir/wepppy/.venv/bin/python` passed.
- Markdown lint for changed package, spec, and tracker files passed.

### 2026-03-26: Runtime integration, UI exposure, and package closeout
**Agent/Contributor**: Codex

**Work completed**:
- Resolved remaining contracts:
  - `momm2025_county_region`: explicit split-county rejection.
  - `canonical_rusle2`: polygon-backed official links only, explicit
    unsupported/table-only rejection.
- Added `wepppy/nodb/mods/rusle/r_modes.py` for deterministic centroid-based
  `R` selection and provenance payloads.
- Integrated `r_mode` through `wepppy/nodb/mods/rusle/rusle.py`, including:
  config/payload parsing, mode branching, updated `manifest.json` provenance,
  and README R-source labeling.
- Exposed `r_mode` through rq-engine payload filtering and run-page controls:
  `wepppy/microservices/rq_engine/rusle_routes.py`,
  `wepppy/weppcloud/templates/controls/rusle_pure.htm`,
  `wepppy/weppcloud/controllers_js/rusle.js`.
- Added or updated regression coverage for selectors, controller behavior,
  rq-engine route filtering, and RUSLE controller JS payload behavior.

**Blockers encountered**:
- None. Open contract questions were resolved in this session.

**Next steps**:
1. Optional follow-up only: derived split-county polygon package if maintainers
   want public sub-county `REGION` support later.
2. Optional follow-up only: scoped table-only canonical contract if broader
   official coverage is needed.

**Test results**:
- `wctl run-pytest tests/nodb/mods -k rusle --maxfail=1` passed.
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py --maxfail=1` passed.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k rusle --maxfail=1` passed.
- `wctl run-npm test -- rusle` passed.
- `wctl run-npm lint` passed.
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` completed.

## Communication Log

### 2026-03-25: User request to scope Momm 2025 integration
**Participants**: User, Codex  
**Question/Topic**: Create a work package to add the Momm 2025 dataset as an
additional R-estimation method, vendor the dataset and county map, update the
RUSLE specification, and identify remaining implementation decisions.  
**Outcome**: Package scaffold, active ExecPlan, spec updates, dataset README,
and vendored Parquet or GeoParquet assets were created. The main remaining
issue is how to handle counties with multiple public `REGION` rows after the
watershed-centroid county has been selected.

### 2026-03-25: User request to add Canonical RUSLE2 as a planned `R` mode
**Participants**: User, Codex  
**Question/Topic**: Promote the cleaned official RUSLE2 dataset from vendored
reference data to a planned `R` mode in the specification and work package.  
**Outcome**: The package and specification scope were expanded to include a
planned `canonical_rusle2` mode alongside `momm2025_county_region`.

### 2026-03-26: User request to execute the package end-to-end
**Participants**: User, Codex  
**Question/Topic**: Carry out
`docs/work-packages/20260325_rusle_momm2025_r_mode/` as an end-to-end
ExecPlan implementation.  
**Outcome**: Remaining contracts were resolved, runtime+UI+manifest support for
`momm2025_county_region` and `canonical_rusle2` shipped, regression coverage
added, and package docs/tracker/ExecPlan moved to closed status.
