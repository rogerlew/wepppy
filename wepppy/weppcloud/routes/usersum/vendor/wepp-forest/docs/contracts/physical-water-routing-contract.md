# Physical water allocation and routing contract

Status: narrow allocation/source/publication contracts reviewed; signed coupling
and complete routing acceptance unresolved,
2026-10-21. Coordinate with WEPPpy
ADR-0101 and work package `20261021_watershed_physical_water_repair`.
Independent review and executable evidence are required before promotion.

## Groundwater

Initial groundwater volume is initial depth (mm)/1000 times total hillslope area
(m²), initialized once at simulation start. Daily Dp recharge sums local OFE
volumes. Preserve the previous-day baseflow/deep-seepage withdrawal recurrence;
reset withdrawals at simulation start, never at an ordinary year boundary.

## Hourly infiltration

The 261029 local-input correction is under release review. Preserve rainfall minus
interception (including the existing prior-interception adjustment), snowmelt,
irrigation and routed contributions in the signed balance regardless of its sign.
The daily sibling retains those inputs before adding channel subsurface flow and
keeps its positive-only allocator. See WEPPpy ADR-0112 and the native
`20261029-negative-fin-water-accounting` package. This correction does not settle
the timing of hourly signed exchange when upstream return water arrives later
than the uniformly distributed downstream debit.

Allocate signed hourly infiltration through a bounded number of layers. Retain
all positive remainders in actual soil storage before existing percolation.
Cap negative allocation against available liquid water at every layer, regardless
of magnitude or layer count. Unmet withdrawal is an explicit unsupported-state
failure until its generating flux can be reconciled; silently discarding it or
creating negative storage is prohibited. For negative inputs, sum original
binary32 liquid inventory in binary64 and reject demand above it. Retain working
stores and remainder in binary64 through the original weighted pass and a bounded
top-down pass over remaining liquid. Exact inventory exhaustion yields zero
stores. Cast once at completion. Account for final binary32 half-ULPs and bounded
binary64 arithmetic; no fitted residual tolerance is used.

## Source reconstruction

For a flat event with positive volume V and finite duration 0 < T <= 86400 s, continuous rate is V/T
on [0,T]. Routing-cell volume is rate times overlap with that interval; its mean
rate is cell volume divided by timestep. Compute overlap bounds/rate in binary64
and cast each mean once, including fine non-divisor grids. Preserve supplied duration when peak
and volume conflict. Cell index zero has no volume. Preserve separate return-flow
support and unchanged exponential controls. Solver point-value conversion is a
separate boundary that must be verified, not assumed from a cell-sum test.

## Channel exchange and unresolved solver boundary

Assemble positive local net water independently of side-hill existence or runoff.
Negative transmission can denote release from the channel water-balance process.
Losses may not exceed available source/store water. Do not scale unrelated source
hydrographs or invent negative discharge. Preserve source support and observe
both actual solver quadrature and independent storage.

WSHCHR Muskingum-Cunge uses temporally averaged upstream rates and, in point mode,
lateral rates. Its numerical storage relation differs from Manning endpoint
geometry; equality is not required by the operator-selected MC contract below.
Full watershed correctness requires an independently measured recurrence,
source/withdrawal and accepted-transfer ledger. A zero printed geometric balance
or passing source-cell sums cannot establish acceptance.

## Compatibility

Do not change ASCII PASS v3/WAT formats, event-selection thresholds, Gregorian
calendar, executable defaults or release artifacts. Regenerate contributing
hillslopes, PASS and watershed together when validating a source candidate.

## Operator decision: preserve Muskingum-Cunge

2026-10-21: The operator rejected replacing numerical MC storage with physical
cross-sectional volume. Preserve MC dynamics and derive consistency from its
implemented recurrence. Geometric inventory is diagnostic, not an equality
acceptance requirement. The fixed-coefficient control closes against MC storage;
its geometric discrepancy alone is not a water-creation or water-loss finding.

Observe variable-coefficient storage increments, parameter revaluation, daily
grid/boundary transitions, source quadrature, clipping and daily publication
separately. Consistent rate and daily-volume transfer remains required. No new
routing scheme, storage-authority change or event-specific switching is authorized.
This supersedes the previous physical-volume recommendation in the review record.

## Reviewed source and publication correction

Admit WSHCQI deferred groundwater into the top rate array once, including the
first-call endpoint. Remove the former separate initial-outlet addition because
that amount is now in qin. Preserve ordinary-day inlet/outlet carry. This shared
source correction applies to KW3 and MC4/5; the routing equations are unchanged.

When positive local net water has no side-hill surface hydrograph, use the
existing uniform daily non-surface representation only when neither side
impoundment supplies positive volume. Impoundment release timing remains open.
Keep the established positive side-hill reconstruction and signed-loss path.

For MC4/5, publish the trapezoidal integral of accepted q1, including index zero,
as chvol/runvol/tmpvol and the downstream daily transfer. Include q0 in daily
peak metadata. Retain independently calculated Manning geometry as a diagnostic;
do not replace it with a residual-derived store or force the printed balance
to zero. KW3 publication retains its existing convention. Public columns and
units are unchanged, but MC reported volumes and geometric balance residuals
can change. Regenerate complete paired outputs; never mix old and new channel
volumes or PASS generations.

This correction does not certify physical closure. Raw negative MC discharge
clipped from exported q1 and signed-loss timing remain measured open boundaries.
WSHDRV has already credited soil with the daily transmission loss before WSHCHR;
reducing that loss afterward without reconciling soil would create water.
A complete signed-exchange repair requires an independently reviewed source/sink
acceptance and soil-commit contract, preserving MC dynamics.

