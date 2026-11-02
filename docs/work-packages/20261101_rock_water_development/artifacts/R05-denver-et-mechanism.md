# R05 Denver ET and carried interception diagnosis

Read-only selective trace analysis, 2026-11-01. No model executions, full-reader reruns or active-campaign edits. Release HOLD remains; accounting explanation and causal attribution are separate.

## Inbare: the daily visible gaps omit canopy carry

Both completed Denver/1718494/inbare/paved/high lanes pass their per-case receipts, full calendars and seven-file ordinary-output parity. Selective extraction independently hashes each complete trace while decoding only source year 7/days 130–139; it reuses the certified daily ledgers. Exact bits, source clocks, sequence numbers and source bindings are retained privately in `R05-denver-inbare-mechanism-v1`.

The year 7/OFE 3 visible residuals of approximately -1.00 mm on day 132 and +0.95 mm on day 134 are dominated by omitted carried canopy storage. The observed candidate-minus-baseline change in daily canopy-storage change is **-0.983697478659451 mm** and **+0.9544629720039666 mm**, respectively. Endpoint residue-storage differences are zero. Including the recorded soil, canopy and residue stores leaves nonzero per-lane ledger residuals of about 1e-6–1e-5 mm on these days; this is not exact arithmetic closure or a new acceptance tolerance. Remaining residual attribution stays separate from the explanation of the printed millimeter-scale gaps.

Actual owner joins, rather than reported Ep alone, establish the transfers:

| Day / lane | Net EVAPPM layer-ST debit (mm) | SWU layer-ST debit (mm) | Closing canopy carry (mm) |
| --- | ---: | ---: | ---: |
| 132 baseline | 0.2594152465 | 0 | 0.9836974787 |
| 132 candidate | -1.0002476774 | 1.8774660493 | 0 |
| 134 baseline | 0 | 1.9690175614 | 0 |
| 134 candidate | 0.1031979336 | 1.2777704765 | 0 |

A negative debit denotes net addition to the observed soil layers. On day 132 the candidate enters EVAPPM with residue interception 1.81645376 mm, reports Es 0.81620610 mm, clears the residue store and returns the unused residue water to soil. Baseline residue interception is 2.62393965 mm and Es 2.88335490 mm. Thus Es is not universally a direct soil debit. Candidate SWU consumes canopy interception 2.35767872 mm and also removes root-zone water; baseline demand is covered by canopy and leaves carry. Day 134 baseline consumes the remaining 0.9544629720 mm canopy plus root withdrawal; candidate has no canopy carry. Recorded sequence and pre/post layer states support these ownership distinctions.

## Inbare: observed stress-branch amplification precedes reported canopy change

At day 130 opening both lanes have the same observed plant geometry and watstr 0. IDAT/WB accepted residue differs by one binary32 step. Actual local FIN is -2.3283064365386963e-10 m in baseline versus +1.1641532182693481e-10 m in candidate, with the same observed rain, carried canopy and accepted canopy operands. Other hidden state is not asserted globally identical.

Before EVAPPM, top-layer relative ST is 0 in baseline and 5.820766785236131e-11 m in candidate; root depth 0.0600355193 m lies within the top 0.1 m layer. EVAPPM's resulting EP is 0 versus 3.617021612778437e-11 m. The baseline skips SWU; the candidate enters it, canopy covers the residual request, root debit is 0, and SWU returns Ep 0 with watstr 1. Baseline retains watstr 0. No physical interpretation of those numerical flags follows merely from their names.

Same-day growth occurs before SWU and uses watstr 0 in both lanes. The next day 131 growth uses the carried 0/1 difference: candidate LAI rises 1.07229543 to 4.21951914 while baseline remains 1.07229543. On day 132 EVAPPM therefore sees those already different opening canopies. Later that day candidate growth raises LAI again to 4.92276335 and root depth from 0.21906748 to 0.39939123 m before SWU. The final ELEMENT canopy is not the canopy used by the earlier EVAPPM calculation.

The observed sequence supports a zero-versus-positive call-gate discontinuity and subsequent stress-state/growth amplification. It does not establish the first divergence anywhere in the full history, nor independently replay every intermediate operation between FIN and root-zone availability.

## Scientific boundary and missing proof

EVAPPM's EP is already conditioned by modeled root-zone water availability. It is **not** the unconstrained atmospheric demand. The source constructs root-zone availability and TAW/RAW, selects the availability factor etks, and combines it with etorc and the canopy coefficient kcbcon to form EP. Current EVP_DEMAND observations capture the resulting EP but not every internal operand of that construction. Exact source-operation reconstruction or explicitly observed initialized operands are needed before claiming that entire expression is independently verified.

