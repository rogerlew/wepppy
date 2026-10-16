# MACA CMIP5 projection selection

## Authority and scope

The operator approved implementing the MACA model/scenario selector and CCSM4
client correction on 2026-10-16. Implementation is pending. Preserve
`future_cmip5`, ClimateMode.Future=3, existing locale/capability eligibility,
spatial behavior, CLIGEN processing, scaling, auth and queue wiring. This is a
selection feature, not a climate pipeline or publication refactor.

## Selection, compatibility and presentation

Use optional request field `maca_projection` and additive saved field
`_maca_projection`. Values are exactly `<model>/RCP4.5` or `<model>/RCP8.5`.
Models are bcc-csm1-1, bcc-csm1-1-m, BNU-ESM, CanESM2, CCSM4, CNRM-CM5,
CSIRO-Mk3-6-0, GFDL-ESM2G, GFDL-ESM2M, HadGEM2-CC365, HadGEM2-ES365,
inmcm4, IPSL-CM5A-MR, IPSL-CM5A-LR, IPSL-CM5B-LR, MIROC5, MIROC-ESM,
MIROC-ESM-CHEM, MRI-CGCM3 and NorESM1-M. All retain the existing future-year
envelope 2006–2099. Preserve existing year validation and error behavior.

New projects and legacy saved objects lacking the field use
`GFDL-ESM2G/RCP8.5`, the prior actual build choice. Omitted request fields preserve
the current selection. Explicit empty/null, non-string, unknown model/scenario
or path-like values fail local validation; do not silently change projections.
Saved malformed values fail on a Future build. Other climate modes ignore this
mode-specific request field. Parsing changes and year validation remain in the
existing atomic NoDb parse/rollback scope; failed parsing restores all fields.

Render one select labeled **MACA driving model and scenario** before future-year
inputs, using shared Pure UI macros and dataset-controlled visibility. Show
model, scenario and year range in each option. Bind the saved/default selection.
For malformed saved values, render a selected empty placeholder requiring an
explicit valid choice; never let the browser implicitly choose the first model.
Omitted submissions and builds still reject malformed saved intent.
Preserve read-only handling. Use **Future MACA CMIP5** and the agreed attribution
to Katherine Hegewisch and John Abatzoglou's Climatology Lab at UC Merced, with
University of Idaho origin/hosting distinguished. Remove the obsolete claim that
the projection is fixed. Keep catalog IDs and mode values unchanged.

Expected invalid selections use the current RQ validation envelope with field
`maca_projection` and code `invalid_maca_selection`; no job is queued.

## Retrieval and scientific behavior

Use a single shared model/member and projection registry. CCSM4 uses `r6i1p1`;
the other listed models use `r1i1p1`. Select the member deterministically before
forming the URL; no fallback or automatic source substitution. The low-level
client rejects unsupported model names before network work. Preserve the existing
historical/RCP wrapper signatures, endpoint, seven-variable retrieval, units,
conversion, date handling, CLIGEN station/seed, and processing quality guards.

The future builder receives the selected model and scenario; optional helper
arguments retain GFDL-ESM2G/RCP8.5 for existing direct callers. Log model, member
and scenario used. Existing `climate/ws.prn`, `climate/wepp.cli`, parameter files,
monthlies and run logs retain their formats and normal browser/archive paths.
No new provenance artifact or report schema is introduced. Saved selection
records intent; generated PRN/CLI content is acceptance evidence. Existing
failure/publication semantics and archive behavior remain unchanged.

The member decision and rationale are in ADR-0097. Retained live evidence in
`docs/dev-notes/artifacts/20261016_maca_ccsm4_probe.json` proves the corrected
member at one location/two dates, not full-period or domain-wide availability.

## Validation

Cover missing/never-used, explicit default, other populated projections,
legacy objects, empty/null and hostile selections. Verify parser rollback,
disk reload, UI selected option/order/visibility, submitted payload, validation
before enqueue, and actual member/model/scenario URLs. Exercise both CCSM4 RCPs
and an unchanged default model. Validate selected source values reach real PRN
and native CLIGEN-generated CLI files with correct dates, precipitation and Tmax/Tmin;
run a bounded live nondefault acquisition/build and retain evidence. No source
or publication mocks may stand in for claimed generated-content evidence.

Inventory existing climate.nodb selection, climate/ws.prn, climate/wepp.cli,
parameter files/monthlies and run logs. Verify normal browser/download visibility
for working, failed and completed builds using existing status/publication paths.
Read back the exact wepp/runs/p*.cli copied by WeppPrepService.prep_climates.
Exercise canonical archive_rq/restore_archive_rq and compare restored artifact
bytes and saved selection. These are regression checks, not publication changes.
