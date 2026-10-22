# WEPP 261021 — artifact revision 2

This reissue replaces the undeployed calendar-only 261021 pair at the owner's
request. Source: `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`, canonical branch
`wepp_260430_negmeltfix_comparator`; comparison baseline: 261010 (`7471bb5e9`).
The original 261021 source (`a87925df9`) and binary hashes remain in the
validation record. Select by binary SHA256 and revision, not filename alone.

## Defects and repairs

- **Century-year drift and stale climate records.** Use one proleptic Gregorian
  execution calendar for climate, hillslope PASS and watershed dates. Reject
  exhausted, incomplete or misordered climate; validate every ASCII PASS daily
  key. This repairs the one-day date-label shift and century-length failure.
- **Initial groundwater area.** Convert a hillslope-equivalent initial storage
  depth using the entire contributing hillslope area, rather than the last
  OFE's area. Multiple-OFE initial water is no longer understated.
- **Hourly soil allocation.** Distribute each infiltration request through the
  soil layers, preserving the positive final-layer remainder and bounding
  signed withdrawals. This prevents loss at the allocation boundary; it is
  not a change to the climate timestep.
- **Flat channel source discretization.** Integrate the supplied volume/duration
  rate over each overlapping routing cell, including a partial last cell.
  A 900 m³ source lasting 900 s with supplied peak 1 m³/s now supplies
  900 m³ on a 600 s routing grid,
  rather than 600 m³.
- **Source admission.** Admit deferred groundwater once, including its initial
  endpoint; remove the redundant outlet addition. Recover eligible ordinary
  channel local water when side-hill surface runoff is absent. Positive
  impoundment paths retain their separate treatment.
- **Live interior and reference state.** Retain nonzero interior channel state
  at dry boundaries. For MC4 only, reuse a valid previous reference when the
  boundary estimate degenerates while interior state remains live. Preserve
  the existing recurrence and Manning relations.
- **Exact fixed-point performance.** MC4 may copy a bitwise unchanged profile
  only when raw states, accepted outlets and remaining forcing meet the exact
  eligibility checks. Signed zero and subnormal values are retained; MC5 is
  excluded. The 100-year acceptance timeout remains unchanged.
- **MC outlet publication.** Publish daily volume from the accepted outlet
  trapezoid, including the initial endpoint, and include that endpoint in the
  peak. Retain the independently computed geometric residual rather than
  forcing it to zero. Publication consistency is not physical storage closure.
- **Receiving-channel working-flux alias.** Initialize runoff working fields
  after inflow assembly and before channel soil calculations. An earlier
  channel's element-indexed output can no longer contaminate a later channel's
  soil-plane calculation. Incoming transfers and actual stores are preserved.

## Watershed audit and practical effects

The [24-page illustrated technical report, revision 1 (PDF)](/weppcloud/static/reports/wepp/release-notes/wepp_261021/wepp_261021_release-notes-r1.pdf)
contains nine original figures and explains Dp, ET, lateral flow, Q/QOFE through the last OFE, daily/hourly
accounting, single/multiple OFEs, controlled causal experiments and all shipped
changes. Its public publication was approved by Roger Lew on October 21, 2026.
Ayush's original input decks were not provided; the workbook is an accounting
lead, not a reproducible validation dataset.

Fresh paired 24-year Cedar Creek comparisons against 261010 show sampled
outlet volume +0.5165%, reported outlet volume +0.05215%, and the largest
reported peak +0.2455%. All 24 annual reported peaks increase by 0.223–2.461%.
Some small-event peaks increase up to 19.07% and window volumes up to 13.55%.
Both hillslope and watershed binaries changed; these are not routing-only
attributions or observational calibration. The report includes adverse cases.

## Compatibility and remaining limits

Regenerate all contributing hillslope PASS files and watershed/interchange
outputs with this matched pair. Retain valid Gregorian climate; CLIGEN itself
is unchanged. ASCII PASS component version 3, existing native interchange,
MOFE/single-input capabilities, prompts, banner and capacities are unchanged.
Schema-2 HBP development changes are not shipped. 261010's initialized-source
normalization and hourly MIXPEAK are inherited, not new repairs here.

Muskingum–Cunge dynamics and numerical storage authority remain intact.
Signed soil/routing withdrawal acceptance and raw negative-discharge clipping
remain unresolved. This release does not establish universal physical closure;
sediment and nutrient consequences have not received comprehensive validation.
No default switch or production deployment is included.

Exact binary identities and completed gates are in the paired JSON sidecars
and the native release validation record (`release/wepp_261021_validation.md`). Roll back the complete binary/sidecar pair from retained
Git history and regenerate outputs; do not mix PASS generations.
