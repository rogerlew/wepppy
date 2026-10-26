# WEPP 261026

This paired release adds return-only SRC3 metadata for late dry-day hourly
soil return, resolving the demonstrated positive-volume/zero-duration channel
failure. It inherits the 261021 artifact-revision-2 physical-water and calendar
repairs. The defect also reproduces with 260803 and 261010 hillslope binaries;
261021's explicit duration check exposed the older missing-source metadata.

## Scope and accepted limitation

Eligibility is continuous hourly execution at the noncontoured terminal OFE,
with zero pre-call runoff/duration and rain/melt/irrigation flags, no existing
active MIX source, and positive return from the existing late WATBAL call.
Serialize authoritative runvol directly in cubic meters and retain hourly
weights. Daily reset keeps the path separate from IRS peak/erosion calculations.
Legacy EVENT, physical hillslope peak (including zero on these events), erosion
and non-target outputs remain unchanged. No schema, capacity, banner or default
change is included.

The existing return consumer uses equivalent support
`3600 * sum(weights) / max(weights)` for these zero-storm events and a uniform
block starting at midnight. Interval overlap preserves caller volume within
arithmetic/printed precision; actual hourly timing and physical peaks are not
recovered. Mixed-source, contour and daily-water-balance paths are outside the
new producer eligibility. Signed routing withdrawals, clipping and universal
physical closure remain open. The owner accepted this bounded approximation;
WEPPpy ADR-0107 records the decision and alternatives.

## Adoption

Select `wepp_261026` and regenerate all contributing hillslopes and watershed
outputs with the matching pair. Do not mix old PASS files with the new watershed
executable. Roads/AgFields composition requires the paired component-v3 reader.
Existing releases remain available. Release/vendoring does not switch project
defaults or deploy production services.

The cumulative scientific report is a new 261026 edition derived from 261010
revision 2, with inherited 261021 repairs and new evidence distinguished.
Historical report editions and their simulation results remain unchanged.
See [validation](wepp_261026_validation.md) for exact release identities and gates.
