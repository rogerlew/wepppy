# ADR-0053: Offline Staley M3 soil thickness evaluation

## Status

Accepted for offline evaluation only, 2026-09-09. Production soil source,
weathered-material treatment and partial-coverage acceptance remain unapproved.

## Decision provenance

- Venue: user/Codex repository session, 2026-09-08 Pacific / 2026-09-09 UTC.
- Participants: requesting user and Codex.
- Decision owner: user for scientific source/availability; Codex for bounded
  reproducible study implementation under the supplied ExecPlan.
- Implementer: Codex.
- Change: no prior M3 soil helper; add strict raw-interval soil candidate and
  labeled all-recorded-layers sensitivity. Mean cm / 254 supplies S. No existing
  production parameterization or WEPP soil behavior changes.

## Decision and rationale

Follow the [offline contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md)
and [predeclared protocol](../work-packages/20260908_staley_m3_soils/artifacts/study_protocol.md).
Require valid zero-start contiguous intervals for selected component thickness;
retain sum/union/endpoint diagnostics on rejected records. Deduplicate stable
IDs separately from depth ranges. Exclude explicit R in the strict candidate;
reject weathered/mixed/unknown material rather than invent scientific treatment.
Compare retaining all recorded layers as a separate sensitivity.

The original USGS SAS sums intervals and renormalizes over nonmissing component
weights without a bedrock filter. SSURGO has different source semantics and
vintage. Expose coverage instead of equating known support to full coverage.
Use complete-only full-catchment outputs and partial diagnostic means, with no
approved numeric cutoff. Soil support is independent of dNBR policy.

## Alternatives

Deepest endpoint fills gaps; summing cumulative bottoms double-counts depth;
union hides alternate overlapping records; generated WEPP profiles can be
clipped or extended. None supplies the selected strict estimate. Fixed-depth,
zero-fill and automatic source fallback are rejected. Finer mapping alone is
insufficient to accept a substitute predictor.

## Evidence, risks and rollback

Evidence and measured findings live in the
[work package](../work-packages/20260908_staley_m3_soils/package.md).
The strict candidate may withhold useful observations; all-layer sensitivity
may include bedrock. Neither demonstrates debris-flow predictive validation.
Survey endpoint censoring and original survey material inclusion remain open.
Retire the offline helper/artifacts if their semantics prove unsuitable; no
persisted production state or deployment rollback is involved.

## Measured outcome

The paired 12-outlet study recommends retaining original STATSGO pending a
scientific source decision. Strict SSURGO support is 0–99.25%; all-layer support
is 84.24–99.25%, so neither supplies complete full-catchment coverage. Maximum
common-support probability effects are 19.35 and 11.52 percentage points,
respectively. These are diagnostic effects, not published acceptance limits.
See the [decision report](../work-packages/20260908_staley_m3_soils/artifacts/soil_decision.md).
Production source, weathered-material and coverage approval remain deferred.
