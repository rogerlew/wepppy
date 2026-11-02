# ADR-0130: Preserve explicit snowpack exhaustion across unit conversion

Status: Accepted for bounded source integration and tested combined-engine compatibility; final release and retention admission remain separate.  
Date: 2026-11-02

Canonical native source integration: `d2e14d96af5942409c9a315dc8594fcc164a702a`. Bounded combined-source validation and native promotion pass; remaining release and retention gates stay open.

## Context

The rock-water investigation observed large runoff/storage differences triggered by tiny positive melt tails in both Flagstaff and Birmingham, with opposite lane directions. MELT had already capped a positive melt request to an entire snowpack, but converting the capped water back to snow depth could leave a floating-point remainder. Melting that remainder in the next hour changed DISAG's strictly positive-hour support count, synthetic storm shape, and downstream runoff branch. The defect concerns ownership of an already executed full-pack cap, not the scientific significance of an arbitrary small snow amount.

Birmingham also exposes a no-addition density calculation that changes the current density by one binary32 step. The physical pack is unchanged, but comparing only numerical depth/density equality would miss this same failure class.

## Decision

Carry an explicit full-pack-cap-executed result from MELT to SNOWD. When the returned water is positive and the receiving pack is demonstrably the capped pack, debit its complete snow depth directly instead of reconstructing that debit through water-to-snow conversion. Continue through the existing complete-melt branch, including its existing water-release expression and terminal store updates.

Recognize the receiving pack through either exact depth/density coordinates or proved no-addition lineage: unchanged depth, zero new snow and both drift inputs, and a current density exactly matching the existing binary32 no-addition density computation. Require positive depth and both densities and the existing 1000 kg/m³ water-density coordinate. Partial melt, negative/zero melt, unmatched/new-snow/density ownership and nonpositive returned-water cases retain their previous arithmetic. No epsilon, new threshold, blanket small-pack deletion, or GRNA runoff-threshold change is proposed.

The bounded correction is accepted on the independently reviewed six-history cohort and permanent actual-routine controls. Combined-source compatibility and native promotion now pass on the evidence below; refreshed release gates remain required.

## Decision provenance

Decision venue: the user-authorized end-to-end repository study, 2026-11-02, America/Los_Angeles. Participants: requesting user, coordinating parent agent, source implementer, and independent science/implementation reviewers. No human meeting or additional approval is asserted.

Decision owner: the requesting user through the coordinating parent agent under the already-authorized program. The parent records bounded source admission after the independent actual cohort reviews in [actual scientific admission](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-cohort-science-admission.json). This implements existing authorization; it does not require another user-permission round. Implementer: source/observer agent under parent orchestration.

The original proposed ADR is retained byte-for-byte in the integration package's historical directory. The admitted decision replaces its pending-admission language; it does not retroactively label the original proposal as accepted. Combined-source compatibility, release regression, binary promotion and deployment remain separate decisions.

## Change summary

Before: a full-pack cap returns water; an independently rounded inverse conversion determines remaining snow and can create a next-hour remainder.

Accepted: an explicit cap result plus validated pack ownership selects exact complete snow-depth debit. Existing complete-melt water release remains the downstream owner. Its binary32 result can differ from the cap expression because their operation order differs; signed exact-rational release-plus-retained-store budgets and an operation-derived rounding bound must be retained. Do not claim exact real-number conservation merely because a native full-melt branch was reused.

The no-addition lineage case additionally retains the density-recomputation difference relative to original owner snow-water equivalent. A cap whose returned water is represented as zero is outside this positive-water correction and remains unchanged.

## Rationale and alternatives

- Explicit exhaustion preserves a completed source decision across coordinate conversion and addresses both observed lane directions.
- Reject an epsilon on remaining snow or hourly melt: it would delete legitimate small partial packs and introduce a new scientific threshold.
- Reject changing GRNA's runoff threshold: the current trace does not identify its internal zero path, and it is downstream of the demonstrated ownership defect.
- Reject direct equality of density as the only ownership proof: the observed no-addition density recomputation can change representation without adding a new pack.
- Reject blanket density normalization or altered partial-melt formulas: these would change unrelated paths without evidence.

