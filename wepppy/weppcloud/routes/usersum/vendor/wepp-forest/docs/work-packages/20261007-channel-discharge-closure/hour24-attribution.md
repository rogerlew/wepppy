# Final-hour return attribution and bounded options

2026-10-08. Roger authorized investigating the final-hour concentration and
potential fixes after the component candidate was withheld. This follow-up adds
observation only, not a new physical candidate. No release, vendor or deployment.

## Finding

The last hour does receive a specific daily remainder: unused residue-interception
water. It does not receive a generic daily-runoff or conservation residual.
Late saturation under uniformly distributed daily infiltration also contributes.
The previous answer distinguishing SURDRA from a remainder assignment was too
narrow to explain the upstream scheduling interaction.

The unchanged baseline code has this sequence:

1. `watbal_hourly.for:344` excludes the residue interception pool from FIN.
2. Lines 460-478 distribute that daily FIN uniformly across the hourly steps.
3. PURK operates before daily ET. ET executes only in the last step (line 549).
4. `evappm.for:462-472` calculates `xx = es - resint`, clears resint, and, when
   xx is negative, adds `resint - es` to the top soil layer. The older EVAP path
   contains the same explicitly documented same-day remainder return.
5. Upward redistribution and lateral drainage follow. The surface surplus check
   at `watbal_hourly.for:843-875` then records the excess in `ui_Scrunf(24)`.
   There is no second PURK call between the residue release and that check.

This is daily interception accounting embedded in an hourly loop. It is not
evidence of water creation: FIN had excluded that intercepted water. Nor is the
clock label proof that the resulting water physically returned in the last hour.
The withheld producer/transport candidate promoted those computational buckets
into both an hourly peak estimate and time-resolved channel forcing.

## Measured evidence

An observation-only copy of the frozen candidate ran H259, H367, H439 and H718
for their full 1980-2003 periods, with observation off and on. All 28 output files
in each mode match the frozen candidate exactly. Eight checkpoints per hour on
four selected dates yield 3,072 rows / 16 hillslope-day cases. Direct native-REAL
arithmetic reproduces the observed ET top-storage addition exactly; ET does not
change storage in hours 1-23 in the selected traces.

| Hillslope and date | Hour 23 return mm | Hour 24 return mm | Daily residue release to soil mm |
| --- | --- | --- | --- |
| H259, 1990-10-21 | 0.000 | 4.174 | 2.616 |
| H367, 1990-10-21 | 0.000 | 2.489 | 2.616 |
| H259, 1998-09-18 | 0.000 | 4.847 | 2.613 |
| H439, 1998-09-18 | 3.033 | 5.647 | 2.614 |

H439 is a particularly clear case: the final-hour increment over the preceding
plateau equals the daily residue release to displayed precision. H259 also has
late saturation: on October 21 its final-hour top layer gains 2.616 mm during ET,
then 1.605 mm through upward redistribution, and loses 0.302 mm through lateral
drainage before 4.174 mm is returned. Removing the observed residue addition
arithmetically would leave 1.558 mm, but that subtraction is not a counterfactual
model run and does not uniquely label the origin of every parcel of water.

The selected ET and hourly water-balance sources are unchanged from f24c957e.
All four soil-output files and three of four full WAT files also match the
baseline; H439's full WAT differs elsewhere under the withheld candidate, while
its inspected September 18 1998 WAT record matches. Do not claim blanket baseline
hourly-state parity from daily-output agreement. The observer comparison itself
is exact against the frozen candidate for every selected output.

## Potential fixes

### Recommended next feasibility specification: steady daily return

Treat returned water as a daily-volume contribution, not a resolved hourly
hydrograph. Preserve native rainfall-only Pr and final V, with no-return cases
following the unchanged baseline path. For eligible positive-return cases, test:

- return rate `Ps = Vs / 86400`;
- physical combined peak `P = Pr + Ps`, followed by existing floor/cap handling;
- erosion effective duration through the existing `V/P` relationship;
- original rainfall reconstruction plus constant current-day return forcing.

This keeps the in-band component approach and existing routing interfaces. A
fixed 24-hour contribution does not need 24 transmitted hourly weights: the next
contract could carry only Vr, Qr and Vs, deriving the return rate directly. Do not
silently reinterpret the archived experimental v1 format; settle the simplified
versioned contract before coding. No previous-day state, user parameter, rrinit
change, ET rescheduling, repeated water balance or routing reconstruction is needed.

This changes the proposed physical rule and requires Roger's agreement before
another candidate. It is not an upper bound on actual return peaks and can smooth
real short events or begin return too early within the computational day. Those
are the accuracy costs to assess, not hide. Native floors/caps and sediment effects
remain visible. Arithmetic using the prior verified H106 components suggests
about 1.404 and 1.670 mm/h for the two triggers, but these are not producer-run
results or proof of watershed acceptability.

### More selective alternative: separate daily residue-driven return

Retain the other hourly components and distribute only the portion attributed to
the daily residue release over a simple within-day support. This preserves more
detail but introduces an attribution obligation: water released into soil is not
automatically all surface return. H367's 2.616 mm release versus 2.489 mm final
return demonstrates the distinction. A `min(release, last_return)` assignment
would be a new allocation assumption, not an established source identity.
This also leaves late saturation caused by uniform daily FIN distribution.

### Broader process-level change: revise interception/infiltration scheduling

Moving ET earlier or changing when residue water joins infiltration can alter
soil storage, percolation, plant water use and daily runoff. It is not merely a
timestamp correction. Using the actual infiltration time series would be a
larger water-balance coupling change. Neither is recommended for this bounded
repair without separate scientific scope and approval. Repeating daily ET each
hour or discarding the last bucket is not a valid local correction.

## Decision boundary

The mechanism is sufficiently established to stop diagnostic expansion. Recommend
one explicitly coarse daily-return feasibility specification next, with source
volume unchanged and consistent physical peak/erosion and channel treatment.
Validate both triggers, the two late-pulse controls, a sustained-return case such
as H439, no-return controls and the existing whole-record standard if a candidate
is authorized. No implementation or acceptance is implied by this recommendation.
The current candidate remains withheld; no comprehensive conservation work has
been reopened.

## Provenance

Full evidence: `/wc1/holdouts/channel-discharge-hour24-20261008`.
`trace_hour24.py` records process receipts, source/binary hashes and off/on output
identity. `assess_hour24.py` checks native storage arithmetic and preserves the
baseline comparisons. The observer patch changes only the copied diagnostic
`watbal_hourly.for`; the candidate source worktree is unchanged.

The initial observer build missed two parameter includes. Its stale-binary
staging attempt was stopped and retained under `failed-instrumentation`; a
subsequent staging collision was corrected before the successful observed runs.
Those attempts supply no attribution evidence. The final runner rejects an
unrebuilt observer binary and only resumes off-mode outputs with matching receipts.

Compact summaries, the observer patch, receipts and plot are archived in
[the incident evidence](../../ablation/20261007_channel_discharge_closure/artifacts/repro/hour24-attribution).
