# Frozen-water reset sequence findings

## Decision

Do not repair the zero-ST reset on this evidence. All 16,753 observed reset
layers exactly match their assigned dry-support target and none increases fine
water. The positive nominal residual is an inherited coarse/fine reference
mismatch, not newly created water. This bounded checkpoint completes the reset
investigation; the wider rock and water-accounting work remains open.

## Coverage and arithmetic

The retained census covers 2,936 / 4,246 / 9,571 zero-ST layers for zero / normal /
high rock, 107,037 nonzero comparison layers, and all 58 clearing chains.
No zero-ST observation is unavailable. Negative fine-cell, negative NWFRZZ,
invalid geometry, negative fine-total and negative coarse-component flags are
all zero in this census. This does not invalidate earlier synthetic counterexamples.

Let L be fine liquid including NWFRZZ, D the dry-support target and A=L-D.
Direction-1 at ST=0 clears NWFRZZ and sets every active SLSW to THETDR;
it preserves ice, geometry, ST, YST and incoming shortage carry. Thus its
assignment error is exactly zero here; fine-total change is therefore -A.
The reconstructed coarse request is float32(ST-YST), or -YST. The routine does
not calculate VARWAT on this branch: this request is reconstructed, not observed.
The nominal residual therefore equals YST-A plus assignment error. Separating
coarse-reference mismatch from coordinate offset also requires the discrepancy
between fine ice and coarse FRZW plus dry water on frozen support; the offset is not merely geometry roundoff.

Twelve prereviewed compiled controls use complete unchanged FRWATC, including
partial/full frost, thin support, mismatched references, multilevel carry and
repeated resets. All pass assignment, finite-state and inactive-support checks.
The zero-ST middle layer preserves an incoming shortage for the next layer;
a tiny positive ST follows a different path. Repeating a reset without advancing
YST is stock-idempotent but can retain a nonzero nominal residual because YST is
unchanged: it is not a new loss.
These deliberate synthetic states are mechanism controls, not field feasibility.

## Three selected sequences

Three complete 16-year histories retargeted the existing observer only. Each
matches seven ordinary outputs, all 17,532 daily keys and the entire frost trace
exactly. Each window contains 144 hourly OFE profiles with complete stages.

| Rock context | Clear → reset map | Cleared NW (mm) | Later fine removal (mm) | Net coarse endpoint drop (mm) |
| --- | --- | ---: | ---: | ---: |
| Zero | 1576 → 1581 | 0.225286247 | 0.642672167 | 0.867958413 |
| Normal | 1591 → 1596 | 0.310954463 | 0.841511916 | 1.152466401 |
| High | 5243 → 5247 | 0.184376317 | 0.839800630 | 1.024176949 |

These are preselected **layer** residual extrema, not full-profile maxima.
Fine stocks and YST remain unchanged from clear POST to reset PRE. Cleared NW
plus subsequent fine removal reconciles net coarse depletion to within
2.2e-11 m. Treating that inherited reset residual as an independent new loss
would double-count the representation difference in these sequences.

For zero/normal, top ST stays unchanged through allocation and PURK and reaches
zero only in the final-hour post-PURK composite interval. Normal has separate
bottom seepage during PURK; repeated SEP in FLUX is not another export.
High receives intervening input: top ST gains about 0.400001183 mm over the day,
then loses 1.424178132 mm in the final-hour composite interval. Its net endpoint
drop is consequently 1.024176949 mm. Gross removal and net depletion differ.
Daily rounded Es (0.87 / 1.15 / 1.42 mm) and source timing support soil evaporation
as a candidate, but do not independently isolate accepted per-call ET.

## Source ownership and remaining evidence gap

Source bindings are in targeted-freeze.json in the private archive. The unchanged
observer binary is fb885d126413b3f19488c640ef3e7fb8d7d9a872f0f8b08b48a207092a956c0f.
Line references below refer to its private build, not a newly published source.

| Boundary | Source owner | What is established | Remaining gap |
| --- | --- | --- | --- |
| Zero-ST reset | FRWATC direction 1 | Exact assignment and inherited reference mismatch | Physical reference ownership across callers |
| Observation selector | contin.for, bpactive near line 2033 | Target day plus preceding day, exact year | Only three selected windows |
| BEFORE → PURK | watbal_hourly.for, lines 530–624 | Allocation operands and net layer changes | Allocation and PURK share one interval |
| PURK → AFTER | watbal_hourly.for, lines 625–980 | Final-hour zero-setting interval | ET, redistribution, drainage and overflow are composite |
| SEEP / FLUX | watbal_hourly.for, lines 625 and 966 | Recorded operands, overlapping SEP | No independently accepted closed external budget |

The next bounded step is an authoritative water-store/clock contract and an
observer of accepted ET and other writers inside the final-hour interval,
including the high-input sequence. Prereview that finite observer and require
full output/trace parity before considering any behavioral ablation. Do not
sum these discrepancies into annual losses or infer a capacity multiplier.
No surface-rock conversion, volumetric-rock default, production formula, native
binary or deployment changes result from this checkpoint.

## Evidence

See retained-science-readback.md, controls-science-readback.md,
control-implementation-readback.md and both targeted readback reviews.
The high-case no-input checker failure is retained alongside its generalized
replacement; no model run or prior evidence was changed to resolve that premise.
Archive and native commit identities are in archive-receipt.json and
native-checkpoint.json. Earlier work packages and private roots remain immutable.