Likewise, canopy satisfaction inside SWU and skipped SWU are distinct state transitions; neither justifies assigning a universal physical stress value. No epsilon, blanket stress reset, alternative evaporation rule or other behavior change is proposed. Independent review must distinguish the source-basis numerical allocation correction from the sensitivity and physical meaning of its downstream consumer policy. Positive uptake, residue return and carry joins in these observations are useful actual coverage; they do not grant general retention or whole-model water admission.

Private inbare summary SHA256: `235596a5e84bb78892dfc3e5a55d609bcdd462c74d12fec3a6a3e9ff198da546`. Its bindings identify the exact selective traces/ledgers/helper; `source-bindings.json` separately binds observed r4/final EVAPPM, SWU, GROW and hourly WATBAL source files without reproducing them.


## Outunrut: opposite-direction carry and stress-gate response

Both completed Denver/1718465/outunrut/paved/high lanes also pass their per-case receipts and exact ordinary-output parity. The separate `R05-denver-outunrut-mechanism-v1` extraction verifies both full trace hashes while retaining only the declared window and existing ledgers.

For year 7/OFE 3, the paired canopy-storage change is **+0.8462983532808721 mm** on day 132 and **-0.8462987025268376 mm** on day 134, explaining the dominant +0.85/-0.84 mm visible gaps. Endpoint residue differences are zero. The remaining paired recorded-ledger residuals are about -3.318e-6 mm and +7.567e-7 mm respectively; they remain explicit, not waived.

The day-130 response reverses direction. Both opening watstr values are 0, but small antecedent plant differences already exist: baseline/candidate LAI is 1.1721934080/1.1721938848. Baseline local FIN is +2.3283064365386963e-10 m and candidate FIN is 0. Before EVAPPM, top ST is 1.1641533570472262e-10 m versus 0; resulting EP is 1.5730398927882305e-10 m versus 0. Baseline enters SWU, has zero root debit, and sets watstr to 1; candidate skips SWU and retains 0. Baseline's reconstructed final Ep is 1.1641532182693481e-10 m, illustrating the additional native rounding boundary in canopy subtraction/addition. Do not infer that demand equals this final reported quantity.

Same-day growth still uses 0 in both lanes. On day 131 only baseline grows substantially, reaching LAI 4.3296928406; candidate remains 1.1721938848. On day 132 baseline EVAPPM returns a net 1.0702763757 mm to soil from unused residue water, then SWU withdraws 1.8633629337 mm from soil and uses canopy water. Candidate EVAPPM removes 0.2890727483 mm from soil; SWU removes no soil water and leaves 0.8462987025 mm canopy carry. On day 134 candidate root withdrawal is 2.1166177876 mm plus consumed canopy carry, while baseline root withdrawal is 0.1957762245 mm with no canopy carry.

This mirrored observed branch chain strengthens the diagnosis of threshold/state sensitivity. It does not make the two cases an exact-state counterfactual, establish the first global divergence, or settle the physical stress policy. Both complete native demand-construction proofs remain pending the additional initialized EVAPPM operands; independent review is required before any behavior proposal.

Opposite-pair summary SHA256: `bd6ef850343ef76243099eddd95ccf5b2b6c184df2605512ae9800355226017e`.

## Minimal additional demand observation

For the owner's separately reviewed observation-only continuation, emit a REAL vector immediately after native EP/ET assignment beside EVP_DEMAND: etorc, etks, TAW, RAW, wftrp, kcbcon, tpdp, etksden, rawpaj, etcsc, kcbadj, selected kcb/rawp, rhd, fwv, ed, emaxt, dlt, rn, gma, ee, tave and eo; retain INTEGER crop selector and layer count. These quantities are initialized on the executed path there. kcbcon is explicitly REAL in ccrpet.inc, not an implicit integer. Existing pre-EVAPPM layer and plant snapshots already retain the root-zone geometry, ST, reference/field-capacity coordinates, roots and canopy.

For residue/soil evaporation construction, TEW, REW, wfevp, etkr, etke, epdp and potes are also initialized by this point. In contrast, bpotes/eaj/kcmax/kecon are conditional: observe them only inside the executed potes-greater-than-residue branch after its assignment, never in an unconditional exit vector. Do not initialize variables or evaluate untaken branches to simplify logging. Bind exact baseline/candidate source anchors and require full ordinary-output and existing-observation parity. The active R05 campaign and its helpers remain unchanged.
