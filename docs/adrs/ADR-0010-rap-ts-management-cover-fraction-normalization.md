# ADR: RAP_TS Management Cover Fraction Normalization

Status: Accepted
Date: 2026-06-26

## Context

RAP band summaries are stored in RAP's native percent scale (`0..100`). The
RAP_TS management-prep path used `RAP_TS.get_cover(...)` to sum annual grass,
perennial grass, shrub, and tree cover, then passed that value directly to
`Management.set_cancov(...)`.

Generated WEPP management files require canopy cover (`cancov`) as a fraction
(`0..1`). The run `/wc1/runs/pr/praetorian-talcum/wepp/runs/p6.man` exposed the
bug: its initial condition line contained `82.00000` for `cancov`, where the
intended canopy cover was `0.82`.

The existing single-year RAP landuse path already divides RAP band summaries by
`100.0` before assigning `cancov`. RAP_TS management preparation needs the same
unit boundary.

## Decision

`RAP_TS.get_cover(topaz_id, year, fallback=True)` will return a WEPP
management canopy-cover fraction by dividing the percent-scale vegetation-band
sum by `100.0`.

Raw RAP_TS data, including `RAP_TS.data` and `<wd>/rap/rap_ts.parquet`, remains
percent-scale. This preserves source-product provenance, existing analytics,
and compatibility with callers that inspect raw RAP band summaries.

This ADR covers the RAP_TS management-file `cancov` path. It does not change
the separate `RAP_TS.prep_cover(...)` `.cov` time-series export contract.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex task from operator report, 2026-06-26 America/Los_Angeles
Participants Present: WEPPcloud operator/user, Codex coding agent
Decision Owner(s): WEPPcloud operator/user
Implementer(s): Codex coding agent

## Change Summary

Old behavior:

- `RAP_TS.get_cover(...)` summed percent-scale RAP vegetation bands and returned
  the raw sum, for example `82.0`.
- `WeppPrepService.prep_managements(...)` passed that value into
  `management.set_cancov(...)`, producing generated `.man` files with
  `cancov=82.00000`.

New behavior:

- `RAP_TS.get_cover(...)` sums the same percent-scale RAP vegetation bands and
  returns `sum / 100.0`, for example `0.82`.
- The generated WEPP management initial condition receives `cancov` in the
  expected `0..1` fraction range.

## Rationale

WEPP documents canopy cover as a fraction (`0..1`) in both initial-condition
state and output headers. Passing percent-scale RAP values into `cancov`
overstates cover by a factor of 100 and can make unburned RAP_TS runs behave
like fully covered hillslopes regardless of the actual vegetation state.

Normalizing in `RAP_TS.get_cover(...)` puts the conversion at the boundary where
RAP_TS changes from raw RAP data access to management-cover parameterization.
It also keeps RAP_TS consistent with the single-year RAP landuse path.

## Alternatives Considered

1. Normalize RAP_TS parquet/data during analysis - rejected because the parquet
   is a raw RAP summary artifact and downstream analytics expect percent-scale
   band values.
2. Normalize inside `WeppPrepService.prep_managements(...)` - rejected because
   the service only needs a WEPP-ready canopy-cover value; putting the unit
   conversion in the RAP_TS accessor keeps the unit contract local to RAP_TS.
3. Leave behavior unchanged - rejected because generated `.man` files can carry
   impossible canopy-cover fractions such as `82.00000`.

## Consequences

RAP_TS scenarios that rebuild management files after this change will have
lower, physically valid canopy-cover inputs wherever RAP_TS cover overrides are
applied to undisturbed forest, deciduous forest, mixed forest, shrub, or tall
grass hillslopes.

Previously generated runs are unchanged until their management files are
rebuilt.

## Evidence

- Reported run artifact:
  `/wc1/runs/pr/praetorian-talcum/wepp/runs/p6.man`
- In the reported artifact, the initial-condition line includes `82.00000` in
  the `cancov` position.
- RAP_TS parquet for the same run stores percent-scale values under
  `/wc1/runs/pr/praetorian-talcum/rap/rap_ts.parquet`.
- WEPP source documents `icanco` as canopy cover at end of simulation `(0-1)`
  in `/workdir/wepp-forest/src/cincon.inc`.
- WEPP output headers document `Canopy cover (0-1)` in
  `/workdir/wepp-forest/src/bighdr.for`.
- Regression tests:
  `tests/nodb/mods/test_rap_ts_cover_transform.py::test_get_cover_returns_wepp_fraction_from_percent_scale_rap_bands`.
  `tests/wepp/test_wepp_prep_managements_rap_ts.py::test_prep_managements_rap_ts_only_updates_undisturbed_classes`.

## Risk and Rollback Notes

Risk: RAP_TS runs rebuilt after this change can produce different runoff and
sediment because canopy cover is no longer inflated by percent-scale values.
That is the intended correction.

Rollback: revert the `RAP_TS.get_cover(...)` division by `100.0` and this ADR.
Use rollback only if follow-up validation shows the management-file writer
expects percent-scale `cancov`, which would contradict WEPP's documented
`0..1` contract.

## Implementation Notes

The implementation deliberately leaves raw RAP_TS storage untouched. The unit
conversion happens only in `RAP_TS.get_cover(...)`, which is the accessor used by
the management-generation path that writes `.man` `cancov`.
