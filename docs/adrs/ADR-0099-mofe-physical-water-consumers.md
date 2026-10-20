# ADR-0099: Physical hillslope water and routed PASS export

## Status

Accepted operator direction on 2026-10-20; contract review and implementation
conformance pending. No production rollout or historical regeneration authorized.

## Decision and rationale

Use physical terminal WAT Q for hillslope reports, dashboard events, daily Ash
inputs and exports. Preserve subthreshold water instead of substituting PASS's
filtered surface export. Compute P as daily local area-weighted depth and lateral
as terminal local depth times terminal area divided by full native hill area.
Select native outlets before merging mapped features. This replaces all-OFE
report P/QOFE/lateral sums, dashboard P/Q sums, the daily Q/lateral area mean,
and export terminal-only local P/unconverted lateral values.

AshPost subtracts selected hills' PASS runvol from the PASS-based watershed
baseline before adding modeled ash runoff. This preserves the source basis of
that subtraction while correcting all-OFE QOFE double counting. Model formulas,
calibration, WEPP event thresholds and report annual divisors do not change.
PASS/baseline reconciliation allows rtol 1e-10 and atol 1e-8 m3 solely for
floating-point accumulation order; this is not a physical discrepancy allowance.
Canonical historical H.wat is admitted under the existing producer contract,
with missing executable lineage disclosed rather than inferred from values.

The complete field, absence, geometry and freshness rules live in the
[hillslope water aggregation contract](../schemas/hillslope-water-aggregation-contract.md).
Raw QOFE remains version-sensitive. Storage and transfer diagnostics do not gain
new physical meanings under this correction.

## Alternatives and evidence

Rejected a universal PASS source for hillslope runoff: paired evidence contains
1,096 MOFE days with positive WAT Q and zero PASS export. Rejected all-OFE
Q/QOFE sums and means: internal boundaries are not independent outlets.
Rejected threshold reconstruction from Q: the model tests internal runoff before
WAT's effective/cumulative-length normalization. Rejected post-only freshness:
old Ash model outputs still contain old daily-loader results.

See the [paired receipt](../work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_paired_source_readback.json)
and [source/compatibility reviews](../work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_preliminary_reviews.md).
Source inspection proves constant-width hillslope normalization; runtime contour
acceptance remains an evidence obligation, not an inferred completed test.

## Decision provenance

Venue: operator/Codex conversation, 2026-10-20; precise time not retained.
Decision owner: requesting operator Roger Lew, who selected "physical wat runoff"
after review of the paired-source distinction. Implementer: Codex.
Ayush Poudel supplied the water-balance workbook discussed with Roger Lew;
meeting date/time and participant attendance were not supplied and are not inferred.
The workbook supports the analysis but is not a universal executable provenance
record or authority to change model physics.

## Compatibility, risk and rollback

Preserve public raw columns and API shape. Numerical caches advance to
`mofe-water-v2`; export numerical version advances separately. Record Ash model
and post provenance independently; retain historical outputs with warnings and
require explicit regeneration before corrected postprocessing. Missing required
outlets fail scientific generation rather than becoming zero. Dashboard shows
unavailable values. Keep atomic publication and normal scope isolation.

Rollback pairs native and Python consumers and their algorithm markers. Retain
old artifacts without labeling them current. Unknown custom normalization,
contour execution coverage and sparse-day legacy TotalWatSed behavior must be
reported as limits; do not hide disagreements through tolerance or clipping.
