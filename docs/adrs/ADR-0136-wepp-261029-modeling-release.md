# ADR-0136: WEPP 261029 modeling corrections and release interpretation

Status: Proposed — release-level synthesis of recorded component decisions.  
Date: 2026-11-05  
Decision scope: the cumulative Linux `wepp_261029` / `wepp_261029_hill` release
through artifact revision 7; no new model implementation or deployment authority.

## Context

WEPP 261029 contains substantial corrections to shared water and sediment
calculations, followed by soil-coefficient ownership and specialized revegetation
changes. Although many repairs preserve the intended equations, they change the
executed model and can materially change predictions. Calling the release only
numerical hardening, a parser update or a Roads fix understates its consequences.

The individual decisions already have ADRs. This record explains their release-level
relationship, why large output changes do not by themselves invalidate a demonstrated
repair, and why passing engineering gates does not establish field validity.
It does not replace the component ADRs or silently change their statuses.

The [owner-approved consolidated report](../../wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-consolidated-ed1.pdf)
is the single stakeholder account of all seven revisions. This ADR records the
rationale and boundaries; the report supplies the detailed methods, figures and
results. Its [publication manifest](../../wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/publication-manifest-consolidated-ed1.json)
binds the exact approved PDF and current executable pair.

## Decision

Record WEPP 261029 as a cumulative modeling correction and compatibility release
with explicitly bounded evidence, rather than a recalibration or a blanket
endorsement of every supported physical scenario.

1. Retain the demonstrated water-accounting, source-mass, boundary-condition,
   numerical-evaluation and coefficient-ownership repairs. Old-output agreement
   is not an acceptance criterion where the old output is traced to a defect.
2. Preserve the distinctions between equation-preserving repairs, the adopted
   hourly return-timing approximation, and the specialized reference
   parameterization. These have different scientific justifications and limits.
3. Disclose material event, annual and cumulative consequences, especially recovered
   sediment delivery. Do not tune parameters, clip output or weaken inventory
   guards simply to recover the previous answer.
4. Identify each artifact by revision and hashes. Reproduction, adoption and rollback
   use a complete matched hillslope/PASS/watershed chain, not the filename alone.
5. Keep numerical repair acceptance, parameterization acceptance, field calibration,
   documentation publication, default selection and deployment as separate decisions.

These statements consolidate existing release choices. This proposed ADR introduces
no new formulas, thresholds, parameter defaults, compatibility promises or rollout.
Component scientific semantics and current domain contracts remain authoritative.

## Decision provenance

- **Venue:** Roger Lew/Codex repository conversation, 2026-11-05,
  America/Los_Angeles; exact message time is not retained.
- **Participants present:** Roger Lew and Codex. No external meeting or additional
  scientific participants are inferred.
- **Decision owner:** Roger Lew requested this release-level ADR after approving the
  consolidated report and authorizing its publication and repository pushes.
  Approval of that report is recorded; ratification of this new ADR is not assumed.
- **Implementers:** Codex implemented the native/application work under the component
  decisions and authored this synthesis. Historical independent AI review is
  distinguished from human scientific peer review and institutional endorsement.
- **Scientific ownership exception:** specialized revegetation semantics remain
  Anurag Srivastava's domain under ADR-0134. No claim is made that he attended,
  reviewed or approved this consolidation.
- **Earlier decisions:** component ADRs below retain their own venues, dates,
  authorizations, acceptance scope and experimental history. This is a retrospective
  record, not a claim that a single meeting approved every revision.

## Change summary and rationale

