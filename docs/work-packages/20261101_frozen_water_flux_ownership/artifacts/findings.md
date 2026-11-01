# Accepted frozen-water flux ownership findings

## Decision

The three selected zero-ST transitions are caused by executed Penman–Monteith
soil evaporation. Their later capacity, drainage, lateral, surface and uptake
stages add no further removal. Combined with the preceding exact reset/clearing
sequence, this resolves the selected apparent loss as a reference/timing question
with an observed sink. Do not repair the reset or introduce a new sink to absorb
its nominal residual. No native physics or rock default was changed.

This conclusion concerns three preselected sequences, not all frost events or an
annual water budget. The broader rock and Roads program remains open.

## Actual observations

Exactly three full 16-year diagnostic KSFLAG1 histories were executed. Each
preserves all 17 runtime inputs, seven ordinary outputs, 17,532 daily keys,
the entire frost trace and the byte-identical prior BPO observation stream.
New observations retain 144 hourly groups and six daily groups per history,
with all ten layers and explicit executed-call identities.

All 18 observed ET calls use EVAPPM. There are 12 actual SWU calls across the
three windows, including one high-context call with zero accepted root uptake;
call count is not nonzero extraction count. There are no tile-drain calls in
these windows. Each selected OFE1/day sequence has no SWU call, with its actual
zero EP/root-depth decision operands retained. Other OFEs do have uptake.

| Context | Selected day / OFE / hour | Soil ET request (mm) | Unmet request (mm) | Returned ES / profile ST removal (mm) |
| --- | --- | ---: | ---: | ---: |
| Zero | year3/day19 / 1 / 24 | 2.245685551 | 1.377727138 | 0.867958413 |
| Normal | year3/day19 / 1 / 24 | 2.530798782 | 1.378332381 | 1.152466401 |
| High | year7/day343 / 1 / 24 | 1.718062675 | 0.293884543 | 1.424178132 |

Returned ES equals the selected profile ST removal exactly in all three cases.
Zero and normal have no residue contribution. High enters ET with approximately
2.01907e-11 m of residue interception; including its clearing leaves a signed
stock-plus-residue-plus-ES residual of -2.01907e-11 m. Preserve this finite-precision
residual rather than claiming exact full-store closure. The selected zero/normal
residuals are zero. These are actual routine-return values, not rounded daily
output or potential demand.

In high, the previous checkpoint measured about 0.400001183 mm of intervening
top-layer input. Its net coarse endpoint depletion is 1.024176949 mm, while the
now-observed gross evaporation is 1.424178132 mm. Normal's bottom seepage belongs
to the preceding PURK interval and is not an additional post-PURK export.

## Complete-window comparisons and flags

All 2,196 declared stage comparisons are within the predeclared numerical
allowances: 2,160 hourly comparisons and 36 daily uptake/growth comparisons.
Maximum absolute ET residual is 5.82077e-11 m; maximum uptake residual is
1.16416e-10 m. Capacity redistribution, tile drainage, lateral flow, surface
overflow and the observed growth intervals have zero net residual and no stock
change in these windows. This does not validate their active flux branches.
The allowances separately identify double-reader roundoff, native REAL arithmetic
and eligible zeroing thresholds; they are not calibrated physical tolerances.

Zero context retains 168 hourly flag records over 24 hours plus two daily flag
records on one OFE/day: all are negative **relative** coordinates at OFE2/layer2.
Absolute component and geometry checks remain valid. Normal and high have no
flags. No reference/support or unsupported-interception flags occur. A negative
FRZW coordinate alone is not negative physical ice; retain its dry-water offset.

## Store and clock interpretation

During hydrology ST is the operative coarse available-liquid coordinate. The
fine-grid state and YST mapping reference do not advance at every coarse flux.
YST is not an independent reservoir. Coarse liquid is ST+THETDR*(DG-FROZEN),
coarse ice is FRZW+THETDR*FROZEN, and total is ST+FRZW+THETDR*DG. The reference
terms must be applied exactly once. Fine and coarse descriptions must not be
added together as if they were distinct physical water stores.

The preceding selected clear/reset sequences reconcile cleared NW plus later
fine removal with net coarse depletion. The new observations identify the actual
gross sink and preserve the high-input distinction. A repeated nominal mapping
residual is therefore not evidence of a repeated external loss. This does not
resolve the separate synthetic positive-thin/threshold counterexamples, the
UL-minus-DRFC singularity, phase-change energy closure or general retention law.

## Validation corrections and reproducibility

The first private build failed before any model process: caller logging tried
to access routine-local ET. The corrected observer removes that caller reference
and records ET only inside its owning routines. Both exact prereviews were
repeated, including explicit declaration-scope checks for every logger operand.
Original failed build/source/reviews remain retained; no native behavior changed.

The original high readback rejected an existing global BP_IRS_ENTER OFE0/index0
record. Supplemental reader v5 permits only that source-confirmed legacy context
and retains every new stage/OFE gate and exact old-stream parity. Readback-v2
revalidates all three completed histories, verifying original complete campaign
inventory and frozen dependencies before/after; it performs no model invocation.
Original high failure remains unchanged. The final control panel rejects 17
malformed cases. The first two supplemental observations are byte-identical to
their original accepted observations. Minor failed summary preparation is also
retained; the final summary is generated by summarize_flux_v3.py.

Independent scientific and implementation actual readbacks are in
science-readback.md and implementation-readback.md. See summary.json for compact
all-window/selected results, ownership-contract.md for equations and source roles,
reproduce.md for read-only commands and archive-receipt.json for raw retention.

## Next scientific decision

Close this selected reset-as-new-loss hypothesis; another identical frost replay
would not justify a capacity correction. Carry the stock/clock distinctions and
retained threshold counterexamples into the separate whole-soil capacity and
retention contract, especially SSURGO source basis, air correction and the
UL/DRFC drainage domain. A behavioral capacity candidate still needs coherent
constitutive limits and independent physical validation before a full comparison.

Surface rock remains a separate development lane: source-supported exposed-area
and vegetation-overlap semantics must precede persistent native protection.
Profile fragment volume cannot supply those observations. No surface default,
retention multiplier, native repair, binary promotion, deployment or withheld
Roads evaluation follows from this checkpoint.
