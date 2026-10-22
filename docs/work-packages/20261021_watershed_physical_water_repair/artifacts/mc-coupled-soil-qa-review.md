# Actual-soil coupled-control secondary QA

Date: 2026-10-21. Independent read-only review of the eight final controls in
`/workdir/watershed-physical-water-repair-20261021/mc-coupled-soil-control-v1/`.
No production source was edited by this reviewer.

## Disposition and scope

**Accept these runs as bounded diagnostic evidence of the actual soil/routing
interface.** All eight cover two complete calendar years and retain the real
WSHCQI, conditional WSHIRS, WATBAL and WSHCHR paths. They prescribe a receiving
upstream boundary for one day; they are not unmodified natural-watershed cases.
They do not establish a new sink-acceptance rule or complete physical-water
closure.

The matrix is early/late 100 m³ input, wet day 159/dry day 160, and daily/hourly
soil balance. Every case uses MC4, 600-second routing, and `mofapp=1`. Hourly
WATBAL performs 24 soil steps; it does not imply channel lateral mode 2. This
study does not supply that additional routing-mode coverage.

## Boundary hook and isolation

The hook runs only for receiving element 3 in 1980 on the selected day, directly
before WSHCQI. It asserts the expected upstream element and 144-step grid. It
preserves the upstream time-zero rate, adjusts the six pulse samples so their
native trapezoid totals 100 m³, sets the matching daily volume to 100 m³ and
duration to 3600 seconds, and records the resulting integral. Every observed
integral agrees within 1e-5 m³. Early and late placement use the same volume and
source duration.

The hook does not assign the runoff/rainfall branch flags, soil fluxes,
transmission loss or runoff result. It saves and restores the entire upstream
q1 array, daily volume and duration after routing the receiving channel. The
actual source diff confirms this scope.

Independent no-hook baselines use the same inputs and instrumented binary with
the pulse day outside the 1980 calendar. Both baselines complete two years.
Every upstream-channel hydrograph and channel-water-balance row is byte-identical
between each baseline and all four corresponding hooked cases. This verifies
restoration and upstream isolation across the full period, beyond inspection of
the save/restore statements.

## Actual soil execution and complete artifacts

The pre/post soil observer surrounds the real WATBAL call. The hourly wrapper
selects WATBAL_HOURLY normally. Liquid and frozen layer sums, runon/runoff,
deep percolation, lateral flow, transpiration, evaporation, rainfall, melt and
surface return are observed without assigning their outcomes. The fin tap
records the value entering allocation, not an independently closed soil budget;
its request also includes existing upstream lateral inputs.

WSHIRS records confirm the wet-day call and dry-day bypass without a forced
branch. Both days still execute WATBAL. Each observed day has the expected
single daily fin record or exactly ordered hourly records 1–24. Soil, hook,
branch and routing records have the expected year and target identities and
finite values. Early and late placement have identical soil traces. The wet
controls produce nearly zero transmission; dry controls produce roughly
37.89 m³ daily and 38.84 m³ hourly transmission requests through the actual soil
calculation. These are observed requests, not proof that routing accepts every
requested exchange physically.

Independent artifact checks verify all eight runs, not only successful process
messages:

- Exactly 731 climate dates, from 1980-01-01 through 1981-12-31.
- Exactly 731 finite daily hillslope water-balance rows.
- Exactly 731 finite daily rows for each of the two channels, with ordered
  year/day/element/channel keys through 1981/day 365.
- Complete routing frames for days 158–162, including every endpoint and every
  spatial/time state, with no truncated or extra binary data.

The observer-off sibling preserves the boundary hook and removes diagnostic
recording. This reviewer independently compared all 300 retained native
input/output file pairs across its eight cases; every pair matches. The
observations therefore do not change the compared native results.

## MCFAST and ledger interpretation

The routing observer writes complete qin, qlat, q1 and qs arrays after routing,
including all states copied by MCFAST. It does not infer missing records from
an abbreviated executed-cell trace. For fixed-coefficient MC4, reconstructing
the existing eligibility guard over every interval supports a complete logical
recurrence ledger, including fast-forwarded intervals.

The field named `net_lateral_executed_m3` means exchange represented by eligible
recurrence intervals; it is not a hardware/executed-loop work counter. The
ledger separates clipping, requests in ineligible intervals, spatial rounding
and changes in the MC coordinate. Its telescoping residual is an accounting
identity, not independent proof of physical closure. The recorded pre/post soil
fields likewise do not yet constitute a full soil budget. In particular, a
positive runoff-depth/forwarded-volume difference must be checked for inherited
plane/element alias state before it is called valid soil runoff that was lost.
The scientific review owns that follow-up.

## Retained evidence and provenance

Independent script: `coupled_soil_qa.py` under the external work root. Final QA
receipt and hashes: `mc-coupled-soil-qa-v3/receipt.json` and
`mc-coupled-soil-qa-v3/review-manifest.json`. The two no-hook runs are retained
there. The manifest pins the final reviewed binary, relevant sources/scripts,
inputs and observed/output artifacts for all eight cases.

The initial study manifest predated the dry-day extension. The owner replaced
it with a final `manifest.json` containing 1857 hashes; this reviewer verified
every entry against the retained file with no mismatch. The independent review
manifest also pins the artifacts assessed here. This diagnostic acceptance does
not establish source repair correctness or full package closure.