## MC4 reference during recession

A boundary-derived reference at or below the existing eps cannot describe live
retained interior flow. MC4 retains its previous valid per-channel reference in
that case only, queried before grid selection through readonly CHRSTATE_LIVE.
Reset history at simulation initialization, preserve ordinary reference selection,
and leave no-history cases, MC5 and KW3 unchanged. This preserves the last valid
reference coordinate during recession; it does not impose geometric continuity.
The reference selection change is observed as WREFC when observability is enabled.

MC4 may skip repeated within-day arithmetic only after forcing is bitwise
constant for all remaining steps and two consecutive complete raw profiles and
accepted outlets are bitwise identical. Copy every future profile and outlet
unchanged, including subnormals and signed zero. MCFAST records the skipped step
count. The pinned build uses 32-bit default REAL and INTEGER. MC5 is excluded
because its coefficients vary within the day. No small-value deletion is allowed.

Portable lifecycle and fixed-point tests cover readonly eligibility, simulation
reset, channel isolation, subnormals, signed zero, future forcing changes and
raw-array/export parity with the shortcut disabled. Continuity/cascade diagnostics
explicitly disable this shortcut to retain exhaustive recurrence observations;
their strict completeness gate and instrumentation provenance remain mandatory.
Signed soil/routing exchange and clipping remain separate unresolved boundaries.

## Channel working-flux lifetime

Initialize runoff(iplane) and chnrun(iplane) for each
receiving channel after WSHCQI and before optional WSHIRS. Completed-channel
element output indices can overlap later channel plane indices; inherited values
are not receiving-channel fluxes. WSHCQI consumes preserved element transfers in
tmpvol and associated arrays. WSHIRS/WATBAL then produce this channel's surface
fluxes, while final output restoration still uses tmprof. Preserve norun, soil
stores and all MC state. A positive inherited depth must not be forwarded by
relaxing the event gate. Require actual multi-channel soil controls and all
native gates before accepting this initialization repair. The validated checkpoint
passes 520 full-suite tests and seven portable causal tests, with independent
scientific review and representative paired replays. Signed exchange remains open.


## Late hourly return metadata (261026)

Continuous hourly runs may generate positive terminal-OFE surface return in the
late WATBAL call after IRS was skipped. When the terminal OFE is noncontoured,
rain/melt/irrigation flags, pre-call runoff and duration are zero, no MIX source
is active, and late WATBAL produces positive SURDRA, record return-only SRC3.
Serialize the authoritative runvol directly in cubic meters and the 24 hourly
return depths as weights; never multiply runvol by hillslope area again. Reset
the separate late-source flag each day. Invalid volume/weights fail explicitly.

The existing MIXRETURN convention uses duration 3600 sum(weights)/max(weights)
and a uniform block beginning at midnight. This conserves the caller's volume
within arithmetic precision; it does not preserve actual hour placement or
validate watershed-wide water closure. Physical hillslope peak and erosion
remain unchanged (including zero peak on these late events). Mixed-source,
contoured and daily-water-balance paths are outside this repair. Do not assign
rainfall duration, fabricate a peak or revive literal-hour forcing as a fallback.
The owner accepted this bounded approximation on 2026-10-26; see WEPPpy ADR-0107
and the retained zero-duration ablation for rationale and rejected alternatives.

## Updated-stock ET accounting (261029)

After either daily or hourly allocation and percolation, EVAPPM must use current
ST for evaporation and root-water integrals. Reapplying an allocated FIN duplicates
an exchange already represented in stock: hourly allocation handles signed
exchange, while daily allocation applies only positive FIN. Negative daily FIN
is unallocated and must not be independently debited by EVAPPM; the daily
signed-exchange boundary remains open. Root water is the sum over rooted portions of the
profile, independently of the surface evaporation estimate. These invariants
apply to both callers and must be tested across wet/dry inputs and partial/full
rooted layers. Never conceal negative water availability by clipping reported ET.

The hourly source-timing partition and ET consumer repairs were accepted after
independent AI scientific and implementation review on 2026-10-30. Retained
evidence and limits are in the 20261030 timing work package.

## Source-time attribution (261029)

For ordinary downstream hillslope elements with negative daily exchange F and
positive area-normalized upstream saturation return A, let B=min(A,-F). Route
fraction B/A of each upstream return increment directly through at that hour;
apply (F+B)/N plus the remaining surface return and all lateral input to soil.
The daily sum remains F+A+sum(lateral input). A genuinely unfunded remainder
continues through the actual-stock inventory guard. Channel, contour and
non-trigger scheduling arithmetic retain their previous path.

This attributes an already calculated daily routed amount to its known upstream
hourly source. It does not introduce a travel-time solver or validate arbitrary
variable-width geometries. The full fixture and frozen development panel pass,
and independent AI scientific and implementation reviews accepted this bounded
contract on 2026-10-30. This is not field validation or institutional endorsement.
Keep the existing guard and never tune soil inputs to evade it.

## Accepted revision-3 recession geometry

See the [recession geometry contract](hillslope-recession-geometry-contract.md)
for the EPLANE origin correction and QINF continuity repair accepted in
`wepp_261029` artifact revision 3. Final native and independent scientific gates
pass. The contract retains the scalar-domain and full contour-event coverage
limits; this acceptance does not establish Roads parameterization success.