## Consequences and risks

The intended change removes a spurious later positive-hour support contribution after an already executed full-pack cap. Runoff can change substantially because the downstream support and branch selection are discontinuous; small mass differences do not justify waiving those changes. Existing final-a8 numerical acceptance evidence becomes historical if this candidate is admitted.

New snow, drifting, density changes, negative melt and retention below/at/above 350 kg/m³ require explicit controls. The observer-only reference must reproduce the exact final-a8 ordinary outputs; the behavioral candidate requires new scientific acceptance and full relevant regression coverage. Any loss of genuine partial snow, unexplained water budget, altered unmatched path, or unsupported branch ownership blocks admission and triggers rejection of the isolated candidate.

## Evidence and implementation boundary

- [Flagstaff exact mechanism](../work-packages/20261101_rock_water_development/artifacts/R05-flagstaff-mechanism.md).
- [Birmingham independent mechanism](../work-packages/20261101_rock_water_development/artifacts/R05-birmingham-mechanism-implementation-review.md).
- Private research source: `out/rock-water-development-20261101/R05-snow-cap-source-v8/`.
- Original local controls: `out/rock-water-development-20261101/R05-snow-cap-controls-v5/receipt.json`; these are synthetic/recorded-operand controls, not compiled model evidence.

Legacy source and patches remain private. Additional GRNA branch and EVAPPM demand observations are diagnostics in both experimental lanes; they do not alter GRNA or ET behavior. Historical R05 execution artifacts and approved readers remain immutable; source integration is recorded separately by the final native commit. Release reports, final binary pairing and numerical gates must be refreshed after any admitted change.

## Corrected attribution and six-case consequences

At the detailed primary Flagstaff hour-18 witness, the actual candidate enters with a different pack and its original inverse conversion would already exhaust that pack. The alternative full-depth debit evaluated on the observer's state is an arithmetic counterfactual, not an identical-entry causal experiment on the actual candidate. The full-history support and runoff changes remain observed; do not collapse the trajectory comparison into that unsupported local attribution.

The following values are candidate-minus-a8 complete-history responses. QOFE is OFE2 local-area depth, not summed hillslope discharge. Terminal ELEMENT export and EBE event delivery are separately defined products.

| Case | OFE2 QOFE change (mm) | Terminal ELEMENT change (kg) | EBE delivery change (kg) |
| --- | ---: | ---: | ---: |
| Primary Flagstaff, 2711184/outrut | -18.257884742 | -0.06732 | 0 |
| Birmingham, 1718465/inbare | -5.91348971 | +1.59588 | +1.188 |
| Denver, 1718494/inbare | -1.20331544 | -0.0198 | 0 |
| Denver, 1718465/outunrut | +3.12674484 | 0 | 0 |
| Secondary Flagstaff, 1718494/outunrut | +1.42648824 | 0 | 0 |
| Charleston, 1718465/outrut | +119.57497549 | +0.85536 | +1.188 |

Annual and event changes can have opposite signs to their period sum. Charleston's OFE2 year-2 runoff increases 55.58937282 mm; its largest daily surface-export increase is accompanied by increased incoming runon and changed carried stock, not merely local melt. Birmingham and Charleston sediment increases are retained consequences. No favorable-sign or smallness criterion replaces their disposition.

The existing ET/stress/growth policy remains unmodified and scientifically limited. A positive represented canopy-covered demand can execute SWU and change stress even with zero accepted root withdrawal; subsequent growth and water use can amplify that branch. The Denver inbare and secondary Flagstaff historical r4-to-a8 mechanisms must not be relabeled snow-cap effects. Denver outunrut does exhibit a snow-increment branch response, including a native day-132 plant-ET increase of 3.862566839 mm with separately observed canopy/soil ownership. Persistent plant differences and temporal redistribution remain explicit; reported EP is not synonymous with accepted root uptake. This correction does not validate physiological policy, establish field accuracy, or introduce a new stress-rule patch.

