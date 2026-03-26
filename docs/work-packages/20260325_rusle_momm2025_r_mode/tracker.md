# Tracker - RUSLE Momm 2025 R-Mode Integration

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Started**: 2026-03-25  
**Current phase**: Scoping complete; scalar, centroid, and provenance contract
locked; split-county `REGION` policy still open  
**Last updated**: 2026-03-25  
**Next milestone**: Resolve split-county `REGION` handling and begin
Milestone 2 data-access implementation  
**Active ExecPlan**:
`prompts/active/rusle_momm2025_r_mode_execplan.md`

## Task Board

### Ready / Backlog
- [ ] Resolve how counties with multiple `REGION` rows are mapped after the
  watershed centroid identifies a split county.
- [ ] Implement `momm2025` data-loading and AOI-selection utilities in the
  RUSLE runtime.
- [ ] Expose the new mode in controller config, manifests, and UI.
- [ ] Add targeted regression coverage and validation evidence.

### In Progress
- [ ] None.

### Blocked
- [ ] Sub-county `REGION` polygons are not present in the public supplement, so
  the exact spatialization contract is still unresolved.

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
- [x] Locked `momm2025` v1 to a scalar run-level `R` that still writes a
  constant `rusle/r.tif`, not a spatially varying erosivity raster
  (2026-03-25).
- [x] Locked multi-county AOI selection to watershed-centroid county lookup
  for `momm2025` (2026-03-25).
- [x] Locked provenance or UI wording so `cligen_static` remains the
  WEPP-aligned `R` path and `momm2025` is labeled as county climatology
  (2026-03-25).
- [x] Registered the package in `PROJECT_TRACKER.md` backlog and linted the
  changed Markdown files (2026-03-25).

## Timeline

- **2026-03-25** - Package created and scoped.
- **2026-03-25** - Public Momm 2025 data normalized and vendored as Parquet.
- **2026-03-25** - Matching county geometry vendored as GeoParquet after FIPS
  vintage review.
- **2026-03-25** - Specification, tracker, and data README updated.
- **2026-03-25** - Scalar, centroid, and provenance decisions locked for the
  planned runtime contract.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Split-county `REGION` rows cannot be spatialized defensibly from public files alone | High | High | Keep as explicit decision checkpoint after centroid county selection; require approved county-only or derived-polygon path before runtime rollout | Open |
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
- [x] RUSLE specification updated for `cligen_static` guidance and planned
  `momm2025` mode.
- [x] Local dataset `README.md` added with attribution and metadata.

### Validation
- [x] `wctl doc-lint` passes for changed Markdown files.
- [ ] Runtime validation for the future `momm2025` mode remains pending.

## Progress Notes

### 2026-03-25: Scoping, data vendoring, and specification update
**Agent/Contributor**: Codex

**Work completed**:
- Researched the Momm 2025 public supplement and normalized the public CSV into
  repo-native Parquet.
- Derived and vendored a matching county GeoParquet after confirming that the
  dataset still expects 2010-vintage county FIPS coverage.
- Updated package docs and the RUSLE specification so the new mode is framed as
  planned rather than silently shipped.
- Locked the scalar, watershed-centroid, and provenance decisions that do not
  depend on missing `REGION` geometry.
- Captured the remaining split-county scientific or product decision needed
  before runtime implementation starts.

**Blockers encountered**:
- The public supplement does not include sub-county `REGION` polygons, so
  split-county spatialization is the main open contract question.

**Next steps**:
1. Approve a split-county `REGION` strategy for counties where centroid lookup
   still lands on multiple public rows.
2. Implement the runtime mode in `wepppy/nodb/mods/rusle/`.
3. Add manifest, UI, and regression coverage.

**Test results**:
- Data-read validation with `/workdir/wepppy/.venv/bin/python` passed.
- Markdown lint for changed package, spec, and tracker files passed.

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
