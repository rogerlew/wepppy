# O5 matching-boundary water accounting

The large O4 stock residual was diagnostic bookkeeping, not evidence of a new
native water defect. Correctly aligned storage observations reconcile all
185,819 completed daily element states. Maximum absolute residual is
3.1203672e-7 m (**0.000312 mm**) at both hourly-end and post-plant-water-use
boundaries. No model behavior, binary release, parameter or tolerance changed.

## What was wrong in the diagnostic

O4 sampled END before SWU, the later plant-water-use routine, but subtracted
`ep + es + eres`. At that point `ep` contains potential plant demand; the later
SWU call limits it to available soil water and handles canopy interception.
Subtracting it before the corresponding storage withdrawal creates an apparent
water deficit.

At Charleston year 9/day 93/element 3, the old residual was −2.400805 m³
(−15.301964 mm). Observed evaporation withdraws 1.802824 mm. The later SWU
withdraws 15.301920 mm. The corrected residual is −0.000042 mm at both boundaries.
The hourly-end and pre-SWU stocks agree exactly across the recorded cases, and
no frozen-water change occurs across the sampled evaporation call.

Residue interception matters separately: evaporation may put unevaporated
interception into soil. For loam baseline year 6/day 53/fill, the measured
"evaporation withdrawal" is **−2.430558 mm**, meaning a stock addition. Native
EVAPPM explicitly implements this transfer when residue interception exceeds
its evaporation demand. Preserve this sign; do not label all ET-stage stock
changes as sinks. The measured change closes that example to −0.000011 mm.

## Scope and limitations

The new equation uses measured stock changes around evaporation and plant water
use, with independently recorded daily FIN, routed inputs, drainage, lateral
outflow and surface return. This establishes consistent accounting boundaries;
it does not independently validate the evaporation law or a new infiltration
model. EPART and PPOT sample post-evaporation variables. In particular PPOT's
residue operand is the **remaining post-call store**, often reset to zero; the
machine field `residue_interception_m` must not be interpreted as pre-call
interception supply. Its `evap_report_difference_m` comparison is only a
post-call diagnostic and is not a conservation test. Capture pre-call stores
if independently auditing that transfer in a later lane.

The five stopped states have no end stock and are excluded from completed-state
closure; their native funding failures remain unresolved. The tiny residuals
are compatible with the single-precision native aggregates, but this study does
not establish a new acceptance tolerance. No numerical guard was changed.
O4's 179 negative shadow outflows remain a valid rejection: they depend on
surface-flow operands, not the repaired stock diagnostic.

## Execution and evidence

Twelve full-period input decks were replayed with O5 observation off/on:
**24/24 expected-status and complete raw-output comparisons match**. Fourteen
executions complete all 16 years; ten reproduce the five expected year-12 stops.
The incident now contains 120 native executions (70 initial, 26 O4, 24 O5).
Repeated road configurations are not independent hydrologic realizations.

Helpers: build_stage_observer.py, replay_stage_observer.py and
reconcile_stage_ledger.py. Receipts: O5-build.json, O5-replay.json and
O5-ledger-summary.json. Raw observations and full signed ledgers are retained
under /workdir/wepppy/out/roads-native-funding-20261031 with a separate verified
stage-ledger-v1 archive; see stage-ledger-retention-receipt.json.
Three setup failures (Python quote, nonunique transpiration anchor, comment
matching the interception reset) happened before model execution. Their logs
are retained. Exact anchored edits succeeded without altering native behavior.

## Next experiment

The [joint ownership specification](native-joint-ownership-experiment.md) declares O6:
observe and attribute **storm infiltration and recession infiltration separately**
in physical volumes, using local/aggregated GRNA storage and actual upstream
accepted fluxes. Test the stold snapshot's timing explicitly. Include all twelve
cases and every recorded day, with ROCHEK and geometry/event counterexamples.
This is an observation/offline attribution lane, not a behavioral formula or a
release candidate. A defensible local-owner formula is still required before
any native repair. The draft remains model_gap / requires_scientific_review.

Roads magnitude acceptance remains unmet. Keep the released revision-2 binary,
withheld materials and human UI specification/layout gate unchanged.

Native helpers and receipts referenced above live in
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261031-roads-open-boundary-funding/artifacts`.

## Validation and retention receipt

O5 host smoke completed all three configured years. Native and parent package
documentation lint, incident finalization, artifact policy and diff checks pass.
The external stage-ledger-v1 archive contains 670 files, with every member
SHA-256 verified; archive SHA-256: `bdb4a19f600fc89166d353ce52c61014daef9c26f0186ec8763f2b95c0df9542`.
Full release, Disturbed and Cedar Creek gates were not rerun: this is an
observation-only study with no behavioral candidate or binary promotion.