These consequences and limits are supported by the six case-specific scientific reviews: [primary Flagstaff](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-flagstaff-response-science-review.md), [Birmingham](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-birmingham-response-science-review.md), [Denver inbare](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-denver-inbare-response-science-review.md), [Denver outunrut](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-denver-outunrut-response-science-review.md), [secondary Flagstaff](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-flagstaff-secondary-response-science-review.md), and [Charleston](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-charleston-response-science-review.md). Their original pending-cohort status remains historical; final admission is bound below.

## Admission evidence

Final cohort aggregate: `R05-snow-cap-experiment-v3/receipt.json`, SHA-256 `f55d1f591b7eafbeb1ab8861944623b427a8ad85c38051e2edfc7dd592bc785c`; full response `R05-repair-response-all6-v1/receipt.json`, SHA-256 `d27625546ba7659166214750316f88eb2a7d3ab1b682e7ac723e2d6495d4321e`. Independent science disposition: [bounded cohort admission](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-cohort-science-admission.json), SHA-256 `6f9a60dca1537d30255c3aaa4eb49f13af70c972a9563ffcbecabefa4191e68b`. Independent implementation disposition: [cohort implementation outcome](../work-packages/20261101_rock_water_development/artifacts/R05-snow-cap-cohort-implementation-outcome-v3.md), SHA-256 `f034ef1402f40b4b1e00943d85bf4cbd0b3c8421a66c48eb2b1f99f525345154`. Permanent compiled actual-routine tests retain 58 passing checks; the old-debit negative control fails six defect checks while 52 unaffected checks pass. Exact signed water budgets, operation-derived release bounds and recorded residuals remain retained without an epsilon waiver. Combined-source results and release evidence are not inferred from isolated acceptance.

## Combined-engine validation, November 2, 2026

All 18 final-source histories pass: six snow nonactivation histories and six B04
plain/observed pairs. [Independent science admission](../work-packages/20261101_rock_water_development/artifacts/combined18-final-science-admission-v1.json)
(`3b7ffa53b66aadfa1226026f1986f08eec80ac02d0849f8cf963433d8ec90cd5`) and
[implementation review](../work-packages/20261101_rock_water_development/artifacts/combined18-actual-implementation-review-v1.json)
(`58c8967795de988c22144eb3ca3d22dba5ea5826cabcd414bab28251a2ca1f17`)
support parent acceptance `312a6fd9fefc86a206da01232d6cabe74334647e74003634f8ca8c29001f50b8`,
retained in `out/rock-water-development-20261101/combined18-final-execution-v3/parent-acceptance-v1.json`.
The outer actual receipt is `c9550ce86d66a4659c33c9e5bcd70890afa0b5a47abab80be3237da01a59272d`.

All 42 snow ordinary outputs match admitted references with zero frost execution.
All six B04 clean/observed pairs match. Their 19 underfunded intervals and
writer/conversion proofs remain identical to standalone B04, with no domain or
terminal-carry findings. Phase arrays differ in five cases, including two changed
funded donor debits. Both 2711184 lanes retain explicit output consequences; ordinary
parity elsewhere is not internal-state identity. The
[final scientific disposition](../work-packages/20261101_rock_water_development/artifacts/combined18-final-science-admission-v1.md)
retains those differences without an epsilon or magnitude waiver.

This accepts bounded compatibility under the existing water/donor policy. It does
not establish thermal availability, cold-snow or whole-system budget closure,
retention adoption, global frost restoration, field validity or deployment.
Native promotion subsequently passes exact six-target readback, receipt
`cd53d1932419d788f4156bf56fca5a0d56e912ada845a1127d6ebabd1161399c`
at `out/rock-water-development-20261101/release-r5-renewed-pair-v2/promotion-receipt.json`.
WEPPpy vendoring, remaining release gates and P03 retention evaluation remain
separate. Earlier isolated evidence and proposed snapshots remain unchanged.
