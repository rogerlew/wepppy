# ADR-0131: Donor-limited freeze restoration

Date: 2026-11-02

Status: Accepted for bounded water-restoration integration and tested combined-engine compatibility on November 2, 2026. Final release and retention remain gated.

Canonical native source integration: `d2e14d96af5942409c9a315dc8594fcc164a702a`. Bounded combined-source validation and native promotion pass; remaining release and retention gates stay open.

## Decision and rationale

Cap the existing FRZNG liquid-reference restoration by its available nonnegative fine-layer ice. Preserve the funded branch arithmetic exactly. On an underfunded restoration, transfer available ice into the positive unfrozen liquid volume, zero ice, and retain the remaining reference deficit for actual FRWATC redistribution. Unsupported nonfinite or negative donor/geometry states fail explicitly. No new threshold, floor, reservoir, thermal parameter or snow policy is introduced.

The original code restored liquid beyond its ice donor and then reset negative ice, adding water. The accepted cap bounds the original total-ice donor category. Eleven observed funded events already require inherited ice; one underfunded inherited-ice event retains the original final bits. Newly formed ice alone would change that existing policy. Conserved water transfer does not establish inherited ice's energetic availability or universal thermal validity.

Removing the reset alone leaves negative ice; raising an earlier liquid floor creates water; limiting new freezing alone misses inherited liquid deficits. Those alternatives do not repair the demonstrated ownership failure.

## Executed isolated evidence

Independent implementation and science reviews replayed all six plain/observed paired histories: 827 phase events, 87 restorations (62 funded, 25 underfunded), 19 closed intervals, 9,791 writer proofs and 19 conversions, with zero domain or terminal-carry findings. All 42 plain/observed ordinary-file comparisons are exact. Five profiles retain all old ordinary outputs; only 2711184 candidate changes.

At the target year 7/day 12/hour 20 witness, the original reset adds exactly 1394559/17179869184 m without a donor. The candidate removes that addition; subsequent actual FRWATC draws from layer 3/cell 2 and closes with zero carry. Exact representation and conversion residuals remain recorded, without a tolerance waiver. Full-history profile endpoint changes and printed flux changes are distinct from conditional same-operand comparisons and are not claimed as a complete reservoir or thermal budget.

Evidence: `B04-restoration-science-actual-v1.md`, `B04-continuation-actual-implementation-review-v2.md`, and retained `B04-actual-attribution-v1` / `B04-target-restoration-attribution-v2`. Permanent source-free actual-routine controls exercise both dispatchers at O0/O2, funded/no-restoration exact bits, underfunded inherited deficits, explicit negative-ice rejection and actual downstream donor redistribution. Forty checks pass; original source fails the 20 defect checks while 20 unaffected checks pass.

## Limits, integration and rollback

The isolated repair and bounded combined snow-cap compatibility are accepted. Complete release regression, unexecuted production paths, retention admission and universal thermal validity remain separate gates. No binary vendoring or deployment is authorized by this ADR. Stage source, tests and source specification together; apply only after active dependency bindings are clear. Rollback restores the prior FRZNG source and regenerates matched artifacts under the normal release process.

## Decision provenance

Venue: user-authorized repository study, November 2, 2026, America/Los_Angeles. Decision owner: requesting user through the coordinating agent, which explicitly accepted bounded integration after independent scientific recommendation and implementation PASS. Implementer: ownership agent. Independent reviewers: rock_contract_science and rock_contract_impl. This accepted ADR supersedes the proposed experiment after the coordinating parent authorized canonical source integration; the original proposed bytes remain retained in the integration package. Historical execution artifacts remain unchanged.

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