| Modeling change | Before → retained behavior | Decision basis |
| --- | --- | --- |
| Signed water accounting and ET | Negative-balance handling could drop local input; ET could count an already allocated exchange again; rooted water could lose earlier layers → preserve complete input, use updated stock once and retain the rooted-layer sum. | Accounting/ownership correction; existing inventory guards and daily positive-only allocation remain. [ADR-0112](ADR-0112-native-negative-balance-local-inputs.md). |
| Hourly return timing | A uniform debit could precede the upstream return water → apportion routed flow-through to its existing hourly support while preserving the daily sum. | Explicit timing approximation, not a travel-time solver or permission to borrow future water. ADR-0112 and consolidated report section 4. |
| Melt support and contributing storage | Receiver-only timing and repeated upstream subtotals could misrepresent connected supply/storage → retain current connected support and count each contributor once. | Preserve topology while correcting support and multiplicity. [ADR-0114](ADR-0114-native-equivalent-melt-support-and-storage.md). |
| Channel source mass | Effective hydraulic volume could amplify or suppress actual sediment-bearing supply → integrate each source's own volume times concentration over the represented span/duration. | Source ownership, retaining the disclosed historical conversion factors. [ADR-0116](ADR-0116-native-channel-sediment-source-accounting.md). |
| Channel hydraulic/deposition boundary | An extreme upstream-flow guard could set inlet discharge to zero; constant-discharge deposition could lose entering load/source → use the all-upstream limit and boundary-preserving solution. | Correct limiting cases without calibrating erosion upward. [ADR-0117](ADR-0117-native-constant-discharge-channel-support.md). |
| Hillslope deposition, sorting and shared capacity | Cancellation, skipped intervals, unsafe roots, inconsistent capacities or boundary resets could corrupt loads → stable evaluation, complete supported integration and actual boundary states. | Repair demonstrated numerical failures of the retained equations. ADR-0115, ADR-0118 and ADR-0121–0124 below. |
| Equivalent-plane geometry and recession | Shifted element origin and an extra unity cutoff → preserve caller geometry and continuous positive-rate recession branches. | Shared infiltration correction, with bounded domain evidence. [ADR-0119](ADR-0119-native-recession-and-equivalent-plane-geometry.md). |
| Interception, snow and frozen water | Allocation could exceed represented supply, full-pack melt could leave an inconsistent depth, and restoration could exceed the ice donor → conservative allocation, owned pack exhaustion and donor-limited restoration. | Bounded water repairs; no frost-energy recalibration or physiological redesign. ADR-0129–0131 below. |
| Layer/OFE coefficients | Later OFEs could overwrite FC/HK used with another OFE's water state → retain layer and OFE identity in producers and consumers. | Ownership correction, preserving formulas, initialization schedule and retention defaults. [ADR-0133](ADR-0133-native-mofe-coefficient-ownership.md). |
| Specialized 9005/RAP behavior | Generic reading could misbind extended soils and omit cover consumers → correctly bind inputs and adopt the specialized reference hydraulics/growth/fire sequence. | Reference compatibility is an adopted specialized parameterization, not merely parsing or proven ecology. [ADR-0134](ADR-0134-specialized-revegetation-reference-port.md). |

Peak and soil-water serialization, portable real32 math, array bounds, diagnostics
and build/provenance changes also belong to the release. They are covered in the
report's complete change map. Output-format repair does not change the underlying
stock; numerical portability is not a new native Windows release.

## Critical sediment-delivery consequence

The final revision-2 Cedar simulation delivered **517,815.77 kg**, versus
**180,137.20 kg** in original 261029 over 1980–2003: **+337,678.57 kg (+187.456%)**.
This comparison is original 261029 versus revision 2, not 261026 versus revision 7.
It is not a measured calibration result or a universal adjustment factor.

The large increase has a traced mechanism. An upstream/lateral volume ratio above
100,000 activated a geometry guard that wrongly removed upstream hydraulic support.
A separate constant-discharge deposition defect lost entering load and lateral
supply. Correct limits retain entering load at zero distance and incoming load
plus distributed supply at zero settling. These defects created *artificial
channel sinks*: computational losses rather than supported physical deposition.

A paired diagnostic for channel 235 on 1990 day 117 received about 7,827.98 kg and
previously exported zero; the corrected channel exported 7,825.85 kg with essentially
zero signed bed exchange. On the five largest daily increases examined, summed
per-class bed erosion decreased by about 18.6–37.1 kg. The evidence supports
recovered incoming transport on those dates, not an increase in bed erosion there.
Internal channel transfers must not be summed as independent watershed sources.

An opposing defect was repaired too: approximately 1.845 kg of real lateral supply
had become approximately 136,060 kg internally. Source correction alone reduced
outlet export in the isolated comparison. Restoring transport through the former
sinks produced the larger net increase. Small aggregate water differences therefore
do not establish small sediment differences or justify rejecting the repair.

The final 24-year intermediate-transfer audit had zero negative/nonfinite class
records. Detailed source/bed checks covered 16 dates, 5,936 channel-events and
29,680 source-class records. Those checks do **not** assign every kilogram of the
period increase to a unique defect, establish complete watershed mass closure or
prove agreement with observed sediment. Later revisions retain the mechanisms;
the report does not claim a fresh complete revision-7 Cedar comparison.

## Alternatives considered

- **Preserve old results or retune soils to reproduce them:** would compensate for
  identified accounting/boundary failures rather than repair them.
- **Clip negative sediment, relax inventory guards or forgive deficits:** would
  conceal lost/created mass and invalidate the diagnostic acceptance criteria.
- **Replace the full hydraulic geometry:** a broader experimental rewrite changed
  connected support and subdivision behavior; the retained repair is bounded to
  demonstrated producer, source and boundary defects.
- **Treat every change as unchanged science because coefficients stayed fixed:**
  ignores materially different executed behavior and the explicit timing and
  specialized-reference modeling choices.
- **Redesign specialized fire, canopy or root semantics during the port:** rejected
  under ADR-0134's ownership decision. Preserve and disclose the reference exceptions.
- **Switch retention defaults or require homogeneous soils to mask FC/HK ownership:**
  would leave the native defect or impose unrelated constraints. Preserve the
  intended inputs and fix consumer ownership.
- **Call successful execution universal validation:** would conflate engineering
  gates, physical accounting, magnitude acceptance and field calibration.

## Consequences and remaining limits

Corrected water supply and routing can propagate into runoff, ET, storage,
vegetation stress, peak flow and sediment. Aggregate agreement can conceal major
local/event changes, and correction direction is not uniformly positive or negative.
For example, default-retention heterogeneous OFE-3 runoff changed -84.692 mm hourly
but +36.875 mm daily over the retained 16-year revision-6 comparison.

The historical Roads magnitude screen remains unmet at 744/840. It is not a fresh
revision-7 result. Optional retention remains separate from default selection;
no universal rock multiplier, global frost change or physiological rewrite is
admitted. Complete water/energy closure and field validity remain unestablished.

Revision 6 repairs the specific FC/HK ownership defect that placed revision 5 on
HOLD. Revision 7 repairs the specialized consumer incompatibility. Neither change
retroactively validates earlier outputs or establishes unrestricted scientific
readiness. The specialized port retains its documented canopy, root-order and
logarithm-domain exceptions; single-event RAP is rejected.

## Evidence and related records

- [Consolidated report, edition 1](../../wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-consolidated-ed1.pdf), especially sections 2, 7, 11 and 14.
- [Approved publication manifest](../../wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/publication-manifest-consolidated-ed1.json).
- [Revision-2 release integration and retained comparisons](../work-packages/20261030_wepp_261029_rerelease/package.md).
- [ADR-0115: boundary-anchored deposition](ADR-0115-native-boundary-anchored-deposition.md) and [ADR-0118: stable Yalin capacity](ADR-0118-stable-yalin-transport-capacity.md).
- [ADR-0121: bounded root search](ADR-0121-depend-bounded-root-search.md), [ADR-0122: erosion interval support](ADR-0122-erod-subgrid-interval-support.md), [ADR-0123: nonzero inflow](ADR-0123-roads-nonzero-inflow-sediment-boundary.md), and [ADR-0124: denominator sign](ADR-0124-param-rounded-continuity-denominator-sign.md).
- [ADR-0129: interception](ADR-0129-conservative-interception-allocation.md), [ADR-0130: snow exhaustion](ADR-0130-explicit-snowpack-exhaustion.md), and [ADR-0131: freeze restoration](ADR-0131-donor-limited-freeze-restoration.md).
- [Native coefficient contract](../schemas/native-mofe-coefficient-contract.md) and [specialized revegetation contract](../schemas/specialized-revegetation-consumer-contract.md).

Some earlier ADR headings retain proposed or experiment-stage wording. This
synthesis does not rewrite those records; final artifact evidence and the
consolidated report distinguish implemented release behavior from earlier proposals.
Research proposals are not promoted merely because their files appear in the
release's source history.

## Risk and rollback notes

Use the complete matched executable pair, JSON sidecars and generated PASS chain.
Record revision, source commit and SHA256 values in comparisons; `wepp_261029` and
the unchanged `2020.500` banner do not uniquely identify the seven artifacts.

Preserve old binaries and their generated artifacts. If a new reproduction finds
incorrect ownership, invalid transfers, incompatible readers or an unexplained
material response, investigate against the exact offending pair and bounded
controls. An operational rollback must restore a complete previously accepted pair
and compatible outputs; it must not silently mix passes or overwrite the current
release under the same identity. Prior revisions have known defects and are not
automatically safe rollback targets. Selection remains an explicit operational
and scientific decision, not an automatic consequence of this ADR.

Existing project results are not silently regenerated. No new default selection,
production deployment, Windows artifact or broad regeneration is authorized here.

## Implementation notes and review

The current revision-7 source is `e0abe0581f77c6f66917e90daf8f8f429e9315c8`.
The public manifest records both exact binary hashes. The consolidated PDF SHA256 is
`429ec4862e6057235af7a63b98d70f02dbc2977ed5d44c7abfaf69f839d31ef2`.

Historical revision-7 evidence records 1,750 native tests, 31 watchlist cases,
both host smokes and a configured 72-hillslope/235-OFE/35-year application workflow.
Focused test counts overlap and must not be added. No model runs were performed
for this ADR or the editorial consolidation; the report approval is a publication
decision, not a new scientific experiment.

Owner review is required to move this release-level ADR from Proposed to Accepted.
Revisit it when changing the default release, admitting a new retention/frost or
specialized scientific policy, revising a material validation conclusion, or
publishing a different executable generation. The approved PDF stays immutable;
substantive corrections require a separately identified report edition and evidence.
